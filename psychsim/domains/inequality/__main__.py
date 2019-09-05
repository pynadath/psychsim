from argparse import ArgumentParser
import copy
import csv
import fileinput
import logging
import numpy
import sys

from psychsim.action import Action
from psychsim.world import World
from psychsim import modeling

def readCodebook(fname,logger=logging.getLogger()):
    logger = logger.getChild('readCodebook')
    # Parse codebook
    codebook = {}
    start = True
    field = {}
    for line in fileinput.input(fname):
        if start:
            # Ignore first line
            start = False
        else:
            elements = line.split()
            if elements:
                if elements[0].strip() == 'withinwt':
                    break
                if not 'question' in field and elements[0][0] == 'Q':
                    value = ' '.join(elements[1:]).strip()
                    index = value.find('*')
                    if index > 0:
                        value = value[:index]
                    if elements[0] == 'Question:':
                        field['question'] = value
                    else:
                        field['question'] = '%s%s' % (elements[0],value)
                    logger.debug('Question: %s' % (field['question']))
                elif not 'domain' in field and elements[0] == 'Value' and elements[1] == 'Labels:':
                    logger.debug('values for %s' % (field['question']))
                    field['domain'] = set()
                    field['labels'] = {}
                    elements = elements[2:]
                    logger.debug(elements)
                elif not 'domain' in field and elements[0] == 'Value' and elements[1] == 'Labels' and elements[2] == 'a:':
                    logger.debug('values for %s' % (field['question']))
                    field['domain'] = set()
                    field['labels'] = {}
                    elements = elements[3:]
                elif elements[0][0] == '*':
                    continue
                if 'domain' in field:
                    elements = (' '.join(elements)).split(',')
                    logger.debug('elements: %s' % (elements))
                    for element in elements:
                        if '=' in element:
                            value,label = element.strip().split('=')
                            field['domain'].add(value)
                            field['labels'][value] = label
            else:
                codebook[field['question']] = field
                if 'labels' in field:
                    if len(field['domain']) == 0:
                        logger.warning('Empty domain: %s' % (field['question']))
                    else:
                        logger.debug('%s: %s' % (field['question'],';'.join(field['labels'].values())))
                else:
                    logger.warning('Missing value labels: %s' % (field['question']))
                field = {}
    return codebook

def createWorld(domain,codebook,logger=logging.getLogger()):
    logger = logger.getChild('createWorld')
    world = World()
    for name,field in domain.fields.items():
        if field['agent']:
            if field['agent'] not in world.agents:
                world.addAgent(field['agent'])
            agent = world.agents[field['agent']]
            model = '%s0' % (agent.name)
            world.setModel(agent.name,model)
        else:
            agent = None
        if field['class'] == 'state':
            if field['type'] == 'list':
                feature = world.defineState(agent,field['variable'],list,list(codebook[field['field']]['labels'].values()))
            elif field['type'] == 'int':
                feature = world.defineState(agent,field['variable'],int)
            logger.debug('New state feature: %s' % feature)
        elif field['class'] == 'action':
            assert field['agent']
            action = Action({'subject': agent.name,'verb': field['variable']})
            agent.addAction(action)
            logger.debug('New action: %s' % (action))
    for agent in world.agents.values():
        if len(agent.actions) == 0:
            agent.addAction({'verb': 'observe'})
    world.setOrder([{name for name in world.agents}])
    return world

def modelIndividual(domain,world,record,codebook,logger=logging.getLogger()):
    logger = logger.getChild('modelIndividual')
    logger.info(domain.recordID(record))
    for name,field in domain.fields.items():
        if field['class'] == 'state':
            value = record[field['field']].strip()
            if len(value) == 0:
                record[field['field']] = value = '-1'
            key = stateKey(field['agent'],field['field'])
            agent = world.agents[field['agent']]
            if world.variables[key]['domain'] is list:
                try:
                    value = codebook[field['field']]['labels'][value]
                except KeyError:
                    logger.warning('Unknown value %s[%s]=%s' % (domain.recordID(record),
                                                                field['field'],value))
                    continue
            agent.setState(field['variable'],value)
            logger.debug('%s: %s' % (key,value))
    agent = world.agents['respondent']
    behavior = agent.decide(world.state)

def tabulate(data,field):
    table = {}
    for datum in data:
        table[datum[field].strip()] = table.get(datum[field].strip(),0)+1
    total = float(sum(table.values()))
    table = {k: float(v)/total for k,v in table.items()}
    return table

def partition(data,field,codebook,minimal=True):
    if minimal:
        values = {record[field] for record in data.values()}
    else:
        values = codebook[field]['labels'].keys()
    return {codebook[field]['labels'][key]: {ID: record for ID,record in data.items() if record[field] == key} for key in values}

if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('-d','--debug',default='WARNING',help='Level of logging detail')
    args = vars(parser.parse_args())
    # Extract logging level from command-line argument
    level = getattr(logging, args['debug'].upper(), None)
    if not isinstance(level, int):
        raise ValueError('Invalid debug level: %s' % args['debug'])
    logging.basicConfig(level=level)
    # Read codebook
    codebook = readCodebook('Afrobarometer - Codebook 2000-2015.txt')
    # for key,entry in states.items():
    #     logging.info(codebook[key])
    domain = modeling.Domain('afrobarometer')
    logging.debug('#records = %d' % (len(domain.data)))
    world = createWorld(domain,codebook)
    hypotheses = set(domain.fields.keys()) - {'COUNTRY_ALPHA','URBRUR','REGION'} - domain.targets
    hypotheses -= {'Q1.Gender','Q2A.Age','Q3.Race','Q5.Tribe','Q7.Religion','Q53.Important_Problem','Q56_ARB.Religious_National'}
    domain.targets -= {'Q55_ARB.Unfairly_Religious'}
    data = domain.data
    ranges = {}
    for hyp in hypotheses|domain.targets:
        if hyp == 'Q2A.Age':
            # Age allows for arbitrary integers
            data = {ID: record for ID,record in data.items() if record[hyp] != ' ' and codebook[hyp]['labels'].get(record[hyp],'OK') not in 
                {'Missing','Don’t know','Not applicable','Not asked','Refused to answer','Don’t','Exception handling','Missing Data','Don’t Know'}}
            logging.debug('%s: %s' % (hyp,sorted({(record[hyp],record[hyp]) for record in data.values()})))
        else:            
            data = {ID: record for ID,record in data.items() if record[hyp] != ' ' and codebook[hyp]['labels'][record[hyp]] not in 
                {'Missing','Don’t know','Not applicable','Not asked','Refused to answer','Don’t','Exception handling','Missing Data','Don’t Know'}}
            logging.debug('%s: %s' % (hyp,sorted({(record[hyp],codebook[hyp]['labels'][record[hyp]]) for record in data.values()})))
        logging.info('After %s: %d' % (hyp,len(data)))
        ranges[hyp] = sorted(map(int,{record[hyp] for record in data.values()}))
        logging.debug('%d,%d' % (ranges[hyp][0],ranges[hyp][-1]))
    countries = partition(data,'COUNTRY_ALPHA',codebook)
    for country,countryData in sorted(countries.items()):
        logging.info('Country: %s (%d)' % (country,len(countryData)))
        target = 'Q55.Unfairly_Ethnic'
        histogram = domain.targetHistogram('-1',countryData)[target]
        for key,matches in sorted(histogram.items(),key=lambda item: -len(item[1])):
            logging.debug('Target: %s=%s (%d)' % (target,codebook[target]['labels'][key],len(matches)))
        hypList = sorted(hypotheses)
        arrays = numpy.array([[float(record[field]) if ranges[field][0] == 1 else float(record[field])+1. 
            for field in hypList+[target]] for record in countryData.values()]).T
        covar = numpy.cov(arrays)
        print(['%s: %6.3f' % (hypList[i],covar[i][len(hypList)]) for i in sorted(range(len(hypList)),key=lambda j: abs(covar[j][len(hypList)]),reverse=True)])
    exit()
    for inData in domain.fields:
        for field,histogram in domain.targetHistogram('-1').items():
            for key,matches in sorted(histogram.items(),key=lambda item: -len(item[1])):
                print('\t%5d: %s=%s | %s' % (len(matches),field,codebook[field]['labels'][key],inData))
                table = tabulate([domain.data[ID] for ID in matches],inData)
                print(', '.join(['%s: %4.1f%%' % (codebook[inData]['labels'].get(k,k),pct*100.) for k,pct in sorted(table.items(),key=lambda i: i[1],reverse=True)]))
#    for ID,record in domain.data.items():
#        modelIndividual(domain,world,record,codebook)
