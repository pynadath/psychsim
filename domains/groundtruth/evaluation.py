from argparse import ArgumentParser
import csv
import logging
import os

QOI = {'Actor alive(count=False)': 'Deaths',
       'Actor health(count<0.2)': 'Casualties',
       'Actor location(count=evacuated)': 'Evacuees',
       'Actor location(count=shelter)': 'Sheltered',
       'Region shelterOccupancy(sum)': 'Sheltered',
       'Actor health(mean)': 'Wellbeing',
       'Actor resources(mean)': 'Wealth',
       'Region risk(invert,mean)': 'Safety',
       'Actor action(count=decreaseRisk)': 'Prosocial',
       'Actor action(count=takeResources)': 'Antisocial',
       }
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    parser = ArgumentParser()
    parser.add_argument('instances',type=int,default=100000,nargs='+',
                        help='Base instance for evaluationLevel of logging detail')
    args = vars(parser.parse_args())

    instances = sum([[base+i+1 for i in range(10)] for base in args['instances']],[])

    qoiData = []
    for instance in instances:
        logging.info('Processing instance %d' % (instance))
        dirName = os.path.join(os.path.dirname(__file__),'Instances','Instance%d' % (instance),
                               'Runs','run-0')
        with open(os.path.join(dirName,'SummaryStatisticsDataTable'),'r') as infile:
            reader = csv.DictReader(infile,delimiter='\t')
            for row in reader:
                label = '%s(%s)' % (row['VariableName'],row['Metadata'])
                entry = {'Instance': instance,
                         'Timestep': int(row['Timestep']),
                         'QOI': QOI[label]}
                if '.' in row['Value']:
                    entry['Value'] = float(row['Value'])
                else:
                    entry['Value'] = int(row['Value'])
                qoiData.append(entry)
    with open(os.path.join(os.path.dirname(__file__),'Evaluation','QOITable'),'w') as outfile:
        fields = ['Instance','Timestep','QOI','Value']
        writer = csv.DictWriter(outfile,fields,delimiter='\t',extrasaction='ignore')
        writer.writeheader()
        for row in qoiData:
            writer.writerow(row)
            
