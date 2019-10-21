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
        GetStats.resize(278, 463)
        self.verticalLayoutWidget = QtWidgets.QWidget(GetStats)
        self.verticalLayoutWidget.setGeometry(QtCore.QRect(10, 20, 241, 421))
        self.verticalLayoutWidget.setObjectName("verticalLayoutWidget")
        self.Vertical = QtWidgets.QVBoxLayout(self.verticalLayoutWidget)
        self.Vertical.setContentsMargins(0, 0, 0, 0)
        self.Vertical.setObjectName("Vertical")
        self.groupBox = QtWidgets.QGroupBox(self.verticalLayoutWidget)
        self.groupBox.setMaximumSize(QtCore.QSize(150, 50))
        self.groupBox.setObjectName("groupBox")
        self.attribute = QtWidgets.QComboBox(self.groupBox)
        self.attribute.setGeometry(QtCore.QRect(10, 20, 131, 26))
        self.attribute.setObjectName("attribute")
        self.Vertical.addWidget(self.groupBox)
        self.groupBox_2 = QtWidgets.QGroupBox(self.verticalLayoutWidget)
        self.groupBox_2.setMaximumSize(QtCore.QSize(150, 50))
        self.groupBox_2.setObjectName("groupBox_2")
        self.function = QtWidgets.QComboBox(self.groupBox_2)
        self.function.setGeometry(QtCore.QRect(10, 20, 131, 26))
        self.function.setObjectName("function")
        self.Vertical.addWidget(self.groupBox_2)
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
        self.groupBox_6 = QtWidgets.QGroupBox(self.verticalLayoutWidget)
        self.groupBox_6.setMaximumSize(QtCore.QSize(150, 50))
        self.groupBox_6.setObjectName("groupBox_6")
        self.name = QtWidgets.QLineEdit(self.groupBox_6)
        self.name.setGeometry(QtCore.QRect(10, 20, 113, 21))
        self.name.setObjectName("name")
        self.Vertical.addWidget(self.groupBox_6)
        self.groupBox_4 = QtWidgets.QGroupBox(self.verticalLayoutWidget)
        self.groupBox_4.setMaximumSize(QtCore.QSize(16777214, 200))
        self.groupBox_4.setObjectName("groupBox_4")
        self.sampleList = QtWidgets.QListWidget(self.groupBox_4)
        self.sampleList.setGeometry(QtCore.QRect(10, 30, 201, 71))
        self.sampleList.setEditTriggers(QtWidgets.QAbstractItemView.AnyKeyPressed|QtWidgets.QAbstractItemView.DoubleClicked|QtWidgets.QAbstractItemView.EditKeyPressed)
        self.sampleList.setObjectName("sampleList")
        self.toolButton = QtWidgets.QToolButton(self.groupBox_4)
        self.toolButton.setGeometry(QtCore.QRect(10, 110, 201, 22))
        self.toolButton.setPopupMode(QtWidgets.QToolButton.InstantPopup)
        self.toolButton.setObjectName("toolButton")
        self.Vertical.addWidget(self.groupBox_4)
        self.buttonBox = QtWidgets.QDialogButtonBox(self.verticalLayoutWidget)
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.Cancel|QtWidgets.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName("buttonBox")
        self.Vertical.addWidget(self.buttonBox)

        self.retranslateUi(GetStats)
        QtCore.QMetaObject.connectSlotsByName(GetStats)

    def retranslateUi(self, GetStats):
        _translate = QtCore.QCoreApplication.translate
        GetStats.setWindowTitle(_translate("GetStats", "GetStats"))
        self.groupBox.setTitle(_translate("GetStats", "Attribute"))
        self.groupBox_2.setTitle(_translate("GetStats", "Function"))
        self.groupBox_3.setTitle(_translate("GetStats", "Days"))
        self.groupBox_6.setTitle(_translate("GetStats", "Plot Name"))
        self.groupBox_4.setTitle(_translate("GetStats", "Samples"))
        self.toolButton.setText(_translate("GetStats", "\'Select Samples \'"))


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    GetStats = QtWidgets.QDialog()
    ui = Ui_GetStats()
    ui.setupUi(GetStats)
    GetStats.show()
    sys.exit(app.exec_())
