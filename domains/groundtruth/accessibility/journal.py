import csv
import os
import random
import sys

from psychsim.probability import Distribution
from psychsim.domains.disaster.groundtruth.data import toLikert

instance = int(sys.argv[1])
inFile = os.path.join(os.path.dirname(__file__),'Instances','Instance%d' % (instance),
                      'Runs','run-0','RunDataTable')

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
                actors[actor][day] ={'Timestep': day,
                                      'Actor': actor,
                                      'Memberships': 'none',
                                      'Perception of Groups': 'n/a'}
            if row['VariableName'] == 'ActorBeliefOfActor risk':
                if ',' in row['Value']:
                    probs = map(float,row['Value'].split(','))
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

outFile = os.path.join(os.path.dirname(__file__),'Instances','Instance100001',
                      'Runs','run-0','AccessibilityDemo10Table')
fields = ['Timestep','Actor','Memberships','Perception of Groups','Perception of Risk',
          'Perception of Government']
remaining = list(actors.keys())
samples = []
with open(outFile,'w') as csvfile:
    writer = csv.DictWriter(csvfile,fields,delimiter='\t',extrasaction='ignore')
    writer.writeheader()
    while len(samples) < 1:
        actor = random.choice(remaining)
        remaining.remove(actor)
        for day in sorted(list(actors[actor].keys())):
            writer.writerow(actors[actor][day])
        samples.append(actor)
