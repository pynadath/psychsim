import string
import sys

from teamwork.shell.TerminalShell import *
from teamwork.shell.PsychShell import extractEntity
from teamwork.utils.PsychUtils import *

from teamwork.examples.ELECT.elect_reader import *

def progress(msg,pct):
    if pct > 0.:
        print 'done.'
    else:
        print msg,'...'
    
class ELECTShell(TerminalShell):
    """Shell subclass enhanced for stories."""
    
    entityList={\
                '1':[('US','US'),('Farid','Farid')],
                }
    

    
    # Uncomment the following to support the undo command
##    __UNDO__ = 1
    
    def __init__(self,entities=None,classes=None,scene='1',
                 debug=0):
        self.scene = scene
        self.loadClasses()
        TerminalShell.__init__(self,entities,self.classes,None,None,None,progress,debug,compileDynamics=True,compilePolicies=None)
##        self.logfile = open("PsychsimLog.txt", 'w')
              
        self.handlers['get_state'] = self.getState
        self.handlers['get_goal'] = self.getGoals
        self.handlers['special_print'] = self.specialPrint
        
        
    # mei 06/30/04 change the param to indicate which scene we are working on
    def createEntities(self):
        
        entities=[]

        for newEntity in self.entityList[self.scene]:
            print newEntity[0]
            entity = createEntity(newEntity[0],newEntity[1],self.classes,
                                  self.agentClass)
            
            if entity:
                entities.append(entity)
                

        for entity in entities:
            print entity.name, entity.getStateFeatures()
            print 'number of state features :', len(entity.getStateFeatures())
            print
        return entities


    def getState(self,entity,feature,results=[]):
        entity1 = None
        resAct = None

        try:
            entity1 = self.entities[entity]
            try:
                resAct = entity1.getSelfBelief(feature)
                for value, prob in resAct.items():
                    break
                results.append(str(value))
            except KeyError:
                results.append('No such state '+feature+' for entity '+\
                               entity.name)
        except IndexError:
            pass
          
##        results = [`item` for item in results]
        print results
        return results


    def get_state(self,entity,feature,results=[]):
         return  self.getState(entity,feature,results)
        
    def getGoals (self,entity,results=[]):
        entity = self.entities[entity]
        print entity.goals
        
    def setState(self,entity,prop,value,results=[]):
        try:
            entity = terminal.entities[entity]
            try:
                entity.setState(prop,value)
                entity.setSelfBelief(prop,float(value))
            except KeyError:
                resAct = 'No such state '+prop+' for entity '+entity.name
                       
        except IndexError:
            pass

    def loadClasses(self):

        er = elect_reader()
        er.process_lines()
        er.add_stateFeatures()
##        er.update_generic_entity_model()
        self.classes = classHierarchy
        if isinstance(self.classes,dict):
            society = GenericSociety()
            society.importDict(self.classes)
            self.classes = society
##            print self.classes
        

    def displayResult(self,cmd,result=[]):
        cmd = string.strip(cmd)
        cmd = string.split(cmd)
        try:
            if cmd[0] in ['entity','getState','hint','step']:
                print result
        except:
            print cmd
            pass
        sys.stdout.flush()


    def setDebuggerLever(self, level=0, results=[]):
        self.debug.setLevel(int(level))
        results.append('Current Debugger Lever: '+str(self.debug.getLevel()))
        

    def specialPrint(self,character,feature='norm',results=[]):
        entity = self.entities[character]
        for feature in entity.getStateFeatures():
            if string.find(feature,'Norm')>-1 or string.find(feature,'goal')>-1 or feature == 'noOK':
                print feature+'     '+ self.getState(character,feature,[])[0]

    def step(self,length=1,results=[]):
        """Steps the simulation the specified number of micro-steps
        into the future (default is 1)"""
        try:
            length = int(length)
        except TypeError:
            results = length
            length = 1
        sequence = []
        for t in range(int(length)):
            delta = self.entities.microstep(turns=[],debug=self.debug)
            if delta['decision']:
                for key in delta['decision'].keys():
                    res = delta['decision'][key][0]
                    
                    print `res`
        return sequence

        
if __name__ == '__main__':
    terminal = ELECTShell()    
    terminal.mainloop()
