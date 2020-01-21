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
    reqNum = int(os.path.splitext(os.path.basename(__file__))[0].split('-')[2])
    team = os.path.splitext(os.path.basename(__file__))[0].split('-')[0]
    random.seed(reqNum)
    cmd = vars(parser.parse_args())
    demos = {'Gender','Children','Religion','Ethnicity'}
    variables = {field: variable for field,variable in accessibility.boilerDict.items() if field in demos}
    for instance,args in accessibility.instanceArgs('Phase3','Explain'):
        print('Instance %d (%d,%d)' % (instance,args['instance'],args['run']))
        logging.info('Instance %d (%d,%d)' % (instance,args['instance'],args['run']))
        config = accessibility.getConfig(args['instance'])
        states = {}
        # Load world
        world = accessibility.unpickle(instance)
        regions = [name for name in world.agents if name[:6] == 'Region' and stateKey(name,'shelterRisk') in world.variables]
        shelters = {'shelter%d' % (int(name[-2:])) for name in regions}
        actors = [name for name in world.agents if name[:5] == 'Actor']
        outside = {name: set(actors) for name in shelters}
        inside = {name: set() for name in shelters}
        output = []
        entry = 0
        exit = 0
        for t in range(1,args['span']):
            for shelter in shelters:
                for name in list(inside[shelter]):
                    try:
                        action = accessibility.getAction(args,name,world,states,t)
                    except KeyError:
                        # He's dead Jim
                        inside[shelter].remove(name)
                        continue

                    if action['verb'] == 'evacuate' or (action['verb'] == 'moveTo' and action['object'] != shelter):
                        exit += 1
                        logging.info('Exiter %d: %s' % (exit,name))
                        root = {'Timestep': t,'EntityIdx': '%s %d Shelter Exit %d' % (team,reqNum,exit)}

                        var = '%s %d Shelter' % (team,reqNum)
                        if var not in variables:
                            variables[var] = {'Name': var,'Values':'Region[01-16]','DataType': 'String'}
                        record = dict(root)
                        record['VariableName'] = var
                        record['Value'] = 'Region%s' % (shelter[7:])
                        output.append(record)

                        values = accessibility.getCurrentDemographics(args,name,world,states,config,t)
                        for var in demos:
                            record = dict(root)
                            record['VariableName'] = var
                            record['Value'] = values[var]
                            output.append(record)

                        inside[shelter].remove(name)
                        outside[shelter].add(name)

            for shelter in shelters:
                for name in list(outside[shelter]):
                    try:
                        action = accessibility.getAction(args,name,world,states,t)
                    except KeyError:
                        # He's dead Jim
                        outside[shelter].remove(name)
                        continue

                    if action['verb'] == 'moveTo' and action['object'] == shelter:
                        entry += 1
                        logging.info('Enterer %d: %s' % (entry,name))
                        root = {'Timestep': t,'EntityIdx': '%s %d Shelter Entry %d' % (team,reqNum,entry)}

                        var = '%s %d Shelter' % (team,reqNum)
                        if var not in variables:
                            variables[var] = {'Name': var,'Values':'Region[01-16]','DataType': 'String'}
                        record = dict(root)
                        record['VariableName'] = var
                        record['Value'] = 'Region%s' % (shelter[7:])
                        output.append(record)

                        values = accessibility.getCurrentDemographics(args,name,world,states,config,t)
                        for var in demos:
                            record = dict(root)
                            record['VariableName'] = var
                            record['Value'] = values[var]
                            output.append(record)

                        inside[shelter].add(name)
                        outside[shelter].remove(name)
            if t > 1:
                del states[t-1]

        if not cmd['debug']:
            accessibility.writeOutput(args,output,accessibility.fields['RunData'],'RunDataTable.tsv',
                os.path.join(os.path.dirname(__file__),'Instances','Instance%d' % (instance),'Runs','run-0'))
    if not cmd['debug']:
        accessibility.writeVarDef(os.path.dirname(__file__),sorted(variables.values(),key=lambda v: v['Name']))
