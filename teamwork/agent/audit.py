from support import *

class Auditor(Supporter):
    """Mix-in entity class that supports an audit trail"""
    
    def __init__(self):
        self.history = {}

    def formatHistory(self,entry):
        str = '%s by %s at %s' % \
              (string.capitalize(entry['what']),
               entry['who'],
               time.strftime('%x %X',time.localtime(entry['when'])))
        return str
        
    def getHistory(self,key):
        return map(self.formatHistory,self.__getHistory(key))
        
    def __getHistory(self,key):
        """Returns the history of changes to this entity's state/goal value"""
        try:
            history = self.history[key]
        except AttributeError:
            history = []
            self.history = {key:history}
        except KeyError:
            history = []
            self.history[key] = history
        return history

    def extendHistory(self,entry,key=None):
        if key:
            history = self.__getHistory(key)
            if len(history) > 0:
                lastEntry = history[0]
                if lastEntry['who'] != entry['who'] \
                   or lastEntry['what'] != entry['what'] \
                   or entry['what'] == 'stepped':
                    # New entry
                    history.insert(0,entry)
                elif lastEntry['what'] == 'modified':
                    lastEntry['when'] = entry['when']
            else:
                history.append(entry)
        else:
            for key in self.getStateFeatures():
                self.extendHistory(entry,key)
            for key in self.getGoals():
                self.extendHistory(entry,key)
            for entity in self.getEntityBeliefs():
                entity.extendHistory(entry)

    def setState(self,feature,value,log=None):
        """Sets this entity's state value for the specified feature to
        the provided float value"""
        Supporter.setState(self,feature,value)
        if log:
            self.extendHistory(log,feature)
