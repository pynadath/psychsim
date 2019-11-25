from argparse import ArgumentParser
import logging
import os.path
import pickle
import random
import sys

from psychsim.pwl import *
from psychsim.domains.groundtruth import accessibility
from psychsim.domains.groundtruth.simulation.execute import fastForward

def processHistory(world,name,root,history,t,variables,prefix,participants=None):
    agent = world.agents[name]
    output = []
    for step in range(0,len(history),3):
        root['Timestep'] = t+step//3+1

        var = '%s Location' % (prefix)
        if var not in variables:
            variables[var] = {'Name': var,'Values':'evacuated,shelter,home','DataType': 'String'}
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
            variables[var] = {'Name': var,'Values':'none,minor,serious','DataType': 'String'}
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
            variables[var] = {'Name': var,'Values':'[0-6],NA','DataType': 'Integer'}
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
            variables[var] = {'Name': var,'Values':'[0-6],NA','DataType': 'Integer'}
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
                variables[var] = {'Name': var,'Values':'yes,no','DataType': 'Boolean'}
            record = dict(root)
            record['VariableName'] = var
            record['Value'] = 'yes' if aid else 'no' 
            output.append(record)

            var = '%s Aid Adequacy' % (prefix)
            if var not in variables:
                variables[var] = {'Name': var,'Values':'[0-6]','DataType': 'Integer'}
            record = dict(root)
            record['VariableName'] = var
            record['Value'] = 3 if aid else 0 
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
    demos = {'Age','Gender'}
    variables = {field: accessibility.boilerDict[field] for field in demos}
    participants = accessibility.readRRParticipants(os.path.join(os.path.dirname(os.path.basename(__file__)),'..','TA2A-TA1C-0372','TA2A-TA1C-0372.log'))
    for instance,args in accessibility.instanceArgs('Phase2'):
        print('Instance %d (%d,%d)' % (instance,args['instance'],args['run']))
        logging.info('Instance %d (%d,%d)' % (instance,args['instance'],args['run']))
        challenge = accessibility.instanceChallenge(instance)[1]
        config = accessibility.getConfig(args['instance'])
        states = {}
        if challenge == 'Explain':
            yearLength = config.getint('Disaster','year_length',fallback=365)
            day1 = (args['span']//yearLength + 1)*yearLength+1
            world = accessibility.unpickle(instance,day=day1)
        else:
            world = accessibility.unpickle(instance)
            day1 = args['span']-5
            accessibility.loadState(args,states,day1,'Nature',world)
        output = []
        for partID in participants[instance]:
            name = participants[instance][partID]
            entry = {'Timestep': day1,'EntityIdx': 'TA2A 372 Participant %d' % (partID)}
            agent = world.agents[name]
            for field,value in accessibility.getCurrentDemographics(args,name,world,states,config).items():
                if field in demos:
                    record = dict(entry)
                    record['VariableName'] = field
                    record['Value'] = value
                    output.append(record)
            var = '%s %d Dissatisfaction' % (team,reqNum)
            if var not in variables:
                variables[var] = {'Name': var,'Values':'[0-6]','DataType': 'Integer'}
            record = dict(entry)
            record['VariableName'] = var
            record['Value'] = accessibility.toLikert(world.getState(name,'grievance').expectation(),7)-1
            output.append(record)
            var = '%s %d Aid Eagerness' % (team,reqNum)
            if var not in variables:
                variables[var] = {'Name': var,'Values':'[0-6]','DataType': 'Integer'}
            record = dict(entry)
            record['VariableName'] = var
            record['Value'] = accessibility.toLikert(world.getState(name,'risk').expectation(),7)-1
            output.append(record)
        # Trigger hurricane
        coastline = {r for r in world.agents if r[:6] == 'Region' and world.agents[r].x == 1}
        accessibility.initiateHurricane(world,5,sorted(coastline)[len(coastline)//2],participants[instance].values(),phase='active')
        history = accessibility.holoCane(world,config,set(participants[instance].values()),6,True,{'System': None},debug=True)
        hurricaneData = []
        for step in range(0,len(history)-1,3):
            hurricaneData.append({'Timestep': day1+step//3,'Name': 'Landed','Value': 'yes'})
            hurricaneData.append({'Timestep': day1+step//3,'Name': 'Category',
                'Value': world.getState('Nature','category',history[step]['state']).first()})
            if world.getState('Nature','location',history[step]['state']).first() == 'none':
                hurricaneData.append({'Timestep': day1+step//3,'Name': 'Location','Value': 'leaving'})
            else:
                hurricaneData.append({'Timestep': day1+step//3,'Name': 'Location',
                    'Value': world.getState('Nature','location',history[step]['state']).first()})
        for partID in participants[instance]:
            name = participants[instance][partID]
            entry = {'Timestep': day1,'EntityIdx': 'TA2A 372 Participant %d' % (partID)}
            output += processHistory(world,name,entry,history[:-1],day1-1,variables,'%s %d' % (team,reqNum))
        if not cmd['debug']:
            accessibility.writeOutput(args,output,accessibility.fields['RunData'],'RunDataTable.tsv',
                os.path.join(os.path.dirname(__file__),'Instances','Instance%d' % (instance),'Runs','run-0'))
            accessibility.writeOutput(args,hurricaneData,accessibility.fields['InstanceVariable'],'InstanceVariableTable.tsv',
                os.path.join(os.path.dirname(__file__),'Instances','Instance%d' % (instance),'Runs','run-0'))
    if not cmd['debug']:
        accessibility.writeVarDef(os.path.dirname(__file__),list(variables.values()))
