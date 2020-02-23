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
        hurricanes = [h for h in accessibility.readHurricanes(args['instance'],args['run']) if h['End'] <= args['span']]
        states = {}
        accessibility.loadState(args,states,args['span']-1,'Nature',world)
        actors = [name for name in world.agents if name[:5] == 'Actor' and stateKey(name,'health') in world.state]
        random.shuffle(actors)

        aid = {}
        beliefs = {name: {} for name in actors}
        for h in hurricanes:
            aid.update(accessibility.getAid(args,world,states,(h['Start'],h['End'])))
            for name in actors:
                beliefs[name][h['Hurricane']] = accessibility.getInitialState(args,'Nature','category',world,states,
                    (h['Start'],h['End']),name)
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

            var = '%s %d Different Relationship Strengths' % (team,reqNum)
            if var not in variables:
                variables[var] = {'Name': var,'Values':'yes,no','DataType': 'Boolean','Notes': 'Q6'}
            record = dict(root)
            record['VariableName'] = var
            record['Value'] = 'no'
            output.append(record)

            var = '%s %d Aid Willingness Family' % (team,reqNum)
            if var not in variables:
                variables[var] = {'Name': var,'Values':'[0-7]','DataType': 'Boolean','Notes': 'Q8a'}
            record = dict(root)
            record['VariableName'] = var
            record['Value'] = aidWillingness(world,name,lambda a: a.name == name or a.spouse == name)
            output.append(record)

            var = '%s %d Aid Willingness Friends' % (team,reqNum)
            if var not in variables:
                variables[var] = {'Name': var,'Values':'[0-7]','DataType': 'Boolean','Notes': 'Q8b'}
            record = dict(root)
            record['VariableName'] = var
            record['Value'] = aidWillingness(world,name,lambda a: name in a.getFriends())
            output.append(record)

            var = '%s %d Aid Willingness Acquaintances' % (team,reqNum)
            if var not in variables:
                variables[var] = {'Name': var,'Values':'[0-7]','DataType': 'Boolean','Notes': 'Q8c'}
            record = dict(root)
            record['VariableName'] = var
            record['Value'] = aidWillingness(world,name,lambda a: name in a.getNeighbors())
            output.append(record)
            for h in hurricanes:

                var = '%s %d Hurricane %d Severity' % (team,reqNum,h['Hurricane'])
                if var not in variables:
                    variables[var] = {'Name': var,'Values':'[1-5]','DataType': 'Integer','Notes': 'Q5'}
                record = dict(root)
                record['VariableName'] = var
                record['Value'] = int(round(max([value.expectation() for value in beliefs[name][h['Hurricane']]])))
                output.append(record)

                var = '%s %d Hurricane %d Aid Received' % (team,reqNum,h['Hurricane'])
                if var not in variables:
                    variables[var] = {'Name': var,'Values':'[1-5]','DataType': 'Integer','Notes': 'Q7'}
                record = dict(root)
                record['VariableName'] = var
                record['Value'] = accessibility.toLikert(len([t for t in range(h['Start'],h['End']) if aid[t] == agent.demographics['home']])
                    /(h['End']-h['Start']),7)
                output.append(record)

            states.clear()

        if not cmd['debug']:
            accessibility.writeOutput(args,output,accessibility.fields['RunData'],'RunDataTable.tsv',
                os.path.join(os.path.dirname(__file__),'Instances','Instance%d' % (instance),'Runs','run-0'))
    if not cmd['debug']:
        accessibility.writeVarDef(os.path.dirname(__file__),list(variables.values()))
