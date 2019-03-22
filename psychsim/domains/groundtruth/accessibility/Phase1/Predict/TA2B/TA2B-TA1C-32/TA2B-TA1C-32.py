import csv
import logging
import os.path
import random

from psychsim.pwl.keys import *
from psychsim.domains.groundtruth import accessibility

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO,filename='%s.log' % (os.path.splitext(__file__)[0]))
    for instance in range(2,len(accessibility.instances)):
        entry = accessibility.instances[instance]
        config = accessibility.getConfig(entry['instance'])
        dirname = accessibility.getDirectory(entry)
        logging.info('Instance %d, run %d' % (entry['instance'],entry['run']))
        data = accessibility.loadRunData(entry['instance'],entry['run'],entry['span'])
        idMap = accessibility.readParticipants(entry['instance'],entry['run'],os.path.join('Input','psychsim.log'))
        network = accessibility.readNetwork(entry['instance'],entry['run'])
        hurricanes = [h for h in accessibility.readHurricanes(entry['instance'],entry['run']) if h['End'] < entry['span']]
        # Pre-hurricane Survey
        fields = None
        outputOld = []
        outputNew = []
        responses = {name: set() for name in idMap['ActorPreTable'].values()}
        with accessibility.openFile(entry,os.path.join('Input','ActorPreTable.tsv')) as csvfile:
            reader = csv.DictReader(csvfile,delimiter='\t')
            for row in reader:
                name = idMap['ActorPreTable'][int(row['Participant'])]
                hurricane = hurricanes[int(row['Hurricane'])-1]
                assert hurricane['Hurricane'] == int(row['Hurricane'])
                responses[name].add(hurricane['Hurricane'])
                outputOld.append(row)
                if fields is None:
                    fields = list(row.keys())
        for i in range(len(outputOld)):
            row = outputOld[i]
            try:
                hurricane = hurricanes[int(row['Hurricane'])]
            except IndexError:
                continue
            # Conduct a follow-up survey
            name = idMap['ActorPreTable'][int(row['Participant'])]
            t = hurricane['Start']+int(row['Timestep'])-hurricanes[int(row['Hurricane'])-1]['Start']
            if not data[name][stateKey(name,'alive')][t]:
                logging.warning('Pre: %s (%s) has died (Day %d)' % (name,row['Participant'],t))
                continue
            if hurricane['Hurricane'] in responses[name]:
                # Already answered this survey
                for j in range(i+1,len(outputOld)):
                    oldRow = outputOld[j]
                    assert int(oldRow['Hurricane']) < hurricane['Hurricane']+1
                    if idMap['ActorPreTable'][int(oldRow['Participant'])] == name:
                        logging.warning('Pre: %s -> %s' % (oldRow['Participant'],row['Participant']))
                        oldRow['Participant'] = row['Participant']
                        break
                else:
                    raise RuntimeError
                continue
            newRow = dict(row)
            newRow['Timestep'] = t
            newRow['Hurricane'] = hurricane['Hurricane']
            newRow['Wealth'] = accessibility.toLikert(data[name][stateKey(name,'resources')][t])
            key = stateKey(name,'employed')
            newRow['Fulltime Job'] = 'yes' if data[name][key].get(t,data[name][key][1]) else 'no'
            loc = data[name][stateKey(name,'location')][t]
            newRow['At Shelter'] = 'yes' if loc[:7] == 'shelter' else 'no'
            newRow['Evacuated'] = 'yes' if loc == 'evacuated' else 'no'
            newRow['Severity'] = int(round(float(data[name]['__beliefs__'][stateKey('Nature','category')][t])))
            assert set(newRow.keys()) == set(fields)
            outputNew.append(newRow)
        output = sorted(outputOld+outputNew,key=lambda row: (int(row['Timestep']),int(row['Participant'])))
        # Save Data
        with open(os.path.join(os.path.dirname(__file__),'Instances','Instance%d' % (instance+1),'Runs','run-0','TA2B-TA1C-32-Pre.tsv'),'w') as csvfile:
            writer = csv.DictWriter(csvfile,fields,delimiter='\t',extrasaction='ignore')
            writer.writeheader()
            for record in output:
                writer.writerow(record)
        # Post-hurricane Survey
        fields = None
        outputOld = []
        outputNew = []
        responses = {name: set() for name in idMap['ActorPostTable'].values()}
        with accessibility.openFile(entry,os.path.join('Input','ActorPostTable.tsv')) as csvfile:
            reader = csv.DictReader(csvfile,delimiter='\t')
            for row in reader:
                name = idMap['ActorPostTable'][int(row['Participant'])]
                hurricane = hurricanes[int(row['Hurricane'])-1]
                assert hurricane['Hurricane'] == int(row['Hurricane'])
                responses[name].add(hurricane['Hurricane'])
                outputOld.append(row)
                if fields is None:
                    fields = list(row.keys())+['Property','Assistance','Number of Friends','Number of Friends Evacuated',
                        'Number of Friends Sheltered','Missed Work','Days Worked']
                row['Property'] = accessibility.propertyDamage(data,hurricane,row['Residence'])
                row['Assistance'] = accessibility.assistance(data,hurricane,row['Residence'])
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
                worked,possible = accessibility.employment(data,name,hurricane)
                if possible == 0:
                    # Unemployed
                    row['Days Worked'] = 'N/A'
                    row['Missed Work'] = 'N/A'
                else:
                    row['Days Worked'] = worked
                    row['Missed Work'] = possible - worked
        for i in range(len(outputOld)):
            row = outputOld[i]
            try:
                hurricane = hurricanes[int(row['Hurricane'])]
            except IndexError:
                continue
            # Conduct a follow-up survey
            name = idMap['ActorPostTable'][int(row['Participant'])]
            t = min(hurricane['End']+int(row['Timestep'])-hurricanes[int(row['Hurricane'])-1]['End'],entry['span']-1)
            if not data[name][stateKey(name,'alive')][t]:
                logging.warning('Post: %s (%s) has died (Day %d)' % (name,row['Participant'],t))
                continue
            if hurricane['Hurricane'] in responses[name]:
                # Already answered this survey
                for j in range(i+1,len(outputOld)):
                    oldRow = outputOld[j]
                    assert int(oldRow['Hurricane']) < hurricane['Hurricane']+1
                    if idMap['ActorPostTable'][int(oldRow['Participant'])] == name:
                        logging.warning('Post: %s -> %s' % (oldRow['Participant'],row['Participant']))
                        oldRow['Participant'] = row['Participant']
                        break
                else:
                    raise RuntimeError
                continue
            newRow = dict(row)
            newRow['Wealth'] = accessibility.toLikert(data[name][stateKey(name,'resources')][t])
            key = stateKey(name,'employed')
            newRow['Fulltime Job'] = 'yes' if data[name][key].get(t,data[name][key][1]) else 'no'
            friends = network['friendOf'].get(name,set())
            newRow['Number of Friends Evacuated'] = 0
            newRow['Number of Friends Sheltered'] = 0
            for friend in friends:
                locations = {data[friend][stateKey(friend,'location')][t] for t in range(hurricane['Landfall'],hurricane['End'])}
                if 'evacuated' in locations:
                    newRow['Number of Friends Evacuated'] += 1
                for loc in locations:
                    if loc[:7] == 'shelter':
                        newRow['Number of Friends Sheltered'] += 1
                        break
            locations = {data[name][stateKey(name,'location')][t] for t in range(hurricane['Landfall'],hurricane['End'])}
            worked,possible = accessibility.employment(data,name,hurricane)
            if possible == 0:
                # Unemployed
                newRow['Days Worked'] = 'N/A'
                newRow['Missed Work'] = 'N/A'
            else:
                newRow['Days Worked'] = worked
                newRow['Missed Work'] = possible - worked
            for field in newRow:
                if field == 'Timestep':
                    newRow[field] = t
                elif field == 'Hurricane':
                    newRow[field] = hurricane['Hurricane']
                elif field == 'Dissatisfaction Previous Hurricane':
                    key = stateKey(name,'grievance')
                    delta = data[name][key][hurricane['End']] - data[name][key][hurricane['Landfall']]
                    newRow[field] = accessibility.toLikert((delta+1.)/2.)
                elif field == 'Injured Previous Hurricane':
                    key = stateKey(name,'health')
                    series = [float(data[name]['__beliefs__'][key][t]) for t in range(hurricane['Landfall'],hurricane['End'])]
                    newRow[field] = 'yes' if min(series) < 0.2 else 'no'
                elif field == 'Risk Previous Hurricane':
                    key = stateKey(name,'risk')
                    series = [float(data[name]['__beliefs__'][key][t]) for t in range(hurricane['Landfall'],hurricane['End'])]
                    newRow[field] = accessibility.toLikert(max(series))
                elif field == 'Evacuated Previous Hurricane':
                    newRow[field] = 'yes' if 'evacuated' in locations else 'no'
                elif field == 'At Shelter Previous Hurricane':
                    for loc in locations:
                        if loc[:7] == 'shelter':
                            newRow[field] = 'yes'
                            break
                    else:
                        newRow[field] = 'no'
                elif field == 'Property':
                    newRow[field] = accessibility.propertyDamage(data,hurricane,row['Residence'])
                elif field == 'Assistance':
                    newRow[field] = accessibility.assistance(data,hurricane,row['Residence'])
                elif field not in accessibility.demographics and \
                    field not in {'Participant','Number of Friends','Number of Friends Evacuated','Number of Friends Sheltered',\
                        'Missed Work','Days Worked'}:
                    raise RuntimeError(field)
            outputNew.append(newRow)
        output = sorted(outputOld+outputNew,key=lambda row: (int(row['Timestep']),int(row['Participant'])))
        # Save Data
        with open(os.path.join(os.path.dirname(__file__),'Instances','Instance%d' % (instance+1),'Runs','run-0','TA2B-TA1C-32-Post.tsv'),'w') as csvfile:
            writer = csv.DictWriter(csvfile,fields,delimiter='\t',extrasaction='ignore')
            writer.writeheader()
            for record in output:
                writer.writerow(record)
