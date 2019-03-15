import csv
import logging
import os.path
import random

from psychsim.pwl.keys import *
from psychsim.domains.groundtruth import accessibility

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO,filename='%s.log' % (os.path.splitext(__file__)[0]))
    random.seed(30)
    fields = ['Timestep','Participant','Assistance Previous Hurricane','Assistance Monetary','Assistance Lost Wages',\
        'Assistance Property Loss','Assistance Injury','Assistance Death']
    for instance in range(2,len(accessibility.instances)):
        entry = accessibility.instances[instance]
        dirname = accessibility.getDirectory(entry)
        logging.info('Instance %d, run %d' % (entry['instance'],entry['run']))
        data = accessibility.loadRunData(entry['instance'],entry['run'],entry['span'])
        hurricanes = accessibility.readHurricanes(entry['instance'],entry['run'])
        output = []
        with accessibility.openFile(entry,os.path.join('Input','ActorPostTable.tsv')) as csvfile:
            reader = csv.DictReader(csvfile,delimiter='\t')
            for row in reader:
                hurricane = hurricanes[int(row['Hurricane'])-1]
                assert hurricane['Hurricane'] == int(row['Hurricane'])
                govt = [data['System'][actionKey('System')][t] for t in range(hurricane['Start'],hurricane['End'])]
                count = len([a for a in govt if a['object'] == row['Residence']])
                row['Assistance Previous Hurricane'] = accessibility.toLikert(float(count)/float(len(govt)))
                row['Assistance Monetary'] = 1
                row['Assistance Lost Wages'] = 1
                row['Assistance Property Loss'] = 1
                row['Assistance Injury'] = 1
                row['Assistance Death'] = 1
                output.append(row)
        # Save Data
        with open(os.path.join(os.path.dirname(__file__),'Instances','Instance%d' % (instance+1),'Runs','run-0','TA2B-TA1C-30.tsv'),'w') as csvfile:
            writer = csv.DictWriter(csvfile,fields,delimiter='\t',extrasaction='ignore')
            writer.writeheader()
            for record in output:
                writer.writerow(record)
