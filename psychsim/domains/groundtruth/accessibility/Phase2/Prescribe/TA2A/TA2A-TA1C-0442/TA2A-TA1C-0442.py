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
    variables = accessibility.boilerDict
    for instance,args in accessibility.instanceArgs('Phase2'):
        print('Instance %d (%d,%d)' % (instance,args['instance'],args['run']))
        logging.info('Instance %d (%d,%d)' % (instance,args['instance'],args['run']))
        challenge = accessibility.instanceChallenge(instance)[1]
        config = accessibility.getConfig(args['instance'])
        world = accessibility.unpickle(instance)
        states = {}
        accessibility.loadState(args,states,args['span']-1,'Nature',world)
        hurricanes = [h for h in accessibility.readHurricanes(args['instance'],args['run']) if h['End'] <= args['span']]
        hurricane = hurricanes[-1]
        aid = accessibility.getAid(args,world,states,(hurricane['Start'],hurricane['End']+1))
        actors = {name for name in world.agents if name[:5] == 'Actor' and world.getState(name,'alive').first()}
        sample = random.sample(actors,len(actors)//10)
        output = []
        for partID in range(len(sample)):
            name = sample[partID]
            logging.info('Participant %d: %s' % (partID+1,name))
            agent = world.agents[name]
            root = {'Timestep': args['span'],'EntityIdx': '%s %d Participant %d' % (team,reqNum,partID+1)}

            var = '%s %d Risk' % (team,reqNum)
            if var not in variables:
                variables[var] = {'Name': var,'Values':'[0-6]','DataType': 'Integer','Notes': 'Q1'}
            risk = [dist.expectation() for dist in accessibility.getInitialState(args,name,'risk',world,states,
                (hurricane['Start'],hurricane['End']+1),name)]
            record = dict(root)
            record['VariableName'] = var
            record['Value'] = accessibility.toLikert(max(risk),7)-1
            output.append(record)

            var = '%s %d Dissatisfaction' % (team,reqNum)
            if var not in variables:
                variables[var] = {'Name': var,'Values':'[0-6]','DataType': 'Integer','Notes': 'Q2'}
            record = dict(root)
            record['VariableName'] = var
            record['Value'] = accessibility.toLikert(world.getState(name,'grievance').expectation(),7)-1
            output.append(record)

            var = '%s %d Injured' % (team,reqNum)
            if var not in variables:
                variables[var] = {'Name': var,'Values':'yes,no','DataType': 'Boolean','Notes': 'Q3'}
            health = [dist.first() for dist in accessibility.getInitialState(args,name,'health',world,states,(hurricane['Start'],hurricane['End']+1))]
            record = dict(root)
            record['VariableName'] = var
            record['Value'] = 'yes' if min(health) < 0.2 else 'no'
            output.append(record)

            var = '%s %d Action' % (team,reqNum)
            if var not in variables:
                variables[var] = {'Name': var,'Values': 'went home,sheltered,evacuated,none','DataType': 'String','Notes': 'Q4: Comma-separated'}
            record = dict(root)
            record['VariableName'] = var
            location = {loc.first() for loc in accessibility.getInitialState(args,name,'location',world,states,(hurricane['Start'],hurricane['End']+1))}
            actions = set(accessibility.getAction(args,name,world,states,(hurricane['Start'],hurricane['End']+1)))
            verbs = {act['verb'] for act in actions}
            if 'decreaseRisk' in verbs:
                verbs.remove('decreaseRisk')
            if 'takeResources' in verbs:
                verbs.remove('takeResources')
            if 'stayInLocation' in verbs or len(verbs) == 0:
                # Never moved
                if len(verbs) == 1:
                    assert len(location) == 1
                    location = next(iter(location))
                    if location == agent.demographics['home']:
                        record['Value'] = 'none'
                    elif location == 'evacuated':
                        record['Value'] = 'evacuated'
                    else:
                        assert location[:7] == 'shelter'
                        record['Value'] = 'sheltered'
                else:
                    # Staying in location for one day does not matter
                    actions = {act for act in actions if act['verb'] != 'stayInLocation'}
            if 'Value' not in record:
                actions = {'sheltered' if act['verb'] == 'moveTo' and act['object'][:7] == 'shelter' else act for act in actions}
                record['Value'] = ','.join(sorted([str(act) for act in actions \
                    if isinstance(act,str) or act['verb'] not in {'decreaseRisk','takeResources'}]))
                assert len(record['Value']) > 0
                record['Value'] = record['Value'].replace('%s-evacuate' % (name),'evacuated')
                record['Value'] = record['Value'].replace('%s-moveTo-%s' % (name,agent.demographics['home']),'went home')
            output.append(record)

            var = '%s %d Paid Evacuation' % (team,reqNum)
            if var not in variables:
                variables[var] = {'Name': var,'Values':'yes,no','DataType': 'Boolean','Notes': 'Q5'}
            record = dict(root)
            record['VariableName'] = var
            record['Value'] = 'no'
            output.append(record)

            var = '%s %d Remain w/Family' % (team,reqNum)
            if var not in variables:
                variables[var] = {'Name': var,'Values':'yes,no','DataType': 'Boolean','Notes': 'Q6'}
            record = dict(root)
            record['VariableName'] = var
            record['Value'] = 'yes'
            output.append(record)

            var = '%s %d Govt Aid' % (team,reqNum)
            if var not in variables:
                variables[var] = {'Name': var,'Values':'yes,no','DataType': 'Boolean','Notes': 'Q7'}
            record = dict(root)
            record['VariableName'] = var
            record['Value'] = 'yes' if agent.demographics['home'] in aid.values() else 'no'
            output.append(record)

            var = '%s %d Tax Change' % (team,reqNum)
            if var not in variables:
                variables[var] = {'Name': var,'Values':'yes,no','DataType': 'Boolean','Notes': 'Q8'}
            record = dict(root)
            record['VariableName'] = var
            record['Value'] = 'N/A'
            output.append(record)

            var = '%s %d Aided Others' % (team,reqNum)
            if var not in variables:
                variables[var] = {'Name': var,'Values':'yes,no','DataType': 'Boolean','Notes': 'Q9'}
            record = dict(root)
            record['VariableName'] = var
            record['Value'] = 'yes' if 'decreaseRisk' in verbs else 'no'
            output.append(record)

        if not cmd['debug']:
            accessibility.writeOutput(args,output,accessibility.fields['RunData'],'RunDataTable.tsv',
                os.path.join(os.path.dirname(__file__),'Instances','Instance%d' % (instance),'Runs','run-0'))
    if not cmd['debug']:
        accessibility.writeVarDef(os.path.dirname(__file__),list(variables.values()))
