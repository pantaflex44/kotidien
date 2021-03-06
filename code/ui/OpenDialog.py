#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
@package Kotidien.ui
"""
"""
Kotidien - Finances personnelles assistées par ordinateur
Copyright (C) 2020-2021 Christophe LEMOINE

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""
import sys
import os
import json

from PyQt5 import QtCore, QtWidgets, QtGui, uic
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *

import libs.completer
import resources
import appinfos
import funcs
import icons

from datamodels import *

from ui.EditDialog import EditDialog


class OpenDialog(QDialog):

    _settings = None
    _locale = None

    def __init__(self, settings, locale, parent=None, default='', *args, **kwargs):
        self._settings = settings
        self._locale = locale
        super(OpenDialog, self).__init__(parent, Qt.Window
                                         | Qt.WindowTitleHint | Qt.CustomizeWindowHint, *args, **kwargs)
        self._init_ui(default)

    def _init_ui(self, default=''):
        # self
        self.ui = funcs.loadUiResource(funcs.rc('/ui/' + self.__class__.__name__ + '.ui'), self)
        self.setLocale(QLocale(self._locale))
        self.ui.setLocale(QLocale(self._locale))
        self.setModal(True)
        qtRectangle = self.frameGeometry()
        centerPoint = QDesktopWidget().availableGeometry().center()
        qtRectangle.moveCenter(centerPoint)
        self.move(qtRectangle.topLeft())
        self.setFixedSize(self.size())
        self.setWindowIcon(QIcon(funcs.rc('/ui/icons/icon.svg')))
        # openbutton
        self.openbutton.clicked.connect(self.openFinancial)
        # newbutton
        self.newbutton.setIcon(QIcon(icons.get('document-add.png')))
        self.newbutton.clicked.connect(self.newFinancial)
        # filepath
        self.fillDefaultFilepath(default)
        # buttonBox
        self.buttonBox.button(
            QDialogButtonBox.Ok).clicked.connect(self.accept)
        self.buttonBox.button(
            QDialogButtonBox.Close).clicked.connect(self.reject)

    def fillDefaultFilepath(self, default: str = ''):
        if os.path.exists(default):
            fp = default
        else:
            fp = self._settings.value('' + appinfos.app_name + '/defaultfile', '')
        if os.path.exists(fp):
            self.filepath.setText(fp)
            self.isdefault.setChecked(True)
            self.password.setFocus()
        else:
            self.filepath.setFocus()

    def openFinancial(self):
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        fileName, _ = QFileDialog.getOpenFileName(self,
                                                  funcs.tr("Dossier financier"),
                                                  os.path.dirname(self.filepath.text())
                                                  if os.path.exists(self.filepath.text())
                                                  else os.path.expanduser('~'),
                                                  appinfos.app_name + ' (*.kot)',
                                                  options=options)
        if fileName:
            self.filepath.setText(fileName)
            self.password.clear()
            self.password.setFocus()

    def newFinancial(self):
        ed = EditDialog(self._settings, self._locale, self, fi=None)
        ed.setWindowTitle(funcs.tr("Nouveau dossier financier"))
        if ed.exec_() == QMessageBox.Accepted:
            if not ed.fi.save():
                QMessageBox.warning(self, '' + appinfos.app_name + '',
                                    funcs.tr("<b>Oh la, il m'est impossible de créer un nouveau dossier financier!</b>"))
                self.newFinancial()
            else:
                self.filepath.setText(ed.fi.filepath)
                self.password.setText(ed.fi.password)
                self.buttonBox.button(QDialogButtonBox.Ok).setFocus()
        else:
            self.fillDefaultFilepath(default='')
            self.password.clear()
            if os.path.exists(self.filepath.text().strip()):
                self.password.setFocus()
            else:
                self.filepath.clear()
                self.filepath.setFocus()