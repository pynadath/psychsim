import csv
import os.path

from psychsim.pwl.keys import *
from psychsim.domains.groundtruth import accessibility

from TA2BTA1C33 import conductSurvey

requested = [174,121,392]
if __name__ == '__main__':
    fields = ['Participant','Timestep','Number of Friends', 'Number of Friends Evacuated', 'Number of Friends Sheltered', 
        'Days Missed Work', 'Days Worked','EverUsedShelter','WhichHurricanesSheltered','EverEvacuated','WhichHurricanesEvacd',
        'OrderingForBoth','DaysSpentInShelter','DaysSpentInEvacd','Dissatisfaction1','Dissatisfaction2']
    for instance in range(6,9):
        args = accessibility.instances[instance-1]
        data = accessibility.loadRunData(args['instance'],args['run'],args['span'])
        participant = accessibility.getTarget(args['instance'],args['run'])
        # Verify that participant asked for in request matches the actual target we specified
        assert participant == requested[instance-6]
        participants = accessibility.readParticipants(args['instance'],args['run'],os.path.join('Input','psychsim.log'))['ActorPostTable']
        name = participants[participant]
        hurricanes = [h for h in accessibility.readHurricanes(args['instance'],args['run']) if h['End'] <= args['span']]
        hurricane = hurricanes[-1]
        network = accessibility.readNetwork(args['instance'],args['run'])
        row = {'Participant': participant, 'Timestep': args['span']}
        friends = [friend for friend in network['friendOf'].get(name,set()) if data[friend][stateKey(friend,'alive')][args['span']]]
        row['Number of Friends'] = len(friends)
        row['Number of Friends Evacuated'] = 0
        row['Number of Friends Sheltered'] = 0
        for friend in friends:
            locations = {data[friend][stateKey(friend,'location')][t] for t in range(hurricane['Landfall'],hurricane['End'])}
            if 'evacuated' in locations:
                row['Number of Friends Evacuated'] += 1
            for loc in locations:
                if loc[:7] == 'shelter':
                    row['Number of Friends Sheltered'] += 1
                    break
        worked,possible = accessibility.employment(data,name,hurricane)
        if possible == 0:
            # Unemployed
            row['Days Worked'] = 'N/A'
            row['Missed Work'] = 'N/A'
        else:
            row['Days Worked'] = worked
            row['Missed Work'] = possible - worked
        conductSurvey(row,data,name,hurricanes)
        with open(os.path.join(os.path.dirname(__file__),'Instances','Instance%d' % (instance),'Runs','run-0','TA2B-TA1C-44.tsv'),'w') as csvfile:
            writer = csv.DictWriter(csvfile,fields,delimiter='\t',extrasaction='ignore')
            writer.writeheader()
            writer.writerow(row)

