from argparse import ArgumentParser
import csv
import os
import statistics

from psychsim.pwl.keys import stateKey

if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('instances',help='Instance to query')
    parser.add_argument('-r','--run',default=0,help='Run to query')
    parser.add_argument('--region',default=None,help='Region to single out')
    parser.add_argument('fields',nargs='+',help='Fields to include in report')
    args = vars(parser.parse_args())

    instances = args['instances'].split(',')
    instances = [instance.split('-') for instance in instances]
    instances = sum([list(range(int(instance[0]),int(instance[1])+1))
                     if len(instance) == 2 else [int(instance[0])]
                     for instance in instances],[])
    valid = {}
    root = os.path.join(os.path.dirname(__file__),'..')
    values = {instance: {} for instance in instances}
    for instance in instances:
        # Read in all potential QOIs
        if args['run'] == 'all':
            runs = os.listdir(os.path.join(root,'Instances','Instance%d' % (instance),'Runs'))
        else:
            runs = ['run-%s' % (args['run'])]
        for runFile in runs:
            values[instance][runFile] = {}
            label = '%s%s' % (instance,runFile)
            inFile = os.path.join(root,'Instances','Instance%d' % (instance),
                                  'Runs',runFile,'SummaryStatisticsDataTable.tsv')
            with open(inFile,'r') as csvfile:
                reader = csv.DictReader(csvfile,delimiter='\t')
                for row in reader:
                    if row['VariableName'][:8] == 'Regional' or 'all' in args['fields']:
                        if args['region'] is None or args['region'] == row['EntityIdx']:
                            if row['VariableName'][:8] == 'Regional':
                                feature = row['VariableName'][9:]
                            else:
                                feature = row['VariableName']
                            if 'all' in args['fields'] or feature in args['fields']:
                                if row['EntityIdx'][0] == '[':
                                    field = 'All %s' % (feature)
                                else:
                                    field = stateKey(row['EntityIdx'],feature)
                                if field not in values[instance][runFile]:
                                    values[instance][runFile][field] = []
                                if '.' in row['Value']:
                                    values[instance][runFile][field].append(float(row['Value']))
                                else:
                                    values[instance][runFile][field].append(int(row['Value']))
                                if instance == instances[0]:
                                    valid[field] = row
                # Analyze QOI time series. Filter out those with nonzero variance.
                for field in list(valid.keys()):
                    if statistics.pvariance(values[instance][runFile][field]) < 1e-8:
                        print(field,instance,runFile)
                        if field[:3] == 'All':
                            del valid[field]
                        else:
                            for other in [f for f in valid if f[:6] == 'Region' and f[8:] == field[8:]]:
                                del valid[other]
    for instance in instances:
        # Write QOI subset
        for runFile,table in values[instance].items():
            timespan = len(table[next(iter(valid))])
            with open(os.path.join(root,'Instances','Instance%d' % (instance),
                                   'Runs',runFile,'QOITable.tsv'),'w') as csvfile:
                fields = ['Timestep','VariableName','EntityIdx','Value','Metadata']
                writer = csv.DictWriter(csvfile,fields,delimiter='\t',extrasaction='ignore')
                writer.writeheader()
                for t in range(timespan):
                    for field,entry in valid.items():
                        assert len(table[field]) == timespan,\
                            'Instance %d has %d values for %s instead of %d' % \
                            (instance,len(table[field]),field,timespan)
                        record = dict(entry)
                        record['Timestep'] = t+1
                        record['Value'] = table[field][t]
                        writer.writerow(record)
