"""
Research method category: Observational Data (Environment, Agencies, and Census)
Specific questions (broken into categories):

Weather Questions (both the content and timing of release, note regional variation): 
For the past 6 hurricanes, are weather prediction data available? E.g. for hurricane X, the location where X was predicted to hit?
For the past 6 hurricanes, how much media coverage there was, and did the media coverage include the predicted weather data?
Actual tracks and severity for each hurricane.
Official announcements, including voluntary and mandatory evacuation orders, storm survival guidelines, sheltering recommendations.
Geographic layout of the regions and regional characteristics (coastal, inland, elevation)

Law Enforcement / Government Questions:
For the last 6 hurricanes, broken down by hurricane, how much property damage was due to looting ($) or, alternatively, how many looting incidents were reported (raw number)? Is it possible to break the $ or number by ethnicity of alleged looter? Ethnicity of reporter?

Additional Census Questions:
Can we get a census table at the end of the hurricane season? If possible, also in the middle, but that’s likely unrealistic
Census of voting patterns? What are the political parties? Can we get number of voters by region by party?
Wealth by region
What does wealth measure when recroded in the census, and when recorded in the surveys conducted pre and post hurricanes (clarification question)?

Sampling Strategy: Access relevant data from the appropriate agencies (weather, law, census beaureau)
Other applicable detail:
Research request identifier: TA2B-TA1C-2weath_law_wealth_census
Research request priority: 2
"""
from argparse import ArgumentParser
import csv
import logging
import os.path
import pickle
import random
from simulation.create import loadPickle
from simulation.execute import writeCensus

if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('-i','--instance',type=int,default=24,help='Instance to query')
    parser.add_argument('-r','--run',type=int,default=1,help='Run to query')
    parser.add_argument('--seed',type=int,default=1,help='Random number generator seed')
    parser.add_argument('-d','--debug',default='WARNING',help='Level of logging detail')
    args = vars(parser.parse_args())
    # Extract logging level from command-line argument
    level = getattr(logging, args['debug'].upper(), None)
    if not isinstance(level, int):
        raise ValueError('Invalid debug level: %s' % args['debug'])
    logfile = '%s.log' % (os.path.splitext(__file__)[0])
    logging.basicConfig(level=level,filename=logfile)
    random.seed(args['seed'])
    root = os.path.join(os.path.dirname(__file__))
    # Weather questions
    inFile = os.path.join(root,'Instances','Instance%d' % (args['instance']),
                          'Runs','run-%d' % (args['run']),'HurricaneTable.tsv')
    with open(inFile,'r') as csvfile:
        reader = csv.DictReader(csvfile,delimiter='\t')
        hurricanes = []
        for row in reader:
            hurricane = int(row['Name'])
            if hurricane > 6:
                break
            if len(hurricanes) < hurricane:
                hurricanes.append({'Hurricane': hurricane,
                                   'Predicted Location': row['Location'],
                                   'Media Coverage': 'yes',
                                   'Actual Track': [],
                                   'Official Announcements': 'none',
                                   'Start': int(row['Timestep']),
                                   })
            elif row['Landed'] == 'yes':
                if row['Location'] == 'leaving':
                    hurricanes[-1]['End'] = int(row['Timestep'])
                else:
                    if not 'Actual Severity' in hurricanes[-1]:
                        hurricanes[-1]['Actual Severity'] = row['Category']
                    if len(hurricanes[-1]['Actual Track']) == 0 or \
                       hurricanes[-1]['Actual Track'][-1] != row['Location']:
                        hurricanes[-1]['Actual Track'].append(row['Location'])
    for record in hurricanes:
        record['Actual Track'] = ','.join(record['Actual Track'])
    with open(os.path.join(os.path.dirname(__file__),'TA2B-TA1C-2weath.tsv'),'w') as csvfile:
        fields = ['Hurricane','Predicted Location','Media Coverage','Actual Track',
                  'Actual Severity','Official Announcements']
        writer = csv.DictWriter(csvfile,fields,delimiter='\t',extrasaction='ignore')
        writer.writeheader()
        for record in hurricanes:
            writer.writerow(record)
    # Geographic question
    world = loadPickle(args['instance'],0)
    with open(os.path.join(os.path.dirname(__file__),'TA2B-TA1C-2geo.tsv'),'w') as csvfile:
        fields = ['Region','North','South','East','West']
        writer = csv.DictWriter(csvfile,fields,delimiter='\t',extrasaction='ignore')
        writer.writeheader()
        for region in sorted(world.agents):
            if region[:6] == 'Region':
                record = {'Region': region}
                if world.agents[region].west == 'none':
                    record['West'] = 'Water'
                else:
                    record['West'] = world.agents[region].west
                if world.agents[region].east == 'none':
                    record['East'] = 'Land'
                else:
                    record['East'] = world.agents[region].east
                if world.agents[region].north == 'none':
                    record['North'] = 'Land'
                else:
                    record['North'] = world.agents[region].north
                if world.agents[region].south == 'none':
                    record['South'] = 'Land'
                else:
                    record['South'] = world.agents[region].south
                writer.writerow(record)
    # Law & Census questions
    inFile = os.path.join(root,'Instances','Instance%d' % (args['instance']),
                          'Runs','run-%d' % (args['run']),'RunDataTable.tsv')
    wealth = {}
    ethnicity = {}
    looters = [{} for hurricane in hurricanes]
    incidents = [0 for hurricane in hurricanes]
    with open(inFile,'r') as csvfile:
        reader = csv.DictReader(csvfile,delimiter='\t')
        for row in reader:
            if row['VariableName'] == 'Actor action':
                action = row['Value'].split('-')
                if action[1] == 'takeResources':
                    for index in range(len(hurricanes)):
                        if hurricanes[index]['Start'] < int(row['Timestep']) < hurricanes[index]['End']:
                            break
                    else:
                        continue
                    looters[index][row['EntityIdx']] = looters[index].get(row['EntityIdx'],0) + 1
                    incidents[index] += 1
            elif row['Timestep'] == '1' and row['VariableName'] == 'Actor ethnicGroup':
                ethnicity[row['EntityIdx']] = row['Value']
            elif row['VariableName'][:6] == 'Actor ':
                feature = row['VariableName'].split()[1]
                if feature == 'resources' and row['Timestep'] == '1':
                    wealth[row['EntityIdx']] = row['Value']
                if '.' in row['Value']:
                    value = float(row['Value'])
                elif row['Value'] == 'True':
                    value = True
                elif row['Value'] == 'False':
                    value = False
                else:
                    value = row['Value']
                world.setState(row['EntityIdx'],feature,value)
    # Law enforcement question
    with open(os.path.join(os.path.dirname(__file__),'TA2B-TA1C-2law.tsv'),'w') as csvfile:
        fields = ['Hurricane','Looting Incidents','Ethnic Majority Looters','Ethnic Minority Looters']
        writer = csv.DictWriter(csvfile,fields,delimiter='\t',extrasaction='ignore')
        writer.writeheader()
        for index in range(len(hurricanes)):
            record = {'Hurricane': index+1, 'Looting Incidents': incidents[index],
                      'Ethnic Minority Looters': 0,'Ethnic Majority Looters': 0}
            for actor in looters[index]:
                if looters[index][actor] > 2:
                    record['Ethnic %s Looters' % (ethnicity[actor].capitalize())] += 1
            writer.writerow(record)
    # Census question
    regions = {name: {'agent': world.agents[name],
                      'inhabitants': [world.agents[a] for a in ethnicity
                                      if world.agents[a].home == name and
                                      world.getState(a,'alive').first()]}
               for name in world.agents if name[:6] == 'Region'}
    for table in regions.values():
        for actor in table['inhabitants']:
            print(actor.name,wealth[actor.name],actor.getState('resources'))
    writeCensus(world,regions,os.path.dirname(__file__),'TA2B-TA1C-2census')
