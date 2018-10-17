#!/usr/bin/python
import sys
import pygame
import random

def handleInput():

    keys = pygame.key.get_pressed()
    pass

class Individual:
#day	participant	gender	age	ethnicity	#children	region	alive	shelter	evacuated	risk	health	grievance
#0	0001	male	38	majority	2	Region01	True	False	False	5	5	2
    def __init__(self, x, y, color, id):
        self.id = id
        self.starcolor = color
        self.percentxpos = float(x)
        self.percentypos = float(y)
        pass

    def update(self, currentDay, currentPropIndividual, vm):
        individualname = "%04d" % (self.id)

        name = vm._simdata["actors"][currentDay-1][individualname]["region"]

        r = vm.getRegion(name)
        if r is None:
            print ("Cant find region %s" %name)
            return
        #print("Drawing circle %d at %f, %f in region %s" %( int(self.id), r.x, r.y, self.id) )
        value = vm._simdata["actors"][currentDay-1][individualname][currentPropIndividual]

        color = SimColor.getColorForValue(value[0]) #1 to 5 => 0 to 1
        #hack to draw filled circle with black border
        circle = pygame.draw.circle(vm._win, (0, 0, 0), (int(r.x + r.width * self.percentxpos), int(r.y + r.height * self.percentypos)), 7, 2)
        circle = pygame.draw.circle(vm._win, color, (int(r.x + r.width * self.percentxpos), int(r.y + r.height * self.percentypos)), 6, 0)
        
class Neighborhood:
    def __init__(self, x, y, width, height, color, id):
        self.id = id
        #self.props = {'casualties':[], 'risk':[]}
        self.startcolor = color
        self.x = x + 1
        self.y = y + 1  
        self.width = width - 2
        self.height = height - 2

        #for i in range(0, numOfDays):
        #    self.props['casualties'].append(random.randrange(0,100,1)/100.0)
        #    self.props['risk'].append(random.randrange(0,100,1) / 100.0 )
        
    def update(self, currentDay, currentPropRegion, vm):
        if self.id < 0:
            rect = pygame.draw.rect(vm._win, self.startcolor, (self.x, self.y, self.width, self.height))
            return
        regionname = "Region%02d" % self.id
        if regionname in vm._simdata["regions"][currentDay-1]:
            value = vm._simdata["regions"][currentDay-1][regionname][currentPropRegion]
            #print ("Day ", currentDay, " Neighborhood ", regionname, "Property ", self.currentProp, "Value", value[0])
            #print (currentDay - 1, "\t", regionname, "\t", value[0], "\t",         )
            if vm._showActors == 1 :
                self.color = SimColor.DGRAY
            else:
                self.color = SimColor.getColorForValue(float(value[0]))

            rect = pygame.draw.rect(vm._win, self.color, (self.x, self.y, self.width, self.height))

            #mouse over code below
            # if rect.collidepoint(pygame.mouse.get_pos()):
            #     s = pygame.Surface((self.width,self.height), pygame.SRCALPHA)
            #     s.set_alpha(127)
            #     s.fill((127, 127, 127))                        
            #     win.blit(s, (self.x, self.y))  

class SimColor:
    RED = (255,0,0)
    LIGHTBLUE = (66,206,244)
    BROWN = (101, 67, 33)
    ORANGE = (255,165,0)
    YELLOW = (255,255,0)
    LGREEN = (0,127,0)
    GREEN = (0,255,0)
    GRAY = (127, 127, 127)
    WHITE = (255, 255, 255)
    BLACK = (0, 0, 0)
    DGRAY = (65, 65, 65)
    LGRAY = (200, 200, 200)

    
    @classmethod
    def getColorForValue(cls,val):
        #test Green to Red
        #temp = float(numOfDays - currentDay) / float(numOfDays)
        #myColor = ( min(255, 255 * 2.0 * (1 - temp)),min(255,255 * 2.0 * temp), 0)
#        myColor = ( min(255, 255 * 2.0 * (1 - val)),min(255,255 * 2.0 * val), 0)
        myColor = ( 255. * (1.-val),255. * val, 32)
        return myColor
        # if val <= 0.2:
        #     return cls.RED
        # elif val <= 0.4:
        #     return cls.ORANGE
        # elif val <= 0.6:
        #     return  cls.YELLOW
        # elif val <= 0.8:
        #     return cls.LGREEN
        # elif val <= 1.0:
        #     return cls.GREEN

class VizMap:


    def pygameInit(self):
        pygame.display.set_caption("Visualization")

    def __init__(self, sWidth, sHeight, numxgrid, numygrid, simdata, showActors, displayTableFileName, win, currentPropRegion, currentPropIndividual):
        
        self._sWidth = sWidth
        self._sHeight = sHeight 
        self._numxgrid = numxgrid 
        self._numygrid = numygrid
        self._simdata = simdata
        self._showActors = showActors
        self._displayTableFileName = displayTableFileName
        self._currentPropIndividual = currentPropIndividual
        self._currentPropRegion = currentPropRegion
        self._win = win
        self.pygameInit()
        self.regionList = self.getRegions() 
        self.individualList = self.getIndividuals()

    def getRegion(self, name):
        # 
        # print ("Looking for region %s" %(name[0]))

        for r in self.regionList:
            regionname = "Region%02d" % r.id
            
            if regionname == name[0]:
                return r

        return None
                
              
    def getRegions(self):
        rl = []
        id = 0
        for i in range(self._numxgrid):
            for j in range(self._numygrid):
                if i == 0:
                    rl.append(Neighborhood(i*self._sWidth/self._numxgrid, j*self._sHeight/self._numygrid, self._sWidth/self._numxgrid, self._sHeight/self._numygrid, SimColor.LIGHTBLUE,-1))
                    continue
                if j == 0 or i == self._numxgrid - 1 or j == self._numygrid - 1:
                    rl.append(Neighborhood(i*self._sWidth/self._numxgrid, j*self._sHeight/self._numygrid, self._sWidth/self._numxgrid, self._sHeight/self._numygrid, SimColor.BROWN, -2))
                    continue
                id+=1
                rl.append(Neighborhood(i*self._sWidth/self._numxgrid, j*self._sHeight/self._numygrid, self._sWidth/self._numxgrid, self._sHeight/self._numygrid, SimColor.GRAY,id))
        #rl.append(Neighborhood(50, 50, 200, 175, SimColor.RED))
        #rl.append(Neighborhood(250, 25, 100, 150, SimColor.GREEN))
        #rl.append(Neighborhood(100, 225, 150, 200, SimColor.YELLOW))
        #rl.append(Neighborhood(250, 175, 200, 200, SimColor.ORANGE))
        return rl
    
    def getIndividuals(self):
        iL = []
#day	participant	gender	age	ethnicity	#children	region	alive	shelter	evacuated	risk	health	grievance
#0	0001	male	38	majority	2	Region01	True	False	False	5	5	2
        header = True
        if not self._displayTableFileName == "":
            with open(self._displayTableFileName) as f:
                lines = f.readlines()
                for line in lines:
                    line = line.rstrip('\n')
                    values = line.split('\t')
                    if header == True:
                        header = False
                        headervalues = values
                    #print ("Header created")
                        continue
                    iL.append(Individual(values[2], values[3], SimColor.GRAY, int(values[1])))
        return iL

    def update(self, currentDay):
        self._win.fill((0,0,0))
        for r in self.regionList:
            r.update(currentDay, self._currentPropRegion, self)
        
        if self._showActors > 0:
            for i in self.individualList:
                i.update(currentDay, self._currentPropIndividual, self)


def main(argv):
    global currentDay
    global numOfDays
    global win
    global sWidth
    global sHeight
    global simdata
    global currentPropRegion
    global currentPropIndividual
    global numxgrid
    global numygrid
    global vm
    global showActors
    global displayTableFileName


    # parser = ArgumentParser()
    # parser.add_argument('-w','--screenwidth',default='WARNING',type-=int,help='Resolution Width')
    # parser.add_argument('-h','--screenheight',default=1,type=int,help='Resolution Height')
    # parser.add_argument('-s','--speed',default=1,type=int,help='Number of runs to run')
    # parser.add_argument('-x','--gridx',action='store_true',help='Profile simulation step')

    # parser.add_argument('-y','--gridy',default=1,type=int,help='Instance number')
    # parser.add_argument('-c','--compile',action='store_true',help='Pre-compile agent policies')
    # args = vars(parser.parse_args())



    usage = "python.exe .\\viz.py 1024 768 1 7 7 .\data2\RegionTable safety .\data2\ActorsTable health .\data2\DisplayTable 0"
    print(usage)

    currentDay = 1 
    numOfDays = 10
    showActors = 0

    sWidth = 1024
    sHeight = 768
    speed = 1.0
    updateInterval = 1000

    displaylayer="Region"
    displayproperty ="Safety"
    

    numxgrid = 7
    numygrid = 7

    if len(argv) >= 3:
        sWidth = int(argv[1])
        sHeight = int(argv[2])

    if len(argv) >= 4:
        speed = float(argv[3])

    if len(argv) >=6:
        numxgrid = int(argv[4])
        numygrid = int(argv[5])
    
    if len(argv) >=7:
        regionFileName = argv[6]
    else:
        regionFileName = "data\RegionTable"
    if len(argv) >=8:
        currentPropRegion = argv[7]
    
        
    else:
        currentPropRegion = 'safety'

    if len(argv) >=9:
        individualFileName = argv[8]
    else:
        regionFileName = "data\ActorsTable"

    

    if len(argv) >=10:
        currentPropIndividual = argv[9]
    else:
        currentPropIndividual = 'risk'

    if len(argv) >=11:
        displayTableFileName = argv[10]
    else:
        displayTableFileName = ''
    
    if len(argv) >= 12:
        showActors = int(argv[11])
        if  showActors == 0:        
            displaylayer = "Regions"
            displayproperty = currentPropRegion    
        if  showActors == 1:        
            displaylayer = "Actors"
            displayproperty = currentPropIndividual
        if  showActors == 2:   
            displaylayer = "Regions and Actors"
            displayproperty = currentPropIndividual
            displayproperty = currentPropRegion
    else:
        showActors = 2
        displaylayer = "Regions and Actors"
        displayproperty = currentPropIndividual
        displayproperty = currentPropRegion

    
    

    win = pygame.display.set_mode((sWidth, sHeight))

    pygame.init()

    run = True
    i = 0
    totalrecords = 0
    simdata = {}
    simdata["actors"] = []
    simdata["regions"] = []

    vm = VizMap(sWidth, sHeight, numxgrid, numygrid, simdata, showActors, displayTableFileName, win, currentPropRegion, currentPropIndividual)

    numOfDays =  readfile(regionFileName, "regions")
    if not individualFileName is "":
        readfile(individualFileName, "actors")
    # i  = 0
    # for daydata in simdata:
    #     i+=1
    #     print("day ", i)
    #     print (n_data)

    pygame.time.delay(2000)
    i = 0.0
    while run:
        pygame.time.delay(100)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                run = False

        handleInput()
        vm.update(currentDay)        

        if i == 0.0:
            pygame.display.set_caption("Visualization Day %d Layer: %s Property: %s" % (currentDay, displaylayer , displayproperty))
            if currentDay < numOfDays :
                currentDay += 1
            else: 
                currentDay = 1
                exit(0)
        if i < 10.0 / speed: 
            i += 1.0
        else:
            i = 0.0

        pygame.display.update()


def readfile(filename, keyname):
    simday = -1
    with open(filename) as f:
        daydata = {}
        lines = f.readlines()
        totalrecords = len(lines)
        #print(lines)
        header = True
        headervalues = []
        for line in lines:
            line = line.rstrip('\n')
            values = line.split('\t')
            #print(line)
            # print ("VALUES",values)

            if header == True:
                header = False
                headervalues = values
                #print ("Header created")
                continue

            #print (values[0])  
            if simday != int(values[0]):
                simday = int (values[0])
                simdata[keyname].append({})
                #print ("DayChanged")
            
            if values[1] in simdata[keyname][simday].keys():
                #print ("Key exists")
                pass
            else:
                #print ("Key does not exist")
                #print (headervalues)
                simdata[keyname][simday][values[1]] = {}
                for h in range(2,len(headervalues)):
                    simdata[keyname][simday][values[1]][headervalues[h]] = [] #{ headervalues[2] : [], headervalues[3] : [],headervalues[4] : [],headervalues[5] : []}

            # print (simdata)
            # print (simday)
            # print (values[1])
           # print (simdata[simday])
            #day	region	casualties	evacuated	shelter	risk
            for cntr in range(2,len(values)):

                simdata[keyname][simday][values[1]][headervalues[cntr]].append(values[cntr])

    return simday


if __name__ == "__main__":
    #print len(sys.argv)
    #print sys.argv
    main(sys.argv)
