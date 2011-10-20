from teamwork.agent.AgentClasses import *
from teamwork.dynamics.pwlDynamics import *

#from ChatDynamics import *
from RedRidingHoodDynamics import *

classHierarchy['NormAgent'] = {
    'parent': [],
    'horizon':2,
    'depth':2,
    'state':{\
            'type':1.0,
            
            'alive':1.0,
            'sameLocation':1.0,
            'actAlive':1.0,

            'likeMove':-1,
            'likeTalk':-1,
            'specialRule':1.0,
             },
 
    'dynamics':[DynFun['basicDyn'],DynFun['RedDyn']],

    }

classHierarchy['red'] = {
    'parent': ['NormAgent'],
    'horizon':2,
    'depth':2,
    'state':{\
            'identity':1,
            'location':0.2,

             },
    'actions': {
                'type':'XOR',
                'key':'type',
                'values':[\
                          {'type':'literal','value':'tell-about-granny'},
                          {'type':'literal','value':'inform-about-granny'},
                          {'type':'literal','value':'move2'},
                          {'type':'literal','value':'wait'},
                         ],
                
                'base': {'type':'XOR',
                         'key':'object',
                         'values':[{'type':'generic','value':'wolf'}],
                         },
                },
			  
		
 
   'goals':[\
             {'entity':['self'],'direction':'max','type':'state',
              'key':'alive','weight':5.},
             {'entity':['self'],'direction':'max','type':'state',
              'key':'actAlive','weight':1000.},
             {'entity':['self'],'direction':'max','type':'state',
              'key':'sameLocation','weight':1000.},
            {'entity':['self'],'direction':'max','type':'state',
              'key':'specialRule','weight':1000.},
            
            {'entity':['self'],'direction':'max','type':'state',
              'key':'likeMove','weight':.5},
            {'entity':['self'],'direction':'max','type':'state',
              'key':'likeTalk','weight':.5},
             ],

    }


classHierarchy['wolf'] = {
    'parent': ['NormAgent'],
    'horizon':2,
    'depth':2,
    'state':{\
            'location':0.4,
            'full':0.0,
            'identity':-1,
             },
      'actions': {'type':'XOR',
                'key':'type',
                'values':[{'type':'literal','value':'eat'},
                          {'type':'literal','value':'enquiry-about-granny'},
                          {'type':'literal','value':'wait'},
                        {'type':'literal','value':'move2'},
                        {'type':'literal','value':'changeIdentity'},
                          ],
                'base': {'type':'XOR',
                        'key':'object',
                        'values':[{'type':'generic','value':'red'}],
                                  
                         },
                },

 
    'goals':[
             {'entity':['self'],'direction':'max','type':'state',
              'key':'full','weight':1.},
             {'entity':['self'],'direction':'max','type':'state',
              'key':'alive','weight':5.},
              
             {'entity':['self'],'direction':'max','type':'state',
              'key':'actAlive','weight':1000.},
             {'entity':['self'],'direction':'max','type':'state',
              'key':'sameLocation','weight':1000.},
             {'entity':['self'],'direction':'max','type':'state',
              'key':'specialRule','weight':1000.},
             

             {'entity':['self'],'direction':'max','type':'state',
              'key':'likeMove','weight':.5},
            {'entity':['self'],'direction':'max','type':'state',
              'key':'likeTalk','weight':.5},
            
            {'entity':['red'],'direction':'min','type':'state',
              'key':'alive','weight':.1},  
             ],

    }

