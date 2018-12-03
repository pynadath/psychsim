"""
TA2A-TA1C-0022-RR.txt

Research method category:
Brief from expert observer
 
Specific question:
We ask the regional government officers about their resources, and registered information about the world. Questions should be asked to the officer over all 16 regions, or officers for each region, as applicable, possible.

1. How many people can shelters in your region accommodate at the same time? (If the number changes, such as if at some time you build another shelter, please provide an accommodation ability report at each time step.)

2. Do you keep a record of what kind of jobs people have in your region, and the number of people occupied in each job? Particularly, we want to know how many firemen, nurses, doctors, policemen and soldiers you have present in your region.

3. What will you do if the hurricane comes? Describe:
 a.The measurements you take to:
i. anticipate each hurricane
ii. identify when a hurricane has arrived 
     b.The policy in your region for each hurricane, specifically:
        i. Who do you evacuate first? What is the basis for you to determine the priority of evacuation.
        ii.Do you have compensation for those who are evacuated, injured, or sheltered? If so, describe how to compensate and how much compensation is provided (as if you give higher compensation for sheltered people than injured people, etc.)

4. What is the maximum speed for evacuation in your region? Or how many people can you evacuate at most in one day? If not an exact number (e.g., number of persons), please tell us the number of cars or trucks, helicopters you have, and the evacuation personnel you have available on staff to provide us with an understanding of your ability to evacuate.

5. Give us a report on the identity and quantity of any registered social organizations in the world (e.g., religious aid organization, philanthropic organizations, worker unions, etc.) and their capacity to evacuate and provide assistance.

Sampling strategy:
We seek this information for all 16 regions and so sampling is not directly applicable.
If we cannot get access to the regional officers for all 16 regions, then we request information from:
The following 4 regions first: Regions 1,5,9,13
Followed by the following 4: Regions 4,8,12,16
Followed by the following 4: Regions 2,6,10,14
Followed by the following 4: Regions 3,7,11,15


Other applicable detail:
None.
"""
from argparse import ArgumentParser
import csv
import logging
import os.path
import pickle
import random

from psychsim.pwl import *
from psychsim.domains.groundtruth.simulation.create import loadPickle

if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('-i','--instance',type=int,default=24,help='Instance to query')
    parser.add_argument('-r','--run',type=int,default=1,help='Run to query')
    parser.add_argument('-o','--output',default='TA2A-TA1C-0022.tsv',help='Output filename')
    parser.add_argument('-d','--debug',default='INFO',help='Level of logging detail')
    args = vars(parser.parse_args())
    # Extract logging level from command-line argument
    level = getattr(logging, args['debug'].upper(), None)
    if not isinstance(level, int):
        raise ValueError('Invalid debug level: %s' % args['debug'])
    logfile = '%s.log' % (os.path.splitext(__file__)[0])
    logging.basicConfig(level=level,filename=logfile)

    world = loadPickle(args['instance'],args['run'])

    regions = sorted([name for name in world.agents if name[:6] == 'Region'])
    actors = sorted([name for name in world.agents if name[:5] == 'Actor'])
    fields = ['Region','Shelter Capacity']
    root = os.path.join(os.path.dirname(__file__),'..','..','..','..','..',
        'Instances','Instance%d' % (args['instance']),
        'Runs','run-%d' % (args['run']))
    with open(os.path.join(root,args['output']),'w') as csvfile:
        writer = csv.DictWriter(csvfile,fields,delimiter='\t',extrasaction='ignore')
        writer.writeheader()
        for region in regions:
            record = {'Region': region}
            if stateKey(region,'shelterRisk') in world.variables:
                record['Shelter Capacity'] = len(actors)
            else:
                record['Shelter Capacity'] = 0
            writer.writerow(record)


