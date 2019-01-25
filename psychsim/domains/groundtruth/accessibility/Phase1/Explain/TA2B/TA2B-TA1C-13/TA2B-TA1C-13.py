from psychsim.pwl.keys import *
from psychsim.domains.groundtruth import accessibility

if __name__ == '__main__':
    parser = accessibility.createParser(output='TA2B-TA1C-13.tsv')
    args = accessibility.parseArgs(parser)
    data = accessibility.loadRunData(args['instance'],args['run'])
    output = []
    for day,action in sorted(data['System'][actionKey('System')].items()):
        output.append({'Timestep': day, 'Aid To': action['object']})
    fields = ['Timestep','Aid To'] 
    accessibility.writeOutput(args,output,fields)
