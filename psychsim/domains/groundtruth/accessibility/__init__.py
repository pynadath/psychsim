from argparse import ArgumentParser
import csv
import logging
import os.path
import pickle
import random

from psychsim.pwl import *

from ..simulation.cdf import *
from ..simulation.create import loadPickle,getConfig
from ..simulation.data import *
from ..simulation.execute import exchangeMessages

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
    {'instance': 85,'run': 1,'span': 189},
    {'instance': 90,'run': 0,'span': 123},
    {'instance': 100,'run': 0,'span': 122},
    {'instance': 101,'run': 0,'span': 135},
    {'instance': 100,'run': 2,'span': 82},
    {'instance': 101,'run': 1,'span': 130},]
    
instanceMap = {'Phase1': {'Explain': [1], 'Predict': [3,4,5,6,7,8], 'Prescribe': [9,10,11,12,13,14]},
    'Phase2': {'Explain': [15,16,17], 'Predict': [18,19]},
    'Phase3': {},
    }
def instanceArgs(phase,challenge=True):
    if challenge is True:
        result = []
        for challenge in instanceMap[phase]:
            result += list(instanceArgs(phase,challenge))
        return result
    else:
        return {instance: instances[instance-1] for instance in instanceMap[phase][challenge]}.items()

def allArgs():
    """
    :warning: Skips Instance2, which was generated only for Team B's request
    """
    return {instance+1: instances[instance] for instance in range(len(instances)) if instance != 1}.items()
def instancePhase(instance):
    assert instance > 0,'First instance is 1'
    assert instance <= len(instances),'Latest instance is %d' % (len(instances))
    return 1 if instance < 15 else 2
def instanceChallenge(instance):
    for phase,table in instanceMap.items():
        for challenge,instances in table.items():
            if instance in instances:
                return phase,challenge
    else:
        raise ValueError('Unknown instance: %s' % (instance))

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
    if dirName and not os.path.exists(dirName):
        os.makedirs(dirName)
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

def loadMultiCSV(fname,instance,run=0,subs=[None],grabFields=True):
    fields = None
    data = []
    for sub in subs:
        with openFile({'instance': instance,'run': run},fname,sub) as csvfile:
            reader = csv.DictReader(csvfile,fields,delimiter='\t')
            for row in reader:
                if fields is None and grabFields:
                    fields = row.keys()
                else:
                    yield row

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

def findHurricane(day,hurricanes,includePrevious=False):
    """
    :param includePrevious: if True, then return the most recent hurricane if this day does not fall within any (otherwise, return None)
    """
    previous = None
    for hurricane in hurricanes:
        if day < hurricane['Start']:
            if includePrevious:
                return previous
            else:
                return None
        elif day <= hurricane['End']:
            return hurricane
        previous = hurricane
    else:
        if includePrevious:
            return previous
        else:
            return None


def findMatches(record,world=None,population={},ignoreWealth=True):
    mismatch = {}
    matches = set()
    if world is None:
        people = population
    else:
        people = world.agents
    for name in sorted(people):
        if name[:5] == 'Actor':
            for field,feature in sorted(demographics.items()):
                if field == 'Wealth' and ignoreWealth:
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
                logging.debug('Participant %s: %s' % (record['Participant'],name))
                matches.add(name)
    if matches:
        return matches
    else:
        for key,names in mismatch.items():
            print(key)
            print({name: population[name][key] for name in names})
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

def prosocial(data):
    """
    :return: The actors who performed prosocial behavior on each day in each region
    """
    result = {name: {} for name in data if name[:6] == 'Region'}
    actors = [name for name in data if name[:5] == 'Actor']
    for name in actors:
        for t,action in data[name][actionKey(name)].items():
            if action['verb'] == 'decreaseRisk':
                try:
                    result[action['object']][t].add(name)
                except KeyError:
                    result[action['object']][t] = {name}
    return result

def aidTargets(data,start=None,end=None):
    if end is None:
        if start is None:
            start = 1
        return [data['System'][actionKey('System')][t+1]['object'] for t in range(start-1,len(data['System'][actionKey('System')]))]
    else:
        if start is None:
            start = 1
        return [data['System'][actionKey('System')][t]['object'] for t in range(start,end)]

def assistance(data,hurricane,region):
    govt = aidTargets(data,hurricane['Start'],hurricane['End'])
    count = len([obj for obj in govt if obj == region])
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

def setBelief(actor,world,data,t,debug=False):
    """
    Sets the belief state of the given actor to be whatever its beliefs were at timestep t in the given run data
    """
    agent = world.agents[actor]
    beliefs = agent.getBelief()
    model,myBelief = next(iter(beliefs.items()))
    newBelief = copy.deepcopy(myBelief)
    for key in newBelief.keys():
        if isActionKey(key):
            continue
        try:
            value = data[actor]['__beliefs__'][key][t]
            if debug: print('Found historical belief for %s' % (key))
        except KeyError:
            if isStateKey(key):
                name = state2agent(key)
            else:
                continue
#                terms = key.split()
#                assert terms[2] == '->'
#                name = terms[0]
            try:
                value = data[name][key][t]
                if debug: print('Found historical value for %s' % (key))
            except KeyError:
                if debug: print('No new value for %s' % (key))
                continue
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

def backwardDemographics(agent,demos):
    agent.demographics = {}
    for key,feature in demographics.items():
        agent.demographics[feature] = demos[agent.name][key]
        
def writeVarDef(dirName,items,relationships=False):
    fields = ['Name','LongName','Values','VarType','DataType','Notes']
    if relationships:
        fields[3] = 'RelType' 
    output = []
    for item in items:
        if 'Values' not in item:
            if item['DataType'] == 'Boolean':
                item['Values'] = 'yes,no'
            else:
                raise ValueError('Values missing from item %s' % (item['Name']))
        if 'LongName' not in item:
            item['LongName'] = item['Name']
        if '%sType' % ('Rel' if relationships else 'Var') not in item:
            item['%sType' % ('Rel' if relationships else 'Var')] = 'dynamic'
    if not os.path.exists(os.path.join(dirName,'SimulationDefinition')):
        os.makedirs(os.path.join(dirName,'SimulationDefinition'))
    with open(os.path.join(dirName,'SimulationDefinition','RelationshipDefTable.tsv' if relationships else 'VariableDefTable.tsv'),'w') as csvfile:
        writer = csv.DictWriter(csvfile,fields,delimiter='\t',extrasaction='ignore')
        writer.writeheader()
        for record in items:
            writer.writerow(record)

def trustInFriends(config,world,friends):
    trust = {'over': config.getint('Actors','friend_opt_trust'),
        'under': config.getint('Actors','friend_pess_trust')}
    trust['none'] = (trust['over']+trust['under'])/2
    return sum([trust[world.agents[friend].distortion] for friend in friends])/len(friends)

def getDeath(args,name,world,states,t):
    for day in range(2,t+1):
        if not getInitialState(args,name,'alive',world,states,day).first():
            return day
    else:
        return None

def getLivePopulation(args,world,states,t):
    """
    :return: dictionary of names of all actors, with the value being the day of their death (or None if they are still alive as of day t)
    """
    if 'Actor0001' in states:
        # Backward compatibility with Phase 1
        actors = {}
        # Find day of death
        for name in states:
            if name[:5] == 'Actor':
                if states[name][stateKey(name,'alive')][len(states[name][stateKey(name,'alive')])-1]:
                    actors[name] = None
                else:
                    # Person died some time
                    for t,value in states[name][stateKey(name,'alive')].items():
                        if not value:
                            actors[name] = t
                            break
        return actors
    else:
        return {name: getDeath(args,name,world,states,t) for name in world.agents if name[:5] == 'Actor'}

def getCurrentDemographics(args,name,world,states,config,t=None):
    """
    :param t: If None, read from the current world state
    """
    if 'Actor0001' in states:
        # Backward compatibility with Phase 1
        return readDemographics(states,old=args['instance'] == 24,last=t,name=name)[name]
    else:
        entry = {}
        for field,key in demographics.items():
            if field == 'Wealth':
                if t is None:
                    value = world.getState(name,'resources')
                else:
                    value = getInitialState(args,name,'resources',world,states,t)
                entry[field] = toLikert(value.first(),7)
            elif field == 'Fulltime Job':
                if t is None:
                    value = world.getState(name,'employed')
                else:
                    value = getInitialState(args,name,'employed',world,states,t)
                entry[field] = 'yes' if value.first() else 'no'
            elif field == 'Pets':
                if stateKey(name,'pet') in world.variables:
                    if t is None:
                        value = world.getState(name,'pet')
                    else:
                        value = getInitialState(args,name,'pet',world,states,t)
                    entry[field] = 'yes' if  value.first() else 'no'
                else:
                    entry[field] = 'no'
            elif field == 'Age':
                if t is None:
                    day = world.getState(WORLD,'day').first()
                else:
                    day = t
                entry[field] = world.agents[name].demographics[key] + day//config.getint('Disaster','year_length')
            else:
                entry[field] = world.agents[name].demographics[key]
        return entry

def loadState(args,states,t,turn,world=None):
    """
    :param world: If provided, the state loaded will be applied to the world (clobbering the existing state and beliefs)
    """
    if t not in states:
        states[t] = {}
    if turn not in states[t]:
        with open(instanceFile(args,'state%d%s.pkl' % (t,turn)),'rb') as f:
            states[t][turn] = pickle.load(f)
    if world:
        for name,state in states[t][turn].items():
            if name == '__state__':
                world.state = state
            else:
                agent = world.agents[name]
                for model,belief in state.items():
                    agent.models[model]['beliefs'] = belief
#                model = agent.getBelief().keys()
#                assert len(model) == 1
#                model = next(iter(model))
#                agent.models[model]['beliefs'] = state[model]

def getInitialState(args,name,feature,world,states,t,believer=None):
    if isinstance(t,int):
        if 'Actor0001' in states:
            # Backward compatibility with Phase 1
            if believer is None:
                return states[name][stateKey(name,feature)][t]
            else:
                return states[believer]['__beliefs__'][stateKey(name,feature)][t]
        else:
            if t == 1:
                # Initial state
                if believer is None:
                    return world.getState(name,feature)
                else:
                    beliefs = world.agents[believer].getBelief()
                    assert len(beliefs) == 1
                    return world.getState(name,feature,next(iter(beliefs.values())))
            else:
                loadState(args,states,t-1,'Nature')
                if believer is None:
                    return world.getState(name,feature,states[t-1]['Nature']['__state__'])
                else:
                    return world.getState(name,feature,next(iter(states[t-1]['Nature'][believer].values())))
    elif isinstance(t,tuple):
        return [getInitialState(args,name,feature,world,states,day,believer) for day in range(t[0],t[1])]
    elif isinstance(t,list) or isinstance(t,set):
        return [getInitialState(args,name,feature,world,states,day,believer) for day in t]

def getAction(args,name,world,states,t):
    """
    :rtype: ActionSet
    """
    if isinstance(t,int):
        if 'Actor0001' in states:
            # Backward compatibility with Phase 1
            return states[name][actionKey(name)][t]
        else:
            turn = 'Actor' if name[:5] == 'Actor' else name
            loadState(args,states,t,turn)
            return world.getFeature(actionKey(name),states[t][turn]['__state__']).first()
    elif isinstance(t,tuple):
        if 'Actor0001' in states:
            # Backward compatibility with Phase 1
            return [getAction(args,name,world,states,day) for day in range(t[0],t[1]) if day == 1 or name == 'System' or \
                getInitialState(args,name,'alive',world,states,day)]
        else:
            return [getAction(args,name,world,states,day) for day in range(t[0],t[1]) if day == 1 or name == 'System' or \
                getInitialState(args,name,'alive',world,states,day).first()]

def readLog(args):
    """
    Extracts expected reward tables from 'psychsim.log'
    """
    ER = [None]
    with openFile(args,'psychsim.log') as logfile:
        for line in logfile:
            words = line.strip().split()
            if words:
                if words[0] == 'Day':
                    t = int(words[1])
                    ER.append({})
                elif words[0] == 'Evaluated':
                    action = Action(words[1])
                    if action['subject'] not in ER[-1]:
                        ER[-1][action['subject']] = {}
                    ER[-1][action['subject']][action] = float(words[-1])
    return ER

def unpickle(instance,sub=None,day=None):
    if day is None:
        if instance == 1:
            day = None
        elif instance < 9:
            day = instances[instance-1]['span']
        elif instance < 15:
            day = instances[instance-1]['span'] + 1
        else:
            day = 0
    if sub is None:
        if 3 <= instance <= 14:
            sub = 'Input'
    return loadPickle(instances[instance-1]['instance'],instances[instance-1]['run'],day,sub)

def aidIfWealthLoss(agent):
    return sum([agent.Rweights[k] for k in ['health','childrenHealth','neighbors']])/sum(agent.Rweights.values())

def holoCane(world,config,actors,span,select=True,policy={},unit='days',debug=False):
    if isinstance(actors,str):
        # Backward compatibility
        return holoCane(world,config,{actors},select,policy)
    state = copy.deepcopy(world.state)
    for key in list(state.keys()):
        actor = state2agent(key)
        if actor[:5] == 'Actor' and actor not in actors and actor not in policy:
            del state[key]
    if config.getboolean('Actors','messages'):
        friends = {name: world.agents[name].friends & set(policy.keys()) for name in actors}
    else:
        friends = {name: set() for name in actors}
    step = 3
    phase = 'none'
    dead = set()
    hurricane = 0
    history = [{'state': copy.deepcopy(state)}]
    if len(actors) == 1:
        history[0]['beliefs'] = copy.deepcopy(next(iter(world.agents[next(iter(actors))].getBelief(state).values())))
    else:
        history[0].update({name: copy.deepcopy(next(iter(world.agents[name].getBelief(state).values()))) for name in actors})
    timeUnits = 0
    while timeUnits < span or (unit == 'hurricanes' and phase != 'none'):
        everyone = set()
        for name in actors-dead:
            if world.getState(name,'alive',state).first():
                # Actor still alive
                if name in world.next(state) and friends[name]:
                    friends[name] = {friend for friend in friends[name] if world.getState(friend,'alive').first()}
                    everyone |= friends[name]
                    everyone.add(name)
            else:
                dead.add(name)
        if everyone:
            exchangeMessages(world,config,state,everyone)
        actions = {name: action for name,action in policy.items() if name in world.next(state) and action is not None}
        if debug:
            print(world.getState(WORLD,'day',state).first(),world.agents[next(iter(world.next(state)))].__class__.__name__,phase)
        world.step(actions=actions,state=state,select=select,keySubset=state.keys())
        step += 1
        oldPhase = phase
        phase = world.getState('Nature','phase',state).first()
        if phase == 'approaching' and oldPhase == 'none':
            hurricane += 1
        history.append({'state': copy.deepcopy(state)})
        if len(actors) == 1:
            history[-1]['beliefs'] = copy.deepcopy(next(iter(world.agents[next(iter(actors))].getBelief(state).values())))
        else:
            history[-1].update({name: copy.deepcopy(next(iter(world.agents[name].getBelief(state).values()))) for name in actors if name not in dead})
        if unit == 'days':
            timeUnits = step // 3
        elif unit == 'hurricanes':
            timeUnits = hurricane
        else:
            raise NameError('Unknown unit of time: %s' % (unit))
    return history

def findParticipants(fname,args,world,states,config,ignoreWealth=True):
    oldSurvey = []
    lastUpdate = 0
    actors = [name for name in world.agents if name[:5] == 'Actor']
    with open(fname,'r') as csvfile:
        reader = csv.DictReader(csvfile,delimiter='\t')
        for entry in reader:
            for key in ['Participant','Timestep', 'Hurricane', 'Age', 'Children', 'Wealth']:
                entry[key] = int(entry[key])
            t = entry['Timestep']
            if t != lastUpdate:
                current = {name: getCurrentDemographics(args,name,world,states,config,t) for name in actors}
                lastUpdate = t
            entry['Name'] = {name for name in findMatches(entry,population=current,ignoreWealth=ignoreWealth)
                if getInitialState(args,name,'alive',world,states,t).first()}
            assert entry['Name'],'No matches for: %s' % (entry)
            oldSurvey.append(entry)
    return oldSurvey
