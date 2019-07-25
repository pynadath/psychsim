import csv
import os.path

from psychsim.probability import Distribution
from psychsim.pwl.keys import *
from psychsim.action import *
from psychsim.domains.groundtruth.simulation.actor import Actor
from psychsim.domains.groundtruth.simulation.region import Region

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

def value2dist(value,notes=None,cls=None):
    if ',' in value:
        probs = [float(v) for v in value.split(',')]
        if cls is None:
            domain = [value2dist(el[6:-1]) for el in notes.split(',')]
        else:
            domain = [cls(el[6:-1]) for el in notes.split(',')]
        value = Distribution({domain[i]: probs[i] for i in range(len(domain))})
        return value
    elif cls is not None:
        return cls(value)
    elif value == 'True':
        return True
    elif value == 'False':
        return False
    elif '.' in value:
        return float(value)
    elif '-' in value:
        return Action(value)
    else:
        try:
            return int(value)
        except ValueError:
            return value


def makeCDFTables(population,regions,regionTable):
    """Setup entity lists for CDF tables
    """
    return {'InstanceVariable': [],
                 'RunData': [],
                 'SummaryStatisticsData':
                 [(population,'alive','count=False','Deaths'),
                  (population,'health','count<0.2','Casualties'),
                  (population,'location','count=evacuated','Evacuees'),
                  (population,'location','count=shelter','Sheltered'),
                  (population,'health','mean','Wellbeing'),
                  (population,'resources','mean','Wealth'),
                  (regions,'risk','invert,mean','Safety'),
                  (population,ACTION,'count=decreaseRisk','Prosocial'),
                  (population,ACTION,'count=takeResources','Antisocial'),
                  (regionTable,'health','mean','Regional Wellbeing'),
                  (regionTable,'alive','count=False','Regional Deaths'),
                  (regionTable,'health','count<0.2','Regional Casualties'),
                  (regionTable,'location','count=shelter','Regional Sheltered'),
                 ],
                 'QualitativeData': [],
                 'RelationshipData': [],
                 'Population': {'Deaths': (population,'alive','count=False'),
                                'Casualties': (population,'health','count<0.2'),
                                'Evacuees': (population,'location','count=evacuated'),
                                'Sheltered': (population,'location','count=shelter'),
                 },
                 'Regional': {'Deaths': (regionTable,'alive','count=False'),
                              'Casualties': (regionTable,'health','count<0.2'),
                              'Sheltered': (regionTable,'location','count=shelter')
                 },
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
        if region:
            idx = region
        elif last-first+1 == len(entities):
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
                    record[field] = record['VariableName']
                    record['VariableName'] = label
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
                                record['Timestep'] = world.getState(WORLD,'day').first()
                            writer.writerow(record)
                neighbors = {}
                for name1 in world.agents:
                    agent1 = world.agents[name1]
                    if isinstance(agent1,Actor):
                        try:
                            neighbors[agent1.demographics['home']].append(name1)
                        except KeyError:
                            neighbors[agent1.demographics['home']] = [name1]
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
                    population = sorted([name for name in world.agents if name[:5] == 'Actor'])
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
                            if key not in world.dynamics and day > 1: # TODO: What about observations?
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
                            record = {'Timestep': 1,
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
                                                     if isinstance(a,Actor) and a.demographics['home'] == agent.name]
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

def addRunDatum(world,name,feature,variable,t,table,state=None,agent=None):
    if agent is None:
        agent = name
    if state is None:
        state = world.state
    key = stateKey(agent,feature)
    if key in world.variables:
        tables['RunData'].append({'Timestep': t, 'VariableName': variable, 'EntityIdx': name})
        value = world.getFeature(key,state)
        if len(value) == 1:
            value = value.first()
            if world.variables[key]['domain'] is bool:
                tables['RunData'][-1]['Value'] = 'yes' if value else 'no'
            elif feature == 'location' and name[:5] == 'Actor':
                if value[:6] == 'Region':
                    assert value == world.agents[name].demographics['home']
                    tables['RunData'][-1]['Value'] = 'home'
                elif value[:7] == 'shelter':
                    tables['RunData'][-1]['Value'] = 'shelter'
                else:
                    tables['RunData'][-1]['Value'] = value
            else:
                tables['RunData'][-1]['Value'] = value
        else:
            tables['RunData'][-1]['Value'] = ','.join(['Pr(%s)=%5.2f%%' % (el,value[el]*100) for el in sorted(value.domain())])

def addSummary(world,state,actors,regions,t,table):
    living = {name for name in actors if world.getState(name,'alive',state).first()}
    table.append({'Timestep': t,'VariableName': 'Deaths','EntityIdx': 'Actor[0001-%04d]' % (len(actors)),
        'Value': len(actors)-len(living),'Metadata': 'Actor\'s health<0.01'})
    table.append({'Timestep': t,'VariableName': 'Casualties','EntityIdx': 'Actor[0001-%04d]' % (len(actors)),
        'Value': len([name for name in actors if float(world.getState(name,'health',state)) < 0.2]),'Metadata': 'Actor\'s health<0.2'})
    table.append({'Timestep': t,'VariableName': 'Evacuees','EntityIdx': 'Actor[0001-%04d]' % (len(actors)),
        'Value': len([name for name in living if world.getState(name,'location',state).first() == 'evacuated']),'Metadata': 'Actor\'s location=evacuated'})
    table.append({'Timestep': t,'VariableName': 'Sheltered','EntityIdx': 'Actor[0001-%04d]' % (len(actors)),
        'Value': len([name for name in living if world.getState(name,'location',state).first()[:7] == 'sheltered']),'Metadata': 'Actor\'s location=shelter*'})
    table.append({'Timestep': t,'VariableName': 'Wellbeing','EntityIdx': 'Actor[0001-%04d]' % (len(actors)),
        'Value': sum([float(world.getState(name,'health',state)) for name in living])/len(living),'Metadata': 'mean(Actor\'s health)'})
    table.append({'Timestep': t,'VariableName': 'Wealth','EntityIdx': 'Actor[0001-%04d]' % (len(actors)),
        'Value': sum([float(world.getState(name,'resources',state)) for name in living])/len(living),'Metadata': 'mean(Actor\'s resources)'})
    table.append({'Timestep': t,'VariableName': 'Dissatisfaction','EntityIdx': 'Actor[0001-%04d]' % (len(actors)),
        'Value': sum([float(world.getState(name,'grievance',state)) for name in living])/len(living),'Metadata': 'mean(Actor\'s grievance)'})
    table.append({'Timestep': t,'VariableName': 'Safety','EntityIdx': 'Region[01-%02d]' % (len(regions)),
        'Value': sum([1.-float(world.getState(name,'risk',state)) for name in regions])/len(regions),'Metadata': 'mean(1-Region\'s risk)'})
    for region in regions:
        residents = {name for name in actors if world.agents[name].demographics['home'] == region}
        table.append({'Timestep': t,'VariableName': 'Regional Deaths','EntityIdx': ','.join(sorted(residents)),
            'Value': len(residents-living),'Metadata': 'Actor\'s health<0.01'})
        table.append({'Timestep': t,'VariableName': 'Regional Casualties','EntityIdx': ','.join(sorted(residents)),
            'Value': len([name for name in residents if float(world.getState(name,'health',state)) < 0.2]),'Metadata': 'Actor\'s health<0.2'})
        table.append({'Timestep': t,'VariableName': 'Regional Evacuees','EntityIdx': ','.join(sorted(residents)),
            'Value': len([name for name in residents&living if world.getState(name,'location',state).first() == 'evacuated']),
            'Metadata': 'Actor\'s location=evacuated'})
        table.append({'Timestep': t,'VariableName': 'Regional Sheltered','EntityIdx': ','.join(sorted(residents)),
            'Value': len([name for name in residents&living if world.getState(name,'location',state).first()[:7] == 'sheltered']),
            'Metadata': 'Actor\'s location=shelter*'})
        table.append({'Timestep': t,'VariableName': 'Regional Wellbeing','EntityIdx': ','.join(sorted(residents)),
            'Value': sum([float(world.getState(name,'health',state)) for name in living&residents])/len(living&residents),
            'Metadata': 'mean(Actor\'s health)'})

if __name__ == '__main__':
    from argparse import ArgumentParser
    import csv
    import logging
    import pickle

    from psychsim.domains.groundtruth import accessibility

    parser = ArgumentParser()
    parser.add_argument('-i','--instance',default=90,type=int,help='Number of instance to process')
    parser.add_argument('-r','--run',default=0,type=int,help='Number of run to process')
    parser.add_argument('--definition',action='store_true',help='Write simulation definition tables')
    parser.add_argument('-d','--debug',default='WARNING',help='Level of logging detail')
    args = vars(parser.parse_args())
    # Extract logging level from command-line argument
    level = getattr(logging, args['debug'].upper(), None)
    if not isinstance(level, int):
        raise ValueError('Invalid debug level: %s' % args['debug'])
    logging.basicConfig(level=level)

    config = accessibility.getConfig(args['instance'])
    dirName = accessibility.getDirectory(args)
    order = ['Actor','System','Nature']
    tables = {'VariableDef': [],
        'RelationshipDef': [],
        'InstanceVariable': [],
        'RunData': [],
        'SummaryStatisticsData': [],
        'QualitativeData': [],
        'RelationshipData': []}
    fields['RelationshipDef'] = ['Name','LongName','Values','RelType','DataType','Notes']
    # Load in initial simulation
    with open(os.path.join(dirName,'scenario0.pkl'),'rb') as f:
        world = pickle.load(f)
    actors = sorted([name for name in world.agents if name[:5] == 'Actor'])
    for proto in actors:
        if stateKey(proto,'childrenHealth') in world.variables and stateKey(proto,'pet') in world.variables:
            break
    else:
        raise ValueError('Unable to find actor with children and pet')
    living = actors
    regions = sorted([name for name in world.agents if name[:6] == 'Region'])
    shelters = [name for name in regions if stateKey(name,'shelterRisk') in world.variables]
    # Fixed variables
    variable = 'Actor\'s home'
    tables['VariableDef'].append({'Name': variable,'LongName': 'Actor\'s region of residence',
        'Values': ','.join(regions),'VarType': 'fixed','DataType': 'String'})
    for name in actors:
        tables['RunData'].append({'VariableName': variable,'EntityIdx': name,'Value': world.agents[name].demographics['home']})
    variable = 'Actor\'s horizon'
    tables['VariableDef'].append({'Name': variable,'LongName': 'Actor\'s short/farsightedness',
        'Values': '[1,Inf)','VarType': 'fixed','DataType': 'Integer'})
    for name in actors:
        agent = world.agents[name]
        tables['RunData'].append({'VariableName': variable,'EntityIdx': name,'Value': agent.getAttribute('horizon',next(iter(agent.models)))})
    for feature in ['childrenHealth','health','neighbors','pet','resources']:
        variable = 'Actor\'s priority of %s' % (feature)
        tables['VariableDef'].append({'Name': variable,'LongName': variable,
            'Values': '[0,1]','VarType': 'fixed','DataType': 'Real'})
        for name in actors:
            agent = world.agents[name]
            tables['RunData'].append({'VariableName': variable,'EntityIdx': name,'Value': agent.Rweights[feature]})
    variable = 'Region\'s shelterPets'
    tables['VariableDef'].append({'Name': variable,'LongName': 'Region\'s shelter allows pets',
        'Values': 'yes,no','VarType': 'fixed','DataType': 'Boolean'})
    for name in shelters:
        tables['RunData'].append({'VariableName': variable,'EntityIdx': name,'Value': 'yes' if world.getState(name,'shelterPets').first() else 'no'})
    for variable in ['friendOf','neighborOf']:
        tables['RelationshipDef'].append({'Name': variable,'LongName': 'Actor %s Actor' % (variable),'Values': 'yes,no','RelType': 'fixed',
            'DataType': 'Boolean'})
        for name in actors:
            if variable == 'friendOf':
                others = world.agents[name].friends
            elif variable == 'neighborOf':
                others = {other for other in actors if other != name and 
                    world.agents[other].demographics['home'] == world.agents[name].demographics['home']}
            else:
                raise NameError('Unknown relationship: %s' % (variable))
            for other in actors:
                if other > name:
                    tables['RelationshipData'].append({'RelationshipType': variable,'Directed': 'no','FromEntityId': name,'ToEntityId': other,'Data': 'yes'})
    # Dynamic variables
    for behaviors in world.agents['Actor0001'].actions:
        action = Action(next(iter(behaviors)))
        action['subject'] = 'Actor'
        if 'object' in action:
            action['object'] = action['object'][:-2]
        tables['VariableDef'].append({'Name': str(action),'LongName': str(action),'Values': 'yes,no','VarType': 'dynamic','DataType': 'Boolean'})
    action = next(iter(next(iter(world.agents['System'].actions))))
    action['object'] = 'Region'
    tables['VariableDef'].append({'Name': str(action),'LongName': str(action),'Values': ','.join(regions),'VarType': 'dynamic',
        'DataType': 'String'})
    # Expected Reward
    tables['VariableDef'].append({'Name': 'Actor\'s Expected Reward','LongName': 'Actor\'s Expected Reward over Actions','Values': '(-Inf,Inf)',
        'VarType': 'dynamic','DataType': 'Real','Notes': 'Table of Real values for each action'})
    # Extract variables associated with true state
    dynamic = {}
    beliefs = {'Actor\'s risk','Nature\'s category','Region\'s risk','Region\'s shelterRisk'}
    summary = {'alive'}
    for key,definition in sorted(world.variables.items()):
        name,feature = state2tuple(key)
        if key not in world.dynamics and (world.agents[name].O is True or key not in world.agents[name].O):
            # Static state feature or system state feature
            continue        
        if feature in summary or name == WORLD:
            continue
        assert not isModelKey(key) and not isTurnKey(key) and not isRewardKey(key) and not isActionKey(key)
        if name in actors:
            variable = stateKey('Actor',feature)
            define = name == proto
        elif name in regions:
            variable = stateKey('Region',feature)
            define = name == shelters[0]
        else:
            variable = key
            define = True
        if define:
            # Set up variable definition for this state variable
            dynamic[state2agent(variable)] = dynamic.get(state2agent(variable),[]) + [feature]
            tables['VariableDef'].append({'Name': variable,'LongName': variable,'VarType': 'dynamic'})
            if definition['domain'] is bool:
                tables['VariableDef'][-1]['Values'] = 'yes,no'
                tables['VariableDef'][-1]['DataType'] = 'Boolean'
            elif definition['domain'] is float:
                tables['VariableDef'][-1]['Values'] = '[0,1]'
                tables['VariableDef'][-1]['DataType'] = 'Real'
            elif definition['domain'] is int:
                tables['VariableDef'][-1]['Values'] = '0,1,2,3,4,5'
                tables['VariableDef'][-1]['DataType'] = 'Integer'
            elif definition['domain'] is list:
                tables['VariableDef'][-1]['Values'] = ','.join(definition['elements'])
                if variable == 'Actor\'s location':
                    tables['VariableDef'][-1]['Values'] = tables['VariableDef'][-1]['Values'].replace(world.agents[name].demographics['home'],'home')
                    for region in shelters:
                        tables['VariableDef'][-1]['Values'] = tables['VariableDef'][-1]['Values'].replace('shelter%s' % (region[-2:]),'shelter')
                tables['VariableDef'][-1]['DataType'] = 'String'
            else:
                raise TypeError('Unknown variable domain: %s' % (definition['domain']))
        # Initial values
        if name == 'Nature':
            tables['InstanceVariable'].append({'Name': variable,'Timestep': 1,'Value': world.getFeature(key).first()})
        else:
            addRunDatum(world,name,feature,variable,1,tables['RunData'])
        # Define subjective perception variables
        if variable in beliefs:
            if define:
                tables['VariableDef'].append({'Name': 'ActorBeliefOf%s' % (variable),'LongName': 'Actor\'s Subjective Perception of %s' % (variable),
                    'Values': tables['VariableDef'][-1]['Values'],'VarType': 'dynamic', 'DataType': 'Real','Notes': 'Probability distribution over possible values'})
    for features in dynamic.values():
        features.sort()
    # Initial beliefs
    for name in living:
        belief = next(iter(world.agents[name].getBelief().values()))
        for variable in beliefs:
            if variable[:5] == 'Actor':
                addRunDatum(world,name,state2feature(variable),'ActorBeliefOf%s' % (variable),1,tables['RunData'],belief,name)
            elif variable == 'Region\'s risk':
                addRunDatum(world,name,state2feature(variable),'ActorBeliefOf%s' % (variable),1,tables['RunData'],
                    belief,world.agents[name].demographics['home'])
            elif variable == 'Region\'s shelterRisk':
                assert len(shelters) == 1
                addRunDatum(world,name,state2feature(variable),'ActorBeliefOf%s' % (variable),1,tables['RunData'],belief,shelters[0])
            else:
                assert variable[:6] == 'Nature'
                addRunDatum(world,name,state2feature(variable),'ActorBeliefOf%s' % (variable),1,tables['RunData'],belief,'Nature')
    # Initial summary stats
    addSummary(world,world.state,actors,regions,1,tables['SummaryStatisticsData'])
    t = 1
    turn = 0

    # Replay logged states and belief states
    while True:
        fname = os.path.join(dirName,'state%d%s.pkl' % (t,order[turn]))
        if not os.path.exists(fname):
            # Presumably we have gone past the end of the simulation
            break
        print(t,turn)
        with open(fname,'rb') as f:
            s = pickle.load(f)
        if order[turn] == 'Actor':
            for name in living:
                for behaviors in world.agents[name].actions:
                    match = world.getFeature(actionKey(name),s['__state__']).first() == behaviors
                    action = Action(next(iter(behaviors)))
                    action['subject'] = 'Actor'
                    if 'object' in action:
                        action['object'] = action['object'][:-2]
                    tables['RunData'].append({'Timestep': t,'VariableName': str(action),'EntityIdx': name,'Value': 'yes' if match else 'no'})
        elif order[turn] == 'System':
            action = world.getFeature(actionKey('System'),s['__state__']).first()
            tables['RunData'].append({'Timestep': t,'VariableName': 'System-allocate-Region','EntityIdx': 'System','Value': action['object']})
        elif order[turn] == 'Nature':
            for agent,features in dynamic.items():
                for feature in features:
                    variable = stateKey(agent,feature)
                    if agent == 'Actor':
                        for name in living:
                            addRunDatum(world,name,feature,variable,t+1,tables['RunData'],s['__state__'])
                    elif agent == 'Region':
                        for name in regions:
                            addRunDatum(world,name,feature,variable,t+1,tables['RunData'],s['__state__'])
            # Beliefs
            for name in living:
                assert len(s[name]) == 1
                belief = next(iter(s[name].values()))
                for variable in beliefs:
                    if variable[:5] == 'Actor':
                        addRunDatum(world,name,state2feature(variable),'ActorBeliefOf%s' % (variable),1,tables['RunData'],belief,name)
                    elif variable == 'Region\'s risk':
                        addRunDatum(world,name,state2feature(variable),'ActorBeliefOf%s' % (variable),1,tables['RunData'],
                            belief,world.agents[name].demographics['home'])
                    elif variable == 'Region\'s shelterRisk':
                        assert len(shelters) == 1
                        addRunDatum(world,name,state2feature(variable),'ActorBeliefOf%s' % (variable),1,tables['RunData'],belief,shelters[0])
                    else:
                        assert variable[:6] == 'Nature'
                        addRunDatum(world,name,state2feature(variable),'ActorBeliefOf%s' % (variable),1,tables['RunData'],belief,'Nature')
        # Summary stats
        addSummary(world,s['__state__'],actors,regions,t+1,tables['SummaryStatisticsData'])
        living = [name for name in living if world.getState(name,'alive',s['__state__']).first()]
        turn += 1
        if turn == len(order):
            turn = 0
            t += 1
    for label,data in tables.items():
        if label[-3:] == 'Def':
            if args['definition']:
                accessibility.writeOutput(args,data,fields[label],'%sTable.tsv' % (label),
                    os.path.join(os.path.dirname(__file__),'..','SimulationDefinition'))
        else:
            accessibility.writeOutput(args,data,fields[label],'%sTable.tsv' % (label))
