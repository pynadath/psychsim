# try:
#     import pygame
# except ModuleNotFoundError:
#     pass

import psychsim.ui.viz as viz
import queue
import time

# Initialize visualization

def initVisualization(args):
    # # pygame.init()
    # global simpaused
    # simpaused = False
    global simdata
    simdata = {}
    global vm
    vm = viz.VizMap(1024, 768, 6, 6, simdata, 2, "safety", "health")
    global dayQueue
    dayQueue= queue.Queue()
    global stopViz
    stopViz = False

def addDayToQueue(day):
    dayQueue.put(day)


def addToIndividualList(entry):
    #print ("Entry %s"%entry)
    vm.individualList.append(viz.Individual(entry['x'], entry['y'], viz.SimColor.GRAY,
                                            entry['participant'], vm, entry['region']))
    

def vizUpdateLoop():
    #global simpaused
    #i = 0.0

    # for event in pygame.event.get():
    #     if event.type == pygame.QUIT:
    #         exit()
    #     elif event.type == pygame.KEYUP:
    #         simpaused = not simpaused
    #         print("Day %d %s" % (day, "(Paused)" if simpaused else "" ))
    prevDay = -1
    day = -1
    while True:  

        try:
            day = dayQueue.get_nowait()
        except queue.Empty:
            pass

        try:
            stopViz = not vm.update(day)        
            if not stopViz and not day is -1:
                vm.updateTitle("Visualization Day %d" % day)
        except:
            print("Renderer threw an exception")     
        if stopViz:
            print("Exiting Renderer")
            break

        
        
    # pygame.display.set_caption("Visualization Day %d %s" % (day, "(Paused)" if simpaused else "" ))
    # pygame.display.update()

def closeViz():
    stopViz = True

def addToVizData(keyname, entry):

    if not keyname in simdata:
        simdata[keyname] = {}

    headervalues = list(entry.keys())
    values = list(entry.values())
    entityname = values[1]
    simday = int(values[0])
    
    if not simday in simdata[keyname]:
        simdata[keyname][simday] = {}
    
    
    if not entityname in simdata[keyname][simday]:
        simdata[keyname][simday][entityname] = {}

    # for h in range(2,len(headervalues)):
    #     simdata[keyname][simday][entityname][headervalues[h]] = []

    entityname = list(entry.values())[1]
    for cntr in range (2, len(entry)):
        
        #simdata[keyname][simday][entityname][headervalues[cntr]].append(values[cntr])
        simdata[keyname][simday][entityname][headervalues[cntr]] = values[cntr]
