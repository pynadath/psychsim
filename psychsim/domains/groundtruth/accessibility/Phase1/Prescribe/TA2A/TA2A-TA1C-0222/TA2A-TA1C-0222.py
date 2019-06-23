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

items = ['Even Within','Unevenly Within Age','Unevenly Within Ethnicity','Unevenly Within Religion','Unevenly Within Gender','Unevenly Within Job',
    'Unevenly Within Children','Unevenly Within Wealth','Evenly Among','Unevenly Among Age','Unevenly Among Ethnicity','Unevenly Among Religion',
    'Unevenly Among Gender','Unevenly Among Job','Unevenly Among Children','Unevenly Among Wealth','Same Payment','Different Payment Age',
    'Different Payment Ethnicity','Different Payment Religion','Different Payment Gender','Different Payment Job','Different Payment Children',
    'Different Payment Wealth','Different Payment Residence','Same Shelter','Different Shelter Age','Different Shelter Ethnicity',
    'Different Shelter Religion','Different Shelter Gender','Different Shelter Job','Different Shelter Children','Different Shelter Wealth',
    'Different Shelter Residence']
request = 222

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO,filename=os.path.join(os.path.dirname(__file__),'TA2A-TA1C-%04d.log' % (request)))
    random.seed(request)
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
                if item == 'Even Within':
                    record[item] = 5
                elif item == 'Evenly Among':
                    record[item] = 0
                elif 'Unevenly' in item:
                    record[item] = 1
                elif 'Payment' in item:
                    record[item] = 'NA'
                elif item == 'Same Shelter':
                    if demos[name]['Pets'] == 'yes':
                        record[item] = 1
                    else:
                        record[item] = 5
                elif 'Different' in item:
                    record[item] = 0
                else:
                    raise RuntimeError(item)
        accessibility.writeOutput(args,output,fields,'TA2A-TA1C-%04d.tsv' % (request),
            os.path.join(os.path.dirname(__file__),'Instances','Instance%d' % (instance),'Runs','run-0'))
