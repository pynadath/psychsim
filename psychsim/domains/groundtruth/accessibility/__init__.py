from argparse import ArgumentParser
import csv
import logging
import os.path
import pickle
import random

from psychsim.pwl import *

from ..simulation.cdf import value2dist
from ..simulation.create import loadPickle,getConfig
from ..simulation.data import *

instances = [{'instance': 24,'run': 1,'span': 82},
    {'instance': 27,'run': 0,'span': 565},
    {'instance': 53,'run': 1,'span': 147},
    {'instance': 52,'run': 1,'span': 135},
    {'instance': 51,'run': 1,'span': 77},
    {'instance': 55,'run': 1,'span': 181},
    {'instance': 56,'run': 1,'span': 168},
    {'instance': 54,'run': 1,'span': 172},
    {'instance': 81,'run': 0,'span': None},
    {'instance': 83,'run': 0,'span': None},
    {'instance': 82,'run': 0,'span': None},
    {'instance': 86,'run': 0,'span': None},
    {'instance': 84,'run': 0,'span': None},
    {'instance': 85,'run': 0,'span': None}]
    
def createParser(output=None,day=None,seed=False,instances=False):
    """
    :param instances: if True, then accept multiple instances
    :return: dictionary of arguments
    """
    parser = ArgumentParser()
    if instances:
        parser.add_argument('-i','--instances',default='24',help='Instances to query')
    else:
        parser.add_argument('-i','--instance',type=int,default=24,help='Instance to query')
    parser.add_argument('-r','--run',type=int,default=1,help='Run to query')
    if output:
        parser.add_argument('-o','--output',default=output,help='Output filename')
    if day:
        parser.add_argument('--day',type=int,default=0,help='Day to start from (default is beginning)')
    if seed:
        parser.add_argument('--seed',type=int,default=1,help='Random number generator seed')
    parser.add_argument('-d','--debug',default='INFO',help='Level of logging detail')
    return parser

def parseArgs(parser,logfile=None):
    args = vars(parser.parse_args())
    # Extract logging level from command-line argument
    level = getattr(logging, args['debug'].upper(), None)
    if not isinstance(level, int):
        raise ValueError('Invalid debug level: %s' % args['debug'])
    if logfile is None:
        logging.basicConfig(level=level)
    else:
        logging.basicConfig(level=level,filename=logfile)
    if 'seed' in args:
        random.seed(args['seed'])
    if 'instances' in args:
        instances = args['instances'].split(',')
        instances = [instance.split('-') for instance in instances]
        args['instances'] = sum([list(range(int(instance[0]),int(instance[1])+1))
                         if len(instance) == 2 else [int(instance[0])]
                         for instance in instances],[])
    return args

def getDirectory(args):
    return os.path.join(os.path.dirname(__file__),'..','Instances','Instance%d' % (args['instance']),'Runs','run-%d' % (args['run']))

def loadFromArgs(args,world=False,hurricanes=False,participants=False,actions=False,deaths=False,network=False,runData=False):
    values = {'directory': getDirectory(args)}
    if world:
        try:
            day = args['day']
        except KeyError:
            day = 0
        values['world'] = loadPickle(args['instance'],args['run'],day)
    if participants:
        values['participants'] = readParticipants(args['instance'],args['run'])
    if actions:
        values['actions'] = readActions(args['instance'],args['run'])
    if hurricanes:
        values['hurricanes'] = readHurricanes(args['instance'],args['run'])
    if deaths:
        values['deaths'] = readDeaths(args['instance'],args['run'])
    if network:
        values['network'] = readNetwork(args['instance'],args['run'])
    if runData:
        values['run'] = readRunData(args['instance'],args['run'])
    return values

def writeOutput(args,data,fields=None,fname=None,dirName=None):
    if fields is None:
        fields = sorted(list(data[0].keys()))
    if fname is None:
        fname = args['output']
    if dirName is None:
        dirName = os.path.join(os.path.dirname(__file__),'..','Instances','Instance%d' % (args['instance']),'Runs','run-%d' % (args['run']))
    with open(os.path.join(dirName,fname),'w') as csvfile:
        writer = csv.DictWriter(csvfile,fields,delimiter='\t',extrasaction='ignore')
        writer.writeheader()
        for record in data:
            writer.writerow(record)

def openFile(args,fname):
    return open(os.path.join(os.path.join(os.path.dirname(__file__),'..','Instances','Instance%d' % (args['instance']),'Runs','run-%d' % (args['run'])),fname),'r')

def loadRunData(instance,run=0,end=None,nature=False):
    inFile = os.path.join(os.path.dirname(__file__),'..','Instances','Instance%d' % (instance),
                          'Runs','run-%d' % (run),'RunDataTable.tsv')
    data = {}
    with open(inFile,'r') as csvfile:
        reader = csv.DictReader(csvfile,delimiter='\t')
        for row in reader:
            t = int(row['Timestep'])
            if end is not None and t > end:
                break
            if 'BeliefOf' in row['VariableName']:
                if row['EntityIdx'] not in data:
                    data[row['EntityIdx']] = {}
                if '__beliefs__' not in data[row['EntityIdx']]:
                    data[row['EntityIdx']]['__beliefs__'] = {}
                try:
                    cls,feature = row['VariableName'][len('ActorBeliefOf'):].split()
                except ValueError:
                    cls = WORLD
                    feature = row['VariableName'][len('ActorBeliefOf'):]
                if cls == 'Actor':
                    key = stateKey(row['EntityIdx'],feature)
                else:
                    key = stateKey(cls,feature)
                if key not in data[row['EntityIdx']]['__beliefs__']:
                    data[row['EntityIdx']]['__beliefs__'][key] = {}
                data[row['EntityIdx']]['__beliefs__'][key][t] = value2dist(row['Value'],row['Notes'])
            else:
                words = row['VariableName'].split()
                if len(words) == 1:
                    entity = WORLD
                    feature = words[0]
                    key = stateKey(entity,feature)
                elif len(words) == 4:
                    entity = words[0]
                    key = binaryKey(entity,words[3],words[2])
                else:
                    assert len(words) == 2,row['VariableName']
                    entity = row['EntityIdx']
                    feature = words[1]
                    if feature == 'action':
                        if t == 1:
                            continue
                        else:
                            t -= 1
                            feature = ACTION
                    key = stateKey(entity,feature)
                if entity not in data:
                    data[entity] = {}
                if key not in data[entity]:
                    data[entity][key] = {}
                data[entity][key][t] = value2dist(row['Value'],row['Notes'])
    if nature:
        inFile = os.path.join(os.path.dirname(__file__),'..','Instances','Instance%d' % (instance),
                              'Runs','run-%d' % (run),'InstanceVariableTable.tsv')
        data['Nature'] = {}
        with open(inFile,'r') as csvfile:
            reader = csv.DictReader(csvfile,delimiter='\t')
            for row in reader:
                t = int(row['Timestep'])
                if end is not None and t > end:
                    break
                entity,feature = row['Name'].split()
                if feature == 'action':
                    if t == 1:
                        continue
                    else:
                        t -= 1
                        feature = ACTION
                key = stateKey(entity,feature)
                if key not in data[entity]:
                    data[entity][key] = {}
                data[entity][key][t] = value2dist(row['Value'])
    return data

def findHurricane(day,hurricanes):
    for hurricane in hurricanes:
        if day < hurricane['Start']:
            return None
        elif day <= hurricane['End']:
            return hurricane
    else:
        return None


def findMatches(record,world=None,population={}):
    mismatch = {}
    matches = set()
    if world is None:
        people = population
    else:
        people = world.agents
    for name in sorted(people):
        if name[:5] == 'Actor':
            for field,feature in sorted(demographics.items()):
                if field == 'Wealth':
                    continue
                if name in population:
                    value = population[name][field]
                else:
                    key = stateKey(name,feature)
                    if world.variables[key]['domain'] is bool:
                        value = {True: 'yes',False: 'no'}[world.agents[name].getState(feature).first()]
                    else:
                        value = str(world.agents[name].getState(feature).first())
                if record[field] != value and record[field] != str(value):
                    try:
                        mismatch[field].append(name)
                    except KeyError:
                        mismatch[field] = [name]
                    break
            else:
                logging.info('Participant %s: %s' % (record['Participant'],name))
                matches.add(name)
    if matches:
        return matches
    else:
        raise ValueError('No match for %s (mismatches: %s)' % (record['Participant'],mismatch))

def readDemographics(data,old=False,last=True,name=None):
    demos = {}
    if name:
        names = [name]
    else:
        names = [name for name in data if name[:5] == 'Actor']
    for name in names:
        demos[name] = {}
        for field,feature in demographics.items():
            series = data[name][stateKey(name,feature)]
            if not isinstance(last,bool):
                value = series[min(max(series),last)]
            elif last:
                value = series[max(series)]
            else:
                value = series[1]
            if value is True:
                value = 'yes'
            elif value is False:
                value = 'no'
            elif field == 'Wealth':
                if old:
                    value = int(value*5.1)
                else:
                    value = toLikert(value)
            demos[name][field] = value
    return demos

def assistance(data,hurricane,region):
    govt = [data['System'][actionKey('System')][t] for t in range(hurricane['Start'],hurricane['End'])]
    count = len([a for a in govt if a['object'] == region])
    return toLikert(float(count)/float(len(govt)))

def propertyDamage(data,hurricane,region):
    real = [float(data[region][stateKey(region,'risk')][t]) \
        for t in range(hurricane['Start'],hurricane['End']+1)]
    # Use real value to be consistent (but can compare against risk perception if desired)
    return toLikert(max(real))

def employment(data,name,hurricane):
    employed = [data[name][stateKey(name,'employed')].get(t,data[name][stateKey(name,'employed')][1]) \
        for t in range(hurricane['Landfall'],hurricane['End'])]
    sheltered = [data[name][stateKey(name,'location')][t][:7] == 'shelter' for t in range(hurricane['Landfall'],hurricane['End'])]
    possible = employed.count(True)
    worked = [employed[t] and not sheltered[t] for t in range(len(employed))].count(True)
    return worked,possible