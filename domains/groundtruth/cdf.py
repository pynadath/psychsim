import csv
import os.path

from psychsim.pwl.keys import *
from psychsim.action import ActionSet
from psychsim.domains.groundtruth.actor import Actor
from psychsim.domains.groundtruth.region import Region

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
          'Population': ['Timestep','Deaths','Casualties','Evacuees','Sheltered'],
          'Regional': ['Timestep','Region','Deaths','Casualties','Sheltered'],
          }

def processDatum(agent,feature,funs,world,data):
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
                data['total'] += value
                data['count'] += 1
            elif fun == 'sum':
                data['total'] += value
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
                    if isinstance(target,str):
                        if value[:len(target)] == target:
                            # Handle prefixes (like "shelter...")
                            data['count'] += 1
                    elif value == target:
                        data['count'] += 1
                elif fun[5] == '<':
                    if value < target:
                        data['count'] += 1
                else:
                    raise ValueError('Unknown comparison: %s' % (fun[5]))

def computeValue(data,funs):
    if funs[-1] == 'mean':
        return data['total'] / float(data['count'])
    elif funs[-1] == 'sum':
        return data['total']
    elif funs[-1][:5] == 'count':
        return data['count']
    else:
        raise ValueError('Unknown functional value: %s' % (funs[-1]))
    
def appendSummary(datum,world,writer,fields,region=None):
    if len(datum) == 3:
        entities,feature,metadata = datum
        label = None
    else:
        assert len(datum) == 4
        entities,feature,metadata,label = datum
    funs = metadata.split(',')
    data = {'total': 0,
            'count': 0}
    if isinstance(entities,dict):
        entities = entities.values()
    recurse = False
    for agent in entities:
        if isinstance(agent,dict):
            # Region dictionary
            if agent['inhabitants']:
                appendSummary((agent['inhabitants'],feature,metadata,label),world,writer,
                              fields,agent['agent'].name)
                recurse = True
        else:
            processDatum(agent,feature,funs,world,data)
    if not recurse:
        generic = next(iter(entities)).__class__.__name__
        key = stateKey(generic,feature)
        entities = sorted([agent.name for agent in entities])
        first = int(entities[0][len(generic):])
        last = int(entities[-1][len(generic):])
        if last-first+1 == len(entities):
            idx = '[%s%d-%d]' % (generic,first,last)
        else:
            idx = '[%s]' % (','.join(entities))
        record = {}
        for field in fields:
            if field == 'VariableName':
                record[field] = shorten(key)
            elif field == 'EntityIdx':
                record[field] = idx
            elif field == 'Metadata':
                if label:
                    record[field] = label
                else:
                    record[field] = metadata
            elif field == 'Timestep':
                record[field] = world.getState(WORLD,'day').first()
            elif field != 'Value':
                raise RuntimeError('Unknown field: %s' % (field))
        record['Value'] = computeValue(data,funs)
        writer.writerow(record)

def agentRoot(name):
    if name[:5] == 'Actor':
        return 'Actor'
    elif name[:5] == 'Group':
        return 'Group'
    elif name[:6] == 'Region':
        return 'Region'
    else:
        return name
    
def shorten(key):
    if isBinaryKey(key):
        relation = key2relation(key)
        return '%s %s %s' % (agentRoot(relation['subject']),relation['relation'],
                             agentRoot(relation['object']))
    elif isStateKey(key):
        if isActionKey(key):
            return '%s action' % (agentRoot(state2agent(key)))
        elif state2agent(key) == WORLD:
            return '%s' % (state2feature(key))
        else:
            return '%s %s' % (agentRoot(state2agent(key)),state2feature(key))
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
    with open(os.path.join(dirName,'VariableDefTable.tsv'),'w') as csvfile:
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
                                  
    with open(os.path.join(dirName,'RelationshipDefTable.tsv'),'w') as csvfile:
        writer = csv.DictWriter(csvfile,fields['RelationshipDef'],delimiter='\t',
                                extrasaction='ignore')
        writer.writeheader()
        for name in sorted(world.variables.keys()):
            if isBinaryKey(name):
                writer.writerow(var2def(name,world))
        record = {'Name': 'Actor neighborOf Actor','LongName': 'Actor is neighbor of Actor',
                  'DataType': 'Boolean',
                  'Values': '[%s]' % (sorted([a.name for a in world.agents.values()
                                              if isinstance(a,Region)])),
                  }
        writer.writerow(record)
                         
                         
                
def toCDF(world,dirName,tables,unobservable=set()):
    day = world.getState(WORLD,'day').first()
    for name,table in tables.items():
        with open(os.path.join(dirName,'%sTable.tsv' % (name)),'w') as csvfile:
            writer = csv.DictWriter(csvfile,fields[name],delimiter='\t',extrasaction='ignore')
            writer.writeheader()
            if name == 'RelationshipData':
                for key,variable in world.variables.items():
                    if isBinaryKey(key):
                        relation = key2relation(key)
                        value = world.getFeature(key)
                        assert len(value) == 1
                        if key in world.dynamics or value.first():
                            record = {'RelationshipType': relation['relation'],
                                      'Directed': 'yes',
                                      'FromEntityId': relation['subject'],
                                      'ToEntityId': relation['object'],
                                      'Data': value.first()
                                      }
                            if key in world.dynamics:
                                record['Timestep'] = day
                            writer.writerow(record)
                neighbors = {}
                for name1 in world.agents:
                    agent1 = world.agents[name1]
                    if isinstance(agent1,Actor):
                        try:
                            neighbors[agent1.home].append(name1)
                        except KeyError:
                            neighbors[agent1.home] = [name1]
                for region,agents in neighbors.items():
                    for i in range(len(agents)-1):
                        for j in range(i+1,len(agents)):
                            record = {'RelationshipType': 'neighbor',
                                      'Directed': 'yes',
                                      'FromEntityId': agents[i],
                                      'ToEntityId': agents[j],
                                      'Data': region,
                            }
                            writer.writerow(record)
                            record['FromEntityId'] = agents[j]
                            record['ToEntityId'] = agents[i]
                            writer.writerow(record)
                    
            # elif name == 'InstanceVariable':
            #     for key,variable in sorted(world.variables.items()):
            #         if (isStateKey(key) and not isTurnKey(key) and not isModelKey(key) and \
            #             not isActionKey(key) and not isRewardKey(key)) or isBinaryKey(key):
            #             agent = state2agent(key)
            #             if agent != 'Nature':
            #                 if key in world.dynamics:
            #                     continue
            #                 elif day > 1:
            #                     continue
            #                 elif isinstance(world.agents[agent].O,dict) and key in world.agents[agent].O:
            #                     continue
            #                 value = world.getFeature(key)
            #                 assert len(value) == 1
            #                 record = {'Name': shorten(key),
            #                           'Value': value.first()}
            #                 if agent == 'Nature':
            #                     record['Timestep'] = day
            #                 writer.writerow(record)
            #     for agent in [a for a in world.agents.values() if isinstance(a,Actor)]:
            #         model = world.getModel(agent.name,world.state)
            #         assert len(model) == 1
            #         record = {'Name': '%sHorizon' % (agent.name),
            #                   'Value': agent.getAttribute('horizon',model.first())}
            #         writer.writerow(record)

def updateCDF(world,dirName,tables,unobservable=set()):
    stateKeys = [key for key in sorted(world.variables.keys()) \
                 if not isModelKey(key) and not isTurnKey(key) and not isBinaryKey(key)]
    day = world.getState(WORLD,'day').first()
    for name,table in tables.items():
        with open(os.path.join(dirName,'%sTable.tsv' % (name)),'a') as csvfile:
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
            elif name == 'QualitativeData':
                if len(table) > 1:
                    population = sorted([a.name for a in world.agents.values() if isinstance(a,Actor)])
                    for key,value in table[-1].items():
                        delta = value - table[-2][key]
                        if delta > len(population)/10:
                            record = {'Timestep': day,
                                      'EntityIdx': '[%s-%s]' % (population[0],population[-1]),
                                      'QualData': 'Many more people %s during this hurricane than the previous one.' % (key),
                                      'Metadata': 'Based on official records.'}
                            writer.writerow(record)
                        elif delta < -len(population)/10:
                            record = {'Timestep': day,
                                      'EntityIdx': '[%s-%s]' % (population[0],population[-1]),
                                      'QualData': 'Many fewer people %s during this hurricane than the previous one.' % (key),
                                      'Metadata': 'Based on official records.'}
                            writer.writerow(record)
            elif name == 'RunData':
                for key,variable in sorted(world.variables.items()):
                    if isStateKey(key) or isBinaryKey(key):
                        agent = state2agent(key)
                        if agent != 'Nature' and not isTurnKey(key) and not isModelKey(key) and not isRewardKey(key) and not isActionKey(key):
                            if key not in world.dynamics and day > 1:
                                continue
                            value = world.getFeature(key)
                            assert len(value) == 1
                            record = {'Value': value.first()}
                            if key in world.dynamics:
                                record['Timestep'] = day
                            else:
                                record['Timestep'] = 1
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
                    if agent.name != 'Nature' and not isinstance(agent,Region):
                        key = stateKey(agent.name,ACTION)
                        if key in world.state:
                            record = {'Timestep': day,
                                      'VariableName': shorten(key),
                                      'EntityIdx': agent.name,
                                      'Value': world.getFeature(key).first()}
                            writer.writerow(record)
                        if day == 1:
                            record = {'Timestep': 0,
                                      'VariableName': '%sHorizon' % (agent.name),
                                      'EntityIdx': agent.name,
                                      'Value': agent.getAttribute('horizon',model.first())}
                            writer.writerow(record)
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
                if isinstance(table,dict):
                    record = {}
                    regions = {}
                    for field in fields[name]:
                        if field == 'Timestep':
                            record[field] = day
                        elif field in table:
                            entities,feature,metadata = table[field]
                            if metadata:
                                funs = metadata.split(',')
                            data = {'total': 0,
                                    'count': 0}
                            for agent in entities:
                                if isinstance(agent,str):
                                    agent = world.agents[agent]
                                if isinstance(agent,Region) and metadata != 'sum':
                                    if not agent.name in regions:
                                        regions[agent.name] = {'Timestep': day,'Region': agent.name}
                                    if stateKey(agent.name,feature) in world.variables:
                                        assert metadata is None
                                        regions[agent.name][field] = agent.getState(feature).first()
                                    else:
                                        residents = [a for a in world.agents.values() \
                                                     if isinstance(a,Actor) and a.home == agent.name]
                                        data = {'total': 0,
                                                'count': 0}
                                        for actor in residents:
                                            processDatum(actor,feature,funs,world,data)
                                        regions[agent.name][field] = computeValue(data,funs)
                                else:
                                    processDatum(agent,feature,funs,world,data)
                            record[field] = computeValue(data,funs)
                        elif field != 'Region':
                            raise ValueError('Unknown field: %s' % (field))
                    if regions:
                        for name,record in regions.items():
                            writer.writerow(record)
                    else:
                        writer.writerow(record)
                else:
                    for datum in table:
                        appendSummary(datum,world,writer,fields[name])
