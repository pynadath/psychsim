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
    variables = {}
    for instance,args in accessibility.instanceArgs('Phase2'):
        print('Instance %d (%d,%d)' % (instance,args['instance'],args['run']))
        logging.info('Instance %d (%d,%d)' % (instance,args['instance'],args['run']))
        challenge = accessibility.instanceChallenge(instance)[1]
        config = accessibility.getConfig(args['instance'])
        world = accessibility.unpickle(instance)
        states = {}
        accessibility.loadState(args,states,args['span']-1,'Nature',world)
        hurricanes = [h for h in accessibility.readHurricanes(args['instance'],args['run']) if h['End'] <= args['span']]
        actors = {name for name in world.agents if name[:5] == 'Actor' and world.getState(name,'alive').first()}
        sample = random.sample(actors,len(actors)//5)
        output = []
        for partID in range(len(sample)):
            name = sample[partID]
            logging.info('Participant %d: %s' % (partID+1,name))
            agent = world.agents[name]
            root = {'Timestep': args['span'],'EntityIdx': '%s %d Participant %d' % (team,reqNum,partID+1)}

            for hurricane in hurricanes[-5:]:
                var = '%s %d Hurricane %d Injury' % (team,reqNum,hurricane['Hurricane'])
                if var not in variables:
                    variables[var] = {'Name': var,'Values':'[0-6]','DataType': 'Integer','Notes': 'Q1'}
                health = [dist.first() for dist in accessibility.getInitialState(args,name,'health',world,states,(hurricane['Start'],hurricane['End']+1))]
                record = dict(root)
                record['VariableName'] = var
                if min(health) < 0.2:
                    record['Value'] = accessibility.toLikert((0.2-min(health))*5*6/7+1/7+1e-4,7)-1
                    assert record['Value'] > 0
                else:
                    record['Value'] = 0
                output.append(record)

                var = '%s %d Hurricane %d Action' % (team,reqNum,hurricane['Hurricane'])
                if var not in variables:
                    variables[var] = {'Name': var,'Values': 'go home,shelter,evacuate,stay in current location',
                    'DataType': 'String','Notes': 'Q2: Comma-separated'}
                record = dict(root)
                record['VariableName'] = var
                location = {loc.first() for loc in accessibility.getInitialState(args,name,'location',world,states,(hurricane['Start'],hurricane['End']+1))}
                actions = set(accessibility.getAction(args,name,world,states,(hurricane['Start'],hurricane['End']+1)))
                verbs = {act['verb'] for act in actions}
                if 'decreaseRisk' in verbs:
                    verbs.remove('decreaseRisk')
                    verbs.add('stayInLocation')
                if 'takeResources' in verbs:
                    verbs.remove('takeResources')
                    verbs.add('stayInLocation')
                if 'stayInLocation' in verbs:
                    if len(verbs) == 1:
                        # Never moved
                        assert len(location) == 1
                        location = next(iter(location))
                        if location == agent.demographics['home']:
                            record['Value'] = 'stay in current location'
                        elif location == 'evacuated':
                            record['Value'] = 'evacuate'
                        else:
                            assert location[:7] == 'shelter'
                            record['Value'] = 'shelter'
                    else:
                        # Staying in location for one day does not matter
                        actions = {act for act in actions if act['verb'] != 'stayInLocation'}
                if 'Value' not in record:
                    actions = {'shelter' if act['verb'] == 'moveTo' and act['object'][:7] == 'shelter' else act for act in actions}
                    record['Value'] = ','.join(sorted([str(act) for act in actions \
                        if isinstance(act,str) or act['verb'] not in {'decreaseRisk','takeResources'}]))
                    assert len(record['Value']) > 0,set(accessibility.getAction(args,name,world,states,(hurricane['Start'],hurricane['End']+1)))
                    record['Value'] = record['Value'].replace('%s-evacuate' % (name),'evacuate')
                    record['Value'] = record['Value'].replace('%s-moveTo-%s' % (name,agent.demographics['home']),'go home')
                output.append(record)

        if not cmd['debug']:
            accessibility.writeOutput(args,output,accessibility.fields['RunData'],'RunDataTable.tsv',
                os.path.join(os.path.dirname(__file__),'Instances','Instance%d' % (instance),'Runs','run-0'))
    if not cmd['debug']:
        accessibility.writeVarDef(os.path.dirname(__file__),list(variables.values()))
