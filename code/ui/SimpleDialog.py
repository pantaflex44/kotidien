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
from datetime import datetime

from PyQt5 import QtCore, QtWidgets, QtGui, uic
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *

import libs.pycountry
import currency

import libs.completer
import resources
import appinfos
import funcs
import icons

from datamodels import *


class SimpleDialog(QDialog):

    _settings = None
    _locale = None

    txt = ''

    def __init__(self, settings, locale, parent=None, txt: str = '', *args, **kwargs):
        self._settings = settings
        self._locale = locale
        self.txt = txt
        super(SimpleDialog, self).__init__(parent, Qt.Window
                                           | Qt.WindowTitleHint | Qt.CustomizeWindowHint, *args, **kwargs)
        self._init_ui()

    def _init_ui(self):
        # self
        self.ui = funcs.loadUiResource(funcs.rc('/ui/' + self.__class__.__name__ + '.ui'), self)
        self.setLocale(QLocale(self._locale))
        self.ui.setLocale(QLocale(self._locale))
        self.setModal(True)
        qtRectangle = self.frameGeometry()
        centerPoint = QDesktopWidget().geometry().center()
        qtRectangle.moveCenter(centerPoint)
        self.move(qtRectangle.topLeft())
        self.setFixedSize(self.size())
        self.setWindowIcon(QIcon(funcs.rc('/ui/icons/icon.svg')))
        # buttonBox
        self.buttonBox.button(
            QDialogButtonBox.Ok).clicked.connect(self.validateForm)
        # txtInput
        self.txtInput.setCompleter(libs.completer.get(self._settings))
        self.txtInput.setText(self.txt)
        self.txtInput.installEventFilter(self)

    def closeEvent(self, event):
        event.ignore()

    def eventFilter(self, obj, event):
        if event.type() == QEvent.FocusIn:
            obj.setStyleSheet('')
            try:
                obj.setPlaceholderText('')
            except:
                pass
        return super(SimpleDialog, self).eventFilter(obj, event)

    def validateForm(self):
        self.txt = self.txtInput.text().strip()
        self.accept()
