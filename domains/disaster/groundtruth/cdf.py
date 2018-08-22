import csv
import os.path

from psychsim.pwl.keys import *
from psychsim.action import ActionSet

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
        for name in sorted(world.variables.keys()):
            if isModelKey(name) or isTurnKey(name) or isBinaryKey(name):
                continue
            # State variables
            writer.writerow(var2def(name,world))
        for name,agent in world.agents.items():
            # Reward variables
            model = '%s0' % (agent.name)
            tree = agent.models[model]['R']
            if tree.isLeaf():
                vector = tree.children[None][makeFuture(rewardKey(name))]
                if len(vector) == 1 and abs(vector[CONSTANT]) < 1e-8:
                    continue
            record = {'Name': 'Reward%s' % (name),
                      'LongName': '%s\'s Reward' % (name),
                      'Values': '[-1.0-1.0]',
                      'Type': 'dynamic',
                      }
            writer.writerow(record)
            # Beliefs
            belief = agent.getBelief(world.state,model)
            for name in belief.keys():
                pass
    with open(os.path.join('SimulationDefinition','RelationshipDefTable'),'w') as csvfile:
        fields = ['Name','LongName','Values','Observable','VarType','DataType','Notes']
        writer = csv.DictWriter(csvfile,fields,delimiter='\t',
                                extrasaction='ignore')
        writer.writeheader()
        for name in sorted(world.variables.keys()):
            if isBinaryKey(name):
                writer.writerow(var2def(name,world))
                
def toCDF(world,dirName,unobservable=set()):
    with open(os.path.join(dirName,'InstanceVariableTable'),'w') as csvfile:
        fields = ['Name','Timestep','Value']
        writer = csv.DictWriter(csvfile,fields,delimiter='\t',extrasaction='ignore')
        writer.writeheader()
        for name,variable in sorted(world.variables.items()):
            if isStateKey(name):
                agent = state2agent(name)
                if not agent in {WORLD,'Nature'}:
                    if name in world.dynamics or isRewardKey(name) or isTurnKey(name) or isModelKey(name):
                        continue
                value = world.getFeature(name)
                assert len(value) == 1
                record = {'Name': shorten(name),
                          'Value': value.first()}
                writer.writerow(record)

def updateCDF(world,unobservable=set()):
    with open(os.path.join('SimulationDefinition','InstanceVariableTable'),'a') as csvfile:
        fields = ['Name','Timestep','Value']
        writer = csv.DictWriter(csvfile,fields,delimiter='\t',extrasaction='ignore')
        writer.writeheader()
        day = world.getState(WORLD,'day').first()
        for name,variable in sorted(world.variables.items()):
            if isStateKey(name):
                agent = state2agent(name)
                if agent in {WORLD,'Nature'}:
                    value = world.getFeature(name)
                    assert len(value) == 1
                    record = {'Name': shorten(name),
                              'Timestep': day,
                              'Value': value.first()}
                    writer.writerow(record)
                        
