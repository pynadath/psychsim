import csv
import logging
import os.path
import random

from psychsim.probability import Distribution
from psychsim.pwl import *
from psychsim.domains.groundtruth import accessibility
from psychsim.action import *

request = 232
items = [{'Name': 'Friends Outside Region','Values':'0+','DataType': 'Integer','Notes': 'QI.2'},
    {'Name': 'Friends Within Region','Values':'0+','DataType': 'Integer','Notes': 'QI.3'},
    {'Name': 'Hurricane Vulnerability','Values':'[1-5]','DataType': 'Integer','Notes': 'QI.5'},
    {'Name': 'Aid if Wealth Loss','Values':'[0-6]','DataType': 'Integer','Notes': 'QI.6'},
    {'Name': 'Acquaintance Aid Wealth Change','Values':'yes,no','DataType': 'Boolean','Notes': 'QII.1'},
    {'Name': 'Acquaintance Aid Wealth Direction','Values':'increase,decrease,N/A','DataType': 'String','Notes': 'QII.1'},
    {'Name': 'Government Aid Wealth Change','Values':'yes,no','DataType': 'Boolean','Notes': 'QII.2'},
    {'Name': 'Government Aid Wealth Direction','Values':'increase,decrease,N/A','DataType': 'String','Notes': 'QII.2'},
    {'Name': 'Acquaintance Aid Injury Change','Values':'yes,no','DataType': 'Boolean','Notes': 'QII.3'},
    {'Name': 'Acquaintance Aid Injury Direction','Values':'increase,decrease,N/A','DataType': 'String','Notes': 'QII.3'},
    {'Name': 'Government Aid Injury Change','Values':'yes,no','DataType': 'Boolean','Notes': 'QII.4'},
    {'Name': 'Government Aid Injury Direction','Values':'increase,decrease,N/A','DataType': 'String','Notes': 'QII.4'},
    {'Name': 'Acquaintance Aid Dissatisfaction Change','Values':'yes,no','DataType': 'Boolean','Notes': 'QII.5'},
    {'Name': 'Acquaintance Aid Dissatisfaction Direction','Values':'increase,decrease,N/A','DataType': 'String','Notes': 'QII.5'},
    {'Name': 'Government Aid Dissatisfaction Change','Values':'yes,no','DataType': 'Boolean','Notes': 'QII.6'},
    {'Name': 'Government Aid Dissatisfaction Direction','Values':'increase,decrease,N/A','DataType': 'String','Notes': 'QII.6'},
    {'Name': 'Acquaintance Aid Risk Change','Values':'yes,no','DataType': 'Boolean','Notes': 'QII.7'},
    {'Name': 'Acquaintance Aid Risk Direction','Values':'increase,decrease,N/A','DataType': 'String','Notes': 'QII.7'},
    {'Name': 'Government Aid Risk Change','Values':'yes,no','DataType': 'Boolean','Notes': 'QII.8'},
    {'Name': 'Government Aid Risk Direction','Values':'increase,decrease,N/A','DataType': 'String','Notes': 'QII.8'},
    {'Name': 'Hurricane Prediction','Values':'yes,no','DataType': 'Boolean','Notes': 'QII.9'},
    {'Name': 'My Aid Wealth Change','Values':'yes,no','DataType': 'Boolean','Notes': 'QII.10'},
    {'Name': 'My Aid Wealth Direction','Values':'increase,decrease,N/A','DataType': 'String','Notes': 'QII.10'},
    {'Name': 'My Aid Injury Change','Values':'yes,no','DataType': 'Boolean','Notes': 'QII.11'},
    {'Name': 'My Aid Injury Direction','Values':'increase,decrease,N/A','DataType': 'String','Notes': 'QII.11'},
    {'Name': 'My Aid Risk Change','Values':'yes,no','DataType': 'Boolean','Notes': 'QII.12'},
    {'Name': 'My Aid Risk Direction','Values':'increase,decrease,N/A','DataType': 'String','Notes': 'QII.12'},
    {'Name': 'Aid to Acquaintances','Values':'yes,no','DataType': 'Boolean','Notes': 'QII.13'},
    {'Name': 'Aid to Friends','Values':'yes,no','DataType': 'Boolean','Notes': 'QII.14'},
    {'Name': 'Aid to Strangers','Values':'yes,no','DataType': 'Boolean','Notes': 'QII.15'},
    {'Name': 'Information Amount','Values':'friends,acquaintances,government,social media,strangers,other','DataType': 'String','Notes': 'QIII.1'},
    {'Name': 'Information Trust','Values':'friends,acquaintances,government,social media,strangers,other','DataType': 'String','Notes': 'QIII.2'},
    {'Name': 'Aid to Ethnicity','Values':'[0-6]','DataType': 'Integer','Notes': 'QIV.1'},
    {'Name': 'Aid to Religion','Values':'[0-6]','DataType': 'Integer','Notes': 'QIV.2'},
    {'Name': 'Aid to Gender','Values':'[0-6]','DataType': 'Integer','Notes': 'QIV.3'},
    {'Name': 'Aid to Age','Values':'[0-6]','DataType': 'Integer','Notes': 'QIV.4'},
    {'Name': 'Aid to Employed','Values':'[0-6]','DataType': 'Integer','Notes': 'QIV.5'},
    {'Name': 'Aid to Unemployed','Values':'[0-6]','DataType': 'Integer','Notes': 'QIV.6'},
    {'Name': 'Aid to Pets','Values':'[0-6]','DataType': 'Integer','Notes': 'QIV.7'},
    {'Name': 'Aid to No Pets','Values':'[0-6]','DataType': 'Integer','Notes': 'QIV.8'},
    {'Name': 'Aid to Young','Values':'[0-6]','DataType': 'Integer','Notes': 'QIV.9'},
    {'Name': 'Aid to Old','Values':'[0-6]','DataType': 'Integer','Notes': 'QIV.10'},
    {'Name': 'Aid to Ethnic Minority','Values':'[0-6]','DataType': 'Integer','Notes': 'QIV.11'},
    {'Name': 'Aid to Ethnic Majority','Values':'[0-6]','DataType': 'Integer','Notes': 'QIV.12'},
    {'Name': 'Aid to No Religion','Values':'[0-6]','DataType': 'Integer','Notes': 'QIV.13'},
    {'Name': 'Aid to Religious Majority','Values':'[0-6]','DataType': 'Integer','Notes': 'QIV.14'},
    {'Name': 'Aid to Religious Minority','Values':'[0-6]','DataType': 'Integer','Notes': 'QIV.15'},
    ]
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO,filename=os.path.join(os.path.dirname(__file__),'TA2A-TA1C-%04d.log' % (request)))
    random.seed(request)
    accessibility.writeVarDef(os.path.dirname(__file__),items)
    fields = ['Timestep','Participant']+sorted(accessibility.demographics.keys())+[item['Name'] for item in items]
    for instance in [1,9,10,11,12,13,14]:
        logging.info('Instance %d' % (instance))
        args = accessibility.instances[instance-1]
        world = accessibility.loadPickle(args['instance'],args['run'],args['span']+(1 if instance == 2 or instance > 8 else 0),
            sub='Input' if instance > 2 else None)
        data = accessibility.loadRunData(args['instance'],args['run'],args['span'],subs=['Input'] if instance > 2 else [None])
        hurricanes = [h for h in accessibility.readHurricanes(args['instance'],args['run'],'Input' if instance > 2 else None) if h['End'] <= args['span']]
        network = accessibility.readNetwork(args['instance'],args['run'],'Input' if instance > 2 else None)
        demos = accessibility.readDemographics(data,last=args['span'])
        govtAid = accessibility.aidTargets(data)
        prosocial = accessibility.prosocial(data)
        population = accessibility.getPopulation(data)
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
                elif item['Name'] == 'Acquaintance Aid Wealth Change' or item['Name'] == 'Government Aid Wealth Change' or \
                    item['Name'] == 'Acquaintance Aid Dissatisfaction Change' or item['Name'] == 'My Aid Wealth Change':
                    record[item['Name']] = 'no'
                elif item['Name'] == 'Acquaintance Aid Wealth Direction' or item['Name'] == 'Government Aid Wealth Direction' or \
                    item['Name'] == 'Acquaintance Aid Dissatisfaction Direction' or item['Name'] == 'My Aid Wealth Direction':
                    record[item['Name']] = 'N/A'
                elif item['Name'] == 'Acquaintance Aid Injury Change':
                    for t,helpers in prosocial[record['Residence']].items():
                        if risks[t+1] < risks[t] and data[name][stateKey(name,'location')][t+1] == record['Residence'] and \
                            data[name][actionKey(name)][t]['verb'] != 'decreaseRisk':
                            # If I believe my personal risk went down, and I was at home, and I didn't do any prosocial behavior myself...
                            record[item['Name']] = 'yes'
                            break
                    else:
                        record[item['Name']] = 'no'
                elif item['Name'] == 'Acquaintance Aid Injury Direction':
                    if record['Acquaintance Aid Injury Change'] == 'yes':
                        record[item['Name']] = 'decrease'
                    else:
                        record[item['Name']] = 'N/A'
                elif item['Name'] == 'Government Aid Injury Change':
                    for t in range(len(govtAid)):
                        if govtAid[t] == record['Residence'] and risks[t+2] < risks[t+1] and \
                            data[name][stateKey(name,'location')][t+2] == record['Residence'] and \
                            data[name][actionKey(name)][t+1]['verb'] != 'decreaseRisk':
                            # If I believe my personal risk went down, and I was at home, and I didn't do any prosocial behavior myself...
                            record[item['Name']] = 'yes'
                            break
                    else:
                        record[item['Name']] = 'no'
                elif item['Name'] == 'Government Aid Injury Direction':
                    if record['Government Aid Injury Change'] == 'yes':
                        record[item['Name']] = 'decrease'
                    else:
                        record[item['Name']] = 'N/A'
                elif item['Name'] == 'Government Aid Dissatisfaction Change':
                    record['Government Aid Dissatisfaction Direction'] = 'N/A'
                    record[item['Name']] = 'no'
                    for t in range(len(govtAid)):
                        if govtAid[t] == record['Residence']:
                            if record['Government Aid Dissatisfaction Direction'] == 'N/A':
                                record[item['Name']] = 'yes'
                                record['Government Aid Dissatisfaction Direction'] = 'decrease'
                            elif record['Government Aid Dissatisfaction Direction'] == 'increase':
                                record['Government Aid Dissatisfaction Direction'] = 'both'
                                break
                        elif record['Government Aid Dissatisfaction Direction'] == 'N/A':
                            record[item['Name']] = 'yes'
                            record['Government Aid Dissatisfaction Direction'] = 'increase'
                        elif record['Government Aid Dissatisfaction Direction'] == 'decrease':
                            record['Government Aid Dissatisfaction Direction'] = 'both'
                            break
                elif item['Name'] == 'Government Aid Dissatisfaction Direction':
                    pass
                elif item['Name'] == 'Acquaintance Aid Risk Change':
                    record[item['Name']] = record['Acquaintance Aid Injury Change']
                elif item['Name'] == 'Acquaintance Aid Risk Direction':
                    record[item['Name']] = record['Acquaintance Aid Injury Direction']
                elif item['Name'] == 'Government Aid Risk Change':
                    record[item['Name']] = record['Government Aid Injury Change']
                elif item['Name'] == 'Government Aid Risk Direction':
                    record[item['Name']] = record['Government Aid Injury Direction']
                elif item['Name'] == 'Hurricane Prediction':
                    record[item['Name']] = 'no'
                elif item['Name'] == 'My Aid Injury Change':
                    record['My Aid Injury Direction'] = 'N/A'
                    for t,helpers in prosocial[record['Residence']].items():
                        if name in helpers:
                            record['Aid to Acquaintances'] = 'yes'
                            if risks[t+1] > risks[t]:
                                if record['My Aid Injury Direction'] == 'N/A':
                                    record[item['Name']] = 'yes'
                                    record['My Aid Injury Direction'] = 'increase'
                                elif record['My Aid Injury Direction'] == 'decrease':
                                    record['My Aid Injury Direction'] = 'both'
                                    break
                            elif risks[t+1] < risks[t]:
                                if record['My Aid Injury Direction'] == 'N/A':
                                    record[item['Name']] = 'yes'
                                    record['My Aid Injury Direction'] = 'decrease'
                                elif record['My Aid Injury Direction'] == 'increase':
                                    record['My Aid Injury Direction'] = 'both'
                                    break
                    else:
                        record[item['Name']] = 'no'
                elif item['Name'] == 'My Aid Injury Direction':
                    pass
                elif item['Name'] == 'My Aid Risk Change':
                    record[item['Name']] = record['My Aid Injury Change']
                elif item['Name'] == 'My Aid Risk Direction':
                    record[item['Name']] = record['My Aid Injury Direction']
                elif item['Name'] == 'Aid to Acquaintances':
                    if item['Name'] not in record:
                        record[item['Name']] = 'no'
                elif item['Name'] == 'Aid to Friends':
                    if record['Aid to Acquaintances'] == 'yes':
                        for friend in friends:
                            if demos[friend]['Residence'] == record['Residence']:
                                record[item['Name']] = 'yes'
                                break
                        else:
                            record[item['Name']] = 'no'
                    else:
                        record[item['Name']] = 'no'
                elif item['Name'] == 'Aid to Strangers':
                    record[item['Name']] = 'no'
                elif item['Name'] == 'Information Amount':
                    record[item['Name']] = 'social media,friends'
                elif item['Name'] == 'Information Trust':
                    record[item['Name']] = 'social media,friends'
                elif item['Name'][:6] == 'Aid to':
                    if agent.Rweights['neighbors'] < .01:
                        record[item['Name']] = 3
                    else:
                        if item['Name'][7:] == 'Ethnicity':
                            inGroup = {other for other in population if demos[other]['Ethnicity'] == record['Ethnicity']}
                            outGroup = {other for other in population if demos[other]['Ethnicity'] != record['Ethnicity']}
                        elif item['Name'][7:] == 'Religion':
                            inGroup = {other for other in population if demos[other]['Religion'] == record['Religion']}
                            outGroup = {other for other in population if demos[other]['Religion'] != record['Religion']}
                        elif item['Name'][7:] == 'Gender':
                            inGroup = {other for other in population if demos[other]['Gender'] == record['Gender']}
                            outGroup = {other for other in population if demos[other]['Gender'] != record['Gender']}
                        elif item['Name'][7:] == 'Age':
                            inGroup = {other for other in population if abs(demos[other]['Age']-record['Age'])<=5}
                            outGroup = {other for other in population if abs(demos[other]['Age']-record['Age'])>5}
                        elif item['Name'][7:] == 'Employed':
                            inGroup = {other for other in population if demos[other]['Fulltime Job'] == 'yes'}
                            outGroup = {other for other in population if demos[other]['Fulltime Job'] != 'yes'}
                        elif item['Name'][7:] == 'Unemployed':
                            inGroup = {other for other in population if demos[other]['Fulltime Job'] == 'no'}
                            outGroup = {other for other in population if demos[other]['Fulltime Job'] != 'no'}
                        elif item['Name'][7:] == 'Pets':
                            inGroup = {other for other in population if demos[other]['Pets'] == 'yes'}
                            outGroup = {other for other in population if demos[other]['Pets'] != 'yes'}
                        elif item['Name'][7:] == 'No Pets':
                            inGroup = {other for other in population if demos[other]['Pets'] == 'no'}
                            outGroup = {other for other in population if demos[other]['Pets'] != 'no'}
                        elif item['Name'][7:] == 'Young':
                            inGroup = {other for other in population if demos[other]['Age'] < 30}
                            outGroup = {other for other in population if demos[other]['Age'] >= 30}
                        elif item['Name'][7:] == 'Old':
                            inGroup = {other for other in population if demos[other]['Age'] >= 30}
                            outGroup = {other for other in population if demos[other]['Age'] < 30}
                        elif item['Name'][7:] == 'Ethnic Minority':
                            inGroup = {other for other in population if demos[other]['Ethnicity'] == 'minority'}
                            outGroup = {other for other in population if demos[other]['Ethnicity'] != 'minority'}
                        elif item['Name'][7:] == 'Ethnic Majority':
                            inGroup = {other for other in population if demos[other]['Ethnicity'] == 'majority'}
                            outGroup = {other for other in population if demos[other]['Ethnicity'] != 'majority'}
                        elif item['Name'][7:] == 'No Religion':
                            inGroup = {other for other in population if demos[other]['Religion'] == 'none'}
                            outGroup = {other for other in population if demos[other]['Religion'] != 'none'}
                        elif item['Name'][7:] == 'Religious Minority':
                            inGroup = {other for other in population if demos[other]['Religion'] == 'minority'}
                            outGroup = {other for other in population if demos[other]['Religion'] != 'minority'}
                        elif item['Name'][7:] == 'Religious Majority':
                            inGroup = {other for other in population if demos[other]['Religion'] == 'majority'}
                            outGroup = {other for other in population if demos[other]['Religion'] != 'majority'}
                        else:
                            raise ValueError('Unknown item: %s' % (item['Name']))
                        assert len(inGroup) > 0
                        assert len(outGroup) > 0
                        globalRatio = len(inGroup)/len(outGroup|inGroup)
                        localRatio = len(inGroup & neighbors)/len((outGroup|inGroup) & neighbors)
                        if localRatio < globalRatio:
                            # Less likely
                            record[item['Name']] = accessibility.toLikert(0.5*localRatio/globalRatio,7)-1
                        else:
                            # More likely
                            record[item['Name']] = accessibility.toLikert(0.5+0.5*globalRatio/localRatio,7)-1
                else:
                    raise ValueError('Unknown item: %s' % (item['Name']))
        accessibility.writeOutput(args,output,fields,'TA2A-TA1C-%04d.tsv' % (request),
            os.path.join(os.path.dirname(__file__),'Instances','Instance%d' % (instance),'Runs','run-0'))
