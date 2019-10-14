# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'CountDialog.ui'
#
# Created by: PyQt5 UI code generator 5.13.0
#
# WARNING! All changes made in this file will be lost!


from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_CountDialog(object):
    def setupUi(self, CountDialog):
        CountDialog.setObjectName("CountDialog")
        CountDialog.setWindowModality(QtCore.Qt.WindowModal)
        CountDialog.setEnabled(True)
        CountDialog.resize(1366, 723)
        CountDialog.setMaximumSize(QtCore.QSize(16777215, 16777215))
        CountDialog.setModal(False)
        self.buttonBox = QtWidgets.QDialogButtonBox(CountDialog)
        self.buttonBox.setGeometry(QtCore.QRect(170, 240, 161, 51))
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.Cancel|QtWidgets.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName("buttonBox")
        self.groupBox = QtWidgets.QGroupBox(CountDialog)
        self.groupBox.setGeometry(QtCore.QRect(30, 20, 441, 221))
        self.groupBox.setObjectName("groupBox")
        self.gridLayoutWidget = QtWidgets.QWidget(self.groupBox)
        self.gridLayoutWidget.setGeometry(QtCore.QRect(10, 30, 421, 181))
        self.gridLayoutWidget.setObjectName("gridLayoutWidget")
        self.gridLayout = QtWidgets.QGridLayout(self.gridLayoutWidget)
        self.gridLayout.setSizeConstraint(QtWidgets.QLayout.SetMinimumSize)
        self.gridLayout.setContentsMargins(0, 0, 0, 0)
        self.gridLayout.setObjectName("gridLayout")
        self.groupBox_3 = QtWidgets.QGroupBox(self.gridLayoutWidget)
        self.groupBox_3.setMaximumSize(QtCore.QSize(16777215, 75))
        self.groupBox_3.setAlignment(QtCore.Qt.AlignJustify|QtCore.Qt.AlignVCenter)
        self.groupBox_3.setObjectName("groupBox_3")
        self.attributeBox = QtWidgets.QComboBox(self.groupBox_3)
        self.attributeBox.setGeometry(QtCore.QRect(10, 30, 104, 26))
        self.attributeBox.setObjectName("attributeBox")
        self.gridLayout.addWidget(self.groupBox_3, 1, 0, 1, 1)
        self.groupBox_6 = QtWidgets.QGroupBox(self.gridLayoutWidget)
        self.groupBox_6.setMaximumSize(QtCore.QSize(16777215, 75))
        self.groupBox_6.setObjectName("groupBox_6")
        self.valueSpinBox = QtWidgets.QDoubleSpinBox(self.groupBox_6)
        self.valueSpinBox.setGeometry(QtCore.QRect(30, 30, 62, 24))
        self.valueSpinBox.setDecimals(1)
        self.valueSpinBox.setMinimum(-1.0)
        self.valueSpinBox.setMaximum(1.0)
        self.valueSpinBox.setSingleStep(0.1)
        self.valueSpinBox.setObjectName("valueSpinBox")
        self.gridLayout.addWidget(self.groupBox_6, 1, 2, 1, 1)
        self.groupBox_2 = QtWidgets.QGroupBox(self.gridLayoutWidget)
        self.groupBox_2.setMaximumSize(QtCore.QSize(16777215, 75))
        self.groupBox_2.setAlignment(QtCore.Qt.AlignLeading|QtCore.Qt.AlignLeft|QtCore.Qt.AlignTop)
        self.groupBox_2.setObjectName("groupBox_2")
        self.operatorBox = QtWidgets.QComboBox(self.groupBox_2)
        self.operatorBox.setGeometry(QtCore.QRect(10, 30, 104, 26))
        self.operatorBox.setObjectName("operatorBox")
        self.gridLayout.addWidget(self.groupBox_2, 1, 1, 1, 1)
        self.groupBox_7 = QtWidgets.QGroupBox(self.gridLayoutWidget)
        self.groupBox_7.setMaximumSize(QtCore.QSize(16777215, 75))
        self.groupBox_7.setAlignment(QtCore.Qt.AlignLeading|QtCore.Qt.AlignLeft|QtCore.Qt.AlignTop)
        self.groupBox_7.setObjectName("groupBox_7")
        self.dayspinBox = QtWidgets.QSpinBox(self.groupBox_7)
        self.dayspinBox.setGeometry(QtCore.QRect(20, 30, 53, 24))
        self.dayspinBox.setMinimum(1)
        self.dayspinBox.setObjectName("dayspinBox")
        self.gridLayout.addWidget(self.groupBox_7, 2, 0, 1, 1)
        self.groupBox_4 = QtWidgets.QGroupBox(self.gridLayoutWidget)
        self.groupBox_4.setMaximumSize(QtCore.QSize(16777215, 75))
        self.groupBox_4.setObjectName("groupBox_4")
        self.nameLine = QtWidgets.QLineEdit(self.groupBox_4)
        self.nameLine.setGeometry(QtCore.QRect(10, 30, 113, 21))
        self.nameLine.setAlignment(QtCore.Qt.AlignLeading|QtCore.Qt.AlignLeft|QtCore.Qt.AlignVCenter)
        self.nameLine.setObjectName("nameLine")
        self.gridLayout.addWidget(self.groupBox_4, 3, 0, 1, 1)

        self.retranslateUi(CountDialog)
        self.buttonBox.accepted.connect(CountDialog.accept)
        self.buttonBox.rejected.connect(CountDialog.reject)
        QtCore.QMetaObject.connectSlotsByName(CountDialog)

    def retranslateUi(self, CountDialog):
        _translate = QtCore.QCoreApplication.translate
        CountDialog.setWindowTitle(_translate("CountDialog", "Apply Filter"))
        self.groupBox.setTitle(_translate("CountDialog", "Count"))
        self.groupBox_3.setTitle(_translate("CountDialog", "attribute"))
        self.attributeBox.setToolTip(_translate("CountDialog", "What freatiure of the agent to fileter by"))
        self.groupBox_6.setTitle(_translate("CountDialog", "value"))
        self.groupBox_2.setTitle(_translate("CountDialog", "operator"))
        self.groupBox_7.setTitle(_translate("CountDialog", "day"))
        self.groupBox_4.setTitle(_translate("CountDialog", "name (optional)"))


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    CountDialog = QtWidgets.QDialog()
    ui = Ui_CountDialog()
    ui.setupUi(CountDialog)
    CountDialog.show()
    sys.exit(app.exec_())
