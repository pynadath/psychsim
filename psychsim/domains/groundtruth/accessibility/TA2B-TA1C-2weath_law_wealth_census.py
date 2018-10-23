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
import os.path

if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('instance',type=int,default=24,help='Instance to query')
    parser.add_argument('-r','--run',type=int,default=1,help='Run to query')
    parser.add_argument('-o','--output',default='TA2B-TA1C-2weath_law_wealth_census.tsv',
                        help='Output filename')
    parser.add_argument('--seed',type=int,default=1,help='Random number generator seed')
    args = vars(parser.parse_args())

inFile = os.path.join(root,'Instances','Instance%d' % (args['instance']),
                              'Runs','run-%d' % (args['run']),'RunDataTable.tsv')
