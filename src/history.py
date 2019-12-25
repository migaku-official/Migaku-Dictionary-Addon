# -*- coding: utf-8 -*-
# 

import json

from aqt.qt import *
from aqt.utils import askUser, showInfo
import datetime
from .miutils import miInfo, miAsk

class HistoryModel(QAbstractTableModel):

    def __init__(self, history, parent=None):
        super(HistoryModel, self).__init__(parent)
        self.history = history
        self.dictInt = parent
        self.justTerms = [item[0] for item in history]
        
    def rowCount(self, index=QModelIndex()):
        return len(self.history)

    def columnCount(self, index=QModelIndex()):
        return 2

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None

        if not 0 <= index.row() < len(self.history):
            return None
        if role == Qt.DisplayRole or role == Qt.EditRole:
            term = self.history[index.row()][0]
            date = self.history[index.row()][1]
            
            if index.column() == 0:
                return term
            elif index.column() == 1:
                return date
        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role != Qt.DisplayRole:
            return None
        if orientation == Qt.Vertical:
            return section + 1;
        return None

    def insertRows(self, position= False, rows=1, index=QModelIndex(), term = False, date = False):
        if not position:
            position = self.rowCount()
        self.beginInsertRows(QModelIndex(), position, position)
        for row in range(rows):
            if term and date:
                if term in self.justTerms:
                    index = self.justTerms.index(term)
                    self.removeRows(index)
                    del self.justTerms[index]
                self.history.insert(0, [term, date])
                self.justTerms.insert(0, term)
        self.endInsertRows()
        self.dictInt.saveHistory()
        return True

    def removeRows(self, position, rows=1, index=QModelIndex()):
        self.beginRemoveRows(QModelIndex(), position, position + rows - 1)
        del self.history[position:position+rows]
        self.endRemoveRows()
        self.dictInt.saveHistory()
        return True

class HistoryBrowser(QWidget):
    def __init__(self, historyModel, parent):
        super(HistoryBrowser, self).__init__(parent, Qt.Window)
        self.setAutoFillBackground(True)
        self.resize(300, 200)
        self.tableView = QTableView()
        self.model = historyModel
        self.dictInt = parent
        self.tableView.setModel(self.model)
        self.clearHistory = QPushButton('Clear History')
        self.clearHistory.clicked.connect(self.deleteHistory)
        self.tableView.doubleClicked.connect(self.searchAgain)
        self.setupTable()
        self.layout = self.getLayout()
        self.setLayout(self.layout)
        self.setColors()
        self.hotkeyEsc = QShortcut(QKeySequence("Esc"), self)
        self.hotkeyEsc.activated.connect(self.hide)

    def setupTable(self):
        tableHeader = self.tableView.horizontalHeader()
        tableHeader.setSectionResizeMode(0, QHeaderView.Stretch)
        tableHeader.setSectionResizeMode(1, QHeaderView.Stretch)
        self.tableView.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tableView.horizontalHeader().hide()

    def searchAgain(self): 
        date = str(datetime.date.today())
        term = self.model.index(self.tableView.selectionModel().currentIndex().row(),0).data()
        self.model.insertRows(term = term, date = date)
        self.dictInt.initSearch(term)

    def setColors(self):
        if self.dictInt.nightModeToggler.day:
            if isMac:
                self.tableView.setStyleSheet(self.dictInt.getMacTableStyle())
            else:
                self.tableView.setStyleSheet('')
            self.setPalette(self.dictInt.ogPalette)
        else:
            self.setPalette(self.dictInt.nightPalette)
            self.tableView.setStyleSheet(self.dictInt.getTableStyle())

    def deleteHistory(self):
        if miAsk('Clearing your history cannot be undone. Would you like to proceed?', self):
            self.model.removeRows(0, len(self.model.history))
            
    def getLayout(self):
        vbox = QVBoxLayout()
        vbox.addWidget(self.tableView)
        hbox = QHBoxLayout()
        self.clearHistory.setFixedSize(100, 30)
        hbox.addStretch()
        hbox.addWidget(self.clearHistory)
        vbox.addLayout(hbox)
        vbox.setContentsMargins(2, 2, 2, 2)
        return vbox

   