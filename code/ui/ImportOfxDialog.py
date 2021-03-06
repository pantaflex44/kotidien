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
import csv
from datetime import datetime

from PyQt5 import QtCore, QtWidgets, QtGui, uic
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *

import libs.pycountry
import currency
from ofxtools.Parser import OFXTree

import libs.currencies
import libs.completer
import resources
import appinfos
import funcs
import icons

from ui.OpeEditDialog import OpeEditDialog

from datamodels import *


class HTMLDelegate(QStyledItemDelegate):

    def __init__(self, parent, settings):
        super(HTMLDelegate, self).__init__(parent)
        self.pen = QPen(QColor(Qt.lightGray))
        self._settings = settings

    def paint(self, painter, option, index):
        options = QStyleOptionViewItem(option)
        self.initStyleOption(options, index)

        style = QApplication.style() if options.widget is None else options.widget.style()
        painter.save()

        ctx = QAbstractTextDocumentLayout.PaintContext()
        mouseOver = (option.state & QStyle.State_MouseOver)

        if type(options.widget) == QTreeView:
            if mouseOver and options.widget.objectName() == 'opeList':
                viewportPos = options.widget.viewport().mapFromGlobal(QCursor.pos())
                if viewportPos.x() >= 0 and viewportPos.y() >= 0:
                    color = option.palette.color(QPalette.Active, QPalette.Highlight)
                    color.setAlpha(30)
                    painter.fillRect(option.rect, color)

        style.drawControl(QStyle.CE_ItemViewItem, options, painter)
        painter.restore()

    def sizeHint(self, option, index):
        size = super(HTMLDelegate, self).sizeHint(option, index)
        options = QStyleOptionViewItem(option)
        self.initStyleOption(options, index)
        return size


class ImportOfxDialog(QDialog):

    _settings = None
    _locale = None

    _file = ''
    _fi = None

    def __init__(self, settings, locale, fi: financial, file:str=None, parent=None, *args, **kwargs):
        self._settings = settings
        self._locale = locale
        self._fi = fi
        self._file = file
        super(ImportOfxDialog, self).__init__(parent, Qt.Window
                                           | Qt.WindowTitleHint | Qt.CustomizeWindowHint, *args, **kwargs)
        self._init_ui()
        self.setWindowTitle(os.path.basename(self._file))
        self.populateAccountsList()
        self.openOfxFile()

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
        self.setWindowIcon(QIcon(icons.get('ofx.png')))
        self.setMouseTracking(True)
        # buttonBox
        self.buttonBox.button(QDialogButtonBox.Ok).clicked.connect(self.validateForm)
        # links
        self.selectAll.linkActivated.connect(self.selectCmdClicked)
        self.unselectAll.linkActivated.connect(self.selectCmdClicked)
        # opeList
        self.opeList.doubleClicked.connect(self.doubleClicked)
        self.opeList.viewport().setMouseTracking(True)

    def closeEvent(self, event):
        event.ignore()

    def eventFilter(self, obj, event):
        if event.type() == QEvent.FocusIn:
            obj.setStyleSheet('')
            try:
                obj.setPlaceholderText('')
            except:
                pass
        return super(ImportOfxDialog, self).eventFilter(obj, event)

    def populateAccountsList(self):
        self.accountsList.clear()
        model = QStandardItemModel()

        r = QStandardItem('')
        r.setData(None, Qt.UserRole)
        r.setBackground(QColor(Qt.white))
        model.appendRow(r)
        for a in self._fi.accounts:
            if not(type(a) == bankaccount):
                continue

            t = a.title.strip()
            n = a.name.strip() if hasattr(a, 'name') and a.name.strip() != '' else ''
            if n != '':
                t = t + ' (' + n + ')'
            r = QStandardItem(t)
            r.setData(a, Qt.UserRole)
            r.setBackground(QColor(Qt.white))
            model.appendRow(r)

        self.accountsList.setModel(model)

    def openOfxFile(self):
        if not os.path.isfile(self._file) or \
           not os.access(self._file, os.R_OK):
            QMessageBox.critical(self, appinfos.app_name, funcs.tr(
                "Impossible de lire le fichier 'Open Financial Exchange' sélectionné!"))
            self.reject()

        try:
            QApplication.setOverrideCursor(Qt.WaitCursor)

            self.opeList.setModel(None)
            m = QStandardItemModel()
            columns = ["Date", "Tiers", "Dénomination", "Moyen de paiement", "Montant"]
            m.setColumnCount(len(columns))
            for i in range(len(columns)):
                m.setHeaderData(i, QtCore.Qt.Horizontal, funcs.tr(columns[i]))

            parser = OFXTree()
            parser.parse(self._file)
            ofx = parser.convert()
            bankmsgsrs = ofx.bankmsgsrsv1
            stmttrnrs = ofx.statements
            for stmtrs in stmttrnrs:
                alpha_3 = stmtrs.curdef if stmtrs.curdef.strip() != '' else 'EUR'
                tranlist = stmtrs.transactions
                for stmttrn in tranlist:
                    dte_value = stmttrn.dtposted.date() if not(stmttrn.dtposted is None) else datetime.now().date()
                    to_value = stmttrn.name.strip().capitalize() if not(stmttrn.name is None) else ''
                    if to_value.strip() == '':
                        to_value = funcs.tr("Inconnu")
                    title_value = stmttrn.memo.strip().capitalize() if not(stmttrn.memo is None) else ''
                    paytype_value = 'Transaction diverse'
                    if not(stmttrn.trntype is None):
                        if stmttrn.trntype == 'PAYMENT':
                            paytype_value = 'Carte de crédit'
                        elif stmttrn.trntype == 'CHECK':
                            paytype_value = 'Chèque'
                        elif stmttrn.trntype == 'DEBIT':
                            paytype_value = 'Prélèvement'
                        elif stmttrn.trntype == 'PAYMENT':
                            paytype_value = 'Virement ponctuel'
                        elif stmttrn.trntype == 'REPEATPMT':
                            paytype_value = 'Virement permanent'
                        elif stmttrn.trntype == 'XFER':
                            paytype_value = 'Transfert'
                        elif stmttrn.trntype == 'CASH':
                            paytype_value = 'Espèces'
                        elif stmttrn.trntype == 'PAYMENT':
                            paytype_value = 'Frais'
                        elif stmttrn.trntype == 'DEP':
                            paytype_value = 'Dépot'
                    amt_value = float(stmttrn.trnamt) if not(stmttrn.trnamt is None) else 0.0

                    data = operation(title=title_value,
                                     id=datetime.now().timestamp(),
                                     amount=amt_value,
                                     fromdate=dte_value,
                                     comment='',
                                     to=to_value,
                                     paytype=paytype_value,
                                     category='Autre',
                                     state=False)

                    dte = QStandardItem()
                    dte.setText(dte_value.strftime('%x'))
                    dte.setEditable(False)
                    dte.setData(dte_value, Qt.UserRole)
                    dte.setCheckable(True)
                    dte.setCheckState(Qt.Checked)

                    to = QStandardItem()
                    to.setText(to_value)
                    to.setEditable(False)
                    to.setData(data, Qt.UserRole)

                    title = QStandardItem()
                    title.setText(title_value)
                    title.setEditable(False)
                    title.setData(data, Qt.UserRole)

                    ptype = QStandardItem()
                    ptype.setText(funcs.tr(paytype_value))
                    ptype.setEditable(False)
                    ptype.setData(data, Qt.UserRole)

                    amt = QStandardItem()
                    amt.setText(libs.currencies.formatCurrency(amt_value, alpha_3))
                    amt.setEditable(False)
                    amt.setData(data, Qt.UserRole)

                    m.appendRow([dte, to, title, ptype, amt])

            self.opeList.setModel(m)
            self.opeList.setItemDelegate(HTMLDelegate(parent=None, settings=self._settings))
            for i in range(len(columns)):
                self.opeList.resizeColumnToContents(i)

            self.opeList.model().setSortRole(Qt.UserRole)
            self.opeList.model().sort(0, Qt.AscendingOrder)

            QApplication.restoreOverrideCursor()
        except:
            QApplication.restoreOverrideCursor()
            QMessageBox.critical(self, appinfos.app_name, funcs.tr(
                "Impossible de lire les données à importer.<br />Le format du fichier serait-il incorrect? {} accepte le format OFX de Money 98 et supérieurs.").format(appinfos.app_name))
            self.destroy()

    def doubleClicked(self, index):
        if not(index is None) and not(self.opeList.model() is None):
            act = self.accountsList.currentData()
            if act is None:
                QMessageBox.warning(self, appinfos.app_name, funcs.tr(
                    "Veuillez choisir le compte d'affectation avant de modifier cette opération!"))
                return

            itm = self.opeList.model().index(index.row(), 1)
            ot = itm.data(Qt.UserRole)

            if type(ot) == operation:
                oed = OpeEditDialog(self._settings,
                                    self._locale,
                                    self,
                                    self._fi,
                                    act,
                                    ope=ot)
                if oed.exec_() == QMessageBox.Accepted:
                    pass
                oed.destroy()

    def selectItem(self, item, state:bool):
        item.setCheckState(Qt.Checked if state else Qt.Unchecked)
        for i in range(item.rowCount()):
            child = item.child(i)
            self.selectItem(child, state)

    def selectCmdClicked(self, cmd):
        if not(self.opeList.model() is None) and not(self.opeList.model().invisibleRootItem() is None):
            self.selectItem(self.opeList.model().invisibleRootItem(), cmd == 'selectall')

    def validateForm(self):
        datas = []
        model = self.opeList.model()
        checked = model.match(
            model.index(0, 0), Qt.CheckStateRole, Qt.Checked, -1,
            Qt.MatchExactly | Qt.MatchRecursive)
        for index in checked:
            item = model.index(index.row(), 1)
            datas.append(item.data(Qt.UserRole))
        if len(datas) == 0:
            QMessageBox.warning(self, appinfos.app_name, funcs.tr(
                "<b>Erreur</b><br />Veuillez cocher les transactions à importer."))
            return

        acct = self.accountsList.currentData()
        if acct is None:
            QMessageBox.warning(self, appinfos.app_name, funcs.tr(
                "<b>Erreur</b><br />Veuillez sélectionner le compte concerné par les données à importer."))
            return

        for o in datas:
            if o.to.strip() == '':
                continue

            if not(o.paytype in self._fi.paytypes):
                self._fi.paytypes.append(o.paytype)

            pc = o.category.split(':')
            p = pc[0].strip()
            c = pc[1].strip() if len(pc) > 1 else ''
            category = p
            if not(p in self._fi.categories.keys()):
                self._fi.categories[p] = []
            if c != '':
                category += ': ' + c
                if not(c in self._fi.categories[p]):
                    self._fi.categories[p].append(c)

            acct.operations.append(o)

        self.accept()
