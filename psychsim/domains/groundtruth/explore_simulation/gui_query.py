import sys
import argparse

try:
    import psychsim.domains.groundtruth.explore_simulation.query_gt as q_gt
except ModuleNotFoundError:
    import query_gt as q_gt

try:
    import psychsim.domains.groundtruth.explore_simulation.query_gt_consts as consts
except ModuleNotFoundError:
    import query_gt_consts as consts

# import pyqtgraph as pg

from PyQt5.uic import loadUiType
 
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import (
    FigureCanvasQTAgg as FigureCanvas,
    NavigationToolbar2QT as NavigationToolbar)


# import matplotlib.pyplot as plt
import numpy as np

Ui_MainWindow, QMainWindow = loadUiType('psychsim/domains/groundtruth/explore_simulation/GUI/new_MainWindow2.ui')


from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QApplication, QMainWindow
# from PyQt5.QtWidgets import QDialog
# from GUI.MainWindow import Ui_MainWindow
from psychsim.domains.groundtruth.explore_simulation.GUI.FilterDialog import Ui_FilterDialog
from psychsim.domains.groundtruth.explore_simulation.GUI.SelectDialog import Ui_SelectDialog
from psychsim.domains.groundtruth.explore_simulation.GUI.GetStats import Ui_GetStats
from psychsim.domains.groundtruth.explore_simulation.GUI.CreateSample import Ui_CreateSample
from psychsim.domains.groundtruth.explore_simulation.GUI.DisplayOneSample import Ui_Display_One_Sample_Dialog
from psychsim.domains.groundtruth.explore_simulation.GUI.GetEntityAttributes import Ui_EntityName
from psychsim.domains.groundtruth.explore_simulation.GUI.DeactivateFilter import Ui_DeactivateFilter
from psychsim.domains.groundtruth.explore_simulation.GUI.ReactivateFilter import Ui_ReactivateFilter
from psychsim.domains.groundtruth.explore_simulation.GUI.CountDialog import Ui_CountDialog

# from GUI.GetDialog import Ui_GetDialog


class Main(QMainWindow, Ui_MainWindow):
    def __init__(self, ):
        super(Main, self).__init__()
        #    def __init__(self, parent=None):
        # super(MainWindow, self).__init__(parent)
        self.subwindowList = {}

        self.setupUi(self)
        self.fig_dict = {}
        self.mplfigs.itemClicked.connect(self.changefig)
        fig = Figure()
        self.addmpl(fig)

        #self.filtersText.clicked.connect(self.on_Filter)
        self.setupQueries()
        self.setupButtons()
        self.initSubWindows()

    def setupButtons(self):
        self.queryBox.activated[str].connect(self.on_Query)
        self.resetButton.clicked.connect(self.on_reset)
        self.helpButton.clicked.connect(self.on_help)
        self.samplesText.itemDoubleClicked.connect(self.samples_dclicked)
        self.apply_filter.clicked.connect(self.apply_filter_clicked)    
        self.activate_filter.clicked.connect(self.activate_filter_clicked)    
        self.deactivate_filter.clicked.connect(self.deactivate_filter_clicked)
        # self.delete_filter.clicked.connect(self.delete_filter_clicked)    
        self.CreateSample.clicked.connect(self.show_create_sample)
        self.DisplaySamples.clicked.connect(self.show_display_samples_clicked)


    def apply_filter_clicked(self):
        self.show_apply_filter()
            
    def samples_dclicked(self, qmodelindex):
        item = self.samplesText.currentItem()
        logparser.display_one_sample(p_name=item.text())
        print(item.text())
                                         
    def delete_filter_clicked(self, qmodelindex):
        item = self.filterText.currentItem().text().split(':')
        logparser.delete_filter(p_name=item[0])
        print(item[0])
    def activate_filter_clicked(self, qmodelindex):
        if self.filterText.currentItem():
            item = self.filterText.currentItem().text().split(':')
            logparser.reactivate_filter(p_name=item[0])
            self.updateFilterList()
            print(item[0])
        else:
            print('Must firest select a filter')
    def deactivate_filter_clicked(self, qmodelindex):
        if self.filterText.currentItem():
            item = self.filterText.currentItem().text().split(':')
            logparser.deactivate_filter(p_name=item[0])
            self.updateFilterList()
            print(item[0])
        else:
            print('Must first select a filter')


    def updateFilterList(self):
        self.filterText.clear()
        self.filterText.addItems([logparser.filters_to_str(f) for f in logparser.filter_list])

                                         
    def changefig(self, item):
        text = item.text()
        self.rmmpl()
        self.addmpl(self.fig_dict[text])

    def addfig(self, name, fig):
        self.fig_dict[name] = fig
        self.mplfigs.addItem(name)

    def addmpl(self, fig):
        self.canvas = FigureCanvas(fig)
        self.mplvl.addWidget(self.canvas)
        self.canvas.draw()
        self.toolbar = NavigationToolbar(self.canvas, self.mplwindow, coordinates=True)
        self.mplvl.addWidget(self.toolbar)
        # This is the alternate toolbar placement. Susbstitute the three lines above
        # for these lines to see the different look.
        #self.toolbar = NavigationToolbar(self.canvas,self, coordinates=True)
        #self.addToolBar(self.toolbar)

    def rmmpl(self,):
        self.mplvl.removeWidget(self.canvas)
        self.canvas.close()
        self.mplvl.removeWidget(self.toolbar)
        self.toolbar.close()
        

        
    def initSubWindows(self):
        self.setup_apply_filter()
        self.setup_select_nactors()
        self.setup_get_stats()
        self.setup_create_sample()
        self.setup_display_one_sample()
        self.setup_get_attribute_names()
        self.setup_deactivate_filter()
        self.setup_reactivate_filter()
        self.setup_count_actors()
        

    def show_get_ndays(self):
        logparser.get_ndays(None)

    def show_display_samples_clicked(self):
        self.on_Query('display_samples')
        # the following should not be necessary since I am above calling the exact same code that
        # does not require a repaint - that code is called from the query combobox and works fine
        # without a repaint--- ie pyqt5 is garbage
        # for some reason therefore the event loop must be sleeping
        # or the automatic repaint doesn't happen when it is called from a button as opposed
        # to a combobox??
        self.historyEdit.repaint()
        
        
    def show_get_nactors(self):
        logparser.get_nactors(None)
       
    def show_get_entities(self):    
        logparser.get_entities(None)

    def setup_get_attribute_names(self):
        self.GetAttributes = QtWidgets.QDialog()
        self.get_attributes = Ui_EntityName()
        self.get_attributes.setupUi(self.GetAttributes)
        self.get_attributes.entityTypes.addItems(logparser.entities_att_list.keys())        
        self.get_attributes.buttonBox.accepted.connect(self.on_get_attribute_names)
    def on_get_attribute_names(self):
        p_name = self.get_attributes.entityTypes.currentText()
        logparser.get_attributes(p_entity=p_name, buffer=None)
    def show_get_attribute_names(self):
        self.GetAttributes.show()
        
        

    def show_reset_selection(self):
        logparser.reset_selection(buffer=sys.stdout)

    def show_show_selection(self):    
        logparser.display_actor_selection()

    def show_show_filters(self):    
        logparser.display_filters()


    def show_display_samples(self):
        logparser.display_samples()
        

    def setup_create_sample(self):
        self.CreateSample = QtWidgets.QDialog()
        self.create_sample = Ui_CreateSample()
        self.create_sample.setupUi(self.CreateSample)
        self.create_sample.buttonBox.accepted.connect(self.on_create_sample)
    def on_create_sample(self):
        p_name = self.create_sample.nameLine.text()
        s1, s2= logparser.get_sample(p_name=p_name)
        if (not s1 and not s2):
            self.samplesText.addItem(p_name)
            logparser.save_sample(p_name)
    def show_create_sample(self):
        self.CreateSample.show()
        self.create_sample.nameLine.setFocus()
  


        
    # def setup_save_sample(self):
    #     self.SaveSample = QtWidgets.QDialog()
    #     self.save_sample = Ui_SaveSample()
    #     self.save_sample.setupUi(self.SaveSample)
    # def on_save_sample(self):
    #     self.save_sample.setupUi(self.SaveSample)
    #     p_name = self.save_sample.nameLine.text()
    #     logparser.select_nactors(p_n=p_n, p_mode_select=p_sel)
    #     s1, s2= logparser.get_sample(p_name=p_name)
    #     if (not s1 and not s2):
    #         self.samplesText.addItem(p_name)
    # def show_save_sample(self,selected):
    #     self.SaveSample.show()
        
    def setup_display_one_sample(self):
        self.DisplayOneSample = QtWidgets.QDialog()
        self.display_one_sample = Ui_Display_One_Sample_Dialog()
        self.display_one_sample.setupUi(self.DisplayOneSample)
        self.display_one_sample.buttonBox.accepted.connect(self.on_display_one_sample)
    def on_display_one_sample(self):
        self.display_one_sample.setupUi(self.DisplayOneSample)
        p_name = self.display_one_sample.nameLine.text()
        logparser.display_one_sample(p_name=p_name)
    def show_display_one_sample(self):
        self.DisplayOneSample.show()

    def setup_select_nactors(self):
        self.SelectDialog = QtWidgets.QDialog()
        self.select_nactors = Ui_SelectDialog()
        self.select_nactors.setupUi(self.SelectDialog)
        self.select_nactors.buttonBox.accepted.connect(self.on_select_nactors)
        #self.select_nactors.numberspinBox.
        self.select_nactors.selBox.addItems(consts.MODE_SELECTION_VALUES_IN)
    def on_select_nactors(self):
        print("#######################\n")
        p_sel = self.select_nactors.selBox.currentText()
        p_n = self.select_nactors.numberspinBox.value()
        logparser.select_nactors(p_n=p_n, p_mode_select=p_sel)
    def show_select_n_actors(self):
        self.SelectDialog.show()

        
    def setup_deactivate_filter(self):
        self.DeactivateFilter = QtWidgets.QDialog()
        self.deactivate_filter = Ui_DeactivateFilter()
        self.deactivate_filter.setupUi(self.DeactivateFilter)
        self.deactivate_filter.buttonBox.accepted.connect(self.on_deactivate_filter)
        # self.deactivate_filter.attributeBox.addItems(logparser.entities_att_list['Actor'])
    def on_deactivate_filter(self):
        print("#######################\n")
        p_name = self.deactivate_filter.comboBox.currentText()
        self.f = logparser.deactivate_filter(p_name=p_name)
        self.updateFilterList()
    def show_deactivate_filter(self):
        self.deactivate_filter.comboBox.addItems([f['name'] for f in logparser.filter_list])
        self.DeactivateFilter.show()


        
    def setup_reactivate_filter(self):
        self.ReactivateFilter = QtWidgets.QDialog()
        self.reactivate_filter = Ui_ReactivateFilter()
        self.reactivate_filter.setupUi(self.ReactivateFilter)
        self.reactivate_filter.buttonBox.accepted.connect(self.on_reactivate_filter)
        # self.deactivate_filter.attributeBox.addItems(logparser.entities_att_list['Actor'])
    def on_reactivate_filter(self):
        print("#######################\n")
        p_name = self.reactivate_filter.comboBox.currentText()
        self.f = logparser.reactivate_filter(p_name=p_name)
        self.updateFilterList()
    def show_reactivate_filter(self):
        self.reactivate_filter.comboBox.addItems([f['name'] for f in logparser.filter_list])
        self.ReactivateFilter.show()

    def setup_apply_filter(self):
        self.FilterDialog = QtWidgets.QDialog()
        self.apply_filter = Ui_FilterDialog()
        self.apply_filter.setupUi(self.FilterDialog)
        self.apply_filter.buttonBox.accepted.connect(self.on_apply_filter)
        self.apply_filter.attributeBox.addItems(logparser.entities_att_list['Actor'])
        self.apply_filter.operatorBox.addItems(['<','>','=','<=','>='])

    def on_apply_filter(self):
        print("#######################\n")
        p_att = self.apply_filter.attributeBox.currentText()
        p_op = self.apply_filter.operatorBox.currentText()
        p_daylst = range(self.apply_filter.dayspinBox.value(),self.apply_filter.dayspinBox_2.value())
        p_val = self.apply_filter.valueSpinBox.value()
        p_name = self.apply_filter.nameLine.text()
        self.f = logparser.apply_filter(p_daylst, p_att, p_val, p_op, p_name=p_name)
        self.filterText.clear()
        self.filterText.addItems([logparser.filters_to_str(f) for f in logparser.filter_list])
        #for f in logparser.filterList:

    def show_apply_filter(self):
        self.apply_filter.dayspinBox_2.setRange(1,logparser.n_days)
        self.apply_filter.dayspinBox.setRange(1,logparser.n_days)
        self.apply_filter.dayspinBox_2.setValue(logparser.n_days)
        self.apply_filter.dayspinBox.setValue(1)
        self.FilterDialog.show()
        
    def setup_get_stats(self):
        self.StatsDialog = QtWidgets.QDialog()
        self.get_stats = Ui_GetStats()
        self.get_stats.setupUi(self.StatsDialog)
        self.get_stats.buttonBox.accepted.connect(self.on_get_stats)
        self.get_stats.toolmenuAtt = QtWidgets.QMenu(self)
        for k in logparser.entities_att_list['Actor']:
            action = self.get_stats.toolmenuAtt.addAction(k)
            action.setCheckable(True)
        self.get_stats.Attributes.setMenu(self.get_stats.toolmenuAtt)
        self.get_stats.toolmenuFct = QtWidgets.QMenu(self)
        for k in consts.STAT_FCT_VALUES_IN:
            action = self.get_stats.toolmenuFct.addAction(k)
            action.setCheckable(True)
        self.get_stats.Functions.setMenu(self.get_stats.toolmenuFct)
        #self.get_stats.sampleList.addItems()

    def on_get_stats(self):
        print("#######################\n")
        p_snames = []
        p_att = []
        p_fct_list = []
        p_daylst = list(range(self.get_stats.dayspinBox_1.value(),self.get_stats.dayspinBox_2.value()))
        p_name  = self.get_stats.name.text()
        for action in self.get_stats.toolmenu.actions():
            if action.isChecked():
                p_snames.append(action.text())
        for action in self.get_stats.toolmenuAtt.actions():
            if action.isChecked():
                p_att.append(action.text())
        for action in self.get_stats.toolmenuFct.actions():
            if action.isChecked():
                p_fct_list.append(action.text())
        figure=Figure()
        logparser.get_stats(p_att, p_fct_list, p_days=p_daylst,p_sample_names=p_snames, fig=figure, using_gui=True)
        main.addfig(p_name, figure)
        self.StatsDialog.hide()
    def show_get_stats(self):
        self.get_stats.dayspinBox_2.setRange(1,logparser.n_days)
        self.get_stats.dayspinBox_1.setRange(1,logparser.n_days)
        self.get_stats.dayspinBox_2.setValue(logparser.n_days)
        self.get_stats.dayspinBox_1.setValue(1)
        self.get_stats.toolmenu = QtWidgets.QMenu(self)
        for k in logparser.samples.keys():
            action = self.get_stats.toolmenu.addAction(k)
            action.setCheckable(True)
        self.get_stats.Samples.setMenu(self.get_stats.toolmenu)
        self.StatsDialog.show()

    def setup_count_actors(self):
        self.CountDialog = QtWidgets.QDialog()
        self.count_actors = Ui_CountDialog()
        self.count_actors.setupUi(self.CountDialog)
        self.count_actors.buttonBox.accepted.connect(self.on_count_actors)
        self.count_actors.attributeBox.addItems(logparser.entities_att_list['Actor'])
        self.count_actors.operatorBox.addItems(['<','>','=','<=','>='])
    def on_count_actors(self):
        print("#######################\n")
        p_att = self.count_actors.attributeBox.currentText()
        p_daylst = range(self.count_actors.dayspinBox_1.value(),self.count_actors.dayspinBox_2.value())
        p_op = self.count_actors.operatorBox.currentText()
        p_val = self.count_actors.valueSpinBox.value()
        logparser.count_actors(p_daylst, p_att, p_op, p_val, sys.stdout)
        self.CountDialog.hide()
    def show_count_actors(self):
        self.count_actors.dayspinBox_2.setRange(1,logparser.n_days)
        self.count_actors.dayspinBox_1.setRange(1,logparser.n_days)
        self.count_actors.dayspinBox_2.setValue(logparser.n_days)
        self.count_actors.dayspinBox_1.setValue(1)
        self.CountDialog.show()

        
    def setupQueries(self):
        self.commands=consts.HELP['commands']
        sep_flag = False
        for cmdType in self.commands.keys():
            print(cmdType)
            if sep_flag:
                self.queryBox.insertSeparator(60) 
            for cmdInst in self.commands[cmdType].keys():
                self.cmd = cmdInst[0].replace(' ','_')
                print(self.cmd)
                self.queryBox.addItem(self.cmd)
                self.subwindowList[self.cmd] = self.commands[cmdType][cmdInst]
                sep_flag = True
        
    def on_execute(self,selected):
        self.parse_execute_query()

    def on_help(self,selected):
        print("#######################\n")
        q_gt.print_help()

    def on_Query(self,selected):
        print("#######################")
        print(selected)
        print("#######################")
        # if (selected == "apply filter"):
        #     self.filter.show()
        self.method = getattr(self, "show_" + selected, lambda: 'self.show_create')
        return self.method()

    def on_reset(self,selected):
        print(selected)
        logparser.reset_selection(None)

        
    def __del__(self):
        sys.stdout = sys.__stdout__

    def parse_execute_query(self,buffer=sys.stdout):
        # logparser.init_queryparams()
        logparser.command = str(self.queryBox.currentText())
        self.query = logparser.command
        #self.query = self.query + ' -' + 'agent ' + str(self.comboBox_agent.currentText())
        #self.query = self.query + ' -' + 'round ' + str(self.comboBox_round.currentText())
        #self.query = self.query + ' -' + 'action ' + str(self.comboBox_action.currentText())
        print(">>>>>> Query: " + self.query + "\n")
        logparser.execute_query(self.query,buffer=sys.stdout)
        sys.stdout.flush()

class unBuffered(object):
    def __init__(self, stream):
       self.stream = stream
    def write(self, data):
       self.stream.moveCursor(QtGui.QTextCursor.End)
       self.stream.insertPlainText(data)
       self.flush()
    #def writelines(self, datas):
    #   self.stream.writelines(datas)
    #   self.flush()

    def flush(self):
       self.stream.moveCursor(QtGui.QTextCursor.End)
       
    def __getattr__(self, attr):
       return getattr(self.stream, attr)


class OutLog:
    def __init__(self, edit, out=None, color=None):
        """(edit, out=None, color=None) -> can write stdout, stderr to a
        QTextEdit.
        edit = QTextEdit
        out = alternate stream ( can be the original sys.stdout )
         """
        self.edit = edit
        self.out = None
 
    def write(self, m):
        self.edit.moveCursor(QtGui.QTextCursor.End)
        self.edit.insertPlainText( m )

    def flush(self):
        pass
    
if __name__ == "__main__":

    argp = argparse.ArgumentParser()
    argp.add_argument('-i', metavar='instance', type=str, help='Instance number to process.')
    argp.add_argument('-r', metavar='run', type=str, help='Run number to process.')
    argp.add_argument("--test", help="Test the tool yourself", action="store_true")

    args = argp.parse_args()


    if (args.test):
        app = QApplication(sys.argv)
        logparser = q_gt.LogParser(args.i, args.r)
        main = Main()
        sys.stdout = unBuffered(main.historyEdit)

        
        fig2 = Figure()
        ax1f2 = fig2.add_subplot(121)
        ax1f2.plot(np.random.rand(5))
        ax2f2 = fig2.add_subplot(122)
        ax2f2.plot(np.random.rand(10))

        fig3 = Figure()
        ax1f3 = fig3.add_subplot(111)
        ax1f3.pcolormesh(np.random.rand(16,16))

 

        main.addfig('Two plots', fig2)
        main.addfig('Pcolormesh Example eg Health', fig3)

        main.filterList = OutLog(main.filterText)
        main.historyEdit.setPlainText("Hi Stacy\n")
        main.show()
        sys.exit(app.exec_())
    elif (args.autotest):
        logparser.demo(autotest=True)
    elif (args.demo):
        logparser.demo(autotest=False)
    else:
        argp.print_help()
        # exit(0)

