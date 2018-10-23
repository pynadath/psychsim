from argparse import ArgumentParser
import csv
import os
import pickle
import random
import sys

from psychsim.pwl.keys import *
from psychsim.action import Action
from psychsim.world import World
from ..simulation.data import toLikert

if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('instance',type=int,help='Instance to query')
    parser.add_argument('survey',help='File with survey questions')
    parser.add_argument('-o','--output',default='RequestSurvey.tsv',help='Output filename')
    parser.add_argument('-r','--run',type=int,default=0,help='Run to query')
    parser.add_argument('-s','--samples',type=int,default=10,help='Number of people to survey')
    parser.add_argument('--seed',type=int,default=None,help='Random number generator seed')
    args = vars(parser.parse_args())

    random.seed(args['seed'])
    root = os.path.join(os.path.dirname(__file__),'..')
    inFile = os.path.join(root,'Instances','Instance%d' % (args['instance']),
                          'Runs','run-%d' % (args['run']),'scenario.pkl')
    with open(inFile,'rb') as f:
        world = pickle.load(f)

    survey = []
    obs = {}
    with open(args['survey'],'r') as csvfile:
        reader = csv.DictReader(csvfile,delimiter='\t')
        for row in reader:
            item = int(row['item'])
            while len(survey) < item:
                survey.append({'conditions': {}})
            if row['type'] == 'condition':
                key = stateKey(row['entity'],row['feature'])
                value = row['value']
                if key in world.variables:
                    if world.variables[key]['domain'] is int:
                        value = int(value)
                survey[item-1]['conditions'][key] = value
            elif row['type'] == 'action':
                survey[item-1]['action'] = row
            elif row['type'] == 'belief':
                survey[item-1]['belief'] = row
                if row['value'] == 'delta':
                    obs[item-1] = {}
                    if row['entity'] == 'self':
                        obs[item-1]['variable'] = 'Actor %s' % (row['feature'])
                    else:
                        raise NameError('Unable to process entity %s' % (row['entity']))
            elif row['type'] == 'observation':
                survey[item-1]['observation'] = row
                obs[item-1] = {'variable': 'System action',
                               'target': row,
                               'action': True,
                               'histogram': {}}

    if obs:
        inFile = os.path.join(root,'Instances','Instance%d' % (args['instance']),
                              'Runs','run-%d' % (args['run']),'RunDataTable.tsv')
        with open(inFile,'r') as csvfile:
            reader = csv.DictReader(csvfile,delimiter='\t')
            for row in reader:
                for item,entry in obs.items():
                    if row['VariableName'] == entry['variable']:
                        if 'action' in entry:
                            value = Action(row['Value'])['object']
                            entry['histogram'][value] = entry['histogram'].get(value,0)+1
                        else:
                            value = row['Value']
                            if row['EntityIdx'] not in entry:
                                entry[row['EntityIdx']] = []
                            entry[row['EntityIdx']].append(float(value))
                                
    actors = [actor for actor in world.agents.values() if actor.name[:5] == 'Actor' and \
              actor.getState('alive').first()]
    numSamples = min(args['samples'],len(actors))

    outFile = os.path.join(root,'Instances','Instance%d' % (args['instance']),
                           'Runs','run-%d' % (args['run']),args['output'])
    fields = ['ParticipantId'] + ['Response%d' % (item+1) for item in range(len(survey))]
    with open(outFile,'w') as csvfile:
        writer = csv.DictWriter(csvfile,fields,delimiter='\t',extrasaction='ignore')
        writer.writeheader()
        samples = []
        while len(samples) < numSamples:
            actor = random.choice(actors)
            actors.remove(actor)
            samples.append({})
            samples[-1]['ParticipantId'] = len(samples)
            model = world.getModel(actor.name,world.state)
            assert len(model) == 1
            model = model.first()
            for item in range(len(survey)):
                for key,value in survey[item]['conditions'].items():
                    if state2agent(key) == 'self':
                        key = stateKey(actor.name,state2feature(key))
                    if isinstance(value,str) and isStateKey(value):
                        if state2agent(value) == 'self':
                            value = stateKey(actor.name,state2feature(value))
                        value = world.getFeature(value)
                    actor.setBelief(key,value,model)
                if 'action' in survey[item]:
                    assert 'belief' not in survey[item],'Cannot have both "action" and "belief" in same survey item'
                    assert survey[item]['action']['entity'] == 'self'
                    result = actor.decide(selection='distribution')
                    for key in result:
                        if key != 'policy':
                            result = result[key]
                            break
                    value = 0.
                    for action in result['action'].domain():
                        if action['verb'] == survey[item]['action']['feature']:
                            target = survey[item]['action']['value']
                            if action['object'][:len(target)] == target:
                                value += result['action'][action]
                elif 'belief' in survey[item]:
                    if survey[item]['belief']['value'] == 'delta':
                        history = obs[item][actor.name]
                        nadir = min(history)
                        value = (history[0]-nadir)/history[0]
                    else:
                        belief = actor.getBelief(model=model)
                        if survey[item]['belief']['entity'] == 'self':
                            key = stateKey(actor.name,survey[item]['belief']['feature'])
                        else:
                            key = stateKey(survey[item]['belief']['entity'],
                                           survey[item]['belief']['feature'])
                        value = world.getFeature(key,belief).expectation()
                elif 'observation' in survey[item]:
                    target = obs[item]['target']['value']
                    total = None
                    if isStateKey(target):
                        entity = state2agent(target)
                        feature = state2feature(target)
                        if entity == 'self':
                            entity = actor.name
                        myValue = world.getFeature(stateKey(entity,feature),belief).first()
                        if feature == 'region':
                            total = len([region for region in world.agents if region[:6] == 'Region'])
                    else:
                        myValue = target
                    if total is None:
                        raise NameError('Unable to find range for value %s' % (target))
                    cutoff = obs[item]['histogram'][myValue]
                    more = 0
                    for action,count in obs[item]['histogram'].items():
                        if count > cutoff:
                            more += 1
                    value = float(total-more)/float(total)
                else:
                    raise ValueError('No actionable field in survey item')
                samples[-1]['Response%d' % (item+1)] = toLikert(value)
            writer.writerow(samples[-1])
