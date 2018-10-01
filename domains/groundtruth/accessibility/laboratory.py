from argparse import ArgumentParser
import csv
import os
import pickle
import random
import sys

from psychsim.pwl.keys import *
from psychsim.world import World

def countAntisocial(world):
    newState = world.step(select=True)
    joint = world.explainAction(newState,level=1)
    count = {}
    for name,action in joint.items():
        assert len(action) == 1
        act = action.first()
        if act['verb'] in ['takeResources','increaseRisk']:
            count[act['object']] = count.get(act['object'],0) + 1
    return count

if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('instance',type=int,help='Instance to query')
    parser.add_argument('-o','--output',default='RequestLaboratory.tsv',help='Output filename')
    parser.add_argument('-r','--run',type=int,default=0,help='Run to query')
    parser.add_argument('-s','--samples',type=int,default=1,help='Number of people to survey')
    args = vars(parser.parse_args())

    root = os.path.join(os.path.dirname(__file__),'..')
    inFile = os.path.join(root,'Instances','Instance%d' % (args['instance']),
                          'Runs','run-%d' % (args['run']),'scenario.pkl')
    with open(inFile,'rb') as f:
        world = pickle.load(f)

    actors = [actor for actor in world.agents.values() if actor.name[:5] == 'Actor' and
              actor.getState('alive').first()]
    preCount = countAntisocial(world)

    all = list(preCount.keys())
    shelters = {'shelter%s' % (name[-2:]) for name in world.agents
                if stateKey(name,'shelterRisk') in world.variables}

    regions = set()
    for i in range(args['samples']):
        region = random.choice(all)
        all.remove(region)
        regions.add(region)

    while True:
        agents = world.next()
        turn = world.agents[next(iter(agents))].__class__.__name__
        if turn == 'Actor':
            break
        world.step(select=True)

    for region in regions:
        residents = {actor for actor in actors if actor.getState('region') == region}
        remove = set()
        while len(remove) < len(residents) / 2:
            actor = random.choice(list(residents-remove))
            remove.add(actor.name)
    #        print(actor.getState(TURN))
            actor.setState('location',random.choice(shelters))

    postCount = countAntisocial(world)
 #   print(preCount,postCount)

    outFile = os.path.join(root,'Instances','Instance%d' % (args['instance']),
                           'Runs','run-%d' % (args['run']),args['output'])
    fields = ['Region','Before','After']
    with open(outFile,'w') as csvfile:
        writer = csv.DictWriter(csvfile,fields,delimiter='\t',extrasaction='ignore')
        writer.writeheader()
        for region in regions:
            record = {'Region': region,
                      'Before': preCount[region],
                      'After': postCount.get(region,0)}
            writer.writerow(record)
        
    
