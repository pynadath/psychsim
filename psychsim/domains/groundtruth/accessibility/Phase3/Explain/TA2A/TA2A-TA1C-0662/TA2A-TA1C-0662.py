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
        severity = accessibility.likert[5][config.getint('Actors','antiresources_benefit')-1]
        world = accessibility.unpickle(instance)
        hurricanes = [h for h in accessibility.readHurricanes(args['instance'],args['run']) if h['End'] <= args['span']]
        states = {}
        accessibility.loadState(args,states,args['span']-1,'Nature',world)
        actors = {name for name in world.agents if name[:5] == 'Actor' and stateKey(name,'health') in world.state}
        sample = random.sample(actors,len(actors)//5)

        crimes = {name: 0 for name in sample}
        locations = {name: {} for name in sample}
        for t in range(1,args['span']):
            for name in crimes:
                action = accessibility.getAction(args,name,world,states,t)
                if action['verb'] == 'takeResources':
                    crimes[name] += 1
            states.clear()

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

            var = '%s %d Aid Willingness Wealth > 1' % (team,reqNum)
            if var not in variables:
                variables[var] = {'Name': var,'Values':'[0-7]','DataType': 'Integer','Notes': 'Q5'}
            record = dict(root)
            record['VariableName'] = var
            record['Value'] = aidWillingness(world,name,lambda a: a.getState('resources',unique=True) >= 1/4)
            output.append(record)

            var = '%s %d Most Take Advantage' % (team,reqNum)
            if var not in variables:
                variables[var] = {'Name': var,'Values':'[0-7]','DataType': 'Integer','Notes': 'Q6'}
            record = dict(root)
            record['VariableName'] = var
            net = 0
            for hurricane in hurricanes:
                for other in agent.getNeighbors():
                    actions = set([act['verb'] for act in accessibility.getAction(args,other,world,states,(hurricane['Start'],hurricane['End']+1))])
                    if 'decreaseRisk' in actions:
                        net -= 1
                    if 'takeResources' in actions:
                        net += 1
                states.clear()
            value = net/(len(agent.getNeighbors())*len(hurricanes)) + 0.5
            record['Value'] = min(int(value*8),7)
            output.append(record)

            var = '%s %d People Can Be Trusted' % (team,reqNum)
            if var not in variables:
                variables[var] = {'Name': var,'Values':'[0-7]','DataType': 'Integer','Notes': 'Q7'}
            record = dict(root)
            record['VariableName'] = var
            config = accessibility.getConfig(args['instance'])
            trust = {'over': config.getint('Actors','friend_opt_trust'),
                'under': config.getint('Actors','friend_pess_trust')}
            trust['none'] = (trust['over']+trust['under'])/2
            if agent.getFriends():
                value = sum([trust[world.agents[friend].distortion] for friend in agent.getFriends()])/len(agent.getFriends())/5
            else:
                value = 0.5
            record['Value'] = min(int(value*8),7)
            output.append(record)

            var = '%s %d Crimes' % (team,reqNum)
            if var not in variables:
                variables[var] = {'Name': var,'Values':'[0+]','DataType': 'Integer','Notes': 'Q8'}
            record = dict(root)
            record['VariableName'] = var
            record['Value'] = crimes[name]
            output.append(record)

            var = '%s %d Crime Severity' % (team,reqNum)
            if var not in variables:
                variables[var] = {'Name': var,'Values':'[0+]','DataType': 'Integer','Notes': 'Q9'}
            record = dict(root)
            record['VariableName'] = var
            record['Value'] = min(int(severity*8),7) if crimes[name] > 0 else 0
            output.append(record)

        if not cmd['debug']:
            accessibility.writeOutput(args,output,accessibility.fields['RunData'],'RunDataTable.tsv',
                os.path.join(os.path.dirname(__file__),'Instances','Instance%d' % (instance),'Runs','run-0'))
    if not cmd['debug']:
        accessibility.writeVarDef(os.path.dirname(__file__),list(variables.values()))
