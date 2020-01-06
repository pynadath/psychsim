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
    for instance,args in accessibility.instanceArgs('Phase2','Prescribe'):
        print('Instance %d (%d,%d)' % (instance,args['instance'],args['run']))
        logging.info('Instance %d (%d,%d)' % (instance,args['instance'],args['run']))
        config = accessibility.getConfig(args['instance'])
        states = {}
        # Load world
        world = accessibility.unpickle(instance)
        hurricanes = [h for h in accessibility.readHurricanes(args['instance'],args['run']) if h['End'] <= args['span']]
        actors = [name for name in world.agents if name[:5] == 'Actor']
        regions = [name for name in world.agents if name[:6] == 'Region']
        shelters = {'shelter%d' % (int(name[6:])) for name in regions if stateKey(name,'shelterRisk') in world.variables}
        output = []
        for hurricane in hurricanes:
            locations = {name: {loc.first() for loc in accessibility.getInitialState(args,name,'location',world,states,(hurricane['Start'],hurricane['End']))}
                for name in actors if accessibility.getInitialState(args,name,'alive',world,states,hurricane['Start']).first()}
            sheltered = {name for name in locations if locations[name] & shelters}
            evacuated = {name for name in locations if 'evacuated' in locations[name]}
            t = hurricane['End'] + 1
            for region in regions: 
                root = {'Timestep': t,'EntityIdx': '%s %d %s' % (team,reqNum,region)}

                var = '%s %d Evacuation Incentives' % (team,reqNum)
                if var not in variables:
                    variables[var] = {'Name': var,'Values': '[0+]','DataType': 'Integer'}
                record = dict(root)
                record['VariableName'] = var
                record['Value'] = 0
                output.append(record)

                var = '%s %d Sheltered' % (team,reqNum)
                if var not in variables:
                    variables[var] = {'Name': var,'Values': '[1-7]', 'DataType': 'Integer'}
                record = dict(root)
                record['VariableName'] = var
                record['Value'] = len([name for name in sheltered if world.agents[name].demographics['home'] == region])
                output.append(record)

        if not cmd['debug']:
            accessibility.writeOutput(args,output,accessibility.fields['RunData'],'RunDataTable.tsv',
                os.path.join(os.path.dirname(__file__),'Instances','Instance%d' % (instance),'Runs','run-0'))
    if not cmd['debug']:
        accessibility.writeVarDef(os.path.dirname(__file__),list(variables.values()))
