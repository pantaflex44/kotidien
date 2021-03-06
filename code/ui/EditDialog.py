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

import libs.pycountry
import currency

import libs.completer
import resources
import appinfos
import funcs
import icons

import datamodels
from datamodels import *

from ui.OpenAccountDialog import OpenAccountDialog
from ui.SimpleDialog import SimpleDialog
from ui.EditCategoryDialog import EditCategoryDialog


class EditDialog(QDialog):

    _settings = None
    _locale = None

    fi = None

    def __init__(self, settings, locale, parent=None, fi: financial = None, *args, **kwargs):
        self._settings = settings
        self._locale = locale
        dv = tuple(map(lambda v: int(v), list(datamodels.__version__.split('.'))))
        self.fi = fi if isinstance(fi, financial) else financial(version=dv)
        super(EditDialog, self).__init__(parent, Qt.Window |
                                         Qt.WindowTitleHint | Qt.CustomizeWindowHint, *args, **kwargs)
        self._init_ui()
        self.populateAccounts()
        self.populatePaytypes()
        self.populateCategories()

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
        self.setWindowIcon(QIcon(icons.get('account.png')))
        self.editTitle.installEventFilter(self)
        self.editFilepath.installEventFilter(self)
        self.accountsList.installEventFilter(self)
        self.tabView.setTabIcon(1, QIcon(icons.get('account.png')))
        self.tabView.setTabIcon(2, QIcon(icons.get('toolbar-paytype.png')))
        self.tabView.setTabIcon(3, QIcon(icons.get('toolbar-category.png')))
        self.accountAdd.setIcon(QIcon(icons.get('document-add.png')))
        self.accountEdit.setIcon(QIcon(icons.get('document-edit.png')))
        self.accountDelete.setIcon(QIcon(icons.get('document-delete.png')))
        self.paytypeAdd.setIcon(QIcon(icons.get('document-add.png')))
        self.paytypeEdit.setIcon(QIcon(icons.get('document-edit.png')))
        self.paytypeDelete.setIcon(QIcon(icons.get('document-delete.png')))
        self.paytypeRestore.setIcon(QIcon(icons.get('undo.png')))
        self.categoryAdd.setIcon(QIcon(icons.get('document-add.png')))
        self.categoryEdit.setIcon(QIcon(icons.get('document-edit.png')))
        self.categoryDelete.setIcon(QIcon(icons.get('document-delete.png')))
        self.categoryRestore.setIcon(QIcon(icons.get('undo.png')))
        # editTitle
        self.editTitle.setText(self.fi.title)
        # chooseFilepath
        self.chooseFilepath.clicked.connect(self.filepathChooser)
        # editFilepath
        self.editFilepath.setText(self.fi.filepath)
        # editPassword
        self.editPassword.setText(self.fi.password)
        # tabView
        self.tabView.setCurrentIndex(0)
        self.tabView.currentChanged.connect(self.tabChanged)
        # buttonBox
        self.buttonBox.button(
            QDialogButtonBox.Ok).clicked.connect(self.validateForm)
        # accountAdd
        self.accountAddMenu = QMenu(self.accountAdd)
        self.accountAddBank = QAction(QIcon(icons.get('bank.png')),
                                      funcs.tr("Nouveau compte en banque"),
                                      self)
        self.accountAddBank.triggered.connect(lambda: self.openAccount(
            n=True, act=bankaccount(title=funcs.tr("Nouveau compte"))))
        self.accountAddMenu.addAction(self.accountAddBank)
        self.accountAddCard = QAction(QIcon(icons.get('credit-card.png')),
                                      funcs.tr("Nouvelle carte de paiement"),
                                      self)
        self.accountAddCard.triggered.connect(lambda: self.openAccount(
            n=True, act=creditcard(title=funcs.tr("Nouvelle carte de paiement"))))
        self.accountAddMenu.addAction(self.accountAddCard)
        self.accountAddMoney = QAction(QIcon(icons.get('money.png')),
                                       funcs.tr(
                                           "Nouveau portefeuille d'espèces"),
                                       self)
        self.accountAddMoney.triggered.connect(lambda: self.openAccount(
            n=True, act=wallet(title=funcs.tr("Nouveau portefeuille d'espèces"))))
        self.accountAddMenu.addAction(self.accountAddMoney)
        self.accountAdd.setMenu(self.accountAddMenu)
        self.accountAdd.setDefaultAction(self.accountAddBank)
        # accountsList
        self.accountsList.clicked.connect(self.accountsClicked)
        self.accountsList.doubleClicked.connect(self.editAccount)
        self.accountEdit.clicked.connect(self.editAccount)
        self.accountDelete.clicked.connect(self.deleteAccount)
        # paytypesList
        self.paytypesList.clicked.connect(self.paytypesClicked)
        self.paytypesList.doubleClicked.connect(self.editPaytype)
        self.paytypeEdit.clicked.connect(self.editPaytype)
        self.paytypeDelete.clicked.connect(self.deletePaytype)
        self.paytypeRestore.clicked.connect(self.restorePaytype)
        self.paytypeAdd.clicked.connect(
            lambda: self.openPaytype(n=True, pt=''))
        # categoriesList
        self.categoriesList.clicked.connect(self.categoriesClicked)
        self.categoriesList.doubleClicked.connect(self.editCategory)
        self.categoryEdit.clicked.connect(self.editCategory)
        self.categoryDelete.clicked.connect(self.deleteCategory)
        self.categoryRestore.clicked.connect(self.restoreCategory)
        self.categoryAdd.clicked.connect(lambda: self.openCategory(
            n=True, parents=self.fi.categories.keys(), parent='', cat=''))
        # self
        self.editTitle.setFocus()

    def closeEvent(self, event):
        event.ignore()

    def filepathChooser(self):
        self.editFilepath.setText('')
        self.editFilepath.setStyleSheet('')
        self.editFilepath.setPlaceholderText('')
        ofd = QFileDialog(self,
                          funcs.tr("Dossier financier"),
                          os.path.expanduser('~'),
                          appinfos.app_name + ' (*.kot)')
        ofd.setLocale(self.locale())
        ofd.setAcceptDrops(False)
        ofd.setFileMode(QFileDialog.AnyFile)
        ofd.setDefaultSuffix('.kot')
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        ofd.setOptions(options)
        if ofd.exec_():
            files = ofd.selectedFiles()
            if len(files) > 0:
                if os.path.exists(files[0]):
                    reply = QMessageBox.question(self, '' + appinfos.app_name + '',
                                                 funcs.tr(
                                                     "<b>Ce fichier existe déja!</b><br /><br />Voulez-vous l'utiliser malgré tout?"),
                                                 QMessageBox.Yes, QMessageBox.No)
                    if reply == QMessageBox.No:
                        self.filepathChooser()
                        return

                self.fi.filepath = files[0]
                self.editFilepath.setText(files[0])
                self.editPassword.setFocus()

    def populateAccounts(self, selectedidx=None):
        self.accountsList.setModel(None)
        m = QStandardItemModel()
        m.setColumnCount(3)
        m.setHeaderData(0, QtCore.Qt.Horizontal, funcs.tr("Titre"))
        m.setHeaderData(1, QtCore.Qt.Horizontal, funcs.tr("Dénomination"))
        m.setHeaderData(2, QtCore.Qt.Horizontal, funcs.tr("Devise"))
        # m.horizontalHeaderItem(2).setTextAlignment(Qt.AlignRight)
        ba = QStandardItem()
        ba.setText(funcs.tr("Comptes en banque"))
        ba.setIcon(self.accountAddBank.icon())
        ba.setEditable(False)
        ba.setData(None)
        cc = QStandardItem()
        cc.setText(funcs.tr("Cartes de paiement"))
        cc.setIcon(self.accountAddCard.icon())
        cc.setEditable(False)
        cc.setData(None)
        wl = QStandardItem()
        wl.setText(funcs.tr("Portefeuille d'espèces"))
        wl.setIcon(self.accountAddMoney.icon())
        wl.setEditable(False)
        wl.setData(None)
        bacnt = 0
        cccnt = 0
        wlcnt = 0
        for a in self.fi.accounts:
            t = a.title
            nm = QStandardItem()
            nm.setText(t)
            nm.setEditable(False)
            nm.setData(a, Qt.UserRole)
            f = nm.font()
            f.setBold(True)
            nm.setFont(f)
            ncstr = a.name.strip() if hasattr(a, 'name') and a.name.strip() != '' else ''
            nc = QStandardItem()
            nc.setText(ncstr)
            nc.setEditable(False)
            nc.setData(ncstr)
            dv = QStandardItem()
            try:
                cn = libs.pycountry.currencies.get(alpha_3=a.alpha_3)
                dv.setText(cn.name)
            except:
                dv.setText('')
            dv.setEditable(False)
            dv.setData(a.alpha_3)
            if type(a) is bankaccount:
                ba.appendRow([nm, nc, dv])
                bacnt = bacnt + 1
            elif type(a) is creditcard:
                cc.appendRow([nm, nc, dv])
                cccnt = cccnt + 1
            elif type(a) is wallet:
                wl.appendRow([nm, nc, dv])
                wlcnt = wlcnt + 1
        ba.setText('{} ({})'.format(ba.text(), str(bacnt)))
        cc.setText('{} ({})'.format(cc.text(), str(cccnt)))
        wl.setText('{} ({})'.format(wl.text(), str(wlcnt)))
        m.appendRow([ba])
        m.appendRow([cc])
        m.appendRow([wl])
        self.accountsList.setModel(m)
        self.accountsList.resizeColumnToContents(1)
        self.accountsList.resizeColumnToContents(2)
        self.accountsList.header().setSectionResizeMode(0, QHeaderView.Stretch)
        self.accountsList.sortByColumn(0, Qt.AscendingOrder)
        self.accountsList.expandAll()
        self.accountEdit.setEnabled(False)
        self.accountDelete.setEnabled(False)
        self.accountsList.selectionModel().selectionChanged.connect(self.accountsSelected)
        if selectedidx is None:
            self.accountsList.setCurrentIndex(
                self.accountsList.model().index(0, 0))
        else:
            self.accountsList.setCurrentIndex(selectedidx)

    def getSelectedAccount(self):
        idx = None
        act = None
        if not(self.accountsList.selectionModel() is None):
            if len(self.accountsList.selectionModel().selectedIndexes()) > 0:
                idx = self.accountsList.selectionModel().selectedIndexes()[0]
                model = idx.model()
                if idx.parent().isValid():
                    parent = idx.parent()
                    act = model.data(model.index(idx.row(), 0, parent),
                                     Qt.UserRole)
                    if not(act is None):
                        if not isinstance(act, account):
                            act = None
                            idx = None
                    else:
                        idx = None
                else:
                    idx = None
        return idx, act

    def accountsClicked(self):
        pass

    def accountsSelected(self, selected, deselected):
        idx, act = self.getSelectedAccount()
        self.accountEdit.setEnabled(not(idx is None) and not(act is None))
        self.accountDelete.setEnabled(not(idx is None) and not(act is None))

    def deleteAccount(self):
        idx, act = self.getSelectedAccount()
        if not(idx is None) and not(act is None):
            reply = QMessageBox.question(self, '' + appinfos.app_name + '',
                                         funcs.tr(
                                             "Etes-vous certain de vouloir supprimer '{}'?"
                                             .format(act.title)),
                                         QMessageBox.Yes, QMessageBox.No)
            if reply == QMessageBox.Yes:
                self.fi.accounts.remove(act)
                self.populateAccounts()
        else:
            self.accountDelete.setEnabled(False)

    def editAccount(self):
        idx, act = self.getSelectedAccount()
        if not(idx is None) and not(act is None):
            self.openAccount(n=False, act=act)
        else:
            self.accountEdit.setEnabled(False)

    def openAccount(self, act: account, n: bool = False):
        oldactType = type(act)
        oldactTitle = act.title
        oad = OpenAccountDialog(self._settings,
                                self._locale,
                                self,
                                act=act,
                                fi=self.fi)
        oad.setWindowTitle(funcs.tr("Nouveau" if n else "Editer"))
        if oad.exec_() == QMessageBox.Accepted:
            if n:
                self.fi.accounts.append(oad.act)
            else:
                for i, a in enumerate(self.fi.accounts):
                    if oldactType == type(a) and oldactTitle == a.title:
                        self.fi.accounts[i] = oad.act
                        break
        oad.destroy()
        self.populateAccounts()

    def populatePaytypes(self, selectedidx=None):
        self.paytypesList.setModel(None)
        m = QStandardItemModel()
        m.setColumnCount(1)
        m.setHeaderData(0, QtCore.Qt.Horizontal, funcs.tr("Dénomination"))
        for p in self.fi.paytypes:
            i = QStandardItem()
            i.setText(funcs.tr(p))
            i.setEditable(False)
            i.setData(p, Qt.UserRole)
            m.appendRow(i)
            libs.completer.add(self._settings, funcs.tr(p).strip())
        self.paytypesList.setModel(m)
        self.paytypesList.header().setSectionResizeMode(0, QHeaderView.Stretch)
        self.paytypesList.sortByColumn(0, Qt.AscendingOrder)
        self.paytypeEdit.setEnabled(False)
        self.paytypeDelete.setEnabled(False)
        self.paytypesList.selectionModel().selectionChanged.connect(self.paytypesSelected)
        if selectedidx is None:
            self.paytypesList.setCurrentIndex(
                self.paytypesList.model().index(0, 0))
        else:
            self.paytypesList.setCurrentIndex(selectedidx)

    def getSelectedPaytype(self):
        idx = None
        pt = ''
        if not(self.paytypesList.selectionModel() is None):
            if len(self.paytypesList.selectionModel().selectedIndexes()) > 0:
                idx = self.paytypesList.selectionModel().selectedIndexes()[0]
                pt = idx.data()
                if not(pt is None):
                    if not isinstance(pt, str):
                        pt = ''
                        idx = None
                else:
                    pt = ''
                    idx = None
        return idx, pt

    def paytypesClicked(self):
        pass

    def paytypesSelected(self, selected, deselected):
        idx, pt = self.getSelectedPaytype()
        self.paytypeEdit.setEnabled(not(idx is None) and pt != '')
        self.paytypeDelete.setEnabled(not(idx is None) and pt != '')

    def deletePaytype(self):
        idx, pt = self.getSelectedPaytype()
        if not(idx is None) and pt != '':
            reply = QMessageBox.question(self, '' + appinfos.app_name + '',
                                         funcs.tr(
                                             "Etes-vous certain de vouloir supprimer '{}'?"
                                             .format(pt)),
                                         QMessageBox.Yes, QMessageBox.No)
            if reply == QMessageBox.Yes:
                self.fi.paytypes.remove(pt)
                if len(self.fi.paytypes) == 0:
                    self.fi.paytypes.append("Expèces")
                self.populatePaytypes()
        else:
            self.paytypeDelete.setEnabled(False)

    def editPaytype(self):
        idx, pt = self.getSelectedPaytype()
        if not(idx is None) and pt != '':
            self.openPaytype(n=False, pt=pt)
        else:
            self.paytypeEdit.setEnabled(False)

    def openPaytype(self, pt: str, n: bool = False):
        oldPt = pt
        opd = SimpleDialog(self._settings,
                           self._locale,
                           self,
                           txt=pt)
        opd.setWindowTitle(funcs.tr("Nouveau" if n else "Editer"))
        if opd.exec_() == QMessageBox.Accepted:
            if opd.txt.strip() != '':
                if n:
                    if not(opd.txt in self.fi.paytypes):
                        self.fi.paytypes.append(opd.txt)
                else:
                    for i, a in enumerate(self.fi.paytypes):
                        if oldPt == a:
                            self.fi.paytypes[i] = opd.txt
                            break
        opd.destroy()
        self.populatePaytypes()

    def restorePaytype(self):
        reply = QMessageBox.question(self, '' + appinfos.app_name + '',
                                     funcs.tr(
                                         "Restaurer la liste des moyens de paiement par défaut?"),
                                     QMessageBox.Yes, QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.fi.paytypes.clear()
            for p in default_paytypes:
                self.fi.paytypes.append(p)
            self.populatePaytypes()

    def populateCategories(self, selectedidx=None):
        self.categoriesList.setModel(None)
        m = QStandardItemModel()
        m.setColumnCount(1)
        m.setHeaderData(0, QtCore.Qt.Horizontal, funcs.tr("Dénomination"))
        cnt = {}
        for k, v in self.fi.categories.items():
            c = QStandardItem()
            c.setText(funcs.tr(k))
            c.setEditable(False)
            c.setData(k, Qt.UserRole)
            f = c.font()
            f.setBold(True)
            c.setFont(f)
            color, html = funcs.text2color(k)
            c.setForeground(
                QBrush(QColor.fromRgb(color[0], color[1], color[2])))
            cnt[k] = 0
            for sc in v:
                s = QStandardItem()
                s.setText(funcs.tr(sc))
                s.setEditable(False)
                s.setData(sc, Qt.UserRole)
                s.setForeground(c.foreground())
                c.appendRow(s)
                libs.completer.add(self._settings, funcs.tr(sc).strip())
                cnt[k] = cnt[k] + 1
            if cnt[k] > 0:
                c.setText('{} ({})'.format(c.text(), str(cnt[k])))
            m.appendRow(c)
        del cnt
        self.categoriesList.setModel(m)
        self.categoriesList.header().setSectionResizeMode(0, QHeaderView.Stretch)
        self.categoriesList.sortByColumn(0, Qt.AscendingOrder)
        self.categoriesList.expandAll()
        self.categoryEdit.setEnabled(False)
        self.categoryDelete.setEnabled(False)
        self.categoriesList.selectionModel().selectionChanged.connect(
            self.categoriesSelected)
        if selectedidx is None:
            self.categoriesList.setCurrentIndex(
                self.categoriesList.model().index(0, 0))
        else:
            self.categoriesList.setCurrentIndex(selectedidx)

    def getSelectedCategory(self):
        idx = None
        cat = ''
        prt = ''
        if not(self.categoriesList.selectionModel() is None):
            if len(self.categoriesList.selectionModel().selectedIndexes()) > 0:
                idx = self.categoriesList.selectionModel().selectedIndexes()[
                    0]
                model = idx.model()
                parent = idx.parent()
                cat = model.data(model.index(idx.row(), 0, parent),
                                 Qt.UserRole)
                prt = str(parent.data(Qt.UserRole)
                          ) if parent.isValid() else ''
                if not(cat is None):
                    if not isinstance(cat, str):
                        cat = ''
                        prt = ''
                        idx = None
                else:
                    prt = ''
                    cat = ''
                    idx = None
        return idx, cat, prt

    def categoriesClicked(self):
        pass

    def categoriesSelected(self, selected, deselected):
        idx, cat, parent = self.getSelectedCategory()
        self.categoryEdit.setEnabled(not(idx is None) and cat != '')
        self.categoryDelete.setEnabled(not(idx is None) and cat != '')

    def deleteCategory(self):
        idx, cat, parent = self.getSelectedCategory()
        if not(idx is None) and cat != '':
            reply = QMessageBox.question(self, '' + appinfos.app_name + '',
                                         funcs.tr(
                                             "Etes-vous certain de vouloir supprimer '{}'?"
                                             .format(cat)),
                                         QMessageBox.Yes, QMessageBox.No)
            if reply == QMessageBox.Yes:
                if not idx.parent().isValid():
                    del self.fi.categories[cat]
                else:
                    model = idx.parent().model()
                    p = idx.parent().data(Qt.UserRole)
                    self.fi.categories[p].remove(cat)
                if len(self.fi.categories.keys()) == 0:
                    self.fi.categories['Dépense'] = []
                    self.fi.categories['Revenu'] = []
                self.populateCategories()
        else:
            self.categoryDelete.setEnabled(False)

    def editCategory(self):
        idx, cat, parent = self.getSelectedCategory()
        if not(idx is None) and cat != '':
            self.openCategory(n=False, parents=self.fi.categories.keys(
            ), parent=parent, cat=cat, selectedidx=idx)
        else:
            self.categoryEdit.setEnabled(False)

    def openCategory(self, cat: str, parent: str = '', parents=[], n: bool = False, selectedidx=None):
        if parent != '' and not(parent in parents):
            self.fi.categories[parent] = []
            parents.append(parent)
        oldParent = parent
        oldCat = cat
        opd = EditCategoryDialog(self._settings,
                                 self._locale,
                                 self,
                                 parents=parents,
                                 parentcat=parent,
                                 cat=cat)
        opd.setWindowTitle(funcs.tr("Nouveau" if n else "Editer"))
        if opd.exec_() == QMessageBox.Accepted:
            if opd.parentcat != oldParent:
                if oldParent != '':
                    self.fi.categories[oldParent].remove(oldCat)
            if opd.parentcat != '':
                if oldCat in self.fi.categories[opd.parentcat]:
                    self.fi.categories[opd.parentcat].remove(oldCat)
                if not(opd.cat in self.fi.categories[opd.parentcat]):
                    self.fi.categories[opd.parentcat].append(opd.cat)
                else:
                    for i, a in enumerate(self.fi.categories[opd.parentcat]):
                        if oldCat == a:
                            self.fi.categories[opd.parentcat][i] = opd.cat
                            break
            else:
                if not(opd.cat in self.fi.categories.keys()):
                    self.fi.categories[opd.cat] = []
        opd.destroy()
        self.populateCategories()

    def restoreCategory(self):
        reply = QMessageBox.question(self, '' + appinfos.app_name + '',
                                     funcs.tr(
                                         "Restaurer la liste des catégories par défaut?"),
                                     QMessageBox.Yes, QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.fi.categories.clear()
            for k, v in default_categories.items():
                self.fi.categories[k] = []
                for c in v:
                    self.fi.categories[k].append(c)
            self.populateCategories()

    def tabChanged(self, index):
        pass

    def eventFilter(self, obj, event):
        if event.type() == QEvent.FocusIn:
            obj.setStyleSheet('')
            try:
                obj.setPlaceholderText('')
            except:
                pass
        return super(EditDialog, self).eventFilter(obj, event)

    def validateForm(self):
        errors = {'editTitle': '', 'editFilepath': '', 'accounts': '', 'paytypes': '',
                  'categories': ''}

        self.editTitle.setText(self.editTitle.text().strip())
        if self.editTitle.text() == '':
            errors['editTitle'] = funcs.tr(
                "Vous devez renseigner un titre pour votre dossier financier.")
            self.editTitle.setStyleSheet(
                '#editTitle { background: #FFDDDD; }')
            self.editTitle.setPlaceholderText(errors['editTitle'])
            self.editTitle.setFocus()
        else:
            self.editTitle.setStyleSheet('')
            self.editTitle.setPlaceholderText('')

        if not os.access(os.path.dirname(self.editFilepath.text()), os.W_OK):
            errors['editFilepath'] = funcs.tr(
                "Vous devez renseigner un chemin accessible en écriture.")
            self.editFilepath.setStyleSheet(
                '#editFilepath { background: #FFDDDD; }')
            self.editFilepath.setText('')
            self.editFilepath.setPlaceholderText(errors['editFilepath'])
        else:
            self.editFilepath.setStyleSheet('')
            self.editFilepath.setPlaceholderText('')

        if len(self.fi.accounts) == 0:
            errors['accounts'] = funcs.tr(
                "Vous devez ajouter au moins un compte à votre portefeuille.")

        if len(self.fi.paytypes) == 0:
            errors['paytypes'] = funcs.tr(
                "Vous devez ajouter au moins un mode de paiement.")

        if len(self.fi.categories) == 0:
            errors['categories'] = funcs.tr(
                "Vous devez ajouter au moins une catégorie.")

        message = ''
        for m in errors.values():
            if m.strip() != '':
                message = message + '<br />-  ' + m
        if len(message) > 0:
            message = funcs.tr(
                "<b>Des erreurs se sont produites:</b><br />") + message
            QMessageBox.critical(self, '' + appinfos.app_name + '', message)
            return

        self.fi.title = self.editTitle.text().strip()
        self.fi.password = self.editPassword.text().strip()

        self.accept()
