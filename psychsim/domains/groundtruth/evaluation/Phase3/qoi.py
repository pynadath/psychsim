from argparse import ArgumentParser
import copy
import csv
import logging
import os.path
import pickle
import random

from psychsim.pwl.keys import *
from psychsim.action import *
from psychsim.probability import Distribution
from psychsim.domains.groundtruth import accessibility

fields = {'SummaryStatisticsData': accessibility.fields['SummaryStatisticsData'],
    'RelationshipData': accessibility.fields['RelationshipData']
}

deadValue = {'health': 0.,'resources': 0.,'grievance': 1.}

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    args = {}
    variables = {}

#    for args['instance'] in range(301,322):
    for args['instance'] in range(332,333):
        config = accessibility.getConfig(args['instance'])
        for args['run'] in range(10):
            tables = {label: [] for label in fields}
            dirName = accessibility.getDirectory(args)
            # Load in initial simulation
            try:
                with open(os.path.join(dirName,'scenario0.pkl'),'rb') as f:
                    world = pickle.load(f)
            except FileNotFoundError:
                print(args['instance'],args['run'],'Skipping...')
                continue
            actors = sorted([name for name in world.agents if name[:5] == 'Actor'])
            regions = sorted([name for name in world.agents if name[:6] == 'Region'])
            shelters = [name for name in regions if stateKey(name,'shelterRisk') in world.variables]
            shelterObjs = {'shelter%s' % (name[-2:]) for name in shelters}
            states = {0: {'Nature': {name: world.agents[name].getBelief() for name in actors}}}
            states[0]['Nature']['__state__'] = world.state
            t = 0
            evacuees = set()
            shelterers = set()
            # Replay logged states and belief states
            while True:
                fname = os.path.join(dirName,'state%dNature.pkl' % (t+1))
                if not os.path.exists(fname):
                    # Presumably we have gone past the end of the simulation
                    break
                t += 1
                with open(fname,'rb') as f:
                    s = pickle.load(f)
                living = [name for name in actors if stateKey(name,'health') in s['__state__'].keys()]
                for feature in ['health','resources','grievance']:
                    var = stateKey('Actor',feature)
                    if var not in variables:
                        variables[var] = {'Name': var,'Values':'[0-1]','DataType': 'Real'}
                    values = [world.getState(name,feature,s['__state__']).expectation() for name in living]
                    tables['SummaryStatisticsData'].append({'Timestep': t,'VariableName': var,'EntityIdx': 'Actor[1-%d]' % (len(actors)),
                        'Value': sum(values)/len(actors),'Metadata': 'mean'})
                for name in living:
                    loc = world.getState(name,'location',s['__state__'],unique=True)
                    if loc == 'evacuated':
                        evacuees.add(name)
                    elif loc[:7] == 'shelter':
                        shelterers.add(name)

                    group = 'Group%s' % (world.agents[name].demographics['home'])
                    key = binaryKey(name,group,'memberOf')
                    if key in world.variables:
                        tables['RelationshipData'].append({'Timestep': t,'RelationshipType': 'memberOf','Directed': 'yes',
                            'FromEntityID': name,'ToEntityID': group,
                            'Data': 'yes' if world.getFeature(key,s['__state__'],True) else 'no'})
                var = 'Deaths'
                if var not in variables:
                    variables[var] = {'Name': var,'Values':'[0+]','DataType': 'Integer'}
                tables['SummaryStatisticsData'].append({'Timestep': t,'VariableName': var,'EntityIdx': 'Actor[1-%d]' % (len(actors)),
                    'Value': len(actors)-len(living),'Metadata': 'count(%s<%4.2f)' % 
                    (stateKey('Actor','health'),config.getfloat('Actors','life_threshold'))})

                var = 'Evacuees'
                if var not in variables:
                    variables[var] = {'Name': var,'Values':'[0+]','DataType': 'Integer'}
                tables['SummaryStatisticsData'].append({'Timestep': t,'VariableName': var,'EntityIdx': 'Actor[1-%d]' % (len(actors)),
                    'Value': len(evacuees),'Metadata': 'count(%s==evacuated)' % 
                    (stateKey('Actor','location'))})

                var = 'Sheltered'
                if var not in variables:
                    variables[var] = {'Name': var,'Values':'[0+]','DataType': 'Integer'}
                tables['SummaryStatisticsData'].append({'Timestep': t,'VariableName': var,'EntityIdx': 'Actor[1-%d]' % (len(actors)),
                    'Value': len(shelterers),'Metadata': 'count(%s==shelter)' % 
                    (stateKey('Actor','location'))})

            if t > 0:
                print(args['instance'],args['run'],'Days: %d' % (t))

                for name in actors:
                    agent = world.agents[name]
                    if agent.spouse:
                        tables['RelationshipData'].append({'Timestep': 1,'RelationshipType': 'marriedTo','Directed': 'yes',
                            'FromEntityID': name,'ToEntityID': agent.spouse,'Data': 'yes'})
                    for other in agent.getFriends():
                        tables['RelationshipData'].append({'Timestep': 1,'RelationshipType': 'friendOf','Directed': 'yes',
                            'FromEntityID': name,'ToEntityID': other,'Data': 'yes'})
                    for other in agent.getNeighbors():
                        tables['RelationshipData'].append({'Timestep': 1,'RelationshipType': 'neighborOf','Directed': 'yes',
                            'FromEntityID': name,'ToEntityID': other,'Data': 'yes'})

                for label,data in tables.items():
                    accessibility.writeOutput(args,data,fields[label],'%sTable.tsv' % (label))
            else:
                print(args['instance'],args['run'],'Skipping...')
    accessibility.writeVarDef(os.path.dirname(__file__),list(variables.values()))
