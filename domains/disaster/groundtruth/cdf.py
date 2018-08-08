import csv
import os.path

from psychsim.pwl.keys import CONSTANT,makeFuture,rewardKey
from psychsim.action import ActionSet

dataTypes = {bool: 'Boolean',
             list: 'String',
             float: 'Real',
             ActionSet: 'String',
             int: 'Integer'}

def toCDF(world,unobservable=set()):
    with open(os.path.join('SimulationDefinition','VariableDefTable'),'w') as csvfile:
        fields = ['Name','LongName','Values','Observable','VarType','DataType','Notes']
        writer = csv.DictWriter(csvfile,fields,delimiter='\t',
                                extrasaction='ignore')
        writer.writeheader()
        for name,variable in sorted(world.variables.items()):
            record = {'Name': name,
                      'Long name': name,
                      'Notes': variable['description'],
                      'Observable': {True: 1, False: 0}[not name in unobservable],
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
                raise TypeError,'Unable to write values for variables of type %s' \
                    % (variable['domain'].__name__)
            if name in world.dynamics:
                record['Type'] = 'dynamic'
            else:
                record['Type'] = 'fixed'
            writer.writerow(record)
        for name,agent in world.agents.items():
            tree = agent.models['%s0' % (agent.name)]['R']
            if tree.isLeaf():
                vector = tree.children[None][makeFuture(rewardKey(name))]
                if len(vector) == 1 and abs(vector[CONSTANT]) < 1e-8:
                    continue
            record = {'Name': 'Reward%s' % (name),
                      'LongName': '%s\'s Reward' % (name),
                      'Values': '[-1.0-1.0]',
                      'Observable': 0,
                      'Type': 'dynamic',
                      }
            writer.writerow(record)
