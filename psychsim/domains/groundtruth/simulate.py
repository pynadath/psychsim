from argparse import ArgumentParser
import csv
import logging
import os.path

from psychsim.domains.groundtruth.simulation.data import mapFromTandE,reverseLikert
from psychsim.domains.groundtruth.simulation.create import getConfig
from psychsim.domains.groundtruth.simulation.execute import runInstance

def addToIndividualList(entry):
    vm.individualList.append(viz.Individual(entry['x'], entry['y'], viz.SimColor.GRAY,
                                            int(entry['participant'])))
    

def vizUpdateLoop(day):
    global simpaused
    i = 0.0
    #pygame.time.delay(100)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            exit()
        elif event.type == pygame.KEYUP:
            simpaused = not simpaused
            print("Day %d %s" % (day, "(Paused)" if simpaused else "" ))
            

    viz.handleInput()
    vm.update(day)        

    pygame.display.set_caption("Visualization Day %d %s" % (day, "(Paused)" if simpaused else "" ))
    pygame.display.update()


def addToVizData(keyname, entry):

    
    if not keyname in simdata:
        simdata[keyname] = []
        simdata[keyname].append({})

    headervalues = list(entry.keys())
    values = list(entry.values())
    entityname = values[1]
    simday = int(values[0])

    #print ("Simday %s EntityName %s %d" %(simday, entityname, len(simdata[keyname])))
    if len(simdata[keyname]) == simday:
        simdata[keyname].append({})
    
    if not entityname in simdata[keyname][simday]:
        simdata[keyname][simday][entityname] = {}

    for h in range(2,len(headervalues)):
        simdata[keyname][simday][entityname][headervalues[h]] = []

    entityname = list(entry.values())[1]
    for cntr in range (2, len(entry)):
        
        simdata[keyname][simday][entityname][headervalues[cntr]].append(values[cntr])
    
if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('-d','--debug',default='WARNING',help='Level of logging detail')
    parser.add_argument('-r','--runs',default=1,type=int,help='Number of runs to run')
    parser.add_argument('--singlerun',action='store_true',help='Run only the specified run')
    parser.add_argument('-p','--profile',action='store_true',help='Profile simulation step')
    parser.add_argument('-c','--compile',action='store_true',help='Pre-compile agent policies')
    parser.add_argument('-w','--write',action='store_true',help='Write simulation definition tables')
    parser.add_argument('-v','--visualize',default=None,help='Visualization feature')
    parser.add_argument('-m','--multiprocessing',action='store_true',help='Use multiprocessing')
    parser.add_argument('--TA2BTA1C10',action='store_true',help='Generate surveys as specified in TA2B-TA1C-10')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('-n','--number',default=None,type=int,help='Number of hurricanes to run')
    group.add_argument('--seasons',default=None,type=int,help='Number of seasons to run')
    group.add_argument('--days',default=None,type=int,help='Number of days to run')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--rerun',action='store_true',help='Run instance, even if previously saved')
    group.add_argument('--reload',type=int,default=0,help='Pick up where instance/run left off')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--pickle',action='store_true',help='Use Python pickle, not XML, to save scenario')
    group.add_argument('--xml',action='store_true',help='Save scenario as XML')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('-i','--instance',default=None,type=int,help='Instance number')
    group.add_argument('-s','--samples',default=None,help='File of sample parameter settings')
    
    args = vars(parser.parse_args())
    # Extract logging level from command-line argument
    level = getattr(logging, args['debug'].upper(), None)
    if not isinstance(level, int):
        raise ValueError('Invalid debug level: %s' % args['debug'])
    logging.basicConfig(level=level)

    # Initialize visualization
    global vm
    global simpaused
    simpaused = False

    if args['visualize']:
        import pygame
        import psychsim.ui.viz as viz

        simdata = {}
        win = pygame.display.set_mode((1024, 768))
        pygame.init()

        vm = viz.VizMap(1024, 768, 7, 7, simdata, 2, "", win, "safety", args['visualize'])


    if args['samples']:
        with open(args['samples']) as csvfile:
            base = int(os.path.splitext(os.path.split(args['samples'])[1])[0])
            config = getConfig(base)
            reader = csv.DictReader(csvfile,delimiter='\t')
            for row in reader:
                shelters = []
                risks = []
                pets = []
                healths = []
                wealths = []
                for key,value in row.items():
                    key = key.strip()
                    if key == 'Sample ID':
                        instance = base+int(row[key])
                    elif key == '\'Actor’s distribution over gender\'':
                        value = int(value)
                        if value == 1:
                            config.set('Actors','male_prob',str(0.5))
                        elif value == 2:
                            config.set('Actors','male_prob',str(0.4))
                        else:
                            assert value == 3
                            config.set('Actors','male_prob',str(0.6))
                    elif key[:6] == 'Region' and key[-9:] == ' shelter\'':
                        if value == '1':
                            shelters.append(int(key[6:-9]))
                            config.set('Shelter','exists','yes')
                            config.set('Shelter','region','%s' % (','.join(['%02d' % (r)
                                                                            for r in shelters])))
                    elif key[:7] == 'Shelter' and key[-22:] == 'initial level of risk\'':
                        region = int(key[7:-22])
                        if region in shelters:
                            risks.append(reverseLikert[value])
                            config.set('Shelter','risk',','.join(risks))
                    elif key[:7] == 'Shelter' and key[-11:] == 'pet policy\'':
                        region = int(key[7:-11])
                        if region in shelters:
                            if value == '0':
                                pets.append('no')
                            else:
                                assert value == '1'
                                pets.append('yes')
                            config.set('Shelter','pets',','.join(pets))
                    elif key[:-2] == '\'Actor’s distribution over health: group ':
                        healths.append(str(max(min(1.,float(value)),0.2)))
                        assert int(key[-2:-1]) == len(healths)
                        config.set('Actors','health_value_age',','.join(healths))
                    elif key[:-2] == '\'Actor’s distribution over resources: group ':
                        wealths.append(str(max(min(1.,float(value)),0.2)))
                        assert int(key[-2:-1]) == len(wealths)
                        config.set('Actors','wealth_value_age',','.join(wealths))
                    else:
                        section,option,fun = mapFromTandE[key]
                        if fun is not None:
                            value = fun[value]
                        if section == 'Regions':
                            value = str(max(min(1.,float(value)),0.2))
                        config.set(section,option,value)
                with open(os.path.join(os.path.dirname(__file__),'config',
                                       '%06d.ini' % (instance)),'w') as csvfile:
                    config.write(csvfile)
                runInstance(instance,args,config,args['rerun'])
    else:
        config = getConfig(args['instance'])
        runInstance(args['instance'],args,config,args['rerun'])
        
