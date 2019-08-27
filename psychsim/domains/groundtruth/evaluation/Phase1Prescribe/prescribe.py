from argparse import ArgumentParser
import bz2
import csv
import logging
import os.path
import shutil
import subprocess

from psychsim.pwl import *
from psychsim.domains.groundtruth import accessibility

fields = ['Instance','Question','Metric','Actual','A','A Delta','B','B Delta','Null']

targets = {9: 'Actor0066',10: 'Actor0044', 11: 'Actor0051', 12: 'Actor0072', 13: 'Actor0160', 14: 'Actor0132'}
TA2Btargets = {
    'UnconstrainedCasualties': {
        9: {'Actor0078','Actor0131', 'Actor0078', 'Actor0021', 'Actor0028', 'Actor0016', 'Actor0096', 'Actor0126', 'Actor0160', 'Actor0014'},
        10: {'Actor0083', 'Actor0160', 'Actor0063', 'Actor0103', 'Actor0033', 'Actor0094', 'Actor0144', 'Actor0006', 'Actor0021'},
        11: {'Actor0111', 'Actor0154', 'Actor0008', 'Actor0146', 'Actor0089', 'Actor0051', 'Actor0059', 'Actor0032', 'Actor0127', 'Actor0104'}},
    'UnconstrainedDissatisfaction': {
        11: {'Actor0154','Actor0051','Actor0111','Actor0089','Actor0127','Actor0008', 'Actor0036', 'Actor0036', 'Actor0082', 'Actor0104'}},
    'InSeasonCasualties': {
        12: {'Actor0023','Actor0029', 'Actor0152', 'Actor0027', 'Actor0106', 'Actor0033', 'Actor0120', 'Actor0059', 'Actor0081', 'Actor0035'},
        13: {'Actor0088', 'Actor0078', 'Actor0056', 'Actor0148', 'Actor0054', 'Actor0068', 'Actor0098', 'Actor0160', 'Actor0043', 'Actor0074'},
        14: {'Actor0011', 'Actor0013', 'Actor0022', 'Actor0094', 'Actor0057', 'Actor0080', 'Actor0079', 'Actor0155', 'Actor0145', 'Actor0068'}},
    'OffseasonCasualties': {
        12: {'Region12','Region13','Region14'},
        13: {'Region12','Region13','Region14'},
        14: {'Region12','Region13','Region14'}},
    'InSeasonDissatisfaction': {
        12: {'tax': ['Actor0028', 'Actor0077', 'Actor0134', 'Actor0028', 'Actor0075', 'Actor0103', 'Actor0037', 'Actor0088', 'Actor0003', 'Actor0086'],
            'aid': ['Region14','Region08','Region10','Region01','Region09','Region04','Region16','Region15','Region13','Region02']},
        13: {'tax': ['Actor0124', 'Actor0062', 'Actor0148', 'Actor0042', 'Actor0092', 'Actor0007', 'Actor0148', 'Actor0134', 'Actor0138', 'Actor0054'],
            'aid': ['Region01','Region07','Region08','Region15','Region04','Region09','Region12','Region06','Region02','Region03']},
        14: {'tax': ['Actor0133', 'Actor0135', 'Actor0135', 'Actor0123', 'Actor0087', 'Actor0133', 'Actor0156', 'Actor0109', 'Actor0016', 'Actor0131'],
            'aid': ['Region13','Region06','Region15','Region14','Region10','Region16','Region05','Region12','Region09','Region01']}}
    }

def scoreCasualties(args,label,data):
    total = set()
    actors = sorted([name for name in data if name[:5] == 'Actor'])
    # Verify casualty count
    for row in accessibility.loadMultiCSV('PopulationTable.tsv',args['instance'],args['run'],['Input',label]):
        t = int(row['Timestep'])
        casualties = {name for name in actors if data[name][stateKey(name,'health')].get(t,1.) < 0.2}
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
        cmd = ['python3',os.path.join(os.path.dirname(__file__),'..','..','simulate.py'),'-i','%d' % (args['instance']),'-r','%d' % (run),'--reload','%d' % (day),'--pickle','-d','INFO','--singlerun']+argv
        logging.info('Executing: %s',' '.join(cmd))
        result = subprocess.run(cmd)
        # Remove original scenario file
        os.remove(os.path.join(dirName,'scenario%d.pkl' % (day)))
        if result.returncode == 0:
            # Successful simulation
            logging.info('Success')
            pklFiles = [name for name in os.listdir(dirName) if os.path.splitext(name)[1] == '.pkl']
            print(pklFiles)
            for name in pklFiles:
                print('compressing %s' % (os.path.join(dirName,name)))
                subprocess.run(['bzip2','"%s"' % (os.path.join(dirName,name))])
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
    storage = {}
    actual = {}
    for instance in range(9,15):
        # Initialize entries in final table
        for question in ['Constrained','Unconstrained','Individual'] if instance < 12 else ['Offseason','InSeason','Individual']:
            for metric in ['Casualties'] if question == 'Individual' else ['Casualties','Dissatisfaction']:
                output['%d%s%s' % (instance,question,metric)] = {'Instance': instance,'Question': question,'Metric': metric}
        args = accessibility.instances[instance-1]
        dirName = os.path.join(os.path.dirname(__file__),'..','..','Instances','Instance%d' % (args['instance']),'Runs','run-%d' % (args['run']))
        # Generate baseline results
        for label in ['Actual','Null']:
            logging.info('Instance %d, Actual' % (instance))
            if instance > 11:
                argv = ['--seasons','2'] # long-term
                hurricane = None
            else:
                argv = ['-n','7','--hurricane',os.path.join(dirName,'Input','HurricaneInput.tsv')] # short-term
                hurricane = accessibility.readHurricanes(args['instance'],args['run'],'Input','HurricaneInput.tsv')[-1]
            if label == 'Null':
                argv += ['--prescription','NULL']
            result = runSimulation(label,instance,args['run'],argv)
            if options['evaluate']:
                # Load in baseline data
                try:
                    data = accessibility.loadRunData(args['instance'],args['run'],subs=['Input',label])
                except FileNotFoundError:
                    logging.warning('No data for %d %d %s' % (args['instance'],args['run'],label))
                    continue
                # Score baseline simulation
                actual[label] = {'Casualties': scoreCasualties(args,label,data),
                    'Dissatisfaction': scoreGrievance(args,label,data,hurricane['End'] if instance < 12 else None),
                    'Individual': scoreIndividual(args,label,data,targets[instance],hurricane['Start'] if instance < 12 else 365,
                        hurricane['End'] if instance < 12 else None)}
                if label == 'Actual':
                    storage[instance] = data
                if label == 'Null':
                    for name in data:
                        if name[:5] == 'Actor':
                            for t,value in data[name][stateKey(name,'grievance')].items():
                                if instance < 12:
                                    start = accessibility.instances[instance-1]['span']+1
                                else:
                                    start = 366
                                if t > start and value < 1.0:
                                    assert value > data[name][stateKey(name,'grievance')][t-1],'%s vs. %s (%d)' % \
                                        (value,data[name][stateKey(name,'grievance')][t-1],t)
        # Simulate prescriptions
        for team in ['A','B']:
            for question in ['Constrained','Unconstrained','Individual'] if instance < 12 else ['Offseason','InSeason','Individual']:
                for metric in ['Casualties'] if question == 'Individual' else ['Casualties','Dissatisfaction']:
                    logging.info('Instance %d, Team %s, Question %s, Metric %s' % (instance,team,question,metric))
                    label = '%s%s%s' % (team,question,metric)
                    # Generate prescription results
                    prescription = os.path.join(os.path.dirname(__file__),team,'%d' % (instance),'%sPrescription%s.tsv' % (question,metric))
                    if os.path.exists(prescription):
                        if instance > 11:
                            # Long term
                            argv = ['--seasons','2']
                        else:
                            argv = ['-n','7','--hurricane',os.path.join(dirName,'Input','HurricaneInput.tsv'),]
                        if question == 'Individual':
                            argv += ['--target',targets[instance],prescription]
                        elif team == 'B' and '%s%s' % (question,metric) in TA2Btargets and instance in TA2Btargets['%s%s' % (question,metric)]:
                            for target in TA2Btargets['%s%s' % (question,metric)][instance]:
                                if target[:5] == 'Actor':
                                    argv += ['--target',target,prescription]
                                elif target[:6] == 'Region':
                                    if instance not in storage:
                                        storage[instance] = accessibility.loadRunData(args['instance'],args['run'],subs=['Input','Actual'])
                                    for name in storage[instance]:
                                        if stateKey(name,'region') in storage[instance][name]:
                                            if storage[instance][name][stateKey(name,'region')][1] == target:
                                                argv += ['--target',name,prescription]
                                elif target == 'tax':
                                    for name in TA2Btargets['%s%s' % (question,metric)][instance][target]:
                                        argv += ['--tax',name]
                                elif target == 'aid':
                                    for name in TA2Btargets['%s%s' % (question,metric)][instance][target]:
                                        argv += ['--aid',name]
                        else:
                            argv += ['--prescription',prescription]
                        result = runSimulation(label,instance,args['run'],argv)
                        if options['evaluate']:
                            try:
                                data = accessibility.loadRunData(args['instance'],args['run'],subs=['Input',label])
                            except FileNotFoundError:
                                logging.warning('No data for %d %d %s' % (args['instance'],args['run'],label))
                                continue
                            for label in ['Actual','Null']:
                                output['%d%s%s' % (instance,question,metric)][label] = actual[label][question if question == 'Individual' else metric]
                            if question == 'Individual':
                                score = scoreIndividual(args,label,data,targets[instance],hurricane['Start'] if instance < 12 else 365,
                                    hurricane['End'] if instance < 12 else None)
                                output['%d%s%s' % (instance,question,metric)]['%s Delta' % (team)] = (actual['Actual'][question]-score)/actual['Actual'][question]
                            elif metric == 'Casualties':
                                score = scoreCasualties(args,label,data)
                                output['%d%s%s' % (instance,question,metric)]['%s Delta' % (team)] = (actual['Actual'][metric]-score)/actual['Actual'][metric]
                            elif metric == 'Dissatisfaction':
                                score = scoreGrievance(args,label,data,hurricane['End'] if instance < 12 else None)
                                output['%d%s%s' % (instance,question,metric)]['%s Delta' % (team)] = (actual['Actual'][metric]-score)/actual['Actual'][metric]
                            else:
                                raise NameError('Unknown question: %s %s' % (question,metric))
                            if isinstance(score,float):
                                logging.info('Score: %5.3f' % (score))
                            else:
                                logging.info('Score: %d' % (score))
                            output['%d%s%s' % (instance,question,metric)][team] = score
    if options['evaluate']:
        accessibility.writeOutput(args,output.values(),fields,'PrescribeResults.tsv',os.path.dirname(__file__))
