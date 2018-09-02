import csv
import os
import random
import sys

instance = int(sys.argv[1])
inFile = os.path.join(os.path.dirname(__file__),'Instances','Instance%d' % (instance),
                      'Runs','run-0','RunDataTable')

actors = {}
with open(inFile) as csvfile:
    reader = csv.DictReader(csvfile,delimiter='\t')
    for row in reader:
        actor = row['EntityIdx']
        if actor[:5] == 'Actor':
            if not actor in actors:
                actors[actor] = {}
            if row['VariableName'] == 'Actor action':
                if row['Value'].split('-')[1] == 'evacuate':
                    actors[actor]['evacuated'] = True
            elif row['VariableName'] == 'Actor region':
                actors[actor]['region'] = row['Value']
outFile = os.path.join(os.path.dirname(__file__),'Instances','Instance100001',
                      'Runs','run-0','AccessibilityDemo08Table')
fields = ['Actor','Evacuated','Known Evacuees']
remaining = list(actors.keys())
samples = []
with open(outFile,'w') as csvfile:
    writer = csv.DictWriter(csvfile,fields,delimiter='\t',extrasaction='ignore')
    writer.writeheader()
    while len(samples) < 10:
        actor = random.choice(remaining)
        remaining.remove(actor)
        record = {'Actor': actor}
        if 'evacuated' in actors[actor]:
            record['Evacuated'] = 'yes'
        else:
            record['Evacuated'] = 'no'
        count = 0
        for other,entry in actors.items():
            if other != actor and entry['region'] == actors[actor]['region'] and \
               'evacuated' in entry:
                count += 1
        record['Known Evacuees'] = count
        writer.writerow(record)
        samples.append(actor)
        
