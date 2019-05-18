import csv
import logging
import os.path
import random

from psychsim.pwl.keys import *
from psychsim.domains.groundtruth import accessibility

from TA2BTA1C32 import *

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO,filename=os.path.join(os.path.dirname(__file__),'%s.log' % (os.path.splitext(__file__)[0])))
    random.seed(47)
    for instance in range(9,15):
        entry = accessibility.instances[instance-1]
        config = accessibility.getConfig(entry['instance'])
        logging.info('Instance %d, run %d' % (entry['instance'],entry['run']))
        data = accessibility.loadRunData(entry['instance'],entry['run'],entry['span'],subs=['Input'])
        idMap = accessibility.readParticipants(entry['instance'],entry['run'],os.path.join('Input','psychsim.log'))
        hurricanes = [h for h in accessibility.readHurricanes(entry['instance'],entry['run'],'Input') if h['End'] < entry['span']]
        # Pre-hurricane Survey
        output,fields = pairedPreSurvey(entry,data,hurricanes,idMap['ActorPreTable'],'Input')
        # Save Data
        with open(os.path.join(os.path.dirname(__file__),'Instances','Instance%d' % (instance),'Runs','run-0','TA2B-TA1C-47-Pre.tsv'),'w') as csvfile:
            writer = csv.DictWriter(csvfile,fields,delimiter='\t',extrasaction='ignore')
            writer.writeheader()
            for record in output:
                writer.writerow(record)
        # Post-hurricane Survey
        output,fields = pairedPostSurvey(entry,data,hurricanes,idMap['ActorPostTable'],'Input')
        # Save Data
        with open(os.path.join(os.path.dirname(__file__),'Instances','Instance%d' % (instance),'Runs','run-0','TA2B-TA1C-47-Post.tsv'),'w') as csvfile:
            writer = csv.DictWriter(csvfile,fields,delimiter='\t',extrasaction='ignore')
            writer.writeheader()
            for record in output:
                writer.writerow(record)
