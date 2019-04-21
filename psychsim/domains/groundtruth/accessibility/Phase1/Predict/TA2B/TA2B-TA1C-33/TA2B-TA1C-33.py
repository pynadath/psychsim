import csv
import logging
import os.path
import random
import sys

from psychsim.pwl.keys import *
from psychsim.domains.groundtruth import accessibility

def conductSurvey(record,data,name,hurricanes):
    sheltered = {}
    evacuated = {}
    for hurricane in hurricanes:
        sheltered[hurricane['Hurricane']] = [t for t in range(hurricane['Start'],hurricane['End']+1) \
            if data[name][stateKey(name,'location')][t][:7] == 'shelter']
        evacuated[hurricane['Hurricane']] = [t for t in range(hurricane['Start'],hurricane['End']+1) \
            if data[name][stateKey(name,'location')][t] == 'evacuated']
    record['EverUsedShelter'] = 'yes' if max([len(days) for days in sheltered.values()]) else 'no'
    hurrShelter = [h for h,days in sheltered.items() if len(days) > 0]
    if hurrShelter:
        record['WhichHurricanesSheltered'] = ','.join(['%d' % (h) for h in hurrShelter])
    else:
        record['WhichHurricanesSheltered'] = 'N/A'
    record['EverEvacuated'] = 'yes' if max([len(days) for days in evacuated.values()]) else 'no'
    hurrEvac = [h for h,days in evacuated.items() if len(days) > 0]
    if hurrEvac:
        record['WhichHurricanesEvacd'] = ','.join(['%d' % (h) for h in hurrEvac])
    else:
        record['WhichHurricanesEvacd'] = 'N/A'
    seq = []
    for hurricane in hurricanes:
        if evacuated[hurricane['Hurricane']] and sheltered[hurricane['Hurricane']]:
            if min(evacuated[hurricane['Hurricane']]) < min(sheltered[hurricane['Hurricane']]):
                seq.append('Evacuated')
            else:
                seq.append('Sheltered')
    if seq:
        record['OrderingForBoth'] = ','.join(seq)
    else:
        record['OrderingForBoth'] = 'N/A'
    if hurrShelter:
        record['DaysSpentInShelter'] = ','.join(['%d' % (len(sheltered[h])) for h in hurrShelter])
    else:
        record['DaysSpentInShelter'] = 'N/A'
    if hurrEvac:
        record['DaysSpentInEvacd'] = ','.join(['%d' % (len(evacuated[h])) for h in hurrEvac])
    else:
        record['DaysSpentInEvacd'] = 'N/A'
    values = [data[name][stateKey(name,'grievance')][hurricane['End']] for hurricane in hurricanes \
        if hurricane['Hurricane'] in hurrEvac or hurricane['Hurricane'] in hurrShelter]
    if values:
        record['Dissatisfaction1'] = ','.join(['%d' % (accessibility.toLikert(v)) for v in values])
    else:
        record['Dissatisfaction1'] = 'N/A'
    values = [data[name][stateKey(name,'grievance')][hurricane['End']] for hurricane in hurricanes \
        if hurricane['Hurricane'] not in hurrEvac and hurricane['Hurricane'] not in hurrShelter]
    if values:
        record['Dissatisfaction2'] = ','.join(['%d' % (accessibility.toLikert(v)) for v in values])
    else:
        record['Dissatisfaction2'] = 'N/A'

def survey(entry,data,hurricanes,start=1,end=None):
    if end is None:
        end = entry['span']
    demos = accessibility.readDemographics(data,last=end)
    population = [name for name in demos if name[:5] == 'Actor' and data[name][stateKey(name,'alive')][end]]
    locations = {name: {data[name][stateKey(name,'location')][t][:7] for t in range(start,end)} for name in population}
    pool = {name for name in population if 'shelter' in locations[name]}
    if len(pool) < 16:
        pool |= set(random.sample([name for name in population if name not in pool],16-len(pool)))
    elif len(pool) > 16:
        pool = set(random.sample(pool,16))
    output = []
    for name in pool:
        record = demos[name]
        record['Hurricane'] = hurricanes[-1]['Hurricane']
        output.append(record)
        record['Participant'] = len(output)
        logging.info('Participant %d: %s' % (record['Participant'],name))
        conductSurvey(record,data,name,hurricanes)
    return output

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO,filename='%s.log' % (os.path.splitext(__file__)[0]))
    random.seed(33)
    fields = ['Participant','Hurricane']+sorted(accessibility.demographics)+['EverUsedShelter','WhichHurricanesSheltered',\
        'EverEvacuated','WhichHurricanesEvacd','OrderingForBoth','DaysSpentInShelter','DaysSpentInEvacd','Dissatisfaction1','Dissatisfaction2']
    for instance in range(1,len(accessibility.instances)):
        entry = accessibility.instances[instance]
        dirname = accessibility.getDirectory(entry)
        logging.info('Instance %d, run %d' % (entry['instance'],entry['run']))
        data = accessibility.loadRunData(entry['instance'],entry['run'],entry['span'])
        hurricanes = accessibility.readHurricanes(entry['instance'],entry['run'])
        if instance == 1:
            output = survey(entry,data,hurricanes[:8],end=184)
            output += survey(entry,data,hurricanes[8:],start=365)
        else:
            output = survey(entry,data,[h for h in hurricanes if h['End'] < entry['span']])
        # Save Data
        with open(os.path.join(os.path.dirname(__file__),'Instances','Instance%d' % (instance+1),'Runs','run-0','TA2B-TA1C-33.tsv'),'w') as csvfile:
            writer = csv.DictWriter(csvfile,fields,delimiter='\t',extrasaction='ignore')
            writer.writeheader()
            for record in output:
                writer.writerow(record)
