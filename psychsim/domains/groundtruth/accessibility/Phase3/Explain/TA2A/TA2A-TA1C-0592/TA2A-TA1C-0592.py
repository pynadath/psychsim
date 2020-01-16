from argparse import ArgumentParser
import logging
import os.path
import pickle
import random
import sys

from psychsim.pwl import *
from psychsim.domains.groundtruth import accessibility

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO,filename='%s%s' % (os.path.splitext(__file__)[0],'.log'))
    parser = ArgumentParser()
    parser.add_argument('-d','--debug',action='store_true',help='Run without writing any files')
    reqNum = int(os.path.splitext(os.path.basename(__file__))[0].split('-')[2])
    team = os.path.splitext(os.path.basename(__file__))[0].split('-')[0]
    random.seed(reqNum)
    cmd = vars(parser.parse_args())
    variables = {}
    for instance,args in accessibility.instanceArgs('Phase3','Explain'):
        print('Instance %d (%d,%d)' % (instance,args['instance'],args['run']))
        logging.info('Instance %d (%d,%d)' % (instance,args['instance'],args['run']))
        config = accessibility.getConfig(args['instance'])
        states = {}
        # Load world
        world = accessibility.unpickle(instance)
        accessibility.loadState(args,states,args['span']-1,'Nature',world)
        participants = accessibility.readParticipants(args['instance'],args['run'])
        hurricanes = [h for h in accessibility.readHurricanes(args['instance'],args['run']) if h['End'] <= args['span']]
        actors = [name for name in world.agents if name[:5] == 'Actor' and stateKey(name,'health') in world.state]
        shelters = [name for name in world.agents if name[:6] == 'Region' and stateKey(name,'shelterRisk') in world.variables]
        sample = random.sample(actors,len(actors)//5)
        output = []
        partID = 0
        for name in sample:
            partID += 1
            agent = world.agents[name]
            logging.info('Participant %d: %s' % (partID,name))

            root = {'Timestep': args['span'],'EntityIdx': '%s %d Participant %d' % (team,reqNum,partID)}

            surveyID = accessibility.participantMatch(name,participants)
            if surveyID is not None:
                var = '%s %d Survey ID' % (team,reqNum)
                if var not in variables:
                    variables[var] = {'Name': var,'Values':'Actor[Pre,Post] [1+] Hurricane [1+]','DataType': 'String'}
                record = dict(root)
                record['VariableName'] = var
                record['Value'] = surveyID
                output.append(record)

            for hurricane in hurricanes:
                locations = accessibility.getInitialState(args,name,'location',world,states,(hurricane['Start']-1,hurricane['End']+1),unique=True)
                wealth = accessibility.getInitialState(args,name,'resources',world,states,(hurricane['Start']-1,hurricane['End']+1),unique=True)

                sheltered = False
                delta = 0
                for t in range(1,len(locations)):
                    if locations[t][:7] == 'shelter':
                        sheltered = True
                        delta += wealth[t] - wealth[t-1]

                if sheltered:
                    var = '%s %d Hurricane %d Shelter Wealth Change' % (team,reqNum,hurricane['Hurricane'])
                    if var not in variables:
                        variables[var] = {'Name': var,'Values':'[-7-7]','DataType': 'Integer','Notes': 'Q1a'}
                    record = dict(root)
                    record['VariableName'] = var
                    if delta < 0:
                        record['Value'] = -accessibility.toLikert(abs(delta),7)
                    else:
                        record['Value'] = accessibility.toLikert(abs(delta),7)
                    output.append(record)

                evacuated = False
                delta = 0
                for t in range(1,len(locations)):
                    if locations[t] == 'evacuated':
                        evacuated = True
                        delta += wealth[t] - wealth[t-1]

                if evacuated:
                    var = '%s %d Hurricane %d Evacuation Wealth Cost' % (team,reqNum,hurricane['Hurricane'])
                    if var not in variables:
                        variables[var] = {'Name': var,'Values':'[1-7]','DataType': 'Integer','Notes': 'Q2a'}
                    record = dict(root)
                    record['VariableName'] = var
                    if delta < 0:
                        record['Value'] = accessibility.toLikert(abs(delta),7)
                    else:
                        record['Value'] = 1
                    output.append(record)

                delta = wealth[-1] - wealth[0]
                if delta < 0:
                    var = '%s %d Hurricane %d Wealth Loss' % (team,reqNum,hurricane['Hurricane'])
                    if var not in variables:
                        variables[var] = {'Name': var,'Values':'[1-7]','DataType': 'Integer','Notes': 'Q3a'}
                    record = dict(root)
                    record['VariableName'] = var
                    record['Value'] = accessibility.toLikert(abs(delta),7)
                    output.append(record)


        if not cmd['debug']:
            accessibility.writeOutput(args,output,accessibility.fields['RunData'],'RunDataTable.tsv',
                os.path.join(os.path.dirname(__file__),'Instances','Instance%d' % (instance),'Runs','run-0'))
    if not cmd['debug']:
        accessibility.writeVarDef(os.path.dirname(__file__),sorted(variables.values(),key=lambda v: v['Name']))
