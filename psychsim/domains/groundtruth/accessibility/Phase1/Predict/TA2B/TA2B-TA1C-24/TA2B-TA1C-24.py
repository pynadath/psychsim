"""
**Research method category**: Survey


**Specific question**:
1. We would like to survey the agents about any information they received from peers prior to making the decision to evacuate / shelter / stay, broken down by hurricane, for each of the five new areas


**Sampling strategy**: 10% random sample of agents in each of the five new areas


**Other applicable detail**: We are interested in all the various ways that peer share information or opinions with each other. This could be sharing weather predictions, sheltering advice, information about receiving government assistance, etc..  


**Research request identifier**: 24peereffects
"""
import csv
import logging
import os
import random

from psychsim.pwl.keys import *
from psychsim.domains.groundtruth import accessibility

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO,filename='%s.log' % (os.path.splitext(__file__)[0]))
    fields = ['Participant','Timestep'] + sorted(accessibility.demographics)+\
        ['Hurricane','Shared Weather Predictions','Shared Sheltering Advice','Shared Government Information',
        'Evacuated Previous Hurricane','At Shelter Previous Hurricane']
    random.seed(24)
    for instance in range(2,len(accessibility.instances)):
        entry = accessibility.instances[instance]
        logging.info('Instance %d, run %d' % (entry['instance'],entry['run']))
        data = accessibility.loadRunData(entry['instance'],entry['run'],entry['span'])
        hurricanes = accessibility.readHurricanes(entry['instance'],entry['run'])
        for h in hurricanes:
            if h['End'] < entry['span']:
                hurricane = h
            else:
                break
        network = accessibility.readNetwork(entry['instance'],entry['run'])
        actors = accessibility.readDemographics(data)
        pool = random.sample(list(actors.keys()),len(actors)//10)
        output = []
        for participant in range(len(pool)):
            name = pool[participant]
            logging.info('Participant %d: %s' % (participant+1,name))
            record = {'Participant': participant+1,'Timestep': entry['span']}
            record.update(actors[name])
            output.append(record)
            record['Hurricane'] = hurricane['Hurricane']
            record['Shared Weather Predictions'] = 'yes' if name in network['friendOf'] else 'no'
            record['Shared Sheltering Advice'] = 'no'
            record['Shared Government Information'] = 'no'
            series = {data[name][stateKey(name,'location')][t] for t in range(hurricane['Start'],hurricane['End']+1)}
            record['Evacuated Previous Hurricane'] = 'yes' if 'evacuated' in series else 'no'
            for loc in series:
                if loc[:7] == 'shelter':
                    record['At Shelter Previous Hurricane'] = 'yes'
                    break
            else:
                record['At Shelter Previous Hurricane'] = 'no'
        with open(os.path.join(os.path.dirname(__file__),'Instances','Instance%d' % (instance+1),'Runs','run-0','TA2B-TA1C-24.csv'),'w') as csvfile:
            writer = csv.DictWriter(csvfile,fields,delimiter='\t',extrasaction='ignore')
            writer.writeheader()
            for record in output:
                writer.writerow(record)
