# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'SelectDialog.ui'
#
# Created by: PyQt5 UI code generator 5.13.0
#
# WARNING! All changes made in this file will be lost!


from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_SelectDialog(object):
    def setupUi(self, SelectDialog):
        SelectDialog.setObjectName("SelectDialog")
        SelectDialog.resize(366, 190)
        self.buttonBox = QtWidgets.QDialogButtonBox(SelectDialog)
        self.buttonBox.setGeometry(QtCore.QRect(260, 100, 81, 71))
        self.buttonBox.setOrientation(QtCore.Qt.Vertical)
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.Cancel|QtWidgets.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName("buttonBox")
        self.groupBox = QtWidgets.QGroupBox(SelectDialog)
        self.groupBox.setGeometry(QtCore.QRect(20, 30, 211, 151))
        self.groupBox.setObjectName("groupBox")
        self.gridLayoutWidget = QtWidgets.QWidget(self.groupBox)
        self.gridLayoutWidget.setGeometry(QtCore.QRect(10, 30, 191, 111))
        self.gridLayoutWidget.setObjectName("gridLayoutWidget")
        self.gridLayout = QtWidgets.QGridLayout(self.gridLayoutWidget)
        self.gridLayout.setContentsMargins(0, 0, 0, 0)
        self.gridLayout.setObjectName("gridLayout")
        self.selBox = QtWidgets.QComboBox(self.gridLayoutWidget)
        self.selBox.setObjectName("selBox")
        self.gridLayout.addWidget(self.selBox, 1, 1, 1, 1)
        self.numberspinBox = QtWidgets.QSpinBox(self.gridLayoutWidget)
        self.numberspinBox.setMinimum(1)
        self.numberspinBox.setMaximum(10000)
        self.numberspinBox.setObjectName("numberspinBox")
        self.gridLayout.addWidget(self.numberspinBox, 0, 1, 1, 1)
        self.label = QtWidgets.QLabel(self.gridLayoutWidget)
        self.label.setObjectName("label")
        self.gridLayout.addWidget(self.label, 0, 0, 1, 1)
        self.label_2 = QtWidgets.QLabel(self.gridLayoutWidget)
        self.label_2.setObjectName("label_2")
        self.gridLayout.addWidget(self.label_2, 1, 0, 1, 1)

        self.retranslateUi(SelectDialog)
        self.buttonBox.accepted.connect(SelectDialog.accept)
        self.buttonBox.rejected.connect(SelectDialog.reject)
        QtCore.QMetaObject.connectSlotsByName(SelectDialog)

    def retranslateUi(self, SelectDialog):
        _translate = QtCore.QCoreApplication.translate
        SelectDialog.setWindowTitle(_translate("SelectDialog", "Dialog"))
        self.groupBox.setTitle(_translate("SelectDialog", "Select"))
        self.label.setText(_translate("SelectDialog", "Number"))
        self.label_2.setText(_translate("SelectDialog", "Select by"))


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    SelectDialog = QtWidgets.QDialog()
    ui = Ui_SelectDialog()
    ui.setupUi(SelectDialog)
    SelectDialog.show()
    sys.exit(app.exec_())
