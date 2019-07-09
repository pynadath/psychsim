from argparse import ArgumentParser
import bz2
import csv
import logging
import os.path
import shutil
import subprocess

from psychsim.pwl import *
from psychsim.domains.groundtruth import accessibility

fields = ['Instance','Question','Metric','Actual','A','A Delta','B','B Delta']

targets = {9: 'Actor0066',10: 'Actor0044', 11: 'Actor0051', 12: 'Actor0072', 13: 'Actor0160', 14: 'Actor0132'}

def scoreCasualties(args,label,data):
    total = set()
    actors = sorted([name for name in data if name[:5] == 'Actor'])
    # Verify casualty count
    for row in accessibility.loadMultiCSV('PopulationTable.tsv',args['instance'],args['run'],['Input',label]):
        t = int(row['Timestep'])
        casualties = {name for name in actors if data[name][stateKey(name,'health')][t] < 0.2}
        if len(casualties) != int(row['Casualties']):
            logging.error('Instance %d, Run %d, Label %s, Timestep %d: Reported casualties=%d, Actual casualties=%s' % \
                (args['instance'],args['run'],label,t,int(row['Casualties']),','.join(sorted(casualties))))
        total |= casualties
    score = len(total)
    return score

def scoreGrievance(args,label,data,end=None):
    """
    :warning: Assumes there is an actor named 'Actor0001'
    """
    if end is None:
        # Find most recent time
        end = max(data['Actor0001'][stateKey('Actor0001','grievance')].keys())
    actors = [name for name in data if name[:5] == 'Actor']
    score = sum([data[name][stateKey(name,'grievance')][end] if data[name][stateKey(name,'alive')][end] else 1. for name in actors]) / len(actors)
    return score

def scoreIndividual(args,label,data,actor,start,end):
    if end is None:
        end = max(data['Actor0001'][stateKey('Actor0001','health')].keys())
    score = min([data[actor][stateKey(actor,'health')][t] for t in range(start,end+1)])
    return 1.-score

def runSimulation(label,instance,run,argv):
    args = accessibility.instances[instance-1]
    # Make directory if it does not already exist
    dirName = os.path.join(os.path.dirname(__file__),'..','..','Instances','Instance%d' % (args['instance']),'Runs','run-%d' % (run))
    if not os.path.exists(dirName):
        os.mkdir(dirName)
    if not os.path.exists(os.path.join(dirName,label)):
        # Have not completed this run yet, so...
        logging.info('Running Instance %d, Run %d, Label %s' % (args['instance'],run,label))
        # Copy over original hurricanes
        shutil.copy(os.path.join(dirName,'Input','HurricaneTable.tsv'),dirName)
        # Copy over original scenario file
        if os.path.exists(os.path.join(dirName,'Input','scenario365.pkl')):
            day = 365
        else:
            day = args['span']+1
        shutil.copy(os.path.join(dirName,'Input','scenario%d.pkl' % (day)),dirName)
        # Execute simulation
        cmd = [os.path.join(os.path.dirname(__file__),'..','..','gt.sh'),'-i','%d' % (args['instance']),'-r','%d' % (run),'--reload','%d' % (day),'--pickle','-d','INFO','--singlerun']+argv
        logging.info('Executing: %s',' '.join(cmd))
        result = subprocess.run(cmd)
        # Remove original scenario file
        os.remove(os.path.join(dirName,'scenario%d.pkl' % (day)))
        if result.returncode == 0:
            # Successful simulation
            logging.info('Success')
            subprocess.run(['bzip2',os.path.join(dirName,'*.pkl')],capture_output=True)
            os.mkdir(os.path.join(dirName,label))
            for name in os.listdir(dirName):
                if os.path.isfile(os.path.join(dirName,name)):
                    shutil.move(os.path.join(dirName,name),os.path.join(dirName,label))
        else:
            # Failed simulation
            logging.error(result.stderr)
        return result

if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('-e','--evaluate',action='store_true',help='Score all available runs')
    options = vars(parser.parse_args())
    logging.basicConfig(level=logging.INFO,filename=os.path.join(os.path.dirname(__file__),'prescribe.log'))
    output = {}
    for instance in range(9,15):
        # Initialize entries in final table
        for question in ['Constrained','Unconstrained','Individual'] if instance < 12 else ['Offseason','InSeason','Individual']:
            for metric in ['Casualties'] if question == 'Individual' else ['Casualties','Dissatisfaction']:
                output['%d%s%s' % (instance,question,metric)] = {'Instance': instance,'Question': question,'Metric': metric}
        args = accessibility.instances[instance-1]
        dirName = os.path.join(os.path.dirname(__file__),'..','..','Instances','Instance%d' % (args['instance']),'Runs','run-%d' % (args['run']))
        # Generate baseline results
        logging.info('Instance %d, Actual' % (instance))
        if instance > 11:
            argv = ['--seasons','2'] # long-term
            hurricane = None
        else:
            argv = ['-n','7','--hurricane',os.path.join(dirName,'Input','HurricaneInput.tsv')] # short-term
            hurricane = accessibility.readHurricanes(args['instance'],args['run'],'Input','HurricaneInput.tsv')[-1]
        result = runSimulation('Actual',instance,args['run'],argv)
        if options['evaluate']:
            # Load in baseline data
            try:
                data = accessibility.loadRunData(args['instance'],args['run'],subs=['Input','Actual'])
            except FileNotFoundError:
                logging.warning('No data for %d %d Actual' % (args['instance'],args['run']))
                continue
            # Score baseline simulation
            actual = {'Casualties': scoreCasualties(args,'Actual',data),
                'Dissatisfaction': scoreGrievance(args,'Actual',data,hurricane['End'] if instance < 12 else None),
                'Individual': scoreIndividual(args,'Actual',data,targets[instance],hurricane['Start'] if instance < 12 else 365,
                    hurricane['End'] if instance < 12 else None)}
        # Simulate prescriptions
        for team in ['A','B']:
            for question in ['Constrained','Unconstrained','Individual'] if instance < 12 else ['Offseason','InSeason','Individual']:
                for metric in ['Casualties'] if question == 'Individual' else ['Casualties','Dissatisfaction']:
                    logging.info('Instance %d, Team %s, Question %s, Metric %s' % (instance,team,question,metric))
                    label = '%s%s%s' % (team,question,metric)
                    # Generate prescription results
                    if instance > 11:
                        # Long term
                        argv = ['--seasons','2','--prescription',
                            os.path.join(os.path.dirname(__file__),team,'%d' % (instance),'%sPrescription%s.tsv' % (question,metric))]
                        if question == 'Individual':
                            argv[2] = '--target'
                            argv.insert(3,targets[instance])
                    else:
                        argv = ['-n','7','--hurricane',os.path.join(dirName,'Input','HurricaneInput.tsv'),'--prescription',
                            os.path.join(os.path.dirname(__file__),team,'%d' % (instance),'%sPrescription%s.tsv' % (question,metric))]
                        if question == 'Individual':
                            argv[4] = '--target'
                            argv.insert(5,targets[instance])
                    result = runSimulation(label,instance,args['run'],argv)
                    if options['evaluate']:
                        try:
                            data = accessibility.loadRunData(args['instance'],args['run'],subs=['Input',label])
                        except FileNotFoundError:
                            logging.warning('No data for %d %d %s' % (args['instance'],args['run'],label))
                            continue
                        if question == 'Individual':
                            score = scoreIndividual(args,label,data,targets[instance],hurricane['Start'] if instance < 12 else 365,
                                hurricane['End'] if instance < 12 else None)
                            output['%d%s%s' % (instance,question,metric)]['Actual'] = actual[question]
                            output['%d%s%s' % (instance,question,metric)]['%s Delta' % (team)] = (actual[question]-score)/actual[question]
                        elif metric == 'Casualties':
                            score = scoreCasualties(args,label,data)
                            output['%d%s%s' % (instance,question,metric)]['Actual'] = actual[metric]
                            output['%d%s%s' % (instance,question,metric)]['%s Delta' % (team)] = (actual[metric]-score)/actual[metric]
                        elif metric == 'Dissatisfaction':
                            score = scoreGrievance(args,label,data,hurricane['End'] if instance < 12 else None)
                            output['%d%s%s' % (instance,question,metric)]['Actual'] = actual[metric]
                            output['%d%s%s' % (instance,question,metric)]['%s Delta' % (team)] = (actual[metric]-score)/actual[metric]
                        else:
                            raise NameError('Unknown question: %s %s' % (question,metric))
                        if isinstance(score,float):
                            logging.info('Score: %5.3f' % (score))
                        else:
                            logging.info('Score: %d' % (score))
                        output['%d%s%s' % (instance,question,metric)][team] = score
    if options['evaluate']:
        accessibility.writeOutput(args,output.values(),fields,'PrescribeResults.tsv',os.path.dirname(__file__))
