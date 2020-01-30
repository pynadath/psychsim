import csv
import os

from psychsim.domains.groundtruth import accessibility

targets = {20: 'Actor0461', 21: 'Actor0361'}
if __name__ == '__main__':
    fields = ['Challenge','Baseline Casualties','TA2A Casualties','TA2B Casualties','Baseline Injury','TA2A Injury','TA2B Injury']
    output = []
    for instance,args in accessibility.instanceArgs('Phase2','Prescribe'):
        print('Instance %d (%d,%d)' % (instance,args['instance'],args['run']))
        config = accessibility.getConfig(args['instance'])
        states = {}
        # Load world
        world = accessibility.unpickle(instance)
        actors = [name for name in world.agents if name[:5] == 'Actor' and world.getState(name,'alive',unique=True)]
        rootDir = accessibility.getDirectory(args)
        if instance == 20:
            entry = {'Challenge': 'Short-term'}
        else:
            entry = {'Challenge': 'Long-term'}
        for sub in ['Actual','TA2A','TA2B']:
            path = os.path.join(rootDir,sub)
            times = [int(name[5:-10]) for name in os.listdir(path) if name[-10:] == 'Nature.pkl']
            states.clear()
            accessibility.loadState(args,states,max(times),'Nature',world,sub)
            casualties = len([name for name in actors if not world.getState(name,'alive',unique=True)])
            if sub == 'Actual':
                entry['Baseline Casualties'] = casualties
                entry['Baseline Injury'] = 0.
            else:
                entry['%s Casualties' % (sub)] = casualties
                entry['%s Injury' % (sub)] = 0.
        output.append(entry)
    with open('PrescribeResults.tsv','w') as csvfile:
        writer = csv.DictWriter(csvfile,fields,delimiter='\t',extrasaction='ignore')
        writer.writeheader()
        for entry in output:
            writer.writerow(entry)
