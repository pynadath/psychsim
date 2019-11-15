from argparse import ArgumentParser
import logging
import os.path
import pickle
import random
import sys

from psychsim.pwl import *
from psychsim.domains.groundtruth import accessibility
from psychsim.domains.groundtruth.simulation.execute import fastForward

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO,filename='%s%s' % (os.path.splitext(__file__)[0],'.log'))
    parser = ArgumentParser()
    parser.add_argument('-d','--debug',action='store_true',help='Run without writing any files')
    reqNum = int(os.path.splitext(os.path.basename(__file__))[0].split('-')[2])
    team = os.path.splitext(os.path.basename(__file__))[0].split('-')[0]
    random.seed(reqNum)
    cmd = vars(parser.parse_args())
    variables = {}
    for instance,args in accessibility.instanceArgs('Phase2'):
        print('Instance %d (%d,%d)' % (instance,args['instance'],args['run']))
        logging.info('Instance %d (%d,%d)' % (instance,args['instance'],args['run']))
        challenge = accessibility.instanceChallenge(instance)[1]
        config = accessibility.getConfig(args['instance'])
        states = {}
        world = accessibility.unpickle(instance)
        regions = {name for name in world.agents if name[:6] == 'Region'}
        output = []
        aid = accessibility.getAid(args,world,states,(1,args['span']))
        for t in range(1,args['span']):
            entry = {'Timestep': t}
            for region in regions:
                var = '%s %d Tax' % (team,reqNum)
                if var not in variables:
                    variables[var] = {'Name': var,'Values':'[0-6]','DataType': 'Integer'}
                record = dict(entry)
                record['EntityIdx'] = region
                record['VariableName'] = var
                record['Value'] = 0
                output.append(record)

                var = '%s %d Aid Sent' % (team,reqNum)
                if var not in variables:
                    variables[var] = {'Name': var,'Values':'[0-6]','DataType': 'Integer'}
                record = dict(entry)
                record['EntityIdx'] = region
                record['VariableName'] = var
                record['Value'] = 3 if aid[t] == region else 0
                output.append(record)

        if not cmd['debug']:
            accessibility.writeOutput(args,output,accessibility.fields['RunData'],'RunDataTable.tsv',
                os.path.join(os.path.dirname(__file__),'Instances','Instance%d' % (instance),'Runs','run-0'))
    if not cmd['debug']:
        accessibility.writeVarDef(os.path.dirname(__file__),list(variables.values()))
