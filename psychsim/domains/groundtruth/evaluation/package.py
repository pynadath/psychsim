from argparse import ArgumentParser
from collections import OrderedDict
import csv
from operator import itemgetter
import os
import sys
import zipfile

def directNeighbors(fname):
    data = []
    with open(fname,'r') as csvfile:
        reader = csv.DictReader(csvfile,delimiter='\t')
        fields = None
        for row in reader:
            if fields is None:
                fields = list(row.keys())
            if row['Directed'] == 'no':
                row['Directed'] = 'yes'
                data.append(row)
                row = row.__class__(row)
                tmp = row['ToEntityId']
                row['ToEntityId'] = row['FromEntityId']
                row['FromEntityId'] = tmp
                data.append(row)
            else:
                data.append(row)
    with open(fname,'w') as csvfile:
        writer = csv.DictWriter(csvfile,fields,delimiter='\t')
        writer.writeheader()
        for row in data:
            writer.writerow(row)

def addMissingTime(fname):
    data = []
    with open(fname,'r') as csvfile:
        reader = csv.DictReader(csvfile,delimiter='\t')
        fields = None
        for row in reader:
            if fields is None:
                fields = list(row.keys())
            if row['Timestep'] == '':
                row['Timestep'] = timestep
            else:
                timestep = row['Timestep']
            data.append(row)
    with open(fname,'w') as csvfile:
        writer = csv.DictWriter(csvfile,fields,delimiter='\t')
        writer.writeheader()
        for row in data:
            writer.writerow(row)
            
def fixStats(fname,stats,residents):
    with open(fname,'r') as csvfile:
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
    with open(fname,'r') as csvfile:
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
    with open(fname,'r') as csvfile:
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
    parser.add_argument('-r','--run',type=int,default=0,
                        help='Archive all runs (otherwise, just run-0)')
    parser.add_argument('--ta2',action='store_true',
                        help='Prepare data package for TA2')
    parser.add_argument('--clean',action='store_true')
    parser.add_argument('--clean2',action='store_true')
    args = vars(parser.parse_args())

    if os.path.dirname(__file__):
        os.chdir(os.path.dirname(__file__))
    os.chdir('..')

    if args['ta2']:
        targets = {'CensusTable','PopulationTable','RegionalTable','ActorPreTable','ActorPostTable','HurricaneTable'}
    else:
        targets = {'InstanceVariableTable','RunDataTable','SummaryStatisticsDataTable',
                   'QualitativeDataTable','RelationshipDataTable','QOITable'}
    
    with zipfile.ZipFile(args['output'],'w') as archive:
        if not args['ta2']:
            archive.write(os.path.join('SimulationDefinition','VariableDefTable.tsv'))
            archive.write(os.path.join('SimulationDefinition','RelationshipDefTable.tsv'))
        for i in args['instances']:
            runDir = os.path.join('Instances','Instance%d' % (i),'Runs')
            runs = os.listdir(runDir)
            if args['all']:
                runList = range(len(runs))
            else:
                runList = [args['run']]
            for run in runList:
                if args['clean'] or args['clean2']:
                    print(i,run)
                    stats = []
                    fields = []
                current = os.path.join(runDir,'run-%d' % (run))
                if args['ta2']:
                    os.chdir(current)
                    current = '.'
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
                        elif args['clean2']:
                            if base == 'RelationshipDataTable':
                                directNeighbors(fname)
                            elif base == 'RunDataTable':
                                addMissingTime(fname)
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
