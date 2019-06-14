import csv
import logging
import os.path
import random

from psychsim.probability import Distribution
from psychsim.pwl import *
from psychsim.domains.groundtruth import accessibility
from psychsim.action import *

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO,filename=os.path.join(os.path.dirname(__file__),'TA2A-TA1C-0182.log'))
    random.seed(182)
    fields = ['Timestep','Participant','Sheltered']+sorted(accessibility.demographics.keys())+['Condition 1 Satisfaction']+\
        sum([['Condition 1 Category %d Evacuate' % (category+1),'Condition 1 Category %d Stayed Home' % (category+1),
            'Condition 1 Category %d Sheltered' % (category+1)] for category in range(5)],[])+['Original Conditions Satisfaction']+\
        sum([['Original Conditions Category %d Evacuate' % (category+1),'Original Conditions Category %d Stayed Home' % (category+1),
            'Original Conditions Category %d Sheltered' % (category+1)] for category in range(5)],[])
    for instance in [1]: # [9,10,11,12,13,14]:
        logging.info('Instance %d' % (instance))
        args = accessibility.instances[instance-1]
        config = accessibility.getConfig(args['instance'])
        data = accessibility.loadRunData(args['instance'],args['run'],args['span'],subs=['Input'] if instance > 2 else [None])
        hurricanes = [h for h in accessibility.readHurricanes(args['instance'],args['run'],'Input' if instance > 2 else None) 
            if h['End'] < args['span']]
        hurricane = hurricanes[-1]
        demos = accessibility.readDemographics(data,last=hurricane['Start'])
        pool = random.sample(accessibility.getPopulation(data),16)
        output = []
        participants = {}
        for name in pool:
            record = demos[name]
            output.append(record)
            record.update({'Timestep': args['span'],'Participant': len(output)})
            logging.info('Participant %d: %s' % (record['Participant'],name))
            participants[name] = record['Participant']
        accessibility.writeOutput(args,output,['Timestep','Participant']+sorted(accessibility.demographics.keys()),
            'TA2A-TA1C-0182-Initial.tsv',os.path.join(os.path.dirname(__file__),'Instances','Instance%d' % (instance),'Runs','run-0'))
        output = []
        for name in pool:
            beliefs = {}
            key = stateKey('Nature','category')
            beliefs = {t: data[name]['__beliefs__'][key][t] for t in range(hurricane['Start']-1,hurricane['End']+1)}
            for t in range(hurricane['Start'],hurricane['End']+1):
                record = {'Timestep': t,'Participant': participants[name],'Information Type': 'Hurricane Category'}
                output.append(record)
                key = stateKey('Nature','category')
                if isinstance(beliefs[t],int):
                    # Only one value
                    record['Value'] = beliefs[t]
                elif float(beliefs[t]) > float(beliefs[t-1]):
                    # Higher category wins
                    record['Value'] = max(beliefs[t].domain())
                else:
                    # Lower category wins
                    record['Value'] = min(beliefs[t].domain())
                record = {'Timestep': t,'Participant': participants[name],'Information Type': 'Hurricane Location'}
                output.append(record)
                record['Value'] = data[name]['__beliefs__'][stateKey('Nature','phase')][t]
                if record['Value'] == 'active':
                    record['Value'] = data[name]['__beliefs__'][stateKey('Nature','location')][t]
        fields = ['Timestep','Participant','Information Type','Value','Other Notes']
        accessibility.writeOutput(args,output,fields,'TA2A-TA1C-0182-Information.tsv',
            os.path.join(os.path.dirname(__file__),'Instances','Instance%d' % (instance),'Runs','run-0'))
        output = []
        for name in pool:
            beliefs = {}
            key = stateKey('Nature','category')
            beliefs = {t: data[name]['__beliefs__'][key][t] for t in range(hurricane['Start']-1,hurricane['End']+1)}
            for t in range(hurricane['Start'],hurricane['End']+1):
                record = {'Timestep': t,'Participant': participants[name],'Location': data[name][stateKey(name,'location')][t]}
                output.append(record)
                # 1.
                if record['Location'][:7] == 'shelter':
                    record['Location'] = 'shelter'
                elif record['Location'] != 'evacuated':
                    record['Location'] = 'home'
                # 3
                record['Hurricane Category'] = int(round(float(data[name]['__beliefs__'][stateKey('Nature','category')][t])))
                # 4
                record['Hurricane Location'] = data[name]['__beliefs__'][stateKey('Nature','phase')][t]
                if record['Hurricane Location'] == 'active':
                    record['Hurricane Location'] = data[name]['__beliefs__'][stateKey('Nature','location')][t]
                # 5
                record['Injury Possibility'] = accessibility.toLikert(float(data[name]['__beliefs__'][stateKey(name,'risk')][t]),7)-1
                # 6
                record['Death Possibility'] = accessibility.toLikert(float(data[name]['__beliefs__'][stateKey(name,'risk')][t])/5,7)-1
                # 7
                record['Shelter Possibility'] = 6 if record['Location'] == 'shelter' else 0
                # 8
                record['Regional Damage'] = accessibility.toLikert(float(data[name]['__beliefs__'][stateKey('Region','risk')][t]))
        fields = ['Timestep','Participant','Location','Hurricane Category','Hurricane Location','Injury Possibility','Death Possibility',
            'Shelter Possibility','Regional Damage']
        accessibility.writeOutput(args,output,fields,'TA2A-TA1C-0182-Journal.tsv',
            os.path.join(os.path.dirname(__file__),'Instances','Instance%d' % (instance),'Runs','run-0'))
