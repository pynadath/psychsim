from argparse import ArgumentParser
import csv
import os
import random
import sys

from psychsim.probability import Distribution
from ..simulation.data import toLikert

if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('instance',type=int,help='Instance to query')
    parser.add_argument('-o','--output',default='RequestJournal.tsv',help='Output filename')
    parser.add_argument('-r','--run',type=int,default=0,help='Run to query')
    parser.add_argument('-s','--samples',type=int,default=1,help='Number of people to survey')
    parser.add_argument('--seed',type=int,default=None,help='Random number generator seed')
    args = vars(parser.parse_args())

    random.seed(args['seed'])
    root = os.path.join(os.path.dirname(__file__),'..')
    inFile = os.path.join(root,'Instances','Instance%d' % (args['instance']),
                          'Runs','run-%d' % (args['run']),'RunDataTable.tsv')

    actors = {}
    with open(inFile) as csvfile:
        reader = csv.DictReader(csvfile,delimiter='\t')
        for row in reader:
            try:
                day = int(row['Timestep'])
            except ValueError:
                continue
            actor = row['EntityIdx']
            if actor[:5] == 'Actor' and day % 7 == 0:
                if not actor in actors:
                    actors[actor] = {}
                if not day in actors[actor]:
                    actors[actor][day] = {'Timestep': day,
                                          'Memberships': 'none',
                                          'Perception of Groups': 'n/a'}
                if row['VariableName'] == 'ActorBeliefOfActor risk':
                    if ',' in row['Value']:
                        probs = [float(v) for v in row['Value'].split(',')]
                        values = row['Notes'].split(',')
                        dist = Distribution()
                        for index in range(len(values)):
                            text = values[index]
                            value = float(text[text.index('=')+1:text.index(')')])
                            dist[value] = probs[index]
                        actors[actor][day]['Perception of Risk'] = toLikert(dist.expectation())
                    else:
                        actors[actor][day]['Perception of Risk'] = toLikert(float(row['Value']))
                elif row['VariableName'] == 'Actor grievance':
                    actors[actor][day]['Perception of Government'] = toLikert(float(row['Value']))

    outFile = os.path.join(root,'Instances','Instance%d' % (args['instance']),
                           'Runs','run-%d' % (args['run']),args['output'])
    fields = ['Timestep','ParticipantId','Memberships','Perception of Groups','Perception of Risk',
              'Perception of Government']
    remaining = list(actors.keys())
    samples = []
    with open(outFile,'w') as csvfile:
        writer = csv.DictWriter(csvfile,fields,delimiter='\t',extrasaction='ignore')
        writer.writeheader()
        while len(samples) < args['samples'] and remaining:
            actor = random.choice(remaining)
            remaining.remove(actor)
            for day in sorted(list(actors[actor].keys())):
                record = actors[actor][day]
                record['ParticipantId'] = len(samples)+1
                writer.writerow(record)
            samples.append(actor)
