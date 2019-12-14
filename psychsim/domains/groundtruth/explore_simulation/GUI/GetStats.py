# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'GetStats.ui'
#
# Created by: PyQt5 UI code generator 5.13.0
#
# WARNING! All changes made in this file will be lost!


from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_GetStats(object):
    def setupUi(self, GetStats):
        GetStats.setObjectName("GetStats")
        GetStats.resize(222, 463)
        self.verticalLayoutWidget = QtWidgets.QWidget(GetStats)
        self.verticalLayoutWidget.setGeometry(QtCore.QRect(20, 20, 181, 421))
        self.verticalLayoutWidget.setObjectName("verticalLayoutWidget")
        self.Vertical = QtWidgets.QVBoxLayout(self.verticalLayoutWidget)
        self.Vertical.setContentsMargins(0, 0, 0, 0)
        self.Vertical.setObjectName("Vertical")
        self.groupBox = QtWidgets.QGroupBox(self.verticalLayoutWidget)
        self.groupBox.setMaximumSize(QtCore.QSize(150, 50))
        self.groupBox.setObjectName("groupBox")
        self.Attributes = QtWidgets.QToolButton(self.groupBox)
        self.Attributes.setGeometry(QtCore.QRect(0, 20, 141, 22))
        self.Attributes.setCheckable(True)
        self.Attributes.setPopupMode(QtWidgets.QToolButton.InstantPopup)
        self.Attributes.setObjectName("Attributes")
        self.Vertical.addWidget(self.groupBox)
        self.groupBox_2 = QtWidgets.QGroupBox(self.verticalLayoutWidget)
        self.groupBox_2.setMaximumSize(QtCore.QSize(150, 50))
        self.groupBox_2.setObjectName("groupBox_2")
        self.Functions = QtWidgets.QToolButton(self.groupBox_2)
        self.Functions.setGeometry(QtCore.QRect(0, 20, 141, 22))
        self.Functions.setCheckable(True)
        self.Functions.setPopupMode(QtWidgets.QToolButton.InstantPopup)
        self.Functions.setObjectName("Functions")
        self.Vertical.addWidget(self.groupBox_2)
        self.groupBox_7 = QtWidgets.QGroupBox(self.verticalLayoutWidget)
        self.groupBox_7.setMaximumSize(QtCore.QSize(150, 50))
        self.groupBox_7.setObjectName("groupBox_7")
        self.Samples = QtWidgets.QToolButton(self.groupBox_7)
        self.Samples.setGeometry(QtCore.QRect(10, 20, 131, 22))
        self.Samples.setCheckable(True)
        self.Samples.setPopupMode(QtWidgets.QToolButton.InstantPopup)
        self.Samples.setArrowType(QtCore.Qt.NoArrow)
        self.Samples.setObjectName("Samples")
        self.Vertical.addWidget(self.groupBox_7)
        self.PlotName = QtWidgets.QGroupBox(self.verticalLayoutWidget)
        self.PlotName.setMaximumSize(QtCore.QSize(150, 50))
        self.PlotName.setObjectName("PlotName")
        self.name = QtWidgets.QLineEdit(self.PlotName)
        self.name.setGeometry(QtCore.QRect(10, 30, 131, 21))
        self.name.setObjectName("name")
        self.Vertical.addWidget(self.PlotName)
        self.groupBox_3 = QtWidgets.QGroupBox(self.verticalLayoutWidget)
        self.groupBox_3.setMaximumSize(QtCore.QSize(150, 50))
        self.groupBox_3.setObjectName("groupBox_3")
        self.dayspinBox_1 = QtWidgets.QSpinBox(self.groupBox_3)
        self.dayspinBox_1.setGeometry(QtCore.QRect(10, 20, 48, 24))
        self.dayspinBox_1.setObjectName("dayspinBox_1")
        self.dayspinBox_2 = QtWidgets.QSpinBox(self.groupBox_3)
        self.dayspinBox_2.setGeometry(QtCore.QRect(60, 20, 48, 24))
        self.dayspinBox_2.setObjectName("dayspinBox_2")
        self.Vertical.addWidget(self.groupBox_3)
        self.buttonBox = QtWidgets.QDialogButtonBox(self.verticalLayoutWidget)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.buttonBox.sizePolicy().hasHeightForWidth())
        self.buttonBox.setSizePolicy(sizePolicy)
        self.buttonBox.setBaseSize(QtCore.QSize(100, 100))
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.Cancel|QtWidgets.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName("buttonBox")
        self.Vertical.addWidget(self.buttonBox)

        self.retranslateUi(GetStats)
        QtCore.QMetaObject.connectSlotsByName(GetStats)

    def retranslateUi(self, GetStats):
        _translate = QtCore.QCoreApplication.translate
        GetStats.setWindowTitle(_translate("GetStats", "GetStats"))
        self.groupBox.setTitle(_translate("GetStats", "Attribute"))
        self.Attributes.setText(_translate("GetStats", "Select Attrbutes"))
        self.groupBox_2.setTitle(_translate("GetStats", "Function"))
        self.Functions.setText(_translate("GetStats", "Select Functions"))
        self.groupBox_7.setTitle(_translate("GetStats", "Samples"))
        self.Samples.setText(_translate("GetStats", "\'Select Samples \'"))
        self.PlotName.setTitle(_translate("GetStats", "Plot Name"))
        self.groupBox_3.setTitle(_translate("GetStats", "Days"))
