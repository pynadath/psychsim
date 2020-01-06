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
    demoFields = {'Age','Children','Pets','Fulltime Job','Wealth'}
    variables = {field: variable for field,variable in accessibility.boilerDict.items() if field in demoFields}
    for instance,args in accessibility.instanceArgs('Phase2','Prescribe'):
        print('Instance %d (%d,%d)' % (instance,args['instance'],args['run']))
        logging.info('Instance %d (%d,%d)' % (instance,args['instance'],args['run']))
        config = accessibility.getConfig(args['instance'])
        states = {}
        # Load world
        world = accessibility.unpickle(instance)
        hurricanes = [h for h in accessibility.readHurricanes(args['instance'],args['run']) if h['End'] <= args['span']]
        actors = [name for name in world.agents if name[:5] == 'Actor']
        shelterTimes = {}
        pool = {}
        for hurricane in hurricanes:
            for t in range(hurricane['Start'],hurricane['End']):
                for name in actors:
                    action = accessibility.getAction(args,name,world,states,t)
                    if action['verb'] == 'moveTo' and action['object'][:7] == 'shelter':
                        try:
                            pool[action['object']].add(name)
                        except KeyError:
                            pool[action['object']] = {name}
                        if name not in shelterTimes:
                            shelterTimes[name] = {}
                        if action['object'] not in shelterTimes[name]:
                            shelterTimes[name][action['object']] = []
                        shelterTimes[name][action['object']].append((hurricane['Hurricane'],t))
        output = []
        partID = 0
        for shelter,people in pool.items():
            sample = random.sample(people,len(people)//5)
            for name in sample:
                partID += 1
                agent = world.agents[name]
                demos = accessibility.getCurrentDemographics(args,name,world,states,config)
                h,t = random.choice(shelterTimes[name][shelter])
                logging.info('Participant %d: %s entered %s at time %d (hurricane %d)' % (partID,name,shelter,t,h))
                root = {'Timestep': 1,'EntityIdx': '%s %d Participant %d' % (team,reqNum,partID)}

                for field in ['Age','Children','Pets','Wealth']:
                    record = dict(root)
                    record['VariableName'] = field
                    record['Value'] = demos[field]
                    output.append(record)

                root['Timestep'] = t

                employed = accessibility.getInitialState(args,name,'employed',world,states,t).first()
                var = 'Fulltime Job'
                record = dict(root)
                record['VariableName'] = var
                record['Value'] = 'yes' if employed else 'no'
                output.append(record)

                var = '%s %d Allowed Entry' % (team,reqNum)
                if var not in variables:
                    variables[var] = {'Name': var,'Values': 'Region[01-16]:yes,no','DataType': 'String'}
                record = dict(root)
                record['VariableName'] = var
                record['Value'] = 'Region%02d:yes' % (int(shelter[7:]))
                output.append(record)

                var = '%s %d Income' % (team,reqNum)
                if var not in variables:
                    variables[var] = {'Name': var,'Values': '[1-7]', 'DataType': 'Integer'}
                record = dict(root)
                record['VariableName'] = var
                if employed:
                    record['Value'] = accessibility.toLikert(accessibility.likert[5][config.getint('Actors','job_impact')-1],7)
                else:
                    record['Value'] = 1
                output.append(record)

                health = accessibility.getInitialState(args,name,'health',world,states,t).expectation()
                var = '%s %d Injury Level' % (team,reqNum)
                if var not in variables:
                    variables[var] = {'Name': var,'Values': '[1-7]','DataType': 'Integer'}
                record = dict(root)
                record['VariableName'] = var
                record['Value'] = accessibility.toLikert(1-health,7)
                output.append(record)

                assert accessibility.getInitialState(args,name,'location',world,states,t+1).first()[:7] == 'shelter'
                belief = states[t]['Nature'][name]
                if isinstance(belief,dict):
                    model,belief = copy.deepcopy(next(iter(belief.items())))
                else:
                    belief = copy.deepcopy(belief)
                    model = world.getFeature(modelKey(name),states[t-1]['Nature']['__state__']).first()
                pEvac = []
                while world.getState('Nature','phase',belief).first() != 'none':
                    if name in world.next(belief):
                        # What am I considering?
                        V = {action: agent.value(belief,action,model,updateBeliefs=False)['__EV__'] for action in agent.getActions(belief)}
                        dist = Distribution(V,agent.getAttribute('rationality',model))
                        for action,prob in dist.items():
                            if action['verb'] == 'evacuate':
                                pEvac.append(prob)
                    world.step(state=belief,select='max',keySubset=belief.keys())
                var = '%s %d Anticipated Evacuation' % (team,reqNum)
                if var not in variables:
                    variables[var] = {'Name': var,'Values':'[1-7]','DataType': 'Integer'}
                record = dict(root)
                record['VariableName'] = var
                record['Value'] = accessibility.toLikert(max(pEvac),7)
                output.append(record)

                var = '%s %d Dissatisfaction Previous' % (team,reqNum)
                if var not in variables:
                    variables[var] = {'Name': var,'Values': '[1-7]','DataType': 'Integer'}
                record = dict(root)
                record['VariableName'] = var
                if hurricane['Hurricane'] > 1:
                    record['Value'] = accessibility.toLikert(accessibility.getInitialState(args,name,'grievance',world,states,
                        hurricanes[h-2]['End']).expectation(),7)
                else:
                    record['Value'] = 'N/A'
                output.append(record)

        if not cmd['debug']:
            accessibility.writeOutput(args,output,accessibility.fields['RunData'],'RunDataTable.tsv',
                os.path.join(os.path.dirname(__file__),'Instances','Instance%d' % (instance),'Runs','run-0'))
    if not cmd['debug']:
        accessibility.writeVarDef(os.path.dirname(__file__),list(variables.values()))
