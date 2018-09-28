from argparse import ArgumentParser
from collections import OrderedDict
import csv
from operator import itemgetter
import os
import sys
import zipfile

def fixStats(fname,stats,residents):
    with open(fname) as csvfile:
        reader = csv.DictReader(csvfile,delimiter='\t')
        fields = None
        for row in reader:
            if fields is None:
                fields = list(row.keys())
            tmp = row['VariableName']
            row['VariableName'] = row['Metadata']
            row['Metadata'] = tmp
            if row['VariableName'] == 'Regional Wellbeing':
                region = None
                for actor in row['EntityIdx'][1:-1].split(','):
                    if region is None:
                        region = residents[actor]
                    else:
                        assert residents[actor] == region
                row['EntityIdx'] = region
            stats.append(row)
    return fields

def mergeRegions(fname,stats):
    with open(fname) as csvfile:
        reader = csv.DictReader(csvfile,delimiter='\t')
        for row in reader:
            for field in ['Deaths','Casualties','Sheltered']:
                record = OrderedDict([('Timestep', row['Timestep']),
                                      ('VariableName', 'Regional %s' % (field)),
                                      ('EntityIdx', row['Region']),
                                      ('Value', row[field])])
                stats.append(record)
                
def mergeData(fname,stats):
    residents = {}
    with open(fname) as csvfile:
        reader = csv.DictReader(csvfile,delimiter='\t')
        for row in reader:
            if row['VariableName'] == 'Region risk':
                record = OrderedDict([('Timestep', row['Timestep']),
                                      ('VariableName', 'Regional Safety'),
                                      ('EntityIdx', row['EntityIdx']),
                                      ('Value', '%f' % (1.-float(row['Value']))),
                                      ('Metadata', 'Region risk')])
                stats.append(record)
            elif row['VariableName'] == 'Actor region':
                residents[row['EntityIdx']] = row['Value']
    return residents
            
if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('output',help='Output file')
    parser.add_argument('instances',type=int,nargs='+',help='Instance numbers to archived')
    parser.add_argument('-a','--all',action='store_true',
                        help='Archive all runs (otherwise, just run-0)')
    parser.add_argument('--clean',action='store_true')
    args = vars(parser.parse_args())

    os.chdir('/home/david/psychsim/domains/groundtruth')
            
    targets = {'InstanceVariableTable','RunDataTable','SummaryStatisticsDataTable',
               'QualitativeDataTable','RelationshipDataTable',}
    
    with zipfile.ZipFile(args['output'],'w') as archive:
        archive.write(os.path.join('SimulationDefinition','VariableDefTable.tsv'))
        archive.write(os.path.join('SimulationDefinition','RelationshipDefTable.tsv'))
        for i in args['instances']:
            runDir = os.path.join('Instances','Instance%d' % (i),'Runs')
            runs = os.listdir(runDir)
            if args['all']:
                maxRun = len(runs)
            else:
                maxRun = 1
            for run in range(maxRun):
                if args['clean']:
                    print(i,run)
                    stats = []
                    fields = []
                current = os.path.join(runDir,'run-%d' % (run))
                for name in os.listdir(current):
                    base,ext = os.path.splitext(name)
                    if base in targets and ext == '.tsv':
                        fname = os.path.join(current,name)
                        if args['clean']:
                            if base == 'SummaryStatisticsDataTable':
                                fields = fixStats(fname,stats,residents)
                                os.rename(fname,os.path.join(current,'%s.bak' % (base)))
                            elif base == 'RunDataTable':
                                residents = mergeData(fname,stats)
                        else:
                            archive.write(fname)
                if args['clean']:
                    mergeRegions(os.path.join(current,'RegionalTable.tsv'),stats)
                    stats.sort(key=lambda r: int(r['Timestep']))
                    with open(os.path.join(current,'SummaryStatisticsDataTable.tsv'),'w') as csvfile:
                        writer = csv.DictWriter(csvfile,fields,delimiter='\t')
                        writer.writeheader()
                        for row in stats:
                            writer.writerow(row)
