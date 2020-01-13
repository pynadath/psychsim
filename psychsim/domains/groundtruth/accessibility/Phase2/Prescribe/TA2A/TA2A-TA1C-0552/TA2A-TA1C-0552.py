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
    demos = ['Residence','Age','Gender','Wealth']
    variables = {field: accessibility.boilerDict[field] for field in demos}
    for instance,args in accessibility.instanceArgs('Phase2'):
        print('Instance %d (%d,%d)' % (instance,args['instance'],args['run']))
        logging.info('Instance %d (%d,%d)' % (instance,args['instance'],args['run']))
        config = accessibility.getConfig(args['instance'])
        world = accessibility.unpickle(instance)
        states = {}
        accessibility.loadState(args,states,args['span']-1,'Nature',world)
        hurricanes = [h for h in accessibility.readHurricanes(args['instance'],args['run']) if h['End'] <= args['span']]
        t = hurricanes[-1]['End']
        actors = [name for name in world.agents if name[:5] == 'Actor' and world.getState(name,'alive').first()]
        shelters = [name for name in world.agents if name[:6] == 'Region' and stateKey(name,'shelterRisk') in world.variables]
        random.shuffle(actors)
        output = []
        for partID in range(len(actors)):
            name = actors[partID]
            logging.info('Participant %d: %s' % (partID+1,name))
            agent = world.agents[name]

            root = {'Timestep': t,'EntityIdx': '%s %d Participant %d' % (team,reqNum,partID+1)}

            values = accessibility.getCurrentDemographics(args,name,world,states,config)
            for var in demos:
                record = dict(root)
                record['VariableName'] = var
                if var == 'Wealth':
                    record['Value'] = accessibility.toLikert(float(accessibility.getInitialState(args,name,'resources',world,states,t)),7)
                else:
                    record['Value'] = values[var]
                output.append(record)

            var = '%s %d Health Issues' % (team,reqNum)
            if var not in variables:
                variables[var] = {'Name': var,'Values':'[1-7]','DataType': 'Integer','Notes': 'Q1e'}
            record = dict(root)
            record['VariableName'] = var
            record['Value'] = 1
            output.append(record)

            actions = accessibility.getAction(args,name,world,states,(1,t))
            var = '%s %d Criminal Record' % (team,reqNum)
            if var not in variables:
                variables[var] = {'Name': var,'Values':'[0+]','DataType': 'Integer','Notes': 'Q2'}
            record = dict(root)
            record['VariableName'] = var
            record['Value'] = [action['verb'] for action in actions].count('takeResources')
            output.append(record)

            var = '%s %d Navigation Confidence' % (team,reqNum)
            if var not in variables:
                variables[var] = {'Name': var,'Values':'[1-7]','DataType': 'Integer','Notes': 'Q3'}
            record = dict(root)
            record['VariableName'] = var
            record['Value'] = 7
            output.append(record)

            locations = accessibility.getInitialState(args,name,'location',world,states,(1,t),unique=True)
            hLocations = [{locations[i-1] for i in range(h['Start'],h['End'])} for h in hurricanes]
            home = [locs for locs in hLocations if len(locs) == 1 and agent.demographics['home'] in locs]

            var = '%s %d Stay Home Willingness' % (team,reqNum)
            if var not in variables:
                variables[var] = {'Name': var,'Values':'[1-7]','DataType': 'Integer','Notes': 'Q4'}
            record = dict(root)
            record['VariableName'] = var
            record['Value'] = accessibility.toLikert(len(home)/len(hurricanes),7)
            output.append(record)

            var = '%s %d Location' % (team,reqNum)
            if var not in variables:
                variables[var] = {'Name': var,'Values':'home,evacuated,shelter','DataType': 'String','Notes': 'Q5'}
            record = dict(root)
            record['VariableName'] = var
            if locations[-1] == agent.demographics['home']:
                record['Value'] = 'home'
            elif locations[-1][:7] == 'shelter':
                record['Value'] = 'shelter'
            else:
                assert locations[-1] == 'evacuated'
                record['Value'] = locations[-1]
            output.append(record)

            var = '%s %d Shelter Comfort' % (team,reqNum)
            if var not in variables:
                variables[var] = {'Name': var,'Values':'[1-7]','DataType': 'Integer','Notes': 'Q6'}
            record = dict(root)
            record['VariableName'] = var
            beliefs = states[t-1]['Nature'][name]
            assert len(beliefs) == 1
            beliefs = next(iter(beliefs.values()))
            for region in shelters:
                if stateKey(region,'shelterRisk') in beliefs.keys():
                    record['Value'] = accessibility.toLikert(1-float(world.getState(region,'shelterRisk',beliefs)),7)
                    break
            else:
                raise ValueError('No beliefs about shelter: %s' % (name))
            output.append(record)

        if not cmd['debug']:
            accessibility.writeOutput(args,output,accessibility.fields['RunData'],'RunDataTable.tsv',
                os.path.join(os.path.dirname(__file__),'Instances','Instance%d' % (instance),'Runs','run-0'))
    if not cmd['debug']:
        accessibility.writeVarDef(os.path.dirname(__file__),list(variables.values()))
