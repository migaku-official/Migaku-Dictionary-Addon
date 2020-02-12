# -*- coding: utf-8 -*-
# 

from aqt.qt import *
from anki.utils import isMac, isLin, isWin
from aqt.utils import ensureWidgetInScreenBoundaries
from os.path import join, exists
from shutil import copyfile
from .miutils import miInfo, miAsk
from . import Pyperclip
import json
from anki.notes import Note
from anki import sound


class MITextEdit(QPlainTextEdit):
    def __init__(self, parent = None, dictInt = None):
        super(MITextEdit, self).__init__(parent)
        self.dictInt = dictInt

    def contextMenuEvent(self, event):
        menu = super().createStandardContextMenu()
        search = QAction('Search')
        search.triggered.connect(self.searchSelected)
        menu.addAction(search)
        menu.exec_(event.globalPos())

    def searchSelected(self):
        self.dictInt.initSearch(self.selectedText())

    def selectedText(self):
        return self.textCursor().selectedText()


class MILineEdit(QLineEdit):
    def __init__(self, parent = None, dictInt = None):
        super(MILineEdit, self).__init__(parent)
        self.dictInt = dictInt

    def contextMenuEvent(self, event):
        menu = super().createStandardContextMenu()
        search = QAction('Search')
        search.triggered.connect(self.searchSelected)
        menu.addAction(search)
        menu.exec_(event.globalPos())

    def searchSelected(self):
        self.dictInt.initSearch(self.selectedText())

class CardExporter():
    def __init__(self, dictInt, dictWeb, templates = [], sentence = False, word = False, definition = False):
        self.window = QWidget(dictInt, Qt.Window)
        self.window.setAutoFillBackground(True);
        self.dictInt = dictInt
        self.mw = self.dictInt.mw
        self.config = self.getConfig()
        self.dictWeb = dictWeb
        self.layout = QVBoxLayout()
        self.decks = self.getDecks()
        self.templates = self.config['ExportTemplates']
        self.templateCB = self.getTemplateCB()
        self.deckCB = self.getDeckCB()
        self.sentenceLE = MITextEdit(dictInt = dictInt)
        self.wordLE = MILineEdit(dictInt = dictInt)
        self.definitions = self.getDefinitions()
        self.clearButton = QPushButton('Clear Current Card')
        self.cancelButton = QPushButton("Cancel")
        self.addButton = QPushButton("Add")      
        self.exportJS = self.config['jReadingCards']
        self.imgName = False
        self.imgPath = False
        self.audioTag = False
        self.audioName = False
        self.audioPath = False
        self.audioPlayer = sound
        self.audioPlay = QPushButton('Play')
        self.audioPlay.clicked.connect(self.playAudio)
        self.audioPlay.hide()
        self.setupLayout()
        self.initHandlers()
        self.setColors()
        self.window.setLayout(self.layout)
        self.window.resize(400,400)
        self.window.setWindowTitle('Card Exporter')
        self.definitionList = []
        self.word = ''
        self.sentence = ''
        self.initTooltips()
        self.window.show()
        self.restoreSizePos()
        self.window.closeEvent = self.closeEvent
        self.window.hideEvent = self.hideEvent
        self.setHotkeys()
        
    
    def initTooltips(self):
        if self.config['tooltips']:
            self.templateCB.setToolTip('Select the export template.')
            self.deckCB.setToolTip('Select the deck to export to.')
            self.clearButton.setToolTip('Clear the card exporter.')

    def restoreSizePos(self):
        sizePos = self.config['exporterSizePos']
        if sizePos:
            self.window.resize(sizePos[2], sizePos[3])
            self.window.move(sizePos[0], sizePos[1])
            ensureWidgetInScreenBoundaries(self.window)

    def setHotkeys(self):
        self.sentencehotkeyS = QShortcut(
    QKeySequence('Ctrl+S'), self.window, self.attemptSearch)
        self.window.hotkeyEsc = QShortcut(QKeySequence("Esc"), self.window)
        self.window.hotkeyEsc.activated.connect(self.window.hide)

    
    def attemptSearch(self):
        focused = self.window.focusWidget()
        if type(focused).__name__ in  ['MILineEdit', 'MITextEdit']:
            focused.searchSelected()


    def setColors(self):
        if self.dictInt.nightModeToggler.day :
            self.window.setPalette(self.dictInt.ogPalette)
            if isMac:
                self.templateCB.setStyleSheet(self.dictInt.getMacComboStyle())
                self.deckCB.setStyleSheet(self.dictInt.getMacComboStyle())
                self.definitions.setStyleSheet(self.dictInt.getMacTableStyle())
            else:
                self.templateCB.setStyleSheet('')
                self.deckCB.setStyleSheet('')
                self.definitions.setStyleSheet('')
        else:
            self.window.setPalette(self.dictInt.nightPalette)
            if isMac: 
                self.templateCB.setStyleSheet(self.dictInt.getMacNightComboStyle())
                self.deckCB.setStyleSheet(self.dictInt.getMacNightComboStyle())
            else:
                self.templateCB.setStyleSheet(self.dictInt.getComboStyle())
                self.deckCB.setStyleSheet(self.dictInt.getComboStyle())
            self.definitions.setStyleSheet(self.dictInt.getTableStyle())
        
    def addNote(self, note, did):
        note.model()['did'] = did
        ret = note.dupeOrEmpty()
        if ret == 1:
            if not miAsk('Your note\'s sorting field will be empty with this configuration. Would you like to continue?', self.window, self.dictInt.nightModeToggler.day):
                return False
        if '{{cloze:' in note.model()['tmpls'][0]['qfmt']:
            if not self.mw.col.models._availClozeOrds(
                    note.model(), note.joinedFields(), False):
                if not miAsk("You have a cloze deletion note type "
                "but have not made any cloze deletions. Would you like to continue?", self.window, self.dictInt.nightModeToggler.day):
                    return False
        cards = self.mw.col.addNote(note)
        if not cards:
            miInfo(("""\
The current input and template combination \
will lead to a blank card and therefore has not been added. \
Please review your template and notetype combination."""), level='wrn', day = self.dictInt.nightModeToggler.day)
            return False
        self.mw.reset()
        return True

    def getDecks(self):
        decksRaw = self.mw.col.decks.decks
        decks = {}
        for did, deck in decksRaw.items():
            if not deck['dyn']:
                decks[deck['name']] = did
        return decks

    def getDeckCB(self):
        cb = QComboBox()
        decks = list(self.decks.keys())
        decks.sort()
        cb.addItems(decks)
        current = self.config['currentDeck']
        if current in decks:
            cb.setCurrentText(current)
        cb.currentIndexChanged.connect(lambda: self.dictInt.writeConfig('currentDeck', cb.currentText()))
        return cb

    def hideEvent(self, event):
        self.saveSizeAndPos()
        event.accept() 

    def closeEvent(self, event):
        self.clearCurrent()
        self.saveSizeAndPos()
        event.accept() 
        
    def saveSizeAndPos(self):
        pos = self.window.pos()
        x = pos.x()
        y = pos.y()
        size = self.window.size()
        width = size.width()
        height = size.height()
        posSize = [x,y,width, height]
        self.dictInt.writeConfig('exporterSizePos', posSize)

    def initHandlers(self):
        self.clearButton.clicked.connect(self.clearCurrent)
        self.cancelButton.clicked.connect(self.window.close)
        self.addButton.clicked.connect(self.addCard)

    def addCard(self):
        templateName = self.templateCB.currentText()
        if templateName in self.templates:
            template = self.templates[templateName]
            noteType = template['noteType']
            model = self.mw.col.models.byName(noteType)
            if model:
                note = Note(self.mw.col, model)
                modelFields = self.mw.col.models.fieldNames(note.model())
                fieldsValues, imgField, audioField = self.getFieldsValues(template)
                if not fieldsValues:
                    miInfo('The currently selected template and values will lead to an invalid card. Please try again.', level='wrn', day = self.dictInt.nightModeToggler.day)
                    return
                for field in fieldsValues:
                    if field in modelFields:
                        note[field] = template['separator'].join(fieldsValues[field])
                did = False
                deck = self.deckCB.currentText()
                if deck in self.decks:
                    did = self.decks[deck]
                if did:
                    if self.exportJS:
                        note = self.dictInt.jHandler.attemptGenerate(note)
                    if not self.addNote(note, did):
                        return
                if imgField and imgField in modelFields:
                    self.moveImageToMediaFolder()
                if audioField and audioField in modelFields:
                    self.moveAudioToMediaFolder()
                self.clearCurrent()
                return
            else:
                miInfo('The notetype for the currently selected template does not exist in the currently loaded profile.', level='err', day = self.dictInt.nightModeToggler.day)
                return
        miInfo('A card could not be added with this current configuration. Please ensure that your template is configured correctly for this collection.', level='err', day = self.dictInt.nightModeToggler.day)
    
    def moveImageToMediaFolder(self):
        if self.imgPath and self.imgName:
            if exists(self.imgPath): 
                path = join(self.mw.col.media.dir(), self.imgName)
                if not exists(path): 
                    copyfile(self.imgPath, path)

    def fieldValid(self, field):
        return field != 'Don\'t Export'

    def getDictionaryEntries(self, dictionary):
        finList = []
        idxs = []
        for idx, defList in enumerate(self.definitionList):
            if defList[0] == dictionary:
                finList.append(defList[2])
                idxs.append(idx)
        idxs.reverse()
        for idx in idxs:
            self.definitionList.pop(idx)
        return finList

    def getFieldsValues(self, t):
        imgField = False
        audioField = False
        fields = {}
        sentenceText = self.sentenceLE.toPlainText()
        if sentenceText != '':
            sentenceField = t['sentence']
            if sentenceField !=  "Don't Export":
                if self.fieldValid(sentenceField):
                    fields[sentenceField] = [sentenceText]
        wordText = self.wordLE.text()
        if wordText != '':
            wordField = t['word']
            if wordField !=  "Don't Export":
                if self.fieldValid(wordField):
                    if wordField not in fields:
                        fields[wordField] = [wordText]
                    else: 
                        fields[wordField].append(wordText)

        imgText = self.imageMap.text()
        if imgText != 'No Image Selected':
            imgField = t['image']
            imgTag = '<img src="'+ self.imgName +'">'
            if self.fieldValid(imgField):
                if imgField not in fields:
                    fields[imgField] = [imgTag]
                else: 
                    fields[imgField].append(imgTag)
        audioText = self.imageMap.text()
        if audioText != 'No Audio Selected' and 'audio' in t and self.audioTag != False:
            audioField = t['audio']
            if self.fieldValid(audioField):
                if audioField not in fields:
                    fields[audioField] = [self.audioTag]
                else: 
                    fields[audioField].append(self.audioTag)
        specific = t['specific']
        for field in specific:
            for dictionary in specific[field]:
                if field not in fields:
                    fields[field] = self.getDictionaryEntries(dictionary)
                else:
                    fields[field] += self.getDictionaryEntries(dictionary)
        unspecified = t['unspecified']
        for idx, defList in enumerate(self.definitionList):
            if unspecified not in fields:
                fields[unspecified] = [defList[2]]
            else:
                fields[unspecified].append(defList[2])
        return fields, imgField, audioField;

    def clearCurrent(self):
        self.definitions.setRowCount(0)
        self.sentenceLE.clear()
        self.wordLE.clear()
        self.definitionList = []
        self.audioMap.clear()
        self.audioMap.setText('No Audio Selected')
        self.audioPlay.hide()
        self.audioTag = False
        self.audioName = False
        self.audioPath = False
        self.imageMap.clear()
        self.imageMap.setText('No Image Selected')
        self.imgPath = False
        self.imgName = False

    def getDefinitions(self):
        macLin = False
        if isMac  or isLin:
            macLin = True
        definitions = QTableWidget()
        definitions.setColumnCount(3)
        tableHeader = definitions.horizontalHeader()
        vHeader = definitions.verticalHeader()
        vHeader.setSectionResizeMode(QHeaderView.ResizeToContents)
        tableHeader.setSectionResizeMode(0, QHeaderView.Fixed)
        definitions.setColumnWidth(1, 100)
        tableHeader.setSectionResizeMode(1, QHeaderView.Stretch)
        tableHeader.setSectionResizeMode(2, QHeaderView.Fixed)
        definitions.setRowCount(0)
        definitions.setSortingEnabled(False)
        definitions.setEditTriggers(QTableWidget.NoEditTriggers)
        definitions.setSelectionBehavior(QAbstractItemView.SelectRows)
        definitions.setColumnWidth(2, 40)
        tableHeader.hide()
        return definitions

    def getConfig(self):
        return self.mw.addonManager.getConfig(__name__)

    
    def setupLayout(self):
        tempLayout = QHBoxLayout()
        tempLayout.addWidget(QLabel('Template: '))
        self.templateCB.setFixedSize(120, 30)
        tempLayout.addWidget(self.templateCB)
        tempLayout.addWidget(QLabel(' Deck: '))
        self.deckCB.setFixedSize(120, 30)
        tempLayout.addWidget(self.deckCB)
        tempLayout.addStretch()
        tempLayout.setSpacing(2)
        self.clearButton.setFixedSize(130, 30)
        tempLayout.addWidget(self.clearButton)
        self.layout.addLayout(tempLayout)
        sentenceL = QLabel('Sentence')
        self.layout.addWidget(sentenceL)
        self.layout.addWidget(self.sentenceLE)
        wordL = QLabel('Word')
        self.layout.addWidget(wordL)
        self.sentenceLE.setFixedHeight(104)
        f = self.sentenceLE.font()
        f.setPointSize(16)
        self.sentenceLE.setFont(f)
        f = self.wordLE.font()
        f.setPointSize(20) 
        self.wordLE.setFont(f)
        self.layout.addWidget(self.wordLE)
        self.wordLE.setFixedHeight(40)
        definitionsL = QLabel('Definitions')
        self.layout.addWidget(definitionsL)
        self.layout.addWidget(self.definitions)

        self.layout.addWidget(QLabel('Audio'))
        self.audioMap = QLabel('No Audio Selected')
        self.layout.addWidget(self.audioMap)
        self.layout.addWidget(self.audioPlay)
        self.layout.addWidget(QLabel('Image'))
        self.imageMap = QLabel('No Image Selected')
        self.layout.addWidget(self.imageMap)
        buttonLayout = QHBoxLayout()
        buttonLayout.addStretch()
        self.cancelButton.setFixedSize(100, 30)
        self.addButton.setFixedSize(100, 30)
        buttonLayout.addWidget(self.cancelButton)
        buttonLayout.addWidget(self.addButton)
        self.layout.addLayout(buttonLayout)
        self.layout.setContentsMargins(2, 2, 2, 2)
        self.layout.setSpacing(2)

    def getTemplateCB(self):
        cb = QComboBox()
        cb.addItems(self.templates)
        current = self.config['currentTemplate']
        
        cb.currentIndexChanged.connect(lambda: self.dictInt.writeConfig('currentTemplate', cb.currentText()))
        if current in self.templates:
            cb.setCurrentText(current)
        return cb

    def addImgs(self, word, imgs, thumbs):
        self.definitions.resizeRowsToContents()
        self.focusWindow()
        defEntry = ["Google Images", False, imgs, imgs]
        if defEntry in self.definitionList:
            miInfo('A card cannot contain duplicate definitions.', level='not', day = self.dictInt.nightModeToggler.day)
            return
        self.definitionList.append(defEntry)
        rc = self.definitions.rowCount()
        self.definitions.setRowCount(rc + 1)
        self.definitions.setItem(rc, 0, QTableWidgetItem("Google Images"))
        self.definitions.setCellWidget(rc, 1, thumbs)
        deleteButton =  QPushButton("X");
        deleteButton.setFixedWidth(40)
        deleteButton.clicked.connect(lambda: self.removeImgs(imgs))
        self.definitions.setCellWidget(rc, 2, deleteButton)
        if self.wordLE.text() == '':
            self.wordLE.setText(word)

    def removeImgs(self, imgs):
        try:
            row = self.definitions.selectionModel().currentIndex().row()
            self.definitions.removeRow(row)
            self.removeImgFromDefinitionList(imgs)
        except: 
            return
    
    def removeImgFromDefinitionList(self, imgs):
        for idx, entry in enumerate(self.definitionList):
            if entry[0] == 'Google Images' and entry[3] == imgs:
                self.definitionList.pop(idx)
                break

    def addDefinition(self, dictName, word, definition):
        self.focusWindow()
        if len(definition) > 40:
            shortDef = definition.replace('<br>', ' ')[:40] + '...'
        else:
            shortDef = definition.replace('<br>', ' ')
        defEntry = [dictName, shortDef, definition, False]
        if defEntry in self.definitionList:
            miInfo('A card can not contain duplicate definitions.', level='not', day = self.dictInt.nightModeToggler.day)
            return
        self.definitionList.append(defEntry)
        rc = self.definitions.rowCount()
        self.definitions.setRowCount(rc + 1)
        self.definitions.setItem(rc, 0, QTableWidgetItem(dictName))  
        self.definitions.setItem(rc, 1, QTableWidgetItem(shortDef)) 
        deleteButton =  QPushButton("X");
        deleteButton.setFixedWidth(40)
        deleteButton.clicked.connect(self.removeDefinition)
        self.definitions.setCellWidget(rc, 2, deleteButton)
        if self.wordLE.text() == '':
            self.wordLE.setText(word)

    def exportImage(self, path, name):
        self.imgName = name
        self.imgPath = path
        if self.imageMap:
            self.imageMap.setText('')
            screenshot = QPixmap(path)
            screenshot = screenshot.scaled(350,350, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.imageMap.setPixmap(screenshot)


    def exportAudio(self, path, tag,  name):
        self.audioTag = tag
        self.audioName = name
        self.audioPath = path
        self.audioMap.setText(tag)
        self.audioPlay.show()

    def moveAudioToMediaFolder(self):
        if self.audioPath and self.audioName:
            if exists(self.audioPath): 
                path = join(self.mw.col.media.dir(), self.audioName)
                if not exists(path): 
                    copyfile(self.audioPath, path)

    def playAudio(self):
        if self.audioPath:
            self.audioPlayer.play(self.audioPath)

    def exportSentence(self, sentence):
        self.focusWindow()
        self.sentenceLE.setPlainText(sentence)

    def removeFromDefinitionList(self, dictName, shortDef):
        for idx, entry in enumerate(self.definitionList):
            if entry[0] == dictName and entry[1] == shortDef:
                self.definitionList.pop(idx)
                break

    def removeDefinition(self):
        try:
            row = self.definitions.selectionModel().currentIndex().row()
            dictName = self.definitions.item(row, 0).text()
            shortDef = self.definitions.item(row, 1).text()
            self.definitions.removeRow(row)
            self.removeFromDefinitionList(dictName, shortDef)
        except: 
            return
     
    def focusWindow(self):
        self.window.show()
        if self.window.windowState() == Qt.WindowMinimized:
            self.window.setWindowState(Qt.WindowNoState)
        self.window.setFocus()
        self.window.activateWindow()



