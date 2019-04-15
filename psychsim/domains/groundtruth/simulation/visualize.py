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


class SimThread:
    threadMap = {}
    def __init__(self, sid, thread):
        self.isRunning = thread.isAlive
        self.sessionid = sid
        self.thread = thread
        self.data = SimData()

    def stop(self):
        self.isRunning = False 
        print ("Stopping %s"%self.sessionid)


        
    def vizUpdateLoop(self, ct):

        
        #global stopViz
        #prevDay = -1
        day = -1
        while True:  
        
            try:
                day = SimThread.threadMap[ct].data.dayQueue.get_nowait()
            except queue.Empty:
                pass

            try:
                if not day is -1:
                    SimThread.threadMap[ct].data.stopViz = not SimThread.threadMap[ct].data.vm.update(day)        
                if not SimThread.threadMap[ct].data.stopViz and not day is -1:
                    SimThread.threadMap[ct].data.vm.updateTitle("Visualization Day %d" % day)
            except:
                print("Renderer threw an exception")     
            if SimThread.threadMap[ct].data.stopViz:
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
        vm = viz.VizMap(1024, 768, 6, 6, SimThread.threadMap[ct].data.simdata, 2, "safety", "health", renderer='pygame')
        SimThread.threadMap[ct].data.vm  = vm

    except:
        print ("Error init visualization")
    finally:
        releaseLock()
    
    
def addDayToQueue(day):
    ct = getCurrentThreadName()
    getLock()

    SimThread.threadMap[ct].data.dayQueue.put(day)
    releaseLock()


def addToIndividualList(entry):
    ct = getCurrentThreadName()
    #print ("Individual Entry %s"%entry)
    getLock()

    SimThread.threadMap[ct].data.vm.individualList.append(viz.Individual(entry['x'], entry['y'], viz.SimColor.GRAY,
                                            entry['participant'], SimThread.threadMap[ct].data.vm, entry['region']))
    releaseLock()

def closeViz():
    ct = getCurrentThreadName()
    getLock()

    SimThread.threadMap[ct].data.stopViz = True
    releaseLock()

def addToVizData(keyname, entry):
    #print('%s Entry %s'%(keyname, entry))

    ct = getCurrentThreadName()

    getLock()

    if not keyname in SimThread.threadMap[ct].data.simdata:
        SimThread.threadMap[ct].data.simdata[keyname] = {}

    headervalues = list(entry.keys())
    values = list(entry.values())
    entityname = values[1]
    simday = int(values[0])
    
    if not simday in SimThread.threadMap[ct].data.simdata[keyname]:
        SimThread.threadMap[ct].data.simdata[keyname][simday] = {}
    
    
    if not entityname in SimThread.threadMap[ct].data.simdata[keyname][simday]:
        SimThread.threadMap[ct].data.simdata[keyname][simday][entityname] = {}

    # for h in range(2,len(headervalues)):
    #     SimThread.threadMap[ct].data.simdata[keyname][simday][entityname][headervalues[h]] = []

    entityname = list(entry.values())[1]
    for cntr in range (2, len(entry)):
        
        #SimThread.threadMap[ct].data.simdata[keyname][simday][entityname][headervalues[cntr]].append(values[cntr])
        SimThread.threadMap[ct].data.simdata[keyname][simday][entityname][headervalues[cntr]] = values[cntr]

    releaseLock()

        
def vizUpdateLoop():
    ctn = getCurrentThreadName()
    childtn = ctn.replace('-consumer','')
    print ("Updating Visualization %s"%ctn)
    #SimThread.threadMap[childtn].vizUpdateLoop(childtn)