import copy
from teamwork.policy.LookupPolicy import LookupPolicy
from teamwork.policy.LookaheadPolicy import LookaheadPolicy

class LookupAheadPolicy(LookupPolicy,LookaheadPolicy):
    lookupClass = LookupPolicy
    lookaheadClass = LookaheadPolicy
    
    def __init__(self,entity,actions,size,depth=1):
        self.lookaheadClass.__init__(self,entity,actions,depth)
        self.lookupClass.__init__(self,entity=entity,actions=actions,
                                  span=size)

    def setHorizon(self,depth=1):
        self.lookaheadClass.setDepth(self,depth)

    def tryLookup(self,state,choices,debug,explain):
        if len(choices) > 0:
            newChoices = choices + [self.entity.actionClass({'type':'lookahead'})]
        else:
            newChoices = choices
        act,exp = self.lookupClass.execute(self,state,newChoices,debug)
        return act,exp
    
    def execute(self,state,choices=[],debug=False,explain=False):
        act,exp = self.tryLookup(state,choices,debug,explain)
        if not act:
            act,exp = self.lookaheadClass.execute(self,state,choices,debug,
                                                  explain=explain)
        elif act[0]['type'] == 'lookahead':
            depth = -1
            for value in act.values():
                if value != 'lookahead' and value:
                    depth = value
                    break
            act,exp = self.lookaheadClass.execute(self,state,choices,debug,
                                                  depth,explain=explain)
        return act,exp

    def __copy__(self):
        newPolicy = self.__class__(self.entity,self.choices,
                                   self.span,self.horizon)
        newPolicy.entries = self.entries[:]
        return newPolicy

    def __deepcopy__(self,memo):
        newPolicy = self.__class__(self.entity,self.choices,
                                   self.span,self.horizon)
        newPolicy.entries = copy.deepcopy(self.entries,memo)
        return newPolicy

    def actionValue(self,state,actStruct,debug=False):
        action,explanation = self.lookupClass.execute(self,state=state,
                                                  debug=debug)
        if not action or action['type'] == 'lookahead':
            return self.lookaheadClass.actionValue(self,state,actStruct,debug)
        else:
            return self.lookupClass.actionValue(self,state,actStruct,debug)

    def __contains__(self,value):
        return self.lookupClass.__contains__(self,value) or \
               self.lookaheadClass.__contains__(self,value)

    def __xml__(self):
        doc = LookaheadPolicy(self)
        doc.documentElement.setAttribute('span',str(self.span))
        return doc

    def parse(self,element):
        LookaheadPolicy.parse(self,element)
        try:
            self.span = int(element.getAttribute('span'))
        except ValueError:
            self.span = 1
