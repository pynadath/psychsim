from argparse import ArgumentParser
import logging
import os.path
import pickle
import random
import sys

from psychsim.pwl import *
from psychsim.domains.groundtruth import accessibility
from psychsim.domains.groundtruth.simulation.execute import fastForward

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO,filename='%s%s' % (os.path.splitext(__file__)[0],'.log'))
    parser = ArgumentParser()
    parser.add_argument('-d','--debug',action='store_true',help='Run without writing any files')
    cmd = vars(parser.parse_args())
    defined = False
    variables = []
    for instance,args in accessibility.instanceArgs('Phase2','Explain'):
        if cmd['debug']:
            print('Instance %d (%d,%d)' % (instance,args['instance'],args['run']))
        logging.info('Instance %d (%d,%d)' % (instance,args['instance'],args['run']))
        config = accessibility.getConfig(args['instance'])
        states = {}
        yearLength = config.getint('Disaster','year_length',fallback=365)
        day1 = (args['span']//yearLength + 1)*yearLength
        try:
            world = accessibility.unpickle(instance,day=day1)
        except FileNotFoundError:
            world = accessibility.unpickle(instance)
            accessibility.loadState(args,states,args['span']-1,'Nature',world)
            fastForward(world,config)
            day = world.getState(WORLD,'day').first()
            with open(os.path.join(accessibility.getDirectory(args),'scenario%d.pkl' % (day)),'wb') as outfile:
                pickle.dump(world,outfile)
        actors = {name for name in world.agents if name[:5] == 'Actor' and world.getState(name,'alive').first()}
        sample = random.sample(actors,5*len(actors)//100)
        output = []
        for partID in range(len(sample)):
            name = sample[partID]
            logging.info('Participant %d: %s' % (partID+1,name))
            agent = world.agents[name]
            print(accessibility.getAction(args,name,world,states,(1,args['span'])))
            history = accessibility.holoCane(world,name,config.getint('Disaster','season_length'))
            for step in range(0,len(history),3):
                record = {}
                output.append(record)
                var = 'Participant'
                if not defined:
                    variables.append({'Name': var,'Values':'[1+]','VarType': 'fixed','DataType': 'Integer'})
                record[var] = partID+1
                var = 'Group'
                if not defined:
                    variables.append({'Name': var,'Values':'[0-4]','VarType': 'fixed','DataType': 'Integer','Notes': 'Assigned condition'})
                record[var] = partID % 5
                var = 'Timestep'
                if not defined:
                    variables.append({'Name': var,'Values':'[1+]','DataType': 'Integer'})
                record[var] = day1+step//3+1
                if not defined:
                    variables += accessibility.boilerPlate
                record.update(accessibility.getCurrentDemographics(args,name,world,states,config))
                var = 'Location'
                if not defined:
                    variables.append({'Name': var,'Values':'evacuated,shelter,home','DataType': 'String'})
                assert len(world.getState(name,'location',history[step])) == 1
                record[var] = world.getState(name,'location',history[step]).first()
                if record[var][:7] == 'shelter':
                    record[var] = 'shelter'
                elif record[var] == agent.demographics['home']:
                    record[var] = 'home'
                var = 'Injured'
                if not defined:
                    variables.append({'Name': var,'Values':'yes,no','DataType': 'Boolean'})
                record[var] = 'yes' if world.getState(name,'health',history[step]).expectation() < 0.2 else 'no'
                var = 'Income Loss'
                if not defined:
                    variables.append({'Name': var,'Values':'yes,no','DataType': 'Boolean'})
                if step > 0:
                    record[var] = 'yes' if world.getState(name,'health',history[step]).expectation() < world.getState(name,'health',history[step-3]).expectation() else 'no'
                else:
                    record[var] = 'no'
                var = 'Property Damage'
                if not defined:
                    variables.append({'Name': var,'Values':'[1-7]','DataType': 'Integer','Notes': 'Degree of current level of property damage (7 being the most severe)'})
                record[var] = accessibility.toLikert(world.getState(agent.demographics['home'],'risk',history[step]).expectation(),7)
                var = 'Dissatisfaction'
                if not defined:
                    variables.append({'Name': var,'Values':'[1-7]','DataType': 'Integer'})
                record[var] = accessibility.toLikert(world.getState(name,'grievance',history[step]).expectation(),7)
                var = 'Government Aid'
                if not defined:
                    variables.append({'Name': var,'Values':'Region[01-16]','DataType': 'String'})
                record[var] = world.getFeature(actionKey('System'),history[step]).first()['object']
                var = 'Hurricane Phase'
                if not defined:
                    variables.append({'Name': var,'Values':'none,approaching,active','DataType': 'String'})
                record[var] = world.getState('Nature','phase',history[step]).first()
                var = 'Hurricane Location'
                if not defined:
                    variables.append({'Name': var,'Values':'Region[01-16],none','DataType': 'String'})
                record[var] = world.getState('Nature','location',history[step]).first()
                var = 'Hurricane Category'
                if not defined:
                    variables.append({'Name': var,'Values':'[0-5],none','DataType': 'String'})
                record[var] = int(round(world.getState('Nature','category',history[step]).expectation()))
                if cmd['debug']:
                    print(record)
                if not defined:
                    if not cmd['debug']:
                        accessibility.writeVarDef(os.path.dirname(__file__),variables)
                    defined = True
        if not cmd['debug']:
            accessibility.writeOutput(args,output,[var['Name'] for var in variables],'%s.tsv' % (os.path.splitext(os.path.basename(__file__))[0]),
                os.path.join(os.path.dirname(__file__),'Instances','Instance%d' % (instance),'Runs','run-0'))
        break