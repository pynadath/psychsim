import csv
import logging
import os.path
import random

from psychsim.pwl.keys import *
from psychsim.domains.groundtruth import accessibility

regions = ['Region%02d' % (region+1) for region in range(16)]

def survey(entry):
    data = accessibility.loadRunData(entry['instance'],entry['run'],entry['span'])
    hurricanes = [h for h in accessibility.readHurricanes(entry['instance'],entry['run']) if h['End'] < entry['span']]
    network = accessibility.readNetwork(entry['instance'],entry['run'])
    population = accessibility.readDemographics(data,last=entry['span'])
    deaths = {name: min([t for t,alive in data[name][stateKey(name,'alive')].items() if not alive],default=None) \
        for name in population}
    dead = {name for name in deaths if deaths[name] is not None}
    sheltered = {name: set() for name in population}
    for name in population:
        for hurricane in hurricanes:
            if deaths[name] is None or deaths[name] > hurricane['Start']:
                for t in range(hurricane['Start'],min(entry['span'] if deaths[name] is None else deaths[name],hurricane['End']+1)):
                    if data[name][actionKey(name)][t]['verb'] == 'moveTo' and data[name][actionKey(name)][t]['object'][:7] == 'shelter':
                        sheltered[name].add(hurricane['Hurricane'])
                        break
    evacuated = {name: set() for name in population}
    for name in population:
        for hurricane in hurricanes:
            if deaths[name] is None or deaths[name] > hurricane['Start']:
                for t in range(hurricane['Start'],min(entry['span'] if deaths[name] is None else deaths[name],hurricane['End']+1)):
                    if data[name][actionKey(name)][t]['verb'] == 'evacuate':
                        evacuated[name].add(hurricane['Hurricane'])
                        break
    pool = random.sample([name for name,death in deaths.items() if death is None],16)
    output = []
    for participant in range(len(pool)):
        name = pool[participant]
        record = {'Timestep': entry['span'],'Participant':participant+1}
        logging.info('Participant %d: %s' % (participant+1,name))
        record.update(population[name])
        output.append(record)
        if name in network['friendOf']:
            friends = list(network['friendOf'][name])
        else:
            friends = []
        for region in regions:
            subset = [f for f in friends if population[f]['Residence'] == region]
            # 1-16
            record['Initial Friends %s' % (region)] = len(subset)
            # 17-32
            record['Current Friends %s' % (region)] = len([f for f in subset if deaths[f] is None])
            # 33
            record['# Friends Sheltered'] = len([f for f in friends if sheltered[f]])
            # 34
            record['# Friends Loss'] = 0
            # 35 
            record['# Friends Unknown'] = 0
            for f1 in range(len(friends)-1):
                name1 = friends[f1]
                for f2 in range(f1+1,len(friends)):
                    name2 = friends[f2]
                    if name2 not in network['friendOf'].get(name1,set()):
                        record['# Friends Unknown'] += 1
            # 36
            record['Assisted Injured Friend'] = 0
            neighbors = [f for f in friends if population[f]['Residence'] == population[name]['Residence']]
            if neighbors:
                start = None
                for hurricane in hurricanes:
                    for f in neighbors:
                        injured = [t for t in range(hurricane['Start'],hurricane['End']+1) if data[f][stateKey(f,'health')][t] < 0.2]
                        if injured: 
                            if start is None:
                                start = min(injured)
                            else:
                                start = min(min(injured),start)
                    else:
                        continue
                    for t in range(start,hurricane['End']+1):
                        if data[name][actionKey(name)][t]['verb'] == 'decreaseRisk':
                            record['Assisted Injured Friend'] += 1                         
            # 37
            record['# Times Friends Sheltered'] = sum([len(sheltered[f]) for f in friends])
            # 38
            record['# Times Sheltered'] = len(sheltered[name])
            # 39
            record['# Different Friends Sheltered'] = len([f for f in friends if sheltered[f]])
            # 40 
            record['# Times Friends Evacuated'] = sum([len(evacuated[f]) for f in friends])
            # 41
            record['# Different Friends Evacuated'] = len([f for f in friends if evacuated[f]])
            # 42
            record['# Times Evacuated'] = len(evacuated[name])
        # 43
        record['# Ethnic Majority Friends'] = len([f for f in friends if population[f]['Ethnicity'] == 'majority'])
        # 44
        record['# Male Friends'] = len([f for f in friends if population[f]['Gender'] == 'male'])
        # 45
        record['# Older Friends'] = len([f for f in friends if population[f]['Age'] > 50])
        # 46
        record['# Religious Majority Friends'] = len([f for f in friends if population[f]['Religion'] == 'majority'])
    return output

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO,filename='%s.log' % (os.path.splitext(__file__)[0]))
    random.seed(38)
    fields = ['Timestep','Participant']+sorted(accessibility.demographics)+['Initial Friends %s' % (r) for r in regions]+\
        ['Current Friends %s' % (r) for r in regions]+['# Friends Sheltered','# Friends Loss','# Friends Unknown',\
        'Assisted Injured Friend','# Times Friends Sheltered','# Times Sheltered','# Different Friends Sheltered',\
        '# Times Friends Evacuated','# Different Friends Evacuated','# Times Evacuated','# Ethnic Majority Friends',\
        '# Male Friends','# Older Friends','# Religious Majority Friends']
    for instance in range(len(accessibility.instances)):
        entry = accessibility.instances[instance]
        if instance == 0:
            entry['span'] = 551
        dirname = accessibility.getDirectory(entry)
        logging.info('Instance %d, run %d' % (entry['instance'],entry['run']))
        output = survey(entry)
        # Save Data
        with open(os.path.join(os.path.dirname(__file__),'Instances','Instance%d' % (instance+1),'Runs','run-0','TA2B-TA1C-38.tsv'),'w') as csvfile:
            writer = csv.DictWriter(csvfile,fields,delimiter='\t',extrasaction='ignore',restval='N/A')
            writer.writeheader()
            for record in output:
                writer.writerow(record)
