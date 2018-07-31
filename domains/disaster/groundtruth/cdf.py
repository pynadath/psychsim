import csv

def toCDF(world):
    with open('ActorVariableDefTable.txt','w') as csvfile:
        fields = ['Name','LongName','Values','Observable','Type','Notes']
        writer = csv.DictWriter(csvfile,fields,delimiter='\t',
                                extrasaction='ignore')
#        writer.writeheader()
        agent = world.agents['Actor00']
        for name,variable in world.variables.items():
            if keys.isStateKey(name) and keys.state2agent(name) == 'Actor00':
                if not keys.isTurnKey(name) and not keys.isActionKey(name):
                    feature = keys.state2feature(name)
                    record = {'Name': feature,
                              'Notes': variable['description'],
                              'Observable': 1,
                              }
                    if variable['domain'] is bool:
                        record['Values'] = 'True,False'
                    elif variable['domain'] is list:
                        record['Values'] = ','.join(variable['elements'])
                    elif variable['domain'] is float:
                        record['Values'] = '%4.2f-%4.2f' % (variable['lo'],variable['hi'])
                    else:
                        raise TypeError,'Unable to write values for variables of type %s' \
                            % (variable['domain'])
                    if name in world.dynamics:
                        record['Type'] = 'dynamic'
                    else:
                        record['Type'] = 'fixed'
                    writer.writerow(record)
        for tree,weight in agent.models['%s0' % (agent.name)]['R'].items():
            assert tree.isLeaf(),'Unable to write nonlinear reward components to CDF'
            vector = tree.children[None]
            assert len(vector) == 1,'Unable to write combined reward componetns to CDF'
            feature = keys.state2feature(vector.keys()[0])
            record = {'Name': 'R(%s)' % (feature),
                      'LongName': 'Reward from %s' % (feature),
                      'Values': '-1.0-1.0',
                      'Observable': 0,
                      'Type': 'fixed',
                      }
            writer.writerow(record)
    with open('GroupVariableDefTable.txt','w') as csvfile:
        pass
    with open('SystemVariableDefTable.txt','w') as csvfile:
        pass
    os.mkdir('Instances')
    os.chdir('Instances')
    for instance in range(1):
        os.mkdir('Instance%d' % (instance+1))
        os.chdir('Instance%d' % (instance+1))
        with open('InstanceParameterTable.txt','w') as csvfile:
            pass
        os.mkdir('Runs')
        os.chdir('Runs')
        for run in range(1):
            os.mkdir('run-%d' % (run))
            os.chdir('run-%d' % (run))
            with open('RunDataTable.txt','w') as csvfile:
                fields = ['Timestep','VariableName','EntityIdx','Name','Value']
                writer = csv.DictWriter(csvfile,fields,delimiter='\t',
                                        extrasaction='ignore')
                for name,variable in world.variables.items():
                    if keys.isStateKey(name):
                        if not keys.isTurnKey(name) and not keys.isActionKey(name):
                            value = world.getFeature(name)
                            assert len(value) == 1,'Unable to write uncertain values to CDF'
                            value = value.domain()[0]
                            record = {'Timestep': 0,
                                      'VariableName': name,
                                      'EntityIdx': keys.state2agent(name),
                                      'Name': keys.state2feature(name),
                                      'Value': value}
                            writer.writerow(record)
