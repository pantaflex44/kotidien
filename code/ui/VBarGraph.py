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

from PyQt5.QtCore import Qt, QPoint, QPointF, QEvent, pyqtSignal
from PyQt5.QtWidgets import QToolTip, QSizePolicy, QApplication
from PyQt5.QtGui import QPen

from pyqtgraph import PlotWidget, plot
import pyqtgraph as pg

import funcs

class VBarGraph(PlotWidget):
	
	_axis = {}
	_vline = None
	
	tooltipCallback = None
	
	def __init__(self, parent=None,
				 datas:dict={},
				 brushes='#D6D300',
				 labels:dict={'left':{'text':'','units':''},'bottom':{'text':'','units':''}},
				 height=250,
				 minHeight:int=250,
				 maxHeight:int=16777215,
				 background:str='#fff',
				 numBars:int=5,
				 **kwargs):
		f = QApplication.font()
		f.setPointSize(6)
		
		self._axis = datas
		axis_x = list(datas.keys())
		axis_y = list(datas.values())
		axis_x_dict = dict(enumerate(axis_x))
		
		stringaxis = pg.AxisItem(orientation='bottom')
		stringaxis.setTickFont(f)
		stringaxis.setTicks([axis_x_dict.items()])		
		
		plotItem = None
		if height < minHeight:
			height = minHeight	
		if height > maxHeight:
			height = maxHeight
		super(VBarGraph, self).__init__(parent, background, plotItem, axisItems={'bottom': stringaxis}, **kwargs)
		self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
		self.setMinimumSize(0, height)
		self.setMaximumSize(16777215, height)
		self.setBackground(background)
		self.showGrid(x=True, y=True)		
		self.enableAutoRange(axis='xy')
		self.setMouseEnabled(x=True, y=False)	
		self.setXRange(-0.5, numBars if len(axis_x) > (numBars + 1) else len(axis_x), padding=0.05)
		self.setYRange(min(axis_y) if min(axis_y) < 0 else 0.0, max(axis_y) if max(axis_y) > 0 else 0.0, padding=0.05)		
		self.getAxis('bottom').setTickFont(f)
		self.getAxis('bottom').setTextPen(QPen(QApplication.palette().text().color()))
		styles = {'color':'#555', 'font-size':'8pt'}		
		for k,v in labels.items():
			if v['text'].strip() != '':
				self.setLabel(k,
							  v['text'].strip(),
							  units=v['units'].strip(), 
							  **styles)
		if len(axis_x) > (numBars + 1):
			styles = {'color':'#F55', 'font-size':'6pt'}
			self.setLabel('bottom',
						  funcs.tr("Cliquer et déplacer la souris à gauche ou à droite pour faire défiler les données du graphique."),
						  units='', 
						  **styles)			
		if type(brushes) == str:
			brushes = [QBrush(QColor(brushes)) for i in range(len(axis_x))]
		else:
			if type(brushes) != list:
				brushes = []
			if len(brushes) != len(axis_x):
				brushes = [QBrush(QColor('#D6D300')) for i in range(len(axis_x))]	
				
		bars = pg.BarGraphItem(x=list(axis_x_dict.keys()),
							   height=axis_y,
							   width=0.6,
							   brushes=brushes)		
		self.addItem(bars)

		pg.SignalProxy(self.scene().sigMouseMoved, rateLimit=60, slot=lambda evt: self.mouseMoved(evt))
		self.scene().sigMouseMoved.connect(lambda evt: self.mouseMoved(evt))
		self.setMouseTracking(True)
		self.installEventFilter(self)		
		
	def eventFilter(self, obj, event):
		if type(obj) == VBarGraph:
			if event.type() == QEvent.Leave:
				QToolTip.hideText()
				if not(self._vline is None):
					obj.removeItem(self._vline)
		return super(VBarGraph, self).eventFilter(obj, event)	
	
	def mouseMoved(self, pos):
		if not(self._vline is None):
			self.removeItem(self._vline)
		if self.sceneBoundingRect().contains(pos):
			mousePoint = self.plotItem.vb.mapSceneToView(pos)
			try:
				x = round(mousePoint.x())
				if x < 0:
					x = 0
				k = x
				if k > len(self.plotItem.listDataItems()) - 1:
					k = len(self.plotItem.listDataItems()) - 1
				dataItem = self.plotItem.listDataItems()[k]
				axis_x, axis_y = dataItem.getData()
				value = axis_y[x]
				pt = self.mapToGlobal(QPoint(pos.x(), pos.y()))
				if callable(self.tooltipCallback):
					value = self.tooltipCallback(value)
				QToolTip.showText(pt, '{}'.format(value))
				self._vline = self.addLine(x=x, pen=pg.mkPen('#777', width=1, style=Qt.DashLine))	
			except Exception as e:
				QToolTip.hideText()
		else:
			QToolTip.hideText()			