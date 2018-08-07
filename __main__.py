import os.path
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from pwl.keys import WORLD
from ui.mainwindow import Ui_MainWindow
from ui.worldview import WorldView
from ui.mapview import MapView
from world import World

settings = QSettings('USC ICT','PsychSim')

class PsychSimUI(QMainWindow, Ui_MainWindow):
    def __init__(self, parent=None):
        self.world = None
        super(PsychSimUI, self).__init__(parent)
        self.setupUi(self)
        self.scene = WorldView(self.graphicsView)
        self.map = MapView(self.graphicsView)
        self.graphicsView.setScene(self.scene)

    @pyqtSlot() # signal with no arguments
    def on_actionOpen_triggered(self):
        filename,types = QFileDialog.getOpenFileName(self,"PsychSim -- Open File")
        if not filename.isEmpty():
            self.openScenario(str(filename))

    def openScenario(self,filename):
        self.world = World(filename)
        self.scene.world = self.world
        self.scene.clear()
        settings.setValue('LastFile',os.path.abspath(filename))
        if settings.value('ViewCyclical') == 'yes':
            self.on_actionGround_Truth_triggered()
        else:
            self.scene.displayWorld()

    @pyqtSlot() # signal with no arguments
    def on_actionSave_triggered(self):
        filename = settings.value('LastFile').toString()
        self.scene.world.save(str(filename))
        self.scene.unsetDirty()

    @pyqtSlot() # signal with no arguments
    def on_actionQuit_triggered(self):
        app.quit()

    @pyqtSlot() # signal with no arguments
    def on_actionAgent_triggered(self):
        self.scene.colorNodes('agent')

    @pyqtSlot() # signal with no arguments
    def on_actionLikelihood_triggered(self):
        self.scene.colorNodes('likelihood')

    @pyqtSlot() # signal with no arguments
    def on_actionMap_triggered(self):
        self.graphicsView.setScene(self.map)

    @pyqtSlot() # signal with no arguments
    def on_actionGround_Truth_triggered(self):
#        self.world.clearCoords()
        self.scene.world = self.world
#        self.scene.clear()
        self.scene.displayGroundTruth(maxRows=6)
        settings.setValue('ViewCyclical','yes')

    @pyqtSlot() # signal with no arguments
    def on_actionAcyclical_triggered(self):
        self.world.clearCoords()
        self.scene.world = self.world
        self.scene.clear()
        self.scene.displayWorld()
        settings.setValue('ViewCyclical','no')

    @pyqtSlot() # signal with no arguments
    def on_actionStep_triggered(self):
        self.scene.step()

    @pyqtSlot() # signal with no arguments
    def on_actionScreenshot_triggered(self):
        name,types = QFileDialog.getSaveFileName(self,'Save File')
        rect = self.scene.sceneRect()
        pix = QImage(rect.width(), rect.height(),QImage.Format_ARGB32)
        painter = QPainter(pix)
        self.scene.render(painter,rect)
        painter.end()
        pix.save(name)

    def wheelEvent(self,event):
#        factor = 1.41**(-event.delta()/240.)
        factor = 1.41**(-event.pixelDelta().y()/240.)
        self.graphicsView.scale(factor,factor)

if __name__ == '__main__':
    import argparse
    import sys

    parser = argparse.ArgumentParser()
    parser.add_argument('scenario',default=None,nargs='?',
                        help='File containing an exising PsychSim scenario')
    parser.add_argument('-c','--cyclical',action='store_true',help='Start with cyclical view of graph')

    app = QApplication(sys.argv)
    app.setOrganizationName('USC ICT')
    app.setOrganizationDomain('ict.usc.edu')
    app.setApplicationName('PsychSim')

    args = parser.parse_args(args=[str(el) for el in app.arguments()][1:])
    if args.cyclical:
        settings.setValue('ViewCyclic','yes')
        settings.sync()
    elif settings.value('ViewCylical') is None:
        settings.setValue('ViewCyclical','no')

    win = PsychSimUI()
    if args.scenario is None:
        filename = settings.value('LastFile').toString()
        if filename and QFile.exists(filename):
            win.openScenario(str(filename))
    else:
        win.openScenario(args.scenario)
    win.showMaximized()
    app.exec_()

