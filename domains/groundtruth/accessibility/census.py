from argparse import ArgumentParser
import csv
import os

from psychsim.domains.groundtruth.region import Region

if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('instance',type=int,help='Instance to query')
    parser.add_argument('-o','--output',default='RequestCensusTable.tsv',help='Output filename')
    parser.add_argument('-r','--run',type=int,default=0,help='Run to query')
    parser.add_argument('--region',type=int,help='Specific region for query')
    parser.add_argument('--day',type=int,help='Days of query')
    parser.add_argument('fields',nargs='+',help='Fields to include in report')
    args = vars(parser.parse_args())

    root = os.path.join(os.path.dirname(__file__),'..')
    inFile = os.path.join(root,'Instances','Instance%d' % (args['instance']),
                          'Runs','run-%d' % (args['run']),'RunDataTable.tsv')
    population = {'__population__': set()}
    if args['region']:
        subset = Region.nameString % (args['region'])
    else:
        subset = 'All'
    with open(inFile,'r') as csvfile:
        reader = csv.DictReader(csvfile,delimiter='\t')
        for row in reader:
            variable = row['VariableName'].split()
            if variable[0] == 'Actor':
                if variable[1] in args['fields']:
                    if not row['EntityIdx'] in population:
                        population[row['EntityIdx']] = {}
                    population[row['EntityIdx']][variable[1]] = row['Value']
                if variable[1] == 'region':
                    if args['region']:
                        if row['Value'] == subset:
                            population['__population__'].add(row['EntityIdx'])
                    else:
                        population['__population__'].add(row['EntityIdx'])
                if args['day'] and row['Timestep'] and int(row['Timestep']) == args['day']:
                    if variable[1] == 'alive' and row['Value'] == 'False':
                        population['__population__'].remove(row['EntityIdx'])
    outFile = os.path.join(root,'Instances','Instance%d' % (args['instance']),
                           'Runs','run-%d' % (args['run']),args['output'])
    fields = ['EntityIdx','Variable','Value']
    with open(outFile,'w') as csvfile:
        writer = csv.DictWriter(csvfile,fields,delimiter='\t',extrasaction='ignore')
        writer.writeheader()
        if 'population' in args['fields']:
            record = {'EntityIdx': subset,
                      'Variable': 'Population',
                      'Value': len(population['__population__'])}
            writer.writerow(record)
        for actor in sorted(population['__population__']):
            for field in args['fields']:
                if field != 'population':
                    record = {'EntityIdx': actor,
                              'Variable': field,
                              'Value': population[actor][field]}
                    writer.writerow(record)
                    
                
