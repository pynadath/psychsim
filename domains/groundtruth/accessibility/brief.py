from argparse import ArgumentParser
import csv
import os
import pickle

from psychsim.action import Action

if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('instance',type=int,help='Instance to query')
    parser.add_argument('-o','--output',default='RequestBrief.tsv',help='Output filename')
    parser.add_argument('-r','--run',type=int,default=0,help='Run to query')
    args = vars(parser.parse_args())
    root = os.path.join(os.path.dirname(__file__),'..')
    inFile = os.path.join(root,'Instances','Instance%d' % (args['instance']),
                          'Runs','run-%d' % (args['run']),'scenario.pkl')
    with open(inFile,'rb') as f:
        world = pickle.load(f)
    
    inFile = os.path.join(root,'Instances','Instance%d' % (args['instance']),
                          'Runs','run-%d' % (args['run']),'RunDataTable.tsv')
    actions = set()
    with open(inFile,'r') as csvfile:
        reader = csv.DictReader(csvfile,delimiter='\t')
        for row in reader:
            if row['VariableName'] == 'Actor action':
                fields = row['Value'].split('-')
                actor = world.agents[row['EntityIdx']]
                for action in actor.actions:
                    if action['verb'] == fields[1]:
                        break
                else:
                    raise NameError('Unknown action: %s' % (row['Value']))
                assert len(action) == 1
                desc = next(iter(action)).description
                actions.add(desc)
    outFile = os.path.join(root,'Instances','Instance%d' % (args['instance']),
                           'Runs','run-%d' % (args['run']),args['output'])
    fields = ['Action']
    with open(outFile,'w') as csvfile:
        writer = csv.DictWriter(csvfile,fields,delimiter='\t',extrasaction='ignore')
        writer.writeheader()
        for action in sorted(actions):
            writer.writerow({'Action': action})
