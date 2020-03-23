from argparse import ArgumentParser
import logging
import os.path
import random
import sys

from psychsim.pwl import *
from psychsim.domains.groundtruth import accessibility
from psychsim.domains.groundtruth.simulation.region import Region
from psychsim.domains.groundtruth.simulation import survey

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO,filename='%s%s' % (os.path.splitext(__file__)[0],'.log'))
    reqNum = int(os.path.splitext(os.path.basename(__file__))[0].split('-')[2])
    random.seed(reqNum)
    team = os.path.splitext(os.path.basename(__file__))[0].split('-')[0]
    parser = ArgumentParser()
    parser.add_argument('-d','--debug',action='store_true',help='Run without writing any files')
    cmd = vars(parser.parse_args())
    demos = ['Gender','Children','Religion','Ethnicity']
    variables = {field: accessibility.boilerDict[field] for field in demos}
    for instance,args in accessibility.instanceArgs('Phase3','Explain'):
        print('Instance %d (%d,%d)' % (instance,args['instance'],args['run']))
        logging.info('Instance %d (%d,%d)' % (instance,args['instance'],args['run']))
        config = accessibility.getConfig(args['instance'])
        world = accessibility.unpickle(instance)
        hurricanes = [h for h in accessibility.readHurricanes(args['instance'],args['run']) if h['End'] <= args['span']]
        states = {}
        actors = {name for name in world.agents if name[:5] == 'Actor'}
        output = []
        participants = {}

        for h in hurricanes:
            actions = {}
            for name in list(actors):
                try:
                    actions[name] = {act for act in accessibility.getAction(args,name,world,states,(h['Start'],h['End']+1)) 
                        if act['verb'] == 'decreaseRisk'}
                except KeyError:
                    logging.info('%s died before the end of hurricane %d' % (name,h['Hurricane']))
                    actors.remove(name)

            living = list(actors)
            random.shuffle(living)
            for name in living:
                try:
                    partID = participants[name]
                except KeyError:
                    partID = participants[name] = len(participants)+1
                logging.info('Participant %d: %s' % (partID,name))
                t = h['End'] + 1
                root = {'Timestep': t,'EntityIdx': '%s %d Participant %d' % (team,reqNum,partID)}

                values = accessibility.getCurrentDemographics(args,name,world,states,config)
                for var in demos:
                    record = dict(root)
                    record['VariableName'] = var
                    record['Value'] = values[var]
                    output.append(record)

                var = '%s %d Number Aided' % (team,reqNum)
                if var not in variables:
                    variables[var] = {'Name': var,'Values':'[0+],unknown','DataType': 'Integer','Notes': 'Q5'}
                record = dict(root)
                record['VariableName'] = var
                record['Value'] = 'unknown' if actions[name] else '0'
                output.append(record)

            states.clear()

        if not cmd['debug']:
            accessibility.writeOutput(args,output,accessibility.fields['RunData'],'RunDataTable.tsv',
                os.path.join(os.path.dirname(__file__),'Instances','Instance%d' % (instance),'Runs','run-0'))
    if not cmd['debug']:
        accessibility.writeVarDef(os.path.dirname(__file__),list(variables.values()))
