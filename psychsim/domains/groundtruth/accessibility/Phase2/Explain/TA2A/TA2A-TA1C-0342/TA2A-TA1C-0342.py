from argparse import ArgumentParser
import logging
import os.path
import pickle
import random
import sys

from psychsim.pwl import *
from psychsim.domains.groundtruth import accessibility
from psychsim.domains.groundtruth.simulation.execute import fastForward

def processHistory(world,name,root,history,output,t,variables,prefix):
    agent = world.agents[name]
    output = []
    for step in range(0,len(history),3):
        root['Timestep'] = t+step//3+1
        var = '%s Location' % (prefix)
        if var not in variables:
            variables[var] = {'Name': var,'Values':'evacuated,shelter,home','DataType': 'String','Notes': 'Q1'}
        assert len(world.getState(name,'location',history[step]['state'])) == 1
        record = dict(root)
        record['VariableName'] = var
        record['Value'] = world.getState(name,'location',history[step]['state']).first()
        if record['Value'][:7] == 'shelter':
            record['Value'] = 'shelter'
        elif record['Value'] == agent.demographics['home']:
            record['Value'] = 'home'
        output.append(record)
        var = '%s Injury' % (prefix)
        if var not in variables:
            variables[var] = {'Name': var,'Values':'none,minor,serious','DataType': 'String','Notes': 'Q2'}
        health = world.getState(name,'health',history[step]['state']).expectation()
        record = dict(root)
        record['VariableName'] = var
        if health < 0.2:
            record['Value'] = 'serious'
        elif health < 0.5:
            record['Value'] = 'minor'
        else:
            record['Value'] = 'none'
        output.append(record)
        var = '%s Wealth Change' % (prefix)
        if var not in variables:
            variables[var] = {'Name': var,'Values':'[-5,5]','DataType': 'Integer','Notes': 'Q3'}
        record = dict(root)
        record['VariableName'] = var
        if step > 0:
            delta = world.getState(name,'health',history[step]['state']).expectation() - world.getState(name,'health',history[step-3]['state']).expectation()
            if delta > 0.:
                record['Value'] = accessibility.toLikert(delta)
            elif delta < 0.:
                record['Value'] = -accessibility.toLikert(-delta)
            else:
                record['Value'] = 0
        else:
            record['Value'] = 0
        output.append(record)
        var = '%s Regional Damage' % (prefix)
        if var not in variables:
            variables[var] = {'Name': var,'Values':'[1-5]','DataType': 'Integer','Notes': 'Q4'}
        record = dict(root)
        record['VariableName'] = var
        record['Value'] = accessibility.toLikert(world.getState(agent.demographics['home'],'risk',history[step][name]).expectation(),5)
        output.append(record)
    return output

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO,filename='%s%s' % (os.path.splitext(__file__)[0],'.log'))
    parser = ArgumentParser()
    parser.add_argument('-d','--debug',action='store_true',help='Run without writing any files')
    reqNum = int(os.path.splitext(os.path.basename(__file__))[0].split('-')[2])
    team = os.path.splitext(os.path.basename(__file__))[0].split('-')[0]
    random.seed(reqNum)
    cmd = vars(parser.parse_args())
    variables = {}
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
            variables.update(accessibility.boilerDict)
            for field,value in accessibility.getCurrentDemographics(args,name,world,states,config).items():
                output.append({'Timestep': day1,'VariableName': field,'EntityIdx': '%s %d Participant %d' % (team,reqNum,partID+1),'Value': value})
            for other in range(len(sample)):
                var = '%s %d Relationship Participant %d' % (team,reqNum,other+1)
                if var not in variables:
                    variables[var] = {'Name': var,'Values':'self,family,friend,acquaintance,none','DataType': 'String','Notes': 'QI.2'}
                if other == partID:
                    value = 'self'
                else:
                    otherName = sample[other]
                    if otherName in agent.getFriends():
                        value = 'friend'
                    elif otherName in agent.getNeighbors():
                        value = 'acquaintance'
                    else:
                        value = 'none'
                output.append({'Timestep': day1,'VariableName': var,'EntityIdx': '%s %d Participant %d' % (team,reqNum,partID+1),'Value': value})
        for partID in range(len(sample)):
            name = sample[partID]
            agent = world.agents[name]
            record = {'EntityIdx': '%s %d Participant %d' % (team,reqNum,partID+1)}
            output += processHistory(world,name,record,history,output,day1,variables,'%s %d' % (team,reqNum))
        for step in range(3,len(history),3):
            actions = {state2agent(key): world.getFeature(key,history[step]['state']).first() 
                for key in history[step]['state'].keys() if isActionKey(key)}
            var = '%s %d Crime' % (team,reqNum)
            if var not in variables:
                variables[var] = {'Name': var,'Values': 'yes','DataType': 'String','Notes': 'Recorded only when a crime is committed'}
            output += [{'Timestep': day1+step//3, 'VariableName': var, 'EntityIdx': '%s %d Participant %d' % (team,reqNum,sample.index(name)+1),
                'Value': 'yes'} for name,action in actions.items() if action['verb'] == 'takeResources']
        for step in range(0,len(history),3):
            for region in world.agents:
                if region[:6] == 'Region':
                    var = '%s %d Regional Damage' % (team,reqNum)
                    if var not in variables:
                        variables[var] = {'Name': var,'Values':'[1-5]','DataType': 'Integer','Notes': 'Q3'}
                    record = {'Timestep': day1+step//3 + 1,'VariableName': var,'EntityIdx': region,
                        'Value': accessibility.toLikert(world.getState(region,'risk',history[step]['state']).expectation(),5)}
                    output.append(record)
            var = '%s %d Aid Destination' % (team,reqNum)
            if var not in variables:
                variables[var] = {'Name': var,'Values':'Region[01-16]','DataType': 'String','Notes': 'Q4'}
            try:
                action = world.getFeature(actionKey('System'),history[step+3]['state']).first()
                record = {'Timestep': day1+step//3 + 1,'VariableName': var,'Value': action['object']}
                output.append(record)
            except IndexError:
                pass
        if not cmd['debug']:
            accessibility.writeOutput(args,output,accessibility.fields['RunData'],'RunDataTable.tsv',
                os.path.join(os.path.dirname(__file__),'Instances','Instance%d' % (instance),'Runs','run-0'))
    if not cmd['debug']:
        accessibility.writeVarDef(os.path.dirname(__file__),list(variables.values()))
