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
import math
from datetime import datetime

from PyQt5 import QtCore, QtWidgets, QtGui, uic
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *

from pyqtgraph import PlotWidget, plot, exporters
import pyqtgraph as pg

import libs.pycountry
import currency

import libs.completer
import resources
import appinfos
import funcs
import icons

from datamodels import *

from ui.MdiFrame import MdiFrame
from ui.HBarGraph import HBarGraph
from ui.VBarGraph import VBarGraph
from ui.PieGraph import PieGraph


class QGraphicsEllipseItemEx(QGraphicsEllipseItem):

	toolTip:str = ''

	def __init__(self, x, y, w, h):
		super().__init__(x, y, w, h)
		self.setAcceptHoverEvents(True)

	def hoverEnterEvent(self, event: 'QGraphicsSceneHoverEvent'):
		if self.toolTip != '':
			QToolTip.showText(QCursor.pos(), self.toolTip)

	def hoverLeaveEvent(self, event: 'QGraphicsSceneHoverEvent'):
		QToolTip.hideText()


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

class HTMLDelegate(QStyledItemDelegate):

	def __init__(self, parent, settings):
		super(HTMLDelegate, self).__init__(parent)
		self.pen = QPen(QColor(Qt.lightGray))
		self._settings = settings

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

		if type(options.widget) == QTreeView:
			if mouseOver:
				viewportPos = options.widget.viewport().mapFromGlobal(QCursor.pos())
				if viewportPos.x() >= 0 and viewportPos.y() >= 0:
					color = option.palette.color(QPalette.Active, QPalette.Highlight)
					color.setAlpha(30)
					painter.fillRect(option.rect, color)

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

		return QSize(doc.size().width(), h)


class MdiStats(MdiFrame):

	_type = 'categories'
	_title = ''

	_act = None
	_graphLines = {}
	_graphsk = {}

	def __init__(self, settings, locale, parent, fi: financial, act: account=None, closable: bool=True, title='', ctype='categories', *args, **kwargs):
		self._act = act
		self._title = title.strip()
		self._type = ctype.strip().lower() \
			if ctype.strip().lower() in ['categories', 'thirdparties', 'paytypes'] \
			else 'categories'
		super(MdiStats, self).__init__(settings, locale, parent, fi, closable, *args, **kwargs)
		self.populateFilterAccount()
		self.populateFilterDate()
		self.populateFilterType()
		self.populate()

	def _init_ui(self):
		super(MdiStats, self)._init_ui()
		self.setWindowTitle(funcs.tr(self._title))
		self.reportLabel.setText(funcs.tr("Rapports et statistiques: {}").format(funcs.tr(self._title)))
		self.setWindowIcon(QIcon(icons.get('reports-' + self._type + '.png')))
		self.scrollArea.setStyleSheet("#scrollArea { background: #fff; }")
		self.scrollAreaWidgetContents.setStyleSheet("#scrollAreaWidgetContents { background: #fff; }")

		self.toolbar2 = QToolBar(self.parent())
		self.toolbar2.setWindowTitle(funcs.tr("Barre de gestion des filtres"))

		self.filterAccount = QComboBox(self.toolbar2)
		self.toolbar2.addWidget(self.filterAccount)

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

		self.opeTrfList.viewport().setMouseTracking(True)

	def eventFilter(self, obj, event):
		if type(obj) == PlotWidget:
			if event.type() == QEvent.Leave:
				QToolTip.hideText()
				for lineName,line in self._graphLines.items():
					obj.removeItem(line)
		return super(MdiStats, self).eventFilter(obj, event)

	def populate(self):
		getattr(self, 'populate' + self._type.capitalize())()

	def populateFilterAccount(self):
		self.filterAccount.clear()
		model = QStandardItemModel()

		l = []
		types = [bankaccount, creditcard, wallet]
		for t in types:
			for a in self._fi.accounts:
				if type(a) == t:
					if t == creditcard and a.accountid != -1:
						continue
					nm = a.title
					if hasattr(a, 'name'):
						nm = '{} ({})'.format(nm, a.name)
					l.append([nm, a.id])
			if len(l) > 0:
				l.append('-')

		separators = []
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
			elif l[n] == '-':
				separators.append(n)

		self.filterAccount.setModel(model)

		for idx in separators:
			self.filterAccount.insertSeparator(idx)

		self.filterAccount.setCurrentIndex(0)
		self.filterAccount.currentIndexChanged.connect(self.filterAccountChanged)

	def filterAccountChanged(self, index):
		self.populate()

	def populateFilterDate(self):
		defaultFilterDate = 'last90days'

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
		filter_date = defaultFilterDate

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
		self.filterDateStart.setEnabled(data == 'custom')
		self.filterDateEnd.setEnabled(data == 'custom')
		self.setFilterDates(data, refresh=True)

	def filterCustomStartDateChanged(self, date):
		data = self.filterDate.currentData()
		if data == 'custom':
			self.populate()

	def filterCustomEndDateChanged(self, date):
		data = self.filterDate.currentData()
		if data == 'custom':
			self.populate()

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
			filter_sdate = funcs.first_day_of_month(datetime.now()).strftime('%Y-%m-%d')
			filter_edate = funcs.last_day_of_month(datetime.now()).strftime('%Y-%m-%d')
			s = datetime.strptime(filter_sdate, '%Y-%m-%d').date()
			e = datetime.strptime(filter_edate, '%Y-%m-%d').date()

		self.filterDateStart.setDate(s)
		self.filterDateEnd.setDate(e)
		if refresh:
			self.populate()


	def populateFilterType(self):
		self.filterType.clear()
		model = QStandardItemModel()
		l = [
		    [funcs.tr("Tous les types"), 'alltypes'],
		    '-',
		    [funcs.tr("Dépenses"), 'debits'],
		    [funcs.tr("Revenus"), 'credits']
		]

		filter_type = 'alltypes'

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
		self.populate()

	def applyFilterOpe(self, act: account, ope: operation):
		f_start_date = self.filterDateStart.date().toPyDate()
		f_end_date = self.filterDateEnd.date().toPyDate()

		f_type_data = self.filterType.currentData()
		f_type = (lambda a, t: True)
		if f_type_data == 'debits':
			f_type = (lambda a, t: a < 0)
		elif f_type_data == 'credits':
			f_type = (lambda a, t: a >= 0)
		elif f_type_data in self._fi.paytypes:
			f_type = (lambda a, t: t == 'alltypes')

		result = True
		result = result and (ope.fromdate >= f_start_date and ope.fromdate <= f_end_date)
		result = result and f_type(ope.amount, ope.paytype)
		return result


	def applyFilterTrf(self, act: account, trf: transfer):
		f_start_date = self.filterDateStart.date().toPyDate()
		f_end_date = self.filterDateEnd.date().toPyDate()

		f_type_data = self.filterType.currentData()
		f_type = (lambda: True)
		if f_type_data == 'debits':
			f_type = (lambda: act.id == trf.fromactid)
		elif f_type_data == 'credits':
			f_type = (lambda: act.id == trf.toactid)
		else:
			f_type = (lambda: f_type_data == 'alltypes')

		result = True
		result = result and (trf.fromdate >= f_start_date and trf.fromdate <= f_end_date)
		result = result and f_type()
		return result

	def makeOpeItem(self, act:account, ope:operation):
		fromdate = QStandardItem()
		fromdate.setText(ope.fromdate.strftime(self._shortDateFormat))
		fromdate.setEditable(False)
		fromdate.setData(ope.fromdate, Qt.UserRole)
		fromdate.setTextAlignment(Qt.AlignRight)

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
				libs.currencies.formatCurrency(ope.amount, act.alpha_3)))
		amount.setEditable(False)
		amount.setData(ope.amount, Qt.UserRole)
		amount.setTextAlignment(Qt.AlignRight)

		return id, fromdate, to, title, paytype, amount

	def makeTrfItem(self, act:account, trf:transfer):
		fa = None
		ta = None
		for a in self._fi.accounts:
			if trf.fromactid == a.id:
				fa = a
			if trf.toactid == a.id:
				ta = a

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
		if (trf.fromactid == act.id) and not(ta is None):
			to.setText(funcs.tr(
					"Vers <i>{}</i>").format(ta.title))
			to.setData(ta, Qt.UserRole)
			amt = -amt
		elif (trf.toactid == act.id) and not(fa is None):
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

		amount = QStandardItem()
		color = self._settings.value('color_positive_amount')
		if amt < 0.0:
			color = self._settings.value('color_negative_amount')
		amount.setText('<span style="color: {};">{}</span>'.format(
				color,
				libs.currencies.formatCurrency(amt, act.alpha_3)))
		amount.setEditable(False)
		amount.setData(amt, Qt.UserRole)
		amount.setTextAlignment(Qt.AlignRight)

		paytype = QStandardItem()
		paytype.setText(funcs.tr("Transfert"))
		paytype.setEditable(False)
		paytype.setData("Transfert", Qt.UserRole)

		return id, fromdate, to, title, paytype, amount

	def clearGraphics(self):
		if type(self.scrollArea.widget()) == QWidget:
			self.scrollArea.widget().deleteLater()
			self._graphLines.clear()
			self._graphsk.clear()
			QApplication.processEvents()

	def makeLayout(self) -> QGridLayout:
		gl = QGridLayout()
		gl.setContentsMargins(12, 12, 12, 12)
		gl.setHorizontalSpacing(12)
		return gl

	def makeGraphics(self, gl:QGridLayout):
		w = QWidget()
		w.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
		w.setObjectName('rw')
		w.setStyleSheet("#rw { background: #fff; }")
		w.setLayout(gl)
		self.scrollArea.setWidget(w)

	def addSubTitle(self, gl:QGridLayout, title:str, row:int=0, col:int=0, rowspan=1, colspan:int=2):
		f = self.font()
		f.setPointSize(8)
		glbl = QLabel(title)
		glbl.setFont(f)
		gl.addWidget(glbl, row, col, rowspan, colspan, alignment=Qt.AlignBottom | Qt.AlignHCenter)

	def addGraphics(self, gl:QGridLayout, graph:QWidget, title:str, row:int=0, col:int=0, rowspan=1, colspan:int=2):
		self.addSubTitle(gl, title, row, col, rowspan, colspan)
		row += 1
		gl.addWidget(graph, row, col, rowspan, colspan, alignment=Qt.AlignTop)

	def addHLine(self, gl:QGridLayout, row:int=0, col:int=0, rowspan=1, colspan:int=2):
		gl.addWidget(QHLine(), row, col, rowspan, colspan, alignment=Qt.AlignTop)

	def createCategoriesGraph(self, act:account, first_date:date, last_date:date, monthes, items):
		self.clearGraphics()
		gl = self.makeLayout()

		datas_credit = {}
		brushes_credit = []
		datas_debit = {}
		brushes_debit = []
		graphs = []
		for k,v in items['list'].items():
			color, chtml = funcs.text2color(k)
			c = QColor(chtml)
			grad = QLinearGradient(0, 0, 0, 1)
			grad.setCoordinateMode(QGradient.ObjectBoundingMode)
			grad.setColorAt(0.1, pg.mkColor((c.red(), c.green(), c.blue(), 100)))
			grad.setColorAt(0.9, pg.mkColor((c.red(), c.green(), c.blue(), 255)))

			if not(k in datas_credit.keys()):
				percent_credit = (v['credit total'] * 100) / items['credit total'] if items['credit total'] != 0 else 0
				datas_credit[k] = percent_credit
				brushes_credit.append(QBrush(grad))
			if not(k in datas_debit.keys()):
				percent_debit = (v['debit total'] * 100) / items['debit total'] if items['debit total'] != 0 else 0
				datas_debit[k] = percent_debit
				brushes_debit.append(QBrush(grad))

			_axis = {}
			_brushes = []
			for dte in monthes:
				key = dte.strftime('%Y-%m')
				amt = 0.0
				ck = 'credit ' + key
				dk = 'debit ' + key
				if ck in v.keys():
					amt += v[ck]
				if dk in v.keys():
					amt += -v[dk]
				_axis[dte.strftime('%Y %b')] = amt
				grad = QLinearGradient(0, 0, 0, 1)
				grad.setCoordinateMode(QGradient.ObjectBoundingMode)
				if amt >= 0:
					grad.setColorAt(0.1, pg.mkColor((c.red(), c.green(), c.blue(), 100)))
					grad.setColorAt(0.9, pg.mkColor((c.red(), c.green(), c.blue(), 255)))
				else:
					grad.setColorAt(0.1, pg.mkColor((c.red(), c.green(), c.blue(), 255)))
					grad.setColorAt(0.9, pg.mkColor((c.red(), c.green(), c.blue(), 100)))
				_brushes.append(QBrush(grad))
			graphs.append({'title':k, 'axis':_axis, 'brushes':_brushes})

		vg_credit = VBarGraph(datas=datas_credit,
							  brushes=brushes_credit,
							  labels={'left':{'text':funcs.tr("Parts (%)"),'units':''},
									  'bottom':{'text':funcs.tr("Catégories"),'units':''}},
							  numBars=7)
		vg_credit.tooltipCallback = (lambda value: '{}%'.format(round(value, 2)))
		self.addGraphics(gl,
						 vg_credit,
						 funcs.tr("Part des <b>revenus</b> par catégories (%)"),
						 row=0, col=0, colspan=1)

		vg_debit = VBarGraph(datas=datas_debit,
							 brushes=brushes_debit,
							 labels={'left':{'text':funcs.tr("Parts (%)"),'units':''},
									 'bottom':{'text':funcs.tr("Catégories"),'units':''}},
							  numBars=7)
		vg_debit.tooltipCallback = (lambda value: '{}%'.format(round(value, 2)))
		self.addGraphics(gl,
						 vg_debit,
						 funcs.tr("Part des <b>dépenses</b> par catégories (%)"),
						 row=0, col=1, colspan=1)

		row = 2
		for item in graphs:
			vg = VBarGraph(datas=item['axis'],
						   brushes=item['brushes'],
						   labels={'left':{'text':funcs.tr("Montants ({})").format(currency.symbol(act.alpha_3)),'units':''},
								   'bottom':{'text':'','units':''}},
						   numBars=10)
			vg.tooltipCallback = (lambda value: '{}'.format(libs.currencies.formatCurrency(value, act.alpha_3)))
			self.addHLine(gl, row)
			row += 1
			self.addGraphics(gl,
							 vg,
							 '<b>{}</b>'.format(funcs.tr(item['title'])),
							 row=row, col=0, colspan=2)
			row += 2

		self.makeGraphics(gl)

	def populateCategories(self):
		QApplication.setOverrideCursor(Qt.WaitCursor)
		self.setUpdatesEnabled(False)

		if not(self.opeTrfList.model() is None):
			self.opeTrfList.model().clear()
		self.opeTrfList.setModel(None)

		# creation de la liste des catégories
		trfcat = 'Transfert'
		l = {}
		for k, v in self._fi.categories.items():
			if len(v) > 0:
				for sc in v:
					l[k + ': ' + sc] = []
			else:
				l[k + ': ' + k] = []
		# si la catégorie 'Transfert' n'existe pas on l'ajoute
		if not(trfcat in l.keys()):
			l[trfcat + ': ' + trfcat] = []

		# on recherche le compte associé à l'Id sélectionné
		actid = self.filterAccount.currentData()
		act = None
		for a in self._fi.accounts:
			if a.id == actid:
				act = a
				break
		if act is None:
			self.setUpdatesEnabled(True)
			QApplication.restoreOverrideCursor()
			return

		# on récupère les opérations filtrées du compte sélectionné
		for ope in act.operations:
			if self.applyFilterOpe(act, ope):
				cats = ope.category.split(':')
				prt = cats[0].strip()
				chld = prt
				if len(cats) > 1:
					chld = cats[1].strip()
				cat = prt + ': ' + chld
				if not(cat in l.keys()):
					l[cat] = []
				l[cat].append(ope)

		# ainsi que la liste des transferts
		for trf in self._fi.transfers:
			if self.applyFilterTrf(act, trf):
				if trf.fromactid == actid or trf.toactid == actid:
					l[trfcat + ': ' + trfcat].append(trf)

		# puis on hierarchise le tout en catégories
		monthes = []
		items = {'count': 0, 'debit total': 0.0, 'credit total': 0.0, 'list': {}}
		for cat, opetrflist in l.items():
			cats = cat.split(':')
			prt = cats[0].strip()
			chld = cats[1].strip()
			if not(prt in items['list'].keys()):
				items['list'][prt] = {'count': 0,
									  'debit total': 0.0,
									  'credit total': 0.0,
									  'childs': {}}
			if not(chld in items['list'][prt]['childs'].keys()):
				items['list'][prt]['childs'][chld] = {'count': 0,
													  'debit total': 0.0,
													  'credit total': 0.0}
			items['list'][prt]['childs'][chld]['count'] = len(opetrflist)
			items['list'][prt]['count'] += items['list'][prt]['childs'][chld]['count']
			items['count'] += items['list'][prt]['childs'][chld]['count']
			for opetrf in opetrflist:
				if not(funcs.first_day_of_month(opetrf.fromdate) in monthes):
					monthes.append(funcs.first_day_of_month(opetrf.fromdate))
				if not(('debit ' + opetrf.fromdate.strftime('%Y-%m')) in items['list'][prt]['childs'][chld].keys()):
					items['list'][prt]['childs'][chld]['debit ' + opetrf.fromdate.strftime('%Y-%m')] = 0.0
				if not(('credit ' + opetrf.fromdate.strftime('%Y-%m')) in items['list'][prt]['childs'][chld].keys()):
					items['list'][prt]['childs'][chld]['credit ' + opetrf.fromdate.strftime('%Y-%m')] = 0.0
				amt = opetrf.amount
				if type(opetrf) == operation:
					if amt < 0:
						items['list'][prt]['childs'][chld]['debit total'] += abs(amt)
						items['list'][prt]['childs'][chld]['debit ' + opetrf.fromdate.strftime('%Y-%m')] += abs(amt)
					else:
						items['list'][prt]['childs'][chld]['credit total'] += abs(amt)
						items['list'][prt]['childs'][chld]['credit ' + opetrf.fromdate.strftime('%Y-%m')] += abs(amt)
				elif type(opetrf) == transfer:
					fa = None
					ta = None
					for a in self._fi.accounts:
						if trf.fromactid == a.id:
							fa = a
						if trf.toactid == a.id:
							ta = a
					if (trf.fromactid == act.id) and not(ta is None):
						items['list'][prt]['childs'][chld]['debit total'] += abs(amt)
						items['list'][prt]['childs'][chld]['debit ' + opetrf.fromdate.strftime('%Y-%m')] += abs(amt)
					elif (trf.toactid == act.id) and not(fa is None):
						items['list'][prt]['childs'][chld]['credit total'] += abs(amt)
						items['list'][prt]['childs'][chld]['credit ' + opetrf.fromdate.strftime('%Y-%m')] += abs(amt)

			items['list'][prt]['credit total'] += items['list'][prt]['childs'][chld]['credit total']
			items['credit total'] += items['list'][prt]['childs'][chld]['credit total']
			items['list'][prt]['debit total'] += items['list'][prt]['childs'][chld]['debit total']
			items['debit total'] += items['list'][prt]['childs'][chld]['debit total']

			for key,value in items['list'][prt]['childs'][chld].items():
				if (key.startswith('credit') and key != 'credit total') or \
				   (key.startswith('debit') and key != 'debit total'):
					if not(key in items['list'][prt]):
						items['list'][prt][key] = 0.0
					items['list'][prt][key] += items['list'][prt]['childs'][chld][key]
					if not(key in items):
						items[key] = 0.0
					items[key] += items['list'][prt][key]

		del l
		monthes = list(sorted(monthes))

		# préparation de la liste
		m = QStandardItemModel()
		m.setColumnCount(5 + len(monthes))
		m.setHeaderData(0, QtCore.Qt.Horizontal, funcs.tr("Catégorie"))
		m.setHeaderData(1, QtCore.Qt.Horizontal, funcs.tr("Revenus"))
		m.horizontalHeaderItem(1).setTextAlignment(Qt.AlignRight)
		m.setHeaderData(2, QtCore.Qt.Horizontal, funcs.tr("%"))
		m.horizontalHeaderItem(2).setTextAlignment(Qt.AlignRight)
		m.setHeaderData(3, QtCore.Qt.Horizontal, funcs.tr("Dépenses"))
		m.horizontalHeaderItem(3).setTextAlignment(Qt.AlignRight)
		m.setHeaderData(4, QtCore.Qt.Horizontal, funcs.tr("%"))
		m.horizontalHeaderItem(4).setTextAlignment(Qt.AlignRight)
		i = 5
		for dte in monthes:
			m.setHeaderData(i, QtCore.Qt.Horizontal, funcs.tr(dte.strftime('%Y %b')))
			m.horizontalHeaderItem(i).setTextAlignment(Qt.AlignRight)
			i += 1

		# affichage du contenu de la liste hierarchisée
		positive_color = self._settings.value('color_positive_amount')
		negative_color = self._settings.value('color_negative_amount')

		root = QStandardItem()
		root.setText('<span>{}</span> <span><small>({})</small></span>'.format(funcs.tr("Toutes catégories"),
																			   items['count']))
		root.setEditable(False)
		root.setData([root.text(), items], Qt.UserRole)

		rootv_credit = QStandardItem()
		rootv_credit.setEditable(False)
		rootv_credit.setText('<span style="color: {};">{}</span>'.format(positive_color,
																		 libs.currencies.formatCurrency(items['credit total'],
																										act.alpha_3)))
		rootv_credit.setTextAlignment(Qt.AlignRight)
		rootv_credit.setData(items['credit total'], Qt.UserRole)
		positive_percent = round(100.00, 2)
		rootp_credit = QStandardItem()
		rootp_credit.setEditable(False)
		rootp_credit.setText('<span style="color: {};">{}%</span>'.format(positive_color,
																		  positive_percent))
		rootp_credit.setTextAlignment(Qt.AlignRight)
		rootp_credit.setData(positive_percent, Qt.UserRole)

		rootv_debit = QStandardItem()
		rootv_debit.setEditable(False)
		rootv_debit.setText('<span style="color: {};">{}</span>'.format(negative_color,
																		libs.currencies.formatCurrency(-items['debit total'],
																									   act.alpha_3)))
		rootv_debit.setTextAlignment(Qt.AlignRight)
		rootv_debit.setData(-items['debit total'], Qt.UserRole)
		negative_percent = round(100.00, 2)
		rootp_debit = QStandardItem()
		rootp_debit.setEditable(False)
		rootp_debit.setText('<span style="color: {};">{}%</span>'.format(negative_color,
																		 negative_percent))
		rootp_debit.setTextAlignment(Qt.AlignRight)
		rootp_debit.setData(negative_percent, Qt.UserRole)

		rmonthes_cols = []
		for dte in monthes:
			key = dte.strftime('%Y-%m')
			amt = 0.0
			ck = 'credit ' + key
			dk = 'debit ' + key
			if ck in items.keys():
				amt += items[ck]
			if dk in items.keys():
				amt += -items[dk]
			r_month = QStandardItem()
			r_month.setEditable(False)
			r_month.setText('<span style="color: {};">{}</span>'.format(negative_color if amt < 0 else positive_color,
																		libs.currencies.formatCurrency(amt, act.alpha_3)))
			r_month.setTextAlignment(Qt.AlignRight)
			r_month.setData(amt, Qt.UserRole)
			rmonthes_cols.append(r_month)

		for k,v in items['list'].items():
			color, html = funcs.text2color(k)
			c = QStandardItem()
			c.setText('<span style="font-weight: bold; color: {}">{}</span> <span><small>({})</small></span>'.format(html,
																													 funcs.tr(k),
																													 v['count']))
			c.setEditable(False)
			c.setData(k, Qt.UserRole)

			cv_credit = QStandardItem()
			cv_credit.setEditable(False)
			cv_credit.setText('<span style="color: {};">{}</span>'.format(positive_color,
																		  libs.currencies.formatCurrency(v['credit total'],
																										 act.alpha_3)))
			cv_credit.setTextAlignment(Qt.AlignRight)
			cv_credit.setData(v['credit total'], Qt.UserRole)
			positive_percent = round((v['credit total'] * 100) / items['credit total'], 2) if items['credit total'] != 0 else 0.0
			cp_credit = QStandardItem()
			cp_credit.setEditable(False)
			cp_credit.setText('<span style="color: {};">{}%</span>'.format(positive_color,
																		   positive_percent))
			cp_credit.setTextAlignment(Qt.AlignRight)
			cp_credit.setData(positive_percent, Qt.UserRole)

			cv_debit = QStandardItem()
			cv_debit.setEditable(False)
			cv_debit.setText('<span style="color: {};">{}</span>'.format(negative_color,
																		 libs.currencies.formatCurrency(-v['debit total'],
																										act.alpha_3)))
			cv_debit.setTextAlignment(Qt.AlignRight)
			cv_debit.setData(-v['debit total'], Qt.UserRole)
			negative_percent = round((v['debit total'] * 100) / items['debit total'], 2) if items['debit total'] != 0 else 0.0
			cp_debit = QStandardItem()
			cp_debit.setEditable(False)
			cp_debit.setText('<span style="color: {};">{}%</span>'.format(negative_color,
																		  negative_percent))
			cp_debit.setTextAlignment(Qt.AlignRight)
			cp_debit.setData(negative_percent, Qt.UserRole)

			monthes_cols = []
			for dte in monthes:
				key = dte.strftime('%Y-%m')
				amt = 0.0
				ck = 'credit ' + key
				dk = 'debit ' + key
				if ck in v.keys():
					amt += v[ck]
				if dk in v.keys():
					amt += -v[dk]
				c_month = QStandardItem()
				c_month.setEditable(False)
				c_month.setText('<span style="color: {};">{}</span>'.format(negative_color if amt < 0 else positive_color,
																			libs.currencies.formatCurrency(amt,
																										   act.alpha_3)))
				c_month.setTextAlignment(Qt.AlignRight)
				c_month.setData(amt, Qt.UserRole)
				monthes_cols.append(c_month)

			if type(v['childs']) == dict:
				for kk,vv in v['childs'].items():
					s = QStandardItem()
					s.setText('<span style="color: {}">{}</span> <span><small>({})</small></span>'.format(html,
																										  funcs.tr(kk),
																										  vv['count']))
					s.setEditable(False)
					s.setData(kk, Qt.UserRole)

					sv_credit = QStandardItem()
					sv_credit.setEditable(False)
					sv_credit.setText('<span style="color: {};">{}</span>'.format(positive_color,
																				  libs.currencies.formatCurrency(vv['credit total'],
																												 act.alpha_3)))
					sv_credit.setTextAlignment(Qt.AlignRight)
					sv_credit.setData(vv['credit total'], Qt.UserRole)
					positive_percent = round((vv['credit total'] * 100) / v['credit total'], 2) if v['credit total'] != 0 else 0.0
					sp_credit = QStandardItem()
					sp_credit.setEditable(False)
					sp_credit.setText('<span style="color: {};"><small>{}%</small></span>'.format(positive_color,
																								  positive_percent))
					sp_credit.setTextAlignment(Qt.AlignRight)
					sp_credit.setData(positive_percent, Qt.UserRole)

					sv_debit = QStandardItem()
					sv_debit.setEditable(False)
					sv_debit.setText('<span style="color: {};">{}</span>'.format(negative_color,
																				 libs.currencies.formatCurrency(-vv['debit total'],
																												act.alpha_3)))
					sv_debit.setTextAlignment(Qt.AlignRight)
					sv_debit.setData(-vv['debit total'], Qt.UserRole)
					negative_percent = round((vv['debit total'] * 100) / v['debit total'], 2) if v['debit total'] != 0 else 0.0
					sp_debit = QStandardItem()
					sp_debit.setEditable(False)
					sp_debit.setText('<span style="color: {};"><small>{}%</small></span>'.format(negative_color,
																								 negative_percent))
					sp_debit.setTextAlignment(Qt.AlignRight)
					sp_debit.setData(negative_percent, Qt.UserRole)

					smonthes_cols = []
					for dte in monthes:
						key = dte.strftime('%Y-%m')
						amt = 0.0
						ck = 'credit ' + key
						dk = 'debit ' + key
						if ck in vv.keys():
							amt += vv[ck]
						if dk in vv.keys():
							amt += -vv[dk]
						s_month = QStandardItem()
						s_month.setEditable(False)
						s_month.setText('<span style="color: {};">{}</span>'.format(negative_color if amt < 0 else positive_color,
																					libs.currencies.formatCurrency(amt,
																												   act.alpha_3)))
						s_month.setTextAlignment(Qt.AlignRight)
						s_month.setData(amt, Qt.UserRole)
						smonthes_cols.append(s_month)

					c.appendRow([s, sv_credit, sp_credit, sv_debit, sp_debit] + smonthes_cols)

			root.appendRow([c, cv_credit, cp_credit, cv_debit, cp_debit] + monthes_cols)

		m.appendRow([root, rootv_credit, rootp_credit, rootv_debit, rootp_debit] + rmonthes_cols)

		# mise en forme
		self.opeTrfList.setModel(m)
		self.opeTrfList.setItemDelegate(HTMLDelegate(parent=None, settings=self._settings))
		for i in range(self.opeTrfList.model().rowCount()):
			self.opeTrfList.setExpanded(self.opeTrfList.model().index(i, 0), True)

		# redimenssionement des colones
		self.opeTrfList.header().resizeSection(0, 250)
		self.opeTrfList.header().resizeSection(1, 100)
		self.opeTrfList.header().resizeSection(2, 70)
		self.opeTrfList.header().resizeSection(3, 100)
		self.opeTrfList.header().resizeSection(4, 70)

		# et pour finir, trie par catégorie
		self.opeTrfList.model().setSortRole(Qt.UserRole)
		self.opeTrfList.sortByColumn(0, Qt.AscendingOrder)
		self.opeTrfList.model().sort(0, Qt.AscendingOrder)

		# parce que les pgraphiques c'est beau, alors on en créé un, affichant la répartition par catégories
		if len(monthes) > 0:
			self.createCategoriesGraph(act, monthes[0], monthes[-1], monthes, items)
		else:
			self.clearGraphics()
		del items
		del monthes

		self.setUpdatesEnabled(True)
		QApplication.restoreOverrideCursor()

	def createThirdpartiesGraph(self, act:account, first_date:date, last_date:date, monthes, items):
		axis = {}
		for k,v in items['list'].items():
			amt = v['credit total'] + -v['debit total']
			axis[k] = amt
		axis_keys = sorted(axis, key=axis.get, reverse=True)
		axis = {k:axis[k] for k in axis_keys}

		color_negative_amount = self._settings.value('color_negative_amount')
		color_positive_amount = self._settings.value('color_positive_amount')
		brushes = []
		for amt in list(axis.values()):
			c = QColor(color_negative_amount) if amt < 0 else QColor(color_positive_amount)
			brushes.append(QBrush(pg.mkColor((c.red(), c.green(), c.blue(), 50))))

		self.clearGraphics()
		gl = self.makeLayout()

		hg = HBarGraph(datas=axis,
					   brushes=brushes,
					   labels={'bottom':{'text':funcs.tr("Montants ({})").format(currency.symbol(act.alpha_3)),'units':''},
							   'left':{'text':'','units':''}})
		hg.tooltipCallback = (lambda value: '{}'.format(libs.currencies.formatCurrency(value, act.alpha_3)))
		self.addGraphics(gl,
						 hg,
						 funcs.tr("Part de chaque <b>tiers</b> en {}").format(currency.symbol(act.alpha_3)),
						 row=0)

		self.makeGraphics(gl)

	def populateThirdparties(self):
		QApplication.setOverrideCursor(Qt.WaitCursor)
		self.setUpdatesEnabled(False)

		if not(self.opeTrfList.model() is None):
			self.opeTrfList.model().clear()
		self.opeTrfList.setModel(None)

		# on recherche le compte associé à l'Id sélectionné
		actid = self.filterAccount.currentData()
		act = None
		for a in self._fi.accounts:
			if a.id == actid:
				act = a
				break
		if act is None:
			self.setUpdatesEnabled(True)
			QApplication.restoreOverrideCursor()
			return

		items = {'count': 0, 'debit total': 0.0, 'credit total': 0.0, 'list': {}}
		for tp in self._fi.thirdparties:
			items['list'][tp.title] = {'count': 0, 'debit total': 0.0, 'credit total': 0.0}

		monthes = []
		for ope in act.operations:
			if self.applyFilterOpe(act, ope):
				if not(ope.to in items['list'].keys()):
					items['list'][ope.to] = {'count': 0, 'debit total': 0.0, 'credit total': 0.0}
				if not(funcs.first_day_of_month(ope.fromdate) in monthes):
					monthes.append(funcs.first_day_of_month(ope.fromdate))
				items['list'][ope.to]['count'] += 1
				items['count'] += 1
				kc = 'credit ' + ope.fromdate.strftime('%Y-%m')
				if not(kc in items['list'][ope.to]):
					items['list'][ope.to][kc] = 0.0
				if not(kc in items):
					items[kc] = 0.0
				kd = 'debit ' + ope.fromdate.strftime('%Y-%m')
				if not(kd in items['list'][ope.to]):
					items['list'][ope.to][kd] = 0.0
				if not(kd in items):
					items[kd] = 0.0
				amt = abs(ope.amount)
				if ope.amount < 0:
					items['list'][ope.to]['debit total'] += amt
					items['debit total'] += amt
					items['list'][ope.to][kd] += amt
					items[kd] += amt
				else:
					items['list'][ope.to]['credit total'] += amt
					items['credit total'] += amt
					items['list'][ope.to][kc] += amt
					items[kc] += amt

		# préparation de la liste
		m = QStandardItemModel()
		m.setColumnCount(5 + len(monthes))
		m.setHeaderData(0, QtCore.Qt.Horizontal, funcs.tr("Tiers"))
		m.setHeaderData(1, QtCore.Qt.Horizontal, funcs.tr("Revenus"))
		m.horizontalHeaderItem(1).setTextAlignment(Qt.AlignRight)
		m.setHeaderData(2, QtCore.Qt.Horizontal, funcs.tr("%"))
		m.horizontalHeaderItem(2).setTextAlignment(Qt.AlignRight)
		m.setHeaderData(3, QtCore.Qt.Horizontal, funcs.tr("Dépenses"))
		m.horizontalHeaderItem(3).setTextAlignment(Qt.AlignRight)
		m.setHeaderData(4, QtCore.Qt.Horizontal, funcs.tr("%"))
		m.horizontalHeaderItem(4).setTextAlignment(Qt.AlignRight)
		i = 5
		for dte in monthes:
			m.setHeaderData(i, QtCore.Qt.Horizontal, funcs.tr(dte.strftime('%Y %b')))
			m.horizontalHeaderItem(i).setTextAlignment(Qt.AlignRight)
			i += 1

		# affichage du contenu de la liste hierarchisée
		positive_color = self._settings.value('color_positive_amount')
		negative_color = self._settings.value('color_negative_amount')

		root = QStandardItem()
		root.setText('<span><b>{}</b></span> <span><small>({})</small></span>'.format(funcs.tr("Tous les tiers"),
																			   items['count']))
		root.setEditable(False)
		root.setData([root.text(), items], Qt.UserRole)

		rootv_credit = QStandardItem()
		rootv_credit.setEditable(False)
		rootv_credit.setText('<span style="color: {};">{}</span>'.format(positive_color,
																		 libs.currencies.formatCurrency(items['credit total'],
																										act.alpha_3)))
		rootv_credit.setTextAlignment(Qt.AlignRight)
		rootv_credit.setData(items['credit total'], Qt.UserRole)
		positive_percent = round(100.00, 2)
		rootp_credit = QStandardItem()
		rootp_credit.setEditable(False)
		rootp_credit.setText('<span style="color: {};">{}%</span>'.format(positive_color,
																		  positive_percent))
		rootp_credit.setTextAlignment(Qt.AlignRight)
		rootp_credit.setData(positive_percent, Qt.UserRole)

		rootv_debit = QStandardItem()
		rootv_debit.setEditable(False)
		rootv_debit.setText('<span style="color: {};">{}</span>'.format(negative_color,
																		libs.currencies.formatCurrency(-items['debit total'],
																									   act.alpha_3)))
		rootv_debit.setTextAlignment(Qt.AlignRight)
		rootv_debit.setData(-items['debit total'], Qt.UserRole)
		negative_percent = round(100.00, 2)
		rootp_debit = QStandardItem()
		rootp_debit.setEditable(False)
		rootp_debit.setText('<span style="color: {};">{}%</span>'.format(negative_color,
																		 negative_percent))
		rootp_debit.setTextAlignment(Qt.AlignRight)
		rootp_debit.setData(negative_percent, Qt.UserRole)

		rmonthes_cols = []
		for dte in monthes:
			key = dte.strftime('%Y-%m')
			amt = 0.0
			ck = 'credit ' + key
			dk = 'debit ' + key
			if ck in items.keys():
				amt += items[ck]
			if dk in items.keys():
				amt += -items[dk]
			r_month = QStandardItem()
			r_month.setEditable(False)
			r_month.setText('<span style="color: {};">{}</span>'.format(negative_color if amt < 0 else positive_color,
																		libs.currencies.formatCurrency(amt, act.alpha_3)))
			r_month.setTextAlignment(Qt.AlignRight)
			r_month.setData(amt, Qt.UserRole)
			rmonthes_cols.append(r_month)

		for k,v in items['list'].items():
			s = QStandardItem()
			s.setText('<span>{}</span> <span><small>({})</small></span>'.format(funcs.tr(k),
																				v['count']))
			s.setEditable(False)
			s.setData(k, Qt.UserRole)

			sv_credit = QStandardItem()
			sv_credit.setEditable(False)
			sv_credit.setText('<span style="color: {};">{}</span>'.format(positive_color,
																		  libs.currencies.formatCurrency(v['credit total'],
																										 act.alpha_3)))
			sv_credit.setTextAlignment(Qt.AlignRight)
			sv_credit.setData(v['credit total'], Qt.UserRole)
			positive_percent = round((v['credit total'] * 100) / v['credit total'], 2) if v['credit total'] != 0 else 0.0
			sp_credit = QStandardItem()
			sp_credit.setEditable(False)
			sp_credit.setText('<span style="color: {};"><small>{}%</small></span>'.format(positive_color,
																						  positive_percent))
			sp_credit.setTextAlignment(Qt.AlignRight)
			sp_credit.setData(positive_percent, Qt.UserRole)

			sv_debit = QStandardItem()
			sv_debit.setEditable(False)
			sv_debit.setText('<span style="color: {};">{}</span>'.format(negative_color,
																		 libs.currencies.formatCurrency(-v['debit total'],
																										act.alpha_3)))
			sv_debit.setTextAlignment(Qt.AlignRight)
			sv_debit.setData(-v['debit total'], Qt.UserRole)
			negative_percent = round((v['debit total'] * 100) / v['debit total'], 2) if v['debit total'] != 0 else 0.0
			sp_debit = QStandardItem()
			sp_debit.setEditable(False)
			sp_debit.setText('<span style="color: {};"><small>{}%</small></span>'.format(negative_color,
																						 negative_percent))
			sp_debit.setTextAlignment(Qt.AlignRight)
			sp_debit.setData(negative_percent, Qt.UserRole)

			smonthes_cols = []
			for dte in monthes:
				key = dte.strftime('%Y-%m')
				amt = 0.0
				ck = 'credit ' + key
				dk = 'debit ' + key
				if ck in v.keys():
					amt += v[ck]
				if dk in v.keys():
					amt += -v[dk]
				s_month = QStandardItem()
				s_month.setEditable(False)
				s_month.setText('<span style="color: {};">{}</span>'.format(negative_color if amt < 0 else positive_color,
																			libs.currencies.formatCurrency(amt,
																										   act.alpha_3)))
				s_month.setTextAlignment(Qt.AlignRight)
				s_month.setData(amt, Qt.UserRole)
				smonthes_cols.append(s_month)

			root.appendRow([s, sv_credit, sp_credit, sv_debit, sp_debit] + smonthes_cols)

		m.appendRow([root, rootv_credit, rootp_credit, rootv_debit, rootp_debit] + rmonthes_cols)

		# mise en forme
		self.opeTrfList.setModel(m)
		self.opeTrfList.setItemDelegate(HTMLDelegate(parent=None, settings=self._settings))
		for i in range(self.opeTrfList.model().rowCount()):
			self.opeTrfList.setExpanded(self.opeTrfList.model().index(i, 0), True)

		# redimenssionement des colones
		self.opeTrfList.header().resizeSection(0, 300)
		self.opeTrfList.header().resizeSection(1, 100)
		self.opeTrfList.header().resizeSection(2, 70)
		self.opeTrfList.header().resizeSection(3, 100)
		self.opeTrfList.header().resizeSection(4, 70)

		# et pour finir, trie par catégorie
		self.opeTrfList.model().setSortRole(Qt.UserRole)
		self.opeTrfList.sortByColumn(0, Qt.AscendingOrder)
		self.opeTrfList.model().sort(0, Qt.AscendingOrder)

		# parce que les pgraphiques c'est beau, alors on en créé un, affichant la répartition par catégories
		if len(monthes) > 0:
			self.createThirdpartiesGraph(act, monthes[0], monthes[-1], monthes, items)
		else:
			self.clearGraphics()
		del items
		del monthes

		self.setUpdatesEnabled(True)
		QApplication.restoreOverrideCursor()

	def createPaytypesGraph(self, act:account, first_date:date, last_date:date, monthes, items):
		self.clearGraphics()
		gl = self.makeLayout()

		datas_credit = {}
		brushes_credit = []
		datas_debit = {}
		brushes_debit = []
		graphs = []
		for k,v in items['list'].items():
			color, chtml = funcs.text2color(k)
			c = QColor(chtml)
			grad = QRadialGradient(0.5, 0.5, 1)
			grad.setCoordinateMode(QGradient.ObjectBoundingMode)
			grad.setColorAt(0.1, pg.mkColor((c.red(), c.green(), c.blue(), 100)))
			grad.setColorAt(0.9, pg.mkColor((c.red(), c.green(), c.blue(), 255)))

			if v['credit total'] > 0:
				if not(k in datas_credit.keys()):
					percent_credit = (v['credit total'] * 100) / items['credit total'] if items['credit total'] != 0 else 0
					datas_credit[k] = percent_credit
					brushes_credit.append(QBrush(grad))
			if v['debit total'] > 0:
				if not(k in datas_debit.keys()):
					percent_debit = (v['debit total'] * 100) / items['debit total'] if items['debit total'] != 0 else 0
					datas_debit[k] = percent_debit
					brushes_debit.append(QBrush(grad))

			_axis = {}
			_brushes = []
			for dte in monthes:
				key = dte.strftime('%Y-%m')
				amt = 0.0
				ck = 'credit ' + key
				dk = 'debit ' + key
				if ck in v.keys():
					amt += v[ck]
				if dk in v.keys():
					amt += -v[dk]
				_axis[dte.strftime('%Y %b')] = amt
				grad = QLinearGradient(0, 0, 0, 1)
				grad.setCoordinateMode(QGradient.ObjectBoundingMode)
				if amt >= 0:
					grad.setColorAt(0.1, pg.mkColor((c.red(), c.green(), c.blue(), 100)))
					grad.setColorAt(0.9, pg.mkColor((c.red(), c.green(), c.blue(), 255)))
				else:
					grad.setColorAt(0.1, pg.mkColor((c.red(), c.green(), c.blue(), 255)))
					grad.setColorAt(0.9, pg.mkColor((c.red(), c.green(), c.blue(), 100)))
				_brushes.append(QBrush(grad))
			graphs.append({'title':k, 'axis':_axis, 'brushes':_brushes})

		pie_credit = PieGraph(datas_credit, brushes_credit)
		self.addGraphics(gl,
						 pie_credit,
						 funcs.tr("Classement par <b>revenus</b> en %"),
						 row=0, col=0, colspan=1)

		pie_debit = PieGraph(datas_debit, brushes_debit)
		self.addGraphics(gl,
						 pie_debit,
						 funcs.tr("Classement par <b>dépenses</b> en %"),
						 row=0, col=1, colspan=1)

		row = 2
		for item in graphs:
			vg = VBarGraph(datas=item['axis'],
						   brushes=item['brushes'],
						   labels={'left':{'text':funcs.tr("Montants ({})").format(currency.symbol(act.alpha_3)),'units':''},
								   'bottom':{'text':'','units':''}},
						   numBars=10)
			vg.tooltipCallback = (lambda value: '{}'.format(libs.currencies.formatCurrency(value, act.alpha_3)))
			self.addHLine(gl, row)
			row += 1
			self.addGraphics(gl,
							 vg,
							 '<b>{}</b>'.format(funcs.tr(item['title'])),
							 row=row, col=0, colspan=2)
			row += 2

		self.makeGraphics(gl)

	def populatePaytypes(self):
		QApplication.setOverrideCursor(Qt.WaitCursor)
		self.setUpdatesEnabled(False)

		if not(self.opeTrfList.model() is None):
			self.opeTrfList.model().clear()
		self.opeTrfList.setModel(None)

		# on recherche le compte associé à l'Id sélectionné
		actid = self.filterAccount.currentData()
		act = None
		for a in self._fi.accounts:
			if a.id == actid:
				act = a
				break
		if act is None:
			self.setUpdatesEnabled(True)
			QApplication.restoreOverrideCursor()
			return

		items = {'count': 0, 'debit total': 0.0, 'credit total': 0.0, 'list': {}}
		for pt in self._fi.paytypes:
			items['list'][pt] = {'count': 0, 'debit total': 0.0, 'credit total': 0.0}

		monthes = []
		for ope in act.operations:
			if self.applyFilterOpe(act, ope):
				if not(ope.paytype in items['list'].keys()):
					items['list'][ope.paytype] = {'count': 0, 'debit total': 0.0, 'credit total': 0.0}
				if not(funcs.first_day_of_month(ope.fromdate) in monthes):
					monthes.append(funcs.first_day_of_month(ope.fromdate))
				items['list'][ope.paytype]['count'] += 1
				items['count'] += 1
				kc = 'credit ' + ope.fromdate.strftime('%Y-%m')
				if not(kc in items['list'][ope.paytype]):
					items['list'][ope.paytype][kc] = 0.0
				if not(kc in items):
					items[kc] = 0.0
				kd = 'debit ' + ope.fromdate.strftime('%Y-%m')
				if not(kd in items['list'][ope.paytype]):
					items['list'][ope.paytype][kd] = 0.0
				if not(kd in items):
					items[kd] = 0.0
				amt = abs(ope.amount)
				if ope.amount < 0:
					items['list'][ope.paytype]['debit total'] += amt
					items['debit total'] += amt
					items['list'][ope.paytype][kd] += amt
					items[kd] += amt
				else:
					items['list'][ope.paytype]['credit total'] += amt
					items['credit total'] += amt
					items['list'][ope.paytype][kc] += amt
					items[kc] += amt

		for trf in self._fi.transfers:
			if trf.fromactid == actid or trf.toactid == actid:
				if self.applyFilterTrf(act, trf):
					tpe = 'Transfert'
					if not(tpe in items['list'].keys()):
						items['list'][tpe] = {'count': 0, 'debit total': 0.0, 'credit total': 0.0}
					if not(funcs.first_day_of_month(trf.fromdate) in monthes):
						monthes.append(funcs.first_day_of_month(trf.fromdate))
					items['list'][tpe]['count'] += 1
					items['count'] += 1
					kc = 'credit ' + trf.fromdate.strftime('%Y-%m')
					if not(kc in items['list'][tpe]):
						items['list'][tpe][kc] = 0.0
					if not(kc in items):
						items[kc] = 0.0
					kd = 'debit ' + trf.fromdate.strftime('%Y-%m')
					if not(kd in items['list'][tpe]):
						items['list'][tpe][kd] = 0.0
					if not(kd in items):
						items[kd] = 0.0
					amt = abs(trf.amount)
					if trf.amount < 0:
						items['list'][tpe]['debit total'] += amt
						items['debit total'] += amt
						items['list'][tpe][kd] += amt
						items[kd] += amt
					else:
						items['list'][tpe]['credit total'] += amt
						items['credit total'] += amt
						items['list'][tpe][kc] += amt
						items[kc] += amt

		# préparation de la liste
		m = QStandardItemModel()
		m.setColumnCount(5 + len(monthes))
		m.setHeaderData(0, QtCore.Qt.Horizontal, funcs.tr("Moyen de paiement"))
		m.setHeaderData(1, QtCore.Qt.Horizontal, funcs.tr("Revenus"))
		m.horizontalHeaderItem(1).setTextAlignment(Qt.AlignRight)
		m.setHeaderData(2, QtCore.Qt.Horizontal, funcs.tr("%"))
		m.horizontalHeaderItem(2).setTextAlignment(Qt.AlignRight)
		m.setHeaderData(3, QtCore.Qt.Horizontal, funcs.tr("Dépenses"))
		m.horizontalHeaderItem(3).setTextAlignment(Qt.AlignRight)
		m.setHeaderData(4, QtCore.Qt.Horizontal, funcs.tr("%"))
		m.horizontalHeaderItem(4).setTextAlignment(Qt.AlignRight)
		i = 5
		for dte in monthes:
			m.setHeaderData(i, QtCore.Qt.Horizontal, funcs.tr(dte.strftime('%Y %b')))
			m.horizontalHeaderItem(i).setTextAlignment(Qt.AlignRight)
			i += 1

		# affichage du contenu de la liste hierarchisée
		positive_color = self._settings.value('color_positive_amount')
		negative_color = self._settings.value('color_negative_amount')

		root = QStandardItem()
		root.setText('<span><b>{}</b></span> <span><small>({})</small></span>'.format(funcs.tr("Tous les moyens de paiements"),
																						  items['count']))
		root.setEditable(False)
		root.setData([root.text(), items], Qt.UserRole)

		rootv_credit = QStandardItem()
		rootv_credit.setEditable(False)
		rootv_credit.setText('<span style="color: {};">{}</span>'.format(positive_color,
																			 libs.currencies.formatCurrency(items['credit total'],
																											act.alpha_3)))
		rootv_credit.setTextAlignment(Qt.AlignRight)
		rootv_credit.setData(items['credit total'], Qt.UserRole)
		positive_percent = round(100.00, 2)
		rootp_credit = QStandardItem()
		rootp_credit.setEditable(False)
		rootp_credit.setText('<span style="color: {};">{}%</span>'.format(positive_color,
																			  positive_percent))
		rootp_credit.setTextAlignment(Qt.AlignRight)
		rootp_credit.setData(positive_percent, Qt.UserRole)

		rootv_debit = QStandardItem()
		rootv_debit.setEditable(False)
		rootv_debit.setText('<span style="color: {};">{}</span>'.format(negative_color,
																			libs.currencies.formatCurrency(-items['debit total'],
																										   act.alpha_3)))
		rootv_debit.setTextAlignment(Qt.AlignRight)
		rootv_debit.setData(-items['debit total'], Qt.UserRole)
		negative_percent = round(100.00, 2)
		rootp_debit = QStandardItem()
		rootp_debit.setEditable(False)
		rootp_debit.setText('<span style="color: {};">{}%</span>'.format(negative_color,
																			 negative_percent))
		rootp_debit.setTextAlignment(Qt.AlignRight)
		rootp_debit.setData(negative_percent, Qt.UserRole)

		rmonthes_cols = []
		for dte in monthes:
			key = dte.strftime('%Y-%m')
			amt = 0.0
			ck = 'credit ' + key
			dk = 'debit ' + key
			if ck in items.keys():
				amt += items[ck]
			if dk in items.keys():
				amt += -items[dk]
			r_month = QStandardItem()
			r_month.setEditable(False)
			r_month.setText('<span style="color: {};">{}</span>'.format(negative_color if amt < 0 else positive_color,
																			libs.currencies.formatCurrency(amt, act.alpha_3)))
			r_month.setTextAlignment(Qt.AlignRight)
			r_month.setData(amt, Qt.UserRole)
			rmonthes_cols.append(r_month)

		for k,v in items['list'].items():
			s = QStandardItem()
			color, chtml = funcs.text2color(k)
			s.setText('<span style="color: {};">{}</span> <span><small>({})</small></span>'.format(chtml,
																								   funcs.tr(k),
																								   v['count']))
			s.setEditable(False)
			s.setData(k, Qt.UserRole)

			sv_credit = QStandardItem()
			sv_credit.setEditable(False)
			sv_credit.setText('<span style="color: {};">{}</span>'.format(positive_color,
																		  libs.currencies.formatCurrency(v['credit total'],
																										 act.alpha_3)))
			sv_credit.setTextAlignment(Qt.AlignRight)
			sv_credit.setData(v['credit total'], Qt.UserRole)
			positive_percent = round((v['credit total'] * 100) / items['credit total'], 2) if v['credit total'] != 0 else 0.0
			sp_credit = QStandardItem()
			sp_credit.setEditable(False)
			sp_credit.setText('<span style="color: {};"><small>{}%</small></span>'.format(positive_color,
																						  positive_percent))
			sp_credit.setTextAlignment(Qt.AlignRight)
			sp_credit.setData(positive_percent, Qt.UserRole)

			sv_debit = QStandardItem()
			sv_debit.setEditable(False)
			sv_debit.setText('<span style="color: {};">{}</span>'.format(negative_color,
																		 libs.currencies.formatCurrency(-v['debit total'],
																										act.alpha_3)))
			sv_debit.setTextAlignment(Qt.AlignRight)
			sv_debit.setData(-v['debit total'], Qt.UserRole)
			negative_percent = round((v['debit total'] * 100) / items['debit total'], 2) if v['debit total'] != 0 else 0.0
			sp_debit = QStandardItem()
			sp_debit.setEditable(False)
			sp_debit.setText('<span style="color: {};"><small>{}%</small></span>'.format(negative_color,
																						 negative_percent))
			sp_debit.setTextAlignment(Qt.AlignRight)
			sp_debit.setData(negative_percent, Qt.UserRole)

			smonthes_cols = []
			for dte in monthes:
				key = dte.strftime('%Y-%m')
				amt = 0.0
				ck = 'credit ' + key
				dk = 'debit ' + key
				if ck in v.keys():
					amt += v[ck]
				if dk in v.keys():
					amt += -v[dk]
				s_month = QStandardItem()
				s_month.setEditable(False)
				s_month.setText('<span style="color: {};">{}</span>'.format(negative_color if amt < 0 else positive_color,
																			libs.currencies.formatCurrency(amt,
																										   act.alpha_3)))
				s_month.setTextAlignment(Qt.AlignRight)
				s_month.setData(amt, Qt.UserRole)
				smonthes_cols.append(s_month)

			root.appendRow([s, sv_credit, sp_credit, sv_debit, sp_debit] + smonthes_cols)

		m.appendRow([root, rootv_credit, rootp_credit, rootv_debit, rootp_debit] + rmonthes_cols)

		# mise en forme
		self.opeTrfList.setModel(m)
		self.opeTrfList.setItemDelegate(HTMLDelegate(parent=None, settings=self._settings))
		for i in range(self.opeTrfList.model().rowCount()):
			self.opeTrfList.setExpanded(self.opeTrfList.model().index(i, 0), True)

		# redimenssionement des colones
		self.opeTrfList.header().resizeSection(0, 300)
		self.opeTrfList.header().resizeSection(1, 100)
		self.opeTrfList.header().resizeSection(2, 70)
		self.opeTrfList.header().resizeSection(3, 100)
		self.opeTrfList.header().resizeSection(4, 70)

		# et pour finir, trie par catégorie
		self.opeTrfList.model().setSortRole(Qt.UserRole)
		self.opeTrfList.sortByColumn(0, Qt.AscendingOrder)
		self.opeTrfList.model().sort(0, Qt.AscendingOrder)

		# parce que les pgraphiques c'est beau, alors on en créé un, affichant la répartition par catégories
		if len(monthes) > 0:
			self.createPaytypesGraph(act, monthes[0], monthes[-1], monthes, items)
		else:
			self.clearGraphics()
		del items
		del monthes

		self.setUpdatesEnabled(True)
		QApplication.restoreOverrideCursor()