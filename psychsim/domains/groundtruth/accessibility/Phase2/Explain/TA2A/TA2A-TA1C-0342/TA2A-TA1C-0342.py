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
            variables.append({'Name': var,'Values':'evacuated,shelter,home','DataType': 'String','Notes': 'Q1'})
        assert len(world.getState(name,'location',history[step]['state'])) == 1
        record[var] = world.getState(name,'location',history[step]['state']).first()
        if record[var][:7] == 'shelter':
            record[var] = 'shelter'
        elif record[var] == agent.demographics['home']:
            record[var] = 'home'
        var = 'Injury'
        if not defined:
            variables.append({'Name': var,'Values':'none,minor,serious','DataType': 'String','Notes': 'Q2'})
        health = world.getState(name,'health',history[step]['state']).expectation()
        if health < 0.2:
            record[var] = 'serious'
        elif health < 0.5:
            record[var] = 'minor'
        else:
            record[var] = 'none'
        var = 'Wealth Change'
        if not defined:
            variables.append({'Name': var,'Values':'[-5,5]','DataType': 'Integer','Notes': 'Q3'})
        if step > 0:
            delta = world.getState(name,'health',history[step]['state']).expectation() - world.getState(name,'health',history[step-3]['state']).expectation()
            if delta > 0.:
                record[var] = accessibility.toLikert(delta)
            elif delta < 0.:
                record[var] = -accessibility.toLikert(-delta)
            else:
                record[var] = 0
        else:
            record[var] = 0
        var = 'Regional Damage'
        if not defined:
            variables.append({'Name': var,'Values':'[1-5]','DataType': 'Integer','Notes': 'Q4'})
        record[var] = accessibility.toLikert(world.getState(agent.demographics['home'],'risk',history[step][name]).expectation(),5)
        if not defined:
            defined = True
    return output

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO,filename='%s%s' % (os.path.splitext(__file__)[0],'.log'))
    parser = ArgumentParser()
    parser.add_argument('-d','--debug',action='store_true',help='Run without writing any files')
    random.seed(int(os.path.splitext(os.path.basename(__file__))[0].split('-')[2]))
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
        sample = random.sample(actors,len(actors)//20)
        history = accessibility.holoCane(world,config,set(sample),1,True,{'System': None},'hurricanes',True)
        output = []
        for partID in range(len(sample)):
            name = sample[partID]
            logging.info('Participant %d: %s' % (partID+1,name))
            agent = world.agents[name]
            record = {}
            output.append(record)
            var = 'Participant'
            if not defined:
                variables.append({'Name': var,'Values':'[1+]','VarType': 'fixed','DataType': 'Integer'})
            record[var] = partID+1
            if not defined:
                variables += accessibility.boilerPlate
            record.update(accessibility.getCurrentDemographics(args,name,world,states,config))
            for other in range(len(sample)):
                var = 'Relationship Participant %d' % (other+1)
                if not defined:
                    variables.append({'Name': var,'Values':'self,family,friend,acquaintance,none','DataType': 'String','Notes': 'QI.2'})
                if other == partID:
                    record[var] = 'self'
                else:
                    otherName = sample[other]
                    if otherName in agent.getFriends():
                        record[var] = 'friend'
                    elif otherName in agent.getNeighbors():
                        record[var] = 'acquaintance'
                    else:
                        record[var] = 'none'
            if cmd['debug']:
                print('Participant:',record)
            if not defined:
                defined = True
        if not cmd['debug']:
            accessibility.writeOutput(args,output,[var['Name'] for var in variables],'%s-Participants.tsv' % (os.path.splitext(os.path.basename(__file__))[0]),
                os.path.join(os.path.dirname(__file__),'Instances','Instance%d' % (instance),'Runs','run-0'))
        startField = len(variables)
        defined = False
        output = []
        for partID in range(len(sample)):
            name = sample[partID]
            agent = world.agents[name]
            record = {}
            var = 'Participant'
            record[var] = partID+1
            newRecords = processHistory(world,name,record,history,output,day1,None if defined else variables)
            if cmd['debug']:
                for record in newRecords:
                    print('Individual:',record)
            output += newRecords
            if not defined:
                defined = True
        if not cmd['debug']:
            accessibility.writeOutput(args,output,['Participant']+[var['Name'] for var in variables[startField:]],
                '%s-Individual.tsv' % (os.path.splitext(os.path.basename(__file__))[0]),
                os.path.join(os.path.dirname(__file__),'Instances','Instance%d' % (instance),'Runs','run-0'))
        startField = len(variables)
        output = []
        for step in range(3,len(history),3):
            actions = {state2agent(key): world.getFeature(key,history[step]['state']).first() 
                for key in history[step]['state'].keys() if isActionKey(key)}
            newRecords = [{'Timestep': day1+step//3, 'Participant': sample.index(name)+1} 
                for name,action in actions.items() if action['verb'] == 'takeResources']
            if cmd['debug']:
                for record in newRecords:
                    print('Crime:',record)
            output += newRecords
        if not cmd['debug']:
            accessibility.writeOutput(args,output,['Timestep','Participant'],
                '%s-Crime.tsv' % (os.path.splitext(os.path.basename(__file__))[0]),
                os.path.join(os.path.dirname(__file__),'Instances','Instance%d' % (instance),'Runs','run-0'))
        defined = False
        output = []
        for step in range(0,len(history),3):
            record = {'Timestep': day1+step//3 + 1}
            output.append(record)
            for region in world.agents:
                if region[:6] == 'Region':
                    var = 'Regional Damage %s' % (region)
                    if not defined:
                        variables.append({'Name': var,'Values':'[1-5]','DataType': 'Integer','Notes': 'Q3'})
                    record[var] = accessibility.toLikert(world.getState(region,'risk',history[step]['state']).expectation(),5)
            var = 'Aid Destination'
            if not defined:
                variables.append({'Name': var,'Values':'Region[01-16]','DataType': 'String','Notes': 'Q4'})
            try:
                action = world.getFeature(actionKey('System'),history[step+3]['state']).first()
                record[var] = action['object']
            except IndexError:
                pass
            if cmd['debug']:
                print('Government:',record)
            if not defined:
                if not cmd['debug']:
                    accessibility.writeVarDef(os.path.dirname(__file__),variables)
                defined = True
        if not cmd['debug']:
            accessibility.writeOutput(args,output,['Timestep']+[var['Name'] for var in variables[startField:]],
                '%s-Government.tsv' % (os.path.splitext(os.path.basename(__file__))[0]),
                os.path.join(os.path.dirname(__file__),'Instances','Instance%d' % (instance),'Runs','run-0'))