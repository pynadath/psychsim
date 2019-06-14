import csv
import logging
import os.path
import random

from psychsim.probability import Distribution
from psychsim.pwl import *
from psychsim.domains.groundtruth import accessibility
from psychsim.action import *

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO,filename=os.path.join(os.path.dirname(__file__),'TA2A-TA1C-0192.log'))
    random.seed(192)
    fields = ['Timestep','Participant']+sorted(accessibility.demographics.keys())+['Household Size','Income','Pregnant','Length of Stay',
        'Acquaintances in Region','Acquaintances outside Region','Acquaintances outside Area','Friends in Region','Friends outside Region',
        'Friends outside Area','Family in Region','Family outside Region','Family outside Area','Any Evacuation Request',
        'Voluntary Evacuation Request','Mandatory Evacuation Request','Family Aid Pre','Family Aid During','Family Aid Post',
        'Acquaintance Aid Pre','Acquaintance Aid During','Acquaintance Aid Post','Friend Aid Pre','Friend Aid During','Friend Aid Post']
    sources = ['Government','Friends','Family','Acquaintances','Others','Social Media']
    fields += ['Hurricane Prediction from %s' % (source) for source in sources]
    fields += ['Hurricane Category from %s' % (source) for source in sources]
    fields += ['Hurricane Location from %s' % (source) for source in sources]
    fields += ['Regional Damage from %s' % (source) for source in sources]
    fields += ['Evacuation Factor Transportation','Evacuation Factor Lose Job','Evacuation Factor Looters','Evacuation Factor Home Safer',
        'Evacuation Factor Reduce Damage','Evacuation Factor Lack of Money','Evacuation Factor Not Healthy','Evacuation Factor No Place',
        'Evacuation Factor Elderly','Evacuation Factor Children','Evacuation Factor Pets','Evacuation Factor Health Condition',
        'Experience Affect Evacuation','Experience Affect Risk Perception','Primary Damage Source','Further Damage','Evacuate Home Same',
        'Evacuate Home Different','Direct Injury','Direct Mental Illness','Indirect Injury','Indirect Mental Illness','Chronic Disease',
        'Know Shelter Location','Know Shelter Policy','Never Evacuate','Never Shelter','Take Advantage','Trustworthy','Helpful',
        'Civic Activities','My Region Risk','My House Risk']
    fields += ['Trust in %s' % (source) for source in sources]
    fields.append('Geographical Features')
    for instance in [1,9,10,11,12,13,14]:
        logging.info('Instance %d' % (instance))
        args = accessibility.instances[instance-1]
        config = accessibility.getConfig(args['instance'])
        data = accessibility.loadRunData(args['instance'],args['run'],args['span'],subs=['Input'] if instance > 2 else [None])
        network = accessibility.readNetwork(args['instance'],args['run'],'Input' if instance > 2 else None)
        world = accessibility.loadPickle(args['instance'],args['run'],args['span']+(1 if instance == 2 or instance > 8 else 0),
            sub='Input' if instance > 2 else None)
        hurricanes = [h for h in accessibility.readHurricanes(args['instance'],args['run'],'Input' if instance > 2 else None) 
            if h['End'] < args['span']]
        demos = accessibility.readDemographics(data,last=args['span'])
        population = accessibility.getPopulation(data)
        pool = random.sample(population,16)
        impactJob = config.getint('Actors','job_impact')
        ceiling = config.getboolean('Actors','wealth_ceiling',fallback=False)
        output = []
        participants = {}
        for name in pool:
            agent = world.agents[name]
            record = demos[name]
            output.append(record)
            record.update({'Timestep': args['span'],'Participant': len(output)})
            logging.info('Participant %d: %s' % (record['Participant'],name))
            participants[name] = record['Participant']
            # I.1.k
            record['Household Size'] = 1+record['Children']
            # I.1.l
            if record['Fulltime Job'] == 'yes':
                wealth = data[name][stateKey(name,'resources')][args['span']]
                record['Income'] = impactJob
            else:
                record['Income'] = 0
            # I.1.m
            record['Pregnant'] = 'no'
            # I.1.n
            record['Length of Stay'] = record['Age']
            # I.2.a
            neighbors = {actor for actor in network['neighbor'][name] if actor in population}
            record['Acquaintances in Region'] = len(neighbors)
            # I.2.b
            record['Acquaintances outside Region'] = 0
            # I.2.c
            record['Acquaintances outside Area'] = 0
            # I.2.d
            friends = {actor for actor in network['friendOf'].get(name,set()) if actor in population}
            record['Friends in Region'] = len([actor for actor in friends if demos[actor]['Residence'] == agent.home])
            # I.2.e
            record['Friends outside Region'] = len([actor for actor in friends if demos[actor]['Residence'] != agent.home])
            # I.2.f
            record['Friends outside Area'] = 0
            # I.2.g
            record['Family in Region'] = record['Children']
            # I.2.h
            record['Family outside Region'] = 0
            # I.2.i
            record['Family outside Area'] = 0
            # II.1.a
            record['Any Evacuation Request'] = 'no'
            # II.1.b
            record['Voluntary Evacuation Request'] = 'no'
            # II.1.c
            record['Mandatory Evacuation Request'] = 'no'
            # II.1.c
            record['Mandatory Evacuation Request'] = 'no'
            # II.2
            record['Family Aid Pre'] = 'no'
            # II.2.a
            record['Family Aid During'] = 'no'
            # II.2.b
            record['Family Aid Post'] = 'no'
            # II.2.cde
            aid = set()
            crime = set()
            for actor in neighbors:
                aid |= {t for t,action in data[actor][actionKey(actor)].items() if action['verb'] == 'decreaseRisk'}
                crime |= {t for t,action in data[actor][actionKey(actor)].items() if action['verb'] == 'takeResources'}
            record['Acquaintance Aid Pre'] = 'no'
            record['Acquaintance Aid During'] = 'no'
            record['Acquaintance Aid Post'] = 'no'
            for hurricane in hurricanes:
                if record['Acquaintance Aid Pre'] == 'no':
                    for t in range(hurricane['Start'],hurricane['Landfall']):
                        if t in aid:
                            record['Acquaintance Aid Pre'] = 'yes'
                            break
                if record['Acquaintance Aid During'] == 'no':
                    for t in range(hurricane['Landfall'],hurricane['End']):
                        if t in aid:
                            record['Acquaintance Aid During'] = 'yes'
                            break
                if record['Acquaintance Aid Post'] == 'no':
                    for t in range(hurricane['End'],args['span'] if hurricane['Hurricane'] == len(hurricanes) \
                        else hurricanes[hurricane['Hurricane']]['Start']):
                        if t in aid:
                            record['Acquaintance Aid Post'] = 'yes'
                            break
            # II.2.fgh
            record['Friend Aid Pre'] = 'no'
            record['Friend Aid During'] = 'no'
            record['Friend Aid Post'] = 'no'
            # II.3
            for source in sources:
                record['Hurricane Prediction from %s' % (source)] = 'no'
                record['Hurricane Category from %s' % (source)] = 'no'
                record['Hurricane Location from %s' % (source)] = 'no'
                record['Regional Damage from %s' % (source)] = 'no'
            if friends:
                record['Hurricane Category from Friends'] = 'yes'
            record['Hurricane Category from Social Media'] = 'yes'
            record['Hurricane Location from Social Media'] = 'yes'
            # II.4
            record['Evacuation Factor Transportation'] = 'no'
            if record['Fulltime Job'] == 'yes' and (config.getint('Actors','evacuation_unemployment') > 0):
                record['Evacuation Factor Lose Job'] = 'yes'
            else:
                record['Evacuation Factor Lose Job'] = 'no'
            record['Evacuation Factor Looters'] = 'no'
            record['Evacuation Factor Home Safer'] = 'no'
            record['Evacuation Factor Reduce Damage'] = 'no'
            record['Evacuation Factor Lack of Money'] = 'no'
            record['Evacuation Factor Not Healthy'] = 'no'
            record['Evacuation Factor No Place'] = 'no'
            record['Evacuation Factor Elderly'] = 'no'
            record['Evacuation Factor Children'] = 'no'
            record['Evacuation Factor Pets'] = 'no'
            record['Evacuation Factor Health Condition'] = 'no'
            # II.5
            record['Experience Affect Evacuation'] = 'yes'
            record['Experience Affect Risk Perception'] = 'no'
            record['Primary Damage Source'] = 'don\'t know'
            record['Further Damage'] = 'no'
            # II.6
            record['Evacuate Home Same'] = 'no'
            record['Evacuate Home Different'] = 'no'
            # II.7
            if min(data[name][stateKey(name,'health')].values()) < 0.2:
                record['Direct Injury'] = 'yes'
            else:
                record['Direct Injury'] = 'no'
            record['Direct Mental Illness'] = 'no'
            record['Indirect Injury'] = 'no'
            record['Indirect Mental Illness'] = 'no'
            record['Chronic Disease'] = 'no'
            # II.8
            record['Know Shelter Location'] = 'yes'
            record['Know Shelter Policy'] = 'yes'
            record['Never Evacuate'] = 'no'
            record['Never Shelter'] = 'no'
            # III.1
            record['Take Advantage'] = random.choice([2,3])
            record['Trustworthy'] = random.choice([2,3])
            try:
                record['Helpful'] = min(5,accessibility.toLikert((len(aid)+len(crime))/len(aid|crime))-1)
            except ZeroDivisionError:
                if len(aid) > len(crime):
                    record['Helpful'] = 3
                elif len(aid) < len(crime):
                    record['Helpful'] = 2
                else:
                    record['Helpful'] = random.choice([2,3])
            record['Civic Activities'] = 0
            # III.2
            record['My Region Risk'] = 'don\'t know'
            record['My House Risk'] = 3
            # III.3
            record['Trust in Government'] = 4
            record['Trust in Social Media'] = 1
            record['Trust in Family'] = 5
            record['Trust in Acquaintances'] = 2
            if friends:
                trust = {'over': config.getint('Actors','friend_opt_trust'),
                    'under': config.getint('Actors','friend_pess_trust')}
                trust['none'] = (trust['over']+trust['under'])/2
                record['Trust in Friends'] = int(round(sum([trust[world.agents[friend].distortion] for friend in friends])/len(friends)))
            else:
                record['Trust in Friends'] = 'N/A'
            record['Trust in Others'] = 0
            # IV.1
            record['Geographical Features'] = 'no'
        accessibility.writeOutput(args,output,fields,'TA2A-TA1C-0192.tsv',
            os.path.join(os.path.dirname(__file__),'Instances','Instance%d' % (instance),'Runs','run-0'))
