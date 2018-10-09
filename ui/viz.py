#!/usr/bin/python
import sys
import pygame
import random
from argparse import ArgumentParser

def handleInput():

    keys = pygame.key.get_pressed()
    pass

class Individual:
#day	participant	gender	age	ethnicity	#children	region	alive	shelter	evacuated	risk	health	grievance
#0	0001	male	38	majority	2	Region01	True	False	False	5	5	2
    def __init__(self, x, y, color, id, region = None):
        self.id = id
        self.starcolor = color

        self.percentxpos = float(x)
        self.percentypos = float(y)
        self.region = region
        pass



    def update(self, currentDay, currentPropIndividual, vm):
        
        individualname = self.id

        #if not individualname == 'Actor0001':        
        #    return

        if self.region is None or self.percentxpos == -1 or self.percentypos == -1:
            return

        if self.region != '': 
            r = vm.getRegion(self.region)
        else:
            return

        if r is None:
            print ("Cant find region %s" %self.region)
            return
        #print("Drawing circle %d at %f, %f in region %s" %( int(self.id), r.x, r.y, self.id) )
        value = vm._simdata["Actor"][currentDay-1][individualname][currentPropIndividual]

        color = SimColor.getColorForValue(float(value)) #1 to 5 => 0 to 1

        #print ("individual %s region %s x %f y %f value %f color %s"%(individualname, self.region, self.percentxpos, self.percentypos, float(value), color))

        #hack to draw filled circle with black border
        pygame.draw.circle(vm._win, (0, 0, 0), (int(r.x + r.width * self.percentxpos), int(r.y + r.height * self.percentypos)), 7, 2)
        pygame.draw.circle(vm._win, color, (int(r.x + r.width * self.percentxpos), int(r.y + r.height * self.percentypos)), 6, 0)
        
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
        #if regionname == 'Region11':
        #    return
        
        try:
            value = vm._simdata["Region"][currentDay-1][regionname][currentPropRegion]
            #print ("regions CURRENTDAY %d REGIONNAME %s PROPERTY %s VALUE %f" %(currentDay - 1, regionname, currentPropRegion, float(value)))

        except:
            #print ("regions CURRENTDAY %d REGIONNAME %s PROPERTY %s" %(currentDay - 1, regionname, currentPropRegion))
            return
        
        #print ("Day ", currentDay, " Neighborhood ", regionname, "Property ", self.currentProp, "Value", value[0])
        #print (currentDay - 1, "\t", regionname, "\t", value[0], "\t",         )
        if vm._showActors == 1 :
            self.color = SimColor.DGRAY
        else:
            self.color = SimColor.getColorForValue(1.0 - float(value)) #temp for inverting safety to risk

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
        myColor = ( min(255, 255 * 2.0 * (1 - val)),min(255,255 * 2.0 * val), 0)
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
        self.individualList = [] #self.getIndividuals()

    def getRegion(self, name):
        # 
        # print ("Looking for region %s" %(name[0]))

        for r in self.regionList:
            regionname = "Region%02d" % r.id
            
            if regionname == name:
                return r

        return None
                
              
    def getRegions(self):
        rl = []
        id = 0
        numcols = self._numxgrid
        numrows = self._numygrid
        for j in range(numcols):
            for i in range(numrows):
                if i == 0:
                    rl.append(Neighborhood(i*self._sWidth/numcols, j*self._sHeight/numrows, self._sWidth/numcols, self._sHeight/numrows, SimColor.LIGHTBLUE,-1))
                    continue
                if j == 0 or i == numcols - 1 or j == numrows - 1:
                    rl.append(Neighborhood(i*self._sWidth/numcols, j*self._sHeight/numrows, self._sWidth/numcols, self._sHeight/numrows, SimColor.BROWN, -2))
                    continue
                id+=1
                rl.append(Neighborhood(i*self._sWidth/numcols, j*self._sHeight/numrows, self._sWidth/numcols, self._sHeight/numrows, SimColor.GRAY,id))

        return rl


    def updateXPos(self, actor, x):

        for i in self.individualList:
            if actor == i.id:
                i.percentxpos = x
                return
        
        #reaching here indicates actor is not yet in the list
        self.individualList.append(Individual(x, -1, SimColor.GRAY, actor))

        
    def updateYPos(self, actor, y):
        for i in self.individualList:
            if actor == i.id:
                i.percentypos = y
                return
        #reaching here indicates actor is not yet in the list

        self.individualList.append(Individual(-1, y, SimColor.GRAY, actor))


    def updateRegion(self, actor, region):
        for i in self.individualList:
            if actor == i.id:
                i.region = region
                return
        #reaching here indicates actor is not yet in the list
        self.individualList.append(Individual(-1, -1, SimColor.GRAY, actor, region))

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
            for ind in self.individualList:
                
                ind.update(currentDay, self._currentPropIndividual, self)


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


    parser = ArgumentParser()
    parser.add_argument('-sw','--screenWidth',default=1024,type=int,help='Resolution Width')
    parser.add_argument('-sh','--screenHeight',default=768,type=int,help='Resolution Height')
    parser.add_argument('-s','--speed',default=1,type=int,help='visualization speed')
    parser.add_argument('-c','--cols',default=7,help='colums in grid')
    parser.add_argument('-r','--rows',default=7,type=int,help='rows in grid')
    parser.add_argument('-ap','--actorProperty',default='health',type=str,help='actor property to display')
    parser.add_argument('-rp','--regionProperty',default='safety',type=str,help='region propery to display')
    parser.add_argument('-dl','--displayLayer',default=2,type=int,help='0 = regions, 1 = actors, 2 = both')
    parser.add_argument('-fn','--fileName',default='d:/groundtruth/data/rundatatable',type=str,help='simulation file name')

    args = vars(parser.parse_args())



    usage = "python.exe .\\viz.py -w 1024 -h 768 -s 1 -c 7 -r 7 -rp safety -ap health -dl 0 -fn d:/groundtruth/data/rundatatable"
    print(usage)

    currentDay = 1 
    numOfDays = 10
    showActors = 0

    sWidth = 1024
    sHeight = 768
    speed = 1.0
    updateInterval = 1000
    numxgrid = 7
    numygrid = 7

    displaylayer="Region"
    
    
    sWidth = int(args['screenWidth'])
    sHeight = int(args['screenHeight'])

    speed = int(args['speed'])

    numxgrid = int(args['cols'])
    numygrid = int(args['rows'])

    currentPropIndividual = args['actorProperty']
    currentPropRegion = args['regionProperty']
    
    showActors = int(args['displayLayer'])
    combinedFileName = args['fileName']

    # if len(argv) >= 3:
    #     sWidth = int(argv[1])
    #     sHeight = int(argv[2])

    # if len(argv) >= 4:
    #     speed = float(argv[3])

    # if len(argv) >=6:
    #     numxgrid = int(argv[4])
    #     numygrid = int(argv[5])
    
    # if len(argv) >=7:
    #     regionFileName = argv[6]
    # else:
    #     regionFileName = "data\RegionTable"
    # if len(argv) >=8:
    #     currentPropRegion = argv[7]
    
        
    # else:
    #     currentPropRegion = 'safety'

    # if len(argv) >=9:
    #     individualFileName = argv[8]
    # else:
    #     regionFileName = "data\ActorsTable"

    

    # if len(argv) >=10:
    #     currentPropIndividual = argv[9]
    # else:
    #     currentPropIndividual = 'risk'

    # if len(argv) >=11:
    #     displayTableFileName = argv[10]
    # else:
    #     displayTableFileName = ''
    
    displayTableFileName = ''

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
 

    
    # if len(argv) >= 13:
    #     combinedFileName = argv[12]

    win = pygame.display.set_mode((sWidth, sHeight))

    pygame.init()

    run = True
    i = 0
    totalrecords = 0
    simdata = {}
    simdata["Actor"] = []
    simdata["Region"] = []

    vm = VizMap(sWidth, sHeight, numxgrid, numygrid, simdata, showActors, displayTableFileName, win, currentPropRegion, currentPropIndividual)

    if not combinedFileName is "" :
        print ("Reading %s" %combinedFileName)
        numOfDays = readfile(combinedFileName, "")
    else:
        print ("No file specified")

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
            pygame.display.set_caption("Visualization Day %d Layer: %s Actor Property: %s Region Property %s" % (currentDay, displaylayer , currentPropIndividual, currentPropRegion))
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

    #read alternate sim file format
    with open(filename) as f:
        daydata = {}
        lines = f.readlines()
        
        totalrecords = len(lines)
        headervalues = []
        values = []
        isHeader = True
        for line in lines:
            if isHeader:
                headervalues = line.rstrip('\n').split('\t')
                isHeader = False
                #print (headervalues)
            else:
                values = line.rstrip('\n').split('\t')
                #print (values)

                valueDay = values[0]
                if valueDay == "":
                    continue
                splitValue1 = values[1].split(' ')
                if len(splitValue1) is 2: 
                    valueKey = values[1].split(' ')[0]
                    valueProp = values[1].split(' ')[1]

                    #print ("VK %s VP %s" %(valueKey, valueProp))
                else:
                    #print("No Split %s" %values)
                    continue
                valueEntityId = values[2]
                valueValue = values[3]
                valueNotes = values[4]
                #id = -1

                if  not valueKey in simdata.keys():
                    simdata[valueKey] = []

                keyname = valueKey
              
                if  valueKey != "Actor" and valueKey != "Region": #skipping everything but Actor and Region entries
                    #print ("Keyname is not Actor or Regiobootn ... skipping %s" %values)
                    continue

                if simday != int(valueDay):
                    try:
                        simday = (int)(valueDay) - 1
                        #print ("Simday%d " %simday)
                    except:
                        #print ("Simday error %s" %values)
                        continue           
                    #print ("KeyName %s %s" %(valueKey, values))

                    simdata[valueKey].append({})
                    #print ("DayChanged Simdata Keyname%s %s"%(valueKey,simdata[valueKey]))

                #print ("Length of %s is %d " %(simdata[valueKey], len(simdata[valueKey])))
                #print ("Simday is %d" % simday)
                if valueEntityId in simdata[valueKey][simday].keys():
                    pass
                else:

                    simdata[valueKey][simday][valueEntityId] = {}
                    

                simdata[valueKey][simday][valueEntityId][valueProp] = valueValue

                # if (valueKey == 'regions' and valueProp == 'risk') or (valueKey == 'actors' and valueProp == 'health'):
                #     print ("%s %d %s %s %f" %(valueKey, simday, valueEntityId, valueProp, float(valueValue)))
                
                if valueKey == 'Actor': # handle region, x, y changes and update actor list
                    if valueProp == 'region': 
                        vm.updateRegion(valueEntityId, valueValue)                            

                    if valueProp == 'x':
                        vm.updateXPos(valueEntityId, float(valueValue))                            
                        
                    if valueProp == 'y':
                        vm.updateYPos(valueEntityId, float(valueValue))                            	

    return simday


if __name__ == "__main__":
    #print len(sys.argv)
    #print sys.argv
    main(sys.argv)