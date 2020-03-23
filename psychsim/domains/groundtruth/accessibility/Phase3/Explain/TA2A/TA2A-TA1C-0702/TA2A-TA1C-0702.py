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
    demos = ['Gender','Children','Religion','Ethnicity']
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
            people = {'Evacuated': [], 'Sheltered': []}
            living = list(actors)
            random.shuffle(living)
            for name in living:
                try:
                    action = accessibility.getAction(args,name,world,states,t)
                except KeyError:
                    # Dead. So dead.
                    actors.remove(name)
                    continue
                if action['verb'] == 'evacuate':
                    people['Evacuated'].append(name)
                elif action['verb'] == 'moveTo' and action['object'][:7] == 'shelter':
                    people['Sheltered'].append(name)
            for behavior,folks in people.items():
                for name in folks:
                    # With other people?
                    agent = world.agents[name]
                    if agent.demographics['kids'] == 0:
                        if agent.spouse is None:
                            continue
                        else:
                            try:
                                action = accessibility.getAction(args,agent.spouse,world,states,t)
                            except KeyError:
                                continue
                    try:
                        partID = participants[name]
                    except KeyError:
                        partID = participants[name] = len(participants)+1
                    logging.info('Participant %d: %s' % (partID,name))
                    root = {'Timestep': t,'EntityIdx': '%s %d Participant %d' % (team,reqNum,partID)}
                    values = accessibility.getCurrentDemographics(args,name,world,states,config)
                    for var in demos:
                        record = dict(root)
                        record['VariableName'] = var
                        record['Value'] = values[var]
                        output.append(record)

                    var = '%s %d %s with Family' % (team,reqNum,behavior)
                    if var not in variables:
                        variables[var] = {'Name': var,'Values':'yes,no','DataType': 'Boolean','Notes': 'Q5a'}
                    record = dict(root)
                    record['VariableName'] = var
                    record['Value'] = 'yes'
                    output.append(record)

                    var = '%s %d %s with Friends' % (team,reqNum,behavior)
                    if var not in variables:
                        variables[var] = {'Name': var,'Values':'yes,no','DataType': 'Boolean','Notes': 'Q5b'}
                    record = dict(root)
                    record['VariableName'] = var
                    record['Value'] = 'no'
                    output.append(record)

                    var = '%s %d %s with Acquaintances' % (team,reqNum,behavior)
                    if var not in variables:
                        variables[var] = {'Name': var,'Values':'yes,no','DataType': 'Boolean','Notes': 'Q5c'}
                    record = dict(root)
                    record['VariableName'] = var
                    record['Value'] = 'no'
                    output.append(record)

            states.clear()

        if not cmd['debug']:
            accessibility.writeOutput(args,output,accessibility.fields['RunData'],'RunDataTable.tsv',
                os.path.join(os.path.dirname(__file__),'Instances','Instance%d' % (instance),'Runs','run-0'))
    if not cmd['debug']:
        accessibility.writeVarDef(os.path.dirname(__file__),list(variables.values()))
