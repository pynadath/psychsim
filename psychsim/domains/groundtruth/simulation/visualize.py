# try:
#     import pygame
# except ModuleNotFoundError:
#     pass

import psychsim.ui.viz as viz
import queue
import time
from threading import Thread, current_thread, RLock
import inspect

currentOwnerThread = 'None'
currentOwnerFunction = 'None'
useLock = True
mapLock = RLock()
def getLock():
    global currentOwnerThread
    global currentOwnerFunction

    if useLock:
        #print ('Requesting Lock Acquire: %s Requesting Function %s Current owner thread is %s Current Owner Function is %s'%(current_thread().name, inspect.stack()[1].function, currentOwnerThread, currentOwnerFunction))
        mapLock.acquire()
        currentOwnerThread = current_thread().name
        currentOwnerFunction = inspect.stack()[1].function
        #print ('After Lock Acquire: New Owner Thread %s New Owner Function %s'%(currentOwnerThread,currentOwnerFunction))

def releaseLock():
    global currentOwnerThread
    global currentOwnerFunction
    if useLock:
        mapLock.release()
        #print ('After Lock Release: PRev Owner Thread %s Prev Owner Function %s'%(currentOwnerThread,currentOwnerFunction))

        currentOwnerThread = "None"
        currentOwnerFunction = "None"


def getCurrentThreadName():
    #print ("%s Requested %s" %(inspect.stack()[1].function, current_thread().name))
    return current_thread().name
    
class SimData:

    def __init__(self):
        self.simdata = {}
        self.dayQueue = queue.Queue()
        self.stopViz = False
        self.vm = None
        self.maxDay = 0


class SimThread:
    threadMap = {}
    def __init__(self, sid, thread, width, height, n, i, gridx, gridy):
        self.isRunning = thread.isAlive
        self.sessionid = sid
        self.thread = thread
        self.data = SimData()   
        self.width = width
        self.height = height
        self.n = n
        self.i = i
        self.gridx = gridx
        self.gridy = gridy

    def stop(self):
        self.isRunning = False 
        print ("Stopping %s"%self.sessionid)


        
    def vizUpdateLoop(self, ct):

        
        #global stopViz
        #prevDay = -1
        day = -1
        while True:  
        
            try:
                day = self.data.dayQueue.get_nowait()
            except queue.Empty:
                pass

            try:
                if not day is -1:
                    self.data.stopViz = not self.data.vm.update(day)        
                if not self.data.stopViz and not day is -1:
                    self.data.vm.updateTitle("Visualization Day %d" % day)
            except:
                print("Renderer threw an exception")     
            if self.data.stopViz:
                print("Exiting Renderer")
                break

        
        
    # pygame.display.set_caption("Visualization Day %d %s" % (day, "(Paused)" if simpaused else "" ))
    # pygame.display.update()

# Initialize visualization
#stopViz = False
def initVisualization(args):
    # # pygame.init()
    # global simpaused
    # simpaused = False

    #print('%s',SimThread.threadMap.keys())
    ct = getCurrentThreadName()
    
    
    # global simdata
    # simdata = {}
    # global vm
    # vm =  = viz.VizMap(1024, 768, 6, 6, simdata, 2, "safety", "health", renderer='web')
    # global dayQueue
    # dayQueue= queue.Queue()
    # global stopViz
    # stopViz = False

    getLock()
    try:
        currentSimThreadObject = SimThread.threadMap[ct]
    except:
        print ("Error init visualization")
    finally:
        releaseLock()

    vm = viz.VizMap(1024, 768, 6, 6, currentSimThreadObject.data.simdata, 2, "safety", "health", renderer='web')
    currentSimThreadObject.data.vm  = vm

    
    
def addDayToQueue(day):
    ct = getCurrentThreadName()
    getLock()
    currentSimThreadObject = SimThread.threadMap[ct]
    releaseLock()
    currentSimThreadObject.data.dayQueue.put(day)
    currentSimThreadObject.data.maxDay = day


def addToIndividualList(entry):
    ct = getCurrentThreadName()
    #print ("Individual Entry %s"%entry)
    getLock()
    currentSimThreadObject = SimThread.threadMap[ct]
    releaseLock()
    currentSimThreadObject.data.vm.individualList.append(viz.Individual(entry['x'], entry['y'], viz.SimColor.GRAY,
                                            entry['participant'], currentSimThreadObject.data.vm, entry['region']))
    

def closeViz():
    ct = getCurrentThreadName()
    getLock()
    currentSimThreadObject = SimThread.threadMap[ct]
    releaseLock()
    currentSimThreadObject.data.stopViz = True

def addToVizData(keyname, entry):
    #print('%s Entry %s'%(keyname, entry))

    ct = getCurrentThreadName()

    getLock()
    currentSimThreadObject = SimThread.threadMap[ct]
    releaseLock()

    if not keyname in currentSimThreadObject.data.simdata:
        currentSimThreadObject.data.simdata[keyname] = {}

    headervalues = list(entry.keys())
    values = list(entry.values())
    entityname = values[1]
    simday = int(values[0])
    
    if not simday in currentSimThreadObject.data.simdata[keyname]:
        currentSimThreadObject.data.simdata[keyname][simday] = {}
    
    
    if not entityname in currentSimThreadObject.data.simdata[keyname][simday]:
        currentSimThreadObject.data.simdata[keyname][simday][entityname] = {}

    # for h in range(2,len(headervalues)):
    #     currentSimThreadObject.data.simdata[keyname][simday][entityname][headervalues[h]] = []

    entityname = list(entry.values())[1]
    for cntr in range (2, len(entry)):
        
        #currentSimThreadObject.data.simdata[keyname][simday][entityname][headervalues[cntr]].append(values[cntr])
        currentSimThreadObject.data.simdata[keyname][simday][entityname][headervalues[cntr]] = values[cntr]


        
def vizUpdateLoop():
    ctn = getCurrentThreadName()
    childtn = ctn.replace('-consumer','')
    #print ("Updating Visualization %s"%ctn)
    #SimThread.threadMap[childtn].vizUpdateLoop(childtn)