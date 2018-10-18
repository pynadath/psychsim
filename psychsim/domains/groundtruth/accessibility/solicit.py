from argparse import ArgumentParser
import csv
import os
import pickle
import random
import sys

from psychsim.pwl.keys import *

from psychsim.world import World


mapping = {'childrenHealth': 'children',
           'resources': 'finances'}

if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('instance',type=int,help='Instance to query')
    parser.add_argument('-o','--output',default='RequestInfoSolicit.tsv',help='Output filename')
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


    samples = []
    actors = [actor for actor in world.agents.values() if actor.name[:5] == 'Actor' and \
              actor.getState('alive').first()]
    outFile = os.path.join(root,'Instances','Instance%d' % (args['instance']),
                           'Runs','run-%d' % (args['run']),args['output'])
    fields = ['ParticipantId','Factor1','Factor2','Factor3']
    with open(outFile,'w') as csvfile:
        writer = csv.DictWriter(csvfile,fields,delimiter='\t',extrasaction='ignore')
        writer.writeheader()
        while len(samples) < args['samples'] and actors:
            actor = random.choice(actors)
            actors.remove(actor)
            samples.append({'ParticipantId': len(samples)+1})
            model = world.getModel(actor.name).first()
            R = actor.getAttribute('R',model)
            assert R.isLeaf()
            R = R.children[None][makeFuture(rewardKey(actor.name))]
            weights = [(R[key],key) for key in R.keys() if key != CONSTANT]
            weights.sort()
            weights.reverse()
            for index in range(min(len(weights),3)):
                feature = state2feature(weights[index][1])
                samples[-1]['Factor%d' % (index+1)] = 'my %s' % (mapping.get(feature,feature))
            writer.writerow(samples[-1])
