import pygame

import psychsim.ui.viz as viz

# Initialize visualization

def initVisualization(args):
    pygame.init()
    global win
    win = pygame.display.set_mode((1024, 768))
    global simpaused
    simpaused = False
    global simdata
    simdata = {}
    global vm
    vm = viz.VizMap(1024, 768, 6, 6, simdata, 2, "", win, "safety", args['visualize'])

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
