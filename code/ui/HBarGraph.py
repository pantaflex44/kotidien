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

from pyqtgraph import PlotWidget, plot
import pyqtgraph as pg

class HBarGraph(PlotWidget):

	_axis = {}
	
	tooltipCallback = None
	
	def __init__(self, parent=None, datas:dict={}, brushes='#D6D300', labels:dict={'left':{'text':'','units':''},'bottom':{'text':'','units':''}}, minHeight:int=250, maxHeight:int=16777215, background:str='#fff', **kwargs):
		f = QApplication.font()
		f.setPointSize(8)
		
		self._axis = datas
		axis_x = list(datas.values())
		axis_y = list(datas.keys())
		axis_y_dict = dict(enumerate(axis_y))
		
		stringaxis = pg.AxisItem(orientation='left')
		stringaxis.setTickFont(f)
		stringaxis.setTicks([axis_y_dict.items()])		
		
		plotItem = None
		height = len(axis_y) * 20
		if height < minHeight:
			height = minHeight	
		if height > maxHeight:
			height = maxHeight
		super(HBarGraph, self).__init__(parent, background, plotItem,
										axisItems={'left': stringaxis},
										**kwargs)
		self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
		self.setMinimumSize(0, height)
		self.setMaximumSize(16777215, height)
		self.setBackground(background)
		self.showGrid(x=True, y=True)		
		self.enableAutoRange(axis='xy')
		self.setMouseEnabled(x=False, y=False)
		self.setXRange(min(axis_x) if min(axis_x) < 0 else 0,
					   max(axis_x) if max(axis_x) > 0 else 0,
					   padding=0.05)
		self.setYRange(0, len(axis_y), padding=0.05)
		self.getAxis('left').setTickFont(f)
		styles = {'color':'#555', 'font-size':'8pt'}	
		for k,v in labels.items():
			if v['text'].strip() != '':
				self.setLabel(k, 
							  v['text'].strip(),
							  units=v['units'].strip(), 
							  **styles)
		if type(brushes) == str:
			brushes = [QBrush(QColor(brushes)) for i in range(len(axis_y))]
		else:
			if type(brushes) != list:
				brushes = []
			if len(brushes) != len(axis_y):
				brushes = [QBrush(QColor('#D6D300')) for i in range(len(axis_y))]	
			
		bars = pg.BarGraphItem(y=list(axis_y_dict.keys()),
							   x0=0,
							   height=0.6,
							   width=axis_x,
							   brushes=brushes)
		self.addItem(bars)
		
		pg.SignalProxy(self.scene().sigMouseMoved, rateLimit=60, slot=lambda evt: self.mouseMoved(evt))
		self.scene().sigMouseMoved.connect(lambda evt: self.mouseMoved(evt))
		self.setMouseTracking(True)
		self.installEventFilter(self)			
		
	def eventFilter(self, obj, event):
		if type(obj) == HBarGraph:
			if event.type() == QEvent.Leave:
				QToolTip.hideText()
		return super(HBarGraph, self).eventFilter(obj, event)	
	
	def mouseMoved(self, pos):
		if self.sceneBoundingRect().contains(pos):
			mousePoint = self.plotItem.vb.mapSceneToView(pos)
			try:
				value = mousePoint.x()
				pt = self.mapToGlobal(QPoint(pos.x(), pos.y()))
				if callable(self.tooltipCallback):
					value = self.tooltipCallback(value)
				QToolTip.showText(pt, '{}'.format(value))
			except Exception as e:
				QToolTip.hideText()
		else:
			QToolTip.hideText()			