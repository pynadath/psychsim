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

def addRecord(var,desc,world,states,t,tables,actions,simLog):
    if desc['type'] == 'state':
        for name in desc['agents']:
            if stateKey(name,desc['variable']) in world.variables:
                if name == 'Nature':
                    record = {'Timestep': t, 'Name': var, 
                        'Value': accessibility.getInitialState(args,name,desc['variable'],world,states,t,unique=True)}
                    tables['InstanceVariable'].append(record)
                else:
                    record = {'Timestep': t, 'VariableName': var,'EntityIdx': name, 
                        'Value': accessibility.getInitialState(args,name,desc['variable'],world,states,t,unique=True)}
                    tables['RunData'].append(record)
    elif desc['type'] == 'belief':
        if t > 1:
            for name in desc['targets']:
                if name not in states[t-1]['Nature']:
                    if name[:5] == 'Group':
                        accessibility.loadState(args,states,t-1,'Nature',world)
                        beliefs = {name: world.agents[name].getBelief() for name in desc['targets']}
                        for name in desc['targets']:
                            for other in desc['agents']:
                                key = stateKey(other,desc['variable'])
                                if key in beliefs[name]:
                                    value = beliefs[name][key]
                                    record = {'Timestep': t, 'VariableName': var,'EntityIdx': name, 
                                        'Value': ','.join(['Pr(%s)=%5.3f' % (el,value[el]) for el in sorted(value.domain())])}
                                    tables['RunData'].append(record)
                    else:
                        desc['targets'].remove(name)
                    continue
                belief = states[t-1]['Nature'][name]
                if isinstance(belief,dict):
                    belief = next(iter(belief.values()))
                record = {'Timestep': t, 'VariableName': var,'EntityIdx': name} 
                others = [other for other in desc['agents'] if stateKey(other,desc['variable']) in belief]
                values = {other: world.getState(other,desc['variable'],belief) for other in others}
                record['Value'] = ','.join(sum([['Pr(%s=%s)=%5.3f' % (stateKey(other,desc['variable']),el,values[other][el]) 
                            for el in sorted(values[other].domain())] for other in others],[]))
#                    value = accessibility.getInitialState(args,other,desc['variable'],world,states,t,name)
#                    record['Value'] = ','.join(['Pr(%s)=%5.3f' % (el,value[el]) for el in sorted(value.domain())])
                tables['RunData'].append(record)
    elif desc['type'] == 'relationship':
        for fromEntity in desc['agents']:
            for toEntity in desc['targets']:
                key = binaryKey(fromEntity,toEntity,desc['variable'])
                if key in world.variables:
                    record = {'Timestep': t, 'RelationshipType': desc['variable'],'Directed': 'yes',
                        'FromEntityID': fromEntity, 'ToEntityID': toEntity}
                    record['Data'] = 'yes' if world.getFeature(key,unique=True) else 'no'
                    tables['RelationshipData'].append(record)
    elif desc['type'] == 'action':
        for name in desc['agents']:
            if name not in actions:
                actions[name] = accessibility.getAction(args,name,world,states,t)
            record = {'Timestep': t, 'VariableName': var,'EntityIdx': name}
            if desc['variable']['verb'] == 'moveTo' and desc['variable']['object'] == 'home':
                record['Value'] = 'yes' if actions[name]['verb'] == 'moveTo' and actions[name]['object'] == world.agents[name].demographics['home'] else 'no'
            elif desc['variable']['verb'] == 'moveTo' and desc['variable']['object'] == 'shelter':
                record['Value'] = 'yes' if actions[name]['verb'] == 'moveTo' and actions[name]['object'][:7] == 'shelter' else 'no'
            elif desc['variable']['verb'] == 'allocate':
                record['Value'] = actions[name]['object']
            else:
                record['Value'] = 'yes' if desc['variable']['verb'] == actions[name]['verb'] else 'no'
            tables['RunData'].append(record)
    elif desc['type'] == 'ER':
        if t > 1:
            for name in sorted(desc['agents']):
                # Death check
                if name[:5] == 'Actor':
                    accessibility.loadState(args,states,t,'Group')
                    try:
                        belief = next(iter(states[t]['Group'][name].values()))
                    except KeyError:
                        print('%s has died' % (name))
                        for entry in mapping.values():
                            try:
                                entry['agents'].remove(name)
                            except ValueError:
                                pass
                        continue
                    choices = world.agents[name].getActions(belief)
                    for choice in list(choices):
                        if choice['verb'] in {'join','leave'}:
                            group = world.getFeature(actionKey(choice['object']),belief,unique=True)
                            if group['verb'] == 'noDecision':
                                choices.remove(choice)
                action = accessibility.getAction(args,name,world,states,t)
                try:
                    result = {'V': {a: v for a,v in simLog[t][name].items() if a != '__horizon__'}}
                except KeyError:
                    assert len(choices) == 1
                    continue
                    if name[:5] == 'Group':
                        accessibility.loadState(args,states,t-1,'Nature',world)
                        belief = world.state
                    result = {'V': {}}
                    world.agents[name].decide(belief,others=set(),model=world.getModel(name,unique=True),debug=result['V'])
                if 'V' in result and len(result['V']) > 1:
                    V = result['V']
                    if action not in V:
                        if world.agents[name].spouse is None:
                            print('Missing action, no spouse %s: %s' % (action,','.join(sorted([a['verb'] for a in V]))))
                        else:
                            try:
                                other = accessibility.getAction(args,world.agents[name].spouse,world,states,t)
                                if other['verb'] != action['verb'] or other['object'] != action['object']:
                                    print('Missing action, spouse mismatch %s vs. %s: %s' % (action,other,','.join(sorted([a['verb'] for a in V]))))
                            except KeyError:
                                print('Missing action, deceased spouse %s: %s' % (action,','.join(sorted([a['verb'] for a in V]))))
                        continue
                    else:
                        # Test that actor/group chose action with highest ER
                        for alt,ER in V.items():
                            if alt != action and alt != '__horizon__' and V[action] < ER:
                                print(simLog[t][name])
                                if world.agents[name].spouse is None:
                                    print('Suboptimal. no spouse %s: %s' % (action,','.join(sorted(['%s: %f' % (a['verb'],V[a]) 
                                        for a in V]))))
                                    break
                                else:
                                    # Although actors can violate this constraint if following spouse's action choice
                                    try:
                                        other = accessibility.getAction(args,world.agents[name].spouse,world,states,t)
                                        if other['verb'] != action['verb'] or other['object'] != action['object']:
                                            print('Suboptimal, spouse mismatch %s vs. %s: %s' % (action,other,','.join(sorted([a['verb'] for a in V]))))
                                            break
                                    except KeyError:
                                        print('Suboptimal, deceased spouse %s: %s' % (action,','.join(sorted([a['verb'] for a in V]))))
                                        break
                        else:
                            # Verified optimal
                            record = {'Timestep': t, 'VariableName': var,'EntityIdx': name,
                                'Value': ','.join(['V(%s)=%6.3f' % (a,V[a]) for a in sorted(V,key=lambda k: str(k)) 
                                    if not isinstance(V[a],str)])}
                            tables['RunData'].append(record)
    else:
        raise TypeError('%s: %s' % (desc['type'],var))

if __name__ == '__main__':
    # Read in ground truth
    parser = ArgumentParser()
    parser.add_argument('-i','--instance',type=int,default=22,help='Instance to be processed')
    parser.add_argument('-r','--run',type=int,default=0,help='Run to be processed')
    parser.add_argument('-g','--graph',default='Annotated Phase 3 Graph USC.xlsx',help='File containing ground truth spreadsheet')
    parser.add_argument('-d','--data',help='File containing existing full data set')
    parser.add_argument('-l','--last',type=int,help='Last day')
    cmd = vars(parser.parse_args())
    if cmd['data']:
        oldRunData = {}
        for record in accessibility.loadMultiCSV(cmd['data'],cmd['instance'],cmd['run'],grabFields=False):
            oldRunData[record['Timestep']] = oldRunData.get(record['Timestep'],[])+[record]
            if cmd['last'] and record['Timestep'] and int(record['Timestep']) > cmd['last']:
                break
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
    tables = {'RunData': []}
    if cmd['data'] is None:
        tables['InstanceVariable'] = []
        tables['RelationshipData'] = []

    if cmd['data'] is None:
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
    else:
        accessibility.writeOutput(args,oldRunData[''],accessibility.fields['RunData'],'RunDataTable_R2.tsv')
    # Dynamic variables
    dynamic = set(variables.keys()) - static
    simLog = accessibility.readLog(args)
    for t in range(1,args['span'] if cmd['last'] is None else cmd['last']+1):
        print(t)
        tables = {'RunData': []}
        actions = {}
        if cmd['data'] is None:
            tables['InstanceVariable'] = []
            tables['RelationshipData'] = []
        else:
            tables['RunData'] += oldRunData[str(t)]
        for var in sorted(dynamic):
            if cmd['data'] is None:
                addRecord(var,mapping[var],world,states,t,tables,actions,simLog)
            elif mapping[var]['type'] == 'ER':
                old = [record for record in oldRunData[str(t)] if record['VariableName'] == var]
                if len(old) == 0:
                    addRecord(var,mapping[var],world,states,t,tables,actions,simLog)
        states.clear()
        if cmd['data'] is None:
            for label,data in tables.items():
                accessibility.writeOutput(args,data,accessibility.fields[label],'%sTable_full.tsv' % (label),append=True)
        else:
            accessibility.writeOutput(args,tables['RunData'],accessibility.fields['RunData'],'RunDataTable_R2.tsv',append=True)
