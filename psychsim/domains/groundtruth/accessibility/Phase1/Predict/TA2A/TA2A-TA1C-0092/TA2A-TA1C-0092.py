import logging
import os.path
from psychsim.pwl.keys import *
from psychsim.domains.groundtruth import accessibility

if __name__ == '__main__':
    parser = accessibility.createParser(output='TA2A-TA1C-0092-RR.tsv',seed=True)
    args = accessibility.parseArgs(parser,'%s.log' % (os.path.splitext(__file__)[0]))
    assert args['instance'] == 24
    assert args['run'] == 1
    data = accessibility.loadRunData(args['instance'],args['run'],82)
    demos = accessibility.readDemographics(data,last=True)
    hurricanes = accessibility.readHurricanes(args['instance'],args['run'])
    output = []
    names = {name for name in demos if demos[name]['Residence'] in {'Region02','Region06','Region09'}}
    fields = ['Timestep']+sorted(accessibility.demographics.keys())+\
        sum([['Evacuated Hurricane %d' % (h['Hurricane']),'Injured Hurricane %d' % (h['Hurricane'])] for h in hurricanes[:6]],[])
    for name in names:
        record = demos[name]
        output.append(record)
        record['Timestep'] = 82
        record['Participant'] = len(output)
        logging.info('Participant %d: %s' % (record['Participant'],name))
        for hurricane in hurricanes[:6]:
            actions = {data[name][actionKey(name)][t]['verb'] for t in range(hurricane['Landfall'],hurricane['End']+1)}
            health = {data[name]['__beliefs__'][stateKey(name,'health')][t]<0.2 for t in range(hurricane['Landfall'],hurricane['End']+1)}
            record['Evacuated Hurricane %d' % (hurricane['Hurricane'])] = 'yes' if 'evacuate' in actions else 'no'
            record['Injured Hurricane %d' % (hurricane['Hurricane'])] = 'yes' if True in health else 'no'
    accessibility.writeOutput(args,output,fields)
    