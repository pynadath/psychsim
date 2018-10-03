from argparse import ArgumentParser
import csv
import os
import random
import sys

if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('instance',type=int,help='Instance to query')
    parser.add_argument('-o','--output',default='RequestInteraction.tsv',help='Output filename')
    parser.add_argument('-r','--run',type=int,default=0,help='Run to query')
    parser.add_argument('-s','--samples',type=int,default=20,help='Number of people to survey')
    parser.add_argument('--seed',type=int,default=None,help='Random number generator seed')
    args = vars(parser.parse_args())

    random.seed(args['seed'])
    root = os.path.join(os.path.dirname(__file__),'..')
    inFile = os.path.join(root,'Instances','Instance%d' % (args['instance']),
                          'Runs','run-%d' % (args['run']),'RelationshipDataTable.tsv')

    actors = {}
    with open(inFile) as csvfile:
        reader = csv.DictReader(csvfile,delimiter='\t')
        for row in reader:
            actor = row['FromEntityId']
            if row['Data'] == 'True':
                actors[actor] = actors.get(actor,set())|{row['ToEntityId']}

    outFile = os.path.join(root,'Instances','Instance%d' % (args['instance']),
                           'Runs','run-%d' % (args['run']),args['output'])
                
    fields = ['ParticipantId','Friend']
    chosen = []
    remaining = list(actors.keys())
    with open(outFile,'w') as csvfile:
        writer = csv.DictWriter(csvfile,fields,delimiter='\t',extrasaction='ignore')
        writer.writeheader()
        while len(chosen) < args['samples'] and remaining:
            actor = random.choice(remaining)
            remaining.remove(actor)
            for friend in actors[actor]:
                record = {'ParticipantId': len(chosen)+1,'Friend': friend}
                writer.writerow(record)
            chosen.append(actor)
        
