from teamwork.agent.AgentClasses import *
from teamwork.dynamics.pwlDynamics import *

from ChatDynamics import *


classHierarchy['NormAgent'] = {
    'parent': [],
    'horizon':1,
    'depth':3,
    'state':{\
             'resp-norm':0.00000000000000001,
             'init-norm':0.00000000000000001,
             'SD':0.00000000000000001,
             'being-enquired':0,

             },
 
    'dynamics':DynFun['basicDyn'],
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
                                  'weight':    1},
                
 
                         ],


    }

classHierarchy['usr'] = {
    'parent': ['NormAgent'],
    'horizon':1,
    'actions': {'type':'XOR',
                 'key':'type',
                  'values':[{'type':'literal','value':'enquiry'},
                    {'type':'literal','value':'pos-inform'},
                    {'type':'literal','value':'neu-inform'},
                    {'type':'literal','value':'neg-inform'},
                    ],
                  'base': {'type':'XOR',
                         'key':'object',
                         'values':[{'type':'literal','value':'cha'},
                                   ],
                         },
                },
 
    'dynamics':DynFun['basicDyn'],

    }


classHierarchy['cha'] = {
    'parent': ['NormAgent'],
    'horizon':1,
    'actions': {'type':'XOR',
                 'key':'type',
                  'values':[{'type':'literal','value':'enquiry'},
                    {'type':'literal','value':'pos-inform'},
                    {'type':'literal','value':'neu-inform'},
                    {'type':'literal','value':'neg-inform'},
                    ],
                  'base': {'type':'XOR',
                         'key':'object',
                         'values':[{'type':'literal','value':'usr'},
                                   ],
                         },
                },
 
    'dynamics':DynFun['basicDyn'],

    }

