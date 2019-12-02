# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'GetEntityAttributes.ui'
#
# Created by: PyQt5 UI code generator 5.13.0
#
# WARNING! All changes made in this file will be lost!


from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_EntityName(object):
    def setupUi(self, EntityName):
        EntityName.setObjectName("EntityName")
        EntityName.setWindowModality(QtCore.Qt.WindowModal)
        EntityName.setEnabled(True)
        EntityName.resize(224, 151)
        EntityName.setMaximumSize(QtCore.QSize(16777215, 16777215))
        EntityName.setModal(False)
        self.buttonBox = QtWidgets.QDialogButtonBox(EntityName)
        self.buttonBox.setGeometry(QtCore.QRect(30, 100, 161, 51))
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.Cancel|QtWidgets.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName("buttonBox")
        self.groupBox = QtWidgets.QGroupBox(EntityName)
        self.groupBox.setGeometry(QtCore.QRect(10, 20, 201, 71))
        self.groupBox.setObjectName("groupBox")
        self.entityTypes = QtWidgets.QComboBox(self.groupBox)
        self.entityTypes.setGeometry(QtCore.QRect(20, 30, 161, 26))
        self.entityTypes.setObjectName("entityTypes")

        self.retranslateUi(EntityName)
        self.buttonBox.accepted.connect(EntityName.accept)
        self.buttonBox.rejected.connect(EntityName.reject)
        QtCore.QMetaObject.connectSlotsByName(EntityName)

    def retranslateUi(self, EntityName):
        _translate = QtCore.QCoreApplication.translate
        EntityName.setWindowTitle(_translate("EntityName", "Get Entity Attributes"))
        self.groupBox.setTitle(_translate("EntityName", "Entity Type"))
