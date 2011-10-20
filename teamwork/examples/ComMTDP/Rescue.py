from teamwork.examples.RAP import *

import string

if __name__== '__main__':
    import getopt
    import sys

    usage = 'Usage: Rescue.py [--buildings <file>] [-x <num>] [-y <num>]'
    try:
	optlist,args = getopt.getopt(sys.argv[1:],'buildings=',['xy'])
    except getopt.error:
        print usage
        sys.exit(-1)

    buildings = '/home/pynadath/src/machinetta/Machinetta/RAPInterface/buildings.txt'
    precision = {'x':2,'y':2}
    for option in optlist:
        if option[0] == '--buildings':
            buildings = options[1]
        elif option[0] == '-x':
            precision['x'] = int(option[1])
        elif option[0] == '-y':
            precision['y'] = int(option[1])
    # Read buildings
    import fileinput
    
    grid = {'x':{'min':-1,'max':-1},
                 'y':{'min':-1,'max':-1}}
    city = {}
    tasks = []
    for line in fileinput.input(buildings):
        values = string.split(line)
        id = values[0]
        x = values[1]
        y = values[2]
        tasks.append('Building '+id)
        city[id] = {'x':x,'y':y}
        # Update range of possible x,y coordinates
        if grid['x']['min'] < 0 or grid['x']['min'] > x:
            grid['x']['min'] = x
        if grid['x']['max'] < 0 or grid['x']['max'] < x:
            grid['x']['max'] = x
        if grid['y']['min'] < 0 or grid['y']['min'] > y:
            grid['y']['min'] = y
        if grid['y']['max'] < 0 or grid['y']['max'] < y:
            grid['y']['max'] = y
    fileinput.close()

    print city

    sys.exit(0)
    taskSpace = DivisibleSpace(tasks,'Task')
##    taskSpace.verify()
    taskSpace.setPrecision(precision['Task'])

##    print len(taskSpace.generator(None,None,0,None))
    stateSpace = range(precision['State'])

    RAPID = 0
    rap1 = RAP(stateSpace,taskSpace,'RAP '+`RAPID`)
    RAPID = RAPID+1
    rap2 = RAP(stateSpace,taskSpace,'RAP '+`RAPID`)
    team = RAPTeam([rap1,rap2])
    
    goalSpace = DivisibleSpace(tasks,'Goal')
    goalSpace.setPrecision(precision['Task'])
    
    model = RAPModel(taskSpace,team)
    
