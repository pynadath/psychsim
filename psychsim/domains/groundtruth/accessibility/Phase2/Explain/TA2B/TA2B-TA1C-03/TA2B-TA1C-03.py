from argparse import ArgumentParser
import logging
import os.path
import pickle
import random
import sys

from psychsim.pwl import *
from psychsim.domains.groundtruth import accessibility
from psychsim.domains.groundtruth.simulation.execute import fastForward

def processHistory(world,name,root,history,output,t,variables=None):
    agent = world.agents[name]
    output = []
    defined = variables is None
    for step in range(0,len(history),3):
        record = dict(root)
        record['Timestep'] = t+step//3+1
        output.append(record)
        var = 'Location'
        if not defined:
            variables.append({'Name': var,'Values':'evacuated,shelter,home','DataType': 'String'})
        assert len(world.getState(name,'location',history[step]['state'])) == 1
        record[var] = world.getState(name,'location',history[step]['state']).first()
        if record[var][:7] == 'shelter':
            record[var] = 'shelter'
        elif record[var] == agent.demographics['home']:
            record[var] = 'home'
        var = 'Injured'
        if not defined:
            variables.append({'Name': var,'Values':'yes,no','DataType': 'Boolean'})
        record[var] = 'yes' if world.getState(name,'health',history[step]['state']).expectation() < 0.2 else 'no'
        var = 'Income Loss'
        if not defined:
            variables.append({'Name': var,'Values':'yes,no','DataType': 'Boolean'})
        if step > 0:
            record[var] = 'yes' if world.getState(name,'health',history[step]['state']).expectation() < world.getState(name,'health',history[step-3]['state']).expectation() else 'no'
        else:
            record[var] = 'no'
        var = 'Property Damage'
        if not defined:
            variables.append({'Name': var,'Values':'[1-7]','DataType': 'Integer','Notes': 'Degree of current level of property damage (7 being the most severe)'})
        record[var] = accessibility.toLikert(world.getState(agent.demographics['home'],'risk',history[step]['beliefs']).expectation(),7)
        var = 'Dissatisfaction'
        if not defined:
            variables.append({'Name': var,'Values':'[1-7]','DataType': 'Integer'})
        record[var] = accessibility.toLikert(world.getState(name,'grievance',history[step]['state']).expectation(),7)
        var = 'Government Aid'
        if not defined:
            variables.append({'Name': var,'Values':'Region[01-16]','DataType': 'String'})
        record[var] = world.getFeature(actionKey('System'),history[step]['state']).first()['object']
        var = 'Hurricane Phase'
        if not defined:
            variables.append({'Name': var,'Values':'none,approaching,active','DataType': 'String'})
        record[var] = world.getState('Nature','phase',history[step]['state']).first()
        var = 'Hurricane Location'
        if not defined:
            variables.append({'Name': var,'Values':'Region[01-16],none','DataType': 'String'})
        record[var] = world.getState('Nature','location',history[step]['state']).first()
        var = 'Hurricane Category'
        if not defined:
            variables.append({'Name': var,'Values':'[1-5],none','DataType': 'String'})
        record[var] = 'none' if record['Hurricane Phase'] == 'none' else int(round(world.getState('Nature','category',history[step]['beliefs']).expectation()))
        if record[var] == 0:
            logging.warning('%s has belief of 0 category hurricane when hurricane is present at step %d' % (name,step))
            record[var] = 'none'
        if not defined:
            defined = True
    return output

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
            world = accessibility.unpickle(instance,day=day1+1)
        except FileNotFoundError:
            world = accessibility.unpickle(instance)
            accessibility.loadState(args,states,args['span']-1,'Nature',world)
            fastForward(world,config)
            day = world.getState(WORLD,'day').first()
            with open(os.path.join(accessibility.getDirectory(args),'scenario%d.pkl' % (day)),'wb') as outfile:
                pickle.dump(world,outfile)
        actors = {name for name in world.agents if name[:5] == 'Actor' and world.getState(name,'alive').first()}
        sample = random.sample(actors,(len(actors)//100)*5)
        output = []
        for partID in range(len(sample)):
            name = sample[partID]
            logging.info('Participant %d: %s' % (partID+1,name))
            agent = world.agents[name]
            record = {}
            var = 'Participant'
            if not defined:
                variables.append({'Name': var,'Values':'[1+]','VarType': 'fixed','DataType': 'Integer'})
            record[var] = partID+1
            var = 'Group'
            if not defined:
                variables.append({'Name': var,'Values':'[0-4]','VarType': 'fixed','DataType': 'Integer','Notes': 'Assigned condition'})
            record[var] = partID % 5
            policy = {}
            if record[var] > 0:
                # Must have 3 friends
                while len(agent.friends) < 3:
                    agent.friends.add(random.choice(list(actors-agent.friends-{name})))
                if record[var] == 1:
                    evacuees = set()
                else:
                    evacuees = random.sample(agent.friends,record[var]-1)
                for friend in agent.friends:
                    for action in world.agents[friend].actions:
                        if friend in evacuees and action['verb'] == 'evacuate':
                            policy[friend] = action
                            break
                        elif friend not in evacuees and action['verb'] == 'stayInLocation':
                            policy[friend] = action
                            break
            else:
                agent.friends = set()
            if not defined:
                variables += accessibility.boilerPlate
            history = accessibility.holoCane(world,config,name,config.getint('Disaster','season_length'),True,policy)
            record.update(accessibility.getCurrentDemographics(args,name,world,states,config))
            newRecords = processHistory(world,name,record,history,output,day1,None if defined else variables)
            if cmd['debug']:
                for record in newRecords:
                    print(record)
            output += newRecords
            print(name)
            if not defined:
                if not cmd['debug']:
                    accessibility.writeVarDef(os.path.dirname(__file__),variables)
                defined = True
        if not cmd['debug']:
            accessibility.writeOutput(args,output,[var['Name'] for var in variables],'%s.tsv' % (os.path.splitext(os.path.basename(__file__))[0]),
                os.path.join(os.path.dirname(__file__),'Instances','Instance%d' % (instance),'Runs','run-0'))
