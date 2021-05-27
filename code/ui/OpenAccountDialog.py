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


class OpenAccountDialog(QDialog):

    _settings = None
    _locale = None

    _fi = None
    act = None

    def __init__(self, settings, locale, parent=None, act: account = None, fi: financial = None, *args, **kwargs):
        self._settings = settings
        self._locale = locale
        self.act = act
        self._fi = fi
        super(OpenAccountDialog, self).__init__(parent, Qt.Window
                                                | Qt.WindowTitleHint | Qt.CustomizeWindowHint, *args, **kwargs)
        self._init_ui(act)
        QApplication.clipboard().dataChanged.connect(self.clipboardChanged)
        self.clipboardChanged()

    def _init_ui(self, act: account):
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
        self.accountTitle.installEventFilter(self)
        # buttonBox
        self.buttonBox.button(QDialogButtonBox.Ok).clicked.connect(
            self.validateForm)
        # accountTitle
        self.accountTitle.setText(act.title)
        # accountAlpha3
        self.accountAlpha3.currentIndexChanged.connect(self.alpha3changed)
        self.accountAlpha3.clear()
        for c in list(libs.pycountry.currencies):
            self.accountAlpha3.addItem(
                "{} - {}".format(c.alpha_3, c.name), c)
        idx = self.accountAlpha3.findText(self.act.alpha_3, Qt.MatchContains)
        self.accountAlpha3.setCurrentIndex(idx)
        # accountAmount
        self.accountAmount.setValue(act.amount)
        self.accountAmount.installEventFilter(self)
        # accountCredit
        self.accountCredit.setValue(act.credit)
        self.accountCredit.installEventFilter(self)
        # bankIban
        rgxIban = QRegExp(ibanmask, Qt.CaseInsensitive)
        vldIban = QRegExpValidator(rgxIban, self.bankIban)
        self.bankIban.setValidator(vldIban)
        self.bankIban.textChanged.connect(
            lambda text: self.bankIban.setText(text.upper()))
        # bankBic
        rgxBic = QRegExp(bicmask, Qt.CaseInsensitive)
        vldBic = QRegExpValidator(rgxBic, self.bankBic)
        self.bankBic.setCompleter(libs.completer.get(self._settings))
        self.bankBic.setValidator(vldBic)
        self.bankBic.textChanged.connect(
            lambda text: self.bankBic.setText(text.upper()))
        # ccNumber
        rgxCCNumber = QRegExp(cardmask, Qt.CaseInsensitive)
        vldCCNumber = QRegExpValidator(rgxCCNumber, self.ccNumber)
        self.ccNumber.setValidator(vldCCNumber)
        # ccCode
        rgxCCCode = QRegExp(cvvmask, Qt.CaseInsensitive)
        vldCCCode = QRegExpValidator(rgxCCCode, self.ccCode)
        self.ccCode.setValidator(vldCCCode)
        # ccAccounts
        self.ccAccountsList.clear()
        self.ccAccountsList.addItem(funcs.tr("(aucun)"), -1)
        if self._fi.accounts != None:
            for a in self._fi.accounts:
                if type(a) is bankaccount:
                    self.ccAccountsList.addItem(
                        '{} ({})'.format(a.title, a.name), a.id)
        self.ccAccountsList.currentIndexChanged.connect(
            self.ccAccountsListCurrentChanged)
        # tabView
        self.tabView.removeTab(1)
        self.tabView.removeTab(1)
        self.tabView.removeTab(1)
        if type(act) is bankaccount:
            self.bankName.setText(act.name)
            self.bankName.setCompleter(libs.completer.get(self._settings))
            self.bankIban.setText(act.iban)
            self.bankBic.setText(act.bic)
            self.tabView.addTab(self.tabBank,
                                QIcon(icons.get('bank.png')),
                                funcs.tr("Compte en banque"))
        elif type(act) is creditcard:
            self.ccName.setText(act.name)
            self.ccName.setCompleter(libs.completer.get(self._settings))
            self.ccNumber.setText(act.number)
            self.ccDate.setDateTime(datetime(act.year, act.month, 1))
            self.ccCode.setText(act.code)
            idx = 0
            for i in range(self.ccAccountsList.count()):
                if float(self.ccAccountsList.itemData(i)) == self.act.accountid:
                    idx = i
                    break
            self.ccAccountsList.setCurrentIndex(idx)
            self.tabView.addTab(self.tabCreditCard,
                                QIcon(icons.get('credit-card.png')),
                                funcs.tr("Carte de paiement"))
        elif type(act) is wallet:
            self.walletElectronic.setCheckState(Qt.Checked
                                                if act.electronic else Qt.Unchecked)
            self.accountCredit.setValue(0.0)
            self.accountCredit.setEnabled(False)
            self.tabView.addTab(self.tabWallet,
                                QIcon(icons.get('money.png')),
                                funcs.tr("Portefeuille d'espèces"))
        self.tabView.setCurrentIndex(0)
        self.tabView.currentChanged.connect(self.tabChanged)
        # paste
        self.pasteIban.clicked.connect(self.pasteIbanClicked)
        self.pasteBic.clicked.connect(self.pasteBicClicked)
        self.pasteNumber.clicked.connect(self.pasteNumberClicked)
        self.pasteCode.clicked.connect(self.pasteCodeClicked)

        self.pasteIban.setIcon(QIcon(icons.get('paste.png')))
        self.pasteBic.setIcon(QIcon(icons.get('paste.png')))
        self.pasteNumber.setIcon(QIcon(icons.get('paste.png')))
        self.pasteCode.setIcon(QIcon(icons.get('paste.png')))

    def closeEvent(self, event):
        event.ignore()

    def tabChanged(self, index):
        pass

    def alpha3changed(self, index):
        try:
            data = self.accountAlpha3.currentData()
            self.accountAmount.setPrefix(currency.symbol(data.alpha_3) + ' ')
            self.accountCredit.setPrefix(currency.symbol(data.alpha_3) + ' ')
        except:
            self.accountAmount.setPrefix('')
            self.accountCredit.setPrefix('')

    def eventFilter(self, obj, event):
        if event.type() == QEvent.FocusIn:
            obj.setStyleSheet('')
            try:
                obj.setPlaceholderText('')
            except:
                pass

        if obj == self.accountAmount or obj == self.accountCredit:
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

        return super(OpenAccountDialog, self).eventFilter(obj, event)

    def clipboardChanged(self):
        text = QApplication.clipboard().text()
        text = "".join(text.split()).strip()
        ibanState, ibanText, ibanPos = self.bankIban.validator().validate(
            text.upper(), 0)
        self.pasteIban.setEnabled(ibanState != QValidator.Invalid)
        bicState, bicText, bicPos = self.bankBic.validator().validate(
            text.upper(), 0)
        self.pasteBic.setEnabled(bicState != QValidator.Invalid)
        numState, numText, numPos = self.ccNumber.validator().validate(
            text.upper(), 0)
        self.pasteNumber.setEnabled(numState != QValidator.Invalid)
        cdeState, cdeText, cdePos = self.ccCode.validator().validate(
            text.upper(), 0)
        self.pasteCode.setEnabled(cdeState != QValidator.Invalid)

    def pasteIbanClicked(self):
        text = QApplication.clipboard().text()
        text = "".join(text.split()).strip()
        self.bankIban.setText(text.upper())

    def pasteBicClicked(self):
        text = QApplication.clipboard().text()
        text = "".join(text.split()).strip()
        self.bankBic.setText(text.upper())

    def pasteNumberClicked(self):
        text = QApplication.clipboard().text()
        text = "".join(text.split()).strip()
        self.ccNumber.setText(text.upper())

    def pasteCodeClicked(self):
        text = QApplication.clipboard().text()
        text = "".join(text.split()).strip()
        self.ccCode.setText(text.upper())

    def ccAccountsListCurrentChanged(self, index):
        id = self.ccAccountsList.currentData()
        if id > -1:
            self.accountAmount.setValue(0.0)
            self.accountAmount.setEnabled(False)
            self.accountCredit.setValue(0.0)
            self.accountCredit.setEnabled(False)
        else:
            self.accountAmount.setEnabled(True)
            self.accountCredit.setEnabled(True)

    def validateForm(self):
        errors = {'accountTitle': ''}

        self.accountTitle.setText(self.accountTitle.text().strip())
        if self.accountTitle.text() == '':
            errors['accountTitle'] = funcs.tr(
                "Vous devez renseigner un titre pour votre dossier financier.")
            self.accountTitle.setStyleSheet(
                '#accountTitle { background: #FFDDDD; }')
            self.accountTitle.setPlaceholderText(errors['accountTitle'])
            self.accountTitle.setFocus()
        else:
            self.accountTitle.setStyleSheet('')
            self.accountTitle.setPlaceholderText('')

        message = ''
        for m in errors.values():
            if m.strip() != '':
                message = message + '<br />-  ' + m
        if len(message) > 0:
            message = funcs.tr(
                "<b>Des erreurs se sont produites:</b><br />") + message
            QMessageBox.critical(self, '' + appinfos.app_name + '', message)
            return

        self.act.title = self.accountTitle.text().strip()
        self.act.alpha_3 = self.accountAlpha3.currentData().alpha_3
        self.act.amount = self.accountAmount.value()
        self.act.credit = self.accountCredit.value()

        if type(self.act) is bankaccount:
            self.act.name = self.bankName.text().strip()
            self.act.iban = self.bankIban.text().strip()
            self.act.bic = self.bankBic.text().strip()
            libs.completer.add(self._settings, self.act.name)
            libs.completer.add(self._settings, self.act.bic)
        elif type(self.act) is creditcard:
            self.act.name = self.ccName.text().strip()
            self.act.number = self.ccNumber.text().strip()
            self.act.month = self.ccDate.dateTime().date().month()
            self.act.year = self.ccDate.dateTime().date().year()
            self.act.code = self.ccCode.text().strip()
            self.act.accountid = self.ccAccountsList.currentData() \
                if self.ccAccountsList.currentIndex() > -1 else -1
            libs.completer.add(self._settings, self.act.name)
        elif type(self.act) is wallet:
            self.act.electronic = self.walletElectronic.isChecked()

        self.accept()



