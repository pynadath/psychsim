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
    variables = dict(accessibility.boilerDict)
    for instance,args in accessibility.instanceArgs('Phase2','Prescribe'):
        print('Instance %d (%d,%d)' % (instance,args['instance'],args['run']))
        logging.info('Instance %d (%d,%d)' % (instance,args['instance'],args['run']))
        config = accessibility.getConfig(args['instance'])
        states = {}
        # Load world
        world = accessibility.unpickle(instance)
        accessibility.loadState(args,states,args['span'],'Nature',world)
        actors = [name for name in world.agents if name[:5] == 'Actor' and world.getState(name,'alive').first()]
        random.shuffle(actors)
        output = []
        for partID in range(len(actors)):
            name = actors[partID]
            logging.info('Participant %d: %s' % (partID+1,name))
            agent = world.agents[name]
            root = {'Timestep': args['span'],'EntityIdx': '%s %d Participant %d' % (team,reqNum,partID+1)}
            for field,value in accessibility.getCurrentDemographics(args,name,world,states,config).items():
                record = dict(root)
                record['VariableName'] = field
                record['Value'] = value
                output.append(record)

            health = accessibility.getInitialState(args,name,'health',world,states,(1,args['span']))
            var = '%s %d Days Injured' % (team,reqNum)
            if var not in variables:
                variables[var] = {'Name': var,'Values': '[0+]','DataType': 'Integer','Notes': 'Q10'}
            record = dict(root)
            record['VariableName'] = var
            record['Value'] = len([value for value in health if value.expectation()<0.2])
            output.append(record)

        if not cmd['debug']:
            accessibility.writeOutput(args,output,accessibility.fields['RunData'],'RunDataTable.tsv',
                os.path.join(os.path.dirname(__file__),'Instances','Instance%d' % (instance),'Runs','run-0'))
    if not cmd['debug']:
        accessibility.writeVarDef(os.path.dirname(__file__),list(variables.values()))
