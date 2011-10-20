from teamwork.agent.AgentClasses import *
from teamwork.dynamics.pwlDynamics import *

from UAIDynamics import *

classHierarchy['character'] = {
    'parent': [],
    'horizon':2,
    'depth':4,
    'dynamics':[DynFun['basicDyn']],
    'state':{\
            'NS':0.0,
            'init-norm':0.0,
            'resp-norm':0.0,
            'being-offered':0.0,
            'being-enquired':0.0,
            'topic':0.0,
             },
    }

classHierarchy['vc1'] = {
    'parent': ['character'],
    'state':{\
            'positive-force':0.0,
             'negative-force':0.0,
             'offered-drink':0.0,
    },
    'goals':[\
             {'entity':['self'],'direction':'max','type':'state',
             'key':'NS','weight':5.},
            
            {'entity':['usr1'],'direction':'max','type':'state',
              'key':'NS','weight':1.},
            
             {'entity':['usr1'],'direction':'max','type':'state',
             'key':'positive-force','weight':.5},
    
            {'entity':['usr1'],'direction':'min','type':'state',
             'key':'negative-force','weight':.5},
            
            {'entity':['self'],'direction':'max','type':'state',
             'key':'init-norm','weight':5.},
            
            {'entity':['self'],'direction':'max','type':'state',
             'key':'resp-norm','weight':5.},
            
             ],
        
     'actions': {'type':'OR',
		'values':[{'type':'decision',
			   'value':{'type':'XOR',
				    'key':'object',
				    'values':[{'type':'generic','value':'usr1'}],
				    'base': {'type':'XOR',
					     'key':'type',
					     'values':[\
                                                       {'type':'literal','value':'offer-drink'},
                                                       {'type':'literal','value':'accept-drink'},
                                                       {'type':'literal','value':'reject-drink'},
                                                       {'type':'literal','value':'offer-physicaltouch'},
                                                       {'type':'literal','value':'accept-physicaltouch'},
                                                       {'type':'literal','value':'reject-physicaltouch'},
                                                       {'type':'literal','value':'enquiry'},
                                                       {'type':'literal','value':'inform'},
                                                       {'type':'literal','value':'inform-negHistory'},
                                                       
                                                       
						       ],
					     },
				    },
			   },
                          
                          {'type':'decision',
			   'value':{'type':'XOR',
					     'key':'type',
					     'values':[\
                                                       {'type':'literal','value':'wait'},     
						       ],
				    },
			   },
                         
			  ],
		},

    }


classHierarchy['usr1'] = {
    'parent': ['character'],
    'state':{\
            'positive-force':0.0,
             'negative-force':0.0,
             'offered-drink':0.0,
    },
    'goals':[\
             {'entity':['self'],'direction':'max','type':'state',
             'key':'NS','weight':5.},
            
            {'entity':['vc1'],'direction':'max','type':'state',
              'key':'NS','weight':1.},
            
             {'entity':['vc1'],'direction':'max','type':'state',
             'key':'positive-force','weight':.5},
    
            {'entity':['vc1'],'direction':'min','type':'state',
             'key':'negative-force','weight':.5},
            
            {'entity':['self'],'direction':'max','type':'state',
             'key':'init-norm','weight':5.},
            
            {'entity':['self'],'direction':'max','type':'state',
             'key':'resp-norm','weight':5.},   
             ],
        
     'actions': {'type':'OR',
		'values':[{'type':'decision',
			   'value':{'type':'XOR',
				    'key':'object',
				    'values':[{'type':'generic','value':'vc1'}],
				    'base': {'type':'XOR',
					     'key':'type',
					     'values':[\
                                                       {'type':'literal','value':'offer-drink'},
                                                       {'type':'literal','value':'accept-drink'},
                                                       {'type':'literal','value':'reject-drink'},
                                                       {'type':'literal','value':'offer-physicaltouch'},
                                                       {'type':'literal','value':'accept-physicaltouch'},
                                                       {'type':'literal','value':'reject-physicaltouch'},
                                                       {'type':'literal','value':'enquiry'},
                                                       {'type':'literal','value':'inform'},
                                                       {'type':'literal','value':'inform-negHistory'},
                                                       
						       ],
					     },
				    },
			   },
                          
                          {'type':'decision',
			   'value':{'type':'XOR',
					     'key':'type',
					     'values':[\
                                                       {'type':'literal','value':'wait'},
                                                       
						       ],
				    },
			   },
                         
			  ],
		},

    }



classHierarchy['vc2'] = {
    'parent': ['character'],
    'state':{\
             'health':0.0,
            'friendship':0.0,
            'pleasure':0.0,
    },
    'goals':[\
            {'entity':['self'],'direction':'max','type':'state',
             'key':'NS','weight':5.},
            
            {'entity':['usr2'],'direction':'max','type':'state',
              'key':'NS','weight':1.},
            
            {'entity':['self'],'direction':'max','type':'state',
             'key':'health','weight':1.},
            
            {'entity':['self'],'direction':'max','type':'state',
             'key':'friendship','weight':5.},
            
            {'entity':['self'],'direction':'max','type':'state',
             'key':'pleasure','weight':5.},
            
            {'entity':['self'],'direction':'max','type':'state',
             'key':'init-norm','weight':5.},
            
            {'entity':['self'],'direction':'max','type':'state',
             'key':'resp-norm','weight':5.},
            
             ],
        
     'actions': {'type':'OR',
		'values':[{'type':'decision',
			   'value':{'type':'XOR',
				    'key':'object',
				    'values':[{'type':'generic','value':'usr2'}],
				    'base': {'type':'XOR',
					     'key':'type',
					     'values':[\
                                                       {'type':'literal','value':'offer-unsafesex'},
                                                       {'type':'literal','value':'accept-unsafesex'},
                                                       {'type':'literal','value':'reject-unsafesex'},
                                                       {'type':'literal','value':'offer-safesex'},
                                                       {'type':'literal','value':'accept-safesex'},
                                                       {'type':'literal','value':'reject-safesex'},
                                                       
						       ],
					     },
				    },
			   },
                          
                          {'type':'decision',
			   'value':{'type':'XOR',
					     'key':'type',
					     'values':[\
                                                       {'type':'literal','value':'wait'},     
						       ],
				    },
			   },
                         
			  ],
		},

    }

classHierarchy['usr2'] = {
    'parent': ['character'],
    'state':{\
             'health':0.0,
            'friendship':0.0,
            'pleasure':0.0,
    },
    'goals':[\
            {'entity':['self'],'direction':'max','type':'state',
             'key':'NS','weight':5.},
            
            {'entity':['vc2'],'direction':'max','type':'state',
              'key':'NS','weight':1.},
            
            {'entity':['self'],'direction':'max','type':'state',
             'key':'health','weight':5.},
            
            {'entity':['self'],'direction':'max','type':'state',
             'key':'friendship','weight':5.},
            
            {'entity':['self'],'direction':'max','type':'state',
             'key':'pleasure','weight':3.},
            
            {'entity':['self'],'direction':'max','type':'state',
             'key':'init-norm','weight':5.},
            
            {'entity':['self'],'direction':'max','type':'state',
             'key':'resp-norm','weight':5.},
            
             ],
        
     'actions': {'type':'OR',
		'values':[{'type':'decision',
			   'value':{'type':'XOR',
				    'key':'object',
				    'values':[{'type':'generic','value':'vc2'}],
				    'base': {'type':'XOR',
					     'key':'type',
					     'values':[\
                                                        {'type':'literal','value':'offer-unsafesex'},
                                                       {'type':'literal','value':'accept-unsafesex'},
                                                       {'type':'literal','value':'reject-unsafesex'},
                                                       {'type':'literal','value':'offer-safesex'},
                                                       {'type':'literal','value':'accept-safesex'},
                                                       {'type':'literal','value':'reject-safesex'},
                                                      
						       ],
					     },
				    },
			   },
                          
                          {'type':'decision',
			   'value':{'type':'XOR',
					     'key':'type',
					     'values':[\
                                                       {'type':'literal','value':'wait'},
                                                       
						       ],
				    },
			   },
                         
			  ],
		},

    }
