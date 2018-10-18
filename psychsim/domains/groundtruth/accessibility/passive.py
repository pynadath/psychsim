from argparse import ArgumentParser
import csv
import os

from psychsim.domains.groundtruth.region import Region

if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('instance',type=int,help='Instance to query')
    parser.add_argument('-o','--output',default='RequestPassive.tsv',help='Output filename')
    parser.add_argument('-r','--run',type=int,default=0,help='Run to query')
    parser.add_argument('--day',type=int,help='Days of query')
    parser.add_argument('fields',nargs='+',help='Fields to include in report')
    args = vars(parser.parse_args())

    root = os.path.join(os.path.dirname(__file__),'..')
    inFile = os.path.join(root,'Instances','Instance%d' % (args['instance']),
                          'Runs','run-%d' % (args['run']),'RunDataTable.tsv')
    population = {}
    regions = {}
    with open(inFile,'r') as csvfile:
        reader = csv.DictReader(csvfile,delimiter='\t')
        for row in reader:
            if row['Timestep'] and int(row['Timestep']) > args['day']:
                break
            if row['EntityIdx'][:5] == 'Actor' and row['EntityIdx'] not in population:
                population[row['EntityIdx']] = {'Casualties': False,'Deaths': False}
            if row['VariableName'] == 'Actor health':
                if float(row['Value']) < 0.2:
                    population[row['EntityIdx']]['Casualties'] = True
            elif row['VariableName'] == 'Actor alive':
                if row['Value'] == 'False':
                    population[row['EntityIdx']]['Deaths'] = True
            elif row['VariableName'] == 'Actor region':
                try:
                    regions[row['Value']].add(row['EntityIdx'])
                except KeyError:
                    regions[row['Value']] = {row['EntityIdx']}
    outFile = os.path.join(root,'Instances','Instance%d' % (args['instance']),
                           'Runs','run-%d' % (args['run']),args['output'])
    fields = ['Timestep','Region']+args['fields']
    with open(outFile,'w') as csvfile:
        writer = csv.DictWriter(csvfile,fields,delimiter='\t',extrasaction='ignore')
        writer.writeheader()
        for region in sorted(regions):
            record = {field: 0 for field in args['fields']}
            record['Timestep'] = args['day']
            record['Region'] = region
            for actor in regions[region]:
                for field in args['fields']:
                    if population[actor][field]:
                        record[field] += 1
            writer.writerow(record)
                    
                
