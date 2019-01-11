from psychsim.pwl.keys import *
from psychsim.domains.groundtruth import accessibility

if __name__ == '__main__':
    parser = accessibility.createParser(output='TA2A-TA1C-0052.tsv')
    args = accessibility.parseArgs(parser)
    data = accessibility.loadRunData(args['instance'],args['run'],82)
    output = []
    for day,action in sorted(data['System'][actionKey('System')].items()):
        output.append({'Timestep': day, 'Aid To': action['object']})
    fields = ['Timestep','Aid To'] 
    accessibility.writeOutput(args,output,fields)
