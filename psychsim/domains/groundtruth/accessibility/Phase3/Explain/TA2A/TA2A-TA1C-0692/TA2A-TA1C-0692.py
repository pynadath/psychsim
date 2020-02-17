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
    random.seed(reqNum)
    team = os.path.splitext(os.path.basename(__file__))[0].split('-')[0]
    parser = ArgumentParser()
    parser.add_argument('-d','--debug',action='store_true',help='Run without writing any files')
    cmd = vars(parser.parse_args())
    demos = ['Gender','Children','Religion','Ethnicity','Residence']
    variables = {field: accessibility.boilerDict[field] for field in demos}
    for instance,args in accessibility.instanceArgs('Phase3'):
        print('Instance %d (%d,%d)' % (instance,args['instance'],args['run']))
        logging.info('Instance %d (%d,%d)' % (instance,args['instance'],args['run']))
        config = accessibility.getConfig(args['instance'])
        world = accessibility.unpickle(instance)
        states = {}
        actors = {name for name in world.agents if name[:5] == 'Actor'}
        output = []
        participants = {}

        for t in range(1,args['span']):
            evacuees = []
            for name in list(actors):
                try:
                    if accessibility.getAction(args,name,world,states,t)['verb'] == 'evacuate':
                        evacuees.append(name)
                except KeyError:
                    # Dead. So dead.
                    actors.remove(name)
            for name in evacuees:
                try:
                    partID = participants[name]
                except KeyError:
                    partID = participants[name] = len(participants)+1
                logging.info('Participant %d: %s' % (partID,name))
                agent = world.agents[name]
                root = {'Timestep': t,'EntityIdx': '%s %d Participant %d' % (team,reqNum,partID)}
                values = accessibility.getCurrentDemographics(args,name,world,states,config)
                for var in demos:
                    record = dict(root)
                    record['VariableName'] = var
                    record['Value'] = values[var]
                    output.append(record)

                var = '%s %d Forced Evacuation' % (team,reqNum)
                if var not in variables:
                    variables[var] = {'Name': var,'Values':'[0-7]','DataType': 'Integer','Notes': 'Q6a'}
                record = dict(root)
                record['VariableName'] = var
                record['Value'] = 0
                output.append(record)

                var = '%s %d Evacuation Subsidized' % (team,reqNum)
                if var not in variables:
                    variables[var] = {'Name': var,'Values':'[0-7],Not Applicable','DataType': 'String','Notes': 'Q6c'}
                record = dict(root)
                record['VariableName'] = var
                record['Value'] = 'Not Applicable'
                output.append(record)

                var = '%s %d Region Familiarity' % (team,reqNum)
                if var not in variables:
                    variables[var] = {'Name': var,'Values':'[0-7]','DataType': 'Integer','Notes': 'Q6d'}
                record = dict(root)
                record['VariableName'] = var
                record['Value'] = 7
                output.append(record)

                var = '%s %d Known Individuals' % (team,reqNum)
                if var not in variables:
                    variables[var] = {'Name': var,'Values':'[0+]','DataType': 'Integer','Notes': 'Q6e'}
                record = dict(root)
                record['VariableName'] = var
                record['Value'] = len([other for other in agent.getNeighbors() if other in states[t]['Actor']])
                output.append(record)

            states.clear()

        if not cmd['debug']:
            accessibility.writeOutput(args,output,accessibility.fields['RunData'],'RunDataTable.tsv',
                os.path.join(os.path.dirname(__file__),'Instances','Instance%d' % (instance),'Runs','run-0'))
    if not cmd['debug']:
        accessibility.writeVarDef(os.path.dirname(__file__),list(variables.values()))
