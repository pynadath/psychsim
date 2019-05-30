import csv
import logging
import os.path
import random

from psychsim.pwl.keys import *
from psychsim.domains.groundtruth import accessibility

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO,filename='%s.log' % (os.path.splitext(__file__)[0]))
    fields = sorted(accessibility.demographics.keys())+['Day of Death','Location at Death','Category When Hit']
    for instance in range(9,15):
        entry = accessibility.instances[instance-1]
        logging.info('Instance %d, run %d' % (entry['instance'],entry['run']))
        data = accessibility.loadRunData(entry['instance'],entry['run'],entry['span'],subs=['Input'])
        demos = accessibility.readDemographics(data,last=entry['span'])
        hurricanes = accessibility.readHurricanes(entry['instance'],entry['run'],sub='Input')
        dead = {name for name in data if name[:5] == 'Actor' and not data[name][stateKey(name,'alive')][entry['span']]}
        output = []
        for name in dead:
            day = min([t for t in range(1,entry['span']) if not data[name][stateKey(name,'alive')][t]])
            # 0
            record = demos[name]
            output.append(record)
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
            hurricane = accessibility.findHurricane(day,hurricanes)
            if hurricane is None:
                # Didn't die during a hurricane. Find most recent one.
                hurricane = [h for h in hurricanes if h['End'] < day][-1]
            offset = hurricane['Landfall'] - hurricane['Start']
            for t in range(hurricane['End']-hurricane['Landfall']+1):
                if hurricane['Actual Location'][t+offset] == record['Residence']:
                    record['Category When Hit'] = hurricane['Actual Category'][t+offset]
                    break
            else:
                record['Category When Hit'] = 'N/A'
        # Save Data
        accessibility.writeOutput(entry,output,fields,'TA2B-TA1C-50.tsv',
            os.path.join(os.path.dirname(__file__),'Instances','Instance%d' % (instance),'Runs','run-0'))

