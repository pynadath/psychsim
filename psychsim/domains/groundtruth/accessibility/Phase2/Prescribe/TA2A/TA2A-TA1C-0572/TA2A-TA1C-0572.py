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
    parser.add_argument('-1',action='store_true',help='Run Condition 1 only')
    reqNum = int(os.path.splitext(os.path.basename(__file__))[0].split('-')[2])
    team = os.path.splitext(os.path.basename(__file__))[0].split('-')[0]
    random.seed(reqNum)
    cmd = vars(parser.parse_args())
    variables = {}
    for instance,args in accessibility.instanceArgs('Phase2'):
        print('Instance %d (%d,%d)' % (instance,args['instance'],args['run']))
        logging.info('Instance %d (%d,%d)' % (instance,args['instance'],args['run']))
        config = accessibility.getConfig(args['instance'])
        states = {}
        # Load world
        world = accessibility.unpickle(instance)
        accessibility.loadState(args,states,args['span']-1,'Nature',world)
        actors = [name for name in world.agents if name[:5] == 'Actor' and world.getState(name,'alive').first()]
        shelters = [name for name in world.agents if name[:6] == 'Region' and stateKey(name,'shelterRisk') in world.variables]
        sample = random.sample(actors,len(actors)//5)
        output = []
        partID = 0
        for name in sample:
            partID += 1
            agent = world.agents[name]
            logging.info('Participant %d: %s' % (partID,name))

            root = {'Timestep': args['span'],'EntityIdx': '%s %d Participant %d' % (team,reqNum,partID)}

            var = '%s %d Wealth' % (team,reqNum)
            if var not in variables:
                variables[var] = {'Name': var,'Values':'[1-7]','DataType': 'Integer','Notes': 'Q3'}
            record = dict(root)
            record['VariableName'] = var
            record['Value'] = accessibility.toLikert(float(accessibility.getInitialState(args,name,'resources',world,states,args['span'])),7)
            output.append(record)

            var = '%s %d Shelter Condition' % (team,reqNum)
            if var not in variables:
                variables[var] = {'Name': var,'Values':'[1-7]','DataType': 'Integer','Notes': 'Q4'}
            record = dict(root)
            record['VariableName'] = var
            beliefs = states[args['span']-1]['Nature'][name]
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
