# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'StatsDialog.ui'
#
# Created by: PyQt5 UI code generator 5.13.0
#
# WARNING! All changes made in this file will be lost!


from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_StatsDialog(object):
    def setupUi(self, StatsDialog):
        StatsDialog.setObjectName("StatsDialog")
        StatsDialog.setWindowModality(QtCore.Qt.WindowModal)
        StatsDialog.setEnabled(True)
        StatsDialog.resize(245, 451)
        StatsDialog.setMaximumSize(QtCore.QSize(16777215, 16777215))
        StatsDialog.setInputMethodHints(QtCore.Qt.ImhNone)
        StatsDialog.setModal(False)
        self.buttonBox = QtWidgets.QDialogButtonBox(StatsDialog)
        self.buttonBox.setGeometry(QtCore.QRect(40, 390, 161, 51))
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.Cancel|QtWidgets.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName("buttonBox")
        self.groupBox = QtWidgets.QGroupBox(StatsDialog)
        self.groupBox.setGeometry(QtCore.QRect(30, 10, 191, 371))
        self.groupBox.setObjectName("groupBox")
        self.gridLayoutWidget = QtWidgets.QWidget(self.groupBox)
        self.gridLayoutWidget.setGeometry(QtCore.QRect(10, 30, 174, 331))
        self.gridLayoutWidget.setObjectName("gridLayoutWidget")
        self.gridLayout = QtWidgets.QGridLayout(self.gridLayoutWidget)
        self.gridLayout.setSizeConstraint(QtWidgets.QLayout.SetMinimumSize)
        self.gridLayout.setContentsMargins(0, 0, 0, 0)
        self.gridLayout.setObjectName("gridLayout")
        self.groupBox_5 = QtWidgets.QGroupBox(self.gridLayoutWidget)
        self.groupBox_5.setMaximumSize(QtCore.QSize(16777215, 75))
        self.groupBox_5.setAlignment(QtCore.Qt.AlignJustify|QtCore.Qt.AlignVCenter)
        self.groupBox_5.setObjectName("groupBox_5")
        self.functionBox = QtWidgets.QComboBox(self.groupBox_5)
        self.functionBox.setGeometry(QtCore.QRect(10, 30, 151, 26))
        self.functionBox.setObjectName("functionBox")
        self.gridLayout.addWidget(self.groupBox_5, 2, 0, 1, 1)
        self.groupBox_3 = QtWidgets.QGroupBox(self.gridLayoutWidget)
        self.groupBox_3.setMaximumSize(QtCore.QSize(16777215, 75))
        self.groupBox_3.setAlignment(QtCore.Qt.AlignJustify|QtCore.Qt.AlignVCenter)
        self.groupBox_3.setObjectName("groupBox_3")
        self.attributeBox = QtWidgets.QComboBox(self.groupBox_3)
        self.attributeBox.setGeometry(QtCore.QRect(10, 30, 151, 26))
        self.attributeBox.setObjectName("attributeBox")
        self.gridLayout.addWidget(self.groupBox_3, 1, 0, 1, 1)
        self.groupBox_7 = QtWidgets.QGroupBox(self.gridLayoutWidget)
        self.groupBox_7.setMaximumSize(QtCore.QSize(16777215, 75))
        self.groupBox_7.setAlignment(QtCore.Qt.AlignLeading|QtCore.Qt.AlignLeft|QtCore.Qt.AlignTop)
        self.groupBox_7.setObjectName("groupBox_7")
        self.dayspinBox_1 = QtWidgets.QSpinBox(self.groupBox_7)
        self.dayspinBox_1.setGeometry(QtCore.QRect(10, 30, 53, 24))
        self.dayspinBox_1.setMinimum(1)
        self.dayspinBox_1.setObjectName("dayspinBox_1")
        self.dayspinBox_2 = QtWidgets.QSpinBox(self.groupBox_7)
        self.dayspinBox_2.setGeometry(QtCore.QRect(90, 30, 53, 24))
        self.dayspinBox_2.setMinimum(1)
        self.dayspinBox_2.setObjectName("dayspinBox_2")
        self.gridLayout.addWidget(self.groupBox_7, 3, 0, 1, 1)
        self.groupBox_4 = QtWidgets.QGroupBox(self.gridLayoutWidget)
        self.groupBox_4.setMaximumSize(QtCore.QSize(16777215, 75))
        self.groupBox_4.setObjectName("groupBox_4")
        self.sampleList = QtWidgets.QListWidget(self.groupBox_4)
        self.sampleList.setGeometry(QtCore.QRect(10, 20, 151, 51))
        self.sampleList.setDragEnabled(True)
        self.sampleList.setDragDropMode(QtWidgets.QAbstractItemView.DragDrop)
        self.sampleList.setSelectionMode(QtWidgets.QAbstractItemView.MultiSelection)
        self.sampleList.setObjectName("sampleList")
        self.gridLayout.addWidget(self.groupBox_4, 4, 0, 1, 1)

        self.retranslateUi(StatsDialog)
        self.buttonBox.accepted.connect(StatsDialog.accept)
        self.buttonBox.rejected.connect(StatsDialog.reject)
        QtCore.QMetaObject.connectSlotsByName(StatsDialog)

    def retranslateUi(self, StatsDialog):
        _translate = QtCore.QCoreApplication.translate
        StatsDialog.setWindowTitle(_translate("StatsDialog", "Stats Display"))
        self.groupBox.setTitle(_translate("StatsDialog", "Stats"))
        self.groupBox_5.setTitle(_translate("StatsDialog", "function"))
        self.functionBox.setToolTip(_translate("StatsDialog", "What freatiure of the agent to fileter by"))
        self.groupBox_3.setTitle(_translate("StatsDialog", "attribute"))
        self.attributeBox.setToolTip(_translate("StatsDialog", "What freatiure of the agent to fileter by"))
        self.groupBox_7.setTitle(_translate("StatsDialog", "days"))
        self.groupBox_4.setTitle(_translate("StatsDialog", "Sample Names (optional)"))


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    StatsDialog = QtWidgets.QDialog()
    ui = Ui_StatsDialog()
    ui.setupUi(StatsDialog)
    StatsDialog.show()
    sys.exit(app.exec_())
