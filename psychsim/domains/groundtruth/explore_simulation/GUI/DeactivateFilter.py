# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'DeactivateFilter.ui'
#
# Created by: PyQt5 UI code generator 5.13.0
#
# WARNING! All changes made in this file will be lost!


from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_DeactivateFilter(object):
    def setupUi(self, DeactivateFilter):
        DeactivateFilter.setObjectName("DeactivateFilter")
        DeactivateFilter.setWindowModality(QtCore.Qt.WindowModal)
        DeactivateFilter.setEnabled(True)
        DeactivateFilter.resize(223, 160)
        DeactivateFilter.setMaximumSize(QtCore.QSize(16777215, 16777215))
        DeactivateFilter.setToolTip("")
        DeactivateFilter.setModal(False)
        self.buttonBox = QtWidgets.QDialogButtonBox(DeactivateFilter)
        self.buttonBox.setGeometry(QtCore.QRect(30, 100, 161, 51))
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.Cancel|QtWidgets.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName("buttonBox")
        self.groupBox = QtWidgets.QGroupBox(DeactivateFilter)
        self.groupBox.setGeometry(QtCore.QRect(10, 20, 201, 71))
        self.groupBox.setObjectName("groupBox")
        self.comboBox = QtWidgets.QComboBox(self.groupBox)
        self.comboBox.setGeometry(QtCore.QRect(10, 30, 181, 26))
        self.comboBox.setObjectName("comboBox")

        self.retranslateUi(DeactivateFilter)
        self.buttonBox.accepted.connect(DeactivateFilter.accept)
        self.buttonBox.rejected.connect(DeactivateFilter.reject)
        QtCore.QMetaObject.connectSlotsByName(DeactivateFilter)

    def retranslateUi(self, DeactivateFilter):
        _translate = QtCore.QCoreApplication.translate
        DeactivateFilter.setWindowTitle(_translate("DeactivateFilter", "Deactivate Filter"))
        self.groupBox.setTitle(_translate("DeactivateFilter", "De-Activate Filter"))
