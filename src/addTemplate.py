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
import re
from . import Pyperclip 
import os
from os.path import dirname, join
from .miutils import miInfo, miAsk

class TemplateEditor(QWidget):
    def __init__(self, mw, parent = None, dictionaries = [], toEdit = False, tName = False):
        super(TemplateEditor, self).__init__(parent, Qt.Window)
        self.setMinimumSize(QSize(400, 0))
        self.setWindowTitle("Add Export Template")
        self.settings = parent
        self.mw = mw
        self.templateName = QLineEdit()
        self.noteType = QComboBox()
        self.wordField = QComboBox()
        self.sentenceField = QComboBox()
        self.imageField = QComboBox()
        self.audioField = QComboBox()
        self.otherDictsField = QComboBox()
        self.dictionaries = QComboBox()
        self.fields = QComboBox()
        self.addDictField = QPushButton('Add')
        self.dictFieldsTable = self.getDictFieldsTable()
        self.entrySeparator = QLineEdit()
        self.dictionaryNames = dictionaries
        self.cancelButton = QPushButton('Cancel')
        self.saveButton = QPushButton('Save')
        self.layout = QVBoxLayout()
        self.notesFields = self.getNotesFields()
        self.setupLayout()
        self.loadTemplateEditor(toEdit, tName, True)
        self.initHandlers()
        self.initTooltips()
        self.show()

    def initTooltips(self):
        self.templateName.setToolTip('The name of the export template.')
        self.noteType.setToolTip('The note type to export to.')
        self.wordField.setToolTip('The destination field for your target word.')
        self.sentenceField.setToolTip('The destination field for the sentence.')
        self.imageField.setToolTip('The destination field for an image pasted from\nthe clipboard with Ctrl/⌘+shift+v.')
        self.audioField.setToolTip('The destination field for an mp3 audio file pasted from\nthe clipboard with Ctrl/⌘+shift+v.')
        self.otherDictsField.setToolTip('The destination field for any dictionary\nwithout a specific destination field set below.')
        self.dictionaries.setToolTip('The dictionary to specify a particular field to.\nThe dictionaries will be prioritized and exported before\ndictionaries without a specified destination field.')
        self.fields.setToolTip('The dictionary\'s destination field.')
        self.addDictField.setToolTip('Add this dictionary/destination field combination.')
        self.entrySeparator.setToolTip('The separator that will be used in the case multiple\nitems(the sentence/word/image/definitions) are exported to the same destination field.\nBy default two line breaks are used ("<br><br>").')

    def clearTemplateEditor(self):
        self.templateName.clear()
        self.setWindowTitle("Add Export Template")
        self.templateName.setEnabled(True)
        self.noteType.clear()
        self.wordField.clear()
        self.sentenceField.clear()
        self.imageField.clear()
        self.audioField.clear()
        self.otherDictsField.clear()
        self.dictionaries.clear()
        self.fields.clear()
        self.dictFieldsTable.setRowCount(0)
        self.entrySeparator.clear()

    def loadTemplateEditor(self, toEdit = False, tName = False, first = False):
        self.clearTemplateEditor()
        
        self.loadDictionaries()
        if not toEdit:
            self.new = True
            self.loadSepValue()
            self.initialNoteFieldsLoad()
        else:
            self.new = False
            self.initialNoteFieldsLoad(False)
            self.templateName.setText(tName)
            self.loadTemplateForEdit(toEdit)
            self.loadTableForEdit(toEdit['specific'])

    def loadTemplateForEdit(self, t):
        self.setWindowTitle("Edit Export Template")
        self.templateName.setEnabled(False)
        self.noteType.setCurrentText(t['noteType'])
        self.sentenceField.setCurrentText(t['sentence'])
        self.wordField.setCurrentText(t['word'])
        self.imageField.setCurrentText(t['image'])
        if 'audio' in t:
            self.audioField.setCurrentText(t['audio'])
        self.otherDictsField.setCurrentText(t['unspecified'])
        self.entrySeparator.setText(t['separator'])

    def loadTableForEdit(self, fieldsDicts):
        for field, dictList in fieldsDicts.items():
            for dictName in dictList:
                self.addDictFieldRow(dictName, field)

    def getConfig(self):
        return self.mw.addonManager.getConfig(__name__)

    def getSpecificDictFields(self):
        dictFields = {}
        for i in range(self.dictFieldsTable.rowCount()):
            dictn = self.dictFieldsTable.item(i, 0).text()
            fieldn = self.dictFieldsTable.item(i, 1).text()
            if fieldn not in dictFields:
                dictFields[fieldn] = [dictn]
            else:
                dictFields[fieldn].append(dictn)
        return dictFields
        
    def saveExportTemplate(self):
        newConfig = self.getConfig()
        tn = self.templateName.text()
        if tn  == '':
            miInfo('The export template must have a name.', level='wrn')
            return
        curGroups = newConfig['ExportTemplates']
        if self.new and tn in curGroups:
            miInfo('A new export template must have a unique name.', level='wrn')
            return
        exportTemplate = {
        'noteType' : self.noteType.currentText(),
        'sentence' : self.sentenceField.currentText(),
        'word' : self.wordField.currentText(),
        'image' : self.imageField.currentText(),
        'audio' :   self.audioField.currentText(),
        'unspecified' : self.otherDictsField.currentText(),
        'specific' : self.getSpecificDictFields(),
        'separator' : self.entrySeparator.text()
        }
        curGroups[tn] = exportTemplate
        self.mw.addonManager.writeConfig(__name__, newConfig)
        self.settings.loadTemplateTable()
        self.hide()
         
    def loadSepValue(self):
        self.entrySeparator.setText('<br><br>')

    def getDictFieldsTable(self):
        macLin = False
        if isMac  or isLin:
            macLin = True
        dictFields = QTableWidget()
        dictFields.setColumnCount(3)
        tableHeader = dictFields.horizontalHeader()
        tableHeader.setSectionResizeMode(0, QHeaderView.Stretch)
        tableHeader.setSectionResizeMode(1, QHeaderView.Stretch)
        tableHeader.setSectionResizeMode(2, QHeaderView.Fixed)
        dictFields.setRowCount(0)
        dictFields.setSortingEnabled(False)
        dictFields.setEditTriggers(QTableWidget.NoEditTriggers)
        dictFields.setSelectionBehavior(QAbstractItemView.SelectRows)
        dictFields.setColumnWidth(2, 40)
        tableHeader.hide()
        return dictFields

    def initHandlers(self):
        self.noteType.currentIndexChanged.connect(self.loadNoteFields)
        self.addDictField.clicked.connect(self.addDictFieldRow)
        self.saveButton.clicked.connect(self.saveExportTemplate)
        self.cancelButton.clicked.connect(self.hide)

    def notInTable(self, dictName):
        for i in range(self.dictFieldsTable.rowCount()):
            if self.dictFieldsTable.item(i, 0).text() == dictName:
                return False
        return True

    def addDictFieldRow(self, dictName = False, fieldName = False):
        if not dictName:
            dictName = self.dictionaries.currentText()
        if not fieldName:
            fieldName = self.fields.currentText()
        if self.notInTable(dictName):
            rc = self.dictFieldsTable.rowCount()
            self.dictFieldsTable.setRowCount(rc + 1)
            self.dictFieldsTable.setItem(rc, 0, QTableWidgetItem(dictName))
            self.dictFieldsTable.setItem(rc, 1, QTableWidgetItem(fieldName))
            deleteButton =  QPushButton("X");
            deleteButton.setFixedWidth(40)
            deleteButton.clicked.connect(self.removeDictField)
            self.dictFieldsTable.setCellWidget(rc, 2, deleteButton)

    def removeDictField(self):
        self.dictFieldsTable.removeRow(self.dictFieldsTable.selectionModel().currentIndex().row())

    def loadNoteFields(self):
        curNote = self.noteType.currentText()

        if curNote in self.notesFields:
            fields = self.notesFields[curNote]
            fields.sort()
            self.sentenceField.clear()
            self.sentenceField.addItem("Don't Export")
            self.sentenceField.addItems(fields)
            self.wordField.clear()
            self.wordField.addItem("Don't Export")
            self.wordField.addItems(fields)
            self.imageField.clear()
            self.imageField.addItems(fields)
            self.audioField.clear()
            self.audioField.addItems(fields)
            self.otherDictsField.clear()
            self.otherDictsField.addItems(fields)
            self.fields.clear()
            self.fields.addItems(fields)
            self.dictFieldsTable.setRowCount(0)
            
    def getNotesFields(self):
        notesFields = {}
        models = self.mw.col.models.all()
        for model in models:
            notesFields[model['name']] = []
            for fld in model['flds']:
                notesFields[model['name']].append(fld['name'])
        return notesFields

    def loadDictionaries(self):
        self.dictionaries.addItems(self.dictionaryNames)
        self.dictionaries.addItem('Google Images')
        self.dictionaries.addItem('Forvo')

    def initialNoteFieldsLoad(self, loadFields = True):
        noteTypes = list(self.notesFields.keys())
        noteTypes.sort()
        self.noteType.addItems(noteTypes)
        if loadFields:

            fields = self.notesFields[noteTypes[0]]
            fields.sort()
            self.sentenceField.clear()
            self.sentenceField.addItem("Don't Export")
            self.sentenceField.addItems(fields)
            self.wordField.clear()
            self.wordField.addItem("Don't Export")
            self.wordField.addItems(fields)
            self.imageField.clear()
            self.imageField.addItems(fields)
            self.audioField.clear()
            self.audioField.addItems(fields)
            self.otherDictsField.clear()
            self.otherDictsField.addItems(fields)
            self.fields.clear()
            self.fields.addItems(fields)
            

    def setupLayout(self):
        tempNameLay = QHBoxLayout()
        tempNameLay.addWidget(QLabel('Name: '))
        tempNameLay.addWidget(self.templateName)
        self.layout.addLayout(tempNameLay)

        noteTypeLay = QHBoxLayout()
        noteTypeLay.addWidget(QLabel('Notetype: '))
        noteTypeLay.addWidget(self.noteType)
        self.layout.addLayout(noteTypeLay)

        sentenceLay = QHBoxLayout()
        sentenceLay.addWidget(QLabel('Sentence Field:'))
        sentenceLay.addWidget(self.sentenceField)
        self.layout.addLayout(sentenceLay)

        wordLay = QHBoxLayout()
        wordLay.addWidget(QLabel('Word Field:'))
        wordLay.addWidget(self.wordField)
        self.layout.addLayout(wordLay)

        imageLay = QHBoxLayout()
        imageLay.addWidget(QLabel('Image Field:'))
        imageLay.addWidget(self.imageField)
        self.layout.addLayout(imageLay)

        audioLay = QHBoxLayout()
        audioLay.addWidget(QLabel('Audio Field:'))
        audioLay.addWidget(self.audioField)
        self.layout.addLayout(audioLay)

        otherDictsLay = QHBoxLayout()
        otherDictsLay.addWidget(QLabel('Unspecified Dictionaries Field:'))
        otherDictsLay.addWidget(self.otherDictsField)
        self.layout.addLayout(otherDictsLay)

        dictFieldLay = QHBoxLayout()
        dictFieldLay.addWidget(self.dictionaries)
        dictFieldLay.addWidget(self.fields)
        dictFieldLay.addWidget(self.addDictField)
        self.layout.addLayout(dictFieldLay)

        self.layout.addWidget(self.dictFieldsTable)

        separatorLay = QHBoxLayout()
        separatorLay.addWidget(QLabel('Entry Separator: '))
        separatorLay.addWidget(self.entrySeparator)
        separatorLay.addStretch()
        self.layout.addLayout(separatorLay)

        cancelSaveButtons = QHBoxLayout()
        cancelSaveButtons.addStretch()
        cancelSaveButtons.addWidget(self.cancelButton)
        cancelSaveButtons.addWidget(self.saveButton)
        self.layout.addLayout(cancelSaveButtons)

        self.setLayout(self.layout)

        