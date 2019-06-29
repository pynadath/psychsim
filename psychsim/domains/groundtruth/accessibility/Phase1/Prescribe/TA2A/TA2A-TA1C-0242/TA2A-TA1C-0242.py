import csv
import logging
import os.path
import random

from psychsim.probability import Distribution
from psychsim.pwl import *
from psychsim.domains.groundtruth import accessibility
from psychsim.action import *

request = 242
items = [{'Name': 'Friends Outside Region','Values':'0+','DataType': 'Integer','Notes': 'QI.2'},
    {'Name': 'Friends Within Region','Values':'0+','DataType': 'Integer','Notes': 'QI.3'},
    {'Name': 'Hurricane Vulnerability','Values':'[1-5]','DataType': 'Integer','Notes': 'QI.5'},
    {'Name': 'Aid if Wealth Loss','Values':'[0-6]','DataType': 'Integer','Notes': 'QI.6'},
    {'Name': 'My Dissatisfaction Effectiveness','Values':'a-h ordering','DataType': 'String','Notes': 'QII.1'},
    {'Name': 'My Injury Risk Effectiveness','Values':'a-h ordering','DataType': 'String','Notes': 'QII.2'},
    {'Name': 'Risk Effectiveness','Values':'a-h ordering','DataType': 'String','Notes': 'QII.3'},
    {'Name': 'My Injury Effectiveness','Values':'a-h ordering','DataType': 'String','Notes': 'QII.4'},
    {'Name': 'Regional Dissatisfaction Effectiveness','Values':'a-h ordering','DataType': 'String','Notes': 'QII.5'},
    {'Name': 'Regional Injury Effectiveness','Values':'a-h ordering','DataType': 'String','Notes': 'QII.6'},
    ]
policies = {'a': 'Pay Evacuees','b': 'Aid Location','c': 'Shelter All Poor','d': 'Pay Injured','e': 'Evacuate Old','f': 'Evacuate Minority',
    'g': 'Evacuate Children','h': 'Communicate Prediction'}

def evacuationGrievance(hurricanes,evacuations,Rwealth,grievanceDelta):
    value = 0.5 + len(evacuations)*0.4*Rwealth
    if Rwealth > grievanceDelta:
        for i in range(len(hurricanes)-len(evacuations)):
            value = value*(1-(Rwealth-grievanceDelta)) + Rwealth - grievanceDelta
    else:
        value *= pow(1+Rwealth-grievanceDelta,len(hurricanes)-len(evacuations))
    return value

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO,filename=os.path.join(os.path.dirname(__file__),'TA2A-TA1C-%04d.log' % (request)))
    random.seed(request)
    accessibility.writeVarDef(os.path.dirname(__file__),items)
    fields = ['Timestep','Participant']+sorted(accessibility.demographics.keys())+[item['Name'] for item in items]
    for instance in [1,9,10,11,12,13,14]:
        logging.info('Instance %d' % (instance))
        args = accessibility.instances[instance-1]
        config = accessibility.getConfig(args['instance'])
        world = accessibility.loadPickle(args['instance'],args['run'],args['span']+(1 if instance == 2 or instance > 8 else 0),
            sub='Input' if instance > 2 else None)
        data = accessibility.loadRunData(args['instance'],args['run'],args['span'],subs=['Input'] if instance > 2 else [None])
        hurricanes = [h for h in accessibility.readHurricanes(args['instance'],args['run'],'Input' if instance > 2 else None) if h['End'] <= args['span']]
        network = accessibility.readNetwork(args['instance'],args['run'],'Input' if instance > 2 else None)
        demos = accessibility.readDemographics(data,last=args['span'])
        govtAid = accessibility.aidTargets(data)
        population = accessibility.getPopulation(data)
        systemDelta = accessibility.likert[5][config.getint('System','system_impact')-1]
        grievanceDelta = accessibility.likert[5][config.getint('Actors','grievance_delta')-1]
        pool = random.sample(population,16)
        output = []
        for name in pool:
            agent = world.agents[name]
            record = demos[name]
            output.append(record)
            record.update({'Timestep': args['span'],'Participant': len(output)})
            logging.info('Participant %d: %s' % (record['Participant'],name))
            friends = {friend for friend in network['friendOf'].get(name,[]) if friend in population}
            neighbors = {neighbor for neighbor in network['neighbor'][name] if neighbor in population}
            risks = {t: float(belief) for t,belief in data[name]['__beliefs__'][stateKey(name,'risk')].items()}
            evacuationTimes = {t for t,action in data[name][actionKey(name)].items() if action['verb'] == 'evacuate'}
            evacuations = {h['Hurricane'] for h in hurricanes if set(range(h['Start'],h['End']))&evacuationTimes}
            shelterTimes = {t for t,loc in data[name][stateKey(name,'location')].items() if loc[:7] == 'shelter'}
            shelters = {h['Hurricane'] for h in hurricanes if set(range(h['Start'],h['End']))&shelterTimes}
            Rwealth = agent.Rweights['resources']/sum(agent.Rweights.values())
            for item in items:
                if item['Name'] == 'Friends Outside Region':
                    record[item['Name']] = len([friend for friend in friends if demos[friend]['Residence'] != record['Residence']])
                elif item['Name'] == 'Friends Within Region':
                    record[item['Name']] = len([friend for friend in friends if demos[friend]['Residence'] == record['Residence']])
                elif item['Name'] == 'Hurricane Vulnerability':
                    values = sum([[risks[t] for t in range(h['Landfall'],h['End'])] for h in hurricanes],[])
                    record[item['Name']] = accessibility.toLikert(sum(values)/len(values))
                elif item['Name'] == 'Aid if Wealth Loss':
                    value = sum([agent.Rweights[k] for k in ['health','childrenHealth','neighbors']])/sum(agent.Rweights.values())
                    record[item['Name']] = accessibility.toLikert(value,7)-1
                elif item['Name'] == 'My Dissatisfaction Effectiveness':
                    values = {}
                    for key,policy in policies.items():
                        if policy == 'Pay Evacuees':
                            count = len([t for t,action in data[name][actionKey(name)].items() if action['verb'] == 'evacuate'])
                            values[key] = 0.5+count*0.4*Rwealth
                        elif policy == 'Aid Location':
                            delta = 0
                            for hurricane in hurricanes:
                                for t in range(hurricane['Landfall'],hurricane['End']):
                                    if govtAid[t] == record['Residence']:
                                        delta -= 1
                                    if hurricane['Actual Location'][t-hurricane['Start']] == record['Residence']:
                                        delta += 1
                            if delta <= 0:
                                values[key] = 0.5*pow(1-grievanceDelta,-delta)
                            else:
                                values[key] = 0.5
                                for i in range(delta):
                                    values[key] = values[key]*(1-grievanceDelta) + grievanceDelta
                        elif policy == 'Shelter All Poor':
                            delta = 0
                            wealth = [accessibility.toLikert(data[name][stateKey(name,'resources')][t]) \
                                for t,loc in data[name][stateKey(name,'location')].items() if loc[:7] == 'shelter']
                            delta -= len([val for val in wealth if val > 2])/len(hurricanes)
                            if record['Pets'] == 'yes':
                                if accessibility.toLikert(min(data[name][stateKey(name,'resources')].values())) < 3:
                                    delta += grievanceDelta
                            values[key] = 0.5+delta
                        elif policy == 'Pay Injured':
                            values[key] = 0.5
                        elif policy == 'Evacuate Old':
                            if record['Age'] > 60:
                                values[key] = evacuationGrievance(hurricanes,evacuations,Rwealth,grievanceDelta)
                            else:
                                values[key] = 0.5
                        elif policy == 'Evacuate Minority':
                            if record['Ethnicity'] == 'minority':
                                values[key] = evacuationGrievance(hurricanes,evacuations,Rwealth,grievanceDelta)
                            else:
                                values[key] = 0.5                                
                        elif policy == 'Evacuate Children':
                            if record['Children'] > 0:
                                values[key] = evacuationGrievance(hurricanes,evacuations,Rwealth,grievanceDelta)
                            else:
                                values[key] = 0.5
                        elif policy == 'Communicate Prediction':
                            # Assume prediction is wrong
                            values[key] = 0.5*(1-grievanceDelta)
                        else:
                            raise ValueError('Unknown policy: %s' % (policy))
                    Vpi = sorted(values.items(),key=lambda V: V[1],reverse=True)
                    record[item['Name']] = ','.join([V[0] for V in Vpi])
                elif item['Name'] == 'My Injury Risk Effectiveness':
                    values = {}
                    for key,policy in policies.items():
                        if policy == 'Pay Evacuees':
                            values[key] = 0.5
                            for hurricane in hurricanes:
                                if hurricane['Hurricane'] not in evacuations:
                                    delta = Rwealth*0.4*max([float(data[name]['__beliefs__'][stateKey(name,'risk')][t]) \
                                        for t in range(hurricane['Start'],hurricane['End'])])
                                    values[key] += delta/len(hurricanes)
                        elif policy == 'Aid Location':
                            values[key] = 0.5
                            for hurricane in hurricanes:
                                for t in range(hurricane['Landfall'],hurricane['End']):
                                    if govtAid[t] == record['Residence']:
                                        if hurricane['Actual Location'][t-hurricane['Start']] != govtAid[t]:
                                            # Undoing government aid
                                            values[key] *= (1-systemDelta)
                                    elif hurricane['Actual Location'][t-hurricane['Start']] == record['Residence']:
                                        values[key] = values[key]*(1-systemDelta) + systemDelta
                        elif policy == 'Shelter All Poor':
                            values[key] = 0.5
                            for hurricane in hurricanes:
                                if hurricane['Hurricane'] in shelters:
                                    # Would I have been able to shelter?
                                    if accessibility.toLikert(data[name][stateKey(name,'resources')][hurricane['Start']]) > 2:
                                        # Nope, so I'm no exposed to home risk
                                        values[key] -= max([float(data[name]['__beliefs__'][stateKey('Region','risk')][t]) \
                                            for t in range(hurricane['Start'],hurricane['End'])])/len(hurricanes)
                                        # Instead of shelter risk
                                        values[key] += max([float(data[name]['__beliefs__'][stateKey('Region','shelterRisk')][t]) \
                                            for t in range(hurricane['Start'],hurricane['End'])])/len(hurricanes)
                                else:
                                    # Now could I shelter?
                                    if accessibility.toLikert(data[name][stateKey(name,'resources')][hurricane['Start']]) < 3 and \
                                        record['Pets'] == 'yes':
                                        # Maybe! Avoiding my previous level of risk
                                        values[key] += max([float(data[name]['__beliefs__'][stateKey(name,'risk')][t]) \
                                            for t in range(hurricane['Start'],hurricane['End'])])/len(hurricanes)
                                        # And only having to face shelter risk
                                        values[key] -= max([float(data[name]['__beliefs__'][stateKey('Region','shelterRisk')][t]) \
                                            for t in range(hurricane['Start'],hurricane['End'])])/len(hurricanes)
                        elif policy == 'Pay Injured':
                            values[key] = 0.5
                            for hurricane in hurricanes:
                                for t in range(hurricane['Start'],hurricane['End']):
                                    if float(data[name]['__beliefs__'][stateKey(name,'health')][t]) < 0.2 and hurricane['Hurricane'] in evacuations:
                                        # Maybe I would've evacuated with this money!
                                        values[key] += Rwealth*0.4*max([float(data[name]['__beliefs__'][stateKey(name,'risk')][t]) \
                                            for t in range(hurricane['Start'],hurricane['End'])])/len(hurricanes)
                                        break
                        elif policy == 'Evacuate Old':
                            values[key] = 0.5
                            if record['Age'] > 60:
                                for hurricane in hurricanes:
                                    if hurricane['Hurricane'] not in evacuations:
                                        delta = max([float(data[name]['__beliefs__'][stateKey(name,'risk')][t]) \
                                            for t in range(hurricane['Start'],hurricane['End'])])
                                        values[key] += delta/len(hurricanes)/2
                        elif policy == 'Evacuate Minority':
                            values[key] = 0.5
                            if record['Ethnicity'] == 'minority':
                                for hurricane in hurricanes:
                                    if hurricane['Hurricane'] not in evacuations:
                                        delta = max([float(data[name]['__beliefs__'][stateKey(name,'risk')][t]) \
                                            for t in range(hurricane['Start'],hurricane['End'])])
                                        values[key] += delta/len(hurricanes)/2
                        elif policy == 'Evacuate Children':
                            values[key] = 0.5
                            if record['Children'] > 0:
                                for hurricane in hurricanes:
                                    if hurricane['Hurricane'] not in evacuations:
                                        delta = max([float(data[name]['__beliefs__'][stateKey(name,'risk')][t]) \
                                            for t in range(hurricane['Start'],hurricane['End'])])
                                        values[key] += delta/len(hurricanes)/2
                        elif policy == 'Communicate Prediction':
                            values[key] = 0.5
                        else:
                            raise ValueError('Unknown policy: %s' % (policy))
                    Vpi = sorted(values.items(),key=lambda V: V[1],reverse=True)
                    record[item['Name']] = ','.join([V[0] for V in Vpi])
                elif item['Name'] == 'Risk Effectiveness':
                    record[item['Name']] = record['My Injury Risk Effectiveness']
                elif item['Name'] == 'My Injury Effectiveness':
                    record[item['Name']] = record['My Injury Risk Effectiveness']
                elif item['Name'] == 'Regional Dissatisfaction Effectiveness':
                    values = {}
                    for key,policy in policies.items():
                        if policy == 'Pay Evacuees':
                            values[key] = 0.5
                        elif policy == 'Aid Location':
                            delta = 0
                            for hurricane in hurricanes:
                                for t in range(hurricane['Landfall'],hurricane['End']):
                                    if govtAid[t] == record['Residence']:
                                        delta -= 1
                                    if hurricane['Actual Location'][t-hurricane['Start']] == record['Residence']:
                                        delta += 1
                            if delta <= 0:
                                values[key] = 0.5*pow(1-grievanceDelta,-delta)
                            else:
                                values[key] = 0.5
                                for i in range(delta):
                                    values[key] = values[key]*(1-grievanceDelta) + grievanceDelta
                        elif policy == 'Shelter All Poor':
                            eligible = [other for other in neighbors if demos[other]['Pets'] == 'yes' and \
                                demos[other]['Wealth'] < 3]
                            values[key] = 0.5
                            for other in eligible:
                                values[key] = values[key]*(1-grievanceDelta/len(neighbors)) + grievanceDelta/len(neighbors)
                        elif policy == 'Pay Injured':
                            values[key] = 0.5
                        elif policy == 'Evacuate Old':
                            eligible = [other for other in neighbors if demos[other]['Age'] > 60]
                            values[key] = 0.5
                            for other in eligible:
                                values[key] = values[key]*(1-grievanceDelta/len(neighbors)) + grievanceDelta/len(neighbors)
                        elif policy == 'Evacuate Minority':
                            eligible = [other for other in neighbors if demos[other]['Ethnicity'] == 'minority']
                            values[key] = 0.5
                            for other in eligible:
                                values[key] = values[key]*(1-grievanceDelta/len(neighbors)) + grievanceDelta/len(neighbors)
                        elif policy == 'Evacuate Children':
                            eligible = [other for other in neighbors if demos[other]['Children'] > 0]
                            values[key] = 0.5
                            for other in eligible:
                                values[key] = values[key]*(1-grievanceDelta/len(neighbors)) + grievanceDelta/len(neighbors)
                        elif policy == 'Communicate Prediction':
                            # Assume prediction is wrong
                            values[key] = 0.5*(1-grievanceDelta)
                        else:
                            raise ValueError('Unknown policy: %s' % (policy))
                    Vpi = sorted(values.items(),key=lambda V: V[1],reverse=True)
                    record[item['Name']] = ','.join([V[0] for V in Vpi])
                elif item['Name'] == 'Regional Injury Effectiveness':
                    values = {}
                    for key,policy in policies.items():
                        if policy == 'Pay Evacuees':
                            values[key] = 0.5
                        elif policy == 'Aid Location':
                            values[key] = 0.5
                            for hurricane in hurricanes:
                                for t in range(hurricane['Landfall'],hurricane['End']):
                                    if govtAid[t] == record['Residence']:
                                        if hurricane['Actual Location'][t-hurricane['Start']] != govtAid[t]:
                                            # Undoing government aid
                                            values[key] *= (1-systemDelta)
                                    elif hurricane['Actual Location'][t-hurricane['Start']] == record['Residence']:
                                        values[key] = values[key]*(1-systemDelta) + systemDelta
                        elif policy == 'Shelter All Poor':
                            values[key] = 0.5
                            eligible = len([other for other in neighbors if demos[other]['Pets'] == 'yes' and \
                                demos[other]['Wealth'] < 3])/len(neighbors)
                            for hurricane in hurricanes:
                                shelterRisk = max([float(data[name]['__beliefs__'][stateKey('Region','shelterRisk')][t]) \
                                    for t in range(hurricane['Start'],hurricane['End'])])
                                regionRisk = max([float(data[name]['__beliefs__'][stateKey('Region','risk')][t]) \
                                    for t in range(hurricane['Start'],hurricane['End'])])
                                values[key] += eligible*(regionRisk-shelterRisk)/(hurricane['End']-hurricane['Start'])/len(hurricanes)
                        elif policy == 'Pay Injured':
                            values[key] = 0.5
                        elif policy == 'Evacuate Old':
                            values[key] = 0.5
                            eligible = len([other for other in neighbors if demos[other]['Age'] > 60])/len(neighbors)
                            for hurricane in hurricanes:
                                shelterRisk = max([float(data[name]['__beliefs__'][stateKey('Region','shelterRisk')][t]) \
                                    for t in range(hurricane['Start'],hurricane['End'])])
                                regionRisk = max([float(data[name]['__beliefs__'][stateKey('Region','risk')][t]) \
                                    for t in range(hurricane['Start'],hurricane['End'])])
                                values[key] += eligible*(regionRisk-shelterRisk)/(hurricane['End']-hurricane['Start'])/len(hurricanes)
                        elif policy == 'Evacuate Minority':
                            values[key] = 0.5
                            eligible = len([other for other in neighbors if demos[other]['Ethnicity'] == 'minority'])/len(neighbors)
                            for hurricane in hurricanes:
                                shelterRisk = max([float(data[name]['__beliefs__'][stateKey('Region','shelterRisk')][t]) \
                                    for t in range(hurricane['Start'],hurricane['End'])])
                                regionRisk = max([float(data[name]['__beliefs__'][stateKey('Region','risk')][t]) \
                                    for t in range(hurricane['Start'],hurricane['End'])])
                                values[key] += eligible*(regionRisk-shelterRisk)/(hurricane['End']-hurricane['Start'])/len(hurricanes)
                        elif policy == 'Evacuate Children':
                            values[key] = 0.5
                            eligible = len([other for other in neighbors if demos[other]['Children'] > 0])/len(neighbors)
                            for hurricane in hurricanes:
                                shelterRisk = max([float(data[name]['__beliefs__'][stateKey('Region','shelterRisk')][t]) \
                                    for t in range(hurricane['Start'],hurricane['End'])])
                                regionRisk = max([float(data[name]['__beliefs__'][stateKey('Region','risk')][t]) \
                                    for t in range(hurricane['Start'],hurricane['End'])])
                                values[key] += eligible*(regionRisk-shelterRisk)/(hurricane['End']-hurricane['Start'])/len(hurricanes)
                        elif policy == 'Communicate Prediction':
                            values[key] = 0.5
                        else:
                            raise ValueError('Unknown policy: %s' % (policy))
                    Vpi = sorted(values.items(),key=lambda V: V[1],reverse=True)
                    record[item['Name']] = ','.join([V[0] for V in Vpi])
                else:
                    raise ValueError('Unknown item: %s' % (item['Name']))
        accessibility.writeOutput(args,output,fields,'TA2A-TA1C-%04d.tsv' % (request),
            os.path.join(os.path.dirname(__file__),'Instances','Instance%d' % (instance),'Runs','run-0'))
