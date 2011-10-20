from teamwork.widgets.bigwidgets import *
from teamwork.dynamics.pwlDynamics import *
from teamwork.agent.AgentClasses import *
from violence import *
from laugh import *
from teamwork.math.Interval import *

##teacher:
##weak
##hates me
##likes victim
##abusive
##fair

teacher = {'nothing':
           {'class':'default','action':{"type":"wait"}},

           'abusive':
           {'class':'observation', 'depth': 4, 'actor': 'bully', 'type': 'pickOn',
            'action':{"type":"punishAll"}},

           'hates-me':
           {'class':'default','action':{"type":"punish","object":"bully"}},

           'punish-laughter':
           {'class':'observation', 'depth': 4, 'type': 'laughAt',
            'action':{"type":"punishAll"}},

           'retaliate':
           {'class':'observation', 'depth': 4, 'actor': 'bully', 'type': 'pickOn',
            'action':{"type":"punish","object":"bully"}},

           'severe':
           {'class':'observation', 'depth': 4, 'actor': 'bully', 'type': 'pickOn',
            'action':{"type":"severelyPunish","object":"bully"}},

           'conditional':
           {'class':'conjunction',
            'clauses':[{'class':'belief','keys':['entities','self','state','power'],
                        'range':Interval(0.5,1.0,)},
                       {'class':'observation','depth': 4, 'actor': 'bully',
                        'type': 'pickOn'}],
            'action':{"type":"punish","object":"bully"}},
           
           }

TeacherModels = {'mean':
                 {'goals':[{'entity':['self'],'direction':'min','type':'state',
                            'key':'power','weight':0.5}],
                  'policy':[teacher['retaliate'],
                            teacher['nothing']]
                  },
                 'fed-up':
                 {'goals':[{'entity':['Student'],'direction':'max',
                            'type':'state','key':'power','weight':0.5}],
                  'policy':[teacher['punish-laughter'],
                            teacher['severe'],
                            teacher['nothing']]
                  },
                 'fair':
                 {'goals':[{'entity':['Student'],'direction':'max',
                            'type':'state','key':'power','weight':0.5}],
                  'policy':[teacher['punish-laughter'],
                            teacher['retaliate'],
                            teacher['nothing']]
                  },
                 'weak':
                 {'goals':[{'entity':['Student'],'direction':'max',
                            'type':'state','key':'power','weight':0.5}],
                  'policy':[teacher['conditional'],
                            teacher['nothing']]
                  }
                 }
    
rules = {'attention':
         {'class':'conjunction',
          'clauses':[{'class':'observation', 'depth': 4, 'type': 'laughAt',
                      'object': 'victim',},
                     {'class':'observation', 'depth': 4, 'actor': 'self',
                      'type': 'pickOn', 'object': 'victim',},],
          'action':{"type":"pickOn","object":"victim"}},

         'retaliate':
         {'class':'observation', 'depth': 4, 'actor': 'teacher',
          'type': 'punish', 'object': 'self',
          'action':{"type":"pickOn","object":"victim"}},

         'encourage':
         {'class':'observation', 'depth': 4, 'type': 'pickOn',
          'object': 'victim', 'action': {"type":"laughAt","object":"victim"}},

         'cower-individual':
         {'class':'observation', 'depth': 4, 'actor': 'teacher',
          'type': 'punish', 'object': 'self', 'action': {"type":"wait"}},

         'cower':
         {'class':'observation', 'depth': 4, 'actor': 'teacher',
          'type': 'punishAll', 'action': {"type":"wait"}},
         
         'defaultNOP':
         {'class':'default', 'action': {"type":"wait"}},

         'defaultFight':
         {'class':'default', 'action': {"type":"pickOn","object":"victim"}},
         }

OnlookerModels = {'discouraging':
                  {'goals':[{'entity':['self'],'direction':'max','type':'state',
                             'key':'power','weight':1.}],
                   'policy':[rules['defaultNOP']]},
                  'encouraging':
                  {'goals':[{'entity':['victim'],'direction':'min','type':'state',
                             'key':'power','weight':0.2},
                            {'entity':['self'],'direction':'max','type':'state',
                             'key':'power','weight':0.8}],
                   'policy':[rules['encourage'],
                             rules['defaultNOP']]},
                  'scared':
                  {'goals':[{'entity':['self'],'direction':'max','type':'state',
                             'key':'power','weight':1.}],
                   'policy':[rules['cower-individual'],
                             rules['cower'],
                             rules['encourage'],
                             rules['defaultNOP']]}
                  }           


VictimModels = {'passive':
                  {'goals':[{'entity':['self'],'direction':'max','type':'state',
                             'key':'power','weight':1.}],
                   'policy':[rules['defaultNOP']]},
                'vindictive':
                {'goals':[{'entity':['self'],'direction':'max','type':'state',
                             'key':'power','weight':.7},
                            {'entity':['bully'],'direction':'min','type':'state',
                             'key':'power','weight':.3}],
                 'policy':[rules['defaultNOP']]}
                }
##victim:
##    hates me
##    thinks he is better than me / special / etc.

##onlooker:
##    do not care
##    funny to beat on victim
##    sad to beat on victim
##    scared

##principal:
BullyModels = {'sadistic':
               {'goals':[{'entity':['self'],
                          'direction':'max','type':'state',
                          'key':'power','weight':.1},
                         {'entity':['Onlooker'],
                          'direction':'max','type':'act','object':'victim',
                          'key':'laughAt','weight':.1},
                         {'entity':['victim'],
                          'direction':'min','type':'state',
                          'key':'power','weight':.8},
                         ],
                'policy':[rules['cower-individual'],
                          rules['cower'],
                          rules['defaultFight']]},
               
               'attention-seeking':
               {'goals':[{'entity':['self'],
                          'direction':'max','type':'state',
                          'key':'power','weight':.1},
                         {'entity':['Onlooker'],
                          'direction':'max','type':'act','object':'victim',
                          'key':'laughAt','weight':.8},
                         {'entity':['victim'],
                          'direction':'min','type':'state',
                          'key':'power','weight':.1},
                         ],
                'policy':[rules['attention'],
                          rules['cower-individual'],
                          rules['cower'],
                          rules['defaultFight']]},
               'rebellious':
               {'goals':[{'entity':['teacher'],'direction':'min','type':'state',
                          'key':'power','weight':0.4},
                         {'entity':['self'],'direction':'max','type':'state',
                          'key':'power','weight':0.6},
                         {'entity':['Onlooker'],'direction':'max','type':'act',
                          'key':'laughAt','weight':0.2}],
                'policy':[rules['cower-individual'],
                          rules['defaultFight']]},
               }                     



classHierarchy['Entity']['horizon'] = 1
classHierarchy['Entity']['depth'] = 2

classHierarchy['Student'] = {
    'parent': ['Entity'],
    'actions':{'type':None},
    'state':{'power':0.3},
    'relationships':{#'teacher':['Teacher'],
                     'victim':['Student']},
    'dynamics':{'power':{'pickOn':{'class':PWLDynamics,
                                   'args':genPunishClass('Victim','power',.5)},
                         'laughAt':{'class':PWLDynamics,
                                  'args':genPunishClass('Victim','power',.25)},
                         'punish':{'class':PWLDynamics,
                                   'args':genAttackDyn('power')},
                         'punishAll':{'class':PWLDynamics,
                                      'args':genPunishClass('Student',
                                                            'power')},
                         'punishBully':{'class':PWLDynamics,
                                        'args':genPunishClass('Bully',
                                                            'power')},
                         'punishOnlooker':{'class':PWLDynamics,
                                           'args':genPunishClass('Onlooker',
                                                                 'power')},
                         'scoldAll':{'class':PWLDynamics,
                                      'args':genPunishClass('Student',
                                                            'power',.5)},
                         'scoldBully':{'class':PWLDynamics,
                                        'args':genPunishClass('Bully',
                                                              'power',.5)},
                         'scoldOnlooker':{'class':PWLDynamics,
                                          'args':genPunishClass('Onlooker',
                                                                'power',.5)},
                         'severelyPunish':{'class':PWLDynamics,
                                           'args':genAttackDyn(fromFeature='power',
                                                       scale=3.)}
                         }
                },
##    'beliefs':{'Teacher':{'_trustworthiness':0.3,
##                          '_likeability':-0.2,
##                          'model':'fair'
##                          },
##               'Bully':{'_trustworthiness':-0.4,
##                        '_likeability':-0.1,
##                        'model':'rebellious'
##                        },
##               'Victim':{'_trustworthiness':-0.2,
##                         '_likeability':-0.1}
##               },
    }

classHierarchy['Onlooker'] = {
    'parent': ['Student'],
    'actions':{'type':'AND',
               'key':'object',
               'values':[{'type':'generic','value':'Victim'}],
               'base': {'type':'XOR',
                        'key':'type',
                        'values':[{'type':'literal','value':'laughAt'},
                                  {'type':'literal','value':'wait'}],
                        },
               },
##     'beliefs':{'self':{'model':'encouraging'},
##                'Teacher':{'_trustworthiness':0.3,
##                           '_likeability':-0.2,
##                           'model':'fair'},
##                'Bully':{'_trustworthiness':-0.4,
##                         '_likeability':0.1,
##                         'model':'rebellious'
##                         },
##                'Victim':{'_trustworthiness':-0.2,
##                          '_likeability':-0.1}
##                },
    'goals': [{'entity':['self'],
              'direction':'max','type':'state',
              'key':'power','weight':1.0},
              {'entity':['Victim'],
               'direction':'min','type':'state',
               'key':'power','weight':0.3}
              ],
##    'models':OnlookerModels
    }

classHierarchy['Teacher'] = {
    'parent': ['Entity'],
##    'relationships':{'bully':['Bully']},
    'goals': [
##    {'entity':['Onlooker'],'direction':'min','type':'act',
##     'key':'pickOn','weight':0.8},
    {'entity':['Student'],'type':'state',
     'direction':'max','key':'power','weight':0.2}
             ],
    'dynamics':{'power':{'punish':{'class':PWLDynamics,
                                   'args':genAttackDyn('power')},
                         'punishAll':{'class':PWLDynamics,
                                      'args':genPunishClass('Student',
                                                            'power')},
                         'severelyPunish':{'class':PWLDynamics,
                                           'args':genAttackDyn(fromFeature='power',
                                                       scale=3.)}
                         }
                },
    'actions':{'type':'XOR',
               'key':'type',
               'values':[{'type':'literal','value':'punishBully'},
                         {'type':'literal','value':'punishAll'},
                         {'type':'literal','value':'punishOnlooker'},
                         {'type':'literal','value':'scoldBully'},
                         {'type':'literal','value':'scoldAll'},
                         {'type':'literal','value':'scoldOnlooker'},
                         {'type':'literal','value':'wait'},
                         ],
               },
##    'actions':{'type':'AND',
##               'key':'object',
##               'values':[{'type':'generic','value':'Bully'}],
####                'values':[{'type':'generic','value':'Student'}],
##               'base': {'type':'XOR',
##                        'key':'type',
##                        'values':[{'type':'literal','value':'punish'},
##                                  {'type':'literal','value':'severelyPunish'},
##                                  {'type':'literal','value':'wait'}],
##                        },
##               },
    'state':{'power':0.7},
##    'models':TeacherModels,
    'widget':'box',
##     'beliefs':{'self':{'model':'fair'},
##                'Bully':{'model':'attention-seeking',
##                         '_trustworthiness':-0.2,
##                         '_likeability':-0.3},
##                'Onlooker':{'model':'scared',
##                           '_trustworthiness':0.1,
##                           '_likeability':0.3},
##                'Victim':{'model':'passive',
##                          '_trustworthiness':0.1,
##                          '_likeability':0.3}}
    }

classHierarchy['Bully'] = {
    'parent': ['Student'],
    'state':{'power':0.4},
    'actions':{'type':'AND',
               'key':'object',
               'values':[{'type':'relationship','value':'victim'}],
               'base': {'type':'XOR',
                        'key':'type',
                        'values':[{'type':'literal','value':'pickOn'},
                                  {'type':'literal','value':'wait'}],
                        },
               },
    'goals': [{'entity':['self'],
               'direction':'max','type':'state',
               'key':'power','weight':.4},
              {'entity':['Onlooker'],
               'direction':'max','type':'act','object':'victim',
               'key':'laughAt','weight':.3},
              {'entity':['victim'],
               'direction':'min','type':'state',
               'key':'power','weight':.3},
              ],
##     'beliefs':{'self':{'model':'rebellious'},
##                'Teacher':{'_trustworthiness':-0.3,
##                           '_likeability':-0.5,
##                           'model':'fair'},
##                'Victim':{'model':'passive',
##                          '_trustworthiness':-0.4,
##                          '_likeability':-0.6},
##                'Onlooker':{'_trustworthiness':-0.2,
##                           '_likeability':0.1,
##                           'model':'encouraging'
##                           }
##                },
    'widget':'polygon',
##    'models':BullyModels
    }

##classHierarchy['AttentionSeekingBully'] = {
##    'parent':['Bully'],
##    'goals': [{'entity':['self'],
##               'direction':'max','type':'state',
##               'key':'power','weight':.1},
##              {'entity':['Onlooker'],
##               'direction':'max','type':'act','object':'victim',
##               'key':'laughAt','weight':.8},
##              {'entity':['victim'],
##               'direction':'min','type':'state',
##               'key':'power','weight':.1},
##              ]
##    }

##classHierarchy['SadisticBully'] = {
##    'parent':['Bully'],
##    'goals': [{'entity':['self'],
##               'direction':'max','type':'state',
##               'key':'power','weight':.1},
##              {'entity':['Onlooker'],
##               'direction':'max','type':'act','object':'victim',
##               'key':'laughAt','weight':.1},
##              {'entity':['victim'],
##               'direction':'min','type':'state',
##               'key':'power','weight':.8},
##              ]
##    }

##classHierarchy['DominatingBully'] = {
##    'parent':['Bully'],
##    'goals': [{'entity':['Onlooker'],
##               'direction':'max','type':'act','object':'victim',
##               'key':'laughAt','weight':.1},
##              {'entity':['self'],
##               'direction':'max','type':'state',
##               'key':'power','weight':.8},
##              {'entity':['victim'],
##               'direction':'min','type':'state',
##               'key':'power','weight':.1},
##              ]
##    }

classHierarchy['Victim'] = {
    'parent': ['Student'],
    'state':{'power':0.2},
##     'beliefs':{'self':{'model':'passive'},
##                'Teacher':{'_likeability':0.2,
##                           'model':'fair'
##                           },
##                'Bully':{'_trustworthiness':-0.5,
##                         '_likeability':-0.5,
##                         'model':'sadistic'
##                         },
##                'Onlooker':{'model':'encouraging',
##                           '_trustworthiness':-0.2,
##                           '_likeability':-0.2}
##                },
##    'models':VictimModels,
    'goals': [{'entity':['self'],
              'direction':'max','type':'state',
              'key':'power','weight':1.0}
              ]
    }

               
if __name__ == '__main__':
    import os.path
    from teamwork.multiagent.GenericSociety import *

    soc = GenericSociety()
    soc.importDict(classHierarchy)
    
    name = '/tmp/%s.xml' % (os.path.basename(__file__))
    f = open(name,'w')
    f.write(soc.__xml__().toxml())
    f.close()

    new = GenericSociety()
    new.parse(parse(name))
##    print new
