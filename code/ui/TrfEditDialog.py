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

import libs.currencies
import libs.completer
import resources
import appinfos
import funcs
import icons

from datamodels import *


class TrfEditDialog(QDialog):

    _settings = None
    _locale = None
    _fi = None
    _act = None

    trf = None

    added = pyqtSignal()

    def __init__(self, settings, locale, parent, fi: financial, act: account, trf: transfer = None, nokeep=False, *args, **kwargs):
        self._settings = settings
        self._locale = locale
        self._fi = fi
        self._act = act
        self.trf = trf
        self._nokeep = nokeep
        self._shortDateFormat = self._settings.value('short_date_format')
        self._longDateFormat = self._settings.value('long_date_format')
        super(TrfEditDialog, self).__init__(parent, Qt.Window |
                                            Qt.WindowTitleHint | Qt.CustomizeWindowHint, *args, **kwargs)
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
        self.setWindowIcon(QIcon(icons.get('transfer.png')))
        # buttonBox
        self.buttonBox.button(
            QDialogButtonBox.Save).clicked.connect(self.validateForm)
        # trfFromdate
        self.trfFromdate.dateChanged.connect(self.dateChanged)
        self.trfFromdate.setDate(datetime.now())
        # trfActualCredit
        self.trfActualCredit.setText(libs.currencies.formatCurrency(
            abs(self._act.credit), self._act.alpha_3))
        # trfAmount
        self.trfAmount.setPrefix(currency.symbol(self._act.alpha_3) + ' ')
        self.trfAmount.valueChanged.connect(self.amountChanged)
        self.trfAmount.installEventFilter(self)
        # trfTitle
        self.trfTitle.setCompleter(libs.completer.get(self._settings))
        # trfComment
        self.trfComment.setCompleter(libs.completer.get(self._settings))
        # trfToactlist
        self.populateTo()
        # saveKeepButton
        self.saveKeepButton.setIcon(QIcon(icons.get('document-save.png')))
        self.saveKeepButton.clicked.connect(
            lambda: self.validateForm(keep=True))
        if not(self.trf is None) or self._nokeep:
            self.saveKeepButton.setVisible(False)

        if not(self.trf is None):
            self.trfTitle.setText(self.trf.title)
            self.trfComment.setText(self.trf.comment)
            self.trfState.setChecked(self.trf.state)
            self.trfAmount.setValue(self.trf.amount)
            self.trfFromdate.setDate(self.trf.fromdate)
            for i in range(self.trfToactlist.count()):
                a = self.trfToactlist.itemData(i, Qt.UserRole)
                if not(a is None) and a.id == self.trf.toactid:
                    self.trfToactlist.setCurrentIndex(i)
                    break

    def closeEvent(self, event):
        event.ignore()

    def eventFilter(self, obj, event):
        if event.type() == QEvent.FocusIn:
            obj.setStyleSheet('')
            try:
                obj.setPlaceholderText('')
            except:
                pass

        if obj == self.trfAmount:
            if event.type() == QEvent.KeyPress:
                if event.key() == Qt.Key_Period:
                    event = QKeyEvent(event.type(),
                                      Qt.Key_Comma,
                                      event.modifiers(),
                                      ",",
                                      event.isAutoRepeat(),
                                      event.count())
                    QApplication.sendEvent(obj, event)
                    return True

        return super(TrfEditDialog, self).eventFilter(obj, event)

    def amountChanged(self, value):
        if abs(value) > self.amountmax:
            self.trfAmount.setStyleSheet(
                "#trfAmount { background: #FFF0F5; }")
        else:
            self.trfAmount.setStyleSheet("")

    def dateChanged(self, dte):
        amt = self._fi.amount_atdate(self._act.id, dte)
        self.trfActualAmount.setText(
            libs.currencies.formatCurrency(amt, self._act.alpha_3))
        if amt < 0.0:
            self.trfActualAmount.setStyleSheet(
                "#trfActualAmount { color: " + self._settings.value('color_positive_amount') + "; }")
        if amt < self._act.credit:
            self.trfActualAmount.setStyleSheet(
                "#trfActualAmount { color: " + self._settings.value('color_credit_amount') + "; }")
        if amt >= 0.0:
            self.trfActualAmount.setStyleSheet(
                "#trfActualAmount { color: " + self._settings.value('color_positive_amount') + "; }")
        self.amountmax = amt + abs(self._act.credit)
        self.amountChanged(self.trfAmount.value())

    def populateTo(self):
        self.trfToactlist.clear()
        model = QStandardItemModel()
        a = QStandardItem('')
        a.setData(None, Qt.UserRole)
        model.appendRow(a)
        hasaccount = False
        for a in self._fi.accounts:
            ha = hasattr(a, 'accountid')
            if ((type(a) == bankaccount) or
                    (type(a) == wallet) or
                (type(a) == creditcard and a.accountid == -1)) and \
                    (a.id != self._act.id):
                i = QStandardItem(a.title)
                i.setData(a, Qt.UserRole)
                model.appendRow(i)
                hasaccount = True
        self.trfToactlist.setModel(model)
        self.trfToactlist.setCurrentIndex(0)
        if not hasaccount:
            QMessageBox.warning(self, '' + appinfos.app_name + '', funcs.tr(
                "Aucun compte dans votre portefeuille n'est éligible au transfert!"))

    def validateForm(self, keep=False):
        # toactid
        i = self.trfToactlist.currentIndex()
        a = self.trfToactlist.itemData(i, Qt.UserRole)
        if a is None:
            QMessageBox.warning(self, '' + appinfos.app_name + '', funcs.tr(
                "Vous devez spécifier un compte vers lequel transférer la somme indiquée!"))
            return
        toactid = a.id
        # title
        title = self.trfTitle.text().strip()
        # comment
        comment = self.trfComment.text().strip()
        # fromdate
        fromdate = self.trfFromdate.date().toPyDate()
        # amount
        amt = self.trfAmount.value()
        # state
        state = self.trfState.isChecked()

        if self.trfTitle.text().strip() != '':
            libs.completer.add(self._settings, self.trfTitle.text())
        if self.trfComment.text().strip() != '':
            libs.completer.add(self._settings, self.trfComment.text())

        id = self.trf.id if not(
            self.trf is None) else datetime.now().timestamp()
        self.trf = transfer(title=title,
                            id=id,
                            amount=amt,
                            fromdate=fromdate,
                            comment=comment,
                            fromactid=self._act.id,
                            toactid=toactid,
                            state=state)

        if keep:
            self.added.emit()
            return

        self.accept()
