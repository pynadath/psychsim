import csv
import logging
import os.path
import random
import sys

from psychsim.pwl.keys import *
from psychsim.domains.groundtruth import accessibility

def survey(entry):
    config = accessibility.getConfig(entry['instance'])
    myScale = accessibility.likert[5][config.getint('Actors','self_trust')-1]
    if config.getint('Actors','friend_opt_trust') > 0:
        optScale = accessibility.likert[5][config.getint('Actors','friend_opt_trust')-1]
    else:
        optScale = 0.
    if config.getint('Actors','friend_pess_trust') > 0:
        pessScale = accessibility.likert[5][config.getint('Actors','friend_pess_trust')-1]
    else:
        pessScale = 0.
    data = accessibility.loadRunData(entry['instance'],entry['run'],entry['span'])
    hurricanes = [h for h in accessibility.readHurricanes(entry['instance'],entry['run']) if h['End'] < entry['span']]
    network = accessibility.readNetwork(entry['instance'],entry['run'])
    population = accessibility.readDemographics(data,last=entry['span'])
    pool = random.sample([name for name in population if data[name][stateKey(name,'alive')][entry['span']]],16)
    output = []
    for participant in range(len(pool)):
        name = pool[participant]
        record = {'Timestep': entry['span'],'Participant':participant+1}
        record.update(population[name])
        output.append(record)
        friends = network['friendOf'].get(name,set())
        live = [friend for friend in friends if data[friend][stateKey(friend,'alive')][entry['span']]]
        record['Number of Friends'] = len(live)
        record['Fewest Friends'] = len(live)
        record['Most Friends'] = len(friends)
        record['New Friends'] = 1
        if friends:
            record['Discontinued Friendships'] = 1
            record['Shared Satisfaction'] = 1
            record['Updated Opinion on Government'] = 1
            record['Shared Sheltering Injury'] = 1
            record['Updated Preference'] = 1
        else:
            record['Discontinued Friendships'] = 'N/A'
            record['Shared Satisfaction'] = 'N/A'
            record['Updated Opinion on Government'] = 'N/A'
            record['Shared Sheltering Injury'] = 'N/A'
            record['Updated Preference'] = 'N/A'
        deltaB = []
        for friend in friends:
            myB = {t: data[name]['__beliefs__'][stateKey('Nature','category')][t] \
                for t in data[name]['__beliefs__'][stateKey('Nature','category')] if data[friend][stateKey(friend,'alive')][t] and \
                data[name]['__beliefs__'][stateKey('Nature','category')][t] != 0.}
            yrB = {t: data[friend]['__beliefs__'][stateKey('Nature','category')][t] for t in myB}
            delta = [float(myB[t])-float(yrB[t]) for t in myB]
            deltaB += [abs(value) for value in delta]
            pess = [-pessScale*b/(pessScale+myScale) for b in delta if b < 0.]
            opt = [optScale*b/(optScale+myScale) for b in delta if b > 0.]
            delta = [abs(value) for value in pess+opt]
            if delta:
                record['Updated Preference'] = max(accessibility.toLikert(max(delta)),record['Updated Preference'])
            else:
                record['Updated Preference'] = 1
        record['Evacuation Assistance'] = 1
        record['Shelter Assistance'] = 1
        record['Riding Out Assistance'] = 1
        record['Media Predicts Track'] = 1
        delta = [abs(float(data[name]['__beliefs__'][stateKey('Nature','category')][hurricane['Landfall']])-\
            float(data[name]['__beliefs__'][stateKey('Nature','category')][hurricane['Start']])) for hurricane in hurricanes]
        record['Media Predicts Landfall Category'] = 6-accessibility.toLikert(sum(delta)/len(delta)/3.)
        delta = [abs(float(data[name]['__beliefs__'][stateKey('Nature','category')][hurricane['End']])-\
            float(data[name]['__beliefs__'][stateKey('Nature','category')][hurricane['Landfall']])) for hurricane in hurricanes]
        record['Media Predicts Category Track'] = 6-accessibility.toLikert(sum(delta)/len(delta)/3.)
        deltaEye = []
        deltaAny = []
        key = stateKey('Region','risk')
        for hurricane in hurricanes:
            for t in range(hurricane['Landfall'],hurricane['End']):
                delta = float(data[name]['__beliefs__'][key][t])-float(data[name]['__beliefs__'][key][t-1])
                delta /= float(data[name]['__beliefs__'][stateKey('Nature','category')][t])
                if hurricane['Actual Location'][t-hurricane['Start']] == record['Residence']:
                    deltaEye.append(delta)
                else:
                    deltaAny.append(delta)
        if deltaEye:
            avgEye = sum(deltaEye)/len(deltaEye)
            avgAny = sum(deltaAny)/len(deltaAny)
            if avgEye and avgAny:
                record['Affect Any Region'] = accessibility.toLikert(avgAny/avgEye)
                record['Impact of Eye'] = accessibility.toLikert(avgEye/avgAny/2.)
            elif avgAny:
                record['Affect Any Region'] = accessibility.toLikert(5)
                record['Impact of Eye'] = accessibility.toLikert(avgEye/avgAny/2.)
        else:
            record['Affect Any Region'] = 3
            record['Impact of Eye'] = 3
        if friends:
            record['Friends Predictions'] = 6-accessibility.toLikert(5*sum(deltaB)/len(deltaB))
            record['Help Friends Evacuate'] = 1
            record['Friends Helped Evacuate'] = 1
        else:
            record['Friends Predictions'] = 'N/A'
            record['Help Friends Evacuate'] = 'N/A'
            record['Friends Helped Evacuate'] = 'N/A'
        injuries = set()
        for friend in friends:
            injuries |= {t for t in data[friend][stateKey(friend,'health')] if data[friend][stateKey(friend,'health')][t] < 0.2}
        if friends and injuries:
            help = [t for t in injuries if data[name][actionKey(name)].get(t,{'verb': None})['verb'] == 'decreaseRisk']
            record['Help Injured Friends'] = accessibility.toLikert(len(help)/len(injuries))
        else:
            record['Help Injured Friends'] = 'N/A'
        injuries |= {t for t in data[name][stateKey(name,'health')] if data[name][stateKey(name,'health')][t] < 0.2}
        if friends and injuries:
            help = set()
            for friend in friends:
                help |= {t for t in injuries if data[friend][actionKey(friend)].get(t,{'verb': None})['verb'] == 'decreaseRisk'}
            record['Friends Helped When Injured'] = accessibility.toLikert(len(help)/len(injuries))
        else:
            record['Friends Helped When Injured'] = 'N/A'
        delta = []
        for hurricane in hurricanes:
            for t in range(hurricane['Landfall'],hurricane['End']):
                delta.append(abs(float(data[name]['__beliefs__'][stateKey(name,'risk')][t])-\
                    float(data[name]['__beliefs__'][stateKey('Region','risk')][t-1])))
        record['Evacuate from Weather'] = 6-accessibility.toLikert(sum(delta)/len(delta))
    return output

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO,filename='%s.log' % (os.path.splitext(__file__)[0]))
    random.seed(35)
    fields = ['Timestep','Participant']+sorted(accessibility.demographics)+['Number of Friends','Fewest Friends','Most Friends','New Friends',\
        'Discontinued Friendships','Shared Satisfaction','Updated Opinion on Government','Shared Sheltering Injury','Updated Preference',\
        'Evacuation Assistance','Shelter Assistance','Riding Out Assistance','Media Predicts Track','Media Predicts Landfall Category',\
        'Media Predicts Category Track','Affect Any Region','Impact of Eye','Friends Predictions',\
        'Help Friends Evacuate','Friends Helped Evacuate','Help Injured Friends','Friends Helped When Injured','Evacuate from Weather']
    for instance in range(len(accessibility.instances)):
        entry = accessibility.instances[instance]
        if instance == 0:
            entry['span'] == 551
        dirname = accessibility.getDirectory(entry)
        logging.info('Instance %d, run %d' % (entry['instance'],entry['run']))
        output = survey(entry)
        # Save Data
        with open(os.path.join(os.path.dirname(__file__),'Instances','Instance%d' % (instance+1),'Runs','run-0','TA2B-TA1C-35.tsv'),'w') as csvfile:
            writer = csv.DictWriter(csvfile,fields,delimiter='\t',extrasaction='ignore')
            writer.writeheader()
            for record in output:
                writer.writerow(record)
