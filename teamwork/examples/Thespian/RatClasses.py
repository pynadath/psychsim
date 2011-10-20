from teamwork.agent.AgentClasses import *
from teamwork.dynamics.pwlDynamics import *

from ratDynamics import *


classHierarchy['usr'] = {
    'parent': ['Entity'],
    'horizon':0,
    'depth':0,
    'state':{\
            'ThespianType':1,
            'money':1.0,
            
            'being-requested-to-match':0,
            
            'resp-norm':0,
            'init-norm':1,
            'actAliveNorm':1,
            'specialRule':1,
            
            },
    'actions':{'type':'OR',
		'values':[{'type':'decision',
                           'value':{'type':'XOR',
                                     'key':'type',
                                      'values':[\
                                              {'type':'literal','value':'request-exercise'},
                                                {'type':'literal','value':'request-match'},
                                                {'type':'literal','value':'feedV'},
                                                {'type':'literal','value':'eshock'},
                                                {'type':'literal','value':'accept'},
                                                {'type':'literal','value':'reject'},
                                        ],
                                      'base': {'type':'XOR',
                                             'key':'object',
                                             'values':[{'type':'literal','value':'labrat1'},
                                                       {'type':'literal','value':'labrat2'},
                                                       {'type':'literal','value':'streetrat'},
                                                       ],
                                             },
                                    },
                           },
                        {'type':'decision',
                           'value':{'type':'XOR',
                                     'key':'type',
                                      'values':[\
                                              {'type':'literal','value':'buyLR'},
                                        ],
                                      'base': {'type':'XOR',
                                             'key':'object',
                                             'values':[{'type':'literal','value':'labrat1'},
                                                       {'type':'literal','value':'labrat2'},
                                                       ],
                                             },
                                    },
                           },
                        {'type':'decision',
                           'value':{'type':'XOR',
                                     'key':'type',
                                      'values':[\
                                              {'type':'literal','value':'catchSR'},
                                        ],
                                      'base': {'type':'XOR',
                                             'key':'object',
                                             'values':[{'type':'literal','value':'streetrat'},
                                                       ],
                                             },
                                    },
                           },
                          {'type':'decision',
                            'value':{'type':'XOR',
					     'key':'type',
					     'values':[\
                                                     #{'type':'literal','value':'buyV'},
                                                       {'type':'literal','value':'wait'},
						       ],
				    },
			   },]
                          },
 
    'dynamics':[DynFun['basicDyn'],DynFun['usrDyn']],
    'goals':[{'entity':    ['self'],
          'direction': 'max',
          'type':      'state',
          'key':   'resp-norm',
          'weight':    1000},
    
        {'entity':    ['self'],
          'direction': 'max',
          'type':      'state',
          'key':   'init-norm',
          'weight':    10},
    
        {'entity':    ['self'],
          'direction': 'max',
          'type':      'state',
          'key':   'specialRule',
          'weight':    1000},
        
        {'entity':    ['self'],
                        'direction': 'max',
                        'type':      'state',
                        'key':   'actAliveNorm',
                        'weight':    1000},
        
        {'entity':    ['self'],
          'direction': 'max',
          'type':      'state',
          'key':   'money',
          'weight':    .01},
        
        {'entity':    ['labrat1'],
          'direction': 'max',
          'type':      'state',
          'key':   'health',
          'weight':    1},
        
        {'entity':    ['labrat2'],
          'direction': 'max',
          'type':      'state',
          'key':   'health',
          'weight':    1},
        
        {'entity':    ['streetrat'],
          'direction': 'max',
          'type':      'state',
          'key':   'health',
          'weight':    1},
        
        {'entity':    ['labrat1'],
          'direction': 'max',
          'type':      'state',
          'key':   'SD',
          'weight':    1},
        
        {'entity':    ['labrat2'],
          'direction': 'max',
          'type':      'state',
          'key':   'SD',
          'weight':    1},
        
        {'entity':    ['streetrat'],
          'direction': 'max',
          'type':      'state',
          'key':   'SD',
          'weight':    1},
        
        {'entity':    ['labrat1'],
          'direction': 'max',
          'type':      'state',
          'key':   'ThespianType',
          'weight':    1},
        
        {'entity':    ['labrat2'],
          'direction': 'max',
          'type':      'state',
          'key':   'ThespianType',
          'weight':    1},
        
        {'entity':    ['streetrat'],
          'direction': 'max',
          'type':      'state',
          'key':   'ThespianType',
          'weight':    1},
        
        
    ]
    }


classHierarchy['rat'] = {
    'parent': ['Entity'],
    'horizon':2,
    'depth':2,
    'state':{\
            'resp-norm':0,
            'init-norm':1,
            'commitNorm':1,
            'actAliveNorm':1,
            'avoidShock':1,
            
            'health':.2,
            'smart':.4,
            'SD':0,
            'being-requested-to-exercise':0,
            'being-requested-to-match':0,
            'requested-to-match':0,
            'commit-to-exercise':0,
            'commit-to-match':0,
            'force-to-commit':0,
            
            'like-to-exercise':0,
            'like-to-match':0,
            
            'just-matched':0,
            
            'ThespianType':0,
            }, 
    'goals':[\
        {'entity':    ['self'],
          'direction': 'max',
          'type':      'state',
          'key':   'resp-norm',
          'weight':    1000},
    
        {'entity':    ['self'],
          'direction': 'max',
          'type':      'state',
          'key':   'init-norm',
          'weight':    10},
    
        {'entity':    ['self'],
          'direction': 'max',
          'type':      'state',
          'key':   'commitNorm',
          'weight':    1000},
        
        {'entity':    ['self'],
          'direction': 'max',
          'type':      'state',
          'key':   'avoidShock',
          'weight':    10},
        
        {'entity':    ['self'],
                        'direction': 'max',
                        'type':      'state',
                        'key':   'actAliveNorm',
                        'weight':    1000},
    
        
        {'entity':    ['self'],
                        'direction': 'max',
                        'type':      'state',
                        'key':   'health',
                        'weight':    1},
        
        {'entity':    ['self'],
                        'direction': 'max',
                        'type':      'state',
                        'key':   'SD',
                        'weight':    1},
        
        {'entity':    ['self'],
                        'direction': 'max',
                        'type':      'state',
                        'key':   'like-to-exercise',
                        'weight':    1},
        
        {'entity':    ['self'],
                        'direction': 'max',
                        'type':      'state',
                        'key':   'like-to-match',
                        'weight':    1},
        
                         ],

    }


classHierarchy['labrat'] = {
    'parent': ['rat'],
    'horizon':2,
    'depth':2,
    'dynamics':[DynFun['basicDyn'],DynFun['ratDyn'],DynFun['labratDyn']],
    'actions':{'type':'OR',
	    'values':[{'type':'decision',
                           'value':{'type':'XOR',
                                     'key':'type',
                                      'values':[\
                                       {'type':'literal','value':'accept'},
                                        {'type':'literal','value':'reject'},
                                        {'type':'literal','value':'request-match'},
                                        ],
                                      'base': {'type':'XOR',
                                             'key':'object',
                                             'values':[{'type':'literal','value':'usr'},
                                                       ],
                                             },
                                    },
                           },
                          {'type':'decision',
			   'value':{'type':'XOR',
					     'key':'type',
					     'values':[\
                                                       {'type':'literal','value':'match'},
                                                     {'type':'literal','value':'exercise'},
                                                       {'type':'literal','value':'wait'},
						       ],
				},
			   },]
                          },
 
    }


classHierarchy['streetrat'] = {
    'parent': ['rat'],
    'horizon':2,
    'depth':2,
    'dynamics':[DynFun['basicDyn'],DynFun['ratDyn'],DynFun['streetratDyn']],
    'actions':{'type':'OR',
		'values':[{'type':'decision',
                           'value':{'type':'XOR',
                                     'key':'type',
                                      'values':[\
                                       {'type':'literal','value':'accept'},
                                        {'type':'literal','value':'reject'},
                                        {'type':'literal','value':'request-match'},
                                        ],
                                      'base': {'type':'XOR',
                                             'key':'object',
                                             'values':[{'type':'literal','value':'usr'},
                                                       ],
                                             },
                                    },
                           },
                          {'type':'decision',
                           'value':{'type':'XOR',
                                     'key':'type',
                                      'values':[\
                                       {'type':'literal','value':'bad-mouth'},
                                        ],
                                      'base': {'type':'XOR',
                                             'key':'object',
                                             'values':[{'type':'literal','value':'labrat1'},
                                                       {'type':'literal','value':'labrat2'},
                                                       ],
                                             },
                                    },
                           },
                          {'type':'decision',
                            'value':{'type':'XOR',
					    'key':'type',
					    'values':[\
                                                     {'type':'literal','value':'exercise'},
                                                    {'type':'literal','value':'match'},
                                                     {'type':'literal','value':'escape'},
                                                       {'type':'literal','value':'wait'},
						       ],
				    },
			   },]
                          },
 
    }


classHierarchy['otherTeam'] = {
    'parent': ['Entity'],
    'horizon':0,
    'depth':1,
    'state':{\
            'ThespianType':1,
            'preferWait':0,
            'winChance':0,
            
            'being-requested-for-match-result':0,
            'resp-norm':0,
            },
    'actions':{
                'type':'XOR',
                'key':'type',
                'values':[\
                          {'type':'literal','value':'wait'},
                           {'type':'literal','value':'increasewinChance'},
                           {'type':'literal','value':'decreasewinChance'},
                           {'type':'literal','value':'win'},
                           {'type':'literal','value':'lose'},
                          ],

                          },
 
    'dynamics':[DynFun['basicDyn'],],
    'goals':[\
            {'entity':    ['self'],
                        'direction': 'max',
                        'type':      'state',
                        'key':   'preferWait',
                        'weight':    1},
            {'entity':    ['self'],
                        'direction': 'max',
                        'type':      'state',
                        'key':   'resp-norm',
                        'weight':    1000},
            ]
    }


classHierarchy['timer'] = {
    'parent': ['Entity'],
    'horizon':1,
    'depth':1,
    'state':{\
            'ThespianType':1,
            'specialRule':1,
            'time':4,
            'day':0,
            },
    'actions':{'type':'XOR',
                 'key':'type',
		 'values':[\
                     {'type':'literal','value':'wait'},
                    {'type':'literal','value':'daypass'},
                ],
		},
    'dynamics':[DynFun['timerDyn'],],
    'goals':[\
            {'entity':    ['self'],
                        'direction': 'max',
                        'type':      'state',
                        'key':   'specialRule',
                        'weight':    1},
            ]
    }
