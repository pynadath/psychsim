# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ReactivateFilter.ui'
#
# Created by: PyQt5 UI code generator 5.13.0
#
# WARNING! All changes made in this file will be lost!


from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_ReactivateFilter(object):
    def setupUi(self, ReactivateFilter):
        ReactivateFilter.setObjectName("ReactivateFilter")
        ReactivateFilter.setWindowModality(QtCore.Qt.WindowModal)
        ReactivateFilter.setEnabled(True)
        ReactivateFilter.resize(223, 160)
        ReactivateFilter.setMaximumSize(QtCore.QSize(16777215, 16777215))
        ReactivateFilter.setToolTip("")
        ReactivateFilter.setModal(False)
        self.buttonBox = QtWidgets.QDialogButtonBox(ReactivateFilter)
        self.buttonBox.setGeometry(QtCore.QRect(30, 100, 161, 51))
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.Cancel|QtWidgets.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName("buttonBox")
        self.groupBox = QtWidgets.QGroupBox(ReactivateFilter)
        self.groupBox.setGeometry(QtCore.QRect(10, 20, 201, 71))
        self.groupBox.setObjectName("groupBox")
        self.comboBox = QtWidgets.QComboBox(self.groupBox)
        self.comboBox.setGeometry(QtCore.QRect(10, 30, 181, 26))
        self.comboBox.setObjectName("comboBox")

        self.retranslateUi(ReactivateFilter)
        self.buttonBox.accepted.connect(ReactivateFilter.accept)
        self.buttonBox.rejected.connect(ReactivateFilter.reject)
        QtCore.QMetaObject.connectSlotsByName(ReactivateFilter)

    def retranslateUi(self, ReactivateFilter):
        _translate = QtCore.QCoreApplication.translate
        ReactivateFilter.setWindowTitle(_translate("ReactivateFilter", "Reactivate Filter"))
        self.groupBox.setTitle(_translate("ReactivateFilter", "Re-Activate Filter"))
