import os.path
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from pwl.keys import WORLD
from ui.mainwindow import Ui_MainWindow
from ui.worldview import WorldView
from ui.mapview import MapView
from world import World

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
        filename = QFileDialog.getOpenFileName(self,"PsychSim -- Open File")
        if not filename.isEmpty():
            self.openScenario(str(filename))

    def openScenario(self,filename):
        self.world = World(filename)
        settings = QSettings()
        settings.setValue('LastFile',os.path.abspath(filename))
        self.scene.displayWorld(self.world)

    @pyqtSlot() # signal with no arguments
    def on_actionSave_triggered(self):
        settings = QSettings()
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
        neighborhood = 'N01'
        agents = ['Actor0001','Actor0002','Nature',neighborhood]
        if 'Group%s' % (neighborhood) in self.world.agents:
            agents.append('Group%s' % (neighborhood))
        if 'shelter' in self.world.agents:
            agents.append('shelter')
        self.world.diagram.x.clear()
        self.world.diagram.y.clear()
        for variable in self.world.variables.values():
            if 'xpre' in variable:
                del variable['xpre']
                del variable['ypre']
                del variable['xpost']
                del variable['ypost']
        self.scene.displayWorld(self.world,agents)

    @pyqtSlot() # signal with no arguments
    def on_actionStep_triggered(self):
        self.scene.step()

    @pyqtSlot() # signal with no arguments
    def on_actionScreenshot_triggered(self):
        name = QFileDialog.getSaveFileName(self,'Save File')
        rect = self.scene.sceneRect()
        pix = QPixmap(rect.width(), rect.height())
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

    app = QApplication(sys.argv)
    app.setOrganizationName('USC ICT')
    app.setOrganizationDomain('ict.usc.edu')
    app.setApplicationName('PsychSim')

    args = parser.parse_args(args=[str(el) for el in app.arguments()][1:])

    win = PsychSimUI()
    if args.scenario is None:
        settings = QSettings()
#        filename = settings.value('LastFile').toString()
#        if filename and QFile.exists(filename):
#            win.openScenario(str(filename))
    else:
        win.openScenario(args.scenario)
    win.show()
    app.exec_()

