from argparse import ArgumentParser
import logging
import os.path
import random
import sys

from psychsim.pwl import *
from psychsim.domains.groundtruth import accessibility
from psychsim.domains.groundtruth.simulation import survey

def aidWillingness(world,name,inGroupTest):
    denom = sum(world.agents[name].Rweights.values())
    altruism = world.agents[name].Rweights['neighbors']/denom
    value = altruism*len([other for other in world.agents[name].getNeighbors() if inGroupTest(world.agents[other])])
    if inGroupTest(world.agents[name]):
        value += world.agents[name].Rweights['health']/denom
    return min(int(value*8),7)

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
        accessibility.loadState(args,states,args['span']-1,'Nature',world)
        actors = {name for name in world.agents if name[:5] == 'Actor' and stateKey(name,'health') in world.state}
        sample = random.sample(actors,len(actors)//5)

        output = []
        for partID in range(len(sample)):
            name = sample[partID]
            logging.info('Participant %d: %s' % (partID+1,name))
            agent = world.agents[name]

            root = {'Timestep': args['span'],'EntityIdx': '%s %d Participant %d' % (team,reqNum,partID+1)}

            values = accessibility.getCurrentDemographics(args,name,world,states,config)
            for var in demos:
                record = dict(root)
                record['VariableName'] = var
                record['Value'] = values[var]
                output.append(record)

            var = '%s %d Aid Willingness Children' % (team,reqNum)
            if var not in variables:
                variables[var] = {'Name': var,'Values':'[0-7]','DataType': 'Integer','Notes': 'Q5'}
            record = dict(root)
            record['VariableName'] = var
            record['Value'] = aidWillingness(world,name,lambda a: a.demographics['kids'] > 0)
            output.append(record)

            var = '%s %d Aid Willingness No Children' % (team,reqNum)
            if var not in variables:
                variables[var] = {'Name': var,'Values':'[0-7]','DataType': 'Integer','Notes': 'Q6'}
            record = dict(root)
            record['VariableName'] = var
            record['Value'] = aidWillingness(world,name,lambda a: a.demographics['kids'] == 0)
            output.append(record)

            var = '%s %d Aid Willingness Male' % (team,reqNum)
            if var not in variables:
                variables[var] = {'Name': var,'Values':'[0-7]','DataType': 'Integer','Notes': 'Q7'}
            record = dict(root)
            record['VariableName'] = var
            record['Value'] = aidWillingness(world,name,lambda a: a.demographics['gender'] == 'male')
            output.append(record)

            var = '%s %d Aid Willingness Female' % (team,reqNum)
            if var not in variables:
                variables[var] = {'Name': var,'Values':'[0-7]','DataType': 'Integer','Notes': 'Q8'}
            record = dict(root)
            record['VariableName'] = var
            record['Value'] = aidWillingness(world,name,lambda a: a.demographics['gender'] == 'female')
            output.append(record)

            var = '%s %d Aid Willingness Minority Religion' % (team,reqNum)
            if var not in variables:
                variables[var] = {'Name': var,'Values':'[0-7]','DataType': 'Integer','Notes': 'Q9'}
            record = dict(root)
            record['VariableName'] = var
            record['Value'] = aidWillingness(world,name,lambda a: a.demographics['religion'] == 'minority')
            output.append(record)

            var = '%s %d Aid Willingness Majority Religion' % (team,reqNum)
            if var not in variables:
                variables[var] = {'Name': var,'Values':'[0-7]','DataType': 'Integer','Notes': 'Q10'}
            record = dict(root)
            record['VariableName'] = var
            record['Value'] = aidWillingness(world,name,lambda a: a.demographics['religion'] == 'majority')
            output.append(record)

        if not cmd['debug']:
            accessibility.writeOutput(args,output,accessibility.fields['RunData'],'RunDataTable.tsv',
                os.path.join(os.path.dirname(__file__),'Instances','Instance%d' % (instance),'Runs','run-0'))
    if not cmd['debug']:
        accessibility.writeVarDef(os.path.dirname(__file__),list(variables.values()))
