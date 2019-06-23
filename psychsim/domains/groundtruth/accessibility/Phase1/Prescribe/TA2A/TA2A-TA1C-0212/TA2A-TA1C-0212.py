import csv
import logging
import os.path
import random
import string
alphabet = dict(enumerate(string.ascii_lowercase, 0))

from psychsim.probability import Distribution
from psychsim.pwl import *
from psychsim.domains.groundtruth import accessibility
from psychsim.action import *

items = ['Actual Aid Target','Preferred Aid Target','Aid Received','Aid Expected','Shelter Policy','Category Accuracy Government Broadcast',
    'Category Accuracy Government Officials','Category Accuracy Friends','Category Accuracy Acquaintances','Category Accuracy Social Media',
    'Location Accuracy Government Broadcast','Location Accuracy Government Officials','Location Accuracy Friends',
    'Location Accuracy Acquaintances','Location Accuracy Social Media','Prediction Accuracy Government Broadcast',
    'Prediction Accuracy Government Officials','Prediction Accuracy Friends','Prediction Accuracy Acquaintances',
    'Prediction Accuracy Social Media','Damage Accuracy Government Broadcast','Damage Accuracy Government Officials',
    'Damage Accuracy Friends','Damage Accuracy Acquaintances','Damage Accuracy social Media','Casualties Accuracy Government Broadcast',
    'Casualties Accuracy Government Officials','Casualties Accuracy Friends','Casualties Accuracy Acquaintances',
    'Casualties Accuracy Social Media','Warning Accuracy Government Broadcast','Warning Accuracy Government Officials',
    'Warning Accuracy Friends','Warning Accuracy Acquaintances','Warning Accuracy Social Media']
relevantItems = {'Actual Aid Target': 50,'Preferred Aid Target': 50,'Aid Received': 50,'Aid Expected': 50,
    'Category Accuracy Friends': 0,'Category Accuracy Social Media':0,'Location Accuracy Social Media':0}

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO,filename=os.path.join(os.path.dirname(__file__),'TA2A-TA1C-0212.log'))
    random.seed(212)
    fields = ['Name','LongName','Values','VarType','DataType','Notes']
    output = []
    for i in range(len(items)):
        output.append({'Name': items[i],'LongName': items[i],'Values': '[0-100]','VarType': 'dynamic','DataType': 'Integer',
            'Notes': '2.%s' % (alphabet[i] if i < 26 else alphabet[i-26]+alphabet[i-26])})
    with open(os.path.join(os.path.dirname(__file__),'SimulationDefinition','VariableDefTable.tsv'),'w') as csvfile:
        writer = csv.DictWriter(csvfile,fields,delimiter='\t',extrasaction='ignore')
        writer.writeheader()
        for record in output:
            writer.writerow(record)
    raise RuntimeError
    fields = ['Timestep','Participant']+sorted(accessibility.demographics.keys())+items
    for instance in [1,9,10,11,12,13,14]:
        logging.info('Instance %d' % (instance))
        args = accessibility.instances[instance-1]
        data = accessibility.loadRunData(args['instance'],args['run'],args['span'],subs=['Input'] if instance > 2 else [None])
        demos = accessibility.readDemographics(data,last=args['span'])
        population = accessibility.getPopulation(data)
        pool = random.sample(population,16)
        output = []
        participants = {}
        for name in pool:
            record = demos[name]
            output.append(record)
            record.update({'Timestep': args['span'],'Participant': len(output)})
            logging.info('Participant %d: %s' % (record['Participant'],name))
            for item in items:
                try:
                    value = relevantItems[item]
                except KeyError:
                    value = 'NAN'
                record[item] = value
        accessibility.writeOutput(args,output,fields,'TA2A-TA1C-0212.tsv',
            os.path.join(os.path.dirname(__file__),'Instances','Instance%d' % (instance),'Runs','run-0'))
