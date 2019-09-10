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
        world = accessibility.unpickle(instance)
        hurricanes = [h for h in accessibility.readHurricanes(args['instance'],args['run']) if h['End'] <= args['span']]
        output = []
        for t in range(1,args['span']):
            if not defined:
                variables.append({'Name': 'Timestep','Values': '[1+]','DataType': 'Integer'})
            record = {'Timestep': t}
            output.append(record)
            var = 'Aid Target'
            if not defined:
                variables.append({'Name': var,'Values': 'Region[01-16]','DataType': 'String'})
            record[var] = accessibility.getAction(args,'System',world,states,t)['object']
            if cmd['debug']:
                print(record)
            if not defined:
                if not cmd['debug']:
                    accessibility.writeVarDef(os.path.dirname(__file__),variables)
                defined = True
        if not cmd['debug']:
            accessibility.writeOutput(args,output,[var['Name'] for var in variables],'%s.tsv' % (os.path.splitext(os.path.basename(__file__))[0]),
                os.path.join(os.path.dirname(__file__),'Instances','Instance%d' % (instance),'Runs','run-0'))
