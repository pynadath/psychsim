import csv
import os.path

from psychsim.pwl.keys import stateKey
from psychsim.domains.groundtruth import accessibility

def augmentRecord(row,data,demos,hurricanes,network):
    matches = accessibility.findMatches(row,population=demos)
    hurricane = hurricanes[int(row['Hurricane'])-1]
    assert hurricane['Hurricane'] == int(row['Hurricane'])
    assert len(matches) == 1
    name = next(iter(matches))
    friends = network['friendOf'].get(name,set())
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

if __name__ == '__main__':
    parser = accessibility.createParser()
    args = accessibility.parseArgs(parser,'%s.log' % (os.path.splitext(__file__)[0]))
    for instance in range(len(accessibility.instances)):
        entry = accessibility.instances[instance]
        if entry['instance'] == args['instance'] and entry['run'] == args['run']:
            break
    else:
        raise ValueError('Unable to find mapping for Instance %d, Run %d' % (args['instance'],args['run']))
    fields = ['Timestep','Participant','Hurricane','Number of Friends','Number of Friends Evacuated','Number of Friends Sheltered']
    hurricanes = accessibility.readHurricanes(args['instance'],args['run'])
    network = accessibility.readNetwork(args['instance'],args['run'])
    data = accessibility.loadRunData(args['instance'],args['run'])
    demos = accessibility.readDemographics(data,True)
    output = []
    if instance == 0 and False:
        with accessibility.openFile(args,'ActorPostTable.tsv') as csvfile:
            reader = csv.DictReader(csvfile,delimiter='\t')
            for row in reader:
                augmentRecord(row,data,demos,hurricanes,network)
                output.append(row)
    with accessibility.openFile(args,'ActorPostNewTable.tsv') as csvfile:
        reader = csv.DictReader(csvfile,delimiter='\t')
        for row in reader:
            augmentRecord(row,data,demos,hurricanes,network)
            output.append(row)
    accessibility.writeOutput(args,output,fields,'TA2B-TA1C-34.tsv',
        os.path.join(os.path.dirname(__file__),'Instances','Instance%d' % (instance+1),'Runs','run-0'))

