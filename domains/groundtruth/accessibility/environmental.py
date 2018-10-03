from argparse import ArgumentParser
import csv
import os

def readHurricanes(instance,run,hurricane=None):
    inFile = os.path.join(os.path.dirname(__file__),'..','Instances','Instance%d' % (instance),
                          'Runs','run-%d' % (run),'HurricaneTable.tsv')
    sequence = []
    with open(inFile,'r') as csvfile:
        reader = csv.DictReader(csvfile,delimiter='\t')
        for row in reader:
            current = int(row['Name'])
            if len(sequence) < current:
                sequence.append([])
            if hurricane and hurricane != int(row['Name']):
                continue
            sequence[-1].append(row)
    return sequence

if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('instance',type=int,help='Instance to query')
    parser.add_argument('-o','--output',default='RequestEnvironmental.tsv',help='Output filename')
    parser.add_argument('-r','--run',type=int,default=0,help='Run to query')
    parser.add_argument('--hurricane',type=int,default=1,help='Specific hurricane for query')
    parser.add_argument('fields',nargs='+',help='Fields to include in report')
    args = vars(parser.parse_args())
    root = os.path.join(os.path.dirname(__file__),'..')
    sequence = readHurricanes(args['instance'],args['run'],args['hurricane'])
    outFile = os.path.join(root,'Instances','Instance%d' % (args['instance']),
                           'Runs','run-%d' % (args['run']),args['output'])
    fields = ['Timestep','Name']+args['fields']
    with open(outFile,'w') as csvfile:
        writer = csv.DictWriter(csvfile,fields,delimiter='\t',extrasaction='ignore')
        writer.writeheader()
        for hurricane in sequence:
            for row in hurricane:
                writer.writerow(row)
            
    
