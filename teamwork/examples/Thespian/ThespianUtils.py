import string
import sys

from teamwork.math.KeyedTree import *
from teamwork.math.KeyedMatrix import *
from teamwork.dynamics.pwlDynamics import *
from teamwork.dynamics.arbitraryDynamics import *

##ObligList = ['greet_resp','greet2_init','greet2_resp','thank','urwelcome','bye_resp','OK','accept']
ObligList = ['greet_resp','bye_resp']

def createObsStates(entities):
    for entity in entities:
        state_value = entity.getState('type')
        for Entity_type, prob in state_value.items():
            break

        if Entity_type==0:
            continue
        
        for other in entities:
            for act1 in other.actions.getOptions():
                for act in act1:
                    for addressee in act['addressee']:
                        obsstate='obs-'+act['actor']+'-'+act['sact_type']+'-to-'+addressee
                
                        if act['sact_type'] in  ['enquiry','inform','request','accept','reject','inform_info']:
                            obsstate += '-about-'+act['factors'][0]['lhs'][1]+ '-'+act['factors'][0]['lhs'][3]

                        entity.setState(obsstate,0)

def ObsStateDyns(entities):
    for entity in entities:
        for feature in entity.getStateFeatures():
            if string.find(feature,'obs')==0 :

                ## won't overwrite existing dynamics
                if entity.dynamics.has_key(feature):
                    continue
                
                key =feature
                try:
                    dummy1, actor, sact_type, dummy2, addr, dummy3,about_entity,about_feature = string.split(feature,'-')
##                    'student, any, inform_info, 0.0, 0.0, entities:student:state:feature_identity=.1'
                    actstr=actor+', '+addr+', '+sact_type+', 0.0, 0.0, entities:'+about_entity+':state:'+about_feature+'= 0.0'
                    entity.dynamics[key]={actstr:apply(PWLDynamics, (setDyn(feature,1),))}
                except:
                    try:
                        dummy1, actor, sact_type, dummy2, addr = string.split(feature,'-')
                        actstr=actor+', '+addr+', '+sact_type+', 0.0, 0.0, entities:student:state:norm= 0.0'
                        entity.dynamics[key]={actstr:apply(PWLDynamics, (setDyn(feature,1),))}
                    except ValueError:
                        print string.split(feature,'-')
                
                

            
def createObligations(entities,level=1,type=0):
    depth = level
    for entity in entities:

        state_value = entity.getState('type')
        for Entity_type, prob in state_value.items():
            break

        if Entity_type==0:
            continue
        for other in entities:
            
            state_value = other.getState('type')
            for Other_type, prob in state_value.items():
                break
            
            if Other_type==0:
                continue

            state_value = entity.getState('group')
            for Entity_group, prob in state_value.items():
                break

            state_value = other.getState('group')
            for Other_group, prob in state_value.items():
                break
                            
            if not Entity_group == Other_group:                
                for act in ObligList:
                    obligation='obli-'+act+'-to-'+other.name
                    entity.setState(obligation,0)

                ## we do not need to handle the content of inform
                if type == 0:
                    obligation='obli-inform-to-'+other.name
                    entity.setState(obligation,0)
                    continue

                ## otherwise we will add obligation of informs with content                
                depth = level
                while depth>0:
                    for subEntity in entities:
                        if not entity.name == subEntity.name:
                            
                            state_value = subEntity.getState('group')
                            for subEntity_group, prob in state_value.items():
                                break

                            state_value = entity.getState('group')
                            for Entity_group, prob in state_value.items():
                                break
                                                        
                                
                            for feature in subEntity.getStateFeatures():
                                if string.find(feature,'feature')==0:
                                    obligation='obli-'+'inform-to-'+other.name+'-about-'+subEntity.name+'-'+feature
                                    entity.setState(obligation,0)
                        else:
                            oldfeatures=[]
                            for feature in subEntity.getStateFeatures():
                                oldfeatures.append(feature)
                            for feature in oldfeatures:
                                if string.find(feature,'feature')==0:
                                    obligation='obli-'+'inform-to-'+other.name+'-about-'+subEntity.name+'-'+feature
                                    entity.setState(obligation,0)
                    depth-=1



def SatisfyObliPolicies(entities):
##    add obligation triggered policies like this
##    "belief entities self state should_thank -.9 1 -> student, Rahim, thank, 0.0, 0.0, entities:student:state:feature_identity = .1:.1",
    p = ['']*17
    p[0] = ''
    p[1] = 'belief entities self state '
    p[2] = '' ##should_thank
    p[3] = ' -.9 1 -> '
    p[4] = '' ##student
    p[5] = ', '
    p[6]='' ## Rahim
    p[7]= ', '
    p[8]= '' ## thank
    p[9] = ', 0.0, 0.0, entities:'
    p[10] = 'stuent' ##can be set
    p[11] = ':state:'
    p[12] = 'norm' ##can be set
    p[13] = ' = '
    p[14] = '.1'##can be set
    p[15] = ':'
    p[16] = '.1'##can be set
        
    for entity in entities:
        state_value = entity.getState('type')
        for Entity_type, prob in state_value.items():
            break

        if Entity_type==0:
            continue
        try:
            ## by default add these policies to model simple
            model = entity.models['simple']
        except:
            print 'entity ',entity.name,' has no model named simple'
            continue
        entries = []

        for feature in entity.getStateFeatures():
            if string.find(feature,'obli')==0 and not feature == 'obligNorm':

                ## for scene 1, special rules are suplied
                if feature == 'obli-accept-to-student' and entity.name in ['Baad','Rahim']:
                    continue
                
                ## obli-inform-to-Hamed-about-student-feature_nationality
                ## obli-bye_resp-to-Xaled
                about_entity = None
                try:
                    dummy1,sact_type,dummy2,toobject,dummy3,about_entity,about_feature = string.split(feature,'-')
                except ValueError:
                    try:
                        dummy1,sact_type,dummy2,toobject = string.split(feature,'-')
                    except:
                        print 'WARNING: Illegal obligation name: ',feature
                        continue

                p[2] = feature
                p[4] = entity.name
                p[6] = toobject
                p[8] = sact_type

                if about_entity:
                    p[10] = about_entity
                    p[12] = about_feature
                else:
                    p[10] = 'student'
                    p[12] = 'norm'
                    ## don't know how to set rhs yet
                    
##                        p[12] = entity.getBelief(about_entity,about_feature)['lo']
##                        p[14] = entity.getBelief(about_entity,about_feature)['hi']
                    

                entry = string.join(p)
##                print entry
##                entries.append(entry)
##                model.policy.extend(entries,entity.actionClass,entity)
                model.policy.append(entry)
                
        model.policy.append("default -> {'type':'wait'}")
    
def ObligationDyns(entities):
    for entity in entities:
        for feature in entity.getStateFeatures():
            if string.find(feature,'obli')==0 and not feature == 'obligNorm':

                ## won't overwrite existing dynamics
                if entity.dynamics.has_key(feature):
                    continue

                auto_update_ogli=0
                for act in ObligList.append('inform'):
                    if feature.find(act)>-1:
                        auto_update_ogli=1

                if auto_update_ogli==0:
                    continue
                
                key =feature
##                entity.dynamics[key]={'any':apply(PWLDynamics, (ObligationDyn(feature),))}
                entity.dynamics[key]={'self-any-to-any':apply(PWLDynamics, (SatisfyObligationDyn(feature),)),
                                     'any-any-to-self':apply(PWLDynamics, (CreateObligationDyn(feature),))}
            
                                             

def addNormToAgents(society,normClasses):
##        print society
    for entity in society:
        ## add state
        for feature,value in normClasses['NormAgent']['state'].items():
            society[entity].setState(feature,value)

        ## add dynamics
        if type(normClasses['NormAgent']['dynamics']) == dict:
            dyndict = [normClasses['NormAgent']['dynamics']]
        else:
            dyndict = normClasses['NormAgent']['dynamics']
            
        for dynamics in dyndict:
            for feature,dynDict in dynamics.items():
                for act,dyn in dynDict.items():
                    if isinstance(dyn,DecisionTree):
                        dyn = {'class':PWLDynamics,
                               'args':{'tree':dyn}}
                    fun = dyn['class']
                    args = dyn['args']
                    if not society[entity].dynamics.has_key(feature):
                        society[entity].dynamics[feature] = {}
                    if not society[entity].dynamics[feature].has_key(act):
                        society[entity].dynamics[feature][act] = apply(fun,(args,))
        ## add goals
        for goal in normClasses['NormAgent']['goals']:
            try:
                key = goal['key']
            except KeyError:
                key = goal['feature']
                print 'Warning: Use "key" instead of "feature" when specifying goals'
            goalObj = MinMaxGoal(entity=goal['entity'],
                                 direction=goal['direction'],
                                 goalType=goal['type'],
                                 key=key)
            try:
                ## norm goals are twice as important as other goals
                goalObj.weight = goal['weight']*2
            except KeyError:
                raise KeyError,'%s has goal "%s" with no weight' % \
                      (self.ancestry(),`goalObj`)
            society[entity].setGoalWeight(goalObj,goalObj.weight,False)
        society[entity].normalizeGoals()

        ## add model
        for name,model in normClasses['NormAgent']['models'].items():
            agent = GenericModel(name)
            agent.setGoals(model['goals'])
            agent.policy = model['policy']
            society[entity].models[name] = agent
    return society
                   

   
def stringToAct(act):
    try:
        actor,type,obj = act.split('-')
    except:
        actor,type1,type2,obj = act.split('-')
        type=type1+'-'+type2
    return actor,type,obj