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


class ValidateThirdpartyName(QtGui.QValidator):

    thirdparties = []

    def __init__(self, parent, thirdparties=[]):
        QtGui.QValidator.__init__(self, parent)
        self.thirdparties = thirdparties

    def validate(self, s, pos):
        if s in self.thirdparties:
            return (QValidator.Invalid, s, pos)
        else:
            return (QValidator.Acceptable, s, pos)

    def fixup(self, s):
        pass


class ThirdpartiesDialog(QDialog):

    _settings = None
    _locale = None

    _thirdparties = []

    fi = None
    updated = False

    def __init__(self, settings, locale, fi: financial, parent=None, *args, **kwargs):
        self._settings = settings
        self._locale = locale
        self.fi = fi
        super(ThirdpartiesDialog, self).__init__(parent, Qt.Window
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
        self.setWindowIcon(QIcon(icons.get('toolbar-thirdparty.png')))
        # buttonBox
        self.buttonBox.button(
            QDialogButtonBox.Close).clicked.connect(self.validateForm)
        # tpList
        self.populateTpList()
        # tpTitle
        self.tpTitle.textChanged.connect(self.tpTitleChanged)
        # tpCategory
        self.populateCategories()
        # tpPaytype
        self.populatePaytypes()
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
        return super(ThirdpartiesDialog, self).eventFilter(obj, event)

    def validateForm(self):
        self.accept()

    def foundTp(self, name: str):
        getrow = -1
        getitem = None
        for row in range(self.tpList.model().rowCount()):
            item = self.tpList.model().itemFromIndex(
                self.tpList.model().index(row, 0))
            d = item.data(Qt.UserRole)
            if isinstance(d, list) and \
                    d[0].lower() == name.strip().lower():
                getrow = row
                getitem = item
                break
        return getrow, getitem

    def populateTpList(self, selected: str = ''):
        self.tpList.setModel(None)
        m = QStandardItemModel()
        m.setColumnCount(1)
        m.setHeaderData(0, QtCore.Qt.Horizontal, funcs.tr(
            "Liste des tiers ({})".format(len(self.fi.thirdparties))))
        for t in self.fi.thirdparties:
            row = QStandardItem()
            row.setText(funcs.tr(t.title))
            row.setEditable(False)
            row.setData([t.title, t.category, t.paytype], Qt.UserRole)
            pc = t.category.split(': ')
            self._thirdparties.append(t.title)
            m.appendRow(row)
        self.tpList.setModel(m)
        self.tpList.header().setSectionResizeMode(0, QHeaderView.Stretch)
        f = self.tpList.header().font()
        f.setBold(True)
        self.tpList.header().setFont(f)
        self.tpList.sortByColumn(0, Qt.AscendingOrder)
        self.tpList.expandAll()
        self.tpList.selectionModel().selectionChanged.connect(self.tpListSelected)
        self.tpTitle.setFocus()
        if selected.strip() != '':
            row, item = self.foundTp(selected)
            if row > -1 and not(self.tpList.selectionModel() is None):
                self.tpList.setCurrentIndex(
                    self.tpList.model().index(row, 0))
                self.tpListSelected(item, None)
                self.tpList.setFocus()

    def tpTitleChanged(self, text):
        row, item = self.foundTp(text)
        if row > -1:
            self.tpList.setCurrentIndex(self.tpList.model().index(row, 0))
        self.saveButton.setEnabled(text.strip() != '')

    def tpListSelected(self, new, old):
        self.removeButton.setEnabled(False)
        index = None
        if isinstance(new, QItemSelection):
            if len(new.indexes()) > 0:
                index = new.indexes()[0]
        else:
            index = new.index()
        if not(index is None):
            row = self.tpList.model().itemFromIndex(index)
            title, category, paytype = row.data(Qt.UserRole)
            self.tpTitle.setText(title)
            i = self.tpCategory.findData(category)
            if i > -1:
                self.tpCategory.setCurrentIndex(i)
            j = self.tpPaytype.findData(paytype)
            if j > -1:
                self.tpPaytype.setCurrentIndex(j)
            self.removeButton.setEnabled(True)
            self.clearButton.setEnabled(True)
        self.saveButton.setEnabled(False)

    def populateCategories(self, selected: str = ''):
        self.tpCategory.clear()
        model = QStandardItemModel()
        a = QStandardItem('')
        a.setData('', Qt.UserRole)
        a.setBackground(QBrush(QColor.fromRgb(255, 255, 255)))
        model.appendRow(a)
        for k, v in self.fi.categories.items():
            i = QStandardItem(funcs.tr(k))
            f = i.font()
            f.setBold(True)
            i.setFont(f)
            i.setData(k, Qt.UserRole)
            color, html = funcs.text2color(funcs.tr(k))
            i.setForeground(
                QBrush(QColor.fromRgb(color[0], color[1], color[2])))
            i.setBackground(a.background())
            model.appendRow(i)
            if isinstance(v, list):
                for c in v:
                    j = QStandardItem(funcs.tr(k) + ": " + funcs.tr(c))
                    j.setData(k + ": " + c, Qt.UserRole)
                    j.setForeground(i.foreground())
                    j.setBackground(a.background())
                    model.appendRow(j)
        self.tpCategory.setModel(model)
        self.tpCategory.currentIndexChanged.connect(
            self.tpCategoryIndexChanged)
        if selected.strip() != '':
            index = self.tpCategory.findData(selected.strip())
            if index == -1:
                index = 0
            self.tpCategory.setCurrentIndex(index)

    def tpCategoryIndexChanged(self, index):
        self.tpTitleChanged(self.tpTitle.text())

    def populatePaytypes(self):
        self.tpPaytype.clear()
        model = QStandardItemModel()
        a = QStandardItem('')
        a.setData('', Qt.UserRole)
        a.setBackground(QBrush(QColor.fromRgb(255, 255, 255)))
        model.appendRow(a)
        for p in self.fi.paytypes:
            i = QStandardItem(funcs.tr(p))
            i.setData(p, Qt.UserRole)
            i.setBackground(a.background())
            model.appendRow(i)
        self.tpPaytype.setModel(model)
        self.tpPaytype.currentIndexChanged.connect(
            self.tpPaytypeIndexChanged)

    def tpPaytypeIndexChanged(self, index):
        self.tpTitleChanged(self.tpTitle.text())

    def saveButtonClicked(self):
        n = self.tpTitle.text().strip()
        c = self.tpCategory.currentData(Qt.UserRole)
        p = self.tpPaytype.currentData(Qt.UserRole)
        tp = thirdparty(title=n,
                        paytype=p,
                        category=c)
        row, item = self.foundTp(n)
        if row > -1:
            for t in self.fi.thirdparties:
                if t.title.lower() == n.lower():
                    self.fi.thirdparties.remove(t)
                    break
        self.fi.thirdparties.append(tp)
        self.updated = True
        self.tpTitle.clear()
        self.tpCategory.setCurrentIndex(0)
        self.tpPaytype.setCurrentIndex(0)
        self.populateTpList(n)

    def removeButtonClicked(self):
        if self.tpList.selectionModel() is None:
            self.removeButton.setEnabled(False)
        if len(self.tpList.selectionModel().selectedIndexes()) == 0:
            self.removeButton.setEnabled(False)
        selected = self.tpList.selectionModel().selectedIndexes()[0]
        item = self.tpList.model().itemFromIndex(selected)
        title, category, paytype = item.data(Qt.UserRole)
        reply = QMessageBox.question(self, '' + appinfos.app_name + '',
                                     funcs.tr(
                                         "Etes-vous certain de vouloir supprimer le tiers '{}'"
                                         .format(title)),
                                     QMessageBox.Yes, QMessageBox.No)
        if reply == QMessageBox.Yes:
            for t in self.fi.thirdparties:
                if t.title.lower() == title.lower():
                    self.fi.thirdparties.remove(t)
                    self.updated = True
                    break
            self.tpTitle.clear()
            self.tpCategory.setCurrentIndex(0)
            self.tpPaytype.setCurrentIndex(0)
            self.populateTpList()

    def clearButtonClicked(self):
        self.tpTitle.clear()
        self.tpCategory.setCurrentIndex(-1)
        self.tpPaytype.setCurrentIndex(-1)
        self.tpList.selectionModel().clearSelection()
        self.tpTitle.setFocus()
        self.clearButton.setEnabled(False)


