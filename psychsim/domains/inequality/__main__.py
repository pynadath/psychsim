from argparse import ArgumentParser
import copy
import csv
import fileinput
import itertools
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

label2prob = {'Never': 0.,'Less than once a month': 0.1,'A few times a month': 0.25, 'A few times a week': 0.5,'Every day': 1.,
    'Just once or twice': 0.25, 'Several times': 0.5, 'Many times': 0.75, 'Always': 1.,
    'Much worse': 0., 'Worse': 0.25, 'Same': 0.5, 'Better': 0.75, 'Much better': 1.,
    'No (not looking)': 0., 'No (looking)': 0.25, 'Yes part time': 0.75, 'Yes full time': 1.,
    'Very bad': 0., 'Fairly bad': 0.25, 'Neither good nor bad': 0.5, 'Fairly good': 0.75, 'Very good': 1.,
    'I feel only (R’s ethnic group)': 0.,'I feel more (R’s ethnic group) than national ID': 0.25,
    'I feel equally national ID and (R’s ethnic group)': 0.5,'I feel more national ID than (R’s ethnic group)': 0.75,
    'I feel only national ID': 1.}

def scoreModel(model,target,data,codebook,ignoreNull=False):
    matches = set()
    for label,datum in data.items():
        if ignoreNull and datum[target] == '0':
            continue
        prob = None
        for field,value in model.items():
            if value is not None:
                factor = 0.5*label2prob[codebook[field]['labels'][datum[field]]]
                if value is False:
                    factor = 1.-factor
                if factor > 1e-6:
                    if prob is None:
                        prob = factor
                    else:
                        prob *= factor
        if prob is None:
            if datum[target] == '0':
                matches.add(label)
        else:
            if int(datum[target]) == int(round(prob*4)):
                matches.add(label)
    print({key:value for key,value in model.items() if value is not None},len(matches))
    return matches

def greedyMatch(matchTable,field,records):
    print(field,len(records))
    hypotheses = sorted([(len(records & matchTable[row][field]),row) for row in range(len(matchTable)) 
        if '%s Rank' % (field) not in matchTable[row]],reverse=True)
    best = matchTable[hypotheses[0][1]]
    if hypotheses[0][0]:
        best['%s Rank' % (field)] = len(matchTable) - len(hypotheses) + 1
        records -= best[field]
        return greedyMatch(matchTable,field,records)
    else:
        # No matches left
        return records

if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('-d','--debug',default='WARNING',help='Level of logging detail')
    parser.add_argument('-t','--threshold',default=0.1,type=float,help='Minimal correlation for considering hypothesis')
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
    print(sorted(hypotheses))
    data = domain.data
    ranges = {}
    for hyp in hypotheses|domain.targets:
        if hyp == 'Q2A.Age':
            # Age allows for arbitrary integers
            data = {ID: record for ID,record in data.items() if record[hyp] != ' ' and codebook[hyp]['labels'].get(record[hyp],'OK') not in 
                {'Missing','Don’t know','Not applicable','Not asked','Refused to answer','Don’t','Exception handling','Missing Data','Don’t Know'}}
            logging.debug('%s: %s' % (hyp,sorted({(record[hyp],record[hyp]) for record in data.values()})))
        else:
            try:
                data = {ID: record for ID,record in data.items() if record[hyp] != ' ' and codebook[hyp]['labels'][record[hyp]] not in 
                    {'Missing','Don’t know','Not applicable','Not asked','Refused to answer','Don’t','Exception handling','Missing Data','Don’t Know'}}
            except KeyError:
                print(sorted(['%s: %s' % (ID,record[hyp]) for ID,record in data.items() if record[hyp] not in codebook[hyp]['labels']]))
                raise RuntimeError('Unable to process field: %s' % (hyp))
            logging.debug('%s: %s' % (hyp,sorted({(record[hyp],codebook[hyp]['labels'][record[hyp]]) for record in data.values()})))
        logging.info('After %s: %d' % (hyp,len(data)))
        ranges[hyp] = sorted(map(int,{record[hyp] for record in data.values()}))
        logging.debug('%d,%d' % (ranges[hyp][0],ranges[hyp][-1]))
    countries = partition(data,'COUNTRY_ALPHA',codebook)
    countryStats = {}
    sigHypos = {hyp: {0: set()} for hyp in hypotheses}
    for country,countryData in sorted(countries.items()):
        logging.info('Country: %s (%d)' % (country,len(countryData)))
        target = 'Q55.Unfairly_Ethnic'
        histogram = domain.targetHistogram('-1',countryData)[target]
        for key,matches in sorted(histogram.items(),key=lambda item: -len(item[1])):
            logging.debug('Target: %s=%s (%d)' % (target,codebook[target]['labels'][key],len(matches)))
        hypList = sorted(hypotheses)
        arrays = numpy.array([[float(record[field]) for field in hypList+[target]] for record in countryData.values()]).T
        covar = numpy.cov(arrays)
        countryStats[country] = {hypList[i]: covar[i][len(hypList)] for i in range(len(hypList))}
        for hyp,value in countryStats[country].items():
            if abs(value) > args['threshold']:
                try:
                    sigHypos[hyp][int(numpy.sign(value))].add(country)
                except KeyError:
                    sigHypos[hyp][int(numpy.sign(value))] = {country}
    hypSpace = []
    for hyp,table in sorted(sigHypos.items()):
        if len(table) > 1:
            print(hyp)
            for value,entries in table.items():
                if value != 0:
                    print(value,sorted(entries))
                    hypSpace.append((hyp,value == 1))
        else:
            del sigHypos[hyp]
    output = []
    for numberUp in range(1,5):
        for hypUp in itertools.combinations(hypSpace,numberUp):
            # Remove combinations that are contradictory
            if len({hyp for hyp,val in hypUp}) == len(hypUp):
                model = {hyp: None for hyp in sigHypos}
                for hyp,val in hypUp:
                    model[hyp] = val
                record = {'Model': hypUp}
                matches = scoreModel(model,target,data,codebook)
                record['Total'] = matches
                record['Total %'] = len(matches)/len(data)
                for country,countryData in sorted(countries.items()):
                    record[country] = matches & set(countryData.keys())
                    record['%s %%' % (country)] = len(record[country])/len(countryData)
                output.append(record)
    for country,countryData in countries.items():
        print(country,len(countryData),len(greedyMatch(output,country,set(countryData.keys()))))
    fields = ['Model','Total %']+['%s %%' % (country) for country in sorted(countries.keys())]+\
        ['%s Rank' % (country) for country in sorted(countries.keys())]
    with open('afrobarometer.tsv','w') as csvfile:
        writer = csv.DictWriter(csvfile,fields,delimiter='\t',extrasaction='ignore')
        writer.writeheader()
        for record in output:
            writer.writerow(record)
    print(len([record for record in data.values() if record[target] != '0']))
    print(len(data))
    exit()
    for inData in domain.fields:
        for field,histogram in domain.targetHistogram('-1').items():
            for key,matches in sorted(histogram.items(),key=lambda item: -len(item[1])):
                print('\t%5d: %s=%s | %s' % (len(matches),field,codebook[field]['labels'][key],inData))
                table = tabulate([domain.data[ID] for ID in matches],inData)
                print(', '.join(['%s: %4.1f%%' % (codebook[inData]['labels'].get(k,k),pct*100.) for k,pct in sorted(table.items(),key=lambda i: i[1],reverse=True)]))
#    for ID,record in domain.data.items():
#        modelIndividual(domain,world,record,codebook)
