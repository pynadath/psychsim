from argparse import ArgumentParser
import logging
import os.path
import pickle
import random
import sys

from psychsim.pwl import *
from psychsim.domains.groundtruth import accessibility
from psychsim.domains.groundtruth.simulation.execute import fastForward

from TA2A_TA1C_0252 import aidWillingnessEtc

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO,filename='%s%s' % (os.path.splitext(__file__)[0],'.log'))
    parser = ArgumentParser()
    parser.add_argument('-d','--debug',action='store_true',help='Run without writing any files')
    random.seed(int(os.path.splitext(os.path.basename(__file__))[0].split('-')[2]))
    cmd = vars(parser.parse_args())
    defined = False
    variables = []
    for instance,args in accessibility.instanceArgs('Phase2','Explain'):
        if cmd['debug']:
            print('Instance %d (%d,%d)' % (instance,args['instance'],args['run']))
        logging.info('Instance %d (%d,%d)' % (instance,args['instance'],args['run']))
        config = accessibility.getConfig(args['instance'])
        states = {}
        yearLength = config.getint('Disaster','year_length',fallback=365)
        day1 = (args['span']//yearLength + 1)*yearLength
        try:
            world = accessibility.unpickle(instance,day=day1+1)
        except FileNotFoundError:
            world = accessibility.unpickle(instance)
            accessibility.loadState(args,states,args['span']-1,'Nature',world)
            fastForward(world,config)
            day = world.getState(WORLD,'day').first()
            with open(os.path.join(accessibility.getDirectory(args),'scenario%d.pkl' % (day)),'wb') as outfile:
                pickle.dump(world,outfile)
        hurricanes = [h for h in accessibility.readHurricanes(args['instance'],args['run']) if h['End'] <= args['span']]
        pool = {name for name in world.agents if name[:5] == 'Actor' and world.getState(name,'alive').first()}
        demos = {name: accessibility.getCurrentDemographics(args,name,world,states,config,args['span']) for name in pool}
        participants = random.sample(pool,(len(pool)//20))
        print(len(participants))
        output = []
        for partID in range(len(participants)):
            if not defined:
                variables.append({'Name': 'Participant','Values': '[1+]','VarType': 'fixed','DataType': 'Integer'})
            record = {'Participant': partID+1}
            output.append(record)
            name = participants[partID]
            logging.info('Participant %d: %s' % (record['Participant'],name))
            agent = world.agents[name]
            # 0.i.1-9
            if not defined:
                variables += accessibility.boilerPlate
            record.update(demos[name])
            # 0.i.10
            record['Timestep'] = args['span']
            # 0.i.11
            if not defined:
                aidVars = []
            else:
                aidVars = None
            aidWillingnessEtc(args,agent,record,world,states,demos,hurricanes,pool,aidVars)
            if not defined:
                variables += aidVars
            for other in range(len(participants)):
                var = 'Relationship Participant %d' % (other+1)
                if not defined:
                    variables.append({'Name': var,'Values': 'self,family,friend,acquaintance,stranger','DataType': 'String','Notes': 'I.1.a.'})
                if other == partID:
                    record[var] = 'self'
                elif participants[other] in agent.getFriends():
                    record[var] = 'friend'
                elif participants[other] in agent.getNeighbors():
                    record[var] = 'acquaintance'
                else:
                    record[var] = 'stranger'
                newvar = 'Closeness Participant %d' % (other+1)
                if not defined:
                    variables.append({'Name': newvar,'Values': '[0-6]','DataType': 'Integer','Notes': 'I.1.b.'})
                if record[var] == 'self':
                    record[newvar] = 6
                elif record[var] == 'friend': 
                    if participants[other] in agent.getNeighbors():
                        record[newvar] = 4
                    else:
                        record[newvar] = 3
                elif record[var] == 'acquaintance':
                    record[newvar] = 2
                else:
                    record[newvar] = 0
            if cmd['debug']:
                print(record)
            if not defined:
                if not cmd['debug']:
                    accessibility.writeVarDef(os.path.dirname(__file__),variables)
                defined = True
        if not cmd['debug']:
            accessibility.writeOutput(args,output,[var['Name'] for var in variables],'%s-Participants.tsv' % (os.path.splitext(os.path.basename(__file__))[0]),
                os.path.join(os.path.dirname(__file__),'Instances','Instance%d' % (instance),'Runs','run-0'))
        exit()
        output = []
        for partID in range(len(sample)):
            name = sample[partID]
            logging.info('Participant %d: %s' % (partID+1,name))
            agent = world.agents[name]
            record = {}
            var = 'Participant'
            if not defined:
                variables.append({'Name': var,'Values':'[1+]','VarType': 'fixed','DataType': 'Integer'})
            record[var] = partID+1
            var = 'Group'
            if not defined:
                variables.append({'Name': var,'Values':'[0-4]','VarType': 'fixed','DataType': 'Integer','Notes': 'Assigned condition'})
            record[var] = partID % 4
            policy = {}
            if record[var] == 1:
                for action in world.agents['System'].actions:
                    if action['verb'] == 'doNothing':
                        policy['System'] = action
                        break
            elif record[var] == 2:
                for action in world.agents['System'].actions:
                    if action['verb'] == 'allocate' and action['object'] == agent.demographics['home']:
                        policy['System'] = action
                        break
            elif record[var] == 3:
                for action in world.agents['System'].actions:
                    if action['verb'] == 'allocate' and action['object'] != agent.demographics['home']:
                        policy['System'] = action
                        break
            history = accessibility.holoCane(world,config,name,config.getint('Disaster','season_length'),True,policy)
            record.update(accessibility.getCurrentDemographics(args,name,world,states,config))
            newRecords = processHistory(world,name,record,history,output,day1,None if defined else variables)
            if cmd['debug']:
                for record in newRecords:
                    print(record)
            output += newRecords
            print(name)
            if not defined:
                if not cmd['debug']:
                    accessibility.writeVarDef(os.path.dirname(__file__),variables)
                defined = True
        if not cmd['debug']:
            accessibility.writeOutput(args,output,[var['Name'] for var in variables],'%s.tsv' % (os.path.splitext(os.path.basename(__file__))[0]),
                os.path.join(os.path.dirname(__file__),'Instances','Instance%d' % (instance),'Runs','run-0'))
