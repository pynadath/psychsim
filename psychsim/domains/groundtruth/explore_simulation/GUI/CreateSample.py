# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'CreateSample.ui'
#
# Created by: PyQt5 UI code generator 5.13.0
#
# WARNING! All changes made in this file will be lost!


from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_CreateSample(object):
    def setupUi(self, CreateSample):
        CreateSample.setObjectName("CreateSample")
        CreateSample.setWindowModality(QtCore.Qt.WindowModal)
        CreateSample.setEnabled(True)
        CreateSample.resize(224, 180)
        CreateSample.setMaximumSize(QtCore.QSize(16777215, 16777215))
        CreateSample.setModal(False)
        self.buttonBox = QtWidgets.QDialogButtonBox(CreateSample)
        self.buttonBox.setGeometry(QtCore.QRect(30, 140, 161, 51))
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.Cancel|QtWidgets.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName("buttonBox")
        self.groupBox = QtWidgets.QGroupBox(CreateSample)
        self.groupBox.setGeometry(QtCore.QRect(10, 20, 201, 111))
        self.groupBox.setObjectName("groupBox")
        self.gridLayoutWidget = QtWidgets.QWidget(self.groupBox)
        self.gridLayoutWidget.setGeometry(QtCore.QRect(0, 20, 201, 91))
        self.gridLayoutWidget.setObjectName("gridLayoutWidget")
        self.gridLayout = QtWidgets.QGridLayout(self.gridLayoutWidget)
        self.gridLayout.setSizeConstraint(QtWidgets.QLayout.SetMinimumSize)
        self.gridLayout.setContentsMargins(0, 0, 0, 0)
        self.gridLayout.setObjectName("gridLayout")
        self.groupBox_4 = QtWidgets.QGroupBox(self.gridLayoutWidget)
        self.groupBox_4.setMaximumSize(QtCore.QSize(16777215, 75))
        self.groupBox_4.setObjectName("groupBox_4")
        self.nameLine = QtWidgets.QLineEdit(self.groupBox_4)
        self.nameLine.setGeometry(QtCore.QRect(10, 30, 151, 21))
        self.nameLine.setAlignment(QtCore.Qt.AlignLeading|QtCore.Qt.AlignLeft|QtCore.Qt.AlignVCenter)
        self.nameLine.setObjectName("nameLine")
        self.gridLayout.addWidget(self.groupBox_4, 1, 0, 1, 1)

        self.retranslateUi(CreateSample)
        self.buttonBox.accepted.connect(CreateSample.accept)
        self.buttonBox.rejected.connect(CreateSample.reject)
        QtCore.QMetaObject.connectSlotsByName(CreateSample)

    def retranslateUi(self, CreateSample):
        _translate = QtCore.QCoreApplication.translate
        CreateSample.setWindowTitle(_translate("CreateSample", "Create Sample"))
        self.groupBox.setTitle(_translate("CreateSample", "Create Sample"))
        self.groupBox_4.setTitle(_translate("CreateSample", "name (optional)"))


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    CreateSample = QtWidgets.QDialog()
    ui = Ui_CreateSample()
    ui.setupUi(CreateSample)
    CreateSample.show()
    sys.exit(app.exec_())
