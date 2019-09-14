from argparse import ArgumentParser
import logging
import os.path
import random

from psychsim.pwl import *
from psychsim.domains.groundtruth import accessibility
from TA2A_TA1C_0252 import aidWillingnessEtc

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO,filename='%s%s' % (os.path.splitext(__file__)[0],'.log'))
    parser = ArgumentParser()
    parser.add_argument('-d','--debug',action='store_true',help='Run without writing any files')
    cmd = vars(parser.parse_args())
    random.seed(int(os.path.basename(__file__)[10:14]))
    defined = False
    variables = accessibility.boilerPlate[:]
    for instance,args in accessibility.allArgs():
        if cmd['debug']:
            print('Instance %d (%d,%d)' % (instance,args['instance'],args['run']))
        logging.info('Instance %d (%d,%d)' % (instance,args['instance'],args['run']))
        config = accessibility.getConfig(args['instance'])
        world = accessibility.unpickle(instance)
        hurricanes = [h for h in accessibility.readHurricanes(args['instance'],args['run'],'Input' if 3 <= instance <= 14 else None)
            if h['End'] <= args['span']]
        if accessibility.instancePhase(instance) == 1:
            states = accessibility.loadRunData(args['instance'],args['run'],args['span'],subs=['Input'] if 3 <= instance <= 14 else [None])
            network = accessibility.readNetwork(args['instance'],args['run'],'Input' if 3 <= instance <= 14 else None)
        else:
            states = {}
            network = None
        actors = accessibility.getLivePopulation(args,world,states,args['span'])
        pool = {name for name,death in actors.items() if death is None}
        demos = {name: accessibility.getCurrentDemographics(args,name,world,states,config,args['span']) for name in pool}
        participants = random.sample(pool,len(pool)//20)
        output = []
        for partID in range(len(participants)):
            if not defined:
                variables.insert(0,{'Name': 'Participant','Values': '[1+]','VarType': 'fixed','DataType': 'Integer'})
            record = {'Participant': partID+1}
            output.append(record)
            name = participants[partID]
            logging.info('Participant %d: %s' % (record['Participant'],name))
            agent = world.agents[name]
            # 0.i.a-i
            record.update(demos[name])
            # 0.i.j
            record['Timestep'] = args['span']
            # 0.i.k
            aidWillingnessEtc(args,agent,record,world,states,demos,hurricanes,pool,None if defined else variables,network)
            if cmd['debug']:
                print(record)
            if not defined:
                defined = True
                startField = len(variables)
        if not cmd['debug']:
            accessibility.writeOutput(args,output,[var['Name'] for var in variables[:startField]],'%s-Participants-R1.tsv' % (os.path.splitext(os.path.basename(__file__))[0]),
                os.path.join(os.path.dirname(__file__),'Instances','Instance%d' % (instance),'Runs','run-0'))
        output = []
        defined = False
        hurricane = hurricanes[-1]
        aid = accessibility.getAction(args,'System',world,states,(hurricane['Start'],hurricane['End']+1))
        actions = {}
        regionalAid = {}
        for partID in range(len(participants)):
            name = participants[partID]
            agent = world.agents[name]
            if accessibility.instancePhase(instance) == 1:
                accessibility.backwardDemographics(agent,demos)
            neighbors = agent.getNeighbors()
            if name not in actions:
                actions[name] = accessibility.getAction(args,name,world,states,(hurricane['Start'],hurricane['End']+1))
            for other in neighbors:
                if other not in actions:
                    actions[other] = accessibility.getAction(args,other,world,states,(hurricane['Start'],hurricane['End']+1))
            for t in range(hurricane['Start'],hurricane['End']+1):
                # 1.a
                record = {'Participant': partID+1,'Timestep': t}
                output.append(record)
                # 1.b
                record['Wealth'] = accessibility.toLikert(float(accessibility.getInitialState(args,name,'resources',world,states,t,name)),7)
                # 1.c
                if not defined:
                    variables.append({'Name': 'Risk','Values':'[1-5]','DataType': 'Integer','Notes': '1.c'})
                risk = float(accessibility.getInitialState(args,name,'risk',world,states,t,name))
                record['Risk'] = accessibility.toLikert(risk)
                # 1.d
                if not defined:
                    variables.append({'Name': 'Severity','Values':'[1-5]','DataType': 'Integer','Notes': '1.d'})
                cat1 = accessibility.getInitialState(args,'Nature','category',world,states,t,name)
                if isinstance(cat1,Distribution):
                    record['Severity'] = int(round(cat1.expectation()))
                else:
                    assert isinstance(cat1,int)
                    record['Severity'] = cat1
                # 1.e
                if not defined:
                    variables.append({'Name': 'Dissatisfaction','Values':'[1-5]','DataType': 'Integer','Notes': '1.e'})
                record['Dissatisfaction'] = accessibility.toLikert(float(accessibility.getInitialState(args,name,'grievance',world,states,t)))
                # 1.f
                if not defined:
                    variables.append({'Name': 'Location','Values':'shelter,evacuated,region,home','DataType': 'String','Notes': '1.f'})
                location = accessibility.getInitialState(args,name,'location',world,states,t)
                if isinstance(location,Distribution):
                    location = location.first()
                if location[:6] == 'Region':
                    record['Location'] = 'home'
                elif location[:7] == 'shelter':
                    record['Location'] = 'shelter'
                else:
                    record['Location'] = location
                # 1.i.1
                var = 'Shelter w/Children'
                if not defined:
                    variables.append({'Name': var,'Values':'yes,no','DataType': 'Boolean','Notes': '1.i.1'})
                if record['Location'] == 'shelter':
                    if agent.demographics['kids'] > 0:
                        record[var] = 'yes'
                    else:
                        record[var] = 'NA'
                else:
                    record[var] = 'NA'
                # 1.i.2
                var = 'Shelter w/Pets'
                if not defined:
                    variables.append({'Name': var,'Values':'yes,no','DataType': 'Boolean','Notes': '1.i.2'})
                if record['Location'] == 'shelter':
                    if agent.demographics['pet'] == 'yes':
                        # If pets are allowed, then your pet is with you; otherwise, it's staying at a farm up north
                        record[var] = 'yes' if world.getState('Region%02d' % (int(location[7:])),'shelterPets').first() else 'no'
                    else:
                        record[var] = 'NA'
                else:
                    record[var] = 'NA'
                # 1.i.3
                var = 'Shelter Tell'
                if not defined:
                    variables.append({'Name': var,'Values':'yes,no','DataType': 'Boolean','Notes': '1.i.3'})
                record[var] = 'no'
                # 1.g
                var = 'Serious Injury Possibility'
                if not defined:
                    variables.append({'Name': var,'Values':'[0-6]','DataType': 'Integer','Notes': '1.g'})
                record[var] = accessibility.toLikert(risk/2)
                # 1.h
                var = 'Minor Injury Possibility'
                if not defined:
                    variables.append({'Name': var,'Values':'[0-6]','DataType': 'Integer','Notes': '1.h'})
                record[var] = accessibility.toLikert(risk)
                assert record[var] >= record['Serious Injury Possibility']
                # 1.i
                var = 'Shelter Possibility'
                if not defined:
                    variables.append({'Name': var,'Values':'[0-6]','DataType': 'Integer','Notes': '1.i'})
                if accessibility.instancePhase(instance) > 1:
                    # Compute value function
                    model,belief = copy.deepcopy(next(iter(states[t-1]['Nature'][name].items())))
                    assert name in world.next(belief)
                    V = {action: agent.value(belief,action,model,updateBeliefs=False)['__EV__'] for action in agent.getActions(belief)}
                    dist = Distribution(V,agent.getAttribute('rationality',model))
                if record['Location'] == 'shelter':
                    record[var] = 'NA'
                elif accessibility.instancePhase(instance) == 1:
                    if actions[name][t-hurricane['Start']]['verb'] == 'moveTo' and actions[name][t-hurricane['Start']]['object'][:7] == 'shelter':
                        record[var] = 6
                    else:
                        record[var] = 0
                else:
                    pShelter = 0.
                    for action,prob in dist.items():
                        if action['verb'] == 'moveTo' and action['object'][:7] == 'shelter':
                            pShelter = max(prob,pShelter)
                    record[var] = accessibility.toLikert(pShelter,7)-1
                # 1.j
                var = 'Evacuation Possibility'
                if not defined:
                    variables.append({'Name': var,'Values':'[0-6]','DataType': 'Integer','Notes': '1.j'})
                if record['Location'] == 'evacuated':
                    record[var] = 'NA'
                elif accessibility.instancePhase(instance) == 1:
                    if actions[name][t-hurricane['Start']]['verb'] == 'evacuate':
                        record[var] = 6
                    else:
                        record[var] = 0
                else:
                    pEvac = 0.
                    for action,prob in dist.items():
                        if action['verb'] == 'evacuate':
                            pEvac = max(prob,pEvac)
                    record[var] = accessibility.toLikert(pEvac,7)-1
                # 1.k
                var = 'Received Govt Aid'
                if not defined:
                    variables.append({'Name': var,'Values':'yes,no','DataType': 'Boolean','Notes': '1.i.k'})
                record[var] = 'yes' if aid[t-hurricane['Start']]['object'] == agent.demographics['home'] else 'no'
                # 1.l
                var = 'Received Acquaintance Aid'
                if not defined:
                    variables.append({'Name': var,'Values':'yes,no','DataType': 'Boolean','Notes': '1.i.l'})
                for other in neighbors:
                    for action in actions[other]:
                        if action['verb'] == 'decreaseRisk':
                            record[var] = 'yes'
                            break
                    if var in record:
                        break
                else:
                    # Wow, your neighbors suck
                    record[var] = 'no'
                try:
                    # Verify that previous residents gave the same response
                    assert record[var] == regionalAid[agent.demographics['home']]
                except KeyError:
                    # Leave my response for others to examine
                    regionalAid[agent.demographics['home']] = record[var]
                # 1.m
                var = 'Gave Aid'
                if not defined:
                    variables.append({'Name': var,'Values':'yes,no','DataType': 'Boolean','Notes': '1.i.m'})
                for action in actions[name]:
                    if action['verb'] == 'decreaseRisk':
                        record[var] = 'yes'
                        break
                else:
                    # Wow, you suck
                    record[var] = 'no'
                if record[var] == 'yes':
                    # Make sure neighbors know I helped
                    try:
                        assert regionalAid[agent.demographics['home']] == 'yes'
                    except KeyError:
                        regionalAid[agent.demographics['home']] = 'yes'
                # 1.n
                var = 'Received Salary'
                if not defined:
                    variables.append({'Name': var,'Values':'yes,no','DataType': 'Boolean','Notes': '1.i.n'})
                record[var] = 'no'
                try:
                    job = accessibility.getInitialState(args,name,'employed',world,states,t)
                except KeyError:
                    # Phase 1 unlogged job
                    if states[name][stateKey(name,'resources')][t] > states[name][stateKey(name,'resources')][t-1]:
                        record[var] = 'yes'
                    job = False
                if job:
                    if actions[name][t-hurricane['Start']]['verb'] == 'moveTo' and actions[name][t-hurricane['Start']]['object'] == agent.demographics['home']:
                        # If you go home, you can work
                        record[var] = 'yes'
                    elif record['Location'] == 'home':
                        # If you stay home, you can work
                        if actions[name][t-hurricane['Start']]['verb'] == 'stayInLocation':
                            record[var] = 'yes'
                    elif record['Location'] == 'evacuated':
                        # If you stay evacuated, you can work
                        if actions[name][t-hurricane['Start']]['verb'] == 'stayInLocation':
                            record[var] = 'yes'
                # 1.o
                var = 'Social Media Location'
                if not defined:
                    variables.append({'Name': var,'Values':'Region[01-16],leaving','DataType': 'String','Notes': '1.i.o'})
                if accessibility.instancePhase(instance) == 1:
                    assert states[name]['__beliefs__'][stateKey('Nature','location')][t] == hurricane['Actual Location'][t-hurricane['Start']] or \
                        (states[name]['__beliefs__'][stateKey('Nature','location')][t] == 'none' and hurricane['Actual Location'][t-hurricane['Start']] == 'leaving')
                record[var] = hurricane['Actual Location'][t-hurricane['Start']]
                # 1.p
                var = 'Social Media Category'
                if not defined:
                    variables.append({'Name': var,'Values':'[0-5]','DataType': 'Integer','Notes': '1.i.p'})
                if accessibility.instancePhase(instance) == 1:
                    cat1 = states[name]['__beliefs__'][stateKey('Nature','category')][t]
                    if isinstance(cat1,int):
                        record[var] = cat1
                    else:
                        cat0 = states[name]['__beliefs__'][stateKey('Nature','category')][t-1]
                        if isinstance(cat0,int):
                            if cat0 == 0:
                                record[var] = cat1.max()
                            else:
                                assert cat0 in cat1.domain(),'%d not in %s' % (cat0,cat1)
                                for el in cat1.domain():
                                    if el != cat0:
                                        record[var] = el
                                        break
                                else:
                                    raise RuntimeError
                        elif cat1.expectation() > cat0.expectation():
                            # Higher category observation
                            record[var] = max(cat1.domain())
                        else:
                            # Lower category observation
                            record[var] = min(cat1.domain())
                else:
                    record[var] = accessibility.getInitialState(args,name,'perceivedCategory',world,states,t).first()
                # 1.q
                var = 'Friend Category'
                if not defined:
                    variables.append({'Name': var,'Values':'[0-5]','DataType': 'Integer','Notes': '1.i.q'})
                friends = agent.getFriends()
                if friends:
                    total = 0.
                    for other in friends:
                        if actors[other] is None or actors[other] > t:
                            # Still alive
                            cat = accessibility.getInitialState(args,'Nature','category',world,states,t,other)
                            if isinstance(cat,Distribution):
                                cat = cat.expectation()
                            total += cat
                    record[var] = int(round(total/len(friends)))
                else:
                    record[var] = 'NA'
                # 1.r
                var = 'Wealth Change'
                if not defined:
                    variables.append({'Name': var,'Values':'[-5-5]','DataType': 'Integer','Notes': '1.i.r'})
                delta = float(accessibility.getInitialState(args,name,'resources',world,states,t))-float(accessibility.getInitialState(args,name,'resources',world,states,t-1))
                if delta < 0.:
                    record[var] = -accessibility.toLikert(abs(delta),7)
                elif delta > 0.:
                    record[var] = accessibility.toLikert(delta,7)
                else:
                    record[var] = 0
                assert abs(record[var]) <= 5
                if t > hurricane['Start']:
                    # Verify delta consistency
                    if record[var] < 0:
                        assert record['Wealth'] <= output[-2]['Wealth']
                    elif record[var] > 0:
                        assert record['Wealth'] >= output[-2]['Wealth']
                    else:
                        assert record['Wealth'] == output[-2]['Wealth']
                # 1.s
                var = 'Dissatisfaction Change'
                if not defined:
                    variables.append({'Name': var,'Values':'[-5-5]','DataType': 'Integer','Notes': '1.i.s'})
                delta = float(accessibility.getInitialState(args,name,'grievance',world,states,t))-float(accessibility.getInitialState(args,name,'grievance',world,states,t-1))
                if delta < 0.:
                    record[var] = -accessibility.toLikert(abs(delta),7)
                elif delta > 0.:
                    record[var] = accessibility.toLikert(delta,7)
                else:
                    record[var] = 0
                assert abs(record[var]) <= 5
                if t > hurricane['Start']:
                    # Verify delta consistency
                    if record[var] < 0:
                        assert record['Dissatisfaction'] <= output[-2]['Dissatisfaction']
                    elif record[var] > 0:
                        assert record['Dissatisfaction'] >= output[-2]['Dissatisfaction'],('\n%s\n%s' % (output[-2],record))
                    else:
                        assert record['Dissatisfaction'] == output[-2]['Dissatisfaction']
                # 1.t
                var = 'Risk Change'
                if not defined:
                    variables.append({'Name': var,'Values':'[-5-5]','DataType': 'Integer','Notes': '1.i.t'})
                delta = float(accessibility.getInitialState(args,name,'risk',world,states,t,name))-float(accessibility.getInitialState(args,name,'risk',world,states,t-1,name))
                if delta < 0.:
                    record[var] = -accessibility.toLikert(abs(delta),7)
                elif delta > 0.:
                    record[var] = accessibility.toLikert(delta,7)
                else:
                    record[var] = 0
                if abs(record[var]) > 5:
                    logging.warning('Clipping %s\'s risk perception change on day %d: %f' % (name,t,delta))
                    if record[var] > 0:
                        record[var] = 5
                    else:
                        record[var] = -5
                if t > hurricane['Start']:
                    # Verify delta consistency
                    if record[var] < 0:
                        assert record['Risk'] <= output[-2]['Risk']
                    elif record[var] > 0:
                        assert record['Risk'] >= output[-2]['Risk']
                    else:
                        assert record['Risk'] == output[-2]['Risk']
                # 1.u
                var = 'Injury Change'
                if not defined:
                    variables.append({'Name': var,'Values':'[-5-5]','DataType': 'Integer','Notes': '1.i.u'})
                record[var] = record['Risk Change']
                if t > hurricane['Start']:
                    # Verify delta consistency
                    if record[var] < 0:
                        assert record['Minor Injury Possibility'] <= output[-2]['Minor Injury Possibility']
                    elif record[var] > 0:
                        assert record['Minor Injury Possibility'] >= output[-2]['Minor Injury Possibility']
                    else:
                        assert record['Minor Injury Possibility'] == output[-2]['Minor Injury Possibility']
                if cmd['debug']:
                    print(record)
                if not defined:
#                    if not cmd['debug']:
#                        accessibility.writeVarDef(os.path.dirname(__file__),variables)
                    defined = True
        if not cmd['debug']:
            accessibility.writeOutput(args,output,['Participant','Timestep','Wealth']+[var['Name'] for var in variables[startField:]],
                '%s-Journal-R1.tsv' % (os.path.splitext(os.path.basename(__file__))[0]),
                os.path.join(os.path.dirname(__file__),'Instances','Instance%d' % (instance),'Runs','run-0'))
