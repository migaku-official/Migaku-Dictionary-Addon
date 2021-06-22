# -*- coding: utf-8 -*-
# 
# 
import json
import sys
import math
from anki.hooks import addHook
from aqt.qt import *
from aqt.utils import openLink, tooltip, showInfo, askUser
from anki.utils import isMac, isWin, isLin
from anki.lang import _
from aqt.webview import AnkiWebView
import re
import os
from os.path import dirname, join, exists
from aqt import mw
from PyQt5 import QtCore
from .miutils import miInfo, miAsk
from shutil import copyfile
from operator import itemgetter
import ntpath

class DictGroupEditor(QDialog):
    def __init__(self, mw, parent = None, dictionaries = [], group = False, groupName = False):
        super(DictGroupEditor, self).__init__(parent, Qt.Window)
        self.mw = mw
        self.settings = parent
        self.setWindowTitle("Add Dictionary Group")
        self.groupName = QLineEdit()
        self.fontFromDropdown = QRadioButton()
        self.fontFromFile = QRadioButton()
        self.fontDropDown = self.getFontCB()
        self.fontFileName = QLabel('None Selected')
        self.browseFontFile = QPushButton('Browse')
        self.dictionaries = self.setupDictionaries()
        self.selectAll = QPushButton('Select All')
        self.removeAll = QPushButton('Remove All')
        self.cancelButton = QPushButton('Cancel')
        self.saveButton = QPushButton('Save')
        self.layout = QVBoxLayout()
        self.setupLayout()
        self.fontToMove = False
        self.dictList = dictionaries
        self.loadDictionaries(dictionaries)
        self.new = True
        if group:
            self.new = False
            self.loadGroupEditor(group, groupName)
        else:
            self.clearGroupEditor()
        self.initHandlers()
        self.initTooltips()

    def initTooltips(self):
        self.groupName.setToolTip('The name of the dictionary group.')
        self.fontFromDropdown.setToolTip('Select a font installed on your system.')
        self.fontDropDown.setToolTip('Select a font installed on your system.')
        self.fontFromFile.setToolTip('Select a font to import from a file.')
        self.browseFontFile.setToolTip('Select a font to import from a file.')
        self.selectAll.setToolTip('Select all dictionaries.')
        self.removeAll.setToolTip('Clear the current selection.')

    def resetNew(self):
        self.new = True

    def clearGroupEditor(self, new = False):
        self.groupName.clear()
        self.groupName.setEnabled(True)
        self.setWindowTitle("Add Dictionary Group")
        self.fontFromDropdown.setChecked(True)
        self.toggleFontType(False)
        self.fontFileName.setText('None Selected')
        self.fontToMove = False
        self.fontDropDown.setCurrentIndex(0)
        self.reloadDictTable()
        if new:
            self.resetNew()

    def reloadDictTable(self):
        self.dictionaries.setRowCount(0)
        self.loadDictionaries(self.dictList)

    def loadGroupEditor(self, group, groupName):
        self.clearGroupEditor()
        self.new = False
        self.setWindowTitle("Edit Dictionary Group")
        self.groupName.setText(groupName)
        self.groupName.setEnabled(False)
        if group['customFont']:
            self.fontFromFile.setChecked(True)
            self.toggleFontType(True)
            self.fontFileName.setText(group['font'])
        else:
            self.fontDropDown.setCurrentText(group['font'])
        self.loadSelectedDictionaries(group['dictionaries'])
        
    def loadSelectedDictionaries(self, dicts):
        count = 1
        for d in dicts:
            for i in range(self.dictionaries.rowCount()):
                if d == self.dictionaries.item(i, 0).text():
                    self.dictionaries.item(i, 1).setText(str(count))
                    self.dictionaries.cellWidget(i, 2).setChecked(True)
                    count+= 1

    def getConfig(self):
        return self.mw.addonManager.getConfig(__name__)

    def initHandlers(self):
        self.browseFontFile.clicked.connect(self.grabFontFromFile)
        self.saveButton.clicked.connect(self.saveDictGroup)
        self.cancelButton.clicked.connect(self.hide)
        self.fontFromDropdown.clicked.connect(lambda: self.toggleFontType(False))
        self.fontFromFile.clicked.connect(lambda: self.toggleFontType(True))
        self.selectAll.clicked.connect(self.selectAllDicts)
        self.removeAll.clicked.connect(self.removeAllDicts)

    def selectAllDicts(self):
        for i in range(self.dictionaries.rowCount()):
            cb = self.dictionaries.cellWidget(i, 2)
            if not cb.isChecked():
                cb.setChecked(True)
                self.setDictionaryOrder(i)

        
    def removeAllDicts(self):
        for i in range(self.dictionaries.rowCount()):
            cb = self.dictionaries.cellWidget(i, 2)
            if cb.isChecked():
                cb.setChecked(False)
                self.setDictionaryOrder(i)


    def toggleFontType(self, fromFile):
        if fromFile:
            self.fontDropDown.setEnabled(False)
            self.browseFontFile.setEnabled(True)
            self.fontFileName.setEnabled(True)
        else:
            self.fontDropDown.setEnabled(True)
            self.browseFontFile.setEnabled(False)
            self.fontFileName.setEnabled(False)

    def grabFontFromFile(self):
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        fileName, _ = QFileDialog.getOpenFileName(self,"Select a Custom Font", "",'Font Files (*.ttf *.woff *.woff2 *.eot)', options=options)
        if fileName:
            if not fileName.endswith('.ttf') and not fileName.endswith('.woff') and not fileName.endswith('.woff2') and not fileName.endswith('.eot') :
                miInfo('Please select a font file.', level='err')
                return
            self.fontFileName.setText(ntpath.basename(fileName))
            self.fontToMove = fileName

    def saveDictGroup(self):
        newConfig = self.getConfig()
        gn = self.groupName.text()
        if gn  == '':
            miInfo('The dictionary group must have a name.', level='wrn')
            return
        curGroups = newConfig['DictionaryGroups']
        if self.new and gn in curGroups:
            miInfo('A new dictionary group must have a unique name.', level='wrn')
            return
        if self.fontFromDropdown.isChecked():
            fontName = self.fontDropDown.currentText()
            customFont = False

        else:
            fontName = self.fontFileName.text()
            if fontName == 'None Selected':
                miInfo('You must select a file if you will be using a font from a file.', level='wrn')
                return
            customFont = True
            if not exists(join(self.settings.addonPath,'user_files', 'fonts', fontName)):
                if not self.moveFontToFolder(self.fontToMove):
                    miInfo('The font file was unable to be loaded, please ensure your file exists in the target folder and try again.', level='err')
                    return
        selectedDicts = self.getSelectedDictionaries(True)
        if len(selectedDicts) < 1:
            miInfo('You must select at least one dictionary.', level='wrn')
            return
        dictGroup = {
        'dictionaries' : selectedDicts,
        'customFont' : customFont,
        'font' : fontName
        }
        curGroups[gn] = dictGroup
        self.mw.addonManager.writeConfig(__name__, newConfig)
        self.settings.loadTemplateTable()
        self.settings.loadGroupTable()
        self.hide()

    def getSelectedDictionaries(self, onlyNames = False):
        dicts = []
        for i in range(self.dictionaries.rowCount()):
            order = self.dictionaries.item(i, 1).text()
            if order != '':
                dicts.append([i, int(order), self.dictionaries.item(i, 0).text()])
        dicts = sorted(dicts, key=itemgetter(1))
        if onlyNames:
            return [item[2] for item in dicts]
        return dicts
    
    def setDictionaryOrder(self, row):
        self.dictionaries.selectRow(row)
        if not self.dictionaries.cellWidget(row, 2).isChecked():
            self.dictionaries.item(row, 1).setText('')
            self.reorderDictionaries()
            return
        self.reorderDictionaries(row)

    def reorderDictionaries(self, last = False):
        dicts = self.getSelectedDictionaries()
        for idx, d in enumerate(dicts):
            self.dictionaries.item(d[0], 1).setText(str(idx + 1))
        if last is not False:
            self.dictionaries.item(last, 1).setText(str(len(dicts) + 1))

    def moveFontToFolder(self, filename):
        try:
            basename = ntpath.basename(filename)
            if exists(filename): 
                path = join(self.settings.addonPath, 'user_files', 'fonts', basename)
                if exists(path): 
                    if not miAsk('A font with the same name currently exists in your custom fonts folder. Would you like to overwrite it?', self):
                        return
                copyfile(filename, path)
                return True
            else:
                return False
        except: 
            return False
    
    def setOrder(self, x):
        return lambda: self.setDictionaryOrder(x)

    def getFontCB(self):
        fonts = QComboBox()
        fams = QFontDatabase().families()
        fonts.addItems(fams)
        return fonts

    def loadDictionaries(self, dictionaries):
        for dictName in dictionaries:
            rc = self.dictionaries.rowCount()
            self.dictionaries.setRowCount(rc + 1)
            self.dictionaries.setItem(rc, 0, QTableWidgetItem(dictName))
            self.dictionaries.setItem(rc, 1, QTableWidgetItem(''))
            checkBox =  QCheckBox()
            checkBox.setFixedWidth(40)
            checkBox.setStyleSheet('QCheckBox{padding-left:10px;}')
            self.dictionaries.setCellWidget(rc, 2, checkBox)
            checkBox.clicked.connect(self.setOrder(rc))
        self.addDefaultDict('Google Images')
        self.addDefaultDict('Forvo')



    def addDefaultDict(self, name):
        rc = self.dictionaries.rowCount()
        self.dictionaries.setRowCount(rc + 1)
        self.dictionaries.setItem(rc, 0, QTableWidgetItem(name))
        self.dictionaries.setItem(rc, 1, QTableWidgetItem(''))
        checkBox =  QCheckBox()
        checkBox.setFixedWidth(40)
        checkBox.setStyleSheet('QCheckBox{padding-left:10px;}')
        checkBox.clicked.connect(self.setOrder(rc))
        self.dictionaries.setCellWidget(rc, 2, checkBox)

    def setupDictionaries(self):
        macLin = False
        if isMac  or isLin:
            macLin = True
        dictionaries = QTableWidget()
        dictionaries.setColumnCount(3)
        tableHeader = dictionaries.horizontalHeader()
        tableHeader.setSectionResizeMode(0, QHeaderView.Stretch)
        tableHeader.setSectionResizeMode(1, QHeaderView.Fixed)
        tableHeader.setSectionResizeMode(2, QHeaderView.Fixed)
        dictionaries.setRowCount(0)
        dictionaries.setSortingEnabled(False)
        dictionaries.setEditTriggers(QTableWidget.NoEditTriggers)
        dictionaries.setSelectionBehavior(QAbstractItemView.SelectRows)
        dictionaries.setColumnWidth(1, 40)
        if macLin:
            dictionaries.setColumnWidth(2, 40)
        else:
            dictionaries.setColumnWidth(2, 20)
        tableHeader.hide()
        return dictionaries

    def setupLayout(self):
        nameLayout = QHBoxLayout()
        nameLayout.addWidget(QLabel('Name: '))
        nameLayout.addWidget(self.groupName)

        self.layout.addLayout(nameLayout)

        fontLayoutH1 = QHBoxLayout()
        fontL1 = QLabel('Font: ')
        fontL1.setFixedWidth(100)
        fontLayoutH1.addWidget(fontL1)
        self.fontDropDown.setFixedWidth(175)
        fontLayoutH1.addWidget(self.fontFromDropdown)
        fontLayoutH1.addWidget(self.fontDropDown)
        fontLayoutH1.addStretch()
        self.layout.addLayout(fontLayoutH1)

        fontLayoutH2 = QHBoxLayout()
        fontL2 = QLabel('Font From File:')
        fontL2.setFixedWidth(100)
        fontLayoutH2.addWidget(fontL2)
        fontLayoutH2.addWidget(self.fontFromFile)
        self.fontFileName.setFixedWidth(100)
        self.browseFontFile.setFixedWidth(72)
        fontLayoutH2.addWidget(self.fontFileName)
        fontLayoutH2.addWidget(self.browseFontFile)
        fontLayoutH2.addStretch()
        self.layout.addLayout(fontLayoutH2)

        self.layout.addWidget(QLabel('Dictionaries'))
        self.layout.addWidget(self.dictionaries)

        selRemButtons = QHBoxLayout()
        selRemButtons.addWidget(self.selectAll)
        selRemButtons.addWidget(self.removeAll)
        selRemButtons.addStretch()
        self.layout.addLayout(selRemButtons)

        cancelSaveButtons = QHBoxLayout()
        cancelSaveButtons.addStretch()
        cancelSaveButtons.addWidget(self.cancelButton)
        cancelSaveButtons.addWidget(self.saveButton)

        self.layout.addLayout(cancelSaveButtons)
        self.setLayout(self.layout)





