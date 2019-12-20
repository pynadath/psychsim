from argparse import ArgumentParser
import logging
import os.path
import random
import sys

from psychsim.pwl import *
from psychsim.domains.groundtruth import accessibility
from psychsim.domains.groundtruth.simulation import survey

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO,filename='%s%s' % (os.path.splitext(__file__)[0],'.log'))
    reqNum = int(os.path.splitext(os.path.basename(__file__))[0].split('-')[2])
    random.seed(reqNum)
    team = os.path.splitext(os.path.basename(__file__))[0].split('-')[0]
    parser = ArgumentParser()
    parser.add_argument('-d','--debug',action='store_true',help='Run without writing any files')
    cmd = vars(parser.parse_args())
    participants = accessibility.readRRParticipants(os.path.join(os.path.dirname(__file__),'..','TA2A-TA1C-0462','TA2A-TA1C-0462.log'))
    variables = {}
    for instance,args in accessibility.instanceArgs('Phase2'):
        print('Instance %d (%d,%d)' % (instance,args['instance'],args['run']))
        logging.info('Instance %d (%d,%d)' % (instance,args['instance'],args['run']))
        config = accessibility.getConfig(args['instance'])
        world = accessibility.unpickle(instance)
        states = {}
        accessibility.loadState(args,states,args['span']-1,'Nature',world)
        hurricanes = [h for h in accessibility.readHurricanes(args['instance'],args['run']) if h['End'] <= args['span']]
        actors = {name for name in world.agents if name[:5] == 'Actor' and world.getState(name,'alive').first()}
        sample = random.sample(actors,len(actors)//5)
        output = []

        for partID,name in sorted(participants[instance].items()):
            logging.info('Participant %d: %s' % (partID,name))
            agent = world.agents[name]
            root = {'Timestep': args['span'],'EntityIdx': '%s %d Participant %d' % (team,reqNum-10,partID)}

            var = '%s %d Ethnicity' % (team,reqNum)
            if var not in variables:
                variables[var] = {'Name': var,'Values': 'majority,minority', 'DataType': 'String','Notes': 'Q1'}
            record = dict(root)
            record['VariableName'] = var
            record['Value'] = agent.demographics['ethnicGroup']
            output.append(record)

            var = '%s %d Wealth' % (team,reqNum)
            if var not in variables:
                variables[var] = {'Name': var,'Values': '[0-6]', 'DataType': 'Integer','Notes': 'Q2'}
            record = dict(root)
            record['VariableName'] = var
            record['Value'] = accessibility.toLikert(accessibility.getInitialState(args,name,'resources',world,states,args['span']).expectation(),7)-1
            output.append(record)

            var = '%s %d Income' % (team,reqNum)
            if var not in variables:
                variables[var] = {'Name': var,'Values': '[0-6]', 'DataType': 'Integer','Notes': 'Q3'}
            record = dict(root)
            record['VariableName'] = var
            if accessibility.getInitialState(args,name,'employed',world,states,args['span']).first():
                record['Value'] = accessibility.toLikert(accessibility.likert[5][config.getint('Actors','job_impact')-1],7)-1
            else:
                record['Value'] = 0
            output.append(record)

            var = '%s %d Tax Rate' % (team,reqNum)
            if var not in variables:
                variables[var] = {'Name': var,'Values': '[0-6]', 'DataType': 'Integer','Notes': 'Q4'}
            record = dict(root)
            record['VariableName'] = var
            record['Value'] = 0
            output.append(record)

            var = '%s %d Evacuation Incentive' % (team,reqNum)
            if var not in variables:
                variables[var] = {'Name': var,'Values': 'yes,no', 'DataType': 'Boolean','Notes': 'Q5'}
            record = dict(root)
            record['VariableName'] = var
            record['Value'] = 'no'
            output.append(record)

            var = '%s %d Law Enforcement Assistance' % (team,reqNum)
            if var not in variables:
                variables[var] = {'Name': var,'Values': 'yes,no', 'DataType': 'Boolean','Notes': 'Q5'}
            record = dict(root)
            record['VariableName'] = var
            record['Value'] = 'no'
            output.append(record)

            var = '%s %d Outside Disaster Relief' % (team,reqNum)
            if var not in variables:
                variables[var] = {'Name': var,'Values': 'yes,no', 'DataType': 'Boolean','Notes': 'Q5'}
            record = dict(root)
            record['VariableName'] = var
            record['Value'] = 'no'
            output.append(record)

            var = '%s %d Evacuation Routes' % (team,reqNum)
            if var not in variables:
                variables[var] = {'Name': var,'Values': 'yes,no', 'DataType': 'Boolean','Notes': 'Q5'}
            record = dict(root)
            record['VariableName'] = var
            record['Value'] = 'no'
            output.append(record)

            var = '%s %d Hospitalization Support' % (team,reqNum)
            if var not in variables:
                variables[var] = {'Name': var,'Values': 'yes,no', 'DataType': 'Boolean','Notes': 'Q5'}
            record = dict(root)
            record['VariableName'] = var
            record['Value'] = 'no'
            output.append(record)

            var = '%s %d Shelter Restriction' % (team,reqNum)
            if var not in variables:
                variables[var] = {'Name': var,'Values': 'Region[01-16],yes,no', 'DataType': 'String','Notes': 'Q6'}
            record = dict(root)
            record['VariableName'] = var
            for action in agent.actions:
                if action['verb'] == 'moveTo' and action['object'][:7] == 'shelter':
                    if agent.demographics['pet']:
                        record['Value'] = 'Region%s,yes' % (action['object'][7:])
                    else:
                        record['Value'] = 'Region%s,no' % (action['object'][7:])
                    break
            output.append(record)

        if not cmd['debug']:
            accessibility.writeOutput(args,output,accessibility.fields['RunData'],'RunDataTable.tsv',
                os.path.join(os.path.dirname(__file__),'Instances','Instance%d' % (instance),'Runs','run-0'))
    if not cmd['debug']:
        accessibility.writeVarDef(os.path.dirname(__file__),list(variables.values()))
