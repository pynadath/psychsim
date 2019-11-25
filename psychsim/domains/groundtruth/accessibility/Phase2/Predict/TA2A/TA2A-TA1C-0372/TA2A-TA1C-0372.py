from argparse import ArgumentParser
import logging
import os.path
import pickle
import random
import sys

from psychsim.pwl import *
from psychsim.domains.groundtruth import accessibility
from psychsim.domains.groundtruth.simulation.execute import fastForward

def processHistory(world,name,root,history,output,t,variables,prefix,participants=None):
    agent = world.agents[name]
    output = []
    oldRisk = world.getState(name,'risk').expectation()
    for step in range(0,len(history),3):
        root['Timestep'] = t+step//3+1
        health = world.getState(name,'health',history[step]['state']).expectation()
        var = '%s Injury' % (prefix)
        if var not in variables:
            variables[var] = {'Name': var,'Values':'none,minor,serious','DataType': 'String','Notes': 'QII.1'}
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
        var = '%s Information Received' % (prefix)
        if var not in variables:
            variables[var] = {'Name': var,'Values':'[1+]*,none','DataType': 'String',
                'Notes': 'QII.2: Comma-separated list of participant IDs (\'none\' if no information received)'}
        record = dict(root)
        record['VariableName'] = var
        record['Value'] = ','.join(sorted('%d' % (participants.index(friend)+1) for friend in world.agents[name].getFriends() & set(participants)))
        if not record['Value']:
            record['Value'] = 'none'
        output.append(record)
        var = '%s Aid Received' % (prefix)
        if var not in variables:
            variables[var] = {'Name': var,'Values':'[1+]*,none','DataType': 'String',
                'Notes': 'QII.3: Comma-separated list of participant IDs (\'none\' if no information received)'}
        record = dict(root)
        record['VariableName'] = var
        record['Value'] = ','.join(sorted('%d' % (participants.index(neighbor)+1) for neighbor in world.agents[name].getNeighbors() & set(participants)
            if world.getFeature(actionKey(neighbor),history[step+1]['state']).first()['verb'] == 'decreaseRisk'))
        if not record['Value']:
            record['Value'] = 'none'
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
    demos = {'Age','Gender','Ethnicity'}
    variables = {'familyWith': {'Name': 'familyWith','Values': 'yes,no','RelType': 'dynamic','DataType': 'Boolean'},
        'friendOf': {'Name': 'friendOf','Values': 'yes,no','RelType': 'dynamic','DataType': 'Boolean'},
        'acquaintanceOf': {'Name': 'acquaintanceOf','Values': 'yes,no','RelType': 'dynamic','DataType': 'Boolean'},
        'strangerTo': {'Name': 'strangerTo','Values': 'yes,no','RelType': 'dynamic','DataType': 'Boolean'},
        }
    if not cmd['debug']:
        accessibility.writeVarDef(os.path.dirname(__file__),list(variables.values()),True)
    variables = {field: accessibility.boilerDict[field] for field in demos}
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
        regions = [name for name in world.agents if name[:6] == 'Region']
        actors = {name for name in world.agents if name[:5] == 'Actor' and world.getState(name,'alive').first()}
        sample = random.sample(actors,len(actors)//20)
        history = accessibility.holoCane(world,config,set(sample),6,True,{'System': None},debug=True)
        output = {'RunData': [],'RelationshipData': []}
        for partID in range(len(sample)):
            name = sample[partID]
            logging.info('Participant %d: %s' % (partID+1,name))
            agent = world.agents[name]
            for field,value in accessibility.getCurrentDemographics(args,name,world,states,config).items():
                if field in demos:
                    output['RunData'].append({'Timestep': day1,'VariableName': field,'EntityIdx': '%s %d Participant %d' % (team,reqNum,partID+1),
                        'Value': value})
            for otherID in range(len(sample)):
                if otherID != partID:
                    if sample[otherID] in agent.getFriends():
                        output['RelationshipData'].append({'Timestep': day1,'RelationshipType': 'friendOf','Directed': 'yes',
                            'FromEntityId': '%s %d Participant %d' % (team,reqNum,otherID+1),
                            'ToEntityId': '%s %d Participant %d' % (team,reqNum,partID+1),'Data': 'yes'})
                    elif sample[otherID] in agent.getNeighbors():
                        output['RelationshipData'].append({'Timestep': day1,'RelationshipType': 'acquaintanceOf','Directed': 'yes',
                            'FromEntityId': '%s %d Participant %d' % (team,reqNum,otherID+1),
                            'ToEntityId': '%s %d Participant %d' % (team,reqNum,partID+1),'Data': 'yes'})
                    else:
                        output['RelationshipData'].append({'Timestep': day1,'RelationshipType': 'strangerTo','Directed': 'yes',
                            'FromEntityId': '%s %d Participant %d' % (team,reqNum,otherID+1),
                            'ToEntityId': '%s %d Participant %d' % (team,reqNum,partID+1),'Data': 'yes'})
            denominator = sum(agent.Rweights.values())
            var = '%s %d Aid to Family' % (team,reqNum)
            if var not in variables:
                variables[var] = {'Name': var,'Values':'[0-6]','DataType': 'Integer','Notes': 'I.3'}
            output['RunData'].append({'Timestep': day1,'VariableName': var,'EntityIdx': '%s %d Participant %d' % (team,reqNum,partID+1),
                'Value': accessibility.toLikert(sum([agent.Rweights[key] for key in ['childrenHealth','pet','health']])/denominator,7)-1})
            var = '%s %d Aid to Friends' % (team,reqNum)
            if var not in variables:
                variables[var] = {'Name': var,'Values':'[0-6]','DataType': 'Integer','Notes': 'I.3'}
            output['RunData'].append({'Timestep': day1,'VariableName': var,'EntityIdx': '%s %d Participant %d' % (team,reqNum,partID+1),
                'Value': accessibility.toLikert(sum([agent.Rweights[key] for key in ['friends']])/denominator,7)-1})
            var = '%s %d Aid to Strangers' % (team,reqNum)
            if var not in variables:
                variables[var] = {'Name': var,'Values':'[0-6]','DataType': 'Integer','Notes': 'I.3'}
            output['RunData'].append({'Timestep': day1,'VariableName': var,'EntityIdx': '%s %d Participant %d' % (team,reqNum,partID+1),
                'Value': accessibility.toLikert(sum([agent.Rweights[key] for key in []])/denominator,7)-1})
        for partID in range(len(sample)):
            name = sample[partID]
            record = {'EntityIdx': '%s %d Participant %d' % (team,reqNum,partID+1)}
            output['RunData'] += processHistory(world,name,record,history[:-1],output,day1-1,variables,'%s %d' % (team,reqNum),sample)
        if not cmd['debug']:
            for name,data in output.items():
                accessibility.writeOutput(args,data,accessibility.fields[name],'%sTable.tsv' % (name),
                    os.path.join(os.path.dirname(__file__),'Instances','Instance%d' % (instance),'Runs','run-0'))
    if not cmd['debug']:
        accessibility.writeVarDef(os.path.dirname(__file__),list(variables.values()))
