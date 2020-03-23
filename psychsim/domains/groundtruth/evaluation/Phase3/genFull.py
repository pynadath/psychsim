from argparse import ArgumentParser
import openpyxl
import os.path
import random
import sys

from psychsim.pwl import *
from psychsim.action import Action
from psychsim.domains.groundtruth import accessibility

attributes = {'information distortion': 'distortion',
    'beliefAggregation': 'aggregator'}

if __name__ == '__main__':
    # Read in ground truth
    parser = ArgumentParser()
    parser.add_argument('-i','--instance',type=int,default=22,help='Instance to be processed')
    parser.add_argument('-r','--run',type=int,default=0,help='Run to be processed')
    parser.add_argument('-g','--graph',default='Annotated Phase 3 Graph USC.xlsx',help='File containing ground truth spreadsheet')
    cmd = vars(parser.parse_args())
    wb = openpyxl.load_workbook(cmd['graph'])
    variables = {}
    static = set()
    first = True
    for row in wb['Nodes'].values:
        if first:
            first = False
        else:
            var = row[1]
            variables[var] = {'Name': var,'DataType': row[3]}
            for attr in list(attributes.keys())+['priority','magnification','friendOf','neighborOf','marriedTo','horizon',
                'home','ethnicGroup','religion']:
                if attr in var and '-' not in var:
                    variables[var]['VarType'] = 'static'
                    static.add(var)
                    break
            if variables[var]['DataType'] == 'Boolean':
                variables[var]['Values'] = 'yes,no'
            else:
                terms = variables[var]['DataType'].split()
                if len(terms) == 3:
                    variables[var]['DataType'] = terms[0]
                    variables[var]['Values'] = terms[2]
                elif len(terms) == 2 and terms[1] == 'integer':
                    variables[var]['DataType'] = terms[1].capitalize()
                    if terms[0] == 'Positive':
                        variables[var]['Values'] = '[1+]'
                    elif terms[0] == 'Nonnegative':
                        variables[var]['Values'] = '[0+]'
                    else:
                        raise NameError(terms[0])
                elif terms[0][:6] == 'String':
                    variables[var]['DataType'] = terms[0][:6]
                    variables[var]['Values'] = ' '.join(terms[1:])
                elif terms[0][:6] == 'Region':
                    variables[var]['Values'] = variables[var]['DataType']
                    variables[var]['DataType'] = 'String'
                elif terms[0] == 'Probability':
                    variables[var]['DataType'] = 'String'
                    variables[var]['Values'] = 'Pr(%s)=Real' % (terms[-1])
                elif terms[0] == 'Real':
                    assert terms[-2] == 'action' and terms[-1] == 'choice'
                    variables[var]['DataType'] = 'String'
                    variables[var]['Values'] = 'V(action)=Real'
                else:
                    raise RuntimeError(variables[var]['DataType'])
            if not isStateKey(var) and len(var.split()) == 3:
                variables[var]['RelType'] = variables[var].get('VarType','dynamic')
    accessibility.writeVarDef(os.path.dirname(__file__),[entry for entry in variables.values() if 'RelType' not in entry])
    accessibility.writeVarDef(os.path.dirname(__file__),[entry for entry in variables.values() if 'RelType' in entry],True)
    # Map GT variables to simulation variables
    args = accessibility.instances[cmd['instance']-1]
    print('Instance %d (%d,%d)' % (cmd['instance'],args['instance'],args['run']))
    config = accessibility.getConfig(args['instance'])
    parameters = {'magnification': config.getint('Groups','magnification')}
    world = accessibility.unpickle(cmd['instance'])
    # Identify relevant ground truth variables
    mapping = {}
    for var in variables:
        mapping[var] = {'type': None,'agents': []}
        if isStateKey(var):
            if 'BeliefOf' in var:
                agent = var[:var.index('BeliefOf')]
                mapping[var]['targets'] = sorted([name for name in world.agents if name[:len(agent)] == agent])
                key = var[var.index('BeliefOf')+len('BeliefOf'):]
                mapping[var]['type'] = 'belief'
            else:
                mapping[var]['type'] = 'state'
                key = var
            agent,feature = state2tuple(key)
            mapping[var]['agents'] = sorted([name for name in world.agents if name[:len(agent)] == agent])
            if feature == 'horizon':
                mapping[var]['type'] = 'model attribute'
                mapping[var]['variable'] = feature
            elif feature in attributes:
                mapping[var]['type'] = 'attribute'
                mapping[var]['variable'] = attributes[feature]
            elif 'priority' in feature:
                mapping[var]['type'] = 'reward'
                mapping[var]['variable'] = var.split()[-1]
                if mapping[var]['variable'] == 'pets':
                    mapping[var]['variable'] = 'pet'
            elif feature == 'Expected Reward':
                mapping[var]['type'] = 'ER'
            elif feature in parameters:
                mapping[var]['type'] = 'parameter'
                mapping[var]['variable'] = parameters[feature]
            else:
                for name in mapping[var]['agents']:
                    if stateKey(name,feature) in world.variables:
                        mapping[var]['variable'] = feature
                        break
                else:
                    for name in mapping[var]['agents']:
                        if agent  == 'Actor' and feature in world.agents[name].demographics:
                            mapping[var]['variable'] = feature
                            mapping[var]['type'] = 'demographic'
                            break
                    else:
                        raise NameError(var)
        elif '-' in var:
            # Action
            mapping[var]['variable'] = action = Action(var)
            mapping[var]['type'] = 'action'
            mapping[var]['agents'] = sorted([name for name in world.agents if name[:len(action['subject'])] == action['subject']])            
        else:
            terms = var.split()
            if len(terms) == 3:
                mapping[var]['agents'] = sorted([name for name in world.agents if name[:len(terms[0])] == terms[0]])
                mapping[var]['type'] = 'relationship'
                mapping[var]['variable'] = terms[1]
                mapping[var]['targets'] = sorted([name for name in world.agents if name[:len(terms[2])] == terms[2]])
            else:
                raise NameError(var)
    # Let's get logging
    states = {}
    tables = {'RunData': [],'InstanceVariable': [],'RelationshipData': []}
    # Fixed variables
    for var in sorted(static):
        if mapping[var]['type'] == 'state':
            for name in mapping[var]['agents']:
                record = {'VariableName': var,'EntityIdx': name, 'Value': world.getState(name,mapping[var]['variable'],unique=True)}
                tables['RunData'].append(record)
        elif mapping[var]['type'] == 'relationship':
            for fromEntity in mapping[var]['agents']:
                if mapping[var]['variable'] == 'neighborOf':
                    for toEntity in world.agents[fromEntity].getNeighbors():
                        record = {'RelationshipType': mapping[var]['variable'],'Directed': 'yes',
                            'FromEntityID': fromEntity, 'ToEntityID': toEntity,'Data': 'yes'}
                        tables['RelationshipData'].append(record)
                elif mapping[var]['variable'] == 'friendOf':
                    for toEntity in world.agents[fromEntity].getFriends():
                        record = {'RelationshipType': mapping[var]['variable'],'Directed': 'yes',
                            'FromEntityID': fromEntity, 'ToEntityID': toEntity,'Data': 'yes'}
                        tables['RelationshipData'].append(record)
                elif mapping[var]['variable'] == 'marriedTo':
                    if world.agents[fromEntity].spouse is not None:
                        record = {'RelationshipType': mapping[var]['variable'],'Directed': 'yes',
                            'FromEntityID': fromEntity, 'ToEntityID': world.agents[fromEntity].spouse,'Data': 'yes'}
                        tables['RelationshipData'].append(record)
                else:
                    raise NameError('Unknown static relationship: %s' % (mapping[var]['variable']))
                    for toEntity in mapping[var]['targets']:
                        key = binaryKey(fromEntity,toEntity,mapping[var]['variable'])
                        if key in world.variables:
                            record = {'RelationshipType': mapping[var]['variable'],'Directed': 'yes',
                                'FromEntityID': fromEntity, 'ToEntityID': toEntity,
                                'Data': 'yes' if world.getFeature(key,unique=True) else 'no'}
                            tables['RelationshipData'].append(record)
        elif mapping[var]['type'] == 'model attribute':
            for name in mapping[var]['agents']:
                value = world.agents[name].getAttribute(mapping[var]['variable'])
                assert len(value) == 1
                record = {'VariableName': var,'EntityIdx': name, 'Value': next(iter(value.values()))}
                tables['RunData'].append(record)
        elif mapping[var]['type'] == 'parameter':
            for name in mapping[var]['agents']:
                record = {'VariableName': var,'EntityIdx': name, 'Value': mapping[var]['variable']}
                tables['RunData'].append(record)
        elif mapping[var]['type'] == 'reward':
            for name in mapping[var]['agents']:
                record = {'VariableName': var,'EntityIdx': name, 'Value': world.agents[name].Rweights[mapping[var]['variable']]}
                tables['RunData'].append(record)
        elif mapping[var]['type'] == 'demographic':
            for name in mapping[var]['agents']:
                record = {'VariableName': var,'EntityIdx': name, 'Value': world.agents[name].demographics[mapping[var]['variable']]}
                tables['RunData'].append(record)
        elif mapping[var]['type'] == 'attribute':
            for name in mapping[var]['agents']:
                record = {'VariableName': var,'EntityIdx': name, 'Value': world.agents[name].__dict__[mapping[var]['variable']]}
                tables['RunData'].append(record)
        else:
            raise TypeError(mapping[var]['type'])
    for label,data in tables.items():
        accessibility.writeOutput(args,data,accessibility.fields[label],'%sTable.tsv' % (label))
    # Dynamic variables
    dynamic = set(variables.keys()) - static
    simLog = accessibility.readLog(args)
    for t in range(1,args['span']):
        tables = {'RunData': [],'InstanceVariable': [],'RelationshipData': []}
        print(t)
        actions = {}
        for var in sorted(dynamic):
            if mapping[var]['type'] == 'state':
                for name in mapping[var]['agents']:
                    if stateKey(name,mapping[var]['variable']) in world.variables:
                        if name == 'Nature':
                            record = {'Timestep': t, 'Name': var, 
                                'Value': accessibility.getInitialState(args,name,mapping[var]['variable'],world,states,t,unique=True)}
                            tables['InstanceVariable'].append(record)
                        else:
                            record = {'Timestep': t, 'VariableName': var,'EntityIdx': name, 
                                'Value': accessibility.getInitialState(args,name,mapping[var]['variable'],world,states,t,unique=True)}
                            tables['RunData'].append(record)
            elif mapping[var]['type'] == 'belief':
                if t > 1:
                    for name in mapping[var]['targets']:
                        if name not in states[t-1]['Nature']:
                            if name[:5] == 'Group':
                                accessibility.loadState(args,states,t-1,'Nature',world)
                                beliefs = {name: world.agents[name].getBelief() for name in mapping[var]['targets']}
                                for name in mapping[var]['targets']:
                                    for other in mapping[var]['agents']:
                                        key = stateKey(other,mapping[var]['variable'])
                                        if key in beliefs[name]:
                                            value = beliefs[name][key]
                                            record = {'Timestep': t, 'VariableName': var,'EntityIdx': name, 
                                                'Value': ','.join(['Pr(%s)=%5.3f' % (el,value[el]) for el in sorted(value.domain())])}
                                            tables['RunData'].append(record)
                            else:
                                mapping[var]['targets'].remove(name)
                            continue
                        belief = states[t-1]['Nature'][name]
                        if isinstance(belief,dict):
                            belief = next(iter(belief.values()))
                        for other in mapping[var]['agents']:
                            if stateKey(other,mapping[var]['variable']) in belief:
                                value = accessibility.getInitialState(args,other,mapping[var]['variable'],world,states,t,name)
                                record = {'Timestep': t, 'VariableName': var,'EntityIdx': name, 
                                    'Value': ','.join(['Pr(%s)=%5.3f' % (el,value[el]) for el in sorted(value.domain())])}
                                tables['RunData'].append(record)
            elif mapping[var]['type'] == 'relationship':
                for fromEntity in mapping[var]['agents']:
                    for toEntity in mapping[var]['targets']:
                        key = binaryKey(fromEntity,toEntity,mapping[var]['variable'])
                        if key in world.variables:
                            record = {'Timestep': t, 'RelationshipType': mapping[var]['variable'],'Directed': 'yes',
                                'FromEntityID': fromEntity, 'ToEntityID': toEntity}
                            record['Data'] = 'yes' if world.getFeature(key,unique=True) else 'no'
                            tables['RelationshipData'].append(record)
            elif mapping[var]['type'] == 'action':
                for name in mapping[var]['agents']:
                    if name not in actions:
                        actions[name] = accessibility.getAction(args,name,world,states,t)
                    record = {'Timestep': t, 'VariableName': var,'EntityIdx': name}
                    if mapping[var]['variable']['verb'] == 'moveTo' and mapping[var]['variable']['object'] == 'home':
                        record['Value'] = 'yes' if actions[name]['verb'] == 'moveTo' and actions[name]['object'] == world.agents[name].demographics['home'] else 'no'
                    elif mapping[var]['variable']['verb'] == 'moveTo' and mapping[var]['variable']['object'] == 'shelter':
                        record['Value'] = 'yes' if actions[name]['verb'] == 'moveTo' and actions[name]['object'][:7] == 'shelter' else 'no'
                    elif mapping[var]['variable']['verb'] == 'allocate':
                        record['Value'] = actions[name]['object']
                    else:
                        record['Value'] = 'yes' if mapping[var]['variable']['verb'] == actions[name]['verb'] else 'no'
                    tables['RunData'].append(record)
            elif mapping[var]['type'] == 'ER':
                if t > 1:
                    for name in list(mapping[var]['agents']):
                        # Death check
                        if name[:5] == 'Actor':
                            accessibility.loadState(args,states,t,'Group')
                            try:
                                belief = next(iter(states[t]['Group'][name].values()))
                            except KeyError:
                                print('%s has died' % (name))
                                for var,entry in mapping.items():
                                    try:
                                        entry['agents'].remove(name)
                                    except ValueError:
                                        pass
                                continue
                        try:
                            result = {'V': simLog[t][name]}
                        except KeyError:
                            if name[:5] == 'Group':
                                accessibility.loadState(args,states,t-1,'Nature',world)
                                belief = world.state
                            result = world.agents[name].decide(belief,others=set(),model=world.getModel(name,unique=True))
                        if 'V' in result and len(result['V']) > 1:
                            V = result['V']
                            action = accessibility.getAction(args,name,world,states,t)
                            for alt,ER in V.items():
                                if alt != action and V[action] < ER:
                                    # Test that actor/group chose action with highest ER
                                    print('%s: %s' % (action,V))
                                    if name[:5] == 'Actor' and world.agents[name].spouse is not None:
                                        try:
                                            # Although actors can violate this constraint if following spouse's action choice
                                            print('\t%s' % (accessibility.getAction(args,world.agents[name].spouse,world,states,t)))
                                        except KeyError:
                                            pass
                                    break
                            else:
                                record = {'Timestep': t, 'VariableName': var,'EntityIdx': name,
                                    'Value': ','.join(['V(%s)=%6.3f' % (a,V[a]) for a in sorted(V)])}
                                tables['RunData'].append(record)
            else:
                raise TypeError('%s: %s' % (mapping[var]['type'],var))
        states.clear()
        for label,data in tables.items():
            accessibility.writeOutput(args,data,accessibility.fields[label],'%sTable.tsv' % (label),append=True)
