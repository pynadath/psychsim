import csv
import logging
import os.path
import random
import shutil

from psychsim.domains.groundtruth import accessibility

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO,filename=os.path.join(os.path.dirname(__file__),'TA2A-TA1C-0202.log'))
    fields = ['Timestep','Hurricane','Predicted Timestep','Predicted Location','Predicted Category']
    for instance in [1,9,10,11,12,13,14]
        logging.info('Instance %d' % (instance))
        args = accessibility.instances[instance-1]
        world = accessibility.loadPickle(args['instance'],args['run'],args['span']+(1 if instance == 2 or instance > 8 else 0),
            sub='Input' if instance > 2 else None)
        hurricanes = [h for h in accessibility.readHurricanes(args['instance'],args['run'],'Input' if instance > 2 else None) 
            if h['End'] < args['span']]
        shutil.copy(accessibility.instanceFile(args,'HurricaneTable.tsv','Input' if instance > 2 else None),
            os.path.join(os.path.dirname(__file__),'Instances','Instance%d' % (instance),'Runs','run-0'))
        output = []
        for hurricane in hurricanes:
            predictions = accessibility.hurricanePrediction(world,hurricane,True)
            print('\n'.join(map(str,predictions)))
            output += predictions
        accessibility.writeOutput(args,output,fields,'TA2A-TA1C-0202.tsv',
            os.path.join(os.path.dirname(__file__),'Instances','Instance%d' % (instance),'Runs','run-0'))
