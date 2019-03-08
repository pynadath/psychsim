
import csv
import logging
import os.path

from psychsim.pwl.keys import *
from psychsim.domains.groundtruth import accessibility

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO,filename='%s.log' % (os.path.splitext(__file__)[0]))
    for instance in range(2,len(accessibility.instances)):
        entry = accessibility.instances[instance]
        dirname = accessibility.getDirectory(entry)
        logging.info('Instance %d, run %d' % (entry['instance'],entry['run']))
        data = accessibility.loadRunData(entry['instance'],entry['run'],entry['span'])
        participants = accessibility.readParticipants(os.path.join(dirname,'Input'))['ActorPostTable']
        hurricanes = accessibility.readHurricanes(entry['instance'],entry['run'])
        # Generate Data
        output = []
        with accessibility.openFile(entry,os.path.join('Input','ActorPostTable.tsv')) as csvfile:
            reader = csv.DictReader(csvfile,delimiter='\t')
            for row in reader:
                name = participants[int(row['Participant'])]
                region = data[name][stateKey(name,'region')][1]
                hurricane = hurricanes[int(row['Hurricane'])-1]
                beliefs = [float(data[name]['__beliefs__'][stateKey('Region','risk')][t]) \
                    for t in range(hurricane['Start'],hurricane['End']+1)]
                real = [float(data[region][stateKey(region,'risk')][t]) \
                    for t in range(hurricane['Start'],hurricane['End']+1)]
                # Use real value to be consistent (but can compare against risk perception if desired)
                row['Property Previous Hurricane'] = accessibility.toLikert(max(real))
                output.append(row)
        # Save Data
        fields = ['Timestep','Participant','Hurricane','Property Previous Hurricane']
        with open(os.path.join(os.path.dirname(__file__),'Instances','Instance%d' % (instance+1),'Runs','run-0','TA2B-TA1C-27.csv'),'w') as csvfile:
            writer = csv.DictWriter(csvfile,fields,delimiter='\t',extrasaction='ignore')
            writer.writeheader()
            for record in output:
                writer.writerow(record)
