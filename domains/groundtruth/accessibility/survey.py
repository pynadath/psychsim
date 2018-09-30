from argparse import ArgumentParser
import csv
import os
import pickle
import random
import sys

from psychsim.pwl.keys import *
from psychsim.world import World
from psychsim.domains.groundtruth.data import toLikert

if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('instance',type=int,help='Instance to query')
    parser.add_argument('survey',help='File with survey questions')
    parser.add_argument('-o','--output',default='RequestSurvey.tsv',help='Output filename')
    parser.add_argument('-r','--run',type=int,default=0,help='Run to query')
    parser.add_argument('-s','--samples',type=int,default=10,help='Number of people to survey')
    args = vars(parser.parse_args())

    root = os.path.join(os.path.dirname(__file__),'..')
    inFile = os.path.join(root,'Instances','Instance%d' % (args['instance']),
                          'Runs','run-%d' % (args['run']),'scenario.pkl')
    with open(inFile,'rb') as f:
        world = pickle.load(f)

    survey = []
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
                    assert survey[item]['action']['entity'] == 'self'
                    result = actor.decide(selection='distribution')
                    for key in result:
                        if key != 'policy':
                            result = result[key]
                            break
                    total = 0.
                    for action in result['action'].domain():
                        if action['verb'] == survey[item]['action']['feature']:
                            target = survey[item]['action']['value']
                            if action['object'][:len(target)] == target:
                                total += result['action'][action]
                    samples[-1]['Response%d' % (item+1)] = toLikert(total)
            writer.writerow(samples[-1])
