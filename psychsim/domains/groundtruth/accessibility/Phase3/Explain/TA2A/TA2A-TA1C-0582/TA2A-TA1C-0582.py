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
    for instance,args in accessibility.instanceArgs('Phase3','Explain'):
        print('Instance %d (%d,%d)' % (instance,args['instance'],args['run']))
        logging.info('Instance %d (%d,%d)' % (instance,args['instance'],args['run']))
        states = {}
        # Load world
        world = accessibility.unpickle(instance)
        regions = [name for name in world.agents if name[:6] == 'Region']
        hurricanes = [h for h in accessibility.readHurricanes(args['instance'],args['run']) if h['End'] <= args['span']]
        output = []
        for hurricane in hurricanes:
            for t in range(hurricane['Start'],hurricane['End']):
                target = accessibility.getAid(args,world,states,t)
                assert target is not None

                for region in regions:
                    var = '%s %d Aid Received Hurricane %d' % (team,reqNum,hurricane['Hurricane'])
                    if var not in variables:
                        variables[var] = {'Name': var,'Values':'[0-1]','DataType': 'Integer'}
                    record = {'Timestep': t,'EntityIdx': region,'VariableName': var,'Value': 1 if region == target else 0}
                    output.append(record)

        if not cmd['debug']:
            accessibility.writeOutput(args,output,accessibility.fields['RunData'],'RunDataTable.tsv',
                os.path.join(os.path.dirname(__file__),'Instances','Instance%d' % (instance),'Runs','run-0'))
    if not cmd['debug']:
        accessibility.writeVarDef(os.path.dirname(__file__),list(variables.values()))
