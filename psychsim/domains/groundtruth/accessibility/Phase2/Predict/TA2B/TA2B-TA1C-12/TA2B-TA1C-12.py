from argparse import ArgumentParser
import logging
import os.path
import random
import sys

from psychsim.pwl import *
from psychsim.domains.groundtruth import accessibility
from psychsim.domains.groundtruth.simulation import survey

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO,filename='%s%s' % (os.path.splitext(__file__)[0],'.log'))
    parser = ArgumentParser()
    parser.add_argument('-d','--debug',action='store_true',help='Run without writing any files')
    cmd = vars(parser.parse_args())
    variables = {}
    for instance,args in accessibility.instanceArgs('Phase2','Predict'):
        print('Instance %d (%d,%d)' % (instance,args['instance'],args['run']))
        logging.info('Instance %d (%d,%d)' % (instance,args['instance'],args['run']))
        config = accessibility.getConfig(args['instance'])
        world = accessibility.unpickle(instance)
        states = {}
        participants = accessibility.readParticipants(args['instance'],args['run'],splitHurricanes=True,duplicates=True)
        hurricanes = [h for h in accessibility.readHurricanes(args['instance'],args['run']) if h['End'] <= args['span']]
        output = []
        for old in hurricanes[:-1]:
            pool = participants['Post-survey %d' % (old['Hurricane'])]
            for partID,name in sorted(pool.items()):
                agent = world.agents[name]
                hurricane = hurricanes[old['Hurricane']]
                t = random.choice(list(range(hurricane['End']+1,
                    hurricanes[hurricane['Hurricane']]['Start'] if hurricane['Hurricane'] < len(hurricanes) else args['span'])))
                if accessibility.getInitialState(args,name,'alive',world,states,t).first():
                    logging.info('Participant %d (%s) completing for post-survey %d' % (partID,name,hurricane['Hurricane']))
                    output += survey.postSurvey(args,name,world,states,config,t,hurricane,variables,'%d Hurricane %d' % (partID,old['Hurricane']))
                else:
                    logging.warning('Participant %d (%s) not available for post-survey %d' % (partID,name,hurricane['Hurricane']))
        output.sort(key=lambda e: (int(e['EntityIdx'].split()[-1]),int(e['EntityIdx'].split()[1])))
        if not cmd['debug']:
            accessibility.writeOutput(args,output,accessibility.fields['RunData'],'RunDataTable.tsv',
                os.path.join(os.path.dirname(__file__),'Instances','Instance%d' % (instance),'Runs','run-0'))
    if not cmd['debug']:
        accessibility.writeVarDef(os.path.dirname(__file__),list(variables.values()))
