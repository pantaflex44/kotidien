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

# dépend des modules python suivants
import inspect
import types
import json
from json import JSONEncoder, JSONDecoder
import re
import os
import shutil
from datetime import datetime, date
import csv
from decimal import Decimal
import xml.etree.ElementTree as ET

# dépend des modules externes suivants
# pip3 install python-dateutil
import dateutil.parser
from dateutil import tz
from dateutil.relativedelta import relativedelta
# pip3 install nh-currency
import currency
# pip3 install fpdf2
from fpdf import FPDF
# pip3 install ofxtools
from ofxtools.models import *
from ofxtools.utils import UTC
from ofxtools.header import make_header

import libs.crypto
import funcs
import appinfos

__author__ = appinfos.app_author
__mail__ = appinfos.app_mail
__copyright__ = appinfos.app_copyright
__licence__ = appinfos.app_licence
__version__ = '0.1.8'  # version de la structure de données de Kotidien

# expressions régulières servant de masques pour détecter Iban, BIC, Numéro de carte de crédit, Numéro CVV
ibanmask = "^(?:(?:IT|SM)\d{2}[A-Z]\d{22}|CY\d{2}[A-Z]\d{23}|NL\d{2}[A-Z]{4}\d{10}|LV\d{2}[A-Z]{4}\d{13}|(?:BG|BH|GB|IE)\d{2}[A-Z]{4}\d{14}|GI\d{2}[A-Z]{4}\d{15}|RO\d{2}[A-Z]{4}\d{16}|KW\d{2}[A-Z]{4}\d{22}|MT\d{2}[A-Z]{4}\d{23}|NO\d{13}|(?:DK|FI|GL|FO)\d{16}|MK\d{17}|(?:AT|EE|KZ|LU|XK)\d{18}|(?:BA|HR|LI|CH|CR)\d{19}|(?:GE|DE|LT|ME|RS)\d{20}|IL\d{21}|(?:AD|CZ|ES|MD|SA)\d{22}|PT\d{23}|(?:BE|IS)\d{24}|(?:FR|MR|MC)\d{25}|(?:AL|DO|LB|PL)\d{26}|(?:AZ|HU)\d{27}|(?:GR|MU)\d{28})$"
bicmask = "^{6}[a-z]{2}[0-9a-z]{2}([0-9a-z]{4})?\z"
cardmask = "^(?:4[0-9]{12}(?:[0-9]{3})?|(?:5[1-5][0-9]{2}|222[1-9]|22[3-9][0-9]|2[3-6][0-9]{2}|27[01][0-9]|2720)[0-9]{12}|3[47][0-9]{13}|3(?:0[0-5]|[68][0-9])[0-9]{11}|6(?:011|5[0-9]{2})[0-9]{12}|(?:2131|1800|35\d{3})\d{11})$"
cvvmask = "^[0-9]{3,4}$"

# moyens de paiements par défaut
default_paytypes = ['Carte de crédit','Chèque','Prélèvement',
                    'Virement ponctuel','Virement permanent','Transfert',
                    'Espèces','Frais','Dépot','Transaction diverse']

# catégories par défaut
default_categories = {'Abonnements':['TV','Internet','Téléphonie'],
                      'Véhicules':['Carburant','Assurance','Entretien','Parking'],
                      'Maison':['Loyer','Assurance','Electricité','Eau','Gaz','Courses','Participation'],
                      'Revenus':['Salaire','Accompte','Don','Rembourssement','Congés payés'],
                      'Taxes':['Amende','Impots'],
                      'Divers':['Crédit','Frais','Rembourssement','Don','Pret'],
                      'Santé':['Examen','Médecin','Pharmacie'],
                      'Autre':[]}



class DateTimeDecoder(json.JSONDecoder):
    """
    décodeur JSON sur mesure pour formatter les dates
    """

    def __init__(self, *args, **kargs):
        JSONDecoder.__init__(self, object_hook=self.dict_to_object,
                             *args, **kargs)

    def dict_to_object(self, d):
        if '__type__' not in d:
            return d

        type = d.pop('__type__')
        try:
            if type == 'datetime':
                return datetime(**d)
            elif type == 'date':
                return datetime(**d).date()
            elif type == 'bool':
                if d['value'].lower() == 'true':
                    return True
                else:
                    return False
            else:
                d['__type__'] = type
                return d
        except:
            d['__type__'] = type
            return d


class DateTimeEncoder(JSONEncoder):
    """
    encodeur JSON sur mesure pour formatter les dates
    """

    def default(self, obj):
        if isinstance(obj, datetime):
            return {
                '__type__' : 'datetime',
                'year' : obj.year,
                'month' : obj.month,
                'day' : obj.day,
                'hour' : obj.hour,
                'minute' : obj.minute,
                'second' : obj.second,
                'microsecond' : obj.microsecond,
            }
        elif isinstance(obj, date):
            return {
                '__type__' : 'date',
                'year' : obj.year,
                'month' : obj.month,
                'day' : obj.day,
                'hour' : 0,
                'minute' : 0,
                'second' : 0,
                'microsecond' : 0,
            }
        elif isinstance(obj, bool):
            return {
                '__type__' : 'bool',
                'value' : 'true' if obj else 'false'
            }
        else:
            return JSONEncoder.default(self, obj)


class serializable:
    """
    classe de base apportant la sérialization
    """

    def serialize(self)->dict:
        """
        sérialize un objet héritant de cette classe
        """

        l1 = lambda x: not callable(x)
        l2 = lambda value: value.serialize() if 'serialize' in dir(value) else value
        l3 = lambda value: [l2(v) for v in value] if isinstance(value, list) else value
        l4 = lambda value: {k:l2(v) for k,v in value.items()} if isinstance(value, dict) else value
        l5 = lambda name, value: [l2(v) for v in value] if name != 'version' and isinstance(value, tuple) else value
        l0 = lambda name, value: '.'.join([str(v) for v in value]) if name == 'version' and isinstance(value, tuple) else value
        return {name: l0(name, l5(name, l4(l3(l2(value))))) \
            for (name, value) in inspect.getmembers(self, l1) \
                if name[0] != '_' and name != 'filepath' and name != 'password'}


    def save(self)->bool:
        """
        sauvegarde l'objet enfant dans le fichier définit par la propriété 'filepath'

        :return: 'Vrai' si l'ipération à réussie, sinon 'Faux'
        :rtype: bool
        """
        return self.saveAs(self.filepath, self.password)


    def saveAs(self, filepath:str, password:str='')->bool:
        """
        sauvegarde l'objet enfant dans le fichier définit par l'argument 'filepath'

        :param filepath: Chemin du fichier conteneur
        :param password: Mot de passe pour le cryptage des données. Laisser vide si non utilisé.
        :type filepath: str
        :type password: str
        :return: 'Vrai' si l'ipération à réussie, sinon 'Faux'
        :rtype: bool
        """

        global __version__

        # seul le portefeuille financier peut etre suavegardé
        if type(self) == financial:
            try:
                # mise à jour de la version du fichier lors de son enregistrement
                dv = tuple(map(lambda v: int(v), list(__version__.split('.'))))
                self.version = dv
                # serialisation des données
                obj = self.serialize()
                # transformation des données sérialisées au format json en données sur 8bits
                jstr = json.dumps(obj, ensure_ascii=False, cls=DateTimeEncoder)
                jbytes = bytes(jstr, encoding='utf8')
                # si un mot de passe est définit alors on encrypte les données
                if password != '':
                    jbytes = libs.crypto.encrypt(password, jbytes)
                # on termine par l'ecriture de ces données dans le fichier souhaité
                fp = open(filepath, 'wb')
                fp.write(jbytes)
                fp.close()
                # on mémorise le chamin du fichier et le mot de passe associé requis pour cet enregistrement
                self.filepath = filepath
                self.password = password
                # opération terminée avec succès
                return True
            except:
                return False
        # opération refusée
        return False

    @staticmethod
    def load(filepath:str, password:str=''):
        """
        charge et désérialize le fichier specifié via l'argument 'filepath'

        :param filepath: Chemin du fichier conteneur
        :param password: Mot de passe pour le cryptage des données. Laisser vide si non utilisé.
        :type filepath: str
        :type password: str
        :return: 'Vrai' si l'ipération à réussie, sinon 'Faux'
        :rtype: bool
        """

        #try:
        if not os.path.exists(filepath):
            return None

        fp = open(filepath, 'rb')
        jbytes = fp.read()
        fp.close()

        if password != '':
            jstr = libs.crypto.decrypt(password, jbytes)
        else:
            jstr = jbytes.decode('utf-8')

        try:
            obj = json.loads(jstr, cls=DateTimeDecoder)
        except:
            print(funcs.tr("La version du portefeuille {} que vous souhaitez ouvrir est illisible!").format(appinfos.app_name))
            return None

        obj['filepath'] = filepath
        obj['password'] = password
        fi = financial.unserialize(obj)

        if len(fi.version) != 3:
            print(funcs.tr("La version du portefeuille {} que vous souhaitez ouvrir est incorrecte!").format(appinfos.app_name))
            return None

        return fi
        #except:
            #return None

    def save2csv(self, dirpath:str, accountids:list, delimiter:str=';', decimal:str=',', dateformat:str='%x', startdate:date=date.min, enddate:date=date.max):
        if type(self) == financial:
            for ot in self.toDict(accountids, decimal, dateformat, startdate, enddate):
                if len(ot['datas']) > 0:
                    columns = ot['datas'][0].keys()
                    filename = "".join( x for x in ot['title'].replace(' ', '_') if (x.isalnum() or x in "_-"))
                    filepath = os.path.join(dirpath, appinfos.app_name + '_' + filename + '.csv')
                    try:
                        with open(filepath, mode='w', encoding='utf-8') as csvfile:
                            writer = csv.DictWriter(csvfile, fieldnames=columns, delimiter=delimiter)
                            writer.writeheader()
                            for data in ot['datas']:
                                writer.writerow(data)
                    except:
                        pass
            return True
        return False

    def save2pdf(self, dirpath:str, accountids:list, decimal:str=',', dateformat:str='%x', startdate:date=date.min, enddate:date=date.max):
        if type(self) == financial:
            for ot in self.toDict(accountids, decimal, dateformat, startdate, enddate):
                if len(ot['datas']) > 0:
                    pdf = FPDF(orientation='L', unit='mm', format='A4')
                    pdf.alias_nb_pages('{nb}')
                    pdf.add_page()
                    page = 0
                    pdf.set_doc_option('core_fonts_encoding', 'latin-1')
                    pdf.set_font('Arial', size=10)
                    pdf.set_fill_color(240, 240, 240)

                    # collection des données à afficher
                    columns = list(ot['datas'][0].keys())
                    values = [list(ot['datas'][i].values()) for i in range(len(ot['datas']))]
                    values.insert(0, columns)

                    # dimensions préliminaires
                    s = pdf.font_size
                    row_height = s + 1
                    col_widths = [20, 57, 50, 50, 35, 35, 30, 10]

                    # titre du document
                    t = ot['title'].encode('latin-1', 'ignore').decode('latin-1')
                    pdf.set_font('Arial', size=12, style='B')
                    pdf.cell(0,
                             row_height,
                             txt=t,
                             border=0,
                             align='C',
                             fill=False)
                    pdf.ln(20)

                    lastdate = ''
                    for j in range(len(values)):
                        row = values[j]

                        # numéro de chaque page en haut à gauche
                        if page != pdf.page_no():
                            page = pdf.page_no()
                            y = int(pdf.y)
                            pdf.set_y(5)
                            pdf.set_font('Arial', size=8, style='I')
                            pdf.cell(0, 0, "Page {}".format(page), 0, 0, 'R')
                            pdf.set_y(y)

                        # indication du solde du compte pour chaque jour comportant des opérations
                        if j > 0 and row[0] != lastdate:
                            atdate = datetime.strptime(row[0], '%Y-%m-%d').date()
                            amt = self.amount_atdate(atdate=atdate,
                                                     accountid=ot['account'].id)
                            amt = libs.currencies.formatCurrency(amt, ot['account'].alpha_3)
                            atdate = atdate.strftime('%x')

                            t = funcs.tr("au {}, solde: {}").format(atdate, amt)
                            t = t.encode('latin-1', 'ignore').decode('latin-1')

                            pdf.ln(5)
                            x = int(pdf.x)
                            y = int(pdf.y)
                            pdf.set_x(pdf.l_margin)
                            pdf.set_y(y + 2)
                            pdf.set_font('Arial', size=8, style='B')
                            pdf.cell(0, 5, t, border='B1', align='R')
                            pdf.set_x(x)
                            pdf.set_y(y)
                            pdf.ln(10)
                            lastdate = row[0]

                        start = 2
                        for i in range(start, len(row) - 1):
                            hd_width = len(columns[i]) * s
                            t = row[i]

                            if j == 0:
                                # ligne des noms de colones
                                pdf.set_font('Arial', size=8, style='B')
                            else:
                                # autres lignes
                                pdf.set_font('Arial', size=8)

                            # colone du montant de la transaction
                            if j > 0 and i == (len(row) - start):
                                t = row[i + 1] + ' ' + t

                            # pour eviter toutes erreurs on converti en latin-1
                            t = t.encode('latin-1', 'ignore').decode('latin-1')

                            # alignement à gauche sauf pour la colone du solde
                            align = 'L' if  i < len(row) - start else 'R'
                            # coloration du fond une ligne sur deux
                            fill = True if j % 2 == 0 else False

                            # on affiche le contenu de la cellule
                            pdf.cell(col_widths[i - start],
                                     row_height,
                                     txt=t,
                                     border=0,
                                     align=align,
                                     fill=fill,
                                     ln=0)

                        # nouvelle ligne
                        pdf.ln(row_height)

                    # enregistrement du fichier PDF
                    filename = "".join( x for x in ot['title'].replace(' ', '_') if (x.isalnum() or x in "_-"))
                    filepath = os.path.join(dirpath, appinfos.app_name + '_' + filename + '.pdf')
                    pdf.output(name=filepath, dest='F')

            return True

        return False

    def save2ofx(self, dirpath:str, accountids:list, decimal:str=',', dateformat:str='%x', startdate:date=date.min, enddate:date=date.max):
        if type(self) == financial:
            cnt = 0
            for ot in self.toDict(accountids, decimal, dateformat, startdate, enddate):
                if len(ot['datas']) > 0:
                    cnt += 1
                    a = ot['account']
                    datas = ot['datas']
                    dt = datetime.now().replace(tzinfo=UTC)
                    ledgerbal = LEDGERBAL(balamt=Decimal(str(self.amount_atdate(accountid=a.id, atdate=dt.date()))), dtasof=dt)
                    bankid = a.bic.strip() if len(a.bic.strip()) > 0 else dt.strftime('%Y%m%d%H%M%S') + 'bid'
                    acctid = a.iban.strip() if len(a.iban.strip()) > 0 else dt.strftime('%Y%m%d%H%M%S') + 'act'
                    acctfrom = BANKACCTFROM(bankid=bankid[-9:], acctid=acctid[-22:], branchid=a.name[0:22], accttype='CHECKING')
                    tranlist = BANKTRANLIST(dtstart=datetime.combine(startdate, datetime.min.time()).replace(tzinfo=UTC),
                                            dtend=datetime.combine(enddate, datetime.min.time()).replace(tzinfo=UTC))

                    for d in datas:
                        trntype = 'DEBIT' if a.amount < 0 else 'CREDIT'
                        if d['Type'] == 'Carte de crédit':
                            trntype = 'PAYMENT'
                        elif d['Type'] == 'Chèque':
                            trntype = 'CHECK'
                        elif d['Type'] == 'Prélèvement':
                            trntype = 'DEBIT'
                        elif d['Type'] == 'Virement ponctuel':
                            trntype = 'PAYMENT'
                        elif d['Type'] == 'Virement permanent':
                            trntype = 'REPEATPMT'
                        elif d['Type'] == 'Transfert':
                            trntype = 'XFER'
                        elif d['Type'] == 'Espèces':
                            trntype = 'CASH'
                        elif d['Type'] == 'Frais':
                            trntype = 'PAYMENT'
                        elif d['Type'] == 'Dépot':
                            trntype = 'DEP'
                        dtposted = datetime.strptime(d['IsoDate'] + ' 00:00:00', '%Y-%m-%d %H:%M:%S').replace(tzinfo=UTC)
                        trnamt = Decimal(str(d['Montant'].replace(decimal, '.')))
                        stmttrn = STMTTRN(trntype=trntype,
                                          dtposted=dtposted,
                                          trnamt=trnamt,
                                          fitid=str(d['ID']),
                                          name=d['Libellé'],
                                          memo=d['Mémo'],
                                          currency=CURRENCY(cursym=a.alpha_3, currate=Decimal(1)))
                        tranlist.append(stmttrn)

                    stmtrs = STMTRS(curdef=a.alpha_3, bankacctfrom=acctfrom, ledgerbal=ledgerbal, banktranlist=tranlist)
                    status = STATUS(code=0, severity='INFO')
                    stmttrnrs = STMTTRNRS(trnuid=str(cnt) + dt.strftime('%Y%m%d%H%M%S'), status=status, stmtrs=stmtrs)
                    bankmsgsrs = BANKMSGSRSV1(stmttrnrs)
                    fi = FI(org=appinfos.app_name, fid=appinfos.app_version)
                    sonrs = SONRS(status=status, dtserver=dt, language='FRA', fi=fi)
                    signonmsgs = SIGNONMSGSRSV1(sonrs=sonrs)
                    ofx = OFX(signonmsgsrsv1=signonmsgs, bankmsgsrsv1=bankmsgsrs)
                    ofx_header = str(make_header(version=220))
                    ofx_str = ET.tostring(ofx.to_etree()).decode()

                    filename = "".join( x for x in ot['title'].replace(' ', '_') if (x.isalnum() or x in "_-"))
                    filepath = os.path.join(dirpath, appinfos.app_name + '_' + filename + '.ofx')
                    with open(filepath, 'w') as ofxfile:
                        ofxfile.write(ofx_header + ofx_str)

            return True
        return False

class account(serializable):

    @property
    def type(self)->str:
        return type(self).__name__

    @property
    def id(self)->float:
        return self._id
    @id.setter
    def id(self, value:float):
        self._id = value

    @property
    def title(self)->str:
        return self._title
    @title.setter
    def title(self, value:str):
        self._title = value

    @property
    def alpha_3(self)->str:
        return self._alpha_3
    @alpha_3.setter
    def alpha_3(self, value:str):
        self._alpha_3 = value

    @property
    def amount(self)->int:
        return self._amount
    @amount.setter
    def amount(self, value:int):
        self._amount = value

    @property
    def credit(self)->int:
        return self._credit
    @credit.setter
    def credit(self, value:int):
        self._credit = value

    @property
    def operations(self)->list:
        return self._operations

    @property
    def planner(self)->list:
        return self._planner

    def __init__(self, title:str, id:float=-1, amount:float=0.0, credit:float=0.0, alpha_3:str='EUR'):
        self._title = title
        self._alpha_3 = alpha_3
        self._amount = amount
        self._credit = credit
        self._id = id if id > -1 else datetime.now().timestamp()
        self._operations = []
        self._planner = []

    def operations2list(self, decimal:str=',', dateformat:str='%x', startdate:date=date.min, enddate:date=date.max):
        ret = []
        for ope in self.operations:
            if ope.fromdate >= startdate and ope.fromdate <= enddate:
                d = {}
                d['IsoDate'] = ope.fromdate.strftime('%Y-%m-%d')
                d['ID'] = ope.id
                d['Date'] = ope.fromdate.strftime(dateformat)
                d['Libellé'] = ope.to.strip()
                d['Mémo'] = ope.title.strip()
                d['Commentaire'] = ope.comment.strip()
                d['Type'] = ope.paytype.strip()
                d['Catégorie'] = ope.category.strip()
                d['Montant'] = ('{:2.2f}'.format(ope.amount)).replace('.', decimal)
                d['Symbole'] = currency.symbol(self.alpha_3)
                ret.append(d)
        return ret


class bankaccount(account):

    @property
    def name(self)->str:
        return self._name
    @name.setter
    def name(self, value:str):
        self._name = value

    @property
    def iban(self)->str:
        return self._iban
    @iban.setter
    def iban(self, value:str):
        self._iban = value

    @property
    def bic(self)->str:
        return self._bic
    @bic.setter
    def bic(self, value:str):
        self._bic = value

    def __init__(self, title:str, id:float=-1, name:str='', iban:str='', bic:str='', amount:int=0, credit:int=0, alpha_3:str='EUR'):
        super(bankaccount, self).__init__(title=title, id=id, alpha_3=alpha_3, amount=amount, credit=credit)
        self._name = name
        self._iban = iban
        self._bic = bic

    @staticmethod
    def unserialize(data:dict):
        if not('title' in data or 'alpha_3' in data):
            return None
        kwargs = {'title':str(data['title']), 'alpha_3':str(data['alpha_3']),
        'amount':float(data['amount']) if 'amount' in data else 0.0,
        'credit':float(data['credit']) if 'credit' in data else 0.0,
        'name':str(data['name']) if 'name' in data else '',
        'iban':str(data['iban']) if 'iban' in data else '',
        'bic':str(data['bic']) if 'bic' in data else '',
        'id':float(data['id']) if 'id' in data else datetime.now().timestamp()}
        a = bankaccount(**kwargs)

        if 'operations' in data and isinstance(data['operations'], list):
            a.operations.clear()
            for v in data['operations']:
                if isinstance(v, dict) and 'type' in v:
                    operation = globals()[v['type']].unserialize(v)
                    if not(operation is None):
                        a.operations.append(operation)

        if 'planner' in data and isinstance(data['planner'], list):
            a.planner.clear()
            for v in data['planner']:
                if isinstance(v, dict) and 'type' in v:
                    evt = globals()[v['type']].unserialize(v)
                    if not(evt is None):
                        a.planner.append(evt)

        return a


class creditcard(account):

    @property
    def name(self)->str:
        return self._name
    @name.setter
    def name(self, value:str):
        self._name = value

    @property
    def number(self)->str:
        return self._number
    @number.setter
    def number(self, value:str):
        self._number = value

    @property
    def month(self)->int:
        return self._month
    @month.setter
    def month(self, value:int):
        self._month = value

    @property
    def year(self)->int:
        return self._year
    @year.setter
    def year(self, value:int):
        self._year = value

    @property
    def code(self)->str:
        return self._code
    @code.setter
    def code(self, value:str):
        self._code = value

    @property
    def accountid(self)->float:
        return self._accountid
    @accountid.setter
    def accountid(self, value:float):
        self._accountid = value

    def __init__(self, title:str, id:float=-1, name:str='', number:str='', month:int=1, year:int=1970, code:str='', amount:int=0, credit:int=0, alpha_3:str='EUR', accountid:float=-1):
        super(creditcard, self).__init__(title=title, id=id, alpha_3=alpha_3, amount=amount, credit=credit)
        self._name = name
        self._number = number
        self._month = month
        self._year = year
        self._code = code
        self._accountid = accountid

    @staticmethod
    def unserialize(data:dict):
        if not('title' in data) or not('alpha_3' in data):
            return None
        kwargs = {'title':str(data['title']),
                  'alpha_3':str(data['alpha_3']),
                  'amount':float(data['amount']) if 'amount' in data else 0.0,
                  'credit':float(data['credit']) if 'credit' in data else 0.0,
                  'name':str(data['name']) if 'name' in data else '',
                  'number':str(data['number']) if 'number' in data else '',
                  'month':int(data['month']) if 'month' in data else 1,
                  'year':int(data['year']) if 'year' in data else 1970,
                  'code':str(data['code']) if 'code' in data else '',
                  'accountid':float(data['accountid']) if 'accountid' in data else -1,
                  'id':float(data['id']) if 'id' in data else datetime.now().timestamp()}
        a = creditcard(**kwargs)

        if 'operations' in data and isinstance(data['operations'], list):
            a.operations.clear()
            for v in data['operations']:
                if isinstance(v, dict) and 'type' in v:
                    operation = globals()[v['type']].unserialize(v)
                    if not(operation is None):
                        a.operations.append(operation)

        if 'planner' in data and isinstance(data['planner'], list):
            a.planner.clear()
            for v in data['planner']:
                if isinstance(v, dict) and 'type' in v:
                    evt = globals()[v['type']].unserialize(v)
                    if not(evt is None):
                        a.planner.append(evt)

        return a


class wallet(account):

    @property
    def electronic(self)->bool:
        return self._electronic
    @electronic.setter
    def electronic(self, value:bool):
        self._electronic = value

    def __init__(self, title:str, id:float=-1, electronic:bool=False, amount:int=0, credit:int=0, alpha_3:str='EUR'):
        super(wallet, self).__init__(title=title, id=id, alpha_3=alpha_3, amount=amount, credit=credit)
        self._electronic = electronic

    @staticmethod
    def unserialize(data:dict):
        if not('title' in data or 'alpha_3' in data):
            return None
        kwargs = {'title':str(data['title']), 'alpha_3':str(data['alpha_3']),
        'amount':float(data['amount']) if 'amount' in data else 0.0,
        'credit':float(data['credit']) if 'credit' in data else 0.0,
        'electronic':True if 'electronic' in data and \
            ((type(data['electronic']) is bool and \
                data['electronic']) or \
                    data['electronic'] == 'true') else False,
        'id':float(data['id']) if 'id' in data else datetime.now().timestamp()}
        a = wallet(**kwargs)

        if 'operations' in data and isinstance(data['operations'], list):
            a.operations.clear()
            for v in data['operations']:
                if isinstance(v, dict) and 'type' in v:
                    operation = globals()[v['type']].unserialize(v)
                    if not(operation is None):
                        a.operations.append(operation)

        if 'planner' in data and isinstance(data['planner'], list):
            a.planner.clear()
            for v in data['planner']:
                if isinstance(v, dict) and 'type' in v:
                    evt = globals()[v['type']].unserialize(v)
                    if not(evt is None):
                        a.planner.append(evt)

        return a


class thirdparty(serializable):

    @property
    def type(self)->str:
        return type(self).__name__

    @property
    def title(self)->str:
        return self._title
    @title.setter
    def title(self, value:str):
        self._title = value

    @property
    def paytype(self)->str:
        return self._paytype
    @paytype.setter
    def paytype(self, value:str):
        self._paytype = value

    @property
    def category(self)->str:
        return self._category
    @category.setter
    def category(self, value:str):
        self._category = value

    def __init__(self, title:str, paytype:str='', category:str=''):
        self._title = title
        self._paytype = paytype
        self._category = category

    @staticmethod
    def unserialize(data:dict):
        if not('title' in data):
            return None
        kwargs = {'title':str(data['title']),
                  'paytype':str(data['paytype']) if 'paytype' in data else '',
                  'category':str(data['category']) if 'category' in data else ''}
        return thirdparty(**kwargs)


class operation(serializable):

    @property
    def type(self)->str:
        return type(self).__name__

    @property
    def id(self)->float:
        return self._id
    @id.setter
    def id(self, value:float):
        self._id = value

    @property
    def title(self)->str:
        return self._title
    @title.setter
    def title(self, value:str):
        self._title = value

    @property
    def fromdate(self)->date:
        return self._fromdate
    @fromdate.setter
    def fromdate(self, value:date):
        self._fromdate = value

    @property
    def amount(self)->float:
        return self._amount
    @amount.setter
    def amount(self, value:float):
        self._amount = value

    @property
    def comment(self)->str:
        return self._comment
    @comment.setter
    def comment(self, value:str):
        self._comment = value

    @property
    def to(self)->str:
        return self._to
    @to.setter
    def to(self, value:str):
        self._to = value

    @property
    def paytype(self)->str:
        return self._paytype
    @paytype.setter
    def paytype(self, value:str):
        self._paytype = value

    @property
    def category(self)->str:
        return self._category
    @category.setter
    def category(self, value:str):
        self._category = value

    @property
    def state(self)->bool:
        return self._state
    @state.setter
    def state(self, value:bool):
        self._state = value

    def __init__(self, title:str='', id:float=-1, amount:float=0.0, fromdate:date=datetime.now(), comment:str='', to:str='', paytype:str='', category:str='', state:bool=False):
        self._title = title
        self._amount = amount
        self._id = id if id > -1 else datetime.now().timestamp()
        self._fromdate = fromdate
        self._comment = comment
        self._to = to
        self._paytype = paytype
        self._category = category
        self._state = state

    @staticmethod
    def unserialize(data:dict):
        kwargs = {'title':str(data['title']) if 'title' in data else '',
                  'id':float(data['id']) if 'id' in data else datetime.now().timestamp(),
                  'paytype':str(data['paytype']) if 'paytype' in data else '',
                  'category':str(data['category']) if 'category' in data else '',
                  'fromdate':data['fromdate'] if 'fromdate' in data else datetime.now(),
                  'amount':float(data['amount']) if 'amount' in data else 0.0,
                  'comment':str(data['comment']) if 'comment' in data else '',
                  'to':str(data['to']) if 'to' in data else '',
                  'state':data['state'] if 'state' in data else False}
        return operation(**kwargs)


class transfer(serializable):

    @property
    def type(self)->str:
        return type(self).__name__

    @property
    def id(self)->float:
        return self._id
    @id.setter
    def id(self, value:float):
        self._id = value

    @property
    def title(self)->str:
        return self._title
    @title.setter
    def title(self, value:str):
        self._title = value

    @property
    def fromdate(self)->date:
        return self._fromdate
    @fromdate.setter
    def fromdate(self, value:date):
        self._fromdate = value

    @property
    def amount(self)->float:
        return self._amount
    @amount.setter
    def amount(self, value:float):
        self._amount = value

    @property
    def comment(self)->str:
        return self._comment
    @comment.setter
    def comment(self, value:str):
        self._comment = value

    @property
    def fromactid(self)->float:
        return self._fromactid
    @fromactid.setter
    def fromactid(self, value:float):
        self._fromactid = value

    @property
    def toactid(self)->float:
        return self._toactid
    @toactid.setter
    def toactid(self, value:float):
        self._toactid = value

    @property
    def state(self)->bool:
        return self._state
    @state.setter
    def state(self, value:bool):
        self._state = value

    def __init__(self, title:str, id:float=-1, amount:float=0.0, fromdate:date=datetime.now(), comment:str='', fromactid:float=-1, toactid:float=-1, state:bool=False):
        self._title = title
        self._amount = amount
        self._id = id if id > -1 else datetime.now().timestamp()
        self._fromdate = fromdate
        self._comment = comment
        self._fromactid = fromactid
        self._toactid = toactid
        self._state = state

    @staticmethod
    def unserialize(data:dict):
        if not('title' in data):
            return None
        kwargs = {'title':str(data['title']),
                  'id':float(data['id']) if 'id' in data else datetime.now().timestamp(),
                  'fromdate':data['fromdate'] if 'fromdate' in data else datetime.now(),
                  'amount':float(data['amount']) if 'amount' in data else 0.0,
                  'comment':str(data['comment']) if 'comment' in data else '',
                  'fromactid':float(data['fromactid']) if 'fromactid' in data else -1,
                  'toactid':float(data['toactid']) if 'toactid' in data else -1,
                  'state':data['state'] if 'state' in data else False}
        return transfer(**kwargs)





class event(serializable):

    @property
    def type(self)->str:
        return type(self).__name__

    @property
    def id(self)->float:
        return self._id
    @id.setter
    def id(self, value:float):
        self._id = value

    @property
    def state(self)->bool:
        return self._state
    @state.setter
    def state(self, value:bool):
        self._state = value

    @property
    def ended(self)->bool:
        return self._ended
    @ended.setter
    def ended(self, value:bool):
        self._ended = value

    @property
    def nextdate(self)->date:
        return self._nextdate
    @nextdate.setter
    def nextdate(self, value:date):
        self._nextdate = value

    @property
    def lastdate(self)->date:
        return self._lastdate
    @lastdate.setter
    def lastdate(self, value:date):
        self._lastdate = value

    @property
    def repeat(self)->int:
        return self._repeat
    @repeat.setter
    def repeat(self, value:int):
        if value > 0:
            self._repeat = value

    @property
    def repeattype(self)->str:
        return self._repeattype
    @repeattype.setter
    def repeattype(self, value:str):
        value = value.strip().lower()
        if value == 'd' or value == 'w' or value == 'm' or value == 'y':
            self._repeattype = value

    @property
    def operation(self)->operation:
        return self._operation
    @operation.setter
    def operation(self, value:operation):
        self._operation = value

    @property
    def transfer(self)->transfer:
        return self._transfer
    @transfer.setter
    def transfer(self, value:transfer):
        self._transfer = value

    @property
    def beforeWeekend(self)->bool:
        return self._beforeWeekend
    @beforeWeekend.setter
    def beforeWeekend(self, value:bool):
        self._beforeWeekend = value

    @property
    def afterWeekend(self)->bool:
        return self._afterWeekend
    @afterWeekend.setter
    def afterWeekend(self, value:bool):
        self._afterWeekend = value

    @property
    def autoPost(self)->bool:
        return self._autoPost
    @autoPost.setter
    def autoPost(self, value:bool):
        self._autoPost = value

    def __init__(self, id:float=-1, state:bool=True, ended:bool=False, nextdate:date=datetime.now(), lastdate:date=datetime.now(), repeat:int=1, repeattype:str='m', operation:operation=None, transfer:transfer=None, beforeWeekend:bool=True, afterWeekend:bool=False, autoPost:bool=True):
        self._id = id if id > -1 else datetime.now().timestamp()
        self._lastdate = lastdate
        self._nextdate = nextdate
        self._repeat = repeat
        self._repeattype = repeattype
        self._operation = operation
        self._transfer = transfer
        self._state = state
        self._ended = ended
        self._beforeWeekend = beforeWeekend
        self._afterWeekend = afterWeekend if not beforeWeekend else False
        self._autoPost = autoPost

    @staticmethod
    def unserialize(data:dict):
        if not('operation' in data) and not('transfer' in data):
            return None
        kwargs = {'id':float(data['id']) if 'id' in data else datetime.now().timestamp(),
                  'lastdate':data['lastdate'] if 'lastdate' in data else datetime.now(),
                  'nextdate':data['nextdate'] if 'nextdate' in data else datetime.now(),
                  'repeat':int(data['repeat']) if 'repeat' in data else 1,
                  'repeattype':str(data['repeattype']) if 'repeattype' in data else 'm',
                  'state':data['state'] if 'state' in data else False,
                  'ended':data['ended'] if 'ended' in data else False,
                  'beforeWeekend':data['beforeWeekend'] if 'beforeWeekend' in data else True,
                  'afterWeekend':data['afterWeekend'] if 'afterWeekend' in data else False,
                  'autoPost':data['autoPost'] if 'autoPost' in data else True}

        operation = None
        if 'operation' in data:
            if isinstance(data['operation'], dict) and 'type' in data['operation']:
                operation = globals()[data['operation']['type']].unserialize(data['operation'])

        transfer = None
        if 'transfer' in data:
            if isinstance(data['transfer'], dict) and 'type' in data['transfer']:
                transfer = globals()[data['transfer']['type']].unserialize(data['transfer'])

        if operation is None and transfer is None:
            return None

        kwargs['operation'] = operation
        kwargs['transfer'] = transfer

        return event(**kwargs)


    def verifyNextdate(self):
        firstdate = self.operation.fromdate if not(self.operation is None) else self.transfer.fromdate
        if self.lastdate < firstdate:
            self.lastdate = firstdate
            self.nextdate = firstdate
            return

        nd = self.nextdate
        while nd > self.lastdate:
            if self.repeattype == 'd':
                nd = nd - relativedelta(days=self.repeat)
            elif self.repeattype == 'w':
                nd = nd - relativedelta(weeks=self.repeat)
            elif self.repeattype == 'm':
                nd = nd - relativedelta(months=self.repeat)
            elif self.repeattype == 'y':
                nd = nd - relativedelta(years=self.repeat)
            if nd < firstdate:
                self.nextdate = firstdate
                break
        self.nextdate = nd
        if self.nextdate < firstdate:
            self.nextdate = firstdate

    def hasNextdate(self, ld:date=None):
        if ld is None:
            ld = self.lastdate
        firstdate = self.operation.fromdate if not(self.operation is None) else self.transfer.fromdate
        if self.repeattype == 'd':
            nt = self.nextdate + relativedelta(days=self.repeat)
            if nt <= ld:
                return True
        elif self.repeattype == 'w':
            nt = self.nextdate + relativedelta(weeks=self.repeat)
            if nt <= ld:
                return True
        elif self.repeattype == 'm':
            nt = self.nextdate + relativedelta(months=self.repeat)
            if nt <= ld:
                return True
        elif self.repeattype == 'y':
            nt = self.nextdate + relativedelta(years=self.repeat)
            if nt <= ld:
                return True
        return False

    def computeNextdate(self):
        firstdate = self.operation.fromdate if not(self.operation is None) else self.transfer.fromdate
        if self.repeattype == 'd':
            nt = self.nextdate + relativedelta(days=self.repeat)
            if nt <= self.lastdate:
                self.nextdate = nt
                return True
        elif self.repeattype == 'w':
            nt = self.nextdate + relativedelta(weeks=self.repeat)
            if nt <= self.lastdate:
                self.nextdate = nt
                return True
        elif self.repeattype == 'm':
            nt = self.nextdate + relativedelta(months=self.repeat)
            if nt <= self.lastdate:
                self.nextdate = nt
                return True
        elif self.repeattype == 'y':
            nt = self.nextdate + relativedelta(years=self.repeat)
            if nt <= self.lastdate:
                self.nextdate = nt
                return True
        return False

    def getNextdate(self, ld:date=None, st:date=None):
        if ld is None:
            ld = self.lastdate
        if st is None:
            st = self.nextdate
        if self.repeattype == 'd':
            nt = st + relativedelta(days=self.repeat)
            if nt <= ld:
                return nt
        elif self.repeattype == 'w':
            nt = st + relativedelta(weeks=self.repeat)
            if nt <= ld:
                return nt
        elif self.repeattype == 'm':
            nt = st + relativedelta(months=self.repeat)
            if nt <= ld:
                return nt
        elif self.repeattype == 'y':
            nt = st + relativedelta(years=self.repeat)
            if nt <= ld:
                return nt
        return None

    def predictNextdate(self, date):
        firstdate = self.operation.fromdate if not(self.operation is None) else self.transfer.fromdate
        if self.repeattype == 'd':
            nt = date + relativedelta(days=self.repeat)
            if nt <= self.lastdate:
                return nt
        elif self.repeattype == 'w':
            nt = date + relativedelta(weeks=self.repeat)
            if nt <= self.lastdate:
                return nt
        elif self.repeattype == 'm':
            nt = date + relativedelta(months=self.repeat)
            if nt <= self.lastdate:
                return nt
        elif self.repeattype == 'y':
            nt = date + relativedelta(years=self.repeat)
            if nt <= self.lastdate:
                return nt
        return None

    def predict2Nextdate(self, date):
        return self.predictNextdate(self.predictNextdate(date))

    def resetNextdate(self):
        firstdate = self.operation.fromdate if not(self.operation is None) else self.transfer.fromdate
        self.nextdate = firstdate

    def getPosition(self, ld:date=None):
        pos = 0
        tot = 0
        dte = self.operation.fromdate if not(self.operation is None) else self.transfer.fromdate
        if ld is None:
            ld = self.lastdate
        while dte <= ld:
            if dte <= self.nextdate:
                pos = pos + 1
            tot = tot + 1
            dte = self.getNextdate(ld=ld, st=dte)
            if dte is None:
                break
        return pos, tot

    def getLastDate(self, ld:date=None):
        if ld is None:
            ld = self.lastdate
        date = self.operation.fromdate if not(self.operation is None) else self.transfer.fromdate
        while date <= ld:
            dt = date
            if self.repeattype == 'd':
                dt = dt + relativedelta(days=self.repeat)
            elif self.repeattype == 'w':
                dt = dt + relativedelta(weeks=self.repeat)
            elif self.repeattype == 'm':
                dt = dt + relativedelta(months=self.repeat)
            elif self.repeattype == 'y':
                dt = dt + relativedelta(years=self.repeat)
            if dt > ld:
                break;
            else:
                date = dt
        return date


class financial(serializable):

    @property
    def version(self)->tuple:
        return self._version
    @version.setter
    def version(self, value:tuple):
        self._version = value

    @property
    def title(self)->str:
        return self._title
    @title.setter
    def title(self, value:str):
        self._title = value

    @property
    def filepath(self)->str:
        return self._filepath
    @filepath.setter
    def filepath(self, value:str):
        self._filepath = value

    @property
    def password(self)->str:
        return self._password
    @password.setter
    def password(self, value:str):
        self._password = value

    @property
    def accounts(self)->list:
        return self._accounts

    @property
    def paytypes(self)->list:
        return self._paytypes

    @property
    def categories(self)->dict:
        return self._categories

    @property
    def thirdparties(self)->list:
        return self._thirdparties

    @property
    def transfers(self)->list:
        return self._transfers

    def __init__(self, version:tuple, filepath:str='', password:str='', title:str=''):
        self._version = version
        self._filepath = filepath
        self._password = password
        self._title = title
        self._accounts = []
        self._paytypes = []
        for p in default_paytypes:
            self._paytypes.append(p)
        self._categories = {}
        for k,v in default_categories.items():
            self._categories[k] = []
            for c in v:
                self._categories[k].append(c)
        self._thirdparties = []
        self._transfers = []

    @staticmethod
    def unserialize(data:dict):
        global __version__

        if 'version' in data and isinstance(data['version'], str):
            version = tuple(map(lambda v: int(v), list(str(data['version']).split('.'))))
        else:
            version = tuple(map(lambda v: int(v), list(__version__.split('.'))))

        if 'filepath' in data and isinstance(data['filepath'], str):
            filepath = data['filepath']
        else:
            return None

        if 'password' in data and isinstance(data['password'], str):
            password = data['password']

        if 'title' in data and isinstance(data['title'], str):
            title = data['title']
        else:
            title = os.path.basename(filepath)

        f = financial(version, filepath, password, title)

        if 'accounts' in data and isinstance(data['accounts'], list):
            for a in data['accounts']:
                if isinstance(a, dict) and 'type' in a:
                    account = globals()[a['type']].unserialize(a)
                    if not(account is None):
                        f.accounts.append(account)

        if 'paytypes' in data and isinstance(data['paytypes'], list):
            f.paytypes.clear()
            for v in data['paytypes']:
                if isinstance(v, str):
                    if not(v in f.paytypes):
                        f.paytypes.append(v)

        if 'categories' in data and isinstance(data['categories'], dict):
            f.categories.clear()
            for k,v in data['categories'].items():
                if isinstance(k, str) and isinstance(v, list):
                    if not(k in f.categories.keys()):
                        f.categories[k] = v

        if 'thirdparties' in data and isinstance(data['thirdparties'], list):
            for tp in data['thirdparties']:
                if isinstance(tp, dict) and 'type' in tp:
                    thirdparty = globals()[tp['type']].unserialize(tp)
                    if not(thirdparty is None):
                        f.thirdparties.append(thirdparty)

        if 'transfers' in data and isinstance(data['transfers'], list):
            for tf in data['transfers']:
                if isinstance(tf, dict) and 'type' in tf:
                    transfer = globals()[tf['type']].unserialize(tf)
                    if not(transfer is None):
                        f.transfers.append(transfer)


        return f

    def amounts(self, accountid:float):
        ldom = funcs.last_day_of_month(datetime.now())

        thistday = 0.0
        endmonth = 0.0
        endyear = 0.0
        credit = 0.0

        for a in self._accounts:
            if a.id == accountid:
                thistday = a.amount
                endmonth = a.amount
                endyear = a.amount
                credit = a.credit
                for op in a.operations:
                    if funcs.until_now(op.fromdate):
                        thistday = thistday + op.amount
                    if funcs.until_last_day_of_month(op.fromdate):
                        endmonth = endmonth + op.amount
                    if funcs.until_last_day_of_year(op.fromdate):
                        endyear = endyear + op.amount
                break

        for t in self._transfers:
            if t.fromactid == accountid:
                if funcs.until_now(t.fromdate):
                    thistday = thistday - t.amount
                if funcs.until_last_day_of_month(t.fromdate):
                    endmonth = endmonth - t.amount
                if funcs.until_last_day_of_year(t.fromdate):
                    endyear = endyear - t.amount
            elif t.toactid == accountid:
                if funcs.until_now(t.fromdate):
                    thistday = thistday + t.amount
                if funcs.until_last_day_of_month(t.fromdate):
                    endmonth = endmonth + t.amount
                if funcs.until_last_day_of_year(t.fromdate):
                    endyear = endyear + t.amount

        return thistday, endmonth, endyear, credit

    def amount_atdate(self, accountid:float, atdate:date):
        amt = 0.0

        for a in self._accounts:
            if a.id == accountid:
                amt = a.amount
                for op in a.operations:
                    if op.fromdate <= atdate:
                        amt = amt + op.amount
                break

        for t in self._transfers:
            if t.fromactid == accountid:
                if t.fromdate <= atdate:
                    amt = amt - t.amount
            elif t.toactid == accountid:
                if t.fromdate <= atdate:
                    amt = amt + t.amount

        return amt

    def transfers2list(self, fromaccount:account, decimal:str=',', dateformat:str='%x', startdate:date=date.min, enddate:date=date.max):
        ret = []
        for trf in self.transfers:
            if trf.fromdate >= startdate and trf.fromdate <= enddate:
                if trf.toactid == fromaccount.id or trf.fromactid == fromaccount.id:
                    fa = None
                    ta = None
                    for b in self.accounts:
                        if trf.fromactid == b.id:
                            fa = b
                        if trf.toactid == b.id:
                            ta = b

                    if trf.toactid == fromaccount.id and not(fa is None):
                        amt = trf.amount
                        to = "Depuis {}".format(fa.title)
                        alpha_3 = fa.alpha_3
                        aid = trf.fromactid
                    elif trf.fromactid == fromaccount.id and not(ta is None):
                        amt = -trf.amount
                        to = "Vers {}".format(ta.title)
                        alpha_3 = fromaccount.alpha_3
                        aid = trf.toactid
                    else:
                        amt = 0
                        to = ''
                        alpha_3 = ''
                        aid = -1

                    if to != '' and aid != -1:
                        d = {}
                        d['IsoDate'] = trf.fromdate.strftime('%Y-%m-%d')
                        d['ID'] = aid
                        d['Date'] = trf.fromdate.strftime(dateformat)
                        d['Libellé'] = to
                        d['Mémo'] = trf.title.strip()
                        d['Commentaire'] = trf.comment.strip()
                        d['Type'] = 'Transfert'
                        d['Catégorie'] = ''
                        d['Montant'] = ('{:2.2f}'.format(amt)).replace('.', decimal)
                        d['Symbole'] = currency.symbol(alpha_3)
                        ret.append(d)
        return ret

    def toDict(self, accountids:list, decimal:str=',', dateformat:str='%x', startdate:date=date.min, enddate:date=date.max):
        allOT = []
        for a in self.accounts:
            if type(a) == bankaccount and a.id in accountids:
                l = []
                l += a.operations2list(decimal, dateformat, startdate, enddate)
                l += self.transfers2list(a, decimal, dateformat, startdate, enddate)
                l = sorted(l, key=lambda k: k['IsoDate'], reverse=True)

                t = a.title
                n = a.name.strip() if hasattr(a, 'name') and a.name.strip() != '' else ''
                if n != '':
                    t = t + ' (' + n + ')'

                t = '{} [{}-{}]'.format(t,
                                        startdate.strftime(dateformat),
                                        enddate.strftime(dateformat))

                allOT.append({'title': t, 'datas': l, 'account': a})
        return allOT



