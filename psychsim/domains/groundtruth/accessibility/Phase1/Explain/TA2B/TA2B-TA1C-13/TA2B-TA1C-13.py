from psychsim.pwl.keys import *
from psychsim.domains.groundtruth import accessibility

if __name__ == '__main__':
    parser = accessibility.createParser(day=True,output='TA2B-TA1C-13.tsv')
    parser.add_argument('--directory',help='Output directory')
    args = accessibility.parseArgs(parser)
    data = accessibility.loadRunData(args['instance'],args['run'],args['day'] if args['day'] else None,
    	subs=['Input'] if args['instance'] > 50 else None)
    output = []
    for day,action in sorted(data['System'][actionKey('System')].items()):
        output.append({'Timestep': day, 'Aid To': action['object']})
    fields = ['Timestep','Aid To'] 
    accessibility.writeOutput(args,output,fields,dirName=args['directory'])
