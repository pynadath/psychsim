# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'FilterDialog.ui'
#
# Created by: PyQt5 UI code generator 5.13.0
#
# WARNING! All changes made in this file will be lost!


from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_FilterDialog(object):
    def setupUi(self, FilterDialog):
        FilterDialog.setObjectName("FilterDialog")
        FilterDialog.setWindowModality(QtCore.Qt.WindowModal)
        FilterDialog.setEnabled(True)
        FilterDialog.resize(497, 286)
        FilterDialog.setMaximumSize(QtCore.QSize(16777215, 16777215))
        FilterDialog.setModal(False)
        self.buttonBox = QtWidgets.QDialogButtonBox(FilterDialog)
        self.buttonBox.setGeometry(QtCore.QRect(170, 240, 161, 51))
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.Cancel|QtWidgets.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName("buttonBox")
        self.groupBox = QtWidgets.QGroupBox(FilterDialog)
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

        self.retranslateUi(FilterDialog)
        self.buttonBox.accepted.connect(FilterDialog.accept)
        self.buttonBox.rejected.connect(FilterDialog.reject)
        QtCore.QMetaObject.connectSlotsByName(FilterDialog)

    def retranslateUi(self, FilterDialog):
        _translate = QtCore.QCoreApplication.translate
        FilterDialog.setWindowTitle(_translate("FilterDialog", "Apply Filter"))
        self.groupBox.setTitle(_translate("FilterDialog", "Apply Filter"))
        self.groupBox_3.setTitle(_translate("FilterDialog", "attribute"))
        self.attributeBox.setToolTip(_translate("FilterDialog", "What freatiure of the agent to fileter by"))
        self.groupBox_6.setTitle(_translate("FilterDialog", "value"))
        self.groupBox_2.setTitle(_translate("FilterDialog", "operator"))
        self.groupBox_7.setTitle(_translate("FilterDialog", "day"))
        self.groupBox_4.setTitle(_translate("FilterDialog", "name (optional)"))


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    FilterDialog = QtWidgets.QDialog()
    ui = Ui_FilterDialog()
    ui.setupUi(FilterDialog)
    FilterDialog.show()
    sys.exit(app.exec_())
