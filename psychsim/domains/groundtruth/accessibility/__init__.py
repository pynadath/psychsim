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
    {'instance': 81,'run': 1,'span': 79},
    {'instance': 83,'run': 1,'span': 133},
    {'instance': 82,'run': 1,'span': 130},
    {'instance': 86,'run': 1,'span': 173},
    {'instance': 84,'run': 1,'span': 176},
    {'instance': 85,'run': 1,'span': 189}]
    
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

def instanceFile(args,name,sub=None):
    fname = os.path.join(os.path.join(os.path.dirname(__file__),'..','Instances','Instance%d' % (args['instance']),'Runs','run-%d' % (args['run'])))
    if sub:
        fname = os.path.join(fname,sub)
    return os.path.join(fname,name)

def openFile(args,fname,sub=None):
    return open(instanceFile(args,fname,sub),'r')

def loadRunData(instance,run=0,end=None,nature=False,subs=[None]):
    fields = None
    data = {}
    for sub in subs:
        if isinstance(sub,tuple):
            useRun = sub[0]
        else:
            useRun = run
        inFile = os.path.join(os.path.dirname(__file__),'..','Instances','Instance%d' % (instance),'Runs','run-%d' % (useRun))
        if isinstance(sub,tuple):
            inFile = os.path.join(inFile,sub[1])
        elif sub:
            inFile = os.path.join(inFile,sub)
        inFile = os.path.join(inFile,'RunDataTable.tsv')
        with open(inFile,'r') as csvfile:
            reader = csv.DictReader(csvfile,fields,delimiter='\t')
            for row in reader:
                if fields is None:
                    fields = row.keys()
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
        assert subs is None,'Have not yet implemented this'
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
            try:
                series = data[name][stateKey(name,feature)]
            except KeyError:
                series = data[name][stateKey(name,oldDemographics[field])]
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

def getTarget(instance,run=0):
    actor = None
    with open(os.path.join(os.path.join(os.path.dirname(__file__),'..','Instances','Instance%d' % (instance),'Runs','run-%d' % (run),
        'Input'),'TargetActor.tsv'),'r') as csvfile:
        reader = csv.DictReader(csvfile,delimiter='\t')
        for row in reader:
            assert actor is None,'Multiple targets found'
            actor = row['Participant']
    assert actor is not None,'No target found'
    return int(actor)

def getPopulation(data):
    """
    :return: list of names of actors who are still alive at the end of the simulation, represented by the given data
    """
    return [name for name in data if name[:5] == 'Actor' and data[name][stateKey(name,'alive')][max(data[name][stateKey(name,'alive')].keys())]]

def setBelief(actor,world,data,t):
    """
    Sets the belief state of the given actor to be whatever its beliefs were at timestep t in the given run data
    """
    agent = world.agents[actor]
    beliefs = agent.getBelief()
    model,myBelief = next(iter(beliefs.items()))
    newBelief = copy.deepcopy(myBelief)
    for key,history in data[actor]['__beliefs'].items():
        value = history[t]
        name,feature = state2tuple(key)
        if name == 'Actor':
            key = stateKey(actor,feature)
        elif name == 'Region':
            key = stateKey(agent.home,feature)
        else:
            print(key)
        world.setFeature(key,value,newBelief)
    return newBelief

def setHurricane(world,category,location,actor,actions=None,locations=None,myStart=None,debug=False):
    """
    :param start: Initial location for actor (default is current location)
    """
    beliefs = world.agents[actor].getBelief()
    model,myBelief = next(iter(beliefs.items()))
    myBelief = copy.deepcopy(myBelief)
    world.setState('Nature','category',category,myBelief)
    world.setState('Nature','phase','approaching',myBelief)
    world.setState('Nature','days',0,myBelief)
    world.setState('Nature','location',location,myBelief)
    if myStart:
        world.setState(actor,'location',myStart,myBelief)
    while world.getState('Nature','location',myBelief).first() != 'none':
        if debug:
            logging.info('%s: %s %s' % (world.next(myBelief),world.getState('Nature','phase',myBelief).first(),
                world.getState('Nature','location',myBelief).first()))
        result = world.step(state=myBelief,select=True,keySubset=myBelief.keys())
        if actions is not None:
            action = myBelief.marginal(actionKey(actor)).first()
            actions.append(world.float2value(actionKey(actor),action))
        if locations is not None:
            locations.append(world.getState(actor,'location',myBelief).first())
    return myBelief

def getParticipantID(name,pool):
    for num,actor in pool.items():
        if name == actor:
            return num
    else:
        raise ValueError('%s not found in pool' % (name))

def hurricanePrediction(world,hurricane,debug=False):
    state = copy.deepcopy(world.state)
    world.setState('Nature','phase','approaching',state)
    location = hurricane['Actual Location'][0]
    world.setState('Nature','location',location,state)
    world.setState('Nature','category',int(hurricane['Actual Category'][0]),state)
    world.setState('Nature','days',0,state)
    world.setState(WORLD,'day',hurricane['Start'],state)
    action = next(iter(world.agents['Nature'].actions))
    predictions = []
    while location != 'none':
        world.rotateTurn('Nature',state)
        world.step({'Nature': action},state,updateBeliefs=False,select=True)
        phase = world.getState('Nature','phase',state).first()
        location = world.getState('Nature','location',state).first()
        if debug:
            print(phase,location,world.getState(WORLD,'day',state).first())
        if phase == 'active':
            record = {'Timestep': hurricane['Start'],
                'Hurricane': hurricane['Hurricane'],
                'Predicted Timestep': world.getState(WORLD,'day',state).first(),
                'Predicted Location': location,
                'Predicted Category': world.getState('Nature','category',state).first()}
            predictions.append(record)
    return predictions