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
    variables = dict(accessibility.boilerDict)
    deltas = {'wealth': 'resources','dissatisfaction': 'grievance','risk': 'risk','injury possibility': 'risk'}
    beliefs = {'risk','injury possibility'}
    for instance,args in accessibility.instanceArgs('Phase2','Predict'):
        print('Instance %d (%d,%d)' % (instance,args['instance'],args['run']))
        logging.info('Instance %d (%d,%d)' % (instance,args['instance'],args['run']))
        world = accessibility.unpickle(instance)
        states = {}
        accessibility.loadState(args,states,args['span']-1,'Nature',world)
        config = accessibility.getConfig(args['instance'])
        hurricanes = [h for h in accessibility.readHurricanes(args['instance'],args['run']) if h['End'] <= args['span']]
        actors = {name for name in world.agents if name[:5] == 'Actor' and world.getState(name,'alive').first()}
        sample = random.sample(actors,len(actors)//10)
        output = []
        for partID in range(len(sample)):
            name = sample[partID]
            logging.info('Participant %d: %s' % (partID+1,name))
            agent = world.agents[name]
            root = {'EntityIdx': '%s %d Participant %d' % (team,reqNum,partID+1)}
            old = {}
            for field,feature in deltas.items():
                if field in beliefs:
                    old[field] = accessibility.getInitialState(args,name,feature,world,states,hurricanes[-1]['Start']-1,name).expectation()
                else:
                    old[field] = accessibility.getInitialState(args,name,feature,world,states,hurricanes[-1]['Start']-1).expectation()

            for t in range(hurricanes[-1]['Start'],hurricanes[-1]['End']):
                for field,feature in deltas.items():
                    var = '%s %d %s Change' % (team,reqNum,field.capitalize())
                    if var not in variables:
                        variables[var] = {'Name': var,'Values':'[-5-5]','DataType': 'Integer'}
                    record = dict(root)
                    record['Timestep'] = t
                    record['VariableName'] = var
                    if field in beliefs:
                        value = accessibility.getInitialState(args,name,feature,world,states,t,name).expectation()
                    else:
                        value = accessibility.getInitialState(args,name,feature,world,states,t).expectation()
                    if value == old[field]:
                        record['Value'] = 0
                    else:
                        try:
                            delta = (value-old[field])/old[field]
                        except ZeroDivisionError:
                            delta = value
                        record['Value'] = accessibility.toLikert(abs(delta))
                        if delta < -1e-8:
                            record['Value'] *= -1
                    old[field] = value
                    output.append(record)

            var = '%s %d Aid If Wealth Loss' % (team,reqNum)
            if var not in variables:
                variables[var] = {'Name': var,'Values':'yes,no','DataType': 'Boolean'}
            record = dict(root)
            record['Timestep'] = args['span']
            record['VariableName'] = var
            record['Value'] = 'no' if accessibility.aidIfWealthLoss(agent) < 0.5 else 'yes'
            output.append(record)

            var = '%s %d Hurricane Vulnerability' % (team,reqNum)
            if var not in variables:
                variables[var] = {'Name': var,'Values':'yes,no','DataType': 'Boolean'}
            record = dict(root)
            record['Timestep'] = args['span']
            record['VariableName'] = var
            record['Value'] = 'yes'
            output.append(record)

            var = '%s %d Stay at Home Willingness' % (team,reqNum)
            if var not in variables:
                variables[var] = {'Name': var,'Values':'yes,no','DataType': 'Boolean'}
            record = dict(root)
            record['Timestep'] = args['span']
            record['VariableName'] = var
            record['Value'] = 'yes'
            output.append(record)

            wealth = [value.expectation() for value in accessibility.getInitialState(args,name,'resources',world,states,(1,args['span']))]
            delta = [wealth[t]-wealth[t-1] for t in range(1,len(wealth))]
            value = 'no' if min(delta) < 0. else 'NA'

            var = '%s %d Wealth Decrease Hurricane' % (team,reqNum)
            if var not in variables:
                variables[var] = {'Name': var,'Values':'yes,no','DataType': 'Boolean'}
            record = dict(root)
            record['Timestep'] = args['span']
            record['VariableName'] = var
            record['Value'] = value
            output.append(record)

            var = '%s %d Wealth Decrease Serious Injury' % (team,reqNum)
            if var not in variables:
                variables[var] = {'Name': var,'Values':'yes,no','DataType': 'Boolean'}
            record = dict(root)
            record['Timestep'] = args['span']
            record['VariableName'] = var
            record['Value'] = value
            output.append(record)

            var = '%s %d Wealth Decrease Minor Injury' % (team,reqNum)
            if var not in variables:
                variables[var] = {'Name': var,'Values':'yes,no','DataType': 'Boolean'}
            record = dict(root)
            record['Timestep'] = args['span']
            record['VariableName'] = var
            record['Value'] = value
            output.append(record)

        if not cmd['debug']:
            accessibility.writeOutput(args,output,accessibility.fields['RunData'],'RunDataTable.tsv',
                os.path.join(os.path.dirname(__file__),'Instances','Instance%d' % (instance),'Runs','run-0'))
    if not cmd['debug']:
        accessibility.writeVarDef(os.path.dirname(__file__),list(variables.values()))
