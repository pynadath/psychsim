from argparse import ArgumentParser
import logging
import os.path
import pickle
import random
import sys

from psychsim.pwl import *
from psychsim.domains.groundtruth import accessibility
from psychsim.domains.groundtruth.simulation import survey

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO,filename='%s%s' % (os.path.splitext(__file__)[0],'.log'))
    parser = ArgumentParser()
    parser.add_argument('-d','--debug',action='store_true',help='Run without writing any files')
    parser.add_argument('-1',action='store_true',help='Run Condition 1 only')
    reqNum = int(os.path.splitext(os.path.basename(__file__))[0].split('-')[2])
    team = os.path.splitext(os.path.basename(__file__))[0].split('-')[0]
    random.seed(reqNum)
    cmd = vars(parser.parse_args())
    prefix = '%s %d' % (team,reqNum)
    variables = {}
    for instance,args in accessibility.instanceArgs('Phase2','Predict'):
        print('Instance %d (%d,%d)' % (instance,args['instance'],args['run']))
        logging.info('Instance %d (%d,%d)' % (instance,args['instance'],args['run']))
        config = accessibility.getConfig(args['instance'])
        states = {}
        hurricanes = [h for h in accessibility.readHurricanes(args['instance'],args['run']) if h['End'] <= args['span']]
        world = accessibility.unpickle(instance)
        target = accessibility.getTarget(args['instance'],args['run'])
        name = target['Name']
        agent = world.agents[name]
        logging.info('Target: %s' % (name))
        output = []
        root = {'EntityIdx': target['EntityIdx']}
        for hurricane in hurricanes:

            # Postsurvey
            t = hurricane['End']
            root['Timestep'] = t

            # Q1
            var = '%s Satisfaction' % (prefix)
            if var not in variables:
                variables[var] = {'Name': var,'Values':'[1-7]','DataType': 'Integer'}
            record = dict(root)
            record['VariableName'] = var
            record['Value'] = 8-accessibility.toLikert(accessibility.getInitialState(args,name,'grievance',world,states,t).expectation(),7)
            output.append(record)

            # Q2
            locations = [dist.first() for dist in accessibility.getInitialState(args,name,'location',world,states,
                (hurricane['Start'],hurricane['End']+1))]
            var = '%s Days at Shelter' % (prefix)
            if var not in variables:
                variables[var] = {'Name': var,'Values':'[0+]','DataType': 'Integer'}
            record = dict(root)
            record['VariableName'] = var
            sheltered = len([loc for loc in locations if loc[:7] == 'shelter'])
            record['Value'] = sheltered
            output.append(record)

            # Q3
            var = '%s Days Evacuated' % (prefix)
            if var not in variables:
                variables[var] = {'Name': var,'Values':'[0+]','DataType': 'Integer'}
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
                variables[var] = {'Name': var,'Values':'none,self,dependents,selfplusdependents','DataType': 'String'}
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
                variables[var] = {'Name': var,'Values':'[1-7]','DataType': 'Integer'}
            risk = [dist.expectation() for dist in accessibility.getInitialState(args,name,'risk',world,states,
                (hurricane['Start'],hurricane['End']+1),name)]
            record = dict(root)
            record['VariableName'] = var
            record['Value'] = accessibility.toLikert(max(risk),7)
            output.append(record)
            
            # Q6
            var = '%s Wealth' % (prefix)
            if var not in variables:
                variables[var] = {'Name': var,'Values':'[1-7]','DataType': 'Integer'}
            record = dict(root)
            record['VariableName'] = var
            record['Value'] = accessibility.toLikert(accessibility.getInitialState(args,name,'resources',world,states,t).expectation(),7)
            output.append(record)

            # Q7
            var = '%s Property Damage' % (prefix)
            if var not in variables:
                variables[var] = {'Name': var,'Values':'[1-7]','DataType': 'Integer'}
            risk = [dist.expectation() for dist in accessibility.getInitialState(args,agent.demographics['home'],'risk',world,states,
                (hurricane['Start'],hurricane['End']+1),name)]
            record = dict(root)
            record['VariableName'] = var
            record['Value'] = accessibility.toLikert(max(risk),7)
            output.append(record)

            # Q8
            var = '%s Government Assistance' % (prefix)
            if var not in variables:
                variables[var] = {'Name': var,'Values':'[1-7]','DataType': 'Integer'}
            record = dict(root)
            record['VariableName'] = var
            aid = [act['object'] for act in accessibility.getAction(args,'System',world,states,(hurricane['Start'],hurricane['End']))]
            record['Value'] = accessibility.toLikert(aid.count(agent.demographics['home'])/len(aid),7)
            output.append(record)

            # Q9                
            friends = agent.getFriends()
            var = '%s Friends Evacuated' % (prefix)
            if var not in variables:
                variables[var] = {'Name': var,'Values':'[0+]','DataType': 'Integer'}
            record = dict(root)
            record['VariableName'] = var
            record['Value'] = 0
            output.append(record)

            # Q10 
            var = '%s Friends Sheltered' % (prefix)
            if var not in variables:
                variables[var] = {'Name': var,'Values':'[0+]','DataType': 'Integer'}
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

        if not cmd['debug']:
            accessibility.writeOutput(args,output,accessibility.fields['RunData'],'RunDataTable.tsv',
                os.path.join(os.path.dirname(__file__),'Instances','Instance%d' % (instance),'Runs','run-0'))
    if not cmd['debug']:
        accessibility.writeVarDef(os.path.dirname(__file__),list(variables.values()))
