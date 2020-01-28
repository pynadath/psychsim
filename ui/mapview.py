import os.path
import sys

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
try:
    from PyQt5 import QtSvg
except ImportError:
    pass

class MapView(QGraphicsScene):
    images = '/home/david/PsychSim/psychsim/domains/inequality/images'

    nations = {'algeria': {'COUNTRY_ALPHA': 1},
               'benin': {'COUNTRY_ALPHA': 2},
               'botswana': {'COUNTRY_ALPHA': 3},
               'burkinafaso': {'COUNTRY_ALPHA': 4},
               'burundi': {'COUNTRY_ALPHA': 5},
               'cameroon': {'COUNTRY_ALPHA': 6},
               'cotedivoire': {'COUNTRY_ALPHA': 8},
               'egypt': {'COUNTRY_ALPHA': 9},
               'ghana': {'COUNTRY_ALPHA': 11},
               'guinea': {'COUNTRY_ALPHA': 12},
               'kenya': {'COUNTRY_ALPHA': 13},
               'lesotho': {'COUNTRY_ALPHA': 14},
               'liberia': {'COUNTRY_ALPHA': 15},
               'madagascar': {'COUNTRY_ALPHA': 16},
               'malawi': {'COUNTRY_ALPHA': 17},
               'mali': {'COUNTRY_ALPHA': 18},
               'morocco': {'COUNTRY_ALPHA': 20},
               'mozambique': {'COUNTRY_ALPHA': 21},
               'namibia': {'COUNTRY_ALPHA': 22},
               'niger': {'COUNTRY_ALPHA': 23},
               'nigeria': {'COUNTRY_ALPHA': 24},
               'senegal': {'COUNTRY_ALPHA': 25},
               'sierraleone': {'COUNTRY_ALPHA': 26},
               'southafrica': {'COUNTRY_ALPHA': 27},
               'sudan': {'COUNTRY_ALPHA': 28},
               'swaziland': {'COUNTRY_ALPHA': 29},
               'tanzania': {'COUNTRY_ALPHA': 30},
               'togo': {'COUNTRY_ALPHA': 31},
               'tunisia': {'COUNTRY_ALPHA': 32},
               'uganda': {'COUNTRY_ALPHA': 33},
               'zambia': {'COUNTRY_ALPHA': 34},
               'zimbabew': {'COUNTRY_ALPHA': 35},
               }

    def __init__(self,parent = None):
        super(MapView,self).__init__(parent)
        self.africa = QPixmap(os.path.join(self.images,'..','Blank_Map-Africa.png'))
        self.addPixmap(self.africa)
        for nation in self.nations:
            self.nations[nation]['image'] = QPixmap(os.path.join(self.images,'%s.png' % (nation)))
            self.colorNation(nation,qRgb(255,204,0))
            item = QGraphicsPixmapItem(self.addPixmap(self.nations[nation]['image']))

    def colorNation(self,nation,newColor):
        img = self.nations[nation]['image'].toImage()
        for x in range(img.width()):
            for y in range(img.height()):
                if img.pixel(x,y) > 0:
                    oldColor = QColor(img.pixel(x,y))
                    delta = abs(oldColor.red()-204)+abs(oldColor.green()-204)+\
                            abs(oldColor.blue()-204)
                    if delta < 10:
                        img.setPixel(x,y,newColor)
        self.nations[nation]['image'].convertFromImage(img)
