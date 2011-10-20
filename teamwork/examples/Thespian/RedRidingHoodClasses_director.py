from teamwork.agent.AgentClasses import *
from teamwork.dynamics.pwlDynamics import *

from RedRidingHoodDynamics_director import *

classHierarchy['character'] = {
    'parent': [],
    #'horizon':1,
    #'depth':2,
    'dynamics':[DynFun['basicDyn'],DynFun['RedDyn']],
    'state':{\
            'alive':1.0,
    
            'being-enquired':0.0,
            'enquired':0.0,
            'init-norm':0.0,
            'resp-norm':0.0,
            'SD-norm':0.0,
            
            'likeMove':-1,
            'likeTalk':-1,
            #'sameLocation':1.0,
            #
            #
            #'wolfAlive':1.0,
            #'redAlive':1.0,
            #'redEaten':0.0,
            #'grannyEaten':0.0,
            
            'indoor':0.0,
            #'specialRule':0.0,
            
             },
    'models': {
        'simple': {'goals':[\
                            {'entity':['self'],'direction':'max','type':'state',
                            'key':'alive','weight':5},
                            # {'entity':['self'],'direction':'max','type':'state',
                            #'key':'sameLocation','weight':1000},
                            ],
                'policy': [],
                     },
    }
    }

classHierarchy['red'] = {
    'parent': ['character'],
    'horizon':1,
    'depth':1,
    'dynamics':[DynFun['basicDyn'],DynFun['RedDyn'],DynFun['RedSelfDyn']],
    'state':{\
            'eaten':0.0,
             'power':0.2,
            'has-cake':1.0,
            'location':0.25,
             },
    'beliefs':{\
               'wolf':{'model':'simple'},
               },

    'goals':[\
            #{'entity':['self'],'direction':'max','type':'state',
            #    'key':'specialRule','weight':1000.},
            #{'entity':['self'],'direction':'max','type':'state',
            #    'key':'sameLocation','weight':1000},
            
            {'entity':['wolf'],'direction':'min','type':'state',
              'key':'alive','weight':50.},
            
            {'entity':['self'],'direction':'max','type':'state',
                'key':'alive','weight':5},
    
            {'entity':['self'],'direction':'max','type':'state',
                'key':'init-norm','weight':1.},
            {'entity':['self'],'direction':'max','type':'state',
                'key':'resp-norm','weight':1.},
            {'entity':['self'],'direction':'max','type':'state',
                'key':'SD-norm','weight':1.},

             {'entity':['self'],'direction':'min','type':'state',
              'key':'eaten','weight':5.},
             
             {'entity':['granny'],'direction':'max','type':'state',
              'key':'has-cake','weight':1.},
            
            {'entity':['self'],'direction':'max','type':'state',
              'key':'likeTalk','weight':.5},
            
            {'entity':['self'],'direction':'max','type':'state',
              'key':'likeMove','weight':.5},
             ],
        
     'actions': {'type':'OR',
		'values':[{'type':'decision',
			   'value':{'type':'XOR',
				    'key':'object',
				    'values':[{'type':'generic','value':'wolf'}],
				    'base': {'type':'XOR',
					     'key':'type',
					     'values':[\
                                                       {'type':'literal','value':'talkabout-granny'},
                                                       {'type':'literal','value':'escape'},
                                                       {'type':'literal','value':'enquiry'},
                                                       {'type':'literal','value':'inform'},
                                                       {'type':'literal','value':'kill'},
                                                       #{'type':'literal','value':'follow'},
						       ],
					     },
				    },
			   },
                          {'type':'decision',
			   'value':{'type':'XOR',
				    'key':'object',
				    'values':[{'type':'generic','value':'granny'},
                                                {'type':'generic','value':'wolf'}],
				    'base': {'type':'XOR',
					     'key':'type',
					     'values':[{'type':'literal','value':'give-cake'},
						       ],
					     },
				    },
			   },
                          {'type':'decision',
			   'value':{'type':'XOR',
					     'key':'type',
					     'values':[{'type':'literal','value':'move1'},
                                                        {'type':'literal','value':'move-1'},
                                                       #{'type':'literal','value':'moveto-granny'},
                                                       {'type':'literal','value':'wait'},
                                                       
						       ],
				    },
			   },
                          {'type':'decision',
			   'value':{'type':'XOR',
				    'key':'object',
				    'values':[{'type':'generic','value':'hunter'},
                                                {'type':'generic','value':'woodcutter'}],
				    'base': {'type':'XOR',
					     'key':'type',
					     'values':[{'type':'literal','value':'enquiry'},
                                                        {'type':'literal','value':'inform'},
						       ],
					     },
				    },
			   },
			  ],
		},

    }

classHierarchy['hunter'] = {
    'parent': ['character'],
    'horizon':1,
    'depth':1,
    'state':{\
             'power':1.0,
             'has-cake':0.0,
            'location':-.55,
            #'location':.95,
             },
 
    'goals':[\
            #{'entity':['self'],'direction':'max','type':'state',
            #    'key':'specialRule','weight':1000.},
            #{'entity':['self'],'direction':'max','type':'state',
            #    'key':'sameLocation','weight':1000},
    
            {'entity':['self'],'direction':'max','type':'state',
            'key':'init-norm','weight':1.},
            {'entity':['self'],'direction':'max','type':'state',
                'key':'resp-norm','weight':1.},
            
            {'entity':['self'],'direction':'max','type':'state',
                'key':'SD-norm','weight':1.},
            
            {'entity':['wolf'],'direction':'min','type':'state',
              'key':'alive','weight':5.},

            {'entity':['self'],'direction':'max','type':'state',
              'key':'likeMove','weight':.5},
             ],
        
     'actions': {'type':'OR',
		'values':[{'type':'decision',
			   'value':{'type':'XOR',
				    'key':'object',
				    'values':[{'type':'generic','value':'wolf'}],
				    'base': {'type':'XOR',
					     'key':'type',
					     'values':[{'type':'literal','value':'kill'},
                                                        {'type':'literal','value':'inform'},
                                                  {'type':'literal','value':'talkabout-granny'},
						       ],
					     },
				    },
			   },
                            {'type':'decision',
			   'value':{'type':'XOR',
				    'key':'object',
				    'values':[{'type':'generic','value':'woodcutter'},
                                              ],
				    'base': {'type':'XOR',
					     'key':'type',
					     'values':[\
                                                       {'type':'literal','value':'help'},
                                                        {'type':'literal','value':'inform'},
                                                        {'type':'literal','value':'enquiry'},
						       ],
					     },
				    },
			   },
                          {'type':'decision',
			   'value':{'type':'XOR',
				    'key':'object',
				    'values':[{'type':'generic','value':'red'},
                                                {'type':'generic','value':'granny'}],
				    'base': {'type':'XOR',
					     'key':'type',
					     'values':[{'type':'literal','value':'inform'},
                                                        {'type':'literal','value':'enquiry'},
                                                        {'type':'literal','value':'give-gun'},
						       ],
					     },
				    },
			   },
                          
                          {'type':'decision',
			   'value':{'type':'XOR',
					     'key':'type',
					     'values':[{'type':'literal','value':'move2'},
                                                        {'type':'literal','value':'move-2'},
                                                        {'type':'literal','value':'move1'},
                                                        {'type':'literal','value':'move-1'},
                                                       {'type':'literal','value':'wait'},
						       ],
				    },
			   },
                          
			  ],
		},

    }

classHierarchy['woodcutter'] = {
    'parent': ['character'],
    'horizon':1,
    'depth':1,
    'dynamics':[DynFun['basicDyn'],DynFun['RedDyn'],DynFun['woodcutterSelfDyn']],
    'state':{\
             'power':1.0,
             'has-cake':0.0,
            'location':0.25,
            #'alive':1.0,
            #'preferWait':1.0,
             },
    'beliefs':{\
               'wolf':{'model':'simple'},
               },
 
    'goals':[\
             #{'entity':['self'],'direction':'max','type':'state',
             #   'key':'sameLocation','weight':1000},
             #
             #{'entity':['self'],'direction':'max','type':'state',
             #   'key':'specialRule','weight':1000.},
    
            {'entity':['self'],'direction':'max','type':'state',
            'key':'init-norm','weight':1.},
            
            {'entity':['self'],'direction':'max','type':'state',
                'key':'resp-norm','weight':1.},
            
            {'entity':['self'],'direction':'max','type':'state',
                'key':'SD-norm','weight':1.},
                            
            {'entity':['red'],'direction':'min','type':'state',
              'key':'eaten','weight':5.},
            
            {'entity':['granny'],'direction':'min','type':'state',
              'key':'eaten','weight':5.},
            
            #{'entity':['self'],'direction':'max','type':'state',
            #  'key':'alive','weight':5.},
            
            #{'entity':['self'],'direction':'max','type':'state',
            #    'key':'preferWait','weight':1.},
            
             ],
        
     'actions': {'type':'OR',
		'values':[{'type':'decision',
			   'value':{'type':'XOR',
				    'key':'object',
				    'values':[{'type':'generic','value':'wolf'}],
				    'base': {'type':'XOR',
					     'key':'type',
					     'values':[{'type':'literal','value':'kill'},
                                                        {'type':'literal','value':'inform'},
                                                        {'type':'literal','value':'talkabout-granny'},
						       ],
					     },
				    },
			   },
                            
                          {'type':'decision',
			   'value':{'type':'XOR',
				    'key':'object',
				    'values':[{'type':'generic','value':'red'},
                                                {'type':'generic','value':'hunter'},
                                               ],
				    'base': {'type':'XOR',
					     'key':'type',
					     'values':[{'type':'literal','value':'inform'},
                                                        {'type':'literal','value':'enquiry'},
						       ],
					     },
				    },
			   },
                          
                          {'type':'decision',
			   'value':{'type':'XOR',
					     'key':'type',
					     'values':[\
                                                       {'type':'literal','value':'wait'},
                                                        #{'type':'literal','value':'move1'},
                                                        #{'type':'literal','value':'move-1'},
						       ],
				    },
			   },
                          
			  ],
		},

    }

classHierarchy['granny'] = {
    'parent': ['character'],
    'dynamics':[DynFun['basicDyn'],DynFun['RedDyn'],DynFun['grannySelfDyn']],
    'horizon':1,
    'depth':1,
    'state':{
            'eaten':0.0,
             'power':0.2,
            'has-cake':0.0,
            'location':0.65,
            
             },

    'goals':[\
             #{'entity':['self'],'direction':'max','type':'state',
             #   'key':'sameLocation','weight':1000.},
             #
             #{'entity':['self'],'direction':'max','type':'state',
             #   'key':'specialRule','weight':1000.},
             
             {'entity':['self'],'direction':'min','type':'state',
              'key':'eaten','weight':5.},
             
             {'entity':['self'],'direction':'max','type':'state',
              'key':'alive','weight':5.},
             
             {'entity':['self'],'direction':'max','type':'state',
            'key':'init-norm','weight':1.},
            
            {'entity':['self'],'direction':'max','type':'state',
                'key':'resp-norm','weight':1.},
             
             ],
     'actions': {'type':'OR',
		'values':[{'type':'decision',
			   'value':{'type':'XOR',
				    'key':'object',
				    'values':[{'type':'generic','value':'wolf'}],
				    'base': {'type':'XOR',
					     'key':'type',
					     'values':[{'type':'literal','value':'escape'},
                                                        {'type':'literal','value':'kill'},
						       ],
					     },
				    },
			   },
                          {'type':'decision',
			   'value':{'type':'XOR',
					     'key':'type',
					     'values':[{'type':'literal','value':'wait'},
						       ],
				    },
			   },
                          
                          {'type':'decision',
			   'value':{'type':'XOR',
				    'key':'object',
				    'values':[{'type':'generic','value':'red'},
                                        {'type':'generic','value':'wolf'},
                                        {'type':'generic','value':'hunter'},
                                        {'type':'generic','value':'woodcutter'},
                                              ],
				    'base': {'type':'XOR',
					     'key':'type',
					     'values':[\
                                                       {'type':'literal','value':'enquiry'},
                                                       {'type':'literal','value':'inform'},
						       ],
					     },
				    },
			   },
                          
			  ],
		},

    }

classHierarchy['wolf'] = {
    'parent': ['character'],
    'horizon':2,
    'depth':2,
    'beliefs':{\
               'red':{'model':'simple'},
               'granny':{'model':'simple'},
               #'hunter':{'model':'simple'},
               },
    'state':{\
             'power':0.6,
             'has-cake':0.0,
             'location':.25,
             'full':0.0,
            
             'know-granny':0.0,
             'SD':0.0,
             'helped':0.0,
             },

    'goals':[
            #{'entity':['self'],'direction':'max','type':'state',
            #   'key':'sameLocation','weight':1000},
            #
            #{'entity':['self'],'direction':'max','type':'state',
            #    'key':'specialRule','weight':1000.},
            
            {'entity':['self'],'direction':'max','type':'state',
                'key':'init-norm','weight':1.},
            {'entity':['self'],'direction':'max','type':'state',
                'key':'resp-norm','weight':1.},
                            
             {'entity':['self'],'direction':'max','type':'state',
              'key':'full','weight':3.},
             
             {'entity':['self'],'direction':'max','type':'state',
              'key':'alive','weight':50.},
              
            
            # {'entity':['self'],'direction':'max','type':'state',
            #  'key':'likeMove','weight':.1},
            #{'entity':['self'],'direction':'max','type':'state',
            #  'key':'likeTalk','weight':.15},
           
             ],
    
     'actions': {'type':'OR',
		'values':[{'type':'decision',
			   'value':{'type':'XOR',
				    'key':'object',
				    'values':[{'type':'generic','value':'red'},
                                              {'type':'generic','value':'granny'}],
				    'base': {'type':'XOR',
					     'key':'type',
					     'values':[{'type':'literal','value':'eat'},
                                                         {'type':'literal','value':'give-cake'},
						       ],
					     },
				    },
			   },
                    
                          {'type':'decision',
			   'value':{'type':'XOR',
				    'key':'object',
				    'values':[{'type':'generic','value':'red'},
                                              ],
				    'base': {'type':'XOR',
					     'key':'type',
					     'values':[\
                                                       {'type':'literal','value':'enquiry'},
                                                       {'type':'literal','value':'inform'},
						       ],
					     },
				    },
			   },
                          
                          {'type':'decision',
			   'value':{'type':'XOR',
				    'key':'object',
				    'values':[{'type':'generic','value':'woodcutter'},
                                              ],
				    'base': {'type':'XOR',
					     'key':'type',
					     'values':[\
                                                       {'type':'literal','value':'help'},
                                                        {'type':'literal','value':'enquiry'},
                                                        {'type':'literal','value':'inform'},
                                                        {'type':'literal','value':'give-cake'},
						       ],
					     },
				    },
			   },
                       
                          {'type':'decision',
                                   'value':{'type':'XOR',
                                                     'key':'type',
                                                     'values':[{'type':'literal','value':'move2'},
                                                                {'type':'literal','value':'move-2'},
                                                                {'type':'literal','value':'move1'},
                                                                {'type':'literal','value':'move-1'},
                                                                {'type':'literal','value':'eat-cake'},
                                                                #{'type':'literal','value':'moveto-granny'},
                                                                {'type':'literal','value':'enter-house'},
                                                                {'type':'literal','value':'exist-house'},
                                                                #{'type':'literal','value':'enter-house'},
                                                               {'type':'literal','value':'wait'},
                                                               ],
                                                    
                                            },
                                   }, 
			  ],
		},
    }

