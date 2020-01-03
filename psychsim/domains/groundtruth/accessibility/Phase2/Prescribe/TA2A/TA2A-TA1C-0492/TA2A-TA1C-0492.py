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
    team = os.path.splitext(os.path.basename(__file__))[0].split('-')[0]
    parser = ArgumentParser()
    parser.add_argument('-d','--debug',action='store_true',help='Run without writing any files')
    cmd = vars(parser.parse_args())
    variables = {}
    for instance,args in accessibility.instanceArgs('Phase2','Prescribe'):
        print('Instance %d (%d,%d)' % (instance,args['instance'],args['run']))
        logging.info('Instance %d (%d,%d)' % (instance,args['instance'],args['run']))
        config = accessibility.getConfig(args['instance'])
        world = accessibility.unpickle(instance)
        regions = [name for name in world.agents if name[:6] == 'Region']
        states = {}
        accessibility.loadState(args,states,args['span']-1,'Nature',world)
        hurricanes = [h for h in accessibility.readHurricanes(args['instance'],args['run']) if h['End'] <= args['span']]
        output = []

        for hurricane in hurricanes:
            if hurricane['Hurricane'] < len(hurricanes):
                end = hurricanes[hurricane['Hurricane']]['Start']
            else:
                end = args['span']
            for t in range(hurricane['Start'],end):
                for region in regions:
                    var = '%s %d Building Damage Hurricane %d' % (team,reqNum,hurricane['Hurricane'])
                    if not var in variables:
                        variables[var] = {'Name': var,'Values': '[0-6]', 'DataType': 'Integer','Notes': 'Q1a'}
                    record = {'Timestep': t,'VariableName': var,'EntityIdx': region,
                        'Value': accessibility.toLikert(accessibility.getInitialState(args,region,'risk',world,states,t).expectation())-1}
                    output.append(record)

                    if stateKey(region,'shelterRisk') in world.variables:
                        var = '%s %d Shelter Damage Hurricane %d' % (team,reqNum,hurricane['Hurricane'])
                        if not var in variables:
                            variables[var] = {'Name': var,'Values': '[0-6]', 'DataType': 'Integer','Notes': 'Q1c'}
                        record = {'Timestep': t,'VariableName': var,'EntityIdx': region,
                            'Value': accessibility.toLikert(accessibility.getInitialState(args,region,'shelterRisk',world,states,t).expectation())-1}
                        output.append(record)

                        var = '%s %d Shelter Capacity Hurricane %d' % (team,reqNum,hurricane['Hurricane'])
                        if not var in variables:
                            variables[var] = {'Name': var,'Values': '[0-100]', 'DataType': 'Integer','Notes': 'Q1d'}
                        record = {'Timestep': t,'VariableName': var,'EntityIdx': region,
                            'Value': 100}
                        output.append(record)

        if not cmd['debug']:
            accessibility.writeOutput(args,output,accessibility.fields['RunData'],'RunDataTable.tsv',
                os.path.join(os.path.dirname(__file__),'Instances','Instance%d' % (instance),'Runs','run-0'))
    if not cmd['debug']:
        accessibility.writeVarDef(os.path.dirname(__file__),list(variables.values()))
