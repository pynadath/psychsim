import csv
import os.path
import random

from psychsim.pwl.keys import *
from psychsim.domains.groundtruth import accessibility

answers = {
    'If there is a potential threat of some property damage': (2,True),
    'If there is a strong threat of some property damage': (2,False),
    'If there is a potential threat of some widespread property damage': (5,True),
    'If there is a strong threat of widespread property damage': (5,False),
    'If there is a potential threat of widespread injury ("casualty")': (2,True),
    'If there is a strong threat of widespread injury("casualty")': (2,False),
    'If there is a potential threat of some death': (4,True),
    'If there is a strong threat of some death': (4,False),
    'If there is a potential threat of widespread death': (5,True),
    'If there is a strong threat of widespread death': (5,False)
    }

if __name__ == '__main__':
    random.seed(122)
    args = accessibility.instances[0]
    data = accessibility.loadRunData(args['instance'],args['run'],args['span'])
    demos = accessibility.readDemographics(data,last=args['span'])
    hurricanes = [h for h in accessibility.readHurricanes(args['instance'],args['run']) if h['End'] <= args['span']]
    pool = {name for name in demos if demos[name]['Residence'] == 'Region05'}
    output = []
    fields = ['Participant']+sorted(accessibility.demographics.keys())
    with open(os.path.join('SimulationDefinition','VariableDefTable.tsv'),'w') as csvfile:
        writer = csv.DictWriter(csvfile,['Name','LongName','Values','VarType','DataType','Notes'],delimiter='\t',extrasaction='ignore')
        writer.writeheader()
        for condition in list(answers.keys())+['Should Have But Did Not','Perspective Change']:
            field = 'Evacuate: %s' % (condition)
            fields.append(field)
            record = {'Name': field,'LongName':field,'Values':'yes,no','VarType':'dynamic','DataType':'boolean'}
            writer.writerow(record)
    for name in pool:
        output.append(demos[name])
        output[-1]['Participant'] = len(output)
        home = demos[name]['Residence'] # Will be Region05, but in general...
        # Taken from TA2A-TA1C-0012.py
        histogram = [{False: 0,True: 0} for value in range(5)]
        for t,action in data[name][actionKey(name)].items():
            if t > 1:
                if data[name][stateKey(name,'location')][t-1] == home:
                    # Only care when deciding from home
                    property = accessibility.toLikert(float(data[name]['__beliefs__'][stateKey('Region','risk')][t-1]))
                    injury = accessibility.toLikert(float(data[name]['__beliefs__'][stateKey(name,'risk')][t-1]))
                    assert property == injury
                    histogram[property-1][action['verb'] == 'evacuate'] += 1
        alwaysEvac = None
        alwaysStay = None
        someEvac = None
        for level in range(len(histogram)):
            if histogram[level][False] == 0:
                if histogram[level][True] > 0 and alwaysEvac is None:
                    # Always evacuate
                    alwaysEvac = level
            elif histogram[level][True] == 0:
                # Always stay
                alwaysStay = level
            else:
                # Sometimes evacuate
                if someEvac is None:
                    someEvac = level
        print(histogram)
        print(name)
        output[-1]['Evacuate: Should Have But Did Not'] = 'no'
        for condition,threshold in answers.items():
            field = 'Evacuate: %s' % (condition)
            level,always = threshold
            if alwaysEvac is not None and alwaysEvac < level:
                output[-1][field] = 'yes'
            elif not always and someEvac is not None and someEvac < level:
                output[-1][field] = 'yes'
            else:
                output[-1][field] = 'no'
        # 4
        output[-1]['Evacuate: Perspective Change'] ='no'
    accessibility.writeOutput(args,output,fields,fname='TA2A-TA1C-0122.tsv')