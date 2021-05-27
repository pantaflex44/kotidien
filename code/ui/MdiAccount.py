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
import re
import dateutil.relativedelta
from datetime import datetime, timedelta
from operator import itemgetter, attrgetter
import inspect
import gc

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

from ui.MdiFrame import MdiFrame
from ui.OpeEditDialog import OpeEditDialog
from ui.TrfEditDialog import TrfEditDialog


class HTMLDelegate(QStyledItemDelegate):

    def __init__(self, parent, settings, fi: financial, act: account, datas:dict={}):
        super(HTMLDelegate, self).__init__(parent)
        self.pen = QPen(QColor(Qt.lightGray))
        self._fi = fi
        self._act = act
        self._datas = datas
        self._settings = settings
        self._shortDateFormat = self._settings.value('short_date_format')
        self._longDateFormat = self._settings.value('long_date_format')

    def paint(self, painter, option, index):
        options = QStyleOptionViewItem(option)
        self.initStyleOption(options, index)

        style = QApplication.style() if options.widget is None else options.widget.style()

        txt = options.text
        if options.font.bold():
            txt = '<b>' + txt + '</b>'
        icn = options.icon.pixmap(QSize(16, 16))
        options.text = ""

        textRect = style.subElementRect(QStyle.SE_ItemViewItemText, options, options.widget)
        painter.save()

        ctx = QAbstractTextDocumentLayout.PaintContext()
        mouseOver = (option.state & QStyle.State_MouseOver)
        selected = (option.state & QStyle.State_Selected)

        if type(options.widget) == QTreeView:
            isEnabled = True
            if options.widget.objectName() == 'opePlanner':
                statecol = index.siblingAtColumn(5)
                stateitm = options.widget.model().itemFromIndex(statecol)
                isEnabled = stateitm.data(Qt.UserRole)

            itm = options.widget.model().itemFromIndex(index)
            if not(itm is None) and not index.parent().isValid():
                key = itm.data(Qt.UserRole)
                if key in self._datas:
                    datas = self._datas[key]
                    if isinstance(datas, list):
                        txt = ''
                        x = options.rect.left()
                        y = options.rect.top()
                        w = options.rect.width()
                        h = options.rect.height()
                        p = painter.pen()
                        f = painter.font()
                        painter.setPen(QPen(QColor(Qt.darkGray)))
                        rect = options.rect
                        painter.drawText(rect, Qt.AlignLeft | Qt.AlignVCenter, datas[0].strftime(self._longDateFormat).capitalize())
                        s = funcs.tr("{} opération{}").format(str(datas[1]), 's' if datas[1] > 1 else '')
                        s += funcs.tr("    Dépense{}: {}").format('s' if datas[3][0] > 1 else '', libs.currencies.formatCurrency(datas[3][1], self._act.alpha_3))
                        s += funcs.tr("    Revenu{}: {}").format('s' if datas[4][0] > 1 else '', libs.currencies.formatCurrency(datas[4][1], self._act.alpha_3))
                        s += funcs.tr("    Total: {}").format(libs.currencies.formatCurrency(datas[4][1] - datas[3][1], self._act.alpha_3))
                        rect.moveLeft(250)
                        f.setPointSize(f.pointSize() - 2)
                        painter.setFont(f)
                        painter.drawText(rect, Qt.AlignLeft | Qt.AlignVCenter, s)
                        s = funcs.tr("Solde: {}").format(libs.currencies.formatCurrency(datas[2], self._act.alpha_3))
                        painter.setPen(QPen(QColor(self._settings.value('color_positive_amount'))))
                        if datas[2] < 0.0:
                            painter.setPen(QPen(QColor(self._settings.value('color_negative_amount'))))
                        f.setBold(True)
                        f.setPointSize(f.pointSize() + 2)
                        painter.setFont(f)
                        rect.moveLeft(15)
                        painter.drawText(rect, Qt.AlignRight | Qt.AlignVCenter, s)
                        f.setBold(False)
                        f.setPointSize(f.pointSize() - 1)
                        painter.setPen(p)
                        painter.setFont(f)
                        options.rect = QRect(x, y, w, h)

            if not selected and \
               mouseOver and \
               ((index.parent().isValid() and options.widget.objectName() == 'opeList') or \
                options.widget.objectName() != 'opeList'):
                viewportPos = options.widget.viewport().mapFromGlobal(QCursor.pos())
                if viewportPos.x() >= 0 and viewportPos.y() >= 0:
                    color = option.palette.color(QPalette.Active, QPalette.Highlight)
                    color.setAlpha(30)
                    painter.fillRect(option.rect, color)

            if selected:
                txt = re.compile(r'<[^>]+>').sub('', txt)
                ctx.palette.setColor(QPalette.Background, option.palette.color(QPalette.Active, QPalette.Highlight))
                if not isEnabled:
                    ctx.palette.setColor(QPalette.Text, option.palette.color(QPalette.Disabled, QPalette.HighlightedText))
                else:
                    ctx.palette.setColor(QPalette.Text, option.palette.color(QPalette.Active, QPalette.HighlightedText))
            else:
                if not isEnabled:
                    ctx.palette.setColor(QPalette.Text, option.palette.color(QPalette.Disabled, QPalette.HighlightedText))

        style.drawControl(QStyle.CE_ItemViewItem, options, painter)

        doc = QTextDocument()
        doc.setHtml(txt)

        rect = option.rect
        offset_x = rect.x()
        offset_y = rect.y() + ((rect.height() - doc.size().height()) / 2)
        if options.displayAlignment == Qt.AlignCenter:
            offset_x = rect.x() + ((rect.width() + doc.size().width()) / 2)
        elif options.displayAlignment == Qt.AlignRight:
            offset_x = rect.x() + (-(doc.size().width() - rect.width()))
        elif options.displayAlignment == Qt.AlignLeft:
            if index.column() == 2:
                offset_x = offset_x + 20

        point = QPoint(offset_x, offset_y)
        painter.translate(point)
        painter.setClipRect(textRect.translated(-point))
        if not index.parent().isValid():
            if index.row() > 0:
                p = painter.pen()
                painter.setPen(self.pen)
                painter.drawLine(0, 0, rect.width(), 0)
                painter.setPen(p)

        doc.documentLayout().draw(painter, ctx)

        if options.font.strikeOut():
            p = painter.pen()
            painter.setPen(self.pen)
            painter.drawLine(0, (doc.size().height() / 2), rect.width(), (doc.size().height() / 2))
            painter.setPen(p)

        painter.restore()

    def sizeHint(self, option, index):
        size = super(HTMLDelegate, self).sizeHint(option, index)
        options = QStyleOptionViewItem(option)
        self.initStyleOption(options, index)

        doc = QTextDocument()
        doc.setHtml(' ' + options.text + ' ')

        h = doc.size().height()
        if type(options.widget) == QTreeView:
            if options.widget.objectName() == 'opeList':
                itm = options.widget.model().itemFromIndex(index)
                if not(itm is None) and not index.parent().isValid():
                    h += 8

        return QSize(doc.size().width(), h)


class QCalendarWidgetEx(QCalendarWidget):

    groupsdata = {}

    dateClicked = pyqtSignal(date)

    def __init__(self, parent, settings, fi: financial, act: account):
        super(QCalendarWidgetEx, self).__init__(parent)
        self.setObjectName('financialCalendar')
        self._fi = fi
        self._act = act
        self._settings = settings
        self._shortDateFormat = self._settings.value('short_date_format')
        self._longDateFormat = self._settings.value('long_date_format')
        self.setDateEditEnabled(False)
        self.setVerticalHeaderFormat(QCalendarWidget.NoVerticalHeader)
        self.setHorizontalHeaderFormat(QCalendarWidget.LongDayNames)
        self.setSelectionMode(QCalendarWidget.SingleSelection)
        self.setGridVisible(False)
        self.setMouseTracking(False)
        color = QColor(settings.value('palette_Highlight', '#00c5b5'))
        color.setAlpha(30)
        self.setStyleSheet("#financialCalendar QTableView { selection-background-color: " + color.name(QColor.HexArgb) + "; }")


    def paintCell(self, painter, rect, date):
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.save()

        count = 0
        amount = 0.0
        debit = []
        credit = []

        key = str(date.year()).rjust(4, '0') + str(date.month()).rjust(2, '0') + str(date.day()).rjust(2, '0')
        if key in self.groupsdata.keys():
            count = self.groupsdata[key][1]
            amount = self.groupsdata[key][2]
            debit = self.groupsdata[key][3]
            credit = self.groupsdata[key][4]

        t = str(date.day())

        r = QRectF(rect)
        r.moveLeft(r.left() - 7)
        r.moveTop(r.top() + 3)

        f = painter.font()
        initial_fsize = f.pointSize()

        current_month = datetime.now().date().month
        if date.month() != current_month:
            color = self.palette().color(QPalette.Disabled, QPalette.WindowText)
        else:
            color = self.palette().color(QPalette.Active, QPalette.WindowText)

        if date.dayOfWeek() == 6 or date.dayOfWeek() == 7:
            bgcolor = self.palette().color(QPalette.Active, QPalette.Highlight)
            bgcolor.setAlpha(10)
            painter.fillRect(rect, bgcolor)

        if date == datetime.now().date():
            f.setPointSize(initial_fsize + 2)
            f.setBold(True)
            r.moveTop(r.top())

        painter.setPen(QPen(color))

        painter.setFont(f)
        painter.drawText(r, Qt.TextSingleLine | Qt.AlignTop | Qt.AlignRight, t)

        if count > 0:
            f.setPointSize(initial_fsize - 1)
            f.setBold(False)
            painter.setFont(f)
            rr = QRectF(rect)
            x = rr.left()
            y = rr.top()
            rr.moveLeft(x + 6)

            color = self.palette().color(QPalette.Active, QPalette.WindowText)
            painter.setPen(QPen(color))
            rr.moveTop(y + (rr.height() / 3) - 4)
            painter.drawText(rr, Qt.TextSingleLine | Qt.AlignTop | Qt.AlignLeft, "{} opération{}".format(count, "s" if count > 1 else ""))

            color = self.palette().color(QPalette.Disabled, QPalette.WindowText)
            painter.setPen(QPen(color))
            rr.moveTop(y + (rr.height() / 2) - 2)
            painter.setPen(QPen(QColor(self._settings.value('color_negative_amount'))))
            painter.drawText(rr, Qt.TextSingleLine | Qt.AlignTop | Qt.AlignLeft, "⇩ {}".format(libs.currencies.formatCurrency(debit[1], self._act.alpha_3)))
            rr.moveTop(y + (rr.height() / 2) + painter.font().pointSize() + 3)
            painter.setPen(QPen(QColor(self._settings.value('color_positive_amount'))))
            painter.drawText(rr, Qt.TextSingleLine | Qt.AlignTop | Qt.AlignLeft, "⇧ {}".format(libs.currencies.formatCurrency(credit[1], self._act.alpha_3)))

            f.setBold(True)
            painter.setFont(f)
            rr.moveTop(y + 4)
            if amount >= 0:
                painter.setPen(QPen(QColor(self._settings.value('color_positive_amount'))))
            else:
                painter.setPen(QPen(QColor(self._settings.value('color_negative_amount'))))
            painter.drawText(rr, Qt.TextSingleLine | Qt.AlignTop | Qt.AlignLeft, "➲ {}".format(libs.currencies.formatCurrency(amount, self._act.alpha_3)))

        bdcolor = QColor(Qt.lightGray)
        pen = QPen(bdcolor)
        pen.setWidth(1)
        painter.setPen(pen)
        painter.drawLine(rect.left(), rect.top(), rect.left() + rect.width(), rect.top())
        painter.drawLine(rect.left() + rect.width(), rect.top(), rect.left() + rect.width(), rect.top() + 24)

        if date == datetime.now().date():
            bdcolor = self.palette().color(QPalette.Active, QPalette.Highlight)
            painter.setPen(QPen(bdcolor))
            painter.drawRect(rect)

        painter.restore()


    def setDatas(self, groupsdata):
        self.groupsdata = groupsdata
        self.update()


class MdiAccount(MdiFrame):

    _act = None
    _fromact = None

    _populatePlannerFlag = False
    _plannerSelectedFlag = False

    def __init__(self, settings, locale, parent, fi: financial, closable: bool=True, actid=-1, fromactid=-1, *args, **kwargs):
        if actid > -1 and not(fi is None):
            for a in fi.accounts:
                if a.id == actid:
                    self._act = a
                if a.id == fromactid:
                    self._fromact = a
        super(MdiAccount, self).__init__(settings, locale, parent, fi, closable, *args, **kwargs)
        QApplication.processEvents()
        self.populateFilterDate()
        self.populateFilterType()
        self.populateFilterState()
        self.populateFilterThirdparty()
        self.populateFilterCategory()
        self.populatePlannerType()
        self.populatePlannerWeekend()
        QApplication.processEvents()
        self.populateOpeTrf()
        self.plannerAutoPost(save=True)
        self.populatePlannner()


    def _init_ui(self):
        super(MdiAccount, self)._init_ui()
        if not(self._act is None):
            t = self._act.title
            if self._fromact is None:
                n = self._act.name.strip() if hasattr(self._act, 'name') and self._act.name.strip() != '' else ''
            else:
                n = self._fromact.title.strip()
            if n != '':
                t = t + ' (' + n + ')'
            self.setWindowTitle(t)
        else:
            self.setWindowTitle(funcs.tr("Erreur, compte inconnu ou illisible!"))
        self.setWindowIcon(QIcon(icons.get('account.png')))

        self.toolbar = QToolBar(self.parent())
        self.toolbar.setWindowTitle(funcs.tr("Barre de gestion du compte"))
        t = funcs.tr("{} - Dossier {}".format(self.windowTitle(), self._fi.title))
        self.opeListLabel.setText(funcs.tr("Détails des opérations et transferts") + " - " + t)
        self.opeCalendarLabel.setText(funcs.tr("Calendrier des opérations et transferts") + " - " + t)
        self.opePlannerLabel.setText(funcs.tr("Liste des opérations et transferts planifiés") + " - " + t)


        self.setMouseTracking(True)
        self.installEventFilter(self)

        self.opeAdd = QToolButton(self.toolbar)
        self.opeAdd.setText(funcs.tr("Nouvelle opération..."))
        self.opeAdd.setIcon(QIcon(icons.get('document-add.png')))
        self.opeAdd.setIconSize(self.toolbar.iconSize())
        self.opeAdd.setToolTip(funcs.tr("Ajouter une nouvelle opération"))
        self.opeAdd.setStatusTip(self.opeAdd.toolTip())
        self.opeAdd.setEnabled(True)
        self.opeAdd.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.opeAdd.clicked.connect(self.opeAddClicked)
        self.opeAddAction = self.toolbar.addWidget(self.opeAdd)

        self.trfAdd = QToolButton(self.toolbar)
        self.trfAdd.setText(funcs.tr("Nouveau transfert..."))
        self.trfAdd.setIcon(QIcon(icons.get('document-add.png')))
        self.trfAdd.setIconSize(self.toolbar.iconSize())
        self.trfAdd.setToolTip(funcs.tr("Ajouter un nouveau transfert"))
        self.trfAdd.setStatusTip(self.trfAdd.toolTip())
        self.trfAdd.setEnabled(True)
        self.trfAdd.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.trfAdd.clicked.connect(self.trfAddClicked)
        self.trfAddAction = self.toolbar.addWidget(self.trfAdd)

        self.opeEdit = QAction(QIcon(icons.get('document-edit.png')),
            funcs.tr("Editer..."),
            self)
        self.opeEdit.setEnabled(False)
        self.opeEdit.setToolTip(funcs.tr("Modifier l'opération sélectionnée"))
        self.opeEdit.setStatusTip(self.opeEdit.toolTip())
        self.opeEdit.triggered.connect(self.opeTrfEditClicked)
        self.toolbar.addAction(self.opeEdit)

        self.opeDelete = QAction(QIcon(icons.get('document-delete.png')),
            funcs.tr("Supprimer"),
            self)
        self.opeDelete.setEnabled(False)
        self.opeDelete.setToolTip(funcs.tr("Supprimer les opérations sélectionnées"))
        self.opeDelete.setStatusTip(self.opeDelete.toolTip())
        self.opeDelete.triggered.connect(self.opeTrfDeleteClicked)
        self.toolbar.addAction(self.opeDelete)
        self.opeSeparator0 = self.toolbar.addSeparator()

        self.opeCheck = QAction(QIcon(icons.get('ope-check.png')),
            funcs.tr("Rapprocher les opérations sélectionnées"),
            self)
        self.opeCheck.setStatusTip(self.opeCheck.text())
        self.opeCheck.setCheckable(False)
        self.opeCheck.setEnabled(False)
        self.opeCheck.setToolTip(funcs.tr("Modifier l'état de l'opération"))
        self.opeCheck.setStatusTip(self.opeCheck.toolTip())
        self.opeCheck.triggered.connect(self.opeTrfCheckClicked)
        self.toolbar.addAction(self.opeCheck)
        self.opeSeparator1 = self.toolbar.addSeparator()

        self.plannerAddOpe = QToolButton(self.toolbar)
        self.plannerAddOpe.setText(funcs.tr("Nouvelle opération planifiée..."))
        self.plannerAddOpe.setIcon(QIcon(icons.get('document-add.png')))
        self.plannerAddOpe.setIconSize(self.toolbar.iconSize())
        self.plannerAddOpe.setToolTip(funcs.tr("Ajouter une nouvelle opération planifiée"))
        self.plannerAddOpe.setStatusTip(self.plannerAddOpe.toolTip())
        self.plannerAddOpe.setEnabled(True)
        self.plannerAddOpe.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.plannerAddOpe.clicked.connect(self.plannerAddOpeClicked)
        self.plannerAddOpeAction = self.toolbar.addWidget(self.plannerAddOpe)

        self.plannerAddTrf = QToolButton(self.toolbar)
        self.plannerAddTrf.setText(funcs.tr("Nouveau transfert planifié..."))
        self.plannerAddTrf.setIcon(QIcon(icons.get('document-add.png')))
        self.plannerAddTrf.setIconSize(self.toolbar.iconSize())
        self.plannerAddTrf.setToolTip(funcs.tr("Ajouter un nouveau transfert planifié"))
        self.plannerAddTrf.setStatusTip(self.plannerAddTrf.toolTip())
        self.plannerAddTrf.setEnabled(True)
        self.plannerAddTrf.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.plannerAddTrf.clicked.connect(self.plannerAddTrfClicked)
        self.plannerAddTrfAction = self.toolbar.addWidget(self.plannerAddTrf)

        self.plannerEdit = QAction(QIcon(icons.get('document-edit.png')),
            funcs.tr(""),
            self)
        self.plannerEdit.setEnabled(False)
        self.plannerEdit.setToolTip(funcs.tr("Modifier la planification sélectionnée sélectionnée"))
        self.plannerEdit.setStatusTip(self.plannerEdit.toolTip())
        self.plannerEdit.triggered.connect(self.plannerEditClicked)
        self.toolbar.addAction(self.plannerEdit)

        self.plannerDelete = QAction(QIcon(icons.get('document-delete.png')),
            funcs.tr(""),
            self)
        self.plannerDelete.setEnabled(False)
        self.plannerDelete.setToolTip(funcs.tr("Supprimer la planification sélectionnée sélectionnée"))
        self.plannerDelete.setStatusTip(self.plannerDelete.toolTip())
        self.plannerDelete.triggered.connect(self.plannerDeleteClicked)
        self.toolbar.addAction(self.plannerDelete)
        self.opeSeparator2 = self.toolbar.addSeparator()

        self.plannerPost = QToolButton(self.toolbar)
        self.plannerPost.setIcon(QIcon(icons.get('post.png')))
        self.plannerPost.setIconSize(self.toolbar.iconSize())
        self.plannerPost.setText("Poster")
        self.plannerPost.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.plannerPost.setEnabled(True)
        self.plannerPost.setToolTip(funcs.tr("Poster la planification sélectionnée"))
        self.plannerPost.setStatusTip(self.plannerPost.toolTip())
        self.plannerPost.clicked.connect(self.plannerPostClicked)
        self.plannerPostAction = self.toolbar.addWidget(self.plannerPost)
        self.plannerPostAction.setEnabled(False)

        self.plannerPostAll = QToolButton(self.toolbar)
        self.plannerPostAll.setIcon(QIcon(icons.get('autopost.png')))
        self.plannerPostAll.setIconSize(self.toolbar.iconSize())
        self.plannerPostAll.setText("")
        self.plannerPostAll.setEnabled(True)
        self.plannerPostAll.setToolTip(funcs.tr("Mettre à jour et poster les retards"))
        self.plannerPostAll.setStatusTip(self.plannerPostAll.toolTip())
        self.plannerPostAll.clicked.connect(lambda: self.plannerAutoPost(save=False, force=True, refresh=True))
        self.plannerPostAllAction = self.toolbar.addWidget(self.plannerPostAll)

        self.opeSeparator4 = self.toolbar.addSeparator()

        self.calendarToday = QToolButton(self.toolbar)
        self.calendarToday.setText(funcs.tr("Aujourd'hui"))
        self.calendarToday.setIcon(QIcon(icons.get('go-today.png')))
        self.calendarToday.setIconSize(self.toolbar.iconSize())
        self.calendarToday.setToolTip(funcs.tr("Aller à aujourd'hui"))
        self.calendarToday.setStatusTip(self.calendarToday.toolTip())
        self.calendarToday.setEnabled(True)
        self.calendarToday.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.calendarToday.clicked.connect(self.calendarTodayClicked)
        self.calendarTodayAction = self.toolbar.addWidget(self.calendarToday)
        self.opeSeparator3 = self.toolbar.addSeparator()

        # filters
        self.toolbar2 = QToolBar(self.parent())
        self.toolbar2.setWindowTitle(funcs.tr("Barre de gestion des filtres"))

        self.filterAction = QPushButton(self.toolbar2)
        self.filterAction.setObjectName('filterAction')
        self.filterAction.setIcon(QIcon(icons.get('filter.png')))
        self.filterAction.setCheckable(True)
        self._settings.sync()
        default_active = self._settings.value('Accounts/default_filter_active')
        active = self._settings.value('Accounts/' + str(self._act.id) + '_filter_active', default_active)
        self.filterAction.setChecked(active)
        self.filterAction.setMinimumWidth(32)
        self.filterAction.setToolTip(funcs.tr("Activer / Désactiver les filtres pour ce compte"))
        self.filterAction.setStatusTip(self.filterAction.toolTip())
        self.filterAction.setStyleSheet("#filterAction { text-align:center; padding:3px;padding-bottom:4px; }")
        self.filterAction.toggled.connect(self.filterActionToggled)
        self.toolbar2.addWidget(self.filterAction)

        self.filterSep0 = QLabel(self.toolbar2)
        self.filterSep0.setText("  ")
        self.toolbar2.addWidget(self.filterSep0)

        self.filterDate = QComboBox(self.toolbar2)
        self.toolbar2.addWidget(self.filterDate)
        self.filterDateStart = QDateEdit(self.toolbar2)
        self.filterDateStart.setCalendarPopup(True)
        self.filterDateStart.dateChanged.connect(self.filterCustomStartDateChanged)
        self.toolbar2.addWidget(self.filterDateStart)
        self.filterDateEnd = QDateEdit(self.toolbar2)
        self.filterDateEnd.setCalendarPopup(True)
        self.filterDateEnd.dateChanged.connect(self.filterCustomEndDateChanged)
        self.toolbar2.addWidget(self.filterDateEnd)

        self.filterSep1 = QLabel(self.toolbar2)
        self.filterSep1.setText("  ")
        self.toolbar2.addWidget(self.filterSep1)

        self.filterType = QComboBox(self.toolbar2)
        self.toolbar2.addWidget(self.filterType)

        self.filterSep2 = QLabel(self.toolbar2)
        self.filterSep2.setText("  ")
        self.toolbar2.addWidget(self.filterSep2)

        self.filterState = QComboBox(self.toolbar2)
        self.toolbar2.addWidget(self.filterState)

        self.filterSep3 = QLabel(self.toolbar2)
        self.filterSep3.setText("  ")
        self.toolbar2.addWidget(self.filterSep3)

        self.filterThirdparty = QComboBox(self.toolbar2)
        self.toolbar2.addWidget(self.filterThirdparty)

        self.filterSep4 = QLabel(self.toolbar2)
        self.filterSep4.setText("  ")
        self.toolbar2.addWidget(self.filterSep4)

        self.filterCategory = QComboBox(self.toolbar2)
        self.toolbar2.addWidget(self.filterCategory)

        self.filterSep5 = QLabel(self.toolbar2)
        self.filterSep5.setText("  ")
        self.toolbar2.addWidget(self.filterSep5)

        self.filterText = QLineEdit(self.toolbar2)
        self.filterText.setMinimumWidth(150)
        self.filterText.setPlaceholderText(funcs.tr("Dénominations ou commentaires contenant les termes... [appuyer sur Entrée pour valider]"))
        self.filterText.setCompleter(libs.completer.get(self._settings))
        self.filterText.editingFinished.connect(self.populateOpeTrf)
        self.toolbar2.addWidget(self.filterText)
        self.filterTextAction = QPushButton(self.toolbar2)
        self.filterTextAction.setObjectName('filterTextAction')
        self.filterTextAction.setIcon(QIcon(icons.get('search.png')))
        self.filterTextAction.setCheckable(False)
        self.filterTextAction.setMinimumWidth(32)
        self.filterTextAction.setStyleSheet("#filterTextAction { text-align:center; padding:3px;padding-bottom:4px; }")
        self.filterTextAction.clicked.connect(self.populateOpeTrf)
        self.toolbar2.addWidget(self.filterTextAction)

        QApplication.processEvents()

        # tabAccount
        self.tabAccount.setTabIcon(0, QIcon(icons.get('list.png')))
        self.tabAccount.setTabIcon(1, QIcon(icons.get('calendar.png')))
        self.tabAccount.setTabIcon(2, QIcon(icons.get('planner.png')))
        self.tabAccount.tabBar().setExpanding(True)
        self.tabAccount.tabBar().setElideMode(Qt.ElideRight)
        self.tabAccount.currentChanged.connect(self.tabAccountChanged)
        self.tabAccount.setCurrentIndex(0)
        self.tabAccountChanged(0)

        # opeList
        self.opeList.doubleClicked.connect(self.opeTrfEditDoubleClicked)
        self.opeList.header().sortIndicatorChanged.connect(self.opeTrfLayoutChanged)
        self.opeList.installEventFilter(self)
        self.opeList.viewport().setMouseTracking(True)
        self.opeList.viewport().installEventFilter(self)
        self.opeList.setFocus()

        # opePlanner
        self.opePlanner.doubleClicked.connect(self.plannerDoubleClicked)
        self.opePlanner.installEventFilter(self)
        self.opePlanner.viewport().setMouseTracking(True)
        self.opePlanner.viewport().installEventFilter(self)

        self.plannerEdit.setEnabled(False)
        self.plannerDelete.setEnabled(False)
        self.plannerState.setChecked(False)
        self.plannerNumber.setValue(0)
        self.plannerCount.valueChanged.connect(self.plannerCountChanged)
        self.plannerCount.setValue(0)
        self.plannerType.setCurrentIndex(-1)
        self.plannerWeekend.setCurrentIndex(-1)
        self.plannerLastdate.setDate(datetime.now().date())
        self.plannerFrame.setEnabled(False)
        self.plannerNextButton.setEnabled(False)
        self.plannerNextButton.clicked.connect(self.plannerNextButtonClicked)
        self.plannerResetButton.setEnabled(False)
        self.plannerResetButton.clicked.connect(self.plannerResetButtonClicked)

        self.plannerAutopostButton.setIcon(QIcon(icons.get('autopost.png')))

        # opeCalendar
        self.opeCalendar = QCalendarWidgetEx(None, self._settings, self._fi, self._act)
        self.opeCalendar.selectionChanged.connect(self.calendarSelectionChanged)
        self.tabAccountCalendarLayout.insertWidget(0, self.opeCalendar)



    def strikeThrough(self, widget, state):
        f = widget.font()
        f.setStrikeOut(state)
        widget.setFont(f)

    def newdayEmitted(self, dte: date):
        reply = QMessageBox.question(self, '' + appinfos.app_name + '', funcs.tr(
            "Nous voici demain!<br />Désirez-vous mettre à jour les planifications programmées?"),
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.plannerAutoPost(save=True, refresh=True)

    def populateFilterDate(self):
        defaultFilterDate = self._settings.value('default_filter_date')

        self.filterDate.clear()
        model = QStandardItemModel()
        l = [
            [funcs.tr("Toutes les dates"), 'alldates'],
            '-',
            [funcs.tr("Mois en cours"), 'thismonth'],
            [funcs.tr("Trimestre en cours"), 'thistrimester'],
            [funcs.tr("Semestre en cours"), 'thissemester'],
            [funcs.tr("Année en cours"), 'thisyear'],
            '-',
            [funcs.tr("Le mois dernier"), 'previousmonth'],
            [funcs.tr("L'année dernière"), 'previousyear'],
            '-',
            [funcs.tr("30 derniers jours"), 'last30days'],
            [funcs.tr("60 derniers jours"), 'last60days'],
            [funcs.tr("90 derniers jours"), 'last90days'],
            [funcs.tr("12 derniers mois"), 'last12monthes'],
            '-',
            [funcs.tr("Personalisées..."), 'custom']
        ]
        filter_date = self._settings.value('Accounts/' + str(self._act.id) + '_filter_date', defaultFilterDate)

        separators = []
        selectedidx = 0
        selecteddata = ''
        for n in range(len(l)):
            if isinstance(l[n], list):
                a = QStandardItem(l[n][0])
                a.setData(l[n][1], Qt.UserRole)
                a.setBackground(QColor(Qt.white))
                if len(l[n]) >= 3:
                    f = a.font()
                    f.setBold(l[n][2])
                    a.setFont(f)
                if len(l[n]) >= 4:
                    a.setForeground(QColor.fromRgb(l[n][3][0], l[n][3][1], l[n][3][2]))
                model.appendRow(a)
                if l[n][1] == filter_date:
                    selectedidx = n
                    selecteddata = filter_date
            elif l[n] == '-':
                separators.append(n)

        self.filterDate.setModel(model)

        for idx in separators:
            self.filterDate.insertSeparator(idx)

        self.filterDate.setCurrentIndex(selectedidx)
        self.filterDate.currentIndexChanged.connect(self.filterDateChanged)
        self.setFilterDates(selecteddata, refresh=False)
        self.filterDateStart.setEnabled(selecteddata == 'custom')
        self.filterDateEnd.setEnabled(selecteddata == 'custom')


    def filterDateChanged(self, index):
        data = self.filterDate.currentData()
        self._settings.setValue('Accounts/' + str(self._act.id) + '_filter_date', data)
        self._settings.sync()
        self.filterDateStart.setEnabled(data == 'custom')
        self.filterDateEnd.setEnabled(data == 'custom')
        self.setFilterDates(data, refresh=True)


    def filterCustomStartDateChanged(self, date):
        data = self.filterDate.currentData()
        if data == 'custom':
            self._settings.setValue('Accounts/' + str(self._act.id) + '_filter_startdate',
                                    self.filterDateStart.date().toString('yyyy-MM-dd'))
            self._settings.sync()
            self.populateOpeTrf()


    def filterCustomEndDateChanged(self, date):
        data = self.filterDate.currentData()
        if data == 'custom':
            self._settings.setValue('Accounts/' + str(self._act.id) + '_filter_enddate',
                                    self.filterDateEnd.date().toString('yyyy-MM-dd'))
            self._settings.sync()
            self.populateOpeTrf()


    def setFilterDates(self, data, refresh: bool=False):
        s = self.filterDateStart.minimumDate().toPyDate()
        e = self.filterDateEnd.maximumDate().toPyDate()
        now = datetime.now().date()
        if data == 'thismonth':
            s = funcs.first_day_of_month(now)
            e = funcs.last_day_of_month(now)
        elif data == 'thistrimester':
            #s = funcs.first_day_of_month(now - dateutil.relativedelta.relativedelta(months=2))
            m = 1
            if now.month >= 4:
                m = 4
            elif now.month >= 7:
                m = 7
            elif now.month >= 10:
                m = 10
            s = funcs.first_day_of_month(datetime(now.year, m, 1).date())
            e = funcs.last_day_of_month(datetime(now.year, m + 2, 1).date())
        elif data == 'thissemester':
            m = 1
            if now.month >= 7:
                m = 7
            s = funcs.first_day_of_month(datetime(now.year, m, 1).date())
            e = funcs.last_day_of_month(datetime(now.year, m + 5, 1).date())
        elif data == 'thisyear':
            s = funcs.first_day_of_month(datetime(now.year, 1, 1).date())
            e = funcs.last_day_of_month(datetime(now.year, 12, 1).date())
        elif data == 'previousmonth':
            n = now - dateutil.relativedelta.relativedelta(months=1)
            s = funcs.first_day_of_month(n)
            e = funcs.last_day_of_month(n)
        elif data == 'previousyear':
            s = funcs.first_day_of_month(datetime(now.year - 1, 1, 1).date())
            e = funcs.last_day_of_month(datetime(now.year - 1, 12, 1).date())
        elif data == 'last30days':
            s = now - dateutil.relativedelta.relativedelta(days=30)
            e = now
        elif data == 'last60days':
            s = now - dateutil.relativedelta.relativedelta(days=60)
            e = now
        elif data == 'last90days':
            s = now - dateutil.relativedelta.relativedelta(days=90)
            e = now
        elif data == 'last12monthes':
            s = now - dateutil.relativedelta.relativedelta(months=12)
            e = now
        elif data == 'custom':
            filter_sdate = self._settings.value('Accounts/' + str(self._act.id) + '_filter_startdate',
                                                self.filterDateStart.minimumDate().toString("yyyy-MM-dd"))
            filter_edate = self._settings.value('Accounts/' + str(self._act.id) + '_filter_enddate',
                                                self.filterDateEnd.maximumDate().toString("yyyy-MM-dd"))
            s = datetime.strptime(filter_sdate, '%Y-%m-%d').date()
            e = datetime.strptime(filter_edate, '%Y-%m-%d').date()

        self.filterDateStart.setDate(s)
        self.filterDateEnd.setDate(e)
        if refresh:
            self.populateOpeTrf()


    def populateFilterType(self):
        self.filterType.clear()
        model = QStandardItemModel()
        l = [
            [funcs.tr("Tous les types"), 'alltypes'],
            '-',
            [funcs.tr("Dépenses"), 'debits'],
            [funcs.tr("Revenus"), 'credits'],
            '-'
        ]
        for pt in sorted(self._fi.paytypes):
            l.append([funcs.tr(pt), pt])

        filter_type = self._settings.value('Accounts/' + str(self._act.id) + '_filter_type', 'alltypes')

        separators = []
        selectedidx = 0
        for n in range(len(l)):
            if isinstance(l[n], list):
                a = QStandardItem(l[n][0])
                a.setData(l[n][1], Qt.UserRole)
                a.setBackground(QColor(Qt.white))
                if len(l[n]) >= 3:
                    f = a.font()
                    f.setBold(l[n][2])
                    a.setFont(f)
                if len(l[n]) >= 4:
                    a.setForeground(QColor.fromRgb(l[n][3][0], l[n][3][1], l[n][3][2]))
                model.appendRow(a)
                if l[n][1] == filter_type:
                    selectedidx = n
            elif l[n] == '-':
                separators.append(n)

        self.filterType.setModel(model)

        for idx in separators:
            self.filterType.insertSeparator(idx)

        self.filterType.setCurrentIndex(selectedidx)
        self.filterType.currentIndexChanged.connect(self.filterTypeChanged)


    def filterTypeChanged(self, index):
        data = self.filterType.currentData()
        self._settings.setValue('Accounts/' + str(self._act.id) + '_filter_type', data)
        self._settings.sync()
        self.populateOpeTrf()


    def populateFilterState(self):
        hide_pointed = self._settings.value('Accounts/default_filter_hide_pointed')

        self.filterState.clear()
        model = QStandardItemModel()
        l = [
            [funcs.tr("Tous les états"), 'allstates'],
            '-',
            [funcs.tr("Non pointés"), 'notpointed'],
            [funcs.tr("Pointés"), 'pointed'],
        ]
        filter_state = self._settings.value('Accounts/' + str(self._act.id) + '_filter_state', 'notpointed' if hide_pointed else 'allstates')

        separators = []
        selectedidx = 0
        for n in range(len(l)):
            if isinstance(l[n], list):
                a = QStandardItem(l[n][0])
                a.setData(l[n][1], Qt.UserRole)
                a.setBackground(QColor(Qt.white))
                if len(l[n]) >= 3:
                    f = a.font()
                    f.setBold(l[n][2])
                    a.setFont(f)
                if len(l[n]) >= 4:
                    a.setForeground(QColor.fromRgb(l[n][3][0], l[n][3][1], l[n][3][2]))
                model.appendRow(a)
                if l[n][1] == filter_state:
                    selectedidx = n
            elif l[n] == '-':
                separators.append(n)

        self.filterState.setModel(model)

        for idx in separators:
            self.filterState.insertSeparator(idx)

        self.filterState.setCurrentIndex(selectedidx)
        self.filterState.currentIndexChanged.connect(self.filterStateChanged)


    def filterStateChanged(self, index):
        data = self.filterState.currentData()
        self._settings.setValue('Accounts/' + str(self._act.id) + '_filter_state', data)
        self._settings.sync()
        self.populateOpeTrf()


    def populateFilterThirdparty(self):
        self.filterThirdparty.clear()
        model = QStandardItemModel()
        l = [
            [funcs.tr("Tous les tiers"), 'allthirdparties'],
            '-'
        ]
        for tp in self._fi.thirdparties:
            l.append([funcs.tr(tp.title), tp.title])
        filter_tp = self._settings.value('Accounts/' + str(self._act.id) + '_filter_thirdparty', 'allthirdparties')

        separators = []
        selectedidx = 0
        for n in range(len(l)):
            if isinstance(l[n], list):
                a = QStandardItem(l[n][0])
                a.setData(l[n][1], Qt.UserRole)
                a.setBackground(QColor(Qt.white))
                if len(l[n]) >= 3:
                    f = a.font()
                    f.setBold(l[n][2])
                    a.setFont(f)
                if len(l[n]) >= 4:
                    a.setForeground(QColor.fromRgb(l[n][3][0], l[n][3][1], l[n][3][2]))
                model.appendRow(a)
                if l[n][1] == filter_tp:
                    selectedidx = n
            elif l[n] == '-':
                separators.append(n)

        self.filterThirdparty.setModel(model)

        for idx in separators:
            self.filterThirdparty.insertSeparator(idx)

        self.filterThirdparty.setCurrentIndex(selectedidx)
        self.filterThirdparty.currentIndexChanged.connect(self.filterThirdpartyChanged)


    def filterThirdpartyChanged(self, index):
        data = self.filterThirdparty.currentData()
        self._settings.setValue('Accounts/' + str(self._act.id) + '_filter_thirdparty', data)
        self._settings.sync()
        self.populateOpeTrf()


    def populateFilterCategory(self):
        self.filterCategory.clear()
        model = QStandardItemModel()
        l = [
            [funcs.tr("Toutes les catégories"), 'allcategories'],
            '-'
        ]
        for k,v in self._fi.categories.items():
            t = funcs.tr(k)
            color, html = funcs.text2color(t)
            l.append([t, t, True, color])
            if isinstance(v, list):
                for c in sorted(v):
                    l.append(['    ' + c, t + ': ' + c, False, color])
        filter_cat = self._settings.value('Accounts/' + str(self._act.id) + '_filter_category', 'allcategories')

        separators = []
        selectedidx = 0
        for n in range(len(l)):
            if isinstance(l[n], list):
                a = QStandardItem(l[n][0])
                a.setData(l[n][1], Qt.UserRole)
                a.setBackground(QColor(Qt.white))
                if len(l[n]) >= 3:
                    f = a.font()
                    f.setBold(l[n][2])
                    a.setFont(f)
                if len(l[n]) >= 4:
                    a.setForeground(QColor.fromRgb(l[n][3][0], l[n][3][1], l[n][3][2]))
                model.appendRow(a)
                if l[n][1] == filter_cat:
                    selectedidx = n
            elif l[n] == '-':
                separators.append(n)

        self.filterCategory.setModel(model)

        for idx in separators:
            self.filterCategory.insertSeparator(idx)

        self.filterCategory.setCurrentIndex(selectedidx)
        self.filterCategory.currentIndexChanged.connect(self.filterCategoryChanged)


    def filterCategoryChanged(self, index):
        data = self.filterCategory.currentData()
        self._settings.setValue('Accounts/' + str(self._act.id) + '_filter_category', data)
        self._settings.sync()
        self.populateOpeTrf()


    def applyFilterOpe(self, ope: operation):
        if not self.filterAction.isChecked():
            return True

        f_start_date = self.filterDateStart.date().toPyDate()
        f_end_date = self.filterDateEnd.date().toPyDate()

        f_type_data = self.filterType.currentData()
        f_type = (lambda a, t: True)
        if f_type_data == 'debits':
            f_type = (lambda a, t: a < 0)
        elif f_type_data == 'credits':
            f_type = (lambda a, t: a >= 0)
        elif f_type_data in self._fi.paytypes:
            f_type = (lambda a, t: t == f_type_data)

        f_state_data = self.filterState.currentData()
        f_state = (lambda s: True)
        if f_state_data == 'pointed':
            f_state = (lambda s: s == True)
        elif f_state_data == 'notpointed':
            f_state = (lambda s: s == False)

        f_tp_data = self.filterThirdparty.currentData()
        f_tp = (lambda t: True)
        tps = [tp.title for tp in self._fi.thirdparties]
        if f_tp_data in tps:
            f_tp = (lambda t: t == f_tp_data)

        f_cat_data = self.filterCategory.currentData()
        f_cat_data_parent = f_cat_data.split(':')[0].strip()
        f_hassub = len(f_cat_data.split(':')) > 1
        f_cat = (lambda t: True)
        cats = []
        for k,v in self._fi._categories.items():
            cats.append(k)
            if isinstance(v, list):
                for c in v:
                    cats.append(k + ': ' + c)
        if f_hassub and f_cat_data in cats:
            f_cat = (lambda c: c == f_cat_data)
        if not f_hassub and f_cat_data_parent in cats:
            f_cat = (lambda c: c.startswith(f_cat_data_parent))

        f_text_data = self.filterText.text().strip()
        f_text = (lambda s: True)
        if f_text_data != '':
            f_text = (lambda s: (s.strip() != '') and not(re.search(s, f_text_data, re.IGNORECASE) is None))

        result = True
        result = result and (ope.fromdate >= f_start_date and ope.fromdate <= f_end_date)
        result = result and f_type(ope.amount, ope.paytype)
        result = result and f_state(ope.state)
        result = result and f_tp(ope.to)
        result = result and f_cat(ope.category)
        result = result and (f_text(ope.title) or f_text(ope.comment))
        return result


    def applyFilterTrf(self, trf: transfer):
        if not self.filterAction.isChecked():
            return True

        f_start_date = self.filterDateStart.date().toPyDate()
        f_end_date = self.filterDateEnd.date().toPyDate()

        f_type_data = self.filterType.currentData()
        f_type = (lambda: True)
        if f_type_data == 'debits':
            f_type = (lambda: self._act.id == trf.fromactid)
        elif f_type_data == 'credits':
            f_type = (lambda: self._act.id == trf.toactid)
        else:
            f_type = (lambda: f_type_data == "Transfert" or f_type_data == 'alltypes')

        f_state_data = self.filterState.currentData()
        f_state = (lambda s: True)
        if f_state_data == 'pointed':
            f_state = (lambda s: s == True)
        elif f_state_data == 'notpointed':
            f_state = (lambda s: s == False)

        f_text_data = self.filterText.text().strip()
        f_text = (lambda s: True)
        if f_text_data != '':
            f_text = (lambda s: (s.strip() != '') and not(re.search(s, f_text_data, re.IGNORECASE) is None))

        f_cat_data = self.filterCategory.currentData()
        f_cat = (lambda : f_cat_data == 'allcategories')

        f_tp_data = self.filterThirdparty.currentData()
        f_tp = (lambda : f_tp_data == 'allthirdparties')

        result = True
        result = result and f_cat()
        result = result and f_tp()
        result = result and f_type()
        result = result and (trf.fromdate >= f_start_date and trf.fromdate <= f_end_date)
        result = result and f_state(trf.state)
        result = result and (f_text(trf.title) or f_text(trf.comment))
        return result


    def filterActionToggled(self, checked):
        active = self.filterAction.isChecked()
        self._settings.setValue('Accounts/' + str(self._act.id) + '_filter_active', active)
        self._settings.sync()
        self.populateOpeTrf()


    def eventFilter(self, obj, event):
        if obj == self.opeList:
            if event.type() == QEvent.KeyPress:
                if event.modifiers() != Qt.ControlModifier and event.key() == Qt.Key_Return:
                    self.opeTrfEditClicked()
                elif event.modifiers() == Qt.ControlModifier and event.key() == Qt.Key_O:
                    self.opeAddClicked()
                elif event.modifiers() == Qt.ControlModifier and event.key() == Qt.Key_T:
                    self.trfAddClicked()
                elif event.key() == Qt.Key_Delete:
                    self.opeTrfDeleteClicked()
                elif event.modifiers() == Qt.ControlModifier and event.key() == Qt.Key_Return:
                    self.opeTrfCheckClicked()

        return super(MdiAccount, self).eventFilter(obj, event)


    def makeOpeItem(self, ope: operation):
        state = QStandardItem()
        state.setText('')
        if ope.state:
            state.setIcon(QIcon(icons.get('ope-check.png')))
        state.setEditable(False)
        state.setData(ope.state, Qt.UserRole)
        state.setTextAlignment(Qt.AlignCenter)

        fromdate = QStandardItem()
        fromdate.setText(ope.fromdate.strftime(self._shortDateFormat))
        fromdate.setEditable(False)
        fromdate.setData(ope.fromdate, Qt.UserRole)
        fromdate.setTextAlignment(Qt.AlignLeft)

        id = QStandardItem()
        id.setEditable(False)
        id.setEnabled(True)
        id.setText("")
        id.setIcon(QIcon(icons.get('alloperation.png')))
        id.setData(ope, Qt.UserRole)
        id.setTextAlignment(Qt.AlignCenter)

        to = QStandardItem()
        to.setText(ope.to)
        to.setEditable(False)
        to.setData(ope.to, Qt.UserRole)
        f = to.font()
        #f.setBold(not ope.state)
        to.setFont(f)

        title = QStandardItem()
        txt = ope.title
        title.setText(txt)
        title.setEditable(False)
        title.setData(ope.title, Qt.UserRole)

        comment = QStandardItem()
        txt = ope.comment
        comment.setText(txt)
        comment.setEditable(False)
        comment.setData(ope.comment, Qt.UserRole)

        paytype = QStandardItem()
        paytype.setText(funcs.tr(ope.paytype))
        paytype.setEditable(False)
        paytype.setData(ope.paytype, Qt.UserRole)

        amount = QStandardItem()
        color = self._settings.value('color_positive_amount')
        if ope.amount < 0.0:
            color = self._settings.value('color_negative_amount')
        amount.setText('<span style="color: {};">{}</span>'.format(
            color,
            libs.currencies.formatCurrency(ope.amount, self._act.alpha_3)))
        amount.setEditable(False)
        amount.setData(ope.amount, Qt.UserRole)
        amount.setTextAlignment(Qt.AlignRight)

        prt = ''
        cat = ope.category.split(':')
        if len(cat) > 1:
            prt = cat[0].strip()
            cat.pop(0)
            cat = (':'.join(cat)).strip()
        if prt == '':
            prt = cat
            cat = ''
        color, html = funcs.text2color(funcs.tr(prt))
        category = QStandardItem()
        color = 'rgb(' + str(color[0]) + ', ' + str(color[1]) + ', ' + str(color[2]) + ')'
        category.setText('<div style="background: {}; color: #fff; font-weight: bold;"><small>&nbsp;{}&nbsp;</small></div>'.format(
            color,
            funcs.tr(ope.category)))
        category.setEditable(False)
        category.setData(ope.category, Qt.UserRole)

        return id, state, fromdate, to, title, comment, paytype, amount, category


    def addOpe(self, ope: operation):
        self._act.operations.append(ope)


    def editOpe(self, ope: operation):
        ot = next((o for o in self._act.operations if o.id == ope.id), None)
        if not(ot is None):
            ot.title = ope.title
            ot.fromdate = ope.fromdate
            ot.amount = ope.amount
            ot.comment = ope.comment
            ot.to = ope.to
            ot.paytype = ope.paytype
            ot.category = ope.category
            ot.state = ope.state


    def makeTrfItem(self, trf: transfer):
        fa = None
        ta = None
        for a in self._fi.accounts:
            if trf.fromactid == a.id:
                fa = a
            if trf.toactid == a.id:
                ta = a

        state = QStandardItem()
        state.setText('')
        if trf.state:
            state.setIcon(QIcon(icons.get('ope-check.png')))
        state.setEditable(False)
        state.setData(trf.state, Qt.UserRole)
        state.setTextAlignment(Qt.AlignCenter)

        fromdate = QStandardItem()
        fromdate.setText(trf.fromdate.strftime(self._shortDateFormat))
        fromdate.setEditable(False)
        fromdate.setData(trf.fromdate, Qt.UserRole)
        fromdate.setTextAlignment(Qt.AlignRight)

        id = QStandardItem()
        id.setEditable(False)
        id.setEnabled(True)
        id.setText("")
        id.setIcon(QIcon(icons.get('transfer.png')))
        id.setData(trf, Qt.UserRole)
        id.setTextAlignment(Qt.AlignCenter)

        amt = trf.amount
        to = QStandardItem()
        to.setEditable(False)
        f = to.font()
        #f.setBold(not trf.state)
        to.setFont(f)
        if (trf.fromactid == self._act.id) and not(ta is None):
            to.setText(funcs.tr(
                "Vers <i>{}</i>").format(ta.title))
            to.setData(ta, Qt.UserRole)
            amt = -amt
        elif (trf.toactid == self._act.id) and not(fa is None):
            to.setText(funcs.tr(
                "Depuis <i>{}</i>").format(fa.title))
            to.setData(fa, Qt.UserRole)
        else:
            to = None
            amt = 0.0
        title = QStandardItem()
        title.setText(trf.title)
        title.setEditable(False)
        title.setData(trf.title, Qt.UserRole)

        comment = QStandardItem()
        comment.setText(trf.comment)
        comment.setEditable(False)
        comment.setData(trf.comment, Qt.UserRole)

        amount = QStandardItem()
        color = self._settings.value('color_positive_amount')
        if amt < 0.0:
            color = self._settings.value('color_negative_amount')
        amount.setText('<span style="color: {};">{}</span>'.format(
            color,
            libs.currencies.formatCurrency(amt, self._act.alpha_3)))
        amount.setEditable(False)
        amount.setData(amt, Qt.UserRole)
        amount.setTextAlignment(Qt.AlignRight)

        paytype = QStandardItem()
        paytype.setText(funcs.tr("Transfert"))
        paytype.setEditable(False)
        paytype.setData("Transfert", Qt.UserRole)

        return id, state, fromdate, to, title, comment, paytype, amount


    def addTrf(self, trf: transfer):
        self._fi.transfers.append(trf)


    def editTrf(self, trf: transfer):
        ot = next((t for t in self._fi.transfers if t.id == trf.id), None)
        if not(ot is None):
            ot.title = trf.title
            ot.fromdate = trf.fromdate
            ot.amount = trf.amount
            ot.comment = trf.comment
            ot.fromactid = trf.fromactid
            ot.toactid = trf.toactid
            ot.state = trf.state


    def makeOpeTrfGroup(self, dte: date, groups: dict = {}):
        y = dte.year
        m = dte.month
        d = dte.day
        key = str(y).rjust(4, '0') + str(m).rjust(2, '0') + str(d).rjust(2, '0')
        if not(key in groups.keys()):
            total = self._fi.amount_atdate(self._act.id, dte)
            groups[key] = QStandardItem()
            groups[key].setEditable(False)
            groups[key].setData(key, Qt.UserRole)
            groups[key].setText('')
            groups[key].setEnabled(False)
            groups[key].setFlags(groups[key].flags() & ~Qt.ItemIsSelectable)
            self.groupsdata[key] = [dte, 0, total, [0, 0.0], [0, 0.0]]
        self.groupsdata[key][1] = groups[key].rowCount() + 1
        return groups, key


    def populateOpeTrf(self, lastselected: bool = False):
        QApplication.setOverrideCursor(Qt.WaitCursor)
        self.setUpdatesEnabled(False)

        lastselectedidx = []
        lastselecteddata = []
        if not(self.opeList.selectionModel() is None):
            if len(self.opeList.selectionModel().selectedIndexes()) > 0:
                for idx in self.opeList.selectionModel().selectedIndexes():
                    idxcol = idx.siblingAtColumn(1)
                    data = self.opeList.model().itemFromIndex(idxcol).data(Qt.UserRole)
                    lastselectedidx.append(idx)
                    lastselecteddata.append(data)
            self.opeList.selectionModel().clearSelection()

        self.opeList.setModel(None)
        self.model = None
        self.model = QStandardItemModel()
        self.model.setColumnCount(9)
        self.model.setHeaderData(0, QtCore.Qt.Horizontal, funcs.tr("Date"))
        self.model.setHeaderData(1, QtCore.Qt.Horizontal, funcs.tr(""))
        self.model.horizontalHeaderItem(1).setTextAlignment(Qt.AlignCenter)
        self.model.setHeaderData(2, QtCore.Qt.Horizontal, funcs.tr(""))
        self.model.horizontalHeaderItem(2).setTextAlignment(Qt.AlignCenter)
        self.model.setHeaderData(3, QtCore.Qt.Horizontal, funcs.tr("Tiers"))
        self.model.setHeaderData(4, QtCore.Qt.Horizontal, funcs.tr("Dénomination"))
        self.model.setHeaderData(5, QtCore.Qt.Horizontal, funcs.tr("Commentaire"))
        self.model.setHeaderData(6, QtCore.Qt.Horizontal, funcs.tr("Type"))
        self.model.setHeaderData(7, QtCore.Qt.Horizontal, funcs.tr("Catégorie"))
        self.model.setHeaderData(8, QtCore.Qt.Horizontal, funcs.tr("Montant"))
        self.model.horizontalHeaderItem(8).setTextAlignment(Qt.AlignRight)

        self.groupsdata = {}
        groups = {}

        QApplication.processEvents()

        # operations
        for ope in self._act.operations:
            if self.applyFilterOpe(ope):
                id, state, fromdate, to, title, comment, paytype, amount, category = self.makeOpeItem(ope)
                fromdate.setText('')
                groups, key = self.makeOpeTrfGroup(ope.fromdate, groups)
                groups[key].appendRow([fromdate, id, state, to, title, comment, paytype, category, amount])
                if ope.amount < 0:
                    self.groupsdata[key][3][0] += 1
                    self.groupsdata[key][3][1] += abs(ope.amount)
                else:
                    self.groupsdata[key][4][0] += 1
                    self.groupsdata[key][4][1] += abs(ope.amount)

        QApplication.processEvents()

        # transfers
        for trf in self._fi.transfers:
            if self.applyFilterTrf(trf):
                id, state, fromdate, to, title, comment, paytype, amount = self.makeTrfItem(trf)
                fromdate.setText('')
                if to is None:
                    continue
                groups, key = self.makeOpeTrfGroup(trf.fromdate, groups)
                e = QStandardItem()
                e.setEditable(False)
                e.setEnabled(False)
                groups[key].appendRow([fromdate, id, state, to, title, comment, paytype, e, amount])
                if amount.data(Qt.UserRole) < 0:
                    self.groupsdata[key][3][0] += 1
                    self.groupsdata[key][3][1] += abs(amount.data(Qt.UserRole))
                else:
                    self.groupsdata[key][4][0] += 1
                    self.groupsdata[key][4][1] += abs(amount.data(Qt.UserRole))

        QApplication.processEvents()

        # sort ascending
        groups = {key: group for key, group in sorted(groups.items(), key=itemgetter(0), reverse=True)}

        for key, group in groups.items():
            t = group.text()
            t = t.replace('##', funcs.tr("{} opération{}").format(
                str(group.rowCount()),
                's' if group.rowCount() > 1 else ''))
            group.setText(t)
            self.model.appendRow([group])

        QApplication.processEvents()

        self.opeList.setModel(self.model)
        self.opeList.setItemDelegate(HTMLDelegate(parent=None, settings=self._settings, fi=self._fi, act=self._act, datas=self.groupsdata))
        self.opeList.header().setMinimumSectionSize(1)
        self.opeList.header().setMinimumSectionSize(2)
        self.opeList.header().resizeSection(0, 50)
        self.opeList.header().resizeSection(1, 20)
        self.opeList.header().resizeSection(2, 20)
        self.opeList.header().resizeSection(3, 200)
        self.opeList.header().setSectionResizeMode(3, QHeaderView.Stretch)
        self.opeList.header().resizeSection(4, 150)
        self.opeList.header().resizeSection(5, 150)
        self.opeList.header().resizeSection(6, 150)
        self.opeList.header().resizeSection(7, 150)
        self.opeList.header().resizeSection(8, 100)

        self.opeList.model().setSortRole(Qt.UserRole)
        default_sort_column = int(self._settings.value('Accounts/default_sort_column'))
        default_sort_order = self._settings.value('Accounts/default_sort_descending')
        sort_column = int(self._settings.value('Accounts/' + str(self._act.id) + '_sort_column', default_sort_column))
        sort_order = Qt.DescendingOrder if self._settings.value('Accounts/' + str(self._act.id) + '_sort_descending', default_sort_order) else Qt.AscendingOrder
        self.opeList.sortByColumn(sort_column, sort_order)
        self.opeList.model().sort(sort_column, sort_order)

        last = {'idx': None, 'itm': None, 'dte': datetime(1970, 1, 1).date()}
        expanded = []
        selective_expand = self._settings.value('selective_expand')
        for i in range(self.opeList.model().rowCount()):
            self.opeList.setFirstColumnSpanned(i, QModelIndex(), True)
            idx = self.opeList.model().index(i, 0)
            itm = self.opeList.model().itemFromIndex(idx)
            for j in range(itm.rowCount()):
                substate = itm.child(j, 2)
                subdate = itm.child(j, 0)
                subid = itm.child(j, 1)
                dta = substate.data(Qt.UserRole)
                dte = subdate.data(Qt.UserRole)
                did = subid.data(Qt.UserRole)
                if dte > last['dte'] and dte <= datetime.now().date():
                    last = {'idx': idx, 'itm': itm, 'dte': dte}
                if selective_expand:
                    if dta == False and dte <= datetime.now().date() and not(idx in expanded):
                        self.opeList.expand(idx)
                        expanded.append(idx)
                if lastselected and len(lastselectedidx) > 0 and did in lastselecteddata:
                    self.opeList.selectionModel().select(
                        self.opeList.model().index(j, 0, itm.index()),
                        QItemSelectionModel.Rows | QItemSelectionModel.Select)
        if not selective_expand:
            self.opeList.expandAll()

        if not(last['itm'] is None):
            self.opeList.setCurrentIndex(last['itm'].index())
            self.opeList.expand(last['itm'].index())
            self.opeList.scrollTo(last['itm'].index(), QAbstractItemView.PositionAtTop)

        self.opeList.selectionModel().selectionChanged.connect(self.opeTrfListSelected)

        QApplication.processEvents()

        self.opeCalendar.setDatas(self.groupsdata)

        self.setUpdatesEnabled(True)
        QApplication.restoreOverrideCursor()


    def opeTrfListSelected(self, new, old):
        scnt = len(self.opeList.selectionModel().selectedRows())
        self.opeEdit.setEnabled(scnt == 1)
        self.opeDelete.setEnabled(scnt >= 1)
        self.opeCheck.setEnabled(scnt >= 1)
        if scnt > 0:
            lastrow = self.opeList.selectionModel().selectedRows()[scnt - 1]
            dte = lastrow.data(Qt.UserRole)
            if isinstance(dte, date):
                self.opeCalendar.selectionChanged.disconnect(self.calendarSelectionChanged)
                self.opeCalendar.setSelectedDate(dte)
                self.opeCalendar.selectionChanged.connect(self.calendarSelectionChanged)


    def opeTrfLayoutChanged(self, column, order):
        self._settings.setValue('Accounts/' + str(self._act.id) + '_sort_column', column)
        self._settings.setValue('Accounts/' + str(self._act.id) + '_sort_descending', (order == Qt.DescendingOrder))
        self._settings.sync()


    def opeAddValidated(self, ope: operation):
        self.addOpe(ope)
        self.updated.emit()
        self.populateOpeTrf(lastselected=True)


    def opeEditValidated(self, ope: operation):
        self.editOpe(ope)
        self.updated.emit()
        self.populateOpeTrf(lastselected=True)


    def opeAddClicked(self):
        oed = OpeEditDialog(self._settings,
                            self._locale,
                            self,
                            self._fi,
                            self._act)
        oed.added.connect(lambda: self.opeAddValidated(oed.ope))
        if oed.exec_() == QMessageBox.Accepted:
            self.opeAddValidated(oed.ope)
        oed.destroy()


    def trfAddValidated(self, trf: transfer):
        self.addTrf(trf)
        self.updated.emit()
        self.populateOpeTrf(lastselected=True)


    def trfEditValidated(self, trf: transfer):
        self.editTrf(trf)
        self.updated.emit()
        self.populateOpeTrf(lastselected=True)


    def trfAddClicked(self):
        ted = TrfEditDialog(self._settings,
                            self._locale,
                            self,
                            self._fi,
                            self._act)
        ted.added.connect(lambda: self.trfAddValidated(ted.trf))
        if ted.exec_() == QMessageBox.Accepted:
            self.trfAddValidated(ted.trf)
        ted.destroy()


    def opeTrfCheckClicked(self):
        for rowidx in self.opeList.selectionModel().selectedRows():
            itmid = rowidx.parent().child(rowidx.row(), 1)
            ot = itmid.data(Qt.UserRole)
            if ot is None:
                continue
            state = False
            exists = False
            for o in self._act.operations:
                if o.id == ot.id:
                    newstate = not o.state
                    if not newstate:
                        reply = QMessageBox.question(self, '' + appinfos.app_name + '', funcs.tr(
                            "Désirez-vous supprimer le pointage de cette opération?"), QMessageBox.Yes | QMessageBox.No)
                        if reply == QMessageBox.No:
                            return
                    o.state = newstate
                    state = o.state
                    exists = True
                    break
            if not exists:
                for t in self._fi.transfers:
                    if t.id == ot.id:
                        newstate = not t.state
                        if not newstate:
                            reply = QMessageBox.question(self, '' + appinfos.app_name + '', funcs.tr(
                                "Désirez-vous supprimer le pointage de ce transfert?"), QMessageBox.Yes | QMessageBox.No)
                            if reply == QMessageBox.No:
                                return
                        t.state = newstate
                        state = t.state
                        exists = True
                        break
            if exists:
                itmstate = rowidx.parent().child(rowidx.row(), 2)
                itm = rowidx.parent().model().itemFromIndex(itmstate)
                itm.setData(state, Qt.UserRole)
                if state:
                    itm.setIcon(QIcon(icons.get('ope-check.png')))
                else:
                    itm.setIcon(QIcon())
                self.updated.emit()


    def opeTrfDeleteClicked(self):
        cnt = 0
        for rowidx in self.opeList.selectionModel().selectedRows():
            if not rowidx.parent().isValid():
                continue
            itmid = rowidx.parent().child(rowidx.row(), 1)
            ot = itmid.data(Qt.UserRole)
            if ot is None:
                return
            cnt += 1
        if cnt < 1:
            return

        reply = QMessageBox.question(self, '' + appinfos.app_name + '', funcs.tr(
            "Etes-vous certain de vouloir supprimer {}?".format(
                "les {} enregistrements sélectionnés".format(cnt) if cnt > 1 else "l'enregistrement sélectionné")),
            QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            idxes = {}
            for rowidx in self.opeList.selectionModel().selectedRows():
                if not rowidx.parent().isValid():
                    continue
                itmid = rowidx.parent().child(rowidx.row(), 1)
                ot = itmid.data(Qt.UserRole)
                if ot is None:
                    return
                if not(rowidx.parent() in idxes.keys()):
                    idxes[rowidx] = []
                exists = False
                for o in self._act.operations:
                    if o.id == ot.id:
                        self._act.operations.remove(o)
                        idxes[rowidx].append(itmid)
                        exists = True
                        break
                if not exists:
                    for t in self._fi.transfers:
                        if t.id == ot.id:
                            self._fi.transfers.remove(t)
                            idxes[rowidx].append(itmid)
                            exists = True
                            break
            # sort groups descending
            idxes = dict(sorted(idxes.items(), key=lambda x: x[0].row(), reverse=True))
            # sort groups values descending
            idxes = {k: sorted(v, key=lambda x: x.row(), reverse=True) for k, v in idxes.items()}
            # delere recursly
            for k, v in idxes.items():
                while len(v) > 0:
                    self.opeList.model().removeRow(v[0].row(), v[0].parent())
                    prt = self.opeList.model().itemFromIndex(v[0].parent())
                    if not(prt is None) and not prt.hasChildren():
                        self.opeList.model().removeRow(v[0].parent().row(), QModelIndex())
                    v.pop(0)
            self.updated.emit()


    def opeTrfEditDoubleClicked(self, index):
        if index.parent().isValid():
            self.opeTrfEditClicked()


    def opeTrfEditClicked(self):
        cnt = len(self.opeList.selectionModel().selectedRows())
        if cnt != 1:
            return

        rowidx = self.opeList.selectionModel().selectedRows()[0]
        itmid = rowidx.parent().child(rowidx.row(), 1)
        ot = itmid.data(Qt.UserRole)

        if type(ot) == operation:
            oed = OpeEditDialog(self._settings,
                                self._locale,
                                self,
                                self._fi,
                                self._act,
                                ope=ot)
            if oed.exec_() == QMessageBox.Accepted:
                self.opeEditValidated(oed.ope)
            oed.destroy()

        elif type(ot) == transfer:
            if ot.toactid == self._act.id:
                self.opeEdit.setEnabled(False)
                QMessageBox.information(self, '' + appinfos.app_name + '', funcs.tr(
                    "Vous ne pouvez pas éditer un transfert qui vous est destiné."))
                return
            ted = TrfEditDialog(self._settings,
                                self._locale,
                                self,
                                self._fi,
                                self._act,
                                trf=ot)
            if ted.exec_() == QMessageBox.Accepted:
                self.trfEditValidated(ted.trf)
            ted.destroy()


    def tabAccountChanged(self, index):
        self.toolbar2.setEnabled(index == 0 or index == 1)
        self.opeAddAction.setVisible(index == 0)
        self.trfAddAction.setVisible(index == 0)
        self.opeEdit.setVisible(index == 0)
        self.opeDelete.setVisible(index == 0)
        self.opeSeparator0.setVisible(index == 0)
        self.opeCheck.setVisible(index == 0)
        self.opeSeparator1.setVisible(index == 0)
        self.plannerAddOpeAction.setVisible(index == 2)
        self.plannerAddTrfAction.setVisible(index == 2)
        self.plannerEdit.setVisible(index == 2)
        self.plannerDelete.setVisible(index == 2)
        self.opeSeparator2.setVisible(index == 2)
        self.calendarTodayAction.setVisible(index == 1)
        self.opeSeparator3.setVisible(index == 1)
        self.plannerPostAction.setVisible(index == 2)
        self.plannerPostAllAction.setVisible(index == 2)
        self.opeSeparator4.setVisible(index == 2)


    def calendarSelectionChanged(self):
        self.opeList.selectionModel().selectionChanged.disconnect(self.opeTrfListSelected)

        dte = self.opeCalendar.selectedDate().toPyDate()
        key = str(dte.year).rjust(4, '0') + str(dte.month).rjust(2, '0') + str(dte.day).rjust(2, '0')
        for i in range(self.opeList.model().rowCount()):
            idx = self.opeList.model().index(i, 0)
            itm = self.opeList.model().itemFromIndex(idx)
            if itm.data(Qt.UserRole) == key:
                self.opeList.expand(idx)
                for j in range(itm.rowCount()):
                    if j == 0:
                        self.opeList.selectionModel().select(
                                self.opeList.model().index(j, 0, itm.index()),
                                QItemSelectionModel.Rows | QItemSelectionModel.ClearAndSelect)
                        self.opeList.scrollTo(self.opeList.model().index(0, 0, itm.index()), QAbstractItemView.EnsureVisible)
                    else:
                        self.opeList.selectionModel().select(
                                self.opeList.model().index(j, 0, itm.index()),
                                QItemSelectionModel.Rows | QItemSelectionModel.Select)
                break;

        self.opeList.selectionModel().selectionChanged.connect(self.opeTrfListSelected)


    def calendarTodayClicked(self):
        self.opeCalendar.setSelectedDate(datetime.now().date())


    def populatePlannerType(self):
        self.plannerType.clear()
        model = QStandardItemModel()
        l = [
            [funcs.tr("jour(s)"), 'd'],
            [funcs.tr("semaine(s)"), 'w'],
            [funcs.tr("mois"), 'm'],
            [funcs.tr("an(s)"), 'y']
        ]
        for n in range(len(l)):
            if isinstance(l[n], list):
                a = QStandardItem(l[n][0])
                a.setData(l[n][1], Qt.UserRole)
                a.setBackground(QColor(Qt.white))
                model.appendRow(a)

        self.plannerType.setModel(model)


    def populatePlannerWeekend(self):
        self.plannerWeekend.clear()
        model = QStandardItemModel()
        l = [
            [funcs.tr("weekend possible"), 'weekend'],
            [funcs.tr("avant le weekend"), 'before'],
            [funcs.tr("après le weekend"), 'after']
        ]
        for n in range(len(l)):
            if isinstance(l[n], list):
                a = QStandardItem(l[n][0])
                a.setData(l[n][1], Qt.UserRole)
                a.setBackground(QColor(Qt.white))
                model.appendRow(a)

        self.plannerWeekend.setModel(model)


    def makePlannerListRowTooltip(self, evt: event, tooltipdatas: dict):
        if evt.ended:
            txt = funcs.tr("<b>Planification terminée.<b>")
        else:
            txt = funcs.tr("<b>Planification {} du {} au {}:<b><br /><br />"\
                          .format("active" if evt.state else "inactive", "{}", "{}"))\
                .format(tooltipdatas['firstdate'], tooltipdatas['lastdate'])
            txt += funcs.tr("<small>{} d'un montant de <b>{}</b> {}</small><br /><br />"\
                           .format("Crédit" if tooltipdatas['amount'] >= 0 else "Débit",
                                   libs.currencies.formatCurrency(tooltipdatas['amount'], self._act.alpha_3),
                                   tooltipdatas['to']))
            txt += funcs.tr("<small><b>Prochain postage {} prévu le {}<b/></small>"\
                           .format("automatique" if evt.autoPost else "manuel", "{}"))\
                .format(tooltipdatas['nextdate'])

        return txt


    def makeEvent(self, evt: event):
        tpe = evt.operation
        if tpe is None:
            tpe = evt.transfer

        disabled_color = self.palette().color(QPalette.Disabled, QPalette.Text).name()
        now = datetime.now().date()

        tooltipdatas = {}

        lastdate = QStandardItem()
        lastdate.setText(evt.lastdate.strftime(self._shortDateFormat))
        tooltipdatas['lastdate'] = evt.lastdate.strftime(self._longDateFormat)
        lastdate.setEditable(False)
        lastdate.setData(evt.lastdate, Qt.UserRole)
        lastdate.setTextAlignment(Qt.AlignLeft)
        if not evt.state or evt.ended:
            lastdate.setText('<span style="color: {};">{}</span>'.format(
                disabled_color,
                lastdate.text()))
        self.strikeThrough(lastdate, evt.ended)

        firstdate = QStandardItem()
        firstdate.setText(tpe.fromdate.strftime(self._shortDateFormat))
        tooltipdatas['firstdate'] = tpe.fromdate.strftime(self._longDateFormat)
        firstdate.setEditable(False)
        firstdate.setData(tpe.fromdate, Qt.UserRole)
        firstdate.setTextAlignment(Qt.AlignLeft)
        if not evt.state or evt.ended:
            firstdate.setText('<span style="color: {};">{}</span>'.format(
                disabled_color,
                firstdate.text()))
        self.strikeThrough(firstdate, evt.ended)

        nextdate = QStandardItem()
        nextdate.setText(evt.nextdate.strftime(self._shortDateFormat))
        tooltipdatas['nextdate'] = evt.nextdate.strftime(self._longDateFormat)
        nextdate.setEditable(False)
        nextdate.setData(evt.nextdate, Qt.UserRole)
        nextdate.setTextAlignment(Qt.AlignLeft)
        if evt.autoPost:
            nextdate.setIcon(QIcon(icons.get('autopost.png')))
        if evt.state and not evt.ended:
            if evt.nextdate < now:
                nextdate.setText('<span style="color: red;">{}</span>'.format(nextdate.text()))
            if (evt.nextdate >= now) and \
               ((evt.repeattype == 'd' and evt.nextdate == now) or \
               (evt.repeattype == 'w' and evt.nextdate.year == now.year and evt.nextdate.isocalendar()[1] == now.isocalendar()[1]) or \
               (evt.repeattype == 'm' and evt.nextdate.month == now.month) or \
               (evt.repeattype == 'y' and evt.nextdate.year == now.year)):
                f = nextdate.font()
                f.setBold(True)
                nextdate.setFont(f)
        if not evt.state or evt.ended:
            nextdate.setText('<span style="color: {};">{}</span>'.format(
                disabled_color,
                nextdate.text()))
        self.strikeThrough(nextdate, evt.ended)

        id = QStandardItem()
        id.setEditable(False)
        id.setText("")
        id.setIcon(QIcon(icons.get('alloperation.png') if not(evt.operation is None) else icons.get('transfer.png')))
        id.setData(evt, Qt.UserRole)
        id.setTextAlignment(Qt.AlignCenter)
        if not evt.state or evt.ended:
            id.setText('<span style="color: {};">{}</span>'.format(
                disabled_color,
                id.text()))
            id.setEnabled(False)
        self.strikeThrough(id, evt.ended)

        state = QStandardItem()
        state.setEditable(False)
        state.setText("")
        state.setData(evt.state, Qt.UserRole)
        state.setTextAlignment(Qt.AlignCenter)
        if not evt.state or evt.ended:
            state.setText('<span style="color: {};">{}</span>'.format(
                disabled_color,
                state.text()))
            state.setEnabled(False)
        else:
            state.setIcon(QIcon(icons.get('ope-check.png')))

        amt = tpe.amount

        to = QStandardItem()
        to.setEditable(False)
        if type(tpe) == operation:
            to.setText(tpe.to)
            to.setData(tpe.to, Qt.UserRole)
            tooltipdatas['to'] = funcs.tr("{} {}".format("en provenance de" if tpe.amount >= 0 else "à destination de", "{}")).format(tpe.to)
        elif type(tpe) == transfer:
            ta = None
            for a in self._fi.accounts:
                if tpe.toactid == a.id:
                    ta = a
            if (tpe.fromactid == self._act.id) and not(ta is None):
                to.setText(funcs.tr(
                    "Vers <i>{}</i>").format(ta.title))
                to.setData(ta, Qt.UserRole)
                tooltipdatas['to'] = funcs.tr(
                    "vers {}").format(ta.title)
                amt = -amt
        if not evt.state or evt.ended:
            to.setText('<span style="color: {};">{}</span>'.format(
                disabled_color,
                to.text()))
        self.strikeThrough(to, evt.ended)

        title = QStandardItem()
        txt = tpe.title
        title.setText(txt)
        title.setEditable(False)
        title.setData(tpe.title, Qt.UserRole)
        if not evt.state or evt.ended:
            title.setText('<span style="color: {};">{}</span>'.format(
                disabled_color,
                title.text()))
        self.strikeThrough(title, evt.ended)

        comment = QStandardItem()
        comment.setText(tpe.comment)
        comment.setEditable(False)
        comment.setData(tpe.comment, Qt.UserRole)
        if not evt.state or evt.ended:
            comment.setText('<span style="color: {};">{}</span>'.format(
                disabled_color,
                comment.text()))
        self.strikeThrough(comment, evt.ended)

        r = evt.repeat
        rt = funcs.tr("mois")
        rs = funcs.tr("tous les {} {}").format(r, rt)
        if evt.repeattype == 'd':
            rt = funcs.tr("jour") if r <= 1 else "jours"
            rs = funcs.tr("tous les {} {}").format(r, rt)
        elif evt.repeattype == 'm':
            rt = funcs.tr("mois") if r <= 1 else "mois"
            rs = funcs.tr("tous les {} {}").format(r, rt)
        elif evt.repeattype == 'w':
            rt = funcs.tr("semaine") if r <= 1 else "semaines"
            rs = funcs.tr("toutes les {} {}").format(r, rt)
        elif evt.repeattype == 'y':
            rt = funcs.tr("an") if r <= 1 else "ans"
            rs = funcs.tr("tous les {} {}").format(r, rt)
        repeat = QStandardItem()
        repeat.setText(rs)
        tooltipdatas['repeat'] = rs
        repeat.setEditable(False)
        repeat.setData("{} {}".format(evt.repeat, evt.repeattype), Qt.UserRole)
        if not evt.state or evt.ended:
            repeat.setText('<span style="color: {};">{}</span>'.format(
                disabled_color,
                repeat.text()))
        self.strikeThrough(repeat, evt.ended)

        amount = QStandardItem()
        amount.setText(libs.currencies.formatCurrency(amt, self._act.alpha_3))
        tooltipdatas['amount'] = tpe.amount
        if evt.state and not evt.ended:
            color = self._settings.value('color_positive_amount')
            if amt < 0.0:
                color = self._settings.value('color_negative_amount')
            amount.setText('<span style="color: {};">{}</span>'.format(
                color,
                libs.currencies.formatCurrency(amt, self._act.alpha_3)))
        amount.setEditable(False)
        amount.setData(amt, Qt.UserRole)
        amount.setTextAlignment(Qt.AlignRight)
        if not evt.state or evt.ended:
            amount.setText('<span style="color: {};">{}</span>'.format(
                disabled_color,
                amount.text()))
        self.strikeThrough(amount, evt.ended)

        tooltip = self.makePlannerListRowTooltip(evt, tooltipdatas)
        lastdate.setToolTip(tooltip)
        firstdate.setToolTip(tooltip)
        nextdate.setToolTip(tooltip)
        id.setToolTip(tooltip)
        state.setToolTip(tooltip)
        to.setToolTip(tooltip)
        title.setToolTip(tooltip)
        comment.setToolTip(tooltip)
        repeat.setToolTip(tooltip)
        amount.setToolTip(tooltip)

        return id, state, firstdate, lastdate, nextdate, repeat, to, title, comment, amount


    def populatePlannner(self, lastselected: bool = False):
        if self._populatePlannerFlag:
            return

        self._populatePlannerFlag = True

        lastselectedidx = []
        lastselecteddata = []
        if not(self.opePlanner.selectionModel() is None):
            if len(self.opePlanner.selectionModel().selectedIndexes()) > 0:
                for idx in self.opePlanner.selectionModel().selectedIndexes():
                    idxcol = idx.siblingAtColumn(4)
                    data = self.opePlanner.model().itemFromIndex(idxcol).data(Qt.UserRole)
                    lastselectedidx.append(idx)
                    lastselecteddata.append(data)
            self.opePlanner.selectionModel().clearSelection()

        self.opePlanner.setModel(None)
        self.model = None
        self.model = QStandardItemModel()
        self.model.setColumnCount(10)
        self.model.setHeaderData(0, QtCore.Qt.Horizontal, funcs.tr("Début"))
        self.model.setHeaderData(1, QtCore.Qt.Horizontal, funcs.tr("Fin"))
        self.model.setHeaderData(2, QtCore.Qt.Horizontal, funcs.tr("Suivante"))
        self.model.setHeaderData(3, QtCore.Qt.Horizontal, funcs.tr("Répétition"))
        self.model.setHeaderData(4, QtCore.Qt.Horizontal, funcs.tr(""))
        self.model.horizontalHeaderItem(4).setTextAlignment(Qt.AlignCenter)
        self.model.setHeaderData(5, QtCore.Qt.Horizontal, funcs.tr(""))
        self.model.horizontalHeaderItem(5).setTextAlignment(Qt.AlignCenter)
        self.model.setHeaderData(6, QtCore.Qt.Horizontal, funcs.tr("Tiers"))
        self.model.setHeaderData(7, QtCore.Qt.Horizontal, funcs.tr("Dénomination"))
        self.model.setHeaderData(8, QtCore.Qt.Horizontal, funcs.tr("Commentaire"))
        self.model.setHeaderData(9, QtCore.Qt.Horizontal, funcs.tr("Montant"))
        self.model.horizontalHeaderItem(9).setTextAlignment(Qt.AlignRight)

        for evt in self._act.planner:
            if evt.operation is None and evt.transfer is None:
                continue

            id, state, firstdate, lastdate, nextdate, repeat, to, title, comment, amount = self.makeEvent(evt)
            self.model.appendRow([firstdate, lastdate, nextdate, repeat, id, state, to, title, comment, amount])

        self.opePlanner.setModel(self.model)
        self.opePlanner.setItemDelegate(HTMLDelegate(parent=None, settings=self._settings, fi=self._fi, act=self._act))
        self.opePlanner.header().setMinimumSectionSize(1)
        self.opePlanner.header().resizeSection(0, 80)
        self.opePlanner.header().resizeSection(1, 80)
        self.opePlanner.header().resizeSection(2, 100)
        self.opePlanner.header().resizeSection(3, 150)
        self.opePlanner.header().resizeSection(4, 24)
        self.opePlanner.header().resizeSection(5, 24)
        self.opePlanner.header().resizeSection(6, 150)
        self.opePlanner.header().setSectionResizeMode(6, QHeaderView.Stretch)
        self.opePlanner.header().resizeSection(7, 150)
        self.opePlanner.header().resizeSection(8, 150)
        self.opePlanner.header().resizeSection(9, 80)

        self.opePlanner.model().setSortRole(Qt.UserRole)
        self.opePlanner.sortByColumn(2, Qt.AscendingOrder)
        self.opePlanner.model().sort(2, Qt.AscendingOrder)

        self.opePlanner.expandAll()

        if lastselected and self.opePlanner.model().rowCount() > 0:
            for i in range(self.opePlanner.model().rowCount()):
                idx = self.opePlanner.model().index(i, 4)
                itm = self.opePlanner.model().itemFromIndex(idx)
                evt = itm.data(Qt.UserRole)
                if len(lastselectedidx) > 0 and evt in lastselecteddata:
                    self.opePlanner.selectionModel().select(
                        idx,
                        QItemSelectionModel.Rows | QItemSelectionModel.ClearAndSelect)
                    self.plannerSelected(idx, QModelIndex())
                    break

        self.opePlanner.selectionModel().selectionChanged.connect(self.plannerSelected)

        self._populatePlannerFlag = False


    def plannerDoubleClicked(self, index):
        self.plannerEditClicked()


    def plannerGetSelectedEvent(self):
        scnt = len(self.opePlanner.selectionModel().selectedRows())
        if scnt > 0:
            lastrow = self.opePlanner.selectionModel().selectedRows()[scnt - 1]
            itm = self.opePlanner.model().itemFromIndex(self.opePlanner.model().index(lastrow.row(), 4, lastrow.parent()))
            evt = itm.data(Qt.UserRole)
            if isinstance(evt, event):
                return evt
        return None


    def plannerUpdateDetailsView(self, evt: event, ld: date=None):
        firstdate = evt.operation.fromdate if not(evt.operation is None) else evt.transfer.fromdate
        if ld is None:
            ld = evt.lastdate
        pos, tot = evt.getPosition(ld=ld)
        try:
            self.plannerCount.valueChanged.disconnect(self.plannerCountChanged)
        except:
            pass
        self.plannerCount.setValue(tot)
        self.plannerCount.valueChanged.connect(self.plannerCountChanged)
        self.plannerCount.setSuffix(" " + funcs.tr("répétition{}").format("s" if tot > 1 else ""))
        self.plannerNextButton.setEnabled(evt.hasNextdate(ld=ld))
        self.plannerResetButton.setEnabled(evt.nextdate > firstdate)
        dt = evt.nextdate
        wd = dt.isoweekday()
        if wd == 6 or wd == 7:
            if evt.beforeWeekend and not evt.afterWeekend:
                dt = dt - relativedelta(days=(wd - 5))
            elif not evt.beforeWeekend and evt.afterWeekend:
                dt = dt + relativedelta(days=((7 - wd) + 1))
        self.plannerResume.setText(funcs.tr("Prochaine date le <b>{}</b>{}, répétition <b>{} sur {}</b>")\
                                   .format(dt.strftime(self._longDateFormat) if dt != evt.nextdate else evt.nextdate.strftime(self._longDateFormat),
                                           " <small>(" + evt.nextdate.strftime(self._longDateFormat) + ")</small>" if dt != evt.nextdate else "",
                                           pos, tot))


    def plannerSelected(self, new, old):
        if self._plannerSelectedFlag:
            return

        self._plannerSelectedFlag = True
        try:
            self.plannerType.currentIndexChanged.disconnect(self.plannerTypeChanged)
            self.plannerWeekend.currentIndexChanged.disconnect(self.plannerWeekendChanged)
            self.plannerState.stateChanged.disconnect(self.plannerStateChanged)
            self.plannerNumber.valueChanged.disconnect(self.plannerNumberChanged)
            self.plannerCount.valueChanged.disconnect(self.plannerCountChanged)
            self.plannerLastdate.valueChanged.disconnect(self.plannerLastdateChanged)
            self.plannerAutopostButton.clicked.disconnect(self.plannerAutopostClicked)
        except:
            pass

        self.plannerFrame.setUpdatesEnabled(False)

        self.plannerEdit.setEnabled(False)
        self.plannerDelete.setEnabled(False)
        self.plannerState.setChecked(False)
        self.plannerNumber.setValue(0)
        self.plannerCount.setValue(0)
        self.plannerType.setCurrentIndex(-1)
        self.plannerWeekend.setCurrentIndex(-1)
        self.plannerLastdate.setDate(datetime.now().date())
        self.plannerNextButton.setEnabled(False)
        self.plannerResetButton.setEnabled(False)
        self.plannerPostAction.setEnabled(False)
        self.plannerAutopostButton.setChecked(False)
        self.plannerFrame.setEnabled(False)
        self.plannerResume.setText("")

        evt = self.plannerGetSelectedEvent()
        if not(evt is None):
            self.plannerEdit.setEnabled(True)
            self.plannerDelete.setEnabled(True)
            self.plannerState.setChecked(evt.state)
            self.plannerNumber.setValue(evt.repeat)
            idx = -1
            if evt.repeattype == 'd':
                idx = 0
            elif evt.repeattype == 'w':
                idx = 1
            elif evt.repeattype == 'm':
                idx = 2
            elif evt.repeattype == 'y':
                idx = 3
            self.plannerType.setCurrentIndex(idx)
            idx = -1
            if evt.beforeWeekend and not evt.afterWeekend:
                idx = 1
            elif not evt.beforeWeekend and evt.afterWeekend:
                idx = 2
            else:
                idx = 0
            self.plannerWeekend.setCurrentIndex(idx)
            firstdate = evt.operation.fromdate if not(evt.operation is None) else evt.transfer.fromdate
            self.plannerLastdate.setMinimumDate(firstdate)
            self.plannerLastdate.setDate(evt.lastdate)
            self.plannerUpdateDetailsView(evt)
            self.plannerPostAction.setEnabled(evt.state and not evt.ended)
            self.plannerAutopostButton.setChecked(not evt.ended and evt.autoPost)
            self.plannerFrame.setEnabled(not evt.ended)

        self.plannerFrame.setUpdatesEnabled(True)

        self.plannerState.stateChanged.connect(self.plannerStateChanged)
        self.plannerType.currentIndexChanged.connect(self.plannerTypeChanged)
        self.plannerWeekend.currentIndexChanged.connect(self.plannerWeekendChanged)
        self.plannerNumber.valueChanged.connect(self.plannerNumberChanged)
        self.plannerCount.valueChanged.connect(self.plannerCountChanged)
        self.plannerLastdate.dateChanged.connect(self.plannerLastdateChanged)
        self.plannerAutopostButton.clicked.connect(self.plannerAutopostClicked)

        self._plannerSelectedFlag = False


    def plannerAddOpeClicked(self):
        oed = OpeEditDialog(self._settings,
                        self._locale,
                        self,
                        self._fi,
                        self._act,
                        nokeep=True)
        if oed.exec_() == QMessageBox.Accepted:
            evt = event(state=False,
                        nextdate=oed.ope.fromdate,
                        lastdate=oed.ope.fromdate,
                        repeat=1,
                        repeattype='m',
                        operation=oed.ope,
                        transfer=None)
            self._act.planner.append(evt)
            self.updated.emit()
            self.populatePlannner()
        oed.destroy()


    def plannerAddTrfClicked(self):
        ted = TrfEditDialog(self._settings,
                                self._locale,
                                self,
                                self._fi,
                                self._act,
                                nokeep=True)
        ted.added.connect(lambda: self.trfAddValidated(ted.trf))
        if ted.exec_() == QMessageBox.Accepted:
            evt = event(state=False,
                        nextdate=ted.trf.fromdate,
                        lastdate=ted.trf.fromdate,
                        repeat=1,
                        repeattype='m',
                        operation=None,
                        transfer=ted.trf)
            self._act.planner.append(evt)
            self.updated.emit()
            self.populatePlannner()
        ted.destroy()


    def plannerEditClicked(self):
        evt = self.plannerGetSelectedEvent()
        if not(evt is None):
            if not(evt.operation is None):
                oed = OpeEditDialog(self._settings,
                                    self._locale,
                                    self,
                                    self._fi,
                                    self._act,
                                    ope=evt.operation)
                if oed.exec_() == QMessageBox.Accepted:
                    evt.operation.title = oed.ope.title
                    evt.operation.fromdate = oed.ope.fromdate
                    evt.operation.amount = oed.ope.amount
                    evt.operation.comment = oed.ope.comment
                    evt.operation.to = oed.ope.to
                    evt.operation.category = oed.ope.category
                    evt.operation.state = oed.ope.state
                    self.updated.emit()
                    self.populatePlannner()
                oed.destroy()

            elif not(evt.transfer is None):
                ted = TrfEditDialog(self._settings,
                                    self._locale,
                                    self,
                                    self._fi,
                                    self._act,
                                    trf=evt.transfer)
                if ted.exec_() == QMessageBox.Accepted:
                    evt.transfer.title = ted.trf.title
                    evt.transfer.fromdate = ted.trf.fromdate
                    evt.transfer.amount = ted.trf.amount
                    evt.transfer.comment = ted.trf.comment
                    evt.transfer.fromactid = ted.trf.fromactid
                    evt.transfer.toactid = ted.trf.toactid
                    evt.transfer.state = ted.trf.state
                    self.updated.emit()
                    self.populatePlannner()
                ted.destroy()

            else:
                self.plannerEdit.setEnabled(False)
        else:
            self.plannerEdit.setEnabled(False)


    def plannerDeleteClicked(self):
        evt = self.plannerGetSelectedEvent()
        if not(evt is None):
            reply = QMessageBox.question(self, '' + appinfos.app_name + '', funcs.tr(
                "Etes-vous certain de vouloir supprimer la planification sélectionnée?"),
                                         QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                self._act.planner.remove(evt)
                self.updated.emit()
                self.populatePlannner()
        else:
            self.plannerDelete.setEnabled(False)


    def plannerTypeChanged(self, index):
        if self._plannerSelectedFlag or self._populatePlannerFlag:
            return
        evt = self.plannerGetSelectedEvent()
        if not(evt is None):
            tpe = self.plannerType.currentData()
            if evt.repeattype == tpe:
                return
            evt.repeattype = tpe
            self.updated.emit()
            self.populatePlannner(lastselected=True)


    def plannerWeekendChanged(self, index):
        if self._plannerSelectedFlag or self._populatePlannerFlag:
            return

        evt = self.plannerGetSelectedEvent()
        if not(evt is None):
            tpe = self.plannerWeekend.currentData()
            before = True if tpe == 'before' else False
            after = True if tpe == 'after' else False
            if evt.beforeWeekend == before and evt.afterWeekend == after:
                return
            evt.beforeWeekend = before
            evt.afterWeekend = after
            self.updated.emit()
            self.populatePlannner(lastselected=True)


    def plannerStateChanged(self, state):
        if self._plannerSelectedFlag or self._populatePlannerFlag:
            return

        evt = self.plannerGetSelectedEvent()
        if not(evt is None):
            if evt.state == state:
                return
            evt.state = state
            self.updated.emit()
            self.populatePlannner(lastselected=True)


    def plannerNumberChanged(self, value):
        if self._plannerSelectedFlag or self._populatePlannerFlag:
            return

        evt = self.plannerGetSelectedEvent()
        if not(evt is None):
            if evt.repeat == value:
                return
            evt.repeat = value
            #self.plannerUpdateDetailsView(evt)
            self.updated.emit()
            self.populatePlannner(lastselected=True)


    def plannerLastdateChanged(self, date):
        if self._plannerSelectedFlag or self._populatePlannerFlag:
            return

        evt = self.plannerGetSelectedEvent()
        if not(evt is None):
            if evt.lastdate == date.toPyDate():
                return
            evt.lastdate = date.toPyDate()
            ld = evt.getLastDate()
            print(ld)
            if evt.nextdate > ld:
                evt.nextdate = ld
                evt.verifyNextdate()
            #self.plannerUpdateDetailsView(evt)
            self.updated.emit()
            self.populatePlannner(lastselected=True)


    def plannerCountChanged(self, value):
        #self.plannerCount.setSuffix(" " + funcs.tr("répétition{}").format("s" if value > 1 else ""))
        if self._plannerSelectedFlag or self._populatePlannerFlag:
            return

        evt = self.plannerGetSelectedEvent()
        if not(evt is None):
            dt = evt.operation.fromdate if not(evt.operation is None) else evt.transfer.fromdate
            for i in range(value - 1):
                if evt.repeattype == 'd':
                    dt = dt + relativedelta(days=evt.repeat)
                elif evt.repeattype == 'w':
                    dt = dt + relativedelta(weeks=evt.repeat)
                elif evt.repeattype == 'm':
                    dt = dt + relativedelta(months=evt.repeat)
                elif evt.repeattype == 'y':
                    dt = dt + relativedelta(years=evt.repeat)
            evt.lastdate = dt
            ld = evt.getLastDate()
            if evt.nextdate > ld:
                evt.nextdate = ld
            evt.verifyNextdate()
            #self.plannerUpdateDetailsView(evt)
            self.updated.emit()
            self.populatePlannner(lastselected=True)


    def plannerNextButtonClicked(self):
        evt = self.plannerGetSelectedEvent()
        if not(evt is None):
            nd = evt.getNextdate()
            if not(nd is None):
                if evt.nextdate == nd:
                    return
                evt.nextdate = nd
                evt.verifyNextdate()
                #self.plannerUpdateDetailsView(evt)
                self.updated.emit()
                self.populatePlannner(lastselected=True)


    def plannerResetButtonClicked(self):
        evt = self.plannerGetSelectedEvent()
        if not(evt is None):
            evt.resetNextdate()
            evt.verifyNextdate()
            #self.plannerUpdateDetailsView(evt)
            self.updated.emit()
            self.populatePlannner(lastselected=True)


    def plannerAddOpe(self, evt: event):
        ope = operation(title=evt.operation.title,
                        amount=evt.operation.amount,
                        fromdate=evt.nextdate,
                        comment=evt.operation.comment,
                        to=evt.operation.to,
                        paytype=evt.operation.paytype,
                        category=evt.operation.category,
                        state=evt.operation.state)
        self.opeAddValidated(ope)


    def plannerAddTrf(self, evt: event):
        trf = transfer(title=evt.transfer.title,
                                           amount=evt.transfer.amount,
                                           fromdate=evt.nextdate,
                                           comment=evt.transfer.comment,
                                           state=evt.transfer.state,
                                           fromactid=evt.transfer.fromactid,
                                           toactid=evt.transfer.toactid)
        self.trfAddValidated(trf)


    def plannerAutopostClicked(self, checked):
        evt = self.plannerGetSelectedEvent()
        if not(evt is None):
            if evt.autoPost == checked:
                return
            evt.autoPost = checked
            evt.verifyNextdate()
            #self.plannerUpdateDetailsView(evt)
            self.updated.emit()
            self.populatePlannner(lastselected=True)


    def plannerPostClicked(self):
        evt = self.plannerGetSelectedEvent()
        if not(evt is None):
            if evt.state and not evt.ended:
                firstdate = evt.operation.fromdate if not(evt.operation is None) else evt.transfer.fromdate

                dt = evt.nextdate
                wd = dt.isoweekday()
                if wd == 6 or wd == 7:
                    if evt.beforeWeekend and not evt.afterWeekend:
                        dt = dt - relativedelta(days=(wd - 5))
                    elif not evt.beforeWeekend and evt.afterWeekend:
                        dt = dt + relativedelta(days=((7 - wd) + 1))

                if not(evt.operation is None):
                    reply = QMessageBox.question(self, '' + appinfos.app_name + '', funcs.tr(
                        "Poster la planification sélectionnée?"), QMessageBox.Yes | QMessageBox.No)
                    if reply == QMessageBox.Yes:
                        ope = operation(title=evt.operation.title,
                                        amount=evt.operation.amount,
                                        fromdate=dt,
                                        comment=evt.operation.comment,
                                        to=evt.operation.to,
                                        paytype=evt.operation.paytype,
                                        category=evt.operation.category,
                                        state=evt.operation.state)
                        evt.ended = not evt.computeNextdate()
                        evt.autoPost = False if evt.ended else evt.autoPost
                        self.opeAddValidated(ope)

                if not(evt.transfer is None):
                    reply = QMessageBox.question(self, '' + appinfos.app_name + '', funcs.tr(
                        "Poster la planification sélectionnée?"), QMessageBox.Yes | QMessageBox.No)
                    if reply == QMessageBox.Yes:
                        trf = transfer(title=evt.transfer.title,
                                       amount=evt.transfer.amount,
                                       fromdate=dt,
                                       comment=evt.transfer.comment,
                                       state=evt.transfer.state,
                                       fromactid=evt.transfer.fromactid,
                                       toactid=evt.transfer.toactid)
                        evt.ended = not evt.computeNextdate()
                        evt.autoPost = False if evt.ended else evt.autoPost
                        self.trfAddValidated(trf)

                evt.verifyNextdate()
                #self.plannerUpdateDetailsView(evt)
                self.plannerClean(save=False)
                self.populatePlannner(lastselected=True)


    def plannerClean(self, save: bool=False):
        remove = []
        for evt in self._act.planner:
            if evt.operation is None and evt.transfer is None:
                remove.append(evt)
                continue
            if evt.ended:
                if self._settings.value('Planner/auto_delete_finished'):
                    remove.append(evt)
        for evt in remove:
            self._act.planner.remove(evt)
        if len(remove) > 0:
            self.forceUpdateRequired.emit(save)


    def plannerAutoPost(self, save: bool=False, force: bool=False, refresh: bool=False):
        if self._settings.value('Planner/auto_post') or force:
            if force:
                reply = QMessageBox.question(self, '' + appinfos.app_name + '', funcs.tr(
                    "Voulez-vous poster toutes les planifications en retard?"), QMessageBox.Yes | QMessageBox.No)
                if reply == QMessageBox.No:
                    return

            postdate = datetime.now().date()

            remove = []
            for evt in self._act.planner:
                if evt.operation is None and evt.transfer is None:
                    remove.append(evt)
                    continue

                nextevt = True
                while nextevt:
                    dt = evt.nextdate
                    wd = dt.isoweekday()
                    if wd == 6 or wd == 7:
                        if evt.beforeWeekend and not evt.afterWeekend:
                            dt = dt - relativedelta(days=(wd - 5))
                        elif not evt.beforeWeekend and evt.afterWeekend:
                            dt = dt + relativedelta(days=((7 - wd) + 1))
                    atdate = (dt <= postdate)

                    if evt.state and not evt.ended and evt.autoPost and atdate:
                        firstdate = evt.operation.fromdate if not(evt.operation is None) else evt.transfer.fromdate

                        if not(evt.operation is None):
                            ope = operation(title=evt.operation.title,
                                            amount=evt.operation.amount,
                                            fromdate=dt,
                                            comment=evt.operation.comment,
                                            to=evt.operation.to,
                                            paytype=evt.operation.paytype,
                                            category=evt.operation.category,
                                            state=evt.operation.state)
                            evt.ended = not evt.computeNextdate()
                            evt.autoPost = False if evt.ended else evt.autoPost
                            self.addOpe(ope)

                        if not(evt.transfer is None):
                            trf = transfer(title=evt.transfer.title,
                                           amount=evt.transfer.amount,
                                           fromdate=dt,
                                           comment=evt.transfer.comment,
                                           state=evt.transfer.state,
                                           fromactid=evt.transfer.fromactid,
                                           toactid=evt.transfer.toactid)
                            evt.ended = not evt.computeNextdate()
                            evt.autoPost = False if evt.ended else evt.autoPost
                            self.addTrf(trf)

                        if evt.ended:
                            if self._settings.value('Planner/auto_delete_finished'):
                                remove.append(evt)
                                nextevt = False
                        else:
                            evt.verifyNextdate()
                    else:
                        nextevt = False

            for evt in remove:
                self._act.planner.remove(evt)

            self.updated.emit()
            self.forceUpdateRequired.emit(save)
            if refresh:
                self.populatePlannner(lastselected=True)
                self.populateOpeTrf(lastselected=True)



