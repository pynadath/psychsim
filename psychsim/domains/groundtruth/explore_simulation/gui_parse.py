import sys
import argparse
import query_gt as q_gt
import pyqtgraph as pg
import query_gt_consts as q_gt_c
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QApplication, QMainWindow
# from PyQt5.QtWidgets import QDialog
from GUI.MainWindow import Ui_MainWindow
from GUI.FilterDialog import Ui_FilterDialog
from GUI.SelectDialog import Ui_SelectDialog
import query_gt_consts as consts
# from GUI.GetDialog import Ui_GetDialog


class MainWindow(QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        #    def __init__(self, parent=None):
        # super(MainWindow, self).__init__(parent)
        self.switch = {}
        self.subwindowList = []
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.ui.queryBox.activated[str].connect(self.on_Query)
        self.ui.resetButton.clicked.connect(self.on_reset)
        self.ui.helpButton.clicked.connect(self.on_help)
        self.setupQueries()
        self.initSubWindows()
        # self.ui.executeButton.clicked.connect(self.on_execute())
        # self.graphicsView = pg.PlotWidget(self.ui.historyEdit)
        # self.L = [1,2,3,4,5]
        # self.graphicsView.plot(self.L) #this line doesn't work
        # 
        


    def initSubWindows(self):
        self.setup_apply_filter()
        self.setup_select_nactors()

    def show_get_ndays(self):
        logparser.get_ndays(buffer)

    def show_get_nactors(self):
        logparser.get_nactors(buffer)
       
    def show_get_entities(self):    
        logparser.get_entities(buffer)

    def show_reset_selection(self):
        logparser.reset_selection(buffer)

    def show_show_selection(self):    
        logparser.show_selection(buffer)

    def show_show_filters(self):    
        logparser.show_filters(buffer)
        

        
    def setup_select_nactors(self):
        self.select_nactors = Ui_SelectDialog()
        self.select_nactors.setupUi(self.select_nactors)
        self.select_nactors.buttonBox.accepted.connect(self.on_select_nactors)
        #self.select_nactors.numberspinBox.
        self.select_nactors.selBox.addItems(consts.MODE_SELECTION_VALUES_IN)
    def on_select_nactors(self):
        print("#######################\n")
        p_sel = self.apply_filter.selBox.currentText()
        p_n = self.select_nactors.numberspinBox.value()
        logparser.select_nactors(p_n=str(p_n), p_mode_select=p_sel)
    def show_select_nactors(self):
        self.select_nactors.show()

        
    def setup_apply_filter(self):
        self.apply_filter = Ui_FilterDialog()
        self.apply_filter.setupUi(self.apply_filter)
        self.apply_filter.buttonBox.accepted.connect(self.on_apply_filter)
        self.apply_filter.attributeBox.addItems(logparser.entities_att_list['Actor'])
        self.apply_filter.operatorBox.addItems(['<','>','=','<=','>='])
    def on_apply_filter(self):
        print("#######################\n")
        p_att = self.apply_filter.attributeBox.currentText()
        p_op = self.apply_filter.operatorBox.currentText()
        p_day = self.apply_filter.dayspinBox.value()
        p_val = self.apply_filter.valueSpinBox.value()
        p_name = self.apply_filter.nameLine.text()
        logparser.apply_filter(p_day=str(p_day), p_att=p_att, p_val=p_val, p_operator=p_op, p_name=p_name)
    def show_apply_filter(self):
        self.apply_filter.show()

        
    def setupQueries(self):
        self.commands=consts.HELP['commands']
        print(self.commands.keys())
        for self.cmds in self.commands[consts.CATEGORY_GENERAL_INFO].keys():
            self.cmd = self.cmds[0].replace(' ','_')
            self.switch[self.cmd] = self.cmd
            self.ui.queryBox.addItem(self.cmd)
            self.subwindowList.append(self.cmd)
            
        for self.cmds in self.commands[consts.CATEGORY_SELECTING_ACTORS].keys():
            self.cmd = self.cmds[0].replace(' ','_')
            self.switch[self.cmd] = self.cmd
            self.ui.queryBox.addItem(self.cmd)
            self.subwindowList.append(self.cmd)
            
        for self.cmds in self.commands[consts.CATEGORY_ACTOR_SPECIFIC].keys():
            self.cmd = self.cmds[0].replace(' ','_')
            self.switch[self.cmd] = self.cmd
            self.ui.queryBox.addItem(self.cmd)
            self.subwindowList.append(self.cmd)

        self.subwindowList.append('graph_days')
        self.ui.queryBox.addItem('graph_days')
        self.subwindowList.append('percent_filtered')
        self.ui.queryBox.addItem('percent_filtered')
        
        
    def on_execute(self):
        print("#######################\n")
        self.parse_execute_query()

    def on_help(self,selected):
        print("#######################\n")
        q_gt.print_help()

    def on_Query(self,selected):
        print(selected)
        print("#############yooooohooo##########\n")
        # if (selected == "apply filter"):
        #     self.filter.show()
        self.method = getattr(self, "show_" + selected, lambda: "No function")
        return self.method()

    def on_reset(self,selected):
        print(selected)
        logparser.reset_selection(None)
        print("#############yooooohooo##########\n")

        
    def __del__(self):
        sys.stdout = sys.__stdout__

    def parse_execute_query(self,buffer=sys.stdout):
        # logparser.init_queryparams()
        logparser.command = str(self.ui.queryBox.currentText())
        self.query = logparser.command
        #self.query = self.query + ' -' + 'agent ' + str(self.ui.comboBox_agent.currentText())
        #self.query = self.query + ' -' + 'round ' + str(self.ui.comboBox_round.currentText())
        #self.query = self.query + ' -' + 'action ' + str(self.ui.comboBox_action.currentText())
        print(">>>>>> Query: " + self.query + "\n")
        logparser.execute_query(self.query,buffer=sys.stdout)
        sys.stdout.flush()



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
    argp.add_argument("--autotest", help="Auto test using demo.json", action="store_true")
    argp.add_argument("--test", help="Test the tool yourself", action="store_true")
    argp.add_argument("--demo", help="Demo of the explore_simulation tool", action="store_true")

    args = argp.parse_args()

    if (args.test):
        # filename = "logs/florian_phd.log"
        logparser = q_gt.LogParser(args.i, args.r)
        app = QApplication(sys.argv)
        uimw = MainWindow()

        #sys.stdout = OutLog(uimw.ui.plainTextEdit, sys.stdout)
        sys.stdout = OutLog(uimw.ui.historyEdit)

        uimw.show()
        uimw.ui.historyEdit.setPlainText("Hi Stacy\n")
        sys.exit(app.exec_())
    elif (args.autotest):
        logparser.demo(autotest=True)
    elif (args.demo):
        logparser.demo(autotest=False)
    else:
        argp.print_help()
        # exit(0)

        

