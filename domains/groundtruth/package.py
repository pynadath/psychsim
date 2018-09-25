from argparse import ArgumentParser
import os
import sys
import zipfile

if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('output',help='Output file')
    parser.add_argument('instances',type=int,nargs='+',help='Instance numbers to archived')
    parser.add_argument('-a','--all',action='store_true',
                        help='Archive all runs (otherwise, just run-0)')
    args = vars(parser.parse_args())

    os.chdir('/home/david/psychsim/domains/groundtruth')
    targets = {'InstanceVariableTable','RunDataTable','SummaryStatisticsDataTable',
               'QualitativeDataTable','RelationshipDataTable',}
    
    with zipfile.ZipFile(args['output'],'w') as archive:
        archive.write(os.path.join('SimulationDefinition','VariableDefTable'))
        archive.write(os.path.join('SimulationDefinition','RelationshipDefTable'))
        for i in args['instances']:
            runDir = os.path.join('Instances','Instance%d' % (i),'Runs')
            runs = os.listdir(runDir)
            if args['all']:
                maxRun = len(runs)
            else:
                maxRun = 1
            for run in range(maxRun):
                current = os.path.join(runDir,'run-%d' % (run))
                for name in os.listdir(current):
                    base,ext = os.path.splitext(name)
                    if base in targets and ext == '.tsv':
                        archive.write(os.path.join(current,name))
