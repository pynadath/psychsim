from teamwork.action.PsychActions import *
from teamwork.math.Keys import *

import unittest

class TestKeys(unittest.TestCase):
    def setUp(self):
        self.action = Action({'actor':'Bill',
                              'type':'picksOn',
                              'object':'Victor'})
        
    def testStateKey(self):
        key = makeStateKey('actor','power')
        self.assertEqual(str(key),"actor's power")
        newKey = key.instantiate(self.action)
        self.assert_(isinstance(newKey,list))
        self.assertEqual(len(newKey),1)
        newKey = newKey[0]
        self.assertEqual(newKey.__class__,key.__class__)
        self.assertEqual(str(newKey),"Bill's power")

    def testXML(self):
        key = makeStateKey('actor','power')
        doc = key.__xml__()
        newKey = Key()
        newKey = newKey.parse(doc.documentElement)
        self.assertEqual(key,newKey)

    def testRelationKey(self):
        key = RelationshipKey({'relater':'object',
                               'feature':'_likes',
                               'relatee':'actor'})
        newKey = key.instantiate(self.action)
        self.assert_(isinstance(newKey,list))
        self.assertEqual(len(newKey),1)
        newKey = newKey[0]
        self.assertEqual(str(newKey),'Victor _likes Bill')
        
if __name__ == '__main__':
    unittest.main()
