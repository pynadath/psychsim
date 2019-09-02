# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'MainWindow.ui'
#
# Created by: PyQt5 UI code generator 5.13.0
#
# WARNING! All changes made in this file will be lost!


from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(800, 646)
        self.centralwidget = QtWidgets.QWidget(MainWindow)
        self.centralwidget.setObjectName("centralwidget")
        self.groupBox = QtWidgets.QGroupBox(self.centralwidget)
        self.groupBox.setGeometry(QtCore.QRect(30, 10, 421, 80))
        self.groupBox.setObjectName("groupBox")
        self.queryBox = QtWidgets.QComboBox(self.groupBox)
        self.queryBox.setGeometry(QtCore.QRect(20, 30, 181, 26))
        self.queryBox.setObjectName("queryBox")
        self.queryBox.addItem("")
        self.queryBox.setItemText(0, "")
        self.helpButton = QtWidgets.QCommandLinkButton(self.groupBox)
        self.helpButton.setGeometry(QtCore.QRect(210, 30, 101, 41))
        self.helpButton.setObjectName("helpButton")
        self.resetButton = QtWidgets.QCommandLinkButton(self.groupBox)
        self.resetButton.setGeometry(QtCore.QRect(310, 30, 91, 41))
        self.resetButton.setObjectName("resetButton")
        self.groupBox_2 = QtWidgets.QGroupBox(self.centralwidget)
        self.groupBox_2.setGeometry(QtCore.QRect(30, 100, 321, 51))
        self.groupBox_2.setObjectName("groupBox_2")
        self.numAgents = QtWidgets.QLabel(self.groupBox_2)
        self.numAgents.setGeometry(QtCore.QRect(100, 30, 56, 13))
        self.numAgents.setObjectName("numAgents")
        self.scrollArea = QtWidgets.QScrollArea(self.centralwidget)
        self.scrollArea.setGeometry(QtCore.QRect(30, 160, 741, 431))
        self.scrollArea.setWidgetResizable(True)
        self.scrollArea.setObjectName("scrollArea")
        self.scrollAreaWidgetContents = QtWidgets.QWidget()
        self.scrollAreaWidgetContents.setGeometry(QtCore.QRect(0, 0, 739, 429))
        self.scrollAreaWidgetContents.setObjectName("scrollAreaWidgetContents")
        self.historyEdit = QtWidgets.QPlainTextEdit(self.scrollAreaWidgetContents)
        self.historyEdit.setGeometry(QtCore.QRect(20, 250, 701, 171))
        self.historyEdit.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOn)
        self.historyEdit.setObjectName("historyEdit")
        self.label = QtWidgets.QLabel(self.scrollAreaWidgetContents)
        self.label.setGeometry(QtCore.QRect(20, 0, 91, 16))
        self.label.setObjectName("label")
        self.plotView = PlotWidget(self.scrollAreaWidgetContents)
        self.plotView.setGeometry(QtCore.QRect(120, 40, 256, 192))
        self.plotView.setObjectName("plotView")
        self.scrollArea.setWidget(self.scrollAreaWidgetContents)
        self.groupBox_3 = QtWidgets.QGroupBox(self.centralwidget)
        self.groupBox_3.setGeometry(QtCore.QRect(490, 0, 281, 151))
        self.groupBox_3.setObjectName("groupBox_3")
        self.scrollArea_2 = QtWidgets.QScrollArea(self.groupBox_3)
        self.scrollArea_2.setGeometry(QtCore.QRect(0, 20, 281, 131))
        self.scrollArea_2.setWidgetResizable(True)
        self.scrollArea_2.setObjectName("scrollArea_2")
        self.scrollAreaWidgetContents_2 = QtWidgets.QWidget()
        self.scrollAreaWidgetContents_2.setGeometry(QtCore.QRect(0, 0, 279, 129))
        self.scrollAreaWidgetContents_2.setObjectName("scrollAreaWidgetContents_2")
        self.filterText = QtWidgets.QPlainTextEdit(self.scrollAreaWidgetContents_2)
        self.filterText.setGeometry(QtCore.QRect(0, 0, 271, 131))
        self.filterText.setUndoRedoEnabled(False)
        self.filterText.setReadOnly(True)
        self.filterText.setObjectName("filterText")
        self.scrollArea_2.setWidget(self.scrollAreaWidgetContents_2)
        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QtWidgets.QMenuBar(MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 800, 22))
        self.menubar.setObjectName("menubar")
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QtWidgets.QStatusBar(MainWindow)
        self.statusbar.setObjectName("statusbar")
        MainWindow.setStatusBar(self.statusbar)

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "MainWindow"))
        self.groupBox.setTitle(_translate("MainWindow", "Query"))
        self.helpButton.setText(_translate("MainWindow", "Help"))
        self.resetButton.setText(_translate("MainWindow", "Reset State"))
        self.groupBox_2.setTitle(_translate("MainWindow", "Number of Agents Selected"))
        self.numAgents.setToolTip(_translate("MainWindow", "Number of agents currently selected"))
        self.numAgents.setText(_translate("MainWindow", "TextLabel"))
        self.label.setText(_translate("MainWindow", "Query History"))
        self.groupBox_3.setTitle(_translate("MainWindow", "Filters"))
from pyqtgraph import PlotWidget


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    MainWindow = QtWidgets.QMainWindow()
    ui = Ui_MainWindow()
    ui.setupUi(MainWindow)
    MainWindow.show()
    sys.exit(app.exec_())
