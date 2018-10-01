from argparse import ArgumentParser
import csv
import os
import pickle
import random
import sys

if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('instance',type=int,help='Instance to query')
    parser.add_argument('-o','--output',default='RequestInfoFlow.tsv',help='Output filename')
    parser.add_argument('-r','--run',type=int,default=0,help='Run to query')
    parser.add_argument('-s','--samples',type=int,default=10,help='Number of people to survey')
    args = vars(parser.parse_args())

    root = os.path.join(os.path.dirname(__file__),'..')
    inFile = os.path.join(root,'Instances','Instance%d' % (args['instance']),
                          'Runs','run-%d' % (args['run']),'RunDataTable.tsv')

    actors = {}
    with open(inFile) as csvfile:
        reader = csv.DictReader(csvfile,delimiter='\t')
        for row in reader:
            actor = row['EntityIdx']
            if actor[:5] == 'Actor':
                if not actor in actors:
                    actors[actor] = {'friends': set()}
                if row['VariableName'] == 'Actor action':
                    if row['Value'].split('-')[1] == 'evacuate':
                        actors[actor]['evacuated'] = True
                elif row['VariableName'] == 'Actor region':
                    actors[actor]['region'] = row['Value']
                elif row['VariableName'] == 'Actor children':
                    actors[actor]['count'] = 1+int(row['Value'])

    inFile = os.path.join(root,'Instances','Instance%d' % (args['instance']),
                          'Runs','run-%d' % (args['run']),'scenario.pkl')
    with open(inFile,'rb') as f:
        world = pickle.load(f)
    for key,rel in world.relations['friendOf'].items():
        if rel['subject'] in actors and rel['object'] in actors:
            actors[rel['object']]['friends'].add(rel['subject'])
    outFile = os.path.join(root,'Instances','Instance%d' % (args['instance']),
                           'Runs','run-%d' % (args['run']),args['output'])
    fields = ['ParticipantId','Evacuated','Known Evacuees']
    remaining = list(actors.keys())
    samples = []
    with open(outFile,'w') as csvfile:
        writer = csv.DictWriter(csvfile,fields,delimiter='\t',extrasaction='ignore')
        writer.writeheader()
        while len(samples) < args['samples'] and remaining:
            actor = random.choice(remaining)
            remaining.remove(actor)
            record = {'ParticipantId': len(samples)+1}
            if 'evacuated' in actors[actor]:
                record['Evacuated'] = 'yes'
            else:
                record['Evacuated'] = 'no'
            count = 0
            for other,entry in actors.items():
                if other != actor and (entry['region'] == actors[actor]['region'] or
                                       other in actors[actor]['friends']):
                    if 'evacuated' in entry:
                        count += 1
            record['Known Evacuees'] = count
            writer.writerow(record)
            samples.append(actor)

