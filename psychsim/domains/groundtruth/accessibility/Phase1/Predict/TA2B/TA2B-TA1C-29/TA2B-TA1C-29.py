import csv
import logging
import os.path
import random

from psychsim.pwl.keys import *
from psychsim.domains.groundtruth import accessibility

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO,filename='%s.log' % (os.path.splitext(__file__)[0]))
    random.seed(29)
    fields = sorted(accessibility.demographics.keys())+['Day of Death','Location at Death','Category When Hit']
    for instance in range(2,len(accessibility.instances)):
        entry = accessibility.instances[instance]
        dirname = accessibility.getDirectory(entry)
        logging.info('Instance %d, run %d' % (entry['instance'],entry['run']))
        data = accessibility.loadRunData(entry['instance'],entry['run'],entry['span'])
        hurricanes = accessibility.readHurricanes(entry['instance'],entry['run'])
        output = []
        for name in data:
            if name[:5] == 'Actor':
                key = stateKey(name,'alive')
                try:
                    day = min([t for t in data[name][key] if not data[name][key][t]])
                except ValueError:
                    # Someone who didn't die. Good job.
                    continue
                # 0
                record = accessibility.readDemographics(data,last=day,name=name)[name]
                # 1
                record['Day of Death'] = day
                # 2
                key = stateKey(name,'location')
                record['Location at Death'] = data[name][key][day]
                if record['Location at Death'][:6] == 'Region':
                    record['Location at Death'] = 'home'
                elif record['Location at Death'][:7] == 'shelter':
                    record['Location at Death'] = 'shelter'
                # 5
                for h in range(len(hurricanes)):
                    if hurricanes[h]['Start'] > day:
                        # This is the next hurricane
                        hurricane = hurricanes[h-1]
                        break
                else:
                    raise ValueError
                offset = hurricane['Landfall'] - hurricane['Start']
                for t in range(hurricane['End']-hurricane['Landfall']+1):
                    if hurricane['Actual Location'][t+offset] == record['Residence']:
                        record['Category When Hit'] = hurricane['Actual Category'][t+offset]
                        break
                else:
                    record['Category When Hit'] = 'N/A'
                output.append(record)
        # Save Data
        with open(os.path.join(os.path.dirname(__file__),'Instances','Instance%d' % (instance+1),'Runs','run-0','TA2B-TA1C-29.tsv'),'w') as csvfile:
            writer = csv.DictWriter(csvfile,fields,delimiter='\t',extrasaction='ignore')
            writer.writeheader()
            for record in output:
                writer.writerow(record)
