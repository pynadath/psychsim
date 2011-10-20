from teamwork.action.PsychActions import *
from teamwork.action.DecisionSpace import *
import unittest

class TestDecisionSpace(unittest.TestCase):
    def setUp(self):
        self.typeList = ['hold','inspect','pass']
        
    def testSpaces(self):
        shippers = ['shipperA','shipperB']
        subSpace = DecisionSpace('type',
                                 map(lambda x:DecisionSpace('type',[x],
                                                            branchType='literal'),
                                     self.typeList),
                                 branchType='XOR',
                                 )
        actionList = subSpace.getOptions()
        self.assertEqual(len(actionList),len(self.typeList))
        for value in self.typeList:
            self.assert_([Action({'type':value})] in actionList)
        
        space = DecisionSpace('object',map(lambda x:DecisionSpace('object',[x],
                                                                  branchType='literal'),shippers),subSpace,'AND')
        actionList = space.getOptions(True)
        self.assertEqual(len(actionList),pow(len(self.typeList),len(shippers)))

    def verifySpace(self,space):
        self.assertEqual(len(space.getOptions()),len(self.typeList))
        for action in space.getOptions():
            self.assertEqual(len(action),1)
        for value in self.typeList:
            for action in space.getOptions():
                if action[0]['type'] == value:
                    break
            else:
                self.fail()
        
    def DONTtestExtract(self):
        self.typeList = ['hold','inspect','pass']
        values = map(lambda x:{'type':'literal','value':x},self.typeList)
        parsedSpace = extractSpace({'type':'AND',
                                    'key':'object',
                                    'values':[{'type':'generic',
                                               'value':'Shipper'}],
                                    'base':{'type':'XOR',
                                            'key':'type',
                                            'values':values}})
        self.verifySpace(parsedSpace)
        doc = parsedSpace.__xml__()
        space = parseSpace(doc.documentElement)
        self.verifySpace(space)

    def DONTtestOR(self):
        space = DecisionSpace()
        space.directAdd([Action({'actor':'Allies',
                                 'type':'DenyUseAction',
                                 'object':'Iraq'})])
        spec = {'type':'OR',
                'values':[{'type':'decision',
                           'value':{'type':'XOR',
                                    'key':'object',
                                    'values':[{'type':'generic','value':'US'}],
                                    'base': {'type':'XOR',
                                             'key':'type',
                                             'values':[{'type':'literal','value':'requestgiveMoneyTo'},
                                                       {'type':'literal','value':'offernotax'},
                                                       {'type':'literal','value':'reject'},
                                                       {'type':'literal','value':'accept'}],
                                             },
                                    },
                           },
                          {'type':'decision',
                           'value':{'type':'AND',
                                    'key':'object',
                                    'values':[{'type':'relationship','value':'ownMarket'}],
                                    'base':{'type':'XOR',
                                            'key':'type',
                                            'values':[{'type':'literal','value':'tax'},
                                                      {'type':'literal','value':'notax'}],
                                            },
                                    },
                           },
                          ],
                }
        space = extractSpace(spec)
        self.assertEqual(len(space.getOptions()),6)

    def DONTtestELECT(self):
        space = extractSpace({'type':'OR',
		'values':[{'type':'decision',
			   'value':{'type':'XOR',
				    'key':'object',
				    'values':[{'type':'generic','value':'US'}],
				    'base': {'type':'XOR',
					     'key':'type',
					     'values':[{'type':'literal','value':'requestgiveMoneyTo'},
						       {'type':'literal','value':'offernotax'},
						       {'type':'literal','value':'reject'},
						       {'type':'literal','value':'accept'}],
					     },
				    },
			   },
			  {'type':'decision',
			   'value':{'type':'AND',
				    'key':'object',
				    'values':[{'type':'relationship','value':'ownMarket'}],
				    'base':{'type':'XOR',
					    'key':'type',
					    'values':[{'type':'literal','value':'tax'},
						      {'type':'literal','value':'notax'}],
					    },
				    },
			   },
			  ],
		})
        count = len(space.getOptions())
        doc = space.__xml__()
        space = parseSpace(doc.documentElement)
        self.assertEqual(len(space.getOptions()),count)

    def DONTtestTiger(self):
        space = extractSpace({'type':'XOR',
               'key':'type',
               'values':[{'type':'literal','value':'openRight'},
                         {'type':'literal','value':'openLeft'},
                         {'type':'literal','value':'listen'},
                         ],
               })
        self.assertEqual(len(space.getOptions()),3)
        
if __name__ == '__main__':
    unittest.main()
