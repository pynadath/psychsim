import csv
import os
import random
import sys

instance = int(sys.argv[1])
inFile = os.path.join(os.path.dirname(__file__),'Instances','Instance%d' % (instance),
                      'Runs','run-0','RelationshipDataTable')

actors = {}
with open(inFile) as csvfile:
    reader = csv.DictReader(csvfile,delimiter='\t')
    for row in reader:
        actor = row['FromEntityId']
        if row['Data'] == 'True':
            actors[actor] = actors.get(actor,set())|{row['ToEntityId']}
outFile = os.path.join(os.path.dirname(__file__),'Instances','Instance100001',
                      'Runs','run-0','AccessibilityDemo09Table')
fields = ['Actor','Friend']
chosen = []
remaining = list(actors.keys())
with open(outFile,'w') as csvfile:
    writer = csv.DictWriter(csvfile,fields,delimiter='\t',extrasaction='ignore')
    writer.writeheader()
    while len(chosen) < 20:
        actor = random.choice(remaining)
        remaining.remove(actor)
        for friend in actors[actor]:
            record = {'Actor': actor,'Friend': friend}
            writer.writerow(record)
        chosen.append(actor)
        
