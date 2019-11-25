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
    demos = {'Residence','Age','Gender','Ethnicity'}
    variables = {var: accessibility.boilerDict[var] for var in demos}
    for instance,args in accessibility.instanceArgs('Phase2'):
        print('Instance %d (%d,%d)' % (instance,args['instance'],args['run']))
        logging.info('Instance %d (%d,%d)' % (instance,args['instance'],args['run']))
        world = accessibility.unpickle(instance)
        size = sum([world.agents[name].demographics['kids']+1 for name in world.agents if name[:5] == 'Actor'])
        print(size)
        states = {}
        accessibility.loadState(args,states,args['span']-1,'Nature',world)
        config = accessibility.getConfig(args['instance'])
        hurricanes = [h for h in accessibility.readHurricanes(args['instance'],args['run']) if h['End'] <= args['span']]
        actors = {name for name in world.agents if name[:5] == 'Actor' and world.getState(name,'alive').first()}
        sample = random.sample(actors,len(actors)//10)
        output = []
        shelters = {}
        for name in actors:
            loc = accessibility.getInitialState(args,name,'location',world,states,args['span']).first()
            if loc[:7] == 'shelter':
                shelters[loc] = shelters.get(loc,set()) | {name}
        assert len(shelters) == 1,'Oh how lucky, this area has more than one shelter'
        for partID in range(len(sample)):
            name = sample[partID]
            logging.info('Participant %d: %s' % (partID+1,name))
            agent = world.agents[name]
            root = {'EntityIdx': '%s %d Participant %d' % (team,reqNum,partID+1)}
            for var,value in accessibility.getCurrentDemographics(args,name,world,states,config).items():
                if var in demos:
                    record = dict(root)
                    record['Timestep'] = args['span']
                    record['VariableName'] = var
                    record['Value'] = value
                    output.append(record)

            locations = [dist.first() for dist in accessibility.getInitialState(args,name,'location',world,states,(1,args['span']))]
            sheltered = locations[-1][:7] == 'shelter'

            var = '%s %d Ever Sheltered' % (team,reqNum)
            if var not in variables:
                variables[var] = {'Name': var,'Values':'yes,no','DataType': 'Boolean'}
            record = dict(root)
            record['Timestep'] = args['span']
            record['VariableName'] = var
            for loc in set(locations):
                if loc[:7] == 'shelter':
                    record['Value'] = 'yes'
                    break
            else:
                record['Value'] = 'no'
            output.append(record)

            var = '%s %d Stay at Home Willingness' % (team,reqNum)
            if var not in variables:
                variables[var] = {'Name': var,'Values':'yes,no','DataType': 'Boolean'}
            record = dict(root)
            record['Timestep'] = args['span']
            record['VariableName'] = var
            record['Value'] = 'yes'
            output.append(record)

            var = '%s %d Location' % (team,reqNum)
            if var not in variables:
                variables[var] = {'Name': var,'Values':'home,shelter,evacuated','DataType': 'String'}
            record = dict(root)
            record['Timestep'] = args['span']
            record['VariableName'] = var
            if sheltered:
                record['Value'] = 'shelter'
            elif locations[-1] == 'evacuated':
                record['Value'] = locations[-1]
            else:
                assert locations[-1] == agent.demographics['home']
                record['Value'] = 'home'
            output.append(record)

            var = '%s %d Number at Shelter' % (team,reqNum)
            if var not in variables:
                variables[var] = {'Name': var,'Values':'[1+],NA','DataType': 'Integer'}
            record = dict(root)
            record['Timestep'] = args['span']
            record['VariableName'] = var
            if sheltered:
                record['Value'] = sum([world.agents[name].demographics['kids']+1 for name in shelters[locations[-1]]])
            else:
                record['Value'] = 'NA'
            output.append(record)

            var = '%s %d Shelter Capacity' % (team,reqNum)
            if var not in variables:
                variables[var] = {'Name': var,'Values':'[0+]','DataType': 'Integer'}
            record = dict(root)
            record['Timestep'] = args['span']
            record['VariableName'] = var
            record['Value'] = size
            output.append(record)

        if not cmd['debug']:
            accessibility.writeOutput(args,output,accessibility.fields['RunData'],'RunDataTable.tsv',
                os.path.join(os.path.dirname(__file__),'Instances','Instance%d' % (instance),'Runs','run-0'))
    if not cmd['debug']:
        accessibility.writeVarDef(os.path.dirname(__file__),list(variables.values()))
