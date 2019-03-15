import csv
import logging
import os.path
import random

from psychsim.pwl.keys import *
from psychsim.domains.groundtruth import accessibility

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO,filename='%s.log' % (os.path.splitext(__file__)[0]))
    random.seed(28)
    for instance in range(2,len(accessibility.instances)):
        entry = accessibility.instances[instance]
        dirname = accessibility.getDirectory(entry)
        logging.info('Instance %d, run %d' % (entry['instance'],entry['run']))
        data = accessibility.loadRunData(entry['instance'],entry['run'],entry['span'])
        network = accessibility.readNetwork(entry['instance'],entry['run'])
        population = accessibility.readDemographics(data,last=True)
        pool = [name for name in population if name[:5] == 'Actor']
        participants = random.sample(pool,len(pool)//10)
        output = []
        for i in range(len(participants)):
        	logging.info('Participant %d: %s' % (i+1,participants[i]))
        	record = {'Participant': i+1,'Timestep': entry['span']}
        	record.update(population[participants[i]])
        	record['# Friends'] = len(network['friendOf'].get(participants[i],[]))
        	output.append(record)
        # Save Data
        fields = ['Timestep','Participant']+sorted(accessibility.demographics.keys())+['# Friends']
        with open(os.path.join(os.path.dirname(__file__),'Instances','Instance%d' % (instance+1),'Runs','run-0','TA2B-TA1C-28.tsv'),'w') as csvfile:
            writer = csv.DictWriter(csvfile,fields,delimiter='\t',extrasaction='ignore')
            writer.writeheader()
            for record in output:
                writer.writerow(record)
