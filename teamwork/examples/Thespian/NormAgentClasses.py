from teamwork.agent.AgentClasses import *
from teamwork.dynamics.pwlDynamics import *

from NormAgentDynamics import *


classHierarchy['NormAgent'] = {
    'parent': [],
    'horizon':1,
    'depth':3,
    'state':{\
             'type': 1,
             'init-norm':0.00000000000000001,
             'resp-norm':0.00000000000000001,
             'makeResp-norm':0.0000000000001,
             'conversation-flow-norm':0.0000000000001,
             'noRepeat-norm':0.0000000000001,
                     
             'conversation':-1,
             'wait-for-response':-1,
             'keep-turn':-1,
             
            'being-greeted':0.0,
            'being-byed':0.0,
            'being-enquired':0.0,

            'greeted':0.0,
            'byed':0.0,

            'conversation':0.0,
            'likeTalk':0.00000000000000001,

             },
 
    'dynamics':DynFun['basicDyn'],
    'goals':[\
                {'entity':    ['self'],
                                  'direction': 'max',
                                  'type':      'state',
                                  'key':   'init-norm',
                                  'weight':    .5},
    
                {'entity':    ['self'],
                                  'direction': 'max',
                                  'type':      'state',
                                  'key':   'resp-norm',
                                  'weight':    1000},
                
                {'entity':    ['self'],
                                  'direction': 'max',
                                  'type':      'state',
                                  'key':   'makeResp-norm',
                                  'weight':    .5},
                
                {'entity':    ['self'],
                                  'direction': 'max',
                                  'type':      'state',
                                  'key':   'conversation-flow-norm',
                                  'weight':    .5},
                
                {'entity':    ['self'],
                                  'direction': 'max',
                                  'type':      'state',
                                  'key':   'noRepeat-norm',
                                  'weight':    .5},
                
                {'entity':  ['self'],
                                'direction':'max',
                                'type':'state',
                                'key':'likeTalk',
                                'weight':.1},
                         
                         
                         ],


    }

classHierarchy['usr'] = {
    'parent': ['NormAgent'],
    'horizon':1,
    'actions': {'type':'XOR',
                 'key':'type',
                  'values':[{'type':'literal','value':'greet-init'},
                    {'type':'literal','value':'greet-resp'},
                    {'type':'literal','value':'bye-init'},
                    {'type':'literal','value':'bye-resp'},
                    {'type':'literal','value':'enquiry'},
                    {'type':'literal','value':'inform'},
                    {'type':'literal','value':'wait'}],
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
                  'values':[{'type':'literal','value':'greet-init'},
                    {'type':'literal','value':'greet-resp'},
                    {'type':'literal','value':'bye-init'},
                    {'type':'literal','value':'bye-resp'},
                    {'type':'literal','value':'enquiry'},
                    {'type':'literal','value':'inform'},
                    {'type':'literal','value':'wait'}],
                  'base': {'type':'XOR',
                         'key':'object',
                         'values':[{'type':'literal','value':'usr'},
                                   ],
                         },
                },
 
    'dynamics':DynFun['basicDyn'],

    }

