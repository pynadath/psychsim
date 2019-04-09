import sys
import os
import random
from argparse import ArgumentParser
from psychsim.ui import gtrenderers

class Individual:
    def __init__(self, x, y, color, id, vm, region = None):
        self.id = id
        self.starcolor = color
        self.percentxpos = float(x)
        self.percentypos = float(y)
        self.region = region
        self.vm = vm
        pass

    def update(self, currentDay, currentPropIndividual):
        individualname = self.id
        if self.region is None or self.percentxpos == -1 or self.percentypos == -1:
            print ("Returning. Self.region %s %d %d "%(self.region, self.percentxpos, self.percentypos))
            return

        if self.region != '': 
            r = self.vm.getRegion(self.region)
        else:
            print ("No region")
            return

        if r is None:
            print ("Cant find region %s" %self.region)
            return
        #print("Drawing circle %s at %f, %f in region %s current day %s individual name %s currentPropIndividual %s" %(self.id, r.x, r.y, self.region, currentDay, individualname, currentPropIndividual ) )

        value = self.vm._simdata["Actor"][currentDay][individualname][currentPropIndividual]

        fValue = float(value) if self.vm.invertActorProp is False else  1-float(value)
        color = SimColor.getColorForValue(fValue) #1 to 5 => 0 to 1
        self.vm.renderer.DrawCircle(int(r.x + r.width * self.percentxpos), int(r.y + r.height * self.percentypos), 6, color)

class Neighborhood:
    def __init__(self, x, y, width, height, color, id, vm):
        self.id = id
        #self.props = {'casualties':[], 'risk':[]}
        self.startcolor = color
        self.x = x + 1
        self.y = y + 1  
        self.width = width - 2
        self.height = height - 2
        self.vm = vm

    def update(self, currentDay, currentPropRegion):
        if self.id == '':
            self.vm.renderer.DrawRectangle(self.x, self.y, self.width, self.height, self.startcolor)
            return
        regionname = self.id

        try:
            value = self.vm._simdata["Region"][currentDay][regionname][currentPropRegion]
            #print ("regions CURRENTDAY %d REGIONNAME %s PROPERTY %s VALUE %f" %(currentDay, regionname, currentPropRegion, float(value)))
        except:
            print ("error regions CURRENTDAY %d REGIONNAME %s PROPERTY %s" %(currentDay, regionname, currentPropRegion))
            return
        fValue = float(value) if self.vm.invertRegionProp is False else  1-float(value)
        
        if self.vm._showActors == 1 :
            self.color = SimColor.DGRAY
        else:
            self.color = SimColor.getColorForValue(fValue)

        self.vm.renderer.DrawRectangle(self.x, self.y, self.width, self.height, self.color)

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
        myColor = ( min(255, 255 * 2.0 * (1 - val)),min(255,255 * 2.0 * (val)), 0)
        return myColor

class VizMap:

    def __init__(self, sWidth, sHeight, numxgrid, numygrid, simdata, showActors, currentPropRegion, currentPropIndividual, invertRegionProp=False, invertActorProp = False, renderer = 'pygame'):
        
        self._sWidth = sWidth
        self._sHeight = sHeight 
        self._numxgrid = numxgrid 
        self._numygrid = numygrid
        self._simdata = simdata
        self._showActors = showActors
#        self._displayTableFileName = displayTableFileName
        self._currentPropIndividual = currentPropIndividual
        self._currentPropRegion = currentPropRegion
        self.regionList = self.getRegions() 
        self.individualList = [] 
        self.invertRegionProp = invertRegionProp
        self.invertActorProp = invertActorProp
        self.renderer = gtrenderers.PyGameRenderer(sWidth, sHeight) if renderer == 'pygame' else gtrenderers.PixiRenderer(self) 

    def getRegion(self, name):
        # print ("Looking for region %s" %(name[0]))
        for r in self.regionList:
            if r.id == name:
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
                    rl.append(Neighborhood(i*self._sWidth/numcols, j*self._sHeight/numrows, self._sWidth/numcols, self._sHeight/numrows, SimColor.LIGHTBLUE,'', self))
                    continue
                if j == 0 or i == numcols - 1 or j == numrows - 1:
                    rl.append(Neighborhood(i*self._sWidth/numcols, j*self._sHeight/numrows, self._sWidth/numcols, self._sHeight/numrows, SimColor.BROWN, '', self))
                    continue
                id+=1
                rl.append(Neighborhood(i*self._sWidth/numcols, j*self._sHeight/numrows, self._sWidth/numcols, self._sHeight/numrows, SimColor.GRAY, "Region%02d"%id, self))

        return rl

    def updateXPos(self, actor, x):
        for i in self.individualList:
            if actor == i.id:
                i.percentxpos = x
                return
        #reaching here indicates actor is not yet in the list
        self.individualList.append(Individual(x, -1, SimColor.GRAY, actor, self))
        
    def updateYPos(self, actor, y):
        for i in self.individualList:
            if actor == i.id:
                i.percentypos = y
                return
        #reaching here indicates actor is not yet in the list
        self.individualList.append(Individual(-1, y, SimColor.GRAY, actor, self , None))

    def updateRegion(self, actor, region):
        for i in self.individualList:
            if actor == i.id:
                i.region = region
                return
        #reaching here indicates actor is not yet in the list
        self.individualList.append(Individual(-1, -1, SimColor.GRAY, actor, self, region))

    def updateTitle(self, title):
        self.renderer.setCaption(title)
    
    def update(self, currentDay):
        self.renderer.preUpdate()

        if currentDay is not -1:
            for r in self.regionList:
                #print (r.id)
                r.update(currentDay, self._currentPropRegion)

            if self._showActors > 0:
                for ind in self.individualList:
                    #print("Individual = %s %s " %( type(ind.id) , ind.id))
                    ind.update(currentDay, self._currentPropIndividual)
            currentDay += 1
            try:

                if 'hurricane' in self._simdata:                 
                    
                    if (currentDay in self._simdata['hurricane']):
                        for hName in self._simdata['hurricane'][currentDay]:
                            region = self._simdata['hurricane'][currentDay][hName]['Location']
                            category = int(self._simdata['hurricane'][currentDay][hName]['Category'])
                            bLanded = True if self._simdata['hurricane'][currentDay][hName]['Landed'] == 'yes' else False
                            bLeaving = True if region == 'leaving' else False
                            imageDim = 20 + 10 * category
                            r = self.getRegion(region)
                            if not bLeaving:
                                if not bLanded:
                                    self.renderer.DrawImage(int(r.x + (r.width + imageDim) * -0.5), int(r.y + (r.height-imageDim) * 0.5), category, imageDim, imageDim)
                                else :
                                    self.renderer.DrawImage(int(r.x + (r.width - imageDim) * 0.5), int(r.y + (r.height - imageDim) * 0.5), category, imageDim, imageDim)
                            else:
                                # if leaving find where it was previous day and turn green
                                region = self._simdata['hurricane'][currentDay - 1][hName]['Location']
                                r = self.getRegion(region)
                                exitId = self.getExitRegion(int(r.id.replace("Region","")))
                                if exitId in [0,1,7]:
                                    self.renderer.DrawImage(int(r.x + (r.width - imageDim) * 0.5), int(r.y + (r.height + imageDim) * -0.5), category, imageDim, imageDim)
                                if exitId in [3,4,5]:
                                    self.renderer.DrawImage(int(r.x + (r.width - imageDim) * 0.5), int(r.y  + r.height + (r.height - imageDim) * 0.5), category, imageDim, imageDim)
                                if exitId in [2]:
                                    self.renderer.DrawImage(int(r.x + r.width + (r.width - imageDim) * 0.5), int(r.y + (r.height - imageDim) * 0.5), category, imageDim, imageDim)
                                if exitId in [6]:
                                    self.renderer.DrawImage(int(r.x + (r.width + imageDim) * - 0.5), int(r.y + (r.height - imageDim) * 0.5), category, imageDim, imageDim)
            except:
                print("Exception - while rendering hurricane. %d %s " %(currentDay, self._simdata['hurricane']))

        return self.renderer.update()

    def getExitRegion(self, id):
        x = self._numxgrid - 2
        y = self._numygrid - 2

        if id == 1:
            return 7 #NW
        if id == x:
            return 1 #NE
        if id == x * y:
            return 3 #SE
        if id == x * (y - 1) + 1:
            return 5 #SW
        if id < x:
            return 0 #N
        if id % y == 0:
            return 2 #E
        if id % y == 1:
            return 6 #W
        if id > x * (y-1):
            return 4

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
    parser.add_argument('-api','--actorPropertyInverted', action='store_true',help='actor property to be inverted')
    parser.add_argument('-rp','--regionProperty',default='safety',type=str,help='region propert y to display')
    parser.add_argument('-rpi','--regionPropertyInverted',action='store_true',help='region property to be inverted')
    
    parser.add_argument('-dl','--displayLayer',default=2,type=int,help='0 = regions, 1 = actors, 2 = both')
    parser.add_argument('-fn','--fileName',default='d:/groundtruth/data/rundatatable.tsv',type=str,help='simulation file name')
    parser.add_argument('-hfn','--hurricaneFileName',default='d:/groundtruth/data/hurricanetable.tsv',type=str,help='simulation hurricane file name')

    args = vars(parser.parse_args())



    usage = "python.exe .\\viz.py -sw 1024 -sh 768 -s 1 -c 7 -r 7 -rp risk -ap health -dl 0 -fn rundatatable.tsv -hfn hurricanetable.tsv"
    print(usage)

    currentDay = 0
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
    hurricaneFileName = args['hurricaneFileName']

    invertRegionProp = args['regionPropertyInverted']
    invertActorProp = args['actorPropertyInverted']

    print ("I = %s R = %s"%(invertActorProp,invertRegionProp) )
    
    

    if  showActors == 0:        
        displaylayer = "Regions"
    if  showActors == 1:        
        displaylayer = "Actors"
    if  showActors == 2:   
        displaylayer = "Regions and Actors"
 


    run = True
    i = 0
    simdata = {}
    
    vm = VizMap(sWidth, sHeight, numxgrid, numygrid, simdata, showActors, currentPropRegion, currentPropIndividual, invertRegionProp, invertActorProp, 'pygame')

    if not combinedFileName is "" :
        print ("Reading %s" %combinedFileName)
        numOfDays = readfile(combinedFileName, "")
    else:
        print ("No data file specified")

    if not hurricaneFileName is "" :
        print ("Reading %s" %hurricaneFileName)
        readHurricaneFile(hurricaneFileName)
    else:
        print ("No data file specified")
    print ("keys ",simdata.keys())
    print ("Simdata: %d %d %d" %(len(simdata['Region']), len(simdata['Actor']), len(simdata['hurricane'])))
  
    i = 0.0
    while run:
        
        vm.update(currentDay)        
        vm.updateTitle("Visualization Day %d Layer: %s Actor Property: %s Region Property %s" % (currentDay, displaylayer , currentPropIndividual, currentPropRegion))

        if i == 0.0:  
            if currentDay < numOfDays :
                currentDay += 1
            else: 
                currentDay = 1
                exit(0)
        if i < 10.0 / speed: 
            i += 1.0
        else:
            i = 0.0


def readHurricaneFile(filename):
    with open(filename) as f:
        lines = f.readlines()
        headervalues = []
        isHeader = True
        for line in lines:
            entry =  line.rstrip('\n').split('\t')
            #print(len(entry))
            if len(entry) is 1:
                #blank lines
                continue
            if isHeader:
                headervalues = entry
                isHeader = False
                print (headervalues)
            else:
                values = entry
                record = {}

                for index in range(len(values)):
                    record[headervalues[index]] = values[index]
                #print(record)
                addToVizData("hurricane", record)

def addToVizData(keyname, entry):
    print ("AddtoVizData - ", keyname, entry)

    
    if not keyname in vm._simdata:
        vm._simdata[keyname] = {}

    headervalues = list(entry.keys())
    values = list(entry.values())
    entityname = values[1]
    simday = int(values[0])

    if not simday in vm._simdata[keyname]:
        vm._simdata[keyname][simday] = {}
    
    if not entityname in vm._simdata[keyname][simday]:
        vm._simdata[keyname][simday][entityname] = {}

    entityname = list(entry.values())[1]
    for cntr in range (2, len(entry)):
        vm._simdata[keyname][simday][entityname][headervalues[cntr]] = (values[cntr])

def readfile(filename, keyname):
    simday = -1

    #read alternate sim file format
    with open(filename) as f:
        lines = f.readlines()        
        totalrecords = len(lines)
        headervalues = []
        values = []
        isHeader = True
        print ("#Num lines = ", len(lines))
        for line in lines:
            entry = line.rstrip('\n').split('\t')
            if len(entry) is 1:
                continue
            if isHeader:
                headervalues = entry
                isHeader = False
                print (headervalues)
            else:
                values = entry
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

                if valueEntityId in simdata[valueKey][simday].keys():
                    pass
                else:

                    simdata[valueKey][simday][valueEntityId] = {}
                    

                simdata[valueKey][simday][valueEntityId][valueProp] = valueValue

#                if (valueKey == 'Region' and valueProp == 'risk') or (valueKey == 'Actor' and valueProp == 'health'):
#                    print ("%s %d %s %s %s" %(valueKey, simday, valueEntityId, valueProp, (valueValue)))
                
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