from argparse import ArgumentParser
import logging
import os.path
import random
import sys

from psychsim.pwl import *
from psychsim.domains.groundtruth import accessibility

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO,filename='%s%s' % (os.path.splitext(__file__)[0],'.log'))
    reqNum = int(os.path.splitext(os.path.basename(__file__))[0].split('-')[2])
    random.seed(reqNum)
    team = os.path.splitext(os.path.basename(__file__))[0].split('-')[0]
    parser = ArgumentParser()
    parser.add_argument('-d','--debug',action='store_true',help='Run without writing any files')
    cmd = vars(parser.parse_args())
    demos = ['Gender','Children','Religion','Ethnicity','Fulltime Job','Pets','Wealth','Residence']
    variables = {field: accessibility.boilerDict[field] for field in demos}
    for instance,args in accessibility.instanceArgs('Phase3'):
        print('Instance %d (%d,%d)' % (instance,args['instance'],args['run']))
        logging.info('Instance %d (%d,%d)' % (instance,args['instance'],args['run']))
        config = accessibility.getConfig(args['instance'])
        world = accessibility.unpickle(instance)
        states = {}
        accessibility.loadState(args,states,args['span']-1,'Nature',world)
        actors = [name for name in world.agents if name[:5] == 'Actor' and stateKey(name,'health') in world.state]
        random.shuffle(actors)

        locations = {name: {} for name in actors}
        actions = {name: {} for name in actors}
        for t in range(1,args['span']):
            for name in locations:
                locations[name][t] = accessibility.getInitialState(args,name,'location',world,states,t,unique=True)
            states.clear()

        output = []
        for partID in range(len(actors)):
            name = actors[partID]
            logging.info('Participant %d: %s' % (partID+1,name))
            agent = world.agents[name]

            root = {'Timestep': args['span'],'EntityIdx': '%s %d Participant %d' % (team,reqNum,partID+1)}

            values = accessibility.getCurrentDemographics(args,name,world,states,config)
            for var in demos:
                record = dict(root)
                record['VariableName'] = var
                record['Value'] = values[var]
                output.append(record)

            for t in range(1,args['span']):
                var = '%s %d Sheltered' % (team,reqNum)
                if var not in variables:
                    variables[var] = {'Name': var,'Values':'yes,no','DataType': 'Boolean','Notes': 'Q9'}
                record = dict(root)
                record['Timestep'] = t
                record['VariableName'] = var
                record['Value'] = 'yes' if locations[name][t][:7] == 'shelter' else 'no'
                output.append(record)

                var = '%s %d Evacuated' % (team,reqNum)
                if var not in variables:
                    variables[var] = {'Name': var,'Values':'yes,no','DataType': 'Boolean','Notes': 'Q10'}
                record = dict(root)
                record['Timestep'] = t
                record['VariableName'] = var
                record['Value'] = 'yes' if locations[name][t] == 'evacuated' else 'no'
                output.append(record)

        if not cmd['debug']:
            accessibility.writeOutput(args,output,accessibility.fields['RunData'],'RunDataTable.tsv',
                os.path.join(os.path.dirname(__file__),'Instances','Instance%d' % (instance),'Runs','run-0'))
    if not cmd['debug']:
        accessibility.writeVarDef(os.path.dirname(__file__),list(variables.values()))
