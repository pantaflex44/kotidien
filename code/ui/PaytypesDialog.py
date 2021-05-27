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


class PaytypesDialog(QDialog):

    _settings = None
    _locale = None

    fi = None
    updated = False

    def __init__(self, settings, locale, fi: financial, parent=None, *args, **kwargs):
        self._settings = settings
        self._locale = locale
        self.fi = fi
        super(PaytypesDialog, self).__init__(parent, Qt.Window
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
        self.setWindowIcon(QIcon(icons.get('toolbar-paytype.png')))
        # buttonBox
        self.buttonBox.button(
            QDialogButtonBox.Close).clicked.connect(self.validateForm)
        # ptList
        self.populatePtList()
        # ptTitle
        self.ptTitle.textChanged.connect(self.ptTitleChanged)
        # saveButton
        self.saveButton.setIcon(QIcon(icons.get('document-save.png')))
        self.saveButton.clicked.connect(self.saveButtonClicked)
        # removeButton
        self.removeButton.setIcon(QIcon(icons.get('document-delete.png')))
        self.removeButton.clicked.connect(self.removeButtonClicked)
        # clearButton
        self.clearButton.setIcon(QIcon(icons.get('clear.png')))
        self.clearButton.clicked.connect(self.clearButtonClicked)

    def closeEvent(self, event):
        event.ignore()

    def eventFilter(self, obj, event):
        if event.type() == QEvent.FocusIn:
            obj.setStyleSheet('')
            try:
                obj.setPlaceholderText('')
            except:
                pass
        return super(PaytypesDialog, self).eventFilter(obj, event)

    def validateForm(self):
        self.accept()

    def foundPt(self, name: str):
        getrow = -1
        getitem = None
        for row in range(self.ptList.model().rowCount()):
            item = self.ptList.model().itemFromIndex(
                self.ptList.model().index(row, 0))
            d = item.data(Qt.UserRole)
            if isinstance(d, str) and \
                    d.lower() == name.strip().lower():
                getrow = row
                getitem = item
                break
        return getrow, getitem

    def populatePtList(self, selected: str = ''):
        self.ptList.setModel(None)
        m = QStandardItemModel()
        m.setColumnCount(1)
        m.setHeaderData(0, QtCore.Qt.Horizontal, funcs.tr(
            "Liste des moyens de paiements ({})".format(len(self.fi.paytypes))))
        for t in self.fi.paytypes:
            row = QStandardItem()
            row.setText(funcs.tr(t))
            row.setEditable(False)
            row.setData(t, Qt.UserRole)
            m.appendRow(row)
        self.ptList.setModel(m)
        self.ptList.header().setSectionResizeMode(0, QHeaderView.Stretch)
        f = self.ptList.header().font()
        f.setBold(True)
        self.ptList.header().setFont(f)
        self.ptList.sortByColumn(0, Qt.AscendingOrder)
        self.ptList.expandAll()
        self.ptList.selectionModel().selectionChanged.connect(self.ptListSelected)
        self.ptTitle.setFocus()
        if selected.strip() != '':
            row, item = self.foundPt(selected)
            if row > -1 and not(self.ptList.selectionModel() is None):
                self.ptList.setCurrentIndex(
                    self.ptList.model().index(row, 0))
                self.ptListSelected(item, None)
                self.ptList.setFocus()

    def ptTitleChanged(self, text):
        row, item = self.foundPt(text)
        if row > -1:
            self.ptList.setCurrentIndex(self.ptList.model().index(row, 0))
        self.saveButton.setEnabled(text.strip() != '')

    def ptListSelected(self, new, old):
        self.removeButton.setEnabled(False)
        index = None
        if isinstance(new, QItemSelection):
            if len(new.indexes()) > 0:
                index = new.indexes()[0]
        else:
            index = new.index()
        if not(index is None):
            row = self.ptList.model().itemFromIndex(index)
            title = row.data(Qt.UserRole)
            self.ptTitle.setText(title)
            self.removeButton.setEnabled(True)
            self.clearButton.setEnabled(True)
        self.saveButton.setEnabled(False)

    def saveButtonClicked(self):
        n = self.ptTitle.text().strip()
        row, item = self.foundPt(n)
        if row > -1:
            for t in self.fi.paytypes:
                if t.lower() == n.lower():
                    self.fi.paytypes.remove(t)
                    break
        self.fi.paytypes.append(n)
        self.updated = True
        self.ptTitle.clear()
        self.populatePtList(n)

    def removeButtonClicked(self):
        if self.ptList.selectionModel() is None:
            self.removeButton.setEnabled(False)
        if len(self.ptList.selectionModel().selectedIndexes()) == 0:
            self.removeButton.setEnabled(False)
        selected = self.ptList.selectionModel().selectedIndexes()[0]
        item = self.ptList.model().itemFromIndex(selected)
        title = item.data(Qt.UserRole)
        reply = QMessageBox.question(self, '' + appinfos.app_name + '',
                                     funcs.tr(
                                         "Etes-vous certain de vouloir supprimer le moyen de paiement '{}'"
                                         .format(title)),
                                     QMessageBox.Yes, QMessageBox.No)
        if reply == QMessageBox.Yes:
            for t in self.fi.paytypes:
                if t.lower() == title.lower():
                    self.fi.paytypes.remove(t)
                    self.updated = True
                    break
            self.ptTitle.clear()
            self.populatePtList()

    def clearButtonClicked(self):
        self.ptTitle.clear()
        self.ptList.selectionModel().clearSelection()
        self.ptTitle.setFocus()
        self.clearButton.setEnabled(False)


