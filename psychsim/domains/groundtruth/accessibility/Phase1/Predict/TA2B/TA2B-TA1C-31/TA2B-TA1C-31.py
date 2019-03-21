import csv
import logging
import os.path

from psychsim.pwl.keys import *
from psychsim.domains.groundtruth import accessibility

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO,filename='%s.log' % (os.path.splitext(__file__)[0]))
    fields = ['Timestep','Participant','Assistance','AssistanceToEvac','AssistanceToShelter',\
        'EverAssistanceToEvac']
    args = {'instance': 24, 'run': 1}
    dirname = accessibility.getDirectory(args)
    data = accessibility.loadRunData(args['instance'],args['run'])
    hurricanes = accessibility.readHurricanes(args['instance'],args['run'])
    output = []
    with accessibility.openFile(args,'ActorPostTable.tsv') as csvfile:
        reader = csv.DictReader(csvfile,delimiter='\t')
        for row in reader:
            hurricane = hurricanes[int(row['Hurricane'])-1]
            assert hurricane['Hurricane'] == int(row['Hurricane'])
            govt = [data['System'][actionKey('System')][t] for t in range(hurricane['Start'],hurricane['End'])]
            count = len([a for a in govt if a['object'] == row['Residence']])
            row['Assistance'] = accessibility.toLikert(float(count)/float(len(govt)))
            row['AssistanceToEvac'] = 1
            row['AssistanceToShelter'] = 1
            row['EverAssistanceToEvac'] = 1
            row['EverAssistanceToShelter'] = 1
            output.append(row)
    accessibility.writeOutput(args,output,fields,'TA2B-TA1C-31.tsv')