from argparse import ArgumentParser
import csv
import fileinput
import logging
import sys

from psychsim.modeling import *

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
                    logger.info('Question: %s' % (field['question']))
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
                        logger.info('%s: %s' % (field['question'],field['labels'].values()))
                else:
                    logger.warning('Missing value labels: %s' % (field['question']))
                field = {}
    return codebook

def createWorld(domain,codebook,logger=logging.getLogger()):
    logger = logger.getChild('createWorld')
    world = World()
    for name,field in domain.fields.items():
        if field['agent']:
            if not world.agents.has_key(field['agent']):
                world.addAgent(field['agent'])
            agent = world.agents[field['agent']]
            model = '%s0' % (agent.name)
            world.setModel(agent.name,model)
        else:
            agent = None
        if field['class'] == 'state':
            if field['type'] == 'list':
                feature = world.defineState(agent,field['variable'],list,codebook[field['field']]['labels'].values())
            elif field['type'] == 'int':
                feature = world.defineState(agent,field['variable'],int)
            logger.debug('New state feature: %s' % feature)
        elif field['class'] == 'action':
            assert field['agent']
            action = Action({'subject': agent.name,'verb': field['variable']})
            agent.addAction(action)
            logger.debug('New action: %s' % (action))
    world.setOrder(world.agents.keys())
    return world

def modelIndividual(domain,world,record,codebook,logger=logging.getLogger()):
    logger = logger.getChild('modelIndividual')
    logger.info(domain.recordID(record))
    for name,field in domain.fields.items():
        if field['class'] == 'state':
            value = record[field['field']].strip()
            if len(value) == 0:
                value = '-1'
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
        table[datum[field]] = table.get(datum[field],0)+1
    total = float(sum(table.values()))
    table = {k: float(v)/total for k,v in table.items()}
    return table

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
    domain = Domain('afrobarometer')
    logging.debug('#records = %d' % (len(domain.data)))
    world = createWorld(domain,codebook)
    for input in domain.fields:
        print input
        for field,histogram in domain.targetHistogram().items():
            print field
            for key,matches in sorted(histogram.items(),key=lambda item: -len(item[1])):
                print '\t%5d: %s' % (len(matches),codebook[field]['labels'][key])
                table = tabulate([domain.data[ID] for ID in matches],input)
                print table.keys()
                print ', '.join(['%s: %4.1f%%' % (codebook[input]['labels'].get(k,k),table[k]*100.) for k in sorted(table.keys())])
#    for ID,record in domain.data.items():
#        modelIndividual(domain,world,record,codebook)
