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

fields = {'VariableDef': ['Name','LongName','Values','VarType','DataType','Notes'],
          'RelationshipDef': ['Name','LongName','Values','Observable','VarType','DataType',
                                   'Notes'],
          'InstanceVariable': ['Name','Timestep','Value'],
          'RunData': ['Timestep','VariableName','EntityIdx','Value','Notes'],
          'SummaryStatisticsData': ['Timestep','VariableName','EntityIdx','Value','Metadata'],
          'QualitativeData': ['Timestep','EntityIdx','QualData','Metadata'],
          'RelationshipData': ['Timestep','RelationshipType','Directed','FromEntityId',
                               'ToEntityId','Data','Notes'],
          }

def appendDatum(datum,world,writer,fields):
    entities,feature,metadata = datum
    funs = metadata.split(',')
    total = 0.
    count = 0
    for agent in entities:
        key = stateKey(agent.name,feature)
        if key in world.variables:
            dist = world.getState(agent.name,feature)
            assert len(dist) == 1
            value = dist.first()
            for fun in funs:
                if fun == 'invert':
                    if isinstance(value,bool):
                        value = not bool
                    else:
                        value = 1.-value
                elif fun == 'mean':
                    total += value
                    count += 1
                elif fun == 'sum':
                    total += value
                elif fun[:5] == 'count':
                    target = fun[6:]
                    if isinstance(value,bool):
                        if target == 'False':
                            target = False
                        else:
                            target = True
                    elif feature == ACTION:
                        value = value['verb']
                    else:
                        target = value.__class__(target)
                    if fun[5] == '=':
                        if value == target:
                            count += 1
                    elif fun[5] == '<':
                        if value < target:
                            count += 1
                    else:
                        raise ValueError('Unknown comparison: %s' % (fun[5]))
    generic = entities[0].__class__.__name__
    key = stateKey(generic,feature)
    entities = sorted([agent.name for agent in entities])
    first = int(entities[0][len(generic):])
    last = int(entities[-1][len(generic):])
    record = {'Timestep': world.getState(WORLD,'day').first(),
              'VariableName': shorten(key),
              'EntityIdx': '[%s%d-%d]' % (generic,first,last),
              'Metadata': metadata,
              }
    if funs[-1] == 'mean':
        record['Value'] = total / float(count)
    elif funs[-1] == 'sum':
        record['Value'] = total
    elif funs[-1][:5] == 'count':
        record['Value'] = count
    else:
        raise ValueError('Unknown functional value: %s' % (funs[-1]))
    writer.writerow(record)

def shorten(key):
    if isBinaryKey(key):
        relation = key2relation(key)
        return '%s %s %s' % (relation['subject'],relation['relation'],relation['object'])
    elif isStateKey(key):
        if isActionKey(key):
            return '%s action' % (state2agent(key))
        elif state2agent(key) == WORLD:
            return '%s' % (state2feature(key))
        else:
            return '%s %s' % (state2agent(key),state2feature(key))
    else:
        return key

def var2def(name,world,base=None):
    if base is None:
        base = name
    variable = world.variables[base]
    record = {'Name': shorten(name),
              'Notes': variable['description'],
              'DataType': dataTypes[variable['domain']],
    }
    if isActionKey(name):
        record['LongName'] = '%s\'s Action Choice' % (state2agent(name))
    else:
        record['LongName'] = name
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
        writer = csv.DictWriter(csvfile,fields['VariableDef'],delimiter='\t',
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
            if isinstance(agent,Actor):
                # Reward variables
                for key,weight in agent.Rweights.items():
                    record = {'Name': '%sRewardWeightOf%s' % (agent.name,shorten(key)),
                              'LongName': 'Priority of %s to %s in reward function' % (key,agent.name),
                              'Values': '[0-1]',
                              'VarType': 'fixed',
                              'DataType': 'Real',
                              'Notes': 'Actor level'
                              }
                    writer.writerow(record)
                # Horizon
                record = {'Name': '%sHorizon' % (agent.name),
                          'LongName': 'Lookahead Horizon for %s\'s Expected Reward' % (agent.name),
                          'Values': '[1-Inf]',
                          'VarType': 'fixed',
                          'DataType': 'Integer',
                          'Notes': 'Actor level. Number of days into the future that the actor looks when evaluating candidate behaviors'
                          }
                writer.writerow(record)
            # Beliefs
            if agent.getAttribute('static',model) is None:
                belief = agent.getAttribute('beliefs',model)
                for key in stateKeys:
                    if key in belief and key in world.dynamics and not isRewardKey(key):
                        record = {'Name': '%s\'s Belief Of%s' % (agent.name,shorten(key)),
                                  'LongName': 'Probabilistic belief that %s has about %s' % (name,key),
                                  'Values': '[0-1]',
                                  'VarType': 'dynamic',
                                  'DataTye': 'Real',
                                  'Notes': '%s level' % (agent.__class__.__name__)
                                  }
                        writer.writerow(record)
                                  
    with open(os.path.join(dirName,'RelationshipDefTable'),'w') as csvfile:
        writer = csv.DictWriter(csvfile,fields['RelationshipDef'],delimiter='\t',
                                extrasaction='ignore')
        writer.writeheader()
        for name in sorted(world.variables.keys()):
            if isBinaryKey(name):
                writer.writerow(var2def(name,world))
                
def toCDF(world,dirName,tables,unobservable=set()):
    day = world.getState(WORLD,'day').first()
    for name,table in tables.items():
        with open(os.path.join(dirName,'%sTable' % (name)),'w') as csvfile:
            writer = csv.DictWriter(csvfile,fields[name],delimiter='\t',extrasaction='ignore')
            writer.writeheader()
            if name == 'InstanceVariable':
                for key,variable in sorted(world.variables.items()):
                    if (isStateKey(key) and not isTurnKey(key) and not isModelKey(key) and \
                        not isRewardKey(key)) or isBinaryKey(key):
                        agent = state2agent(key)
                        if agent != 'Nature':
                            if key in world.dynamics:
                                continue
                            elif day > 1:
                                continue
                            elif isinstance(world.agents[agent].O,dict) and key in world.agents[agent].O:
                                continue
                            value = world.getFeature(key)
                            assert len(value) == 1
                            record = {'Name': shorten(key),
                                      'Value': value.first()}
                            if agent == 'Nature':
                                record['Timestep'] = day
                            writer.writerow(record)
                for agent in [a for a in world.agents.values() if isinstance(a,Actor)]:
                    model = world.getModel(agent.name,world.state)
                    assert len(model) == 1
                    record = {'Name': '%sHorizon' % (agent.name),
                              'Value': agent.getAttribute('horizon',model.first())}
                    writer.writerow(record)
            elif name == 'RelationshipData':
                for key,variable in world.variables.items():
                    if isBinaryKey(key):
                        relation = key2relation(key)
                        value = world.getFeature(key)
                        assert len(value) == 1
                        record = {'RelationshipType': relation['relation'],
                                  'Directed': 'yes',
                                  'FromEntityId': relation['subject'],
                                  'ToEntityId': relation['object'],
                                  'Data': value.first()
                                  }
                        if key in world.dynamics:
                            record['Timestep'] = day
                        writer.writerow(record)
            elif name == 'RunData':
                pass
#            else:
#                for datum in table:
#                    appendDatum(datum,world,writer,fields[name])

def updateCDF(world,dirName,tables,unobservable=set()):
    stateKeys = [key for key in sorted(world.variables.keys()) \
                 if not isModelKey(key) and not isTurnKey(key) and not isBinaryKey(key)]
    day = world.getState(WORLD,'day').first()
    for name,table in tables.items():
        with open(os.path.join(dirName,'%sTable' % (name)),'a') as csvfile:
            writer = csv.DictWriter(csvfile,fields[name],delimiter='\t',extrasaction='ignore')
            if name == 'InstanceVariable':
                for key,variable in sorted(world.variables.items()):
                    if isStateKey(key) and state2agent(key) == 'Nature' and not isModelKey(key) \
                       and not isTurnKey(key):
                        value = world.getFeature(key)
                        assert len(value) == 1
                        record = {'Name': shorten(key),
                                  'Timestep': day,
                                  'Value': value.first()}
                        writer.writerow(record)
            elif name == 'RelationshipData':
                for key,variable in world.variables.items():
                    if isBinaryKey(key) and key in world.dynamics:
                        relation = key2relation(key)
                        value = world.getFeature(key)
                        assert len(value) == 1
                        record = {'Timestep': day,
                                  'RelationshipType': relation['relation'],
                                  'Directed': 'yes',
                                  'FromEntityId': relation['subject'],
                                  'ToEntityId': relation['object'],
                                  'Data': value.first()}
                        writer.writerow(record)
            elif name == 'RunData':
                for key,variable in sorted(world.variables.items()):
                    if isStateKey(key) or isBinaryKey(key):
                        agent = state2agent(key)
                        if agent != 'Nature' and key in world.dynamics:
                            value = world.getFeature(key)
                            assert len(value) == 1
                            record = {'Timestep': day,
                                      'Value': value.first(),
                                      }
                            if agent in world.agents:
                                generic = stateKey(world.agents[agent].__class__.__name__,
                                                   state2feature(key))
                                record['VariableName'] = shorten(generic)
                                record['EntityIdx'] = agent
                            else:
                                record['VariableName'] = state2feature(key)
                            writer.writerow(record)
                for agent in world.agents.values():
                    model = world.getModel(agent.name,world.state)
                    assert len(model) == 1
                    if agent.getAttribute('static',model.first()) is None:
                        belief = agent.getAttribute('beliefs',model.first())
                        for key in stateKeys:
                            if key in belief and key in world.dynamics and not isRewardKey(key):
                                value = world.getFeature(key,belief)
                                record = {'Timestep': day,
                                          'VariableName': '%sBeliefOf%s' % (agent.__class__.__name__,
                                                                            shorten(key)),
                                          'EntityIdx': agent.name}
                                if len(value) == 1:
                                    record['Value'] = value.first()
                                    record['Notes'] = 'Belief with certainty'
                                else:
                                    domain = sorted(value.domain())
                                    record['Notes'] = ','.join(['Prob(=%s)' % (el) for el in domain])
                                    record['Value'] = ','.join(['%6.4f' % (value[el]) for el in domain])
                                writer.writerow(record)
            else:
                for datum in table:
                    appendDatum(datum,world,writer,fields[name])
