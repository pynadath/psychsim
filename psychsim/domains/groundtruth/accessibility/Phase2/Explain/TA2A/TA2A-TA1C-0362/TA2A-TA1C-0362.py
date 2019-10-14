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
    oldRisk = world.getState(name,'risk').expectation()
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
        health = world.getState(name,'health',history[step]['state']).expectation()
        var = '%s Injury' % (prefix)
        if var not in variables:
            variables[var] = {'Name': var,'Values':'none,minor,serious','DataType': 'String','Notes': 'Q2a'}
        health = world.getState(name,'health',history[step]['state']).expectation()
        record = dict(root)
        record['VariableName'] = var
        if health < 0.2:
            injury = 'serious'
        elif health < 0.5:
            injury = 'minor'
        else:
            injury = 'none'
        record['Value'] = injury
        output.append(record)
        var = '%s Minor Injury Possibility' % (prefix)
        if var not in variables:
            variables[var] = {'Name': var,'Values':'[0-6],NA','DataType': 'Integer','Notes': 'Q2b'}
        record = dict(root)
        record['VariableName'] = var
        risk = world.getState(name,'risk',history[step][name]).expectation()
        if injury == 'none':
            record['Value'] = accessibility.toLikert(risk,7)-1
        else:
            record['Value'] = 'NA'            
        output.append(record)
        var = '%s Serious Injury Possibility' % (prefix)
        if var not in variables:
            variables[var] = {'Name': var,'Values':'[0-6],NA','DataType': 'Integer','Notes': 'Q2b'}
        record = dict(root)
        record['VariableName'] = var
        if injury == 'none':
            record['Value'] = accessibility.toLikert(world.getState(name,'risk',history[step][name]).expectation()/2,7)-1
        else:
            record['Value'] = 'NA'            
        output.append(record)
        try:
            aid = world.getFeature(actionKey('System'),history[step+3]['state']).first()['object'] == agent.demographics['home']
        except IndexError:
            aid = None
        if aid is not None:
            var = '%s Received Aid' % (prefix)
            if var not in variables:
                variables[var] = {'Name': var,'Values':'yes,no','DataType': 'Boolean','Notes': 'Q3'}
            record = dict(root)
            record['VariableName'] = var
            record['Value'] = 'yes' if aid else 'no' 
            output.append(record)
            var = '%s Aid Adequacy' % (prefix)
            if var not in variables:
                variables[var] = {'Name': var,'Values':'[0-6]','DataType': 'Integer','Notes': 'Q3'}
            record = dict(root)
            record['VariableName'] = var
            record['Value'] = 3 if aid else 0 
            output.append(record)
        var = '%s Risk Change' % (prefix)
        if var not in variables:
            variables[var] = {'Name': var,'Values':'[-6,6]','DataType': 'Integer','Notes': 'Q4'}
        record = dict(root)
        record['VariableName'] = var
        delta = risk - oldRisk
        if delta > 0.:
            record['Value'] = accessibility.toLikert(delta,7)-1
        elif delta < 0.:
            record['Value'] = -accessibility.toLikert(-delta,7)+1
        else:
            record['Value'] = 0
        output.append(record)
        var = '%s Injury Possibility Change' % (prefix)
        if var not in variables:
            variables[var] = {'Name': var,'Values':'[-6,6]','DataType': 'Integer','Notes': 'Q4a'}
        record = dict(root)
        record['VariableName'] = var
        delta = risk - oldRisk
        if delta > 0.:
            record['Value'] = accessibility.toLikert(delta,7)-1
        elif delta < 0.:
            record['Value'] = -accessibility.toLikert(-delta,7)+1
        else:
            record['Value'] = 0
        output.append(record)
        oldRisk = risk
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
        regions = [name for name in world.agents if name[:6] == 'Region']
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
            var = '%s %d Dissatisfaction' % (team,reqNum)
            if var not in variables:
                variables[var] = {'Name': var,'Values':'[0-6]','DataType': 'Integer','Notes': 'QI.2'}
            output.append({'Timestep': day1,'VariableName': var,'EntityIdx': '%s %d Participant %d' % (team,reqNum,partID+1),
                'Value': accessibility.toLikert(world.getState(name,'grievance').expectation(),7)-1})
            var = '%s %d Aid Eagerness' % (team,reqNum)
            if var not in variables:
                variables[var] = {'Name': var,'Values':'[0-6]','DataType': 'Integer','Notes': 'QI.3'}
            output.append({'Timestep': day1,'VariableName': var,'EntityIdx': '%s %d Participant %d' % (team,reqNum,partID+1),
                'Value': accessibility.toLikert(world.getState(name,'risk').expectation(),7)-1})
        for partID in range(len(sample)):
            name = sample[partID]
            agent = world.agents[name]
            record = {'EntityIdx': '%s %d Participant %d' % (team,reqNum,partID+1)}
            output += processHistory(world,name,record,history,output,day1,variables,'%s %d' % (team,reqNum))
        for step in range(0,len(history),3):
            try:
                action = world.getFeature(actionKey('System'),history[step+3]['state']).first()
            except IndexError:
                continue
            var = '%s %d Aid' % (team,reqNum)
            if var not in variables:
                variables[var] = {'Name': var,'Values':'yes,no','DataType': 'Boolean','Notes': 'QII.2'}
            for region in regions:
                record = {'Timestep': day1+step//3 + 1,'VariableName': var,'EntityIdx': region,
                    'Value': 'yes' if action['object'] == region else 'no'}
                output.append(record)
            var = '%s %d Non-Financial Aid' % (team,reqNum)
            if var not in variables:
                variables[var] = {'Name': var,'Values':'yes,no','DataType': 'Boolean','Notes': 'QII.3'}
            for region in regions:
                record = {'Timestep': day1+step//3 + 1,'VariableName': var,'EntityIdx': region,
                    'Value': 'yes' if action['object'] == region else 'no'}
                output.append(record)
        if not cmd['debug']:
            accessibility.writeOutput(args,output,accessibility.fields['RunData'],'RunDataTable.tsv',
                os.path.join(os.path.dirname(__file__),'Instances','Instance%d' % (instance),'Runs','run-0'))
    if not cmd['debug']:
        accessibility.writeVarDef(os.path.dirname(__file__),list(variables.values()))
