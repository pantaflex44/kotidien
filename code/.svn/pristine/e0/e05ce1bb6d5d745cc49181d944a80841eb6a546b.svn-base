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
import math

from PyQt5 import QtCore, QtWidgets, QtGui, uic
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *

from pyqtgraph import PlotWidget, plot
import pyqtgraph as pg

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

class PieGraph(QGraphicsView):
	
	_background = '#fff'
	
	def __init__(self,
				 datas:dict={},
				 brushes='#D6D300',
				 width:int=250,
				 height:int=250,
				 minHeight:int=250,
				 maxHeight:int=16777215,
				 background:str='#fff'):
		self._background = background
		
		scn = QGraphicsScene()
		if len(datas) > 0:
			mx = max(list(datas.values()))
			if mx > 100:
				diff = (mx - 100) / len(datas)
				datas = {k:(v - diff) for k,v in datas.items()}
				
			if type(brushes) == str:
				brushes = [QBrush(QColor(brushes)) for i in range(len(datas))]
			else:
				if type(brushes) != list:
					brushes = []
				if len(brushes) != len(datas):
					brushes = [QBrush(QColor('#D6D300')) for i in range(len(datas))]	
					
			if width < 0:
				width = 0
			if height < minHeight:
				height = minHeight
			if height > maxHeight:
				height = maxHeight
	
			start_angle = 0
			i = 0
			for k,v in datas.items():
				if v <= 0:
					continue
				pie = (v * 360) / 100
				
				g = QGraphicsEllipseItemEx(0, 0, width, height)
				g.toolTip = '<b>{}</b><br />{}%'.format(k, round(v, 2))
				g.setStartAngle(start_angle * 16)
				g.setSpanAngle(pie * 16)
				g.setBrush(brushes[i])
				g.setPen(QPen(QColor(self._background)))
				scn.addItem(g)			
				
				a = start_angle + (pie / 2)
				x = (math.cos(math.radians(a)) * (width / 2)) + (width / 2)
				y = (math.sin(math.radians(360 - a)) * (height / 2)) + (height / 2)
				ff = QApplication.font()
				ff.setPointSize(6)
				t = QGraphicsTextItem(k)
				t.setFont(ff)
				fm = QFontMetrics(ff)
				w = fm.width(k)
				h = fm.height() * 2
				if a > 90 and a < 270:
					x = x - w - 10
				if a >= 0 and a < 180:
					y = y - h
				else:
					y -= 5
				t.setPos(x, y + 5)
				scn.addItem(t)
				
				start_angle += pie		
				i += 1
			
		super(PieGraph, self).__init__(scn)
		self.setMinimumHeight(height + int(height / 2))
		self.setMinimumWidth(width + int(width / 2))
		self.setFrameShape(QFrame.NoFrame)
		self.setBackgroundBrush(QBrush(QColor(self._background)))		
		