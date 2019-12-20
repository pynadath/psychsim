from argparse import ArgumentParser
import logging
import os.path
import pickle
import random
import sys

from psychsim.pwl import *
from psychsim.domains.groundtruth import accessibility
from psychsim.domains.groundtruth.simulation import survey

def runHurricane(args,world,oldStates,config,sample,hurricanes,day1,variables,output,team,reqNum,condition):
    logging.info('Condition %d' % (condition))
    prefix = '%s %d Pt1 Condition %d' % (team,reqNum,condition)
    history = accessibility.holoCane(world,config,set(sample),1,True,{'System': None},'hurricanes',hurricanes[-1],True)
    states = {t-1: {'Nature': history[(t-day1-1)*3]} for t in range(hurricanes[-1]['Start'],hurricanes[-1]['End']+1)}
    aid = [act['object'] for act in accessibility.getAction(args,'System',world,states,(hurricanes[-1]['Start'],hurricanes[-1]['End']))]
    if not cmd['debug']:
        for partID in range(len(sample)):
            name = sample[partID]
            agent = world.agents[name]
            root = {'Timestep': day1,'EntityIdx': '%s %d Participant %d' % (team,reqNum,partID+1)}

            # Presurvey
            t = random.randint(hurricanes[-1]['Start'],hurricanes[-1]['Landfall']-1)
            root['Timestep'] = t

            # Q1
            var = '%s Evacuation Best' % (prefix)
            if var not in variables:
                variables[var] = {'Name': var,'Values':'[1-7]','DataType': 'Integer'}
            record = dict(root)
            record['VariableName'] = var
            total = 0
            evac = 0
            for hurricane in hurricanes[:-1]:
                locations = [dist.first() for dist in accessibility.getInitialState(args,name,'location',world,oldStates,
                    (hurricane['Start'],hurricane['End']+1))]
                evac += locations.count('evacuated')
                total += hurricane['End']-hurricane['Start']-1
            record['Value'] = accessibility.toLikert(evac/total,7)
            output[3].append(record)

            belief = states[t-1]['Nature'][name]
            if isinstance(belief,dict):
                model,belief = copy.deepcopy(next(iter(belief.items())))
            else:
                belief = copy.deepcopy(belief)
                model = world.getFeature(modelKey(name),states[t-1]['Nature']['__state__']).first()
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

            # Q2
            var = '%s Risk' % (prefix)
            if var not in variables:
                variables[var] = {'Name': var,'Values':'[1-7]','DataType': 'Integer'}
            record = dict(root)
            record['VariableName'] = var
            record['Value'] = accessibility.toLikert(max(risks),7)
            output[3].append(record)

            # Q3
            var = '%s Shelter Possibility' % (prefix)
            if var not in variables:
                variables[var] = {'Name': var,'Values':'[1-7]','DataType': 'Integer'}
            record = dict(root)
            record['VariableName'] = var
            # If never have any sheltering opportunities, must already be sheltered
            record['Value'] = accessibility.toLikert(max(pShelter),7) if pShelter else 7
            output[3].append(record)

            # Q4
            var = '%s Evacuation Possibility' % (prefix)
            if var not in variables:
                variables[var] = {'Name': var,'Values':'[1-7]','DataType': 'Integer','Notes': 'N/A if already evacuated'}
            record = dict(root)
            record['VariableName'] = var
            # If never have any evacuation opportunities, must already be evacuated
            record['Value'] = accessibility.toLikert(max(pEvac),7) if pEvac else 7
            output[3].append(record)

            # Q5
            var = '%s Stay at Home Possibility' % (prefix)
            if var not in variables:
                variables[var] = {'Name': var,'Values':'[1-7]','DataType': 'Integer'}
            record = dict(root)
            record['VariableName'] = var
            # If one of is empty, then we've already left home
            record['Value'] = accessibility.toLikert((1.-max(pShelter))*(1.-max(pEvac)),7) if pShelter and pEvac else 1
            output[3].append(record)

            # Q6
            health = accessibility.getInitialState(args,name,'health',world,states,t).expectation()
            var = '%s Injuries' % (prefix)
            if var not in variables:
                variables[var] = {'Name': var,'Values':'none,self,dependents,selfplusdependents','DataType': 'String'}
            record = dict(root)
            record['VariableName'] = var
            record['Value'] = 'self' if health < 0.2 else 'none'
            if stateKey(name,'childrenHealth') in world.variables:
                health = accessibility.getInitialState(args,name,'childrenHealth',world,states,t).expectation()
                if health < 0.2:
                    if record['Value'] == 'none':
                        record['Value'] = 'dependents'
                    else:
                        record['Value'] += 'plusdependents'
            output[3].append(record)

            # Q7
            locations = [dist.first() for dist in accessibility.getInitialState(args,name,'location',world,oldStates,
                (hurricanes[-2]['Start'],hurricanes[-2]['End']+1))]
            var = '%s Days at Shelter' % (prefix)
            if var not in variables:
                variables[var] = {'Name': var,'Values':'[0+]','DataType': 'Integer'}
            record = dict(root)
            record['VariableName'] = var
            sheltered = len([loc for loc in locations if loc[:7] == 'shelter'])
            record['Value'] = sheltered
            output[3].append(record)

            # Q8
            var = '%s Days Evacuated' % (prefix)
            if var not in variables:
                variables[var] = {'Name': var,'Values':'[0+]','DataType': 'Integer'}
            record = dict(root)
            record['VariableName'] = var
            evacuated = locations.count('evacuated')
            record['Value'] = evacuated
            output[3].append(record)
            
            # Q9
            var = '%s Wealth' % (prefix)
            if var not in variables:
                variables[var] = {'Name': var,'Values':'[1-7]','DataType': 'Integer'}
            record = dict(root)
            record['VariableName'] = var
            record['Value'] = accessibility.toLikert(accessibility.getInitialState(args,name,'resources',world,states,t).expectation(),7)
            output[3].append(record)

            # Q10
            var = '%s Property Damage' % (prefix)
            if var not in variables:
                variables[var] = {'Name': var,'Values':'[1-7]','DataType': 'Integer'}
            risk = [dist.expectation() for dist in accessibility.getInitialState(args,agent.demographics['home'],'risk',world,oldStates,
                (hurricanes[-2]['Start'],hurricanes[-2]['End']+1),name)]
            record = dict(root)
            record['VariableName'] = var
            record['Value'] = accessibility.toLikert(max(risk),7)
            output[3].append(record)

            # Postsurvey
            t = hurricanes[-1]['End']
            root['Timestep'] = t

            # Q1
            locations = [dist.first() for dist in accessibility.getInitialState(args,name,'location',world,states,
                (hurricanes[-1]['Start'],hurricanes[-1]['End']+1))]
            var = '%s Days at Home' % (prefix)
            if var not in variables:
                variables[var] = {'Name': var,'Values':'[1-7]','DataType': 'Integer'}
            record = dict(root)
            record['VariableName'] = var
            record['Value'] = locations.count(agent.demographics['home'])
            output[1].append(record)

            # Q2
            var = '%s Days at Shelter' % (prefix)
            if var not in variables:
                variables[var] = {'Name': var,'Values':'[0+]','DataType': 'Integer'}
            record = dict(root)
            record['VariableName'] = var
            sheltered = len([loc for loc in locations if loc[:7] == 'shelter'])
            record['Value'] = sheltered
            output[1].append(record)

            # Q3
            var = '%s Days Evacuated' % (prefix)
            if var not in variables:
                variables[var] = {'Name': var,'Values':'[0+]','DataType': 'Integer'}
            record = dict(root)
            record['VariableName'] = var
            evacuated = locations.count('evacuated')
            record['Value'] = evacuated
            output[1].append(record)

            # Q4
            actions = accessibility.getAction(args,name,world,states,(hurricanes[-1]['Start'],hurricanes[-1]['End']+1))
            pShelter = []
            pEvac = []
            pHome = []
            for day in range(hurricanes[-1]['Start'],hurricanes[-1]['End']+1):
                belief = states[day-1]['Nature'][name]
                if isinstance(belief,dict):
                    model,belief = copy.deepcopy(next(iter(belief.items())))
                else:
                    belief = copy.deepcopy(belief)
                    model = world.getFeature(modelKey(name),states[day-1]['Nature']['__state__']).first()
                pEvac.append(0.)
                pShelter.append(0.)
                pHome.append(0.)
                V = {action: agent.value(belief,action,model,updateBeliefs=False)['__EV__'] for action in agent.getActions(belief)}
                dist = Distribution(V,agent.getAttribute('rationality',model))
                for action,prob in dist.items():
                    if action != actions[day-hurricanes[-1]['Start']]:
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
            var = '%s Shelter Possibility' % (prefix)
            if var not in variables:
                variables[var] = {'Name': var,'Values':'[1-7]','DataType': 'Integer','Notes': 'N/A if already at shelter'}
            record = dict(root)
            record['VariableName'] = var
            if sheltered:
                record['Value'] = 'N/A'
            else:
                record['Value'] = accessibility.toLikert(max(pShelter),7)
            output[1].append(record)

            # Q5
            var = '%s Evacuation Possibility' % (prefix)
            if var not in variables:
                variables[var] = {'Name': var,'Values':'[1-7]','DataType': 'Integer','Notes': 'N/A if already evacuated'}
            record = dict(root)
            record['VariableName'] = var
            if evacuated:
                record['Value'] = 'N/A'
            else:
                record['Value'] = accessibility.toLikert(max(pEvac),7)
            output[1].append(record)

            # Q6
            health = [dist.expectation() for dist in accessibility.getInitialState(args,name,'health',world,states,
                (hurricanes[-1]['Start'],hurricanes[-1]['End']+1))]
            var = '%s Injuries' % (prefix)
            if var not in variables:
                variables[var] = {'Name': var,'Values':'none,self,dependents,selfplusdependents','DataType': 'String'}
            record = dict(root)
            record['VariableName'] = var
            record['Value'] = 'self' if min(health) < 0.2 else 'none'
            if stateKey(name,'childrenHealth') in world.variables:
                health = [dist.first() for dist in accessibility.getInitialState(args,name,'childrenHealth',world,states,
                    (hurricanes[-1]['Start'],hurricanes[-1]['End']+1))]
                if min(health) < 0.2:
                    if record['Value'] == 'none':
                        record['Value'] = 'dependents'
                    else:
                        record['Value'] += 'plusdependents'
            output[1].append(record)

            # Q7
            var = '%s Risk' % (prefix)
            if var not in variables:
                variables[var] = {'Name': var,'Values':'[1-7]','DataType': 'Integer'}
            risk = [dist.expectation() for dist in accessibility.getInitialState(args,name,'risk',world,states,
                (hurricanes[-1]['Start'],hurricanes[-1]['End']+1),name)]
            record = dict(root)
            record['VariableName'] = var
            record['Value'] = accessibility.toLikert(max(risk),7)
            output[1].append(record)
            
            # Q8
            var = '%s Wealth' % (prefix)
            if var not in variables:
                variables[var] = {'Name': var,'Values':'[1-7]','DataType': 'Integer'}
            record = dict(root)
            record['VariableName'] = var
            record['Value'] = accessibility.toLikert(accessibility.getInitialState(args,name,'resources',world,states,t).expectation(),7)
            output[1].append(record)

            # Q9
            var = '%s Property Damage' % (prefix)
            if var not in variables:
                variables[var] = {'Name': var,'Values':'[1-7]','DataType': 'Integer'}
            risk = [dist.expectation() for dist in accessibility.getInitialState(args,agent.demographics['home'],'risk',world,states,
                (hurricanes[-1]['Start'],hurricanes[-1]['End']+1),name)]
            record = dict(root)
            record['VariableName'] = var
            record['Value'] = accessibility.toLikert(max(risk),7)
            output[1].append(record)

            # Q10
            var = '%s Government Assistance' % (prefix)
            if var not in variables:
                variables[var] = {'Name': var,'Values':'[1-7]','DataType': 'Integer'}
            record = dict(root)
            record['VariableName'] = var
            record['Value'] = accessibility.toLikert(aid.count(agent.demographics['home'])/len(aid),7)
            output[1].append(record)

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO,filename='%s%s' % (os.path.splitext(__file__)[0],'.log'))
    parser = ArgumentParser()
    parser.add_argument('-d','--debug',action='store_true',help='Run without writing any files')
    parser.add_argument('-1',action='store_true',help='Run Condition 1 only')
    reqNum = int(os.path.splitext(os.path.basename(__file__))[0].split('-')[2])
    team = os.path.splitext(os.path.basename(__file__))[0].split('-')[0]
    random.seed(reqNum)
    cmd = vars(parser.parse_args())
    variables = dict(accessibility.boilerDict)
    for instance,args in accessibility.instanceArgs('Phase2','Prescribe'):
        print('Instance %d (%d,%d)' % (instance,args['instance'],args['run']))
        logging.info('Instance %d (%d,%d)' % (instance,args['instance'],args['run']))
        challenge = accessibility.instanceChallenge(instance)[1]
        config = accessibility.getConfig(args['instance'])
        states = {}
        hurricanes = [h for h in accessibility.readHurricanes(args['instance'],args['run']) if h['End'] <= args['span']]
        # Load world
        world = accessibility.unpickle(instance)
        day1 = hurricanes[-1]['Start']-2
        accessibility.loadState(args,states,day1,'Nature',world)
        participants = accessibility.readParticipants(args['instance'],args['run'],splitHurricanes=True,duplicates=True)
        if len(participants) == 0:
            participants = accessibility.loadParticipants(args,world)
        actors = {name for name in world.agents if name[:5] == 'Actor' and world.getState(name,'alive').first()}
        sample = random.sample(actors,len(actors)//20)
        target = accessibility.getTarget(args['instance'],args['run'],world)
        if target not in sample:
            sample.append(target)

        output = {1: [], 2: [], 3: []}
        for partID in range(len(sample)):
            name = sample[partID]
            logging.info('Participant %d: %s' % (partID+1,name))
            agent = world.agents[name]
            root = {'Timestep': day1,'EntityIdx': '%s %d Participant %d' % (team,reqNum,partID+1)}
            for field,value in accessibility.getCurrentDemographics(args,name,world,states,config).items():
                record = dict(root)
                record['VariableName'] = field
                record['Value'] = value
                output[2].append(record)

            var = '%s %d Participant ID' % (team,reqNum)
            if var not in variables:
                variables[var] = {'Name': var,'Values': 'Actor','DataType': 'String','Notes': 'Map to pre/post-survey ID'}
            record = dict(root)
            record['VariableName'] = var
            if name == target:
                record['Value'] = 'TargetActor'
                output[1].append(record)
                output[2].append(record)
                output[3].append(record)
            else:
                for label,table in participants.items():
                    for entity,entry in table.items():
                        if isinstance(table[entity],dict):
                            matches = accessibility.findMatches(table[entity],world,ignoreJob=True)
                            if name in matches:
                                record['Timestep'] = table[entity]['Timestep']
                                if len(matches) > 1:
                                    value = accessibility.getInitialState(args,name,'employed',world,states,record['Timestep']).first()
                                    if entry['Fulltime Job'] != ('yes' if value else 'no'):
                                        continue
                                    value = accessibility.getInitialState(args,name,'resources',world,states,record['Timestep']).expectation()
                                    if entry['Wealth'] != accessibility.toLikert(value,7):
                                        continue
                                    for other in list(matches):
                                        value = accessibility.getInitialState(args,other,'employed',world,states,record['Timestep']).first()
                                        if entry['Fulltime Job'] != ('yes' if value else 'no'):
                                            matches.remove(other)
                                        else:
                                            value = accessibility.getInitialState(args,other,'resources',world,states,record['Timestep']).expectation()
                                            if int(entry['Wealth']) != accessibility.toLikert(value,7):
                                                matches.remove(other)
                                    print(matches)
                                    raise ValueError(entry)
                                else:
                                    entity = table[entity]['Participant']
                                break
                        elif name == table[entity]:
                            record['Timestep'] = accessibility.getSurveyTime(args,label[:3] == 'Pre',int(label.split()[1]),entity,True)
                            break
                    else:
                        continue
                    h = label.split()[-1]
                    if label[:3] == 'Pre':
                        record['Value'] = 'ActorPre %d Hurricane %s' % (entity,h)
                    else:
                        record['Value'] = 'ActorPost %d Hurricane %s' % (entity,h)
                    output[1].append(record)
                    output[2].append(record)
                    output[3].append(record)
                    logging.info('%s: %s and %s %d' % (name,root['EntityIdx'],label,entity))
                    break
                else:
                    logging.warning('%s never filled out survey' % (name))

            var = '%s %d Friends' % (team,reqNum)
            if var not in variables:
                variables[var] = {'Name': var,'Values':'[0+]','DataType': 'Integer'}
            record = dict(root)
            record['VariableName'] = var
            record['Value'] = len([friend for friend in agent.getFriends() if world.getState(friend,'alive').first()])
            output[2].append(record)
        # Condition 0
        runHurricane(args,world,states,config,sample,hurricanes,day1,variables,output,team,reqNum,0)
        # Condition 1
        world = accessibility.unpickle(instance)
        day1 = hurricanes[-1]['Start']-2
        accessibility.loadState(args,states,day1,'Nature',world)
        for name in sample:
            agent = world.agents[name]
            agent.riskAttitude = 'averse'
            action = ActionSet(Action({'subject': name,'verb': 'evacuate'}))
            del world.dynamics[action][stateKey(name,'resources')]
            del world.dynamics[stateKey(name,'resources')][action]
        world.agents['System'].setAidDynamics(sample,0.5)
        # Trigger hurricane
        runHurricane(args,world,states,config,sample,hurricanes,day1,variables,output,team,reqNum,1)
        if not cmd['debug']:
            for part in range(3):
                accessibility.writeOutput(args,output[part+1],accessibility.fields['RunData'],'RunDataTable%d.tsv' % (part+1),
                    os.path.join(os.path.dirname(__file__),'Instances','Instance%d' % (instance),'Runs','run-0'))
    if not cmd['debug']:
        accessibility.writeVarDef(os.path.dirname(__file__),list(variables.values()))
