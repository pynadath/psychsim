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
    variables = {}
    for instance,args in accessibility.instanceArgs('Phase2'):
        print('Instance %d (%d,%d)' % (instance,args['instance'],args['run']))
        logging.info('Instance %d (%d,%d)' % (instance,args['instance'],args['run']))
        challenge = accessibility.instanceChallenge(instance)
        config = accessibility.getConfig(args['instance'])
        world = accessibility.unpickle(instance)
        states = {}
        accessibility.loadState(args,states,args['span']-1,'Nature',world)
        hurricanes = [h for h in accessibility.readHurricanes(args['instance'],args['run']) if h['End'] <= args['span']]
        if challenge[1] == 'Explain':
            target = []
        else:
            target = [accessibility.getTarget(args['instance'],args['run'],world)]
        actors = {name for name in world.agents if name[:5] == 'Actor' and world.getState(name,'alive').first()}
        sample = target+random.sample(actors-set(target),len(actors)//5-len(target))
        output = []
        for hurricane in hurricanes:
            aid = [act['object'] for act in accessibility.getAction(args,'System',world,states,(hurricane['Start'],hurricane['End']))]
            prefix = '%s %d Hurricane %d' % (team,reqNum,hurricane['Hurricane'])
            for partID in range(len(sample)):
                name = sample[partID]
                if name in target:
                    logging.info('Target: %s' % (name))
                    root = {'Timestep': hurricane['End'],'EntityIdx': 'TargetActor'}
                else:
                    if sample[0] in target:
                        root = {'Timestep': hurricane['End'],'EntityIdx': '%s %d Participant %d' % (team,reqNum,partID)}
                        logging.info('Participant %d: %s' % (partID,name))
                    else:
                        root = {'Timestep': hurricane['End'],'EntityIdx': '%s %d Participant %d' % (team,reqNum,partID+1)}
                        logging.info('Participant %d: %s' % (partID+1,name))
                agent = world.agents[name]

                # Q1
                var = '%s Maximum Category' % (prefix)
                if var not in variables:
                    variables[var] = {'Name': var,'Values': '[1-5]', 'DataType': 'Integer','Notes': 'Q1'}
                record = dict(root)
                record['VariableName'] = var
                belief = accessibility.getInitialState(args,'Nature','category',world,states,hurricane['Landfall'],name)
                record['Value'] = max(belief.domain())
                output.append(record)

                # Q2
                locations = [dist.first() for dist in accessibility.getInitialState(args,name,'location',world,states,
                    (hurricane['Start'],hurricane['End']+1))]
                var = '%s Days at Shelter' % (prefix)
                if var not in variables:
                    variables[var] = {'Name': var,'Values':'[0+]','DataType': 'Integer','Notes': 'Q2'}
                record = dict(root)
                record['VariableName'] = var
                sheltered = len([loc for loc in locations if loc[:7] == 'shelter'])
                record['Value'] = sheltered
                output.append(record)

                # Q3
                var = '%s Days Evacuated' % (prefix)
                if var not in variables:
                    variables[var] = {'Name': var,'Values':'[0+]','DataType': 'Integer','Notes': 'Q3'}
                record = dict(root)
                record['VariableName'] = var
                evacuated = locations.count('evacuated')
                record['Value'] = evacuated
                output.append(record)

                # Q4
                health = [dist.expectation() for dist in accessibility.getInitialState(args,name,'health',world,states,
                    (hurricane['Start'],hurricane['End']+1))]
                var = '%s Injuries' % (prefix)
                if var not in variables:
                    variables[var] = {'Name': var,'Values':'none,self,dependents,selfplusdependents','DataType': 'String','Notes': 'Q4'}
                record = dict(root)
                record['VariableName'] = var
                record['Value'] = 'self' if min(health) < 0.2 else 'none'
                if stateKey(name,'childrenHealth') in world.variables:
                    health = [dist.first() for dist in accessibility.getInitialState(args,name,'childrenHealth',world,states,
                        (hurricane['Start'],hurricane['End']+1))]
                    if min(health) < 0.2:
                        if record['Value'] == 'none':
                            record['Value'] = 'dependents'
                        else:
                            record['Value'] += 'plusdependents'
                output.append(record)

                # Q5
                var = '%s Risk' % (prefix)
                if var not in variables:
                    variables[var] = {'Name': var,'Values':'[1-7]','DataType': 'Integer','Notes': 'Q5'}
                risk = [dist.expectation() for dist in accessibility.getInitialState(args,name,'risk',world,states,
                    (hurricane['Start'],hurricane['End']+1),name)]
                record = dict(root)
                record['VariableName'] = var
                record['Value'] = accessibility.toLikert(max(risk),7)
                output.append(record)
            
                # Q6
                var = '%s Wealth' % (prefix)
                if var not in variables:
                    variables[var] = {'Name': var,'Values':'[1-7]','DataType': 'Integer','Notes': 'Q6'}
                record = dict(root)
                record['VariableName'] = var
                record['Value'] = accessibility.toLikert(accessibility.getInitialState(args,name,'resources',world,states,hurricane['End']).expectation(),7)
                output.append(record)

                # Q7
                var = '%s Property Damage' % (prefix)
                if var not in variables:
                    variables[var] = {'Name': var,'Values':'[1-7]','DataType': 'Integer','Notes': 'Q7'}
                risk = [dist.expectation() for dist in accessibility.getInitialState(args,agent.demographics['home'],'risk',world,states,
                    (hurricane['Start'],hurricane['End']+1),name)]
                record = dict(root)
                record['VariableName'] = var
                record['Value'] = accessibility.toLikert(max(risk),7)
                output.append(record)

                # Q8
                var = '%s Government Assistance' % (prefix)
                if var not in variables:
                    variables[var] = {'Name': var,'Values':'[1-7]','DataType': 'Integer','Notes': 'Q8'}
                record = dict(root)
                record['VariableName'] = var
                record['Value'] = accessibility.toLikert(aid.count(agent.demographics['home'])/len(aid),7)
                output.append(record)

                # Q9                
                friends = agent.getFriends()
                var = '%s Friends Evacuated' % (prefix)
                if var not in variables:
                    variables[var] = {'Name': var,'Values':'[0+]','DataType': 'Integer','Notes': 'Q9'}
                record = dict(root)
                record['VariableName'] = var
                record['Value'] = 0
                output.append(record)

                # Q10 
                var = '%s Friends Sheltered' % (prefix)
                if var not in variables:
                    variables[var] = {'Name': var,'Values':'[0+]','DataType': 'Integer','Notes': 'Q10'}
                record = dict(root)
                record['VariableName'] = var
                record['Value'] = 0
                output.append(record)
                for friend in friends:
                    locations = {dist.first() for dist in accessibility.getInitialState(args,name,'location',world,states,
                        (hurricane['Start'],hurricane['End']+1))}
                    for loc in locations:
                        if loc[:7] == 'shelter':
                            output[-1]['Value'] += 1
                        elif loc == 'evacuated':
                            output[-2]['Value'] += 1

            states.clear()
        if not cmd['debug']:
            accessibility.writeOutput(args,output,accessibility.fields['RunData'],'RunDataTable.tsv',
                os.path.join(os.path.dirname(__file__),'Instances','Instance%d' % (instance),'Runs','run-0'))
    if not cmd['debug']:
        accessibility.writeVarDef(os.path.dirname(__file__),list(variables.values()))
