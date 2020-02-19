import csv
import os

from psychsim.domains.groundtruth import accessibility

targets = {20: 'Actor0461', 21: 'Actor0361'}
if __name__ == '__main__':
    fields = ['Challenge']
    output = []
    for instance,args in accessibility.instanceArgs('Phase2','Prescribe'):
        print('Instance %d (%d,%d)' % (instance,args['instance'],args['run']))
        runs = ['Actual','TA2A','TA2B']
        if instance == 20:
            entry = {'Challenge': 'Short-term'}
            runs += ['TA2AConstrained','TA2AUnconstrained','TA2BConstrained','TA2BUnconstrained']
        else:
            entry = {'Challenge': 'Long-term'}
        config = accessibility.getConfig(args['instance'])
        states = {}
        # Load world
        world = accessibility.unpickle(instance)
        actors = [name for name in world.agents if name[:5] == 'Actor' and world.getState(name,'alive',unique=True)]
        rootDir = accessibility.getDirectory(args)
        for sub in runs:
            path = os.path.join(rootDir,sub)
            times = [int(name[5:-10]) for name in os.listdir(path) if name[-10:] == 'Nature.pkl']
            states.clear()
            accessibility.loadState(args,states,max(times),'Nature',world,sub)
            casualties = len([name for name in actors if not world.getState(name,'alive',unique=True)])
            if sub == 'Actual':
                var = 'Baseline Casualties'
            else:
                var = '%s Casualties' % (sub)
            entry[var] = casualties
            if instance == 20:
                fields.append(var)
            if sub == 'Actual':
                var = 'Baseline Injury'
            else:
                var = '%s Injury' % (sub)
            entry[var] = 0.
            if instance == 20:
                fields.append(var)
        output.append(entry)
    with open('PrescribeResults.tsv','w') as csvfile:
        writer = csv.DictWriter(csvfile,fields,delimiter='\t',extrasaction='ignore')
        writer.writeheader()
        for entry in output:
            writer.writerow(entry)
