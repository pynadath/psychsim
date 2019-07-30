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

fields = {'Population': ['Timestep','Deaths','Casualties','Evacuees','Sheltered'],
    'Regional': ['Timestep','Region','Deaths','Casualties','Sheltered'],
    'Hurricane': ['Timestep','Name','Category','Location','Landed'],
    'ActorPre': ['Participant','Timestep','Hurricane']+sorted(accessibility.demographics.keys())+['At Shelter','Evacuated','Anticipated Shelter',
        'Anticipated Evacuation','Category','Risk'],
    'ActorPost': ['Participant','Timestep','Hurricane']+sorted(accessibility.demographics.keys())+['At Shelter','Evacuated','Injured',
        'Risk','Dissatisfaction','Shelter Possibility','Evacuation Possibility','Stay at Home Possibility']
}

def doPopulation(world,state,actors,t):
    living = {name for name in actors if world.getState(name,'alive',state).first()}
    return {'Timestep': t,'Deaths': len(actors)-len(living), 
        'Casualties': len([name for name in actors if float(world.getState(name,'health',state)) < 0.2]),
        'Evacuees': len([name for name in living if world.getState(name,'location',state).first() == 'evacuated']),
        'Sheltered': len([name for name in living if world.getState(name,'location',state).first()[:7] == 'shelter'])}

if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('instances',nargs='+',type=int,help='Number of instance(s) to process')
    parser.add_argument('-r','--run',default=0,type=int,help='Number of run to process')
    parser.add_argument('-d','--debug',default='WARNING',help='Level of logging detail')
    parser.add_argument('--skiptables',action='store_true',help='Do not generate event tables')
    parser.add_argument('--skippre',action='store_true',help='Do not generate pre-hurricane survey')
    parser.add_argument('--skippost',action='store_true',help='Do not generate post-hurricane survey')
    args = vars(parser.parse_args())
    # Extract logging level from command-line argument
    level = getattr(logging, args['debug'].upper(), None)
    if not isinstance(level, int):
        raise ValueError('Invalid debug level: %s' % args['debug'])
    logging.basicConfig(level=level)

    for args['instance'] in args['instances']:
        config = accessibility.getConfig(args['instance'])
        dirName = accessibility.getDirectory(args)
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
            tables['Population'].append(doPopulation(world,world.state,actors,1))
            for region in regions:
                tables['Regional'].append(doPopulation(world,world.state,{name for name in actors if world.agents[name].demographics['home'] == region},1))
                tables['Regional'][-1]['Region'] = region
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
                    tables['Population'].append(doPopulation(world,s['__state__'],actors,t+1))
                    entries = []
                    for region in regions:
                        entries.append(doPopulation(world,s['__state__'],{name for name in actors if world.agents[name].demographics['home'] == region},t+1))
                        entries[-1]['Region'] = region
                    for field in tables['Population'][-1].keys():
                        if field == 'Timestep':
                            for entry in entries:
                                assert entry[field] == tables['Population'][-1][field]
                        else:
                            assert tables['Population'][-1][field] == sum([entry[field] for entry in entries])
                    tables['Regional'] += entries
                    if phase != world.getState('Nature','phase',s['__state__']).first():
                        phase = world.getState('Nature','phase',s['__state__']).first()
                        if phase == 'approaching':
                            # New hurricane
                            hurricane += 1
                    if phase != 'none':
                        region = world.getState('Nature','location',s['__state__']).first()
                        tables['Hurricane'].append({'Timestep': t+1,'Name': hurricane,'Category': world.getState('Nature','category',s['__state__']).first(),
                            'Location': 'leaving' if region == 'none' else region, 'Landed': 'yes' if phase == 'active' else 'no'})
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
            preCount = int(round(len(actors)*config.getfloat('Data','presample',fallback=0.1)))
            preSurveyed = set()
            for hurricane in hurricanes:
                # Pre-hurricane survey
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
                # Conduct survey
                entries = []
                for name in sample:
                    print('Pre',hurricane['Hurricane'],name)
                    agent = world.agents[name]
                    t = random.randint(hurricane['Start'],hurricane['Landfall']-1)
                    entry = {'Name': name,'Timestep': t,'Hurricane': hurricane['Hurricane']}
                    entry.update(accessibility.getCurrentDemographics(args,name,world,states,config,t))
                    entry['At Shelter'] = 'yes' if accessibility.getInitialState(args,name,'location',world,states,t).first() in shelterObjs else 'no'
                    entry['Evacuated'] = 'yes' if accessibility.getInitialState(args,name,'location',world,states,t).first() == 'evacuated' else 'no'
                    entry['Category'] = int(round(accessibility.getInitialState(args,'Nature','category',world,states,t,name).expectation()))
                    entries.append(entry)
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
                                elif action['verb'] == 'moveTo' and action['object'] in shelterObjs:
                                    pShelter[-1] = max(prob,pShelter[-1])
                        world.step(state=belief,select='max',keySubset=belief.keys())
                        risks.append(float(world.getState(name,'risk',belief)))
                    if entry['At Shelter'] == 'yes':
                        entry['Anticipated Shelter'] = 'N/A'
                    else:
                        entry['Anticipated Shelter'] = accessibility.toLikert(max(pShelter),7)
                    if entry['Evacuated'] == 'yes':
                        entry['Anticipated Evacuation'] = 'N/A'
                    else:
                        entry['Anticipated Evacuation'] = accessibility.toLikert(max(pEvac),7)
                    entry['Risk'] = accessibility.toLikert(max(risks),7)
                entries.sort(key=lambda e: e['Timestep'])
                for entry in entries:
                    tables['ActorPre'].append(entry)
                    entry['Participant'] = len(tables['ActorPre'])
                    logging.info('Pre-survey Participant %d: %s' % (entry['Participant'],entry['Name']))
        if not args['skippost']:
            postCount = int(round(len(actors)*config.getfloat('Data','postsample',fallback=0.1)))
            postSurveyed = set()
            for hurricane in hurricanes:
                # Post-hurricane survey
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
                # Conduct survey
                entries = []
                for name in sample:
                    print('Post',hurricane['Hurricane'],name)
                    agent = world.agents[name]
                    t = random.randint(hurricane['End'],end-1)
                    entry = {'Name': name,'Timestep': t,'Hurricane': hurricane['Hurricane']}
                    entry.update(accessibility.getCurrentDemographics(args,name,world,states,config,t))
                    actions = accessibility.getAction(args,name,world,states,(hurricane['Start'],hurricane['End']+1))
                    locations = {dist.first() for dist in accessibility.getInitialState(args,name,'location',world,states,(hurricane['Start'],hurricane['End']+1))}
                    entry['At Shelter'] = 'yes' if locations & shelterObjs else 'no'
                    entry['Evacuated'] = 'yes' if 'evacuated' in locations else 'no'
                    health = [dist.first() for dist in accessibility.getInitialState(args,name,'health',world,states,(hurricane['Start'],hurricane['End']+1))]
                    entry['Injured'] = 'yes' if min(health) < 0.2 else 'no'
                    risk = [dist.expectation() for dist in accessibility.getInitialState(args,name,'risk',world,states,(hurricane['Start'],hurricane['End']+1),name)]
                    entry['Risk'] = accessibility.toLikert(max(risk),7)
                    entry['Dissatisfaction'] = accessibility.toLikert(accessibility.getInitialState(args,name,'grievance',world,states,t).first(),7)
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
                    if entry['At Shelter'] == 'yes':
                        entry['Shelter Possibility'] = 'N/A'
                    else:
                        entry['Shelter Possibility'] = accessibility.toLikert(max(pShelter),7)
                    if entry['Evacuated'] == 'yes':
                        entry['Evacuation Possibility'] = 'N/A'
                    else:
                        entry['Evacuation Possibility'] = accessibility.toLikert(max(pEvac),7)
                    if entry['At Shelter'] == 'no' and entry['Evacuated'] == 'no':
                        entry['Stay at Home Possibility'] = 'N/A'
                    else:
                        entry['Stay at Home Possibility'] = accessibility.toLikert(max(pHome),7)
                    entries.append(entry)
                entries.sort(key=lambda e: e['Timestep'])
                for entry in entries:
                    tables['ActorPost'].append(entry)
                    entry['Participant'] = len(tables['ActorPost'])
                    logging.info('Post-survey Participant %d: %s' % (entry['Participant'],entry['Name']))
        for label,data in tables.items():
            if (label == 'ActorPre' and not args['skippre']) or (label == 'ActorPost' and not args['skippost']) or \
                (label != 'Hurricane' and not args['skiptables']):
                    accessibility.writeOutput(args,data,fields[label],'%sTable.tsv' % (label))
