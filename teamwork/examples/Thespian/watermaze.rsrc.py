{'application':{'type':'Application',
          'name':'Template',
    'backgrounds': [
    {'type':'Background',
          'name':'bgTemplate',
          'title':'Standard Template with File->Exit menu',
          'size':(1173, 932),
          'style':['resizeable'],

        'menubar': {'type':'MenuBar',
         'menus': [
             {'type':'Menu',
             'name':'menuFile',
             'label':'&File',
             'items': [
                  {'type':'MenuItem',
                   'name':'menuFileExit',
                   'label':'E&xit',
                   'command':'exit',
                  },
              ]
             },
         ]
     },
         'components': [

{'type':'Button', 
    'name':'start', 
    'position':(867, 81), 
    'size':(238, 87), 
    'font':{'faceName': 'Tahoma', 'family': 'sansSerif', 'size': 18}, 
    'foregroundColor':(0, 128, 0, 255), 
    'label':'Start a New Game', 
    },

{'type':'Image', 
    'name':'Image1', 
    'position':(10, 10), 
    'size':(1131, 844), 
    'file':'../../../../Documents and Settings/meisi/My Documents/My Pictures/water maze/waterMaze1.JPG', 
    },

] # end components
} # end background
] # end backgrounds
} }
