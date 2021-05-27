#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
@package Kotidien
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

import locale
import currency


def formatCurrency(value: float = 0.0, alpha_3: str = 'EUR'):
    cursymb = currency.symbol(alpha_3)
    return cursymb + ' ' + locale.format('%.2f', value, grouping=True)
