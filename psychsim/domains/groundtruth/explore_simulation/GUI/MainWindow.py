# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'psychsim/domains/groundtruth/explore_simulation/GUI/MainWindow.ui'
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
        self.groupBox.setGeometry(QtCore.QRect(30, 20, 451, 80))
        self.groupBox.setObjectName("groupBox")
        self.queryBox = QtWidgets.QComboBox(self.groupBox)
        self.queryBox.setGeometry(QtCore.QRect(20, 30, 181, 26))
        self.queryBox.setObjectName("queryBox")
        self.queryBox.addItem("")
        self.queryBox.addItem("")
        self.queryBox.addItem("")
        self.queryBox.addItem("")
        self.queryBox.addItem("")
        self.queryBox.addItem("")
        self.queryBox.addItem("")
        self.executeButton = QtWidgets.QCommandLinkButton(self.groupBox)
        self.executeButton.setGeometry(QtCore.QRect(220, 30, 101, 31))
        self.executeButton.setObjectName("executeButton")
        self.resetButton = QtWidgets.QCommandLinkButton(self.groupBox)
        self.resetButton.setGeometry(QtCore.QRect(330, 20, 91, 31))
        self.resetButton.setObjectName("resetButton")
        self.helpButton = QtWidgets.QCommandLinkButton(self.groupBox)
        self.helpButton.setGeometry(QtCore.QRect(330, 50, 51, 41))
        self.helpButton.setObjectName("helpButton")
        self.groupBox_2 = QtWidgets.QGroupBox(self.centralwidget)
        self.groupBox_2.setGeometry(QtCore.QRect(30, 100, 321, 51))
        self.groupBox_2.setObjectName("groupBox_2")
        self.numAgents = QtWidgets.QLabel(self.groupBox_2)
        self.numAgents.setGeometry(QtCore.QRect(100, 30, 56, 13))
        self.numAgents.setObjectName("numAgents")
        self.scrollArea = QtWidgets.QScrollArea(self.centralwidget)
        self.scrollArea.setGeometry(QtCore.QRect(30, 170, 741, 431))
        self.scrollArea.setWidgetResizable(True)
        self.scrollArea.setObjectName("scrollArea")
        self.scrollAreaWidgetContents = QtWidgets.QWidget()
        self.scrollAreaWidgetContents.setGeometry(QtCore.QRect(0, 0, 739, 429))
        self.scrollAreaWidgetContents.setObjectName("scrollAreaWidgetContents")
        self.label = QtWidgets.QLabel(self.scrollAreaWidgetContents)
        self.label.setGeometry(QtCore.QRect(20, 0, 91, 16))
        self.label.setObjectName("label")
        self.historyEdit = QtWidgets.QTextEdit(self.scrollAreaWidgetContents)
        self.historyEdit.setGeometry(QtCore.QRect(20, 20, 701, 391))
        self.historyEdit.setObjectName("historyEdit")
        self.scrollArea.setWidget(self.scrollAreaWidgetContents)
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
        self.queryBox.setItemText(0, _translate("MainWindow", "Select Query"))
        self.queryBox.setItemText(1, _translate("MainWindow", "select actors"))
        self.queryBox.setItemText(2, _translate("MainWindow", "get entities"))
        self.queryBox.setItemText(3, _translate("MainWindow", "get attribute_names"))
        self.queryBox.setItemText(4, _translate("MainWindow", "get nactors"))
        self.queryBox.setItemText(5, _translate("MainWindow", "apply filter"))
        self.queryBox.setItemText(6, _translate("MainWindow", "show filters"))
        self.executeButton.setText(_translate("MainWindow", "Execute"))
        self.resetButton.setText(_translate("MainWindow", "Reset"))
        self.helpButton.setText(_translate("MainWindow", "Help"))
        self.groupBox_2.setTitle(_translate("MainWindow", "Number of Agents Selected"))
        self.numAgents.setToolTip(_translate("MainWindow", "Number of agents currently selected"))
        self.numAgents.setText(_translate("MainWindow", "TextLabel"))
        self.label.setText(_translate("MainWindow", "Query History"))
