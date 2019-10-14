# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'DisplayOneSample.ui'
#
# Created by: PyQt5 UI code generator 5.13.0
#
# WARNING! All changes made in this file will be lost!


from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_Display_One_Sample_Dialog(object):
    def setupUi(self, Display_One_Sample_Dialog):
        Display_One_Sample_Dialog.setObjectName("Display_One_Sample_Dialog")
        Display_One_Sample_Dialog.setWindowModality(QtCore.Qt.WindowModal)
        Display_One_Sample_Dialog.setEnabled(True)
        Display_One_Sample_Dialog.resize(220, 189)
        Display_One_Sample_Dialog.setMaximumSize(QtCore.QSize(16777215, 16777215))
        Display_One_Sample_Dialog.setModal(False)
        self.buttonBox = QtWidgets.QDialogButtonBox(Display_One_Sample_Dialog)
        self.buttonBox.setGeometry(QtCore.QRect(30, 120, 161, 51))
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.Cancel|QtWidgets.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName("buttonBox")
        self.groupBox = QtWidgets.QGroupBox(Display_One_Sample_Dialog)
        self.groupBox.setGeometry(QtCore.QRect(10, 20, 201, 101))
        self.groupBox.setObjectName("groupBox")
        self.gridLayoutWidget = QtWidgets.QWidget(self.groupBox)
        self.gridLayoutWidget.setGeometry(QtCore.QRect(10, 20, 181, 71))
        self.gridLayoutWidget.setObjectName("gridLayoutWidget")
        self.gridLayout = QtWidgets.QGridLayout(self.gridLayoutWidget)
        self.gridLayout.setSizeConstraint(QtWidgets.QLayout.SetMinimumSize)
        self.gridLayout.setContentsMargins(0, 0, 0, 0)
        self.gridLayout.setObjectName("gridLayout")
        self.groupBox_4 = QtWidgets.QGroupBox(self.gridLayoutWidget)
        self.groupBox_4.setMaximumSize(QtCore.QSize(16777215, 75))
        self.groupBox_4.setObjectName("groupBox_4")
        self.nameLine = QtWidgets.QLineEdit(self.groupBox_4)
        self.nameLine.setGeometry(QtCore.QRect(10, 30, 161, 21))
        self.nameLine.setAlignment(QtCore.Qt.AlignLeading|QtCore.Qt.AlignLeft|QtCore.Qt.AlignVCenter)
        self.nameLine.setObjectName("nameLine")
        self.gridLayout.addWidget(self.groupBox_4, 1, 0, 1, 1)

        self.retranslateUi(Display_One_Sample_Dialog)
        self.buttonBox.accepted.connect(Display_One_Sample_Dialog.accept)
        self.buttonBox.rejected.connect(Display_One_Sample_Dialog.reject)
        QtCore.QMetaObject.connectSlotsByName(Display_One_Sample_Dialog)

    def retranslateUi(self, Display_One_Sample_Dialog):
        _translate = QtCore.QCoreApplication.translate
        Display_One_Sample_Dialog.setWindowTitle(_translate("Display_One_Sample_Dialog", "Display A Sample"))
        self.groupBox.setTitle(_translate("Display_One_Sample_Dialog", "Display_One_Sample"))
        self.groupBox_4.setTitle(_translate("Display_One_Sample_Dialog", "name"))


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    Display_One_Sample_Dialog = QtWidgets.QDialog()
    ui = Ui_Display_One_Sample_Dialog()
    ui.setupUi(Display_One_Sample_Dialog)
    Display_One_Sample_Dialog.show()
    sys.exit(app.exec_())
