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
from datetime import datetime, date

from PyQt5 import QtCore, QtWidgets, QtGui, uic
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *

from pyqtgraph import PlotWidget, plot
import pyqtgraph as pg

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


class QHLine(QFrame):

    def __init__(self):
        h = 25
        super(QHLine, self).__init__()
        self.setFrameShape(QFrame.HLine)
        self.setFrameShadow(QFrame.Sunken)
        self.setLineWidth(1)
        self.setEnabled(False)
        self.setContentsMargins(0, h - self.lineWidth(), 0, 0)
        self.setMinimumSize(QSize(0, h))

class MdiHome(MdiFrame):

    _amounts = {}
    _debits = {}
    _credits = {}

    def __init__(self, settings, locale, parent, fi: financial, closable: bool = True, *args, **kwargs):
        super(MdiHome, self).__init__(settings, locale,
                                      parent, fi, closable, *args, **kwargs)

    def _init_ui(self):
        super(MdiHome, self)._init_ui()
        self.setWindowIcon(QIcon(icons.get('go-home.png')))
        self.homeLabel.setText(funcs.tr("Etats et résumé du portefeuille"))
        self.scrollArea.setStyleSheet("#scrollArea { background: #fff; }")
        self.scrollAreaWidgetContents.setStyleSheet("#scrollAreaWidgetContents { background: #fff; }")

        QApplication.setOverrideCursor(Qt.WaitCursor)

        self.gl = QGridLayout()
        self.gl.setContentsMargins(12, 12, 12, 12)

        rownum = 0
        for a in self._fi.accounts:
            if type(a) == creditcard and a.accountid != -1:
                continue
            rownum = self.populateGraphs(a, rownum)

        try:
            spacer = QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding)
            self.gl.addItem(spacer, rownum, 0, 1, 2, alignment=Qt.AlignTop)
        except Exception as e:
            print(e)

        w = QWidget()
        w.setObjectName('rw')
        w.setStyleSheet("#rw { background: #fff; }")
        w.setLayout(self.gl)
        self.scrollArea.setWidget(w)

        QApplication.restoreOverrideCursor()

    def eventFilter(self, obj, event):
        if type(obj) == PlotWidget:
            if event.type() == QEvent.Leave:
                QToolTip.hideText()
                obj.removeItem(self.amountEvoVLine)
                obj.removeItem(self.credebwidgetVLine)
        return super(MdiHome, self).eventFilter(obj, event)

    def computeAmountEvo(self, a:account, dte:date=datetime.now().date()):
        s = date(dte.year, dte.month, 1)
        e = s + relativedelta(months=1)
        axis_x = [n + 1 for n in range((e - s).days)]
        axis_y = [0 for n in range(len(axis_x))]
        for i in range(len(axis_x)):
            day = axis_x[i]
            amts = self._fi.amount_atdate(accountid=a.id, atdate=date(dte.year, dte.month, day))
            axis_y[i] += amts
        return axis_x, axis_y

    def makeAmountEvo(self, a:account, axis_x:list, axis_y:list, dte:date=datetime.now(), minY=0, maxY=0):
        amountEvo = pg.PlotWidget()
        amountEvo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        amountEvo.setMinimumSize(0, 250)
        amountEvo.setMaximumSize(16777215, 250)
        amountEvo.setBackground('#fff')
        amountEvo.showGrid(x=True, y=True)
        amountEvo.setXRange(min(axis_x), max(axis_x), padding=0.01)
        if minY != 0 and minY != maxY:
            amountEvo.setYRange(0 if minY >= 0 else minY, maxY, padding=0.1)
        else:
            amountEvo.setYRange(0 if min(axis_y) >= 0 else min(axis_y), max(axis_y), padding=0.1)
        amountEvo.addLegend()
        styles = {'color':'#555', 'font-size':'8pt'}
        amountEvo.setLabel('left', funcs.tr("Solde ({})").format(currency.symbol(a.alpha_3)), units='', **styles)
        amountEvo.setLabel('bottom', dte.strftime('%B %Y').capitalize(), units='', **styles)
        amountEvo.setTitle(funcs.tr("Evolution du solde sur {}").format(dte.strftime('%B %Y')), color='#000', size='8pt')
        for i in range(0, len(axis_x) - 1, 1):
            p1 = [axis_x[i], axis_x[i + 1]]
            p2 = [axis_y[i], axis_y[i + 1]]
            chtml = '#D6D300'
            c = QColor(chtml)
            amountEvo.plot(p1, p2, pen=pg.mkPen(color=chtml), brush=(c.red(), c.green(), c.blue(), 40), fillLevel=0)
        self.amountEvoVLine = amountEvo.addLine(x=min(axis_x))
        amountEvoCallback = lambda evt: self.graphsAmountEvoMouseMoved(amountEvo, evt, dte.year, dte.month, a.id, a.alpha_3)
        pg.SignalProxy(amountEvo.scene().sigMouseMoved, rateLimit=60, slot=amountEvoCallback)
        amountEvo.scene().sigMouseMoved.connect(amountEvoCallback)
        amountEvo.setMouseTracking(True)
        amountEvo.installEventFilter(self)
        return amountEvo

    def computeCreDeb(self, a:account, dte:date=datetime.now().date()):
        s = date(dte.year, dte.month, 1)
        e = s + relativedelta(months=1)
        axis_x = [n + 1 for n in range((e - s).days)]
        axis_y_deb = [0 for n in range(len(axis_x))]
        axis_y_cre = [0 for n in range(len(axis_x))]
        for i in range(len(axis_x)):
            for o in a.operations:
                if o.fromdate.year == dte.year and o.fromdate.month == dte.month and o.fromdate.day == axis_x[i]:
                    if o.amount >= 0:
                        axis_y_cre[i] += abs(o.amount)
                    else:
                        axis_y_deb[i] += o.amount
            for t in self._fi.transfers:
                if t.fromdate.year == dte.year and t.fromdate.month == dte.month and t.fromdate.day == axis_x[i]:
                    if t.fromactid == a.id:
                        axis_y_deb[i] += -t.amount
                    if t.toactid == a.id:
                        axis_y_cre[i] += abs(t.amount)
        return axis_x, axis_y_deb, axis_y_cre

    def makeCreDeb(self, a:account, axis_x:list, axis_y_deb:list, axis_y_cre:list, dte:date=datetime.now(), minY=0, maxY=0):
        credebwidget = pg.PlotWidget()
        credebwidget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        credebwidget.setMinimumSize(0, 250)
        credebwidget.setMaximumSize(16777215, 250)
        credebwidget.setBackground('#fff')
        credebwidget.showGrid(x=True, y=True)
        credebwidget.setXRange(min(axis_x), max(axis_x), padding=0.01)
        if minY != 0 and minY != maxY:
            credebwidget.setYRange(minY, maxY, padding=0.1)
        else:
            credebwidget.setYRange(min(axis_y_deb), max(axis_y_cre), padding=0.1)
        credebwidget.addLegend()
        styles = {'color':'#555', 'font-size':'8pt'}
        credebwidget.setLabel('left', funcs.tr("Dépenses | Revenus ({})").format(currency.symbol(a.alpha_3)), units='', **styles)
        credebwidget.setLabel('bottom', dte.strftime('%B %Y').capitalize(), units='', **styles)
        credebwidget.setTitle(funcs.tr("Revenus et dépenses cumulés de {}").format(dte.strftime('%B %Y')), color='#000', size='8pt')
        chtml = self._settings.value('color_negative_amount')
        c = QColor(chtml)
        deb = pg.BarGraphItem(x=axis_x, height=axis_y_deb, width=0.8, brush=(c.red(), c.green(), c.blue(), 50))
        credebwidget.addItem(deb)
        chtml = self._settings.value('color_positive_amount')
        c = QColor(chtml)
        cre = pg.BarGraphItem(x=axis_x, height=axis_y_cre, width=0.8, brush=(c.red(), c.green(), c.blue(), 50))
        credebwidget.addItem(cre)
        self.credebwidgetVLine = credebwidget.addLine(x=min(axis_x))
        credebwidgetCallback = lambda evt: self.graphsCredDebMouseMoved(credebwidget, evt, dte.year, dte.month, a.id, a.alpha_3)
        pg.SignalProxy(credebwidget.scene().sigMouseMoved, rateLimit=60, slot=credebwidgetCallback)
        credebwidget.scene().sigMouseMoved.connect(credebwidgetCallback)
        credebwidget.setMouseTracking(True)
        credebwidget.installEventFilter(self)
        return credebwidget

    def populateGraphs(self, a:account, rownum:int=0):
        txt = a.title
        n = a.name.strip() if hasattr(a, 'name') and a.name.strip() != '' else ''
        if n != '':
            txt = txt + ' (' + n + ')'

        prevMonth = datetime.now().date() - relativedelta(months=1)
        now = datetime.now().date()

        prev_axis_x, prev_axis_y = self.computeAmountEvo(a, prevMonth)
        now_axis_x, now_axis_y = self.computeAmountEvo(a, now)
        minY = min(prev_axis_y + now_axis_y)
        maxY = max(prev_axis_y + now_axis_y)
        prev_amountEvo = self.makeAmountEvo(a, prev_axis_x, prev_axis_y, dte=prevMonth, minY=minY, maxY=maxY)
        now_amountEvo = self.makeAmountEvo(a, now_axis_x, now_axis_y, dte=now, minY=minY, maxY=maxY)

        prev_axis_x, prev_axis_y_deb, prev_axis_y_cre = self.computeCreDeb(a, prevMonth)
        now_axis_x, now_axis_y_deb, now_axis_y_cre = self.computeCreDeb(a, now)
        minY = min(prev_axis_y_deb + now_axis_y_deb)
        maxY = max(prev_axis_y_cre + now_axis_y_cre)
        prev_credebwidget = self.makeCreDeb(a, prev_axis_x, prev_axis_y_deb, prev_axis_y_cre, dte=prevMonth, minY=minY, maxY=maxY)
        now_credebwidget = self.makeCreDeb(a, now_axis_x, now_axis_y_deb, now_axis_y_cre, dte=now, minY=minY, maxY=maxY)

        lbl = QLabel()
        lbl.setText('<b>' + txt + '</b>')
        self.gl.addWidget(lbl, rownum, 0, 1, 2, alignment=Qt.AlignTop)
        self.gl.addWidget(prev_amountEvo, rownum + 1, 0, 1, 1, alignment=Qt.AlignTop)
        self.gl.addWidget(now_amountEvo, rownum + 1, 1, 1, 1, alignment=Qt.AlignTop)
        self.gl.addWidget(prev_credebwidget, rownum + 2, 0, 1, 1, alignment=Qt.AlignTop)
        self.gl.addWidget(now_credebwidget, rownum + 2, 1, 1, 1, alignment=Qt.AlignTop)
        self.gl.addWidget(QHLine(), rownum + 3, 0, 1, 2, alignment=Qt.AlignTop)

        return (rownum + 4)

    def graphsAmountEvoMouseMoved(self, graph, pos, year, month, actid, alpha_3):
        graph.removeItem(self.amountEvoVLine)
        if graph.sceneBoundingRect().contains(pos):
            vb = graph.plotItem.vb
            mousePoint = vb.mapSceneToView(pos)
            try:
                day = round(mousePoint.x())
                s = date(year, month, 1)
                e = s + relativedelta(months=1)
                if day >= 1 and day <= (e - s).days:
                    k = day - 1
                    p = 0
                    if k > len(graph.plotItem.listDataItems()) - 1:
                        k = len(graph.plotItem.listDataItems()) - 1
                        p = -1
                    dataItem = graph.plotItem.listDataItems()[k]
                    axis_x, axis_y = dataItem.getData()
                    amount = axis_y.tolist()[p]
                    dt_format = date(year, month, day).strftime(self._longDateFormat)
                    amt_format = libs.currencies.formatCurrency(amount, alpha_3)
                    pt = graph.mapToGlobal(QPoint(pos.x(), pos.y()))
                    QToolTip.showText(pt, funcs.tr("<small>{}</small><br /><b>{}</b>").format(dt_format, amt_format))
                    self.amountEvoVLine = graph.addLine(x=day, pen=pg.mkPen('#777', width=1, style=Qt.DashLine))
                else:
                    QToolTip.hideText()
            except:
                QToolTip.hideText()
        else:
            QToolTip.hideText()

    def graphsCredDebMouseMoved(self, graph, pos, year, month, actid, alpha_3):
        graph.removeItem(self.credebwidgetVLine)
        if graph.sceneBoundingRect().contains(pos):
            vb = graph.plotItem.vb
            mousePoint = vb.mapSceneToView(pos)
            try:
                day = round(mousePoint.x())
                s = date(year, month, 1)
                e = s + relativedelta(months=1)
                if day >= 1 and day <= (e - s).days:
                    dataItem = graph.plotItem.listDataItems()[0]
                    axis_x, axis_y = dataItem.getData()
                    idx = axis_x.index(day)
                    debit = axis_y[idx]
                    dataItem = graph.plotItem.listDataItems()[1]
                    axis_x, axis_y = dataItem.getData()
                    idx = axis_x.index(day)
                    credit = axis_y[idx]
                    dt_format = date(year, month, day).strftime(self._longDateFormat)
                    dbt_format = libs.currencies.formatCurrency(debit, alpha_3)
                    crd_format = libs.currencies.formatCurrency(credit, alpha_3)
                    pt = graph.mapToGlobal(QPoint(pos.x(), pos.y()))
                    QToolTip.showText(pt, funcs.tr("<small>{}</small><br />Dépenses totales: <b>{}</b><br />Revenus totaux: <b>{}</b>").format(dt_format, dbt_format, crd_format))
                    self.credebwidgetVLine = graph.addLine(x=day, pen=pg.mkPen('#777', width=1, style=Qt.DashLine))
                else:
                    QToolTip.hideText()
            except:
                QToolTip.hideText()
        else:
            QToolTip.hideText()
