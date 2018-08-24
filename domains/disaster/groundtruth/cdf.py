import csv
import os.path

from psychsim.pwl.keys import *
from psychsim.action import ActionSet
from actor import Actor

dataTypes = {bool: 'Boolean',
             list: 'String',
             float: 'Real',
             ActionSet: 'String',
             int: 'Integer'}

def shorten(key):
    if isBinaryKey(key):
        relation = key2relation(key)
        return '%s %s %s' % (relation['subject'],relation['relation'],relation['object'])
    elif isStateKey(key):
        return '%s %s' % (state2agent(key),state2feature(key))
    else:
        return key

def var2def(name,world,base=None):
    if base is None:
        base = name
    variable = world.variables[base]
    record = {'Name': shorten(name),
              'LongName': name,
              'Notes': variable['description'],
              'DataType': dataTypes[variable['domain']],
    }
    if variable['domain'] is bool:
        record['Values'] = 'True,False'
    elif variable['domain'] is list:
        record['Values'] = ','.join(variable['elements'])
    elif variable['domain'] is ActionSet:
        record['Values'] = ','.join(map(str,variable['elements']))
    elif variable['domain'] is float:
        record['Values'] = '[%4.2f-%4.2f]' % (variable['lo'],variable['hi'])
    elif variable['domain'] is int:
        record['Values'] = '[%d-%d]' % (variable['lo'],variable['hi'])
    else:
        raise TypeError('Unable to write values for variables of type %s' \
                        % (variable['domain'].__name__))
    if name in world.dynamics and not isRewardKey(name):
        record['VarType'] = 'dynamic'
    else:
        record['VarType'] = 'fixed'
    return record
    
def writeDefinition(world,dirName):
    with open(os.path.join(dirName,'VariableDefTable'),'w') as csvfile:
        fields = ['Name','LongName','Values','VarType','DataType','Notes']
        writer = csv.DictWriter(csvfile,fields,delimiter='\t',
                                extrasaction='ignore')
        writer.writeheader()
        # State variables
        stateKeys = [key for key in sorted(world.variables.keys()) \
                     if not isModelKey(key) and not isTurnKey(key) and not isBinaryKey(key)]
        for name in stateKeys:
            writer.writerow(var2def(name,world))
        for name,agent in world.agents.items():
            assert len(agent.models) == 1
            model = next(iter(agent.models.keys()))
            # Reward variables
            if isinstance(agent,Actor):
                for key,weight in agent.Rweights.items():
                    record = {'Name': '%sRewardWeightOf%s' % (agent.name,shorten(key)),
                              'LongName': 'Priority of %s to %s in reward function' % (key,agent.name),
                              'Values': '[0-1]',
                              'VarType': 'fixed',
                              'DataType': 'Real',
                              'Notes': 'Actor level'
                              }
                    writer.writerow(record)
            # Beliefs
            if agent.getAttribute('static',model) is None:
                belief = agent.getAttribute('beliefs',model)
                for key in stateKeys:
                    if key in belief and key in world.dynamics and not isRewardKey(key):
                        record = {'Name': '%sBeliefOf%s' % (agent.name,shorten(key)),
                                  'LongName': 'Probabilistic belief that %s has about %s' % (name,key),
                                  'Values': '[0-1]',
                                  'VarType': 'dynamic',
                                  'DataTye': 'Real',
                                  'Notes': '%s level' % (agent.__class__.__name__)
                                  }
                        writer.writerow(record)
                                  
    with open(os.path.join(dirName,'RelationshipDefTable'),'w') as csvfile:
        fields = ['Name','LongName','Values','Observable','VarType','DataType','Notes']
        writer = csv.DictWriter(csvfile,fields,delimiter='\t',
                                extrasaction='ignore')
        writer.writeheader()
        for name in sorted(world.variables.keys()):
            if isBinaryKey(name):
                writer.writerow(var2def(name,world))
                
def toCDF(world,dirName,unobservable=set()):
    day = world.getState(WORLD,'day').first()
    with open(os.path.join(dirName,'InstanceVariableTable'),'w') as csvfile:
        fields = ['Name','Timestep','Value']
        writer = csv.DictWriter(csvfile,fields,delimiter='\t',extrasaction='ignore')
        writer.writeheader()
        for name,variable in sorted(world.variables.items()):
            if isStateKey(name) or isBinaryKey(name):
                agent = state2agent(name)
                if agent == 'Nature' or (name in world.dynamics and day == 0):
                    value = world.getFeature(name)
                    assert len(value) == 1
                    record = {'Name': shorten(name),
                              'Value': value.first()}
                    if agent == 'Nature':
                        record['Timestep'] = day
                    writer.writerow(record)
    with open(os.path.join(dirName,'RunDataTable'),'w') as csvfile:
        fields = ['Timestep','VariableName','EntityIdx','Value','Notes']
        writer = csv.DictWriter(csvfile,fields,delimiter='\t',extrasaction='ignore')
        writer.writeheader()
    with open(os.path.join(dirName,'SummaryStatisticsDataTable'),'w') as csvfile:
        fields = ['Timestep','VariableName','EntityIdx','Value','Metadata']
        writer = csv.DictWriter(csvfile,fields,delimiter='\t',extrasaction='ignore')
        writer.writeheader()
    with open(os.path.join(dirName,'QualitativeDataTable'),'w') as csvfile:
        fields = ['Timestep','EntityIdx','QualData','Metadata']
        writer = csv.DictWriter(csvfile,fields,delimiter='\t',extrasaction='ignore')
        writer.writeheader()
    with open(os.path.join(dirName,'RelationshipDataTable'),'w') as csvfile:
        fields = ['Timestep','RelationshipType','Directed','FromEntityId','ToEntityId','Data','Notes']
        writer = csv.DictWriter(csvfile,fields,delimiter='\t',extrasaction='ignore')
        writer.writeheader()

def updateCDF(world,dirName,unobservable=set()):
    with open(os.path.join(dirName,'InstanceVariableTable'),'a') as csvfile:
        fields = ['Name','Timestep','Value']
        writer = csv.DictWriter(csvfile,fields,delimiter='\t',extrasaction='ignore')
        day = world.getState(WORLD,'day').first()
        for name,variable in sorted(world.variables.items()):
            if isStateKey(name) and state2agent(name) == 'Nature' and not isModelKey(name) \
               and not isTurnKey(name):
                value = world.getFeature(name)
                assert len(value) == 1
                record = {'Name': shorten(name),
                          'Timestep': day,
                          'Value': value.first()}
                writer.writerow(record)
    with open(os.path.join(dirName,'RunDataTable'),'a') as csvfile:
        fields = ['Timestep','VariableName','EntityIdx','Value','Notes']
        writer = csv.DictWriter(csvfile,fields,delimiter='\t',extrasaction='ignore')

    with open(os.path.join(dirName,'SummaryStatisticsDataTable'),'a') as csvfile:
        fields = ['Timestep','VariableName','EntityIdx','Value','Metadata']
        writer = csv.DictWriter(csvfile,fields,delimiter='\t',extrasaction='ignore')

    with open(os.path.join(dirName,'QualitativeDataTable'),'a') as csvfile:
        fields = ['Timestep','EntityIdx','QualData','Metadata']
        writer = csv.DictWriter(csvfile,fields,delimiter='\t',extrasaction='ignore')

    with open(os.path.join(dirName,'RelationshipDataTable'),'a') as csvfile:
        fields = ['Timestep','RelationshipType','Directed','FromEntityId','ToEntityId','Data','Notes']
        writer = csv.DictWriter(csvfile,fields,delimiter='\t',extrasaction='ignore')
        writer.writeheader()
