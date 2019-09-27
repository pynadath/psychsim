from argparse import ArgumentParser
import copy
import csv
import logging
import os.path
import pickle
import random

from psychsim.pwl.keys import *
from psychsim.action import *
from psychsim.probability import Distribution
from psychsim.domains.groundtruth import accessibility

fields = {#'Population': ['Timestep','Deaths','Casualties','Evacuees','Sheltered'],
    #'Regional': ['Timestep','Region','Deaths','Casualties','Sheltered'],
    'Hurricane': ['Timestep','Name','Category','Location','Landed'],
    #'ActorPre': ['Participant','Timestep','Hurricane']+sorted(accessibility.demographics.keys())+['At Shelter','Evacuated','Anticipated Shelter',
    #    'Anticipated Evacuation','Category','Risk'],
    #'ActorPost': ['Participant','Timestep','Hurricane']+sorted(accessibility.demographics.keys())+['At Shelter','Evacuated','Injured',
    #    'Risk','Dissatisfaction','Shelter Possibility','Evacuation Possibility','Stay at Home Possibility'],
    'RunData': accessibility.fields['RunData'],
    'InstanceVariable': accessibility.fields['InstanceVariable'],
}

def doPopulation(world,state,actors,t,variables,entity,prefix=''):
    data = []
    var = '%sDeaths' % (prefix)
    living = {name for name in actors if world.getState(name,'alive',state).first()}
    if var not in variables:
        variables[var] = {'Name': var,'Values':'[0+]','DataType': 'Integer'}
    record = {'Timestep': t,'VariableName': var,'EntityIdx': entity,'Value': len(actors)-len(living)}
    data.append(record)
    var = '%sCasualties' % (prefix)
    living = {name for name in actors if world.getState(name,'alive',state).first()}
    if var not in variables:
        variables[var] = {'Name': var,'Values':'[0+]','DataType': 'Integer'}
    record = {'Timestep': t,'VariableName': var,'EntityIdx': entity,
        'Value': len([name for name in actors if float(world.getState(name,'health',state)) < 0.2])}
    data.append(record)
    var = '%sEvacuees' % (prefix)
    living = {name for name in actors if world.getState(name,'alive',state).first()}
    if var not in variables:
        variables[var] = {'Name': var,'Values':'[0+]','DataType': 'Integer'}
    record = {'Timestep': t,'VariableName': var,'EntityIdx': entity,
        'Value': len([name for name in living if world.getState(name,'location',state).first() == 'evacuated'])}
    data.append(record)
    var = '%sSheltered' % (prefix)
    living = {name for name in actors if world.getState(name,'alive',state).first()}
    if var not in variables:
        variables[var] = {'Name': var,'Values':'[0+]','DataType': 'Integer'}
    record = {'Timestep': t,'VariableName': var,'EntityIdx': entity,
        'Value': len([name for name in living if world.getState(name,'location',state).first()[:7] == 'shelter'])}
    data.append(record)
    return data

def chooseParticipant(entry,oldSurvey):
    old = [oldEntry for oldEntry in oldSurvey if entry['Name'] in oldEntry['Name'] and entry['Timestep'] == oldEntry['Timestep']]
    for oldEntry in old:
        if len(oldEntry['Name']) == 1:
            # Only one possible match
            entry['Participant'] = oldEntry['Participant']
            print('Unique match: %s (%d)' % (entry['Name'],entry['Participant']))
        elif old:
            # Which matches best
            correct = {name for name,wrong in oldEntry['Name'].items() if len(wrong) == 0}
            if len(correct) == 0:
                print('Unable to match (%d):\n%s' % (oldEntry['Participant'],oldEntry))
                print(oldEntry['Name'])
                best = min(map(len,oldEntry['Name'].values()))
                correct = {name for name,wrong in oldEntry['Name'].items() if len(wrong) == best}
            if len(correct) == 1:
                oldEntry['Name'] = {entry['Name']}
                print('Best match (%d): %s' % (oldEntry['Participant'],entry['Name']))
            else:
                oldEntry['Name'] = {random.choice(list(correct))}
                print('Random choice (%d):\n%s' % (oldEntry['Participant'],oldEntry))
            if entry['Name'] in oldEntry['Name']:
                entry['Participant'] = oldEntry['Participant']

def preSurvey(args,name,world,states,config,t,hurricane,variables=None,partID=None):
    data = []
    agent = world.agents[name]
    entry = {'Name': name,'Timestep': t,'Hurricane': hurricane['Hurricane']}
    if partID is not None:
        entry['EntityIdx'] = 'ActorPre %d' % (partID)
    variables.update(accessibility.boilerDict)
    for var,value in accessibility.getCurrentDemographics(args,name,world,states,config,t).items():
        record = dict(entry)
        record['VariableName'] = var
        record['Value'] = value
        data.append(record)
    var = 'ActorPre At Shelter'
    if var not in variables:
        variables[var] = {'Name': var,'Values':'yes,no','DataType': 'Boolean'}
    record = dict(entry)
    record['VariableName'] = var
    sheltered = accessibility.getInitialState(args,name,'location',world,states,t).first()[:7] == 'shelter'
    record['Value'] = 'yes' if sheltered else 'no'
    data.append(record)
    var = 'ActorPre Evacuated'
    if var not in variables:
        variables[var] = {'Name': var,'Values':'yes,no','DataType': 'Boolean'}
    record = dict(entry)
    record['VariableName'] = var
    evacuated = accessibility.getInitialState(args,name,'location',world,states,t).first() == 'evacuated'
    record['Value'] = 'yes' if evacuated else 'no'
    data.append(record)
    var = 'ActorPre Category'
    if var not in variables:
        variables[var] = {'Name': var,'Values':'[1-5]','DataType': 'Integer'}
    record = dict(entry)
    record['VariableName'] = var
    record['Value'] = int(round(accessibility.getInitialState(args,'Nature','category',world,states,t,name).expectation()))
    data.append(record)
    model,belief = copy.deepcopy(next(iter(states[t-1]['Nature'][name].items())))
    pEvac = []
    pShelter = []
    risks = []
    landfall = None
    while world.getState('Nature','phase',belief).first() != 'none':
        if name in world.next(belief):
            # What am I considering?
            V = {action: agent.value(belief,action,model,updateBeliefs=False)['__EV__'] for action in agent.getActions(belief)}
            dist = Distribution(V,agent.getAttribute('rationality',model))
            pShelter.append(0.)
            for action,prob in dist.items():
                if action['verb'] == 'evacuate':
                    pEvac.append(prob)
                elif action['verb'] == 'moveTo' and action['object'][:7] == 'shelter':
                    pShelter[-1] = max(prob,pShelter[-1])
        world.step(state=belief,select='max',keySubset=belief.keys())
        risks.append(float(world.getState(name,'risk',belief)))
    var = 'ActorPre Anticipated Shelter'
    if var not in variables:
        variables[var] = {'Name': var,'Values':'[1-7]','DataType': 'Integer','Notes': 'N/A if already at shelter'}
    record = dict(entry)
    record['VariableName'] = var
    if sheltered:
        record['Value'] = 'N/A'
    else:
        record['Value'] = accessibility.toLikert(max(pShelter),7)
    data.append(record)
    var = 'ActorPre Anticipated Evacuation'
    if var not in variables:
        variables[var] = {'Name': var,'Values':'[1-7]','DataType': 'Integer','Notes': 'N/A if already evacuated'}
    record = dict(entry)
    record['VariableName'] = var
    if evacuated:
        record['Value'] = 'N/A'
    else:
        record['Value'] = accessibility.toLikert(max(pEvac),7)
    data.append(record)
    var = 'ActorPre Risk'
    if var not in variables:
        variables[var] = {'Name': var,'Values':'[1-7]','DataType': 'Integer'}
    record = dict(entry)
    record['VariableName'] = var
    record['Value'] = accessibility.toLikert(max(risks),7)
    data.append(record)
    return data

def postSurvey(args,name,world,states,config,t,hurricane,variables=None,partID=None):
    data = []
    agent = world.agents[name]
    entry = {'Name': name,'Timestep': t,'Hurricane': hurricane['Hurricane']}
    if partID is not None:
        entry['EntityIdx'] = 'ActorPost %d' % (partID)
    variables.update(accessibility.boilerDict)
    for var,value in accessibility.getCurrentDemographics(args,name,world,states,config,t).items():
        record = dict(entry)
        record['VariableName'] = var
        record['Value'] = value
        data.append(record)
    actions = accessibility.getAction(args,name,world,states,(hurricane['Start'],hurricane['End']+1))
    var = 'ActorPost At Shelter'
    if var not in variables:
        variables[var] = {'Name': var,'Values':'yes,no','DataType': 'Boolean'}
    locations = {dist.first() for dist in accessibility.getInitialState(args,name,'location',world,states,(hurricane['Start'],hurricane['End']+1))}
    record = dict(entry)
    record['VariableName'] = var
    sheltered = len({loc for loc in locations if loc[:7] == 'shelter'}) > 0
    record['Value'] = 'yes' if sheltered else 'no'
    data.append(record)
    var = 'ActorPost Evacuated'
    if variables is not None:
        variables[var] = {'Name': var,'Values':'yes,no','DataType': 'Boolean'}
    evacuated = 'evacuated' in locations
    record = dict(entry)
    record['VariableName'] = var
    record['Value'] = 'yes' if evacuated else 'no'
    data.append(record)
    var = 'ActorPost Injured'
    if var not in variables:
        variables[var] = {'Name': var,'Values':'yes,no','DataType': 'Boolean'}
    health = [dist.first() for dist in accessibility.getInitialState(args,name,'health',world,states,(hurricane['Start'],hurricane['End']+1))]
    record = dict(entry)
    record['VariableName'] = var
    record['Value'] = 'yes' if min(health) < 0.2 else 'no'
    data.append(record)
    var = 'ActorPost Risk'
    if var not in variables:
        variables[var] = {'Name': var,'Values':'[1-7]','DataType': 'Integer'}
    risk = [dist.expectation() for dist in accessibility.getInitialState(args,name,'risk',world,states,(hurricane['Start'],hurricane['End']+1),name)]
    record = dict(entry)
    record['VariableName'] = var
    record['Value'] = accessibility.toLikert(max(risk),7)
    data.append(record)
    var = 'ActorPost Dissatisfaction'
    if var not in variables:
        variables[var] = {'Name': var,'Values':'[1-7]','DataType': 'Integer'}
    record = dict(entry)
    record['VariableName'] = var
    record['Value'] = accessibility.toLikert(accessibility.getInitialState(args,name,'grievance',world,states,t).first(),7)
    data.append(record)
    pShelter = []
    pEvac = []
    pHome = []
    for day in range(hurricane['Start'],hurricane['End']+1):
        model,belief = copy.deepcopy(next(iter(states[day-1]['Nature'][name].items())))
        pEvac.append(0.)
        pShelter.append(0.)
        pHome.append(0.)
        V = {action: agent.value(belief,action,model,updateBeliefs=False)['__EV__'] for action in agent.getActions(belief)}
        #//GT: Verify that behavior in log is the optimal value
        assert V[actions[day-hurricane['Start']]] == max(V.values())
        dist = Distribution(V,agent.getAttribute('rationality',model))
        for action,prob in dist.items():
            if action != actions[day-hurricane['Start']]:
                if action['verb'] == 'evacuate':
                    pEvac.append(prob)
                elif action['verb'] == 'moveTo' and action['object'][:7] == 'shelter':
                    pShelter[-1] = max(prob,pShelter[-1])
                elif action['verb'] in {'decreaseRisk','takeResources'}:
                    # Must be at home
                    pHome[-1] += prob
                elif action['verb'] == 'moveTo' and action['object'] == agent.demographics['home']:
                    # Must be away from home
                    pHome[-1] += prob
                elif action['verb'] == 'stayInLocation' and world.getState(name,'location',belief).first() == agent.demographics['home']:
                    pHome[-1] += prob
    var = 'ActorPost Shelter Possibility'
    if var not in variables:
        variables[var] = {'Name': var,'Values':'[1-7]','DataType': 'Integer','Notes': 'N/A if already at shelter'}
    record = dict(entry)
    record['VariableName'] = var
    if sheltered == 'yes':
        record['Value'] = 'N/A'
    else:
        record['Value'] = accessibility.toLikert(max(pShelter),7)
    data.append(record)
    var = 'ActorPost Evacuation Possibility'
    if var not in variables:
        variables[var] = {'Name': var,'Values':'[1-7]','DataType': 'Integer','Notes': 'N/A if already evacuated'}
    record = dict(entry)
    record['VariableName'] = var
    if evacuated:
        record['Value'] = 'N/A'
    else:
        record['Value'] = accessibility.toLikert(max(pEvac),7)
    data.append(record)
    var = 'ActorPost Stay at Home Possibility'
    if var not in variables:
        variables[var] = {'Name': var,'Values':'[1-7]','DataType': 'Integer','Notes': 'N/A if stayed home'}
    record = dict(entry)
    record['VariableName'] = var
    if not sheltered and not evacuated:
        record['Value'] = 'N/A'
    else:
        record['Value'] = accessibility.toLikert(max(pHome),7)
    data.append(record)
    return data

def doCensus(world,variables):
    data = []
    actors = {name for name in world.agents if name[:5] == 'Actor'}
    regions = {name: {actor for actor in actors if world.agents[actor].demographics['home'] == name}
        for name in world.agents if name[:6] == 'Region'}
    census = {'Population': None,
              'Gender': 'gender',
              'Ethnicity': 'ethnicGroup',
              'Religion': 'religion',
              'Age': 'age',
              'Employment': 'employed',
    }
    ages = [world.agents[actor].demographics['age'] for actor in actors]
    limits = [18]+[i for i in range(25,max(ages),5)]
    labels = ['<%d' % (limits[0])]
    labels += ['%d-%d' % (limits[i],limits[i+1]-1) for i in range(len(limits)-1)]
    labels.append('>%d' % (limits[-1]-1))
    for field,feature in census.items():
        if field == 'Population':
            total = 0
        else:
            total = {}
        # Census
        for name,residents in regions.items():
            if field == 'Population':
                if not field in variables:
                    variables[field] = {'Name': field,'Values':'[0+]','DataType': 'Integer'}
                data.append({'Timestep': 1, 'VariableName': field, 'EntityIdx': name,'Value': len(residents) + \
                    sum([world.agents[actor].demographics['kids'] for actor in residents])})
                total += data[-1]['Value']
            elif field == 'Age':
                histogram = [0 for limit in limits]
                histogram.append(0)
                for actor in residents:
                    agent = world.agents[actor]
                    histogram[0] += agent.demographics['kids']
                    for i in range(len(limits)):
                        if agent.demographics['age'] < limits[i]:
                            histogram[i] += 1
                            break
                    else:
                        histogram[-1] += 1
                for i in range(len(histogram)):
                    var = '%s %s' % (field,labels[i])
                    if not var in variables:
                        variables[var] = {'Name': var,'Values':'[0+]','DataType': 'Integer'}
                    record = {'Timestep': 1,'VariableName': var,'EntityIdx': name,'Value': histogram[i]}
                    data.append(record)
                    total[labels[i]] = total.get(labels[i],0)+record['Value']
            else:
                histogram = {}
                for actor in residents:
                    agent = world.agents[actor]
                    try:
                        value = agent.demographics[feature]
                    except KeyError:
                        value = agent.getState(feature).first()
                    histogram[value] = histogram.get(value,0) + 1
                for value,count in histogram.items():
                    total[value] = total.get(value,0) + count
                    var = '%s %s' % (field,value)
                    if not var in variables:
                        variables[var] = {'Name': var,'Values':'[0+]','DataType': 'Integer'}
                    record = {'Timestep': 1,'VariableName': var,'EntityIdx': name, 'Value': count}
                    data.append(record)
        if field == 'Population':
            record = {'Timestep': 1,'VariableName': field,'Value': total}
            data.append(record)
        else:
            for value,count in sorted(total.items()):
                record = {'Timestep': 1,'VariableName': '%s %s' % (field,value),'Value': count}
                data.append(record)
    return data

if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('instances',nargs='+',type=int,help='Number of instance(s) to process')
    parser.add_argument('-r','--run',default=0,type=int,help='Number of run to process')
    parser.add_argument('-d','--debug',default='WARNING',help='Level of logging detail')
    parser.add_argument('--skiptables',action='store_true',help='Do not generate event tables')
    parser.add_argument('--skippre',action='store_true',help='Do not generate pre-hurricane survey')
    parser.add_argument('--skippost',action='store_true',help='Do not generate post-hurricane survey')
    parser.add_argument('--usepre',help='Use existing pre-hurricane survey file for participants')
    parser.add_argument('--usepost',help='Use existing post-hurricane survey file for participants')
    args = vars(parser.parse_args())
    # Extract logging level from command-line argument
    level = getattr(logging, args['debug'].upper(), None)
    if not isinstance(level, int):
        raise ValueError('Invalid debug level: %s' % args['debug'])
    logging.basicConfig(level=level)
    variables = {}

    for args['instance'] in args['instances']:
        print(args['instance'],args['run'])
        config = accessibility.getConfig(args['instance'])
        dirName = accessibility.getDirectory(args)
        l = logging.getLogger()
        for h in l.handlers:
            l.removeHandler(h)
        l.addHandler(logging.FileHandler(os.path.join(dirName,'psychsim.log'),'a'))
        random.seed(args['instance']*100+args['run'])
        order = ['Actor','System','Nature']
        ER = accessibility.readLog(args)
        # Load in initial simulation
        with open(os.path.join(dirName,'scenario0.pkl'),'rb') as f:
            world = pickle.load(f)
        actors = sorted([name for name in world.agents if name[:5] == 'Actor'])
        living = actors
        regions = sorted([name for name in world.agents if name[:6] == 'Region'])
        shelters = [name for name in regions if stateKey(name,'shelterRisk') in world.variables]
        shelterObjs = {'shelter%s' % (name[-2:]) for name in shelters}
        states = {0: {'Nature': {name: world.agents[name].getBelief() for name in actors}}}
        states[0]['Nature']['__state__'] = world.state
        # Compute length of simulation run
        files = [int(name[5:-10]) for name in os.listdir(dirName) if name[:5] == 'state' and name[-10:] == 'Nature.pkl']
        args['span'] = max(files)
        tables = {label: [] for label in fields}
        if not args['skiptables']:
            tables['RunData'] += doCensus(world,variables)
            # Casualty stats
            tables['RunData'] += doPopulation(world,world.state,actors,1,variables,'Actor[0001-%04d]' % (len(actors)))
            for region in regions:
                tables['RunData'] += doPopulation(world,world.state,{name for name in actors if world.agents[name].demographics['home'] == region},
                    1,variables,region,'Regional ')
            t = 1
            states[t] = {}
            turn = 0
            hurricane = 0
            phase = 'none'
            # Replay logged states and belief states
            while True:
                fname = os.path.join(dirName,'state%d%s.pkl' % (t,order[turn]))
                if not os.path.exists(fname):
                    # Presumably we have gone past the end of the simulation
                    break
                print(t,order[turn])
                with open(fname,'rb') as f:
                    s = pickle.load(f)
                states[t][order[turn]] = s
                if order[turn] == 'Nature':
                    tables['RunData'] += doPopulation(world,s['__state__'],actors,t+1,variables,entity='Actor[0001-%04d]' % (len(actors)))
                    for region in regions:
                        tables['RunData'] += doPopulation(world,s['__state__'],{name for name in actors if world.agents[name].demographics['home'] == region},
                            t+1,variables,region,'Regional ')
                    if phase != world.getState('Nature','phase',s['__state__']).first():
                        phase = world.getState('Nature','phase',s['__state__']).first()
                        if phase == 'approaching':
                            # New hurricane
                            hurricane += 1
#                            if hurricane > 6:
#                                break
                    if phase != 'none':
                        region = world.getState('Nature','location',s['__state__']).first()
                        var = 'Hurricane'
                        if var not in variables:
                            variables[var] = {'Name': var,'Values':'[1+]','DataType': 'Integer'}
                        tables['InstanceVariable'].append({'Timestep': t+1,'Name': var,'Value': hurricane})
                        var = 'Category'
                        if var not in variables:
                            variables[var] = {'Name': var,'Values':'[0-5]','DataType': 'Integer'}
                        tables['InstanceVariable'].append({'Timestep': t+1,'Name': var,'Value': world.getState('Nature','category',s['__state__']).first()})
                        var = 'Location'
                        if var not in variables:
                            variables[var] = {'Name': var,'Values':'Region[01-16],leaving','DataType': 'String'}
                        tables['InstanceVariable'].append({'Timestep': t+1,'Name': var,'Value': 'leaving' if region == 'none' else region})
                        var = 'Landed'
                        if var not in variables:
                            variables[var] = {'Name': var,'Values':'yes,no','DataType': 'Boolean'}
                        tables['InstanceVariable'].append({'Timestep': t+1,'Name': var,'Value': 'yes' if phase == 'active' else 'no'})
                        tables['Hurricane'].append({'Timestep': t+1,'Name': hurricane,
                            'Category': world.getState('Nature','category',s['__state__']).first(), 'Location': 'leaving' if region == 'none' else region,
                            'Landed': 'yes' if phase == 'active' else 'no'})
                living = [name for name in living if world.getState(name,'alive',s['__state__']).first()]
                turn += 1
                if turn == len(order):
                    turn = 0
                    t += 1
                    states[t] = {}
            # Write down hurricane data for easier recall when doing surveys
            if tables['Hurricane'][-1]['Landed'] == 'no':
                del tables['Hurricane'][-1]
            accessibility.writeOutput(args,tables['Hurricane'],fields['Hurricane'],'HurricaneTable.tsv')
        # Actor surveys
        hurricanes = accessibility.readHurricanes(args['instance'],args['run'])
        if not args['skippre']:
            if args['usepre']:
                oldSurvey = accessibility.findParticipants(args['usepre'],args,world,states,config)
            preCount = int(round(len(actors)*config.getfloat('Data','presample',fallback=0.1)))
            preSurveyed = set()
            samples = []
            for hurricane in hurricanes:
                # Pre-hurricane survey
                if args['usepre']:
                    sample = set()
                    participants = {}
                    for entry in [entry for entry in oldSurvey if entry['Hurricane'] == hurricane['Hurricane']]:
                        participants[entry['Participant']] = {}
                        entry['Name'] = {name: None for name in entry['Name']}
                        for name in entry['Name']:
                            sample.add((name,entry['Timestep']))
                else:
                    pool = {name for name in actors if accessibility.getInitialState(args,name,'alive',world,states,hurricane['Landfall']).first()}
                    if len(pool-preSurveyed) <= preCount:
                        # Going to have to ask some people again
                        sample = pool - preSurveyed
                        if len(sample) < preCount:
                            # Still need some more people
                            sample |= set(random.sample(pool-sample,preCount-len(sample)))
                        preSurveyed = set()
                    else:
                        # Can afford to be selective
                        sample = random.sample(pool-preSurveyed,preCount)
                    preSurveyed |= set(sample)
                    sample = list(sample)
                # Conduct survey
                entries = []
                for partID in range(len(sample)):
                    name = sample[partID]
                    logging.info('Pre-survey %d: Participant %d: %s' % (hurricane['Hurricane'],partID+1,name))
                    print('Pre',hurricane['Hurricane'],name)
                    if args['usepre']:
                        name,t = name
                    else:
                        t = random.randint(hurricane['Start'],hurricane['Landfall']-1)
                    entries += preSurvey(args,name,world,states,config,t,hurricane,variables,partID+1)
                entries.sort(key=lambda e: e['Timestep'])
                tables['RunData'] += entries
                samples.append({partID+1: sample[partID] for partID in range(len(samples))})
        if not args['skippost']:
            if args['usepost']:
                oldSurvey = accessibility.findParticipants(args['usepost'],args,world,states,config)
            postCount = int(round(len(actors)*config.getfloat('Data','postsample',fallback=0.1))) 
            postSurveyed = set()
            samples = []
            for hurricane in hurricanes:
                # Post-hurricane survey
                if args['usepost']:
                    sample = set()
                    participants = {}
                    for entry in [entry for entry in oldSurvey if entry['Hurricane'] == hurricane['Hurricane']]:
                        participants[entry['Participant']] = {}
                        entry['Name'] = {name: None for name in entry['Name']}
                        for name in entry['Name']:
                            sample.add((name,entry['Timestep']))
                else:
                    if hurricane['Hurricane'] < len(hurricanes):
                        # Pool people who are alive when the next hurricane starts
                        pool = {name for name in actors 
                            if accessibility.getInitialState(args,name,'alive',world,states,hurricanes[hurricane['Hurricane']]['Start']).first()}
                        end = hurricanes[hurricane['Hurricane']]['Start']
                    else:
                        # Pool people who are alive at the end of the simulation
                        pool = {name for name in actors if accessibility.getInitialState(args,name,'alive',world,states,args['span']).first()}
                        end = args['span']
                    if len(pool-postSurveyed) <= postCount:
                        # Going to have to ask some people again
                        sample = pool - postSurveyed
                        if len(sample) < postCount:
                            # Still need some more people
                            sample |= set(random.sample(pool-sample,postCount-len(sample)))
                        postSurveyed = set()
                    else:
                        # Can afford to be selective
                        sample = random.sample(pool-postSurveyed,postCount)
                    postSurveyed |= set(sample)
                    sample = list(sample)
                # Conduct survey
                entries = []
                for partID in range(len(sample)):
                    name = sample[partID]
                    logging.info('Post-survey %d: Participant %d: %s' % (hurricane['Hurricane'],partID+1,name))
                    print('Post',hurricane['Hurricane'],name)
                    if args['usepost']:
                        name,t = name
                    else:
                        t = random.randint(hurricane['End'],end-1)
                    agent = world.agents[name]
                    entries += postSurvey(args,name,world,states,config,t,hurricane,variables,partID+1)
                entries.sort(key=lambda e: e['Timestep'])
                tables['RunData'] += entries
                samples.append({partID+1: sample[partID] for partID in range(len(samples))})
                if hurricane == hurricanes[-1]:
                    for actor in pool:
                        print(name,accessibility.getActions(args,actor,world,states,config,(1,args['span']-1))) 
        for label,data in tables.items():
            accessibility.writeOutput(args,data,fields[label],'%sTable_temp.tsv' % (label))
    accessibility.writeVarDef(os.path.join(os.path.dirname(__file__),'..'),list(variables.values()))
