from argparse import ArgumentParser
import csv
import logging
import os.path
import random
import sys

from psychsim.pwl import *
from psychsim.action import makeActionSet
from psychsim.domains.groundtruth import accessibility
from psychsim.domains.groundtruth.simulation import survey

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO,filename='%s%s' % (os.path.splitext(__file__)[0],'.log'))
    parser = ArgumentParser()
    parser.add_argument('-d','--debug',action='store_true',help='Run without writing any files')
    cmd = vars(parser.parse_args())
    defined = False
    variables = []
    for instance,args in accessibility.instanceArgs('Phase2','Explain'):
        if cmd['debug']:
            print('Instance %d (%d,%d)' % (instance,args['instance'],args['run']))
        logging.info('Instance %d (%d,%d)' % (instance,args['instance'],args['run']))
        config = accessibility.getConfig(args['instance'])
        world = accessibility.unpickle(instance)
        states = {}
        participants = accessibility.readParticipants(args['instance'],args['run'],splitHurricanes=True)
        hurricanes = [h for h in accessibility.readHurricanes(args['instance'],args['run']) if h['End'] <= args['span']]
        output = []
        # Grab timesteps from previous paired survey
        timesteps = {}
        with open(os.path.join(os.path.dirname(__file__),'..','TA2B-TA1C-02','Instances','Instance%d' % (instance),'Runs','run-0',
            'TA2B-TA1C-2-Post.tsv'),'r') as csvfile:
            reader = csv.DictReader(csvfile,delimiter='\t')
            for row in reader:
                partID = int(row['Participant'])
                if partID not in timesteps:
                    timesteps[partID] = {}
                hurricane = int(row['Hurricane'])
                timesteps[partID][hurricane] = int(row['Timestep'])
        for partID in timesteps:
            name = participants['Post-survey %d' % (min(timesteps[partID]))][partID]
            for hurricaneID,t in timesteps[partID].items():
                hurricane = hurricanes[hurricaneID-1]
                assert hurricane['Hurricane'] == hurricaneID
                logging.info('Participant %d Hurricane %d: %s' % (partID,hurricane['Hurricane'],name))
                agent = world.agents[name]
                record = {}
                output.append(record)
                var = 'Participant'
                if not defined:
                    variables.append({'Name': var,'Values':'[1+]','VarType': 'fixed','DataType': 'Integer'})
                record[var] = partID
                var = 'Hurricane'
                if not defined:
                    variables.append({'Name': var,'Values':'[1+]','DataType': 'Integer'})
                record[var] = hurricane['Hurricane']
                var = 'Timestep'
                if not defined:
                    variables.append({'Name': var,'Values':'[1+]','DataType': 'Integer'})
                record[var] = t
                var = 'Evacuation Past Safety'
                if not defined:
                    variables.append({'Name': var,'Values':'[1-7]','DataType': 'Integer','Notes': 'Q1'})
                evac = random.randint(hurricane['Start']+1,hurricane['Landfall'])
                risks = [risk.expectation() for risk in accessibility.getInitialState(args,name,'risk',world,states,(hurricane['Start'],evac),name)]
                record[var] = accessibility.toLikert(max(risks),7)
                var = 'Shelter Past Safety'
                if not defined:
                    variables.append({'Name': var,'Values':'[1-7]','DataType': 'Integer','Notes': 'Q2'})
                shelter = random.randint(hurricane['Start']+1,hurricane['Landfall'])
                risks = [risk.expectation() for risk in accessibility.getInitialState(args,name,'risk',world,states,(hurricane['Start'],shelter),name)]
                shelterAct = []
                for action in agent.actions:
                    if action['verb'] == 'moveTo' and action['object'][:7] == 'shelter':
                        risks += [risk.expectation() for risk in accessibility.getInitialState(args,'Region%s' % (action['object'][7:]),
                            'shelterRisk',world,states,(shelter,hurricane['End']),name)]
                        shelterAct.append(action)
                record[var] = accessibility.toLikert(max(risks),7)
                risks = accessibility.getInitialState(args,agent.demographics['home'],'risk',world,states,(hurricane['Start'],hurricane['End']),name)
                riskMax = max([risk.expectation() for risk in risks])
                var = 'Stay at Home Past Safety'
                if not defined:
                    variables.append({'Name': var,'Values':'[1-7]','DataType': 'Integer','Notes': 'Q3'})
                record[var] = accessibility.toLikert(riskMax,7)
                var = 'Evacuation Past Property'
                if not defined:
                    variables.append({'Name': var,'Values':'[1-7]','DataType': 'Integer','Notes': 'Q4'})
                record[var] = accessibility.toLikert(riskMax,7)
                var = 'Shelter Past Property'
                if not defined:
                    variables.append({'Name': var,'Values':'[1-7]','DataType': 'Integer','Notes': 'Q5'})
                record[var] = accessibility.toLikert(riskMax,7)
                var = 'Stay at Home Past Property'
                if not defined:
                    variables.append({'Name': var,'Values':'[1-7]','DataType': 'Integer','Notes': 'Q6'})
                record[var] = accessibility.toLikert(riskMax,7)
                var = 'Evacuation Past Wealth'
                if not defined:
                    variables.append({'Name': var,'Values':'[1-7]','DataType': 'Integer','Notes': 'Q7'})
                wealth = [accessibility.getInitialState(args,name,'resources',world,states,evac-1,name)]
                for day in range(evac,hurricane['End']):
                    state = states[day-1]['Nature'][name]
                    assert len(state) == 1
                    state = copy.deepcopy(next(iter(state.values())))
                    if day == evac:
                        tree = world.dynamics[makeActionSet(name,'evacuate')][stateKey(name,'employed')]
                        state *= tree
                        job = state[stateKey(name,'employed',True)]
                        tree = world.dynamics[makeActionSet(name,'evacuate')][stateKey(name,'resources')]
                    else:
                        world.setState(name,'employed',job,state)
                        world.setState(name,'resources',wealth[-1],state)
                        world.setState(name,'location','evacuated',state)
                        tree = world.dynamics[makeActionSet(name,'stayInLocation')][stateKey(name,'resources')]
                    state *= tree
                    wealth.append(state[stateKey(name,'resources',True)])
                logging.info([w.expectation() for w in wealth])
                try:
                    record[var] = accessibility.toLikert(1.-wealth[-1].expectation()/wealth[0].expectation(),7)
                except ZeroDivisionError:
                    record[var] = 1
                var = 'Shelter Past Wealth'
                if not defined:
                    variables.append({'Name': var,'Values':'[1-7]','DataType': 'Integer','Notes': 'Q8'})
                wealth = [accessibility.getInitialState(args,name,'resources',world,states,evac-1,name)]
                assert len(shelterAct) == 1
                action = next(iter(shelterAct))
                for day in range(evac,hurricane['End']):
                    state = states[day-1]['Nature'][name]
                    assert len(state) == 1
                    state = copy.deepcopy(next(iter(state.values())))
                    if day == shelter:
                        pass
                    else:
                        world.setState(name,'resources',wealth[-1],state)
                        world.setState(name,'location','shelter%s' % (action['object'][-2:]),state)
                        tree = world.dynamics[makeActionSet(name,'stayInLocation')][stateKey(name,'resources')]
                    state *= tree
                    wealth.append(state[stateKey(name,'resources',True)])
                logging.info([w.expectation() for w in wealth])
                try:
                    record[var] = accessibility.toLikert(1.-wealth[-1].expectation()/wealth[0].expectation(),7)
                except ZeroDivisionError:
                    record[var] = 1
                var = 'Stay at Home Past Wealth'
                if not defined:
                    variables.append({'Name': var,'Values':'[1-7]','DataType': 'Integer','Notes': 'Q9'})
                wealth = [accessibility.getInitialState(args,name,'resources',world,states,evac-1,name)]
                for day in range(evac,hurricane['End']):
                    state = states[day-1]['Nature'][name]
                    assert len(state) == 1
                    state = copy.deepcopy(next(iter(state.values())))
                    world.setState(name,'location',agent.demographics['home'],state)
                    world.setState(name,'resources',wealth[-1],state)
                    tree = world.dynamics[makeActionSet(name,'stayInLocation')][stateKey(name,'resources')]
                    state *= tree
                    wealth.append(state[stateKey(name,'resources',True)])
                logging.info([w.expectation() for w in wealth])
                try:
                    record[var] = accessibility.toLikert(1.-wealth[-1].expectation()/wealth[0].expectation(),7)
                except ZeroDivisionError:
                    record[var] = 1
                var = 'Risk Independent Past'
                if not defined:
                    variables.append({'Name': var,'Values':'[1-7]','DataType': 'Integer','Notes': 'Q10. NA if no friends.'})
                friendRisk = None
                for friend in agent.getFriends():
                    try:
                        friendRisks = accessibility.getInitialState(args,world.agents[friend].demographics['home'],'risk',world,states,
                            (hurricane['Start'],hurricane['End']),friend)
                    except KeyError:
                        logging.warning('%s assumed dead somewhere before day %s' % (friend,hurricane['End']))
                        continue
                    if friendRisk is None:
                        friendRisk = max([risk.expectation() for risk in friendRisks])
                    else:
                        friendRisk += max([risk.expectation() for risk in friendRisks])
                if friendRisk is None:
                    record[var] = 'NA'
                else:   
                    delta = riskMax - friendRisk/len(agent.getFriends())
                    record[var] = accessibility.toLikert(delta+0.5,7)
                if cmd['debug']:
                    print(record)
                if not defined:
                    if not cmd['debug']:
                        accessibility.writeVarDef(os.path.dirname(__file__),variables)
                    defined = True
        if not cmd['debug']:
            accessibility.writeOutput(args,output,[var['Name'] for var in variables],'%s.tsv' % (os.path.splitext(os.path.basename(__file__))[0]),
                os.path.join(os.path.dirname(__file__),'Instances','Instance%d' % (instance),'Runs','run-0'))
