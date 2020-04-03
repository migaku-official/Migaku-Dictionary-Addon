# -*- coding: utf-8 -*-
# 
from os.path import dirname, join, basename, exists, join
import sys, os, platform, re, subprocess, aqt.utils
from anki.utils import stripHTML, isWin, isMac, isLin
from . import Pyperclip 
from .midict import DictInterface, ClipThread
import re
import unicodedata
import urllib.parse
from shutil import copyfile
from anki.hooks import addHook, wrap, runHook, runFilter
from aqt.utils import shortcut, saveGeom, saveSplitter, showInfo, askUser
import aqt.editor
import json
from aqt import mw
from aqt.qt import *
from . import dictdb
from aqt.webview import AnkiWebView
from .miutils import miInfo, miAsk
from .addonSettings import SettingsGui
import codecs
from operator import itemgetter
from aqt.addcards import AddCards
from aqt.editcurrent import EditCurrent
from aqt.browser import Browser
from aqt.tagedit import TagEdit
from aqt.reviewer import Reviewer
from . import googleimages
from .forvodl import Forvo
from urllib.request import Request, urlopen
import requests
import time
import os


mw.MIADictConfig = mw.addonManager.getConfig(__name__)
mw.MIAExportingDefinitions = False
mw.dictSettings = False
mw.miDictDB = dictdb.DictDB()
progressBar = False
addon_path = dirname(__file__)
currentNote = False 
currentField = False
currentKey = False
wrapperDict = False
tmpdir = join(addon_path, 'temp')



def refreshMIADictConfig():
    mw.MIADictConfig = mw.addonManager.getConfig(__name__)

mw.refreshMIADictConfig = refreshMIADictConfig

def removeTempFiles():
    filelist = [ f for f in os.listdir(tmpdir)]
    for f in filelist:
        os.remove(os.path.join(tmpdir, f))

removeTempFiles()

def mia(text):
    showInfo(text ,False,"", "info", "MIA Dictionary Add-on")

def showA(ar):
    showInfo(json.dumps(ar, ensure_ascii=False))

def getDirLangs():
    return [name for name in os.listdir(join(addon_path, "user_files", "dictionaries"))
            if os.path.isdir(os.path.join(join(addon_path, "user_files", "dictionaries"), name))]

def getDirDicts(dirLang):
    return [name for name in os.listdir(join(addon_path, "user_files", "dictionaries" , dirLang))
            if os.path.isdir(os.path.join(join(addon_path, "user_files", "dictionaries", dirLang), name))]

def updateDs(lang, dirDs, dbDs, frequencyDict):
    notInDb = [item for item in dirDs if item not in dbDs]
    notInDir = [item for item in dbDs if item not in dirDs]
    if len(notInDb) > 0:
        termHeader = getTermHeader(lang)
        notInDb = mw.miDictDB.addDicts(notInDb, lang, termHeader)
        for current ,d in enumerate(notInDb):
            if current == len(notInDb) - 1:
                getDictFiles(lang, d, frequencyDict, True)
            else:
                getDictFiles(lang, d, frequencyDict)
    if len(notInDir) > 0:
        lid = str(mw.miDictDB.getLangId(lang))
        progressWidget, bar, textL = getDeletionProgress()
        bar.setMaximum(len(notInDir))
        for idx, d in enumerate(notInDir):
            textL.setText('Currently removing the "' + d + '" dictionary for the "' + lang + '" language...')
            mw.app.processEvents() 
            mw.miDictDB.dropTables('l' + lid + 'name' + d)
            mw.miDictDB.deleteDict(d)
            bar.setValue(idx+1)
            mw.app.processEvents() 
        mw.miDictDB.commitChanges()
        mw.miDictDB.c.execute("VACUUM;")
        progressWidget.hide()
        miInfo('All dictionaries successfully removed. The database has been updated to reflect the current directory structure.')


def natural_sort(l): 
    convert = lambda text: int(text) if text.isdigit() else text.lower() 
    alphanum_key = lambda key: [convert(c) for c in re.split('([0-9]+)', key)] 
    return sorted(l, key=alphanum_key)

def getDeletionProgress():
    progressWidget = QWidget(None)
    textDisplay = QLabel()
    progressWidget.setWindowIcon(QIcon(join(addon_path, 'icons', 'mia.png')))
    progressWidget.setWindowTitle("Removing Dictionaries Not Found in Directory...")
    textDisplay.setText("Removing... ")
    progressWidget.setFixedSize(500, 100)
    progressWidget.setWindowModality(Qt.ApplicationModal)
    bar = QProgressBar(progressWidget)
    layout = QVBoxLayout()
    layout.addWidget(textDisplay)
    layout.addWidget(bar)
    progressWidget.setLayout(layout) 
    bar.move(10,10)
    per = QLabel(bar)
    per.setAlignment(Qt.AlignCenter)
    progressWidget.show()
    progressWidget.setFocus()
    return progressWidget, bar, textDisplay;

def getProgressWidgetDict(freq = False):
    progressWidget = QWidget(None)
    textDisplay = QLabel()
    fileCounter = QLabel() 
    progressWidget.setWindowIcon(QIcon(join(addon_path, 'icons', 'mia.png')))
    if freq:
        progressWidget.setWindowTitle("Applying Frequency Data to Dictionary...")
    else:
        progressWidget.setWindowTitle("Dictionary Add-on, Installing Dictionaries...")
    textDisplay.setText("Importing... ")
    fileCounter.setText("File...")
    progressWidget.setFixedSize(500, 100)
    progressWidget.setWindowModality(Qt.ApplicationModal)
    bar = QProgressBar(progressWidget)
    layout = QVBoxLayout()
    layout.addWidget(textDisplay)
    layout.addWidget(fileCounter) 
    layout.addWidget(bar)
    progressWidget.setLayout(layout) 
    bar.move(10,10)
    per = QLabel(bar)
    per.setAlignment(Qt.AlignCenter)
    progressWidget.show()
    progressWidget.setFocus()
    return progressWidget, bar, textDisplay, fileCounter;

def loadDict(files, lang, dictName, frequencyDict, miDict = False, last = False):
    global progressBar
    howMany = len(files)
    count = 1
    progressBar, bar, txtD, fileC = getProgressWidgetDict();
    tableName = 'l' + str(mw.miDictDB.getLangId(lang)) + 'name' + dictName
    jsonDict = []
    for file in files:
        jsonDictPath = join(addon_path, "user_files", "dictionaries" , lang, dictName, file)
        with open(jsonDictPath, "r", encoding="utf-8") as jsonDictFile:
            jsonDict += json.loads(jsonDictFile.read())
    bar.setMinimum(0)
    total = len(jsonDict)
    strTotal = str(total)
    bar.setMaximum(total)
    txtD.setText("Importing dict: '" + dictName + "' into language:'"+ lang + "'.")
    freq = False
    if frequencyDict:
        freq = True
        if miDict:
            jsonDict = organizeDictionaryByFrequency(jsonDict, frequencyDict, dictName, lang, True)
        else:
            jsonDict = organizeDictionaryByFrequency(jsonDict, frequencyDict, dictName, lang)
    for count, entry in enumerate(jsonDict):
        fileC.setText("Importing word " + str(count) + " of " + strTotal + ".")
        if miDict:
            handleMiDictEntry(jsonDict, count, entry, freq)
        else: 
            handleYomiDictEntry(jsonDict, count, entry, freq)
        if count % 5000 == 0:
            bar.setValue(count)
            mw.app.processEvents() 
    mw.miDictDB.importToDict(tableName, jsonDict)
    bar.setValue(total)
    progressBar.hide()
    if last:
        miInfo('Your dictionaries for the "' + lang + '" language have been successfully imported.')     
    mw.miDictDB.commitChanges()
    return

def getAdjustedTerm(term):
    term = term.replace('\n', '')
    if len(term) > 1:
        term = term.replace('=', '')
    return term

def getAdjustedPronunciation(pronunciation):
    return pronunciation.replace('\n', '')

def getAdjustedDefinition(definition):
    definition = definition.replace('<br>','◟')
    definition = definition.replace('<', '&lt;').replace('>', '&gt;')
    definition = definition.replace('◟','<br>').replace('\n', '<br>')
    return re.sub(r'<br>$', '', definition)

def handleMiDictEntry(jsonDict, count, entry, freq = False):
        starCount = ''
        frequency = ''
        if freq:
            starCount = entry['starCount']
            frequency = entry['frequency']
        reading = entry['pronunciation']
        if reading == '':
            reading = entry['term']
        term = getAdjustedTerm(entry['term']) 
        altTerm = getAdjustedTerm(entry['altterm'])
        reading = getAdjustedPronunciation(reading)
        definition = getAdjustedDefinition(entry['definition'])
        jsonDict[count] = (term, altTerm, reading, entry['pos'], definition, '', '', frequency, starCount)

def handleYomiDictEntry(jsonDict, count, entry, freq = False):
        starCount = ''
        frequency = ''
        if freq:
            starCount = entry[9]
            frequency = entry[8]
        reading = entry[1]
        if reading == '':
            reading = entry[0]
        term = getAdjustedTerm(entry[0])
        reading = getAdjustedPronunciation(reading)
        definition = getAdjustedDefinition(', '.join(entry[5]))
        jsonDict[count] = (term, '', reading, entry[2], definition, '', '', frequency, starCount)


def kaner(to_translate, hiraganer = False):
        hiragana = u"がぎぐげござじずぜぞだぢづでどばびぶべぼぱぴぷぺぽ" \
                   u"あいうえおかきくけこさしすせそたちつてと" \
                   u"なにぬねのはひふへほまみむめもやゆよらりるれろ" \
                   u"わをんぁぃぅぇぉゃゅょっゐゑ"
        katakana = u"ガギグゲゴザジズゼゾダヂヅデドバビブベボパピプペポ" \
                   u"アイウエオカキクケコサシスセソタチツテト" \
                   u"ナニヌネノハヒフヘホマミムメモヤユヨラリルレロ" \
                   u"ワヲンァィゥェォャュョッヰヱ"
        if hiraganer:
            katakana = [ord(char) for char in katakana]
            translate_table = dict(zip(katakana, hiragana))
            return to_translate.translate(translate_table)
        else:
            hiragana = [ord(char) for char in hiragana]
            translate_table = dict(zip(hiragana, katakana))
            return to_translate.translate(translate_table) 

def adjustReading(reading):
    return kaner(reading)

def organizeDictionaryByFrequency(jsonDict, frequencyDict, dictName, lang, miDict = False):
    readingHyouki = False
    if frequencyDict['readingDictionaryType']:
        readingHyouki = True
    progressBar, bar, txtD, fileC = getProgressWidgetDict(True);
    progressBar.setFixedWidth(600)
    txtD.setText('Applying frequency data for the "' + lang + '" language to the "'+ dictName + '" dictionary.')
    bar.setMinimum(0)
    total = len(jsonDict)
    strTotal = str(total)
    bar.setMaximum(total)
    for idx, entry in enumerate(jsonDict):
        fileC.setText("Adding frequency information: word " + str(idx) + " of " + strTotal + ".")
        if miDict:
            if readingHyouki:
                reading = entry['pronunciation']
                if reading == '':
                    reading = entry['term']
                adjusted = adjustReading(reading)
            if not readingHyouki and entry['term'] in frequencyDict:
                jsonDict[idx]['frequency'] = frequencyDict[entry['term']]
                jsonDict[idx]['starCount'] = getStarCount(jsonDict[idx]['frequency'])
            elif readingHyouki and entry['term'] in frequencyDict and adjusted in frequencyDict[entry['term']]:
                jsonDict[idx]['frequency'] = frequencyDict[entry['term']][adjusted]
                jsonDict[idx]['starCount'] = getStarCount(jsonDict[idx]['frequency'])
            else:
                jsonDict[idx]['frequency'] = 999999 
                jsonDict[idx]['starCount'] = getStarCount(jsonDict[idx]['frequency'])
            bar.setValue(idx)
        else:
            if readingHyouki:
                reading = entry[1]
                if reading == '':
                    reading = entry[0]
                adjusted = adjustReading(reading)
            if not readingHyouki and entry[0] in frequencyDict:
                if len(entry) > 8:
                    jsonDict[idx][8] = frequencyDict[entry[0]]
                    jsonDict[idx][9] = getStarCount(jsonDict[idx][8])
                else: 
                    jsonDict[idx].append(frequencyDict[entry[0]])
                    jsonDict[idx].append(getStarCount(jsonDict[idx][8]))
            elif readingHyouki and entry[0] in frequencyDict and adjusted in frequencyDict[entry[0]]:
                if len(entry) > 8:
                    jsonDict[idx][8] = frequencyDict[entry[0]][adjusted]
                    jsonDict[idx][9] = getStarCount(jsonDict[idx][8])
                else: 
                    jsonDict[idx].append(frequencyDict[entry[0]][adjusted])
                    jsonDict[idx].append(getStarCount(jsonDict[idx][8]))
            else:
                if len(entry) > 8:
                    jsonDict[idx][8] = 999999
                    jsonDict[idx][9] = ''
                else: 
                    jsonDict[idx].append(999999)
                    jsonDict[idx].append('')
        if idx % 5000 == 0:
            bar.setValue(idx)
            mw.app.processEvents()
    bar.hide()
    if miDict:
        return sorted(jsonDict, key = lambda i: i['frequency'])
    else:
        return sorted(jsonDict, key=itemgetter(8))

def getStarCount(freq):
    if freq < 1501:
        return '★★★★★'
    elif freq < 5001:
        return '★★★★'
    elif freq < 15001:
        return '★★★'
    elif freq < 30001:
        return '★★'
    elif freq < 60001:
        return '★'
    else:
        return ''

def yomichanClean(l):
    return list(filter(lambda x: x.startswith('term_bank_'), l))

def getFrequencyList(lang):
    filePath = join(addon_path, "user_files", 'dictionaries', lang, "frequency.json")
    frequencyDict = {}
    if os.path.exists(filePath):
        frequencyList = json.load(codecs.open(filePath, 'r', 'utf-8-sig'))
        if isinstance(frequencyList[0], str):
            yomi = False
            frequencyDict['readingDictionaryType'] = False 
        elif isinstance(frequencyList[0], list) and len(frequencyList[0]) == 2 and isinstance(frequencyList[0][0], str) and isinstance(frequencyList[0][1], str):
            yomi = True
            frequencyDict['readingDictionaryType'] = True 
        else:
            miInfo('The frequency list you have included seems to be of an incorrect format. Your dictionaries will therefore be imported without frequency information. Please check "frequency.json" and ensure it is of an accepted format and try again.', level='err')
            return False
        for idx, f in enumerate(frequencyList):
            if yomi:
                if f[0] in frequencyDict:
                    frequencyDict[f[0]][f[1]] = idx
                else:
                    frequencyDict[f[0]] = {}
                    frequencyDict[f[0]][f[1]] = idx
            else:
                frequencyDict[f] = idx
        return frequencyDict
    else:
        return False

def getDictFiles(lang, dictName, frequencyDict, last = False):
    files = []
    yomichan = False
    for file in os.listdir(join(addon_path, "user_files", "dictionaries" , lang, dictName)):
        if file.endswith(".json"):
            if not yomichan and file.startswith('term_bank_'):
                yomichan = True
                files.append(file)
            elif not file.startswith('index'):
                files.append(file)
    files = natural_sort(files)
    if not files:
        return
    if yomichan:
        loadDict(yomichanClean(files), lang, dictName, frequencyDict, last = last)
    else:
        loadDict(files, lang, dictName, frequencyDict, True, last = last)

def getTermHeader(lang):
    finalHeader = ['term', 'altterm', 'pronunciation']
    filePath = join(addon_path, "user_files", 'dictionaries', lang, "header.csv")
    if os.path.exists(filePath):
        with open(filePath, "r", encoding="utf-8") as header:
            termHeader = header.read().split(',')
        if not (len(termHeader) == 3 and 'term' in termHeader and 'altterm' in termHeader and 'pronunciation' in termHeader):
            miInfo('The "' + lang + '" folder contains a "termHeader.csv" file that could not be correctly parsed, therefore dictionaries will use the default header. Please ensure the format is correct and try again.', level='err')
        else:
            finalHeader = termHeader
    return json.dumps(finalHeader)

def updateLs(dirls, dbls):
    inBoth = list(set(dirls).intersection(dbls))
    notInDb = [item for item in dirls if item not in dbls]
    notInDir = [item for item in dbls if item not in dirls]
    if len(notInDb) > 0:
        mw.miDictDB.addLanguages(notInDb)
        for lang in notInDb:
            frequencyDict = getFrequencyList(lang)
            termHeader = getTermHeader(lang)
            dicts = getDirDicts(lang)
            if len(dicts) > 0:
                dicts = mw.miDictDB.addDicts(dicts, lang, termHeader)
                for current ,d in enumerate(dicts):
                    if current == len(dicts) - 1:
                        getDictFiles(lang, d, frequencyDict, True)
                    else:
                        getDictFiles(lang, d, frequencyDict)
    if len(notInDir) > 0:
        progressWidget, bar, textL = getDeletionProgress()
        mw.miDictDB.deleteLanguages(notInDir, progressWidget, bar, textL)
        miInfo('The following languages have been successfully removed:<br><br>' + ','.join(notInDir))
    if len(inBoth) > 0:
        for lang in inBoth:
            frequencyDict = getFrequencyList(lang)
            updateDs(lang, getDirDicts(lang), mw.miDictDB.getDictsByLanguage(lang), frequencyDict)

def checkForNewDictDir():
    dbLangs = mw.miDictDB.getCurrentDbLangs()
    dirLangs = getDirLangs()
    updateLs(dirLangs, dbLangs)

dictWidget  = False

js = QFile(':/qtwebchannel/qwebchannel.js')
assert js.open(QIODevice.ReadOnly)
js = bytes(js.readAll()).decode('utf-8')



mw.currentlyPressed = []

def captureKey(keyList):
    key = keyList[0]
    char = str(key)
    if char not in mw.currentlyPressed:
            mw.currentlyPressed.append(char)
    if isWin:
        if 'Key.ctrl_l' in mw.currentlyPressed and "'c'" in mw.currentlyPressed and'Key.space'  in mw.currentlyPressed:
            mw.hkThread.handleSystemSearch()
            mw.currentlyPressed = []
        elif 'Key.ctrl_l' in mw.currentlyPressed and "'c'" in mw.currentlyPressed and 'Key.alt_l' in mw.currentlyPressed:
            mw.hkThread.handleSentenceExport()
            mw.currentlyPressed = []
        elif 'Key.ctrl_l' in mw.currentlyPressed and 'Key.enter' in mw.currentlyPressed:
            mw.hkThread.attemptAddCard()
            mw.currentlyPressed = []
        elif 'Key.ctrl_l' in mw.currentlyPressed and 'Key.shift' in mw.currentlyPressed and "'v'" in mw.currentlyPressed:
            mw.hkThread.handleImageExport()
            mw.currentlyPressed = []
    elif isLin:
        if 'Key.ctrl' in mw.currentlyPressed and "'c'" in mw.currentlyPressed and'Key.space'  in mw.currentlyPressed:
            mw.hkThread.handleSystemSearch()
            mw.currentlyPressed = []
        elif 'Key.ctrl' in mw.currentlyPressed and "'c'" in mw.currentlyPressed and 'Key.alt' in mw.currentlyPressed:
            mw.hkThread.handleSentenceExport()
            mw.currentlyPressed = []
        elif 'Key.ctrl' in mw.currentlyPressed and 'Key.enter' in mw.currentlyPressed:
            mw.hkThread.attemptAddCard()
            mw.currentlyPressed = []
        elif 'Key.ctrl' in mw.currentlyPressed and 'Key.shift' in mw.currentlyPressed and "'v'" in mw.currentlyPressed:
            mw.hkThread.handleImageExport()
            mw.currentlyPressed = []
    else:
        if ('Key.cmd' in mw.currentlyPressed or 'Key.cmd_r' in mw.currentlyPressed)  and "'c'" in mw.currentlyPressed and "'b'"  in mw.currentlyPressed:
            mw.hkThread.handleSystemSearch()
            mw.currentlyPressed = []
        elif ('Key.cmd' in mw.currentlyPressed or 'Key.cmd_r' in mw.currentlyPressed) and "'c'" in mw.currentlyPressed and 'Key.ctrl' in mw.currentlyPressed:
            mw.hkThread.handleSentenceExport()
            mw.currentlyPressed = []
        elif ('Key.cmd' in mw.currentlyPressed or 'Key.cmd_r' in mw.currentlyPressed) and 'Key.enter' in mw.currentlyPressed:
            mw.hkThread.attemptAddCard()
            mw.currentlyPressed = []
        elif ('Key.cmd' in mw.currentlyPressed or 'Key.cmd_r' in mw.currentlyPressed) and 'Key.shift' in mw.currentlyPressed and "'v'" in mw.currentlyPressed:
            mw.hkThread.handleImageExport()
            mw.currentlyPressed = []

   
def releaseKey(keyList):
    key = keyList[0]
    try:
        mw.currentlyPressed.remove(str(key))
    except:
        return
    

def exportSentence(sentence):
    if mw.miaDictionary and mw.miaDictionary.isVisible():
        mw.miaDictionary.dict.exportSentence(sentence)

def exportImage(img):
    if mw.miaDictionary and mw.miaDictionary.isVisible():
        if img[1].startswith('[sound:'):
            mw.miaDictionary.dict.exportAudio(img)
        else:
            mw.miaDictionary.dict.exportImage(img)

def trySearch(term):
    if mw.miaDictionary and mw.miaDictionary.isVisible():
        mw.miaDictionary.initSearch(term)
    elif mw.MIADictConfig['openOnGlobal']:
        mw.dictionaryInit(term)



def attemptAddCard(add):
    if mw.miaDictionary and mw.miaDictionary.isVisible() and mw.miaDictionary.dict.addWindow and mw.miaDictionary.dict.addWindow.window.isVisible():
        time.sleep(.3)
        mw.miaDictionary.dict.addWindow.addCard()


def openDictionarySettings():
    if not mw.dictSettings:
        mw.dictSettings = SettingsGui(mw, addon_path, openDictionarySettings)
    mw.dictSettings.show()
    if mw.dictSettings.windowState() == Qt.WindowMinimized:
            # Window is minimised. Restore it.
           mw.dictSettings.setWindowState(Qt.WindowNoState)
    mw.dictSettings.setFocus()
    mw.dictSettings.activateWindow()


def getWelcomeScreen():
    htmlPath = join(addon_path, 'welcome.html')
    with open(htmlPath,'r', encoding="utf-8") as fh:
        file =  fh.read()
    return file
           
def getMacWelcomeScreen():
    htmlPath = join(addon_path, 'macwelcome.html')
    with open(htmlPath,'r', encoding="utf-8") as fh:
        file =  fh.read()
    return file

if isMac:
    welcomeScreen =  getMacWelcomeScreen()
else:
    welcomeScreen = getWelcomeScreen()


def dictionaryInit(term = False):
    shortcut = '(Ctrl+W)'
    if isMac:
        shortcut = '⌘W'
    if not mw.miaDictionary:
        mw.miaDictionary = DictInterface(mw, addon_path, welcomeScreen, term = term)
        mw.openMiDict.setText("Close Dictionary " + shortcut)
    elif mw.miaDictionary and mw.miaDictionary.isVisible():
        mw.miaDictionary.saveSizeAndPos()
        mw.miaDictionary.hide()
        mw.openMiDict.setText("Open Dictionary "+ shortcut)
    else:
        mw.miaDictionary.dict.close()
        mw.miaDictionary.dict.deleteLater()
        mw.miaDictionary.deleteLater()
        mw.miaDictionary = DictInterface(mw, addon_path, welcomeScreen, term = term)
        mw.openMiDict.setText("Close Dictionary "+ shortcut)

mw.dictionaryInit = dictionaryInit

def setupGuiMenu():
    addMenu = False
    if not hasattr(mw, 'MIAMainMenu'):
        mw.MIAMainMenu = QMenu('MIA',  mw)
        addMenu = True
    if not hasattr(mw, 'MIAMenuSettings'):
        mw.MIAMenuSettings = []
    if not hasattr(mw, 'MIAMenuActions'):
        mw.MIAMenuActions = []

    setting = QAction("Dictionary Settings", mw)
    setting.triggered.connect(openDictionarySettings)
    mw.MIAMenuSettings.append(setting)

    mw.openMiDict = QAction("Open Dictionary (Ctrl+W)", mw)
    mw.openMiDict.triggered.connect(dictionaryInit)
    mw.MIAMenuActions.append(mw.openMiDict)

    mw.MIAMainMenu.clear()
    for act in mw.MIAMenuSettings:
        mw.MIAMainMenu.addAction(act)
    mw.MIAMainMenu.addSeparator()
    for act in mw.MIAMenuActions:
        mw.MIAMainMenu.addAction(act)

    if addMenu:
        mw.form.menubar.insertMenu(mw.form.menuHelp.menuAction(), mw.MIAMainMenu)  

setupGuiMenu()


mw.miaDictionary = False


def initGlobalHotkeys():
    mw.hkThread = ClipThread(mw, addon_path)
    mw.hkThread.sentence.connect(exportSentence)
    mw.hkThread.search.connect(trySearch)
    mw.hkThread.image.connect(exportImage)
    mw.hkThread.add.connect(attemptAddCard)
    mw.hkThread.test.connect(captureKey)
    mw.hkThread.release.connect(releaseKey)
    mw.hkThread.run()

if mw.addonManager.getConfig(__name__)['globalHotkeys'] and not isLin:
    initGlobalHotkeys()

mw.hotkeyW = QShortcut(QKeySequence("Ctrl+W"), mw)
mw.hotkeyW.activated.connect(dictionaryInit)


def selectedText(page):    
    text = page.selectedText()
    if not text:
        return False
    else:
        return text

def searchTerm(self):
    text = selectedText(self)
    if text:
        text = re.sub(r'\[[^\]]+?\]', '', text)
        text = text.strip()
        if not mw.miaDictionary or not mw.miaDictionary.isVisible():
            dictionaryInit(text)
        mw.miaDictionary.ensureVisible()
        mw.miaDictionary.initSearch(text)
        if self.title == 'main webview':
            if mw.state == 'review':
                mw.miaDictionary.dict.setReviewer(mw.reviewer)
        elif self.title == 'editor':
            target = getTarget(type(self.parentEditor.parentWindow).__name__)
            mw.miaDictionary.dict.setCurrentEditor(self.parentEditor, target)



def searchCol(self):
    text = selectedText(self)
    if text:
        text = text.strip()
        browser = aqt.DialogManager._dialogs["Browser"][1]
        if not browser:
            mw.onBrowse()
            browser = aqt.DialogManager._dialogs["Browser"][1]
        if browser:
            browser.form.searchEdit.lineEdit().setText(text)
            browser.onSearchActivated()


mw.searchTerm = searchTerm
mw.searchCol = searchCol

mw.hotkeyS = QShortcut(QKeySequence("Ctrl+S"), mw)
mw.hotkeyS.activated.connect(lambda: searchTerm(mw.web))

def addToContextMenu(self, m):
    a = m.addAction("Search (Ctrl+S)")
    a.triggered.connect(self.searchTerm)
    b = m.addAction("Search Collection")
    b.triggered.connect(self.searchCol)

def exportDefinitionsWidget(browser):
    import anki.find
    notes = browser.selectedNotes()
    if notes:
        fields = anki.find.fieldNamesForNotes(mw.col, notes)
        generateWidget = QDialog(None, Qt.Window)
        layout = QHBoxLayout()
        origin = QComboBox()
        origin.addItems(fields)
        addType = QComboBox()
        addType.addItems(['Add','Overwrite', 'If Empty'])
        dicts = QComboBox()
        dict2 = QComboBox()
        dict3 = QComboBox()
        dictDict = {}
        tempdicts = []
        for d in mw.miDictDB.getAllDicts():
            dictName = mw.miDictDB.cleanDictName(d)
            dictDict[dictName] = d;
            tempdicts.append(dictName)
        tempdicts.append('Google Images')
        tempdicts.append('Forvo')
        dicts.addItems(sorted(tempdicts))
        dict2.addItem('None')
        dict2.addItems(sorted(tempdicts))
        dict3.addItem('None')
        dict3.addItems(sorted(tempdicts))
        dictDict['Google Images'] = 'Google Images'
        dictDict['Forvo'] = 'Forvo'
        dictDict['None'] = 'None'
        ex =  QPushButton('Execute')
        ex.clicked.connect(lambda: exportDefinitions(origin.currentText(), destination.currentText(), addType.currentText(), [dictDict[dicts.currentText()], dictDict[dict2.currentText()] , dictDict[dict3.currentText()]], howMany.value(), notes, generateWidget, [dicts.currentText(),dict2.currentText(), dict3.currentText()]))
        destination = QComboBox()
        destination.addItems(fields)
        howMany = QSpinBox()
        howMany.setValue(1)
        howMany.setMinimum(1)
        howMany.setMaximum(20)
        oLayout = QVBoxLayout()
        oh1 = QHBoxLayout()
        oh2 = QHBoxLayout()
        oh1.addWidget(QLabel('Input Field:'))
        oh1.addWidget(origin)
        oh2.addWidget(QLabel('Output Field:'))
        oh2.addWidget(destination)
        oLayout.addStretch()
        oLayout.addLayout(oh1)
        oLayout.addLayout(oh2)
        oLayout.addStretch()
        oLayout.setContentsMargins(6,0, 6, 0)
        layout.addLayout(oLayout)
        dlay = QHBoxLayout()
        dlay.addWidget(QLabel('Dictionaries:'))
        dictLay = QVBoxLayout()
        dictLay.addWidget(dicts)
        dictLay.addWidget(dict2)
        dictLay.addWidget(dict3)
        dlay.addLayout(dictLay)
        dlay.setContentsMargins(6,0, 6, 0)
        layout.addLayout(dlay)
        bLayout = QVBoxLayout()
        bh1 = QHBoxLayout()
        bh2 = QHBoxLayout()
        bh1.addWidget(QLabel('Output Mode:'))
        bh1.addWidget(addType)
        bh2.addWidget(QLabel('Max Per Dict:'))
        bh2.addWidget(howMany)
        bLayout.addStretch()
        bLayout.addLayout(bh1)
        bLayout.addLayout(bh2)
        bLayout.addStretch()
        bLayout.setContentsMargins(6,0, 6, 0)
        layout.addLayout(bLayout)
        layout.addWidget(ex)
        layout.setContentsMargins(10,6, 10, 6)
        generateWidget.setWindowFlags(generateWidget.windowFlags() | Qt.MSWindowsFixedSizeDialogHint)
        generateWidget.setWindowTitle("Dictionary: Export Definitions")
        generateWidget.setWindowIcon(QIcon(join(addon_path, 'icons', 'mia.png')))
        generateWidget.setLayout(layout)
        generateWidget.exec_()
    else:
        miInfo('Please select some cards before attempting to export definitions.', level='not')

def getProgressWidgetDefs():
    progressWidget = QWidget(None)
    layout = QVBoxLayout()
    progressWidget.setFixedSize(400, 70)
    progressWidget.setWindowIcon(QIcon(join(addon_path, 'icons', 'mia.png')))
    progressWidget.setWindowTitle("Generating Definitions...")
    progressWidget.setWindowModality(Qt.ApplicationModal)
    bar = QProgressBar(progressWidget)
    if isMac:
        bar.setFixedSize(380, 50)
    else:
        bar.setFixedSize(390, 50)
    bar.move(10,10)
    per = QLabel(bar)
    per.setAlignment(Qt.AlignCenter)
    progressWidget.show()
    return progressWidget, bar;

def getTermHeaderText(th, entry, fb, bb):
    headerList = []
    term = entry['term']
    altterm = entry['altterm']
    if altterm == term:
        altterm == ''
    pron = entry['pronunciation']
    if pron == term:
        pron = ''

    termHeader = ''
    for header in th:
        if header == 'term':
            termHeader += fb + term + bb
        elif header == 'altterm':
            if altterm != '':
                termHeader += fb + altterm + bb
        elif header == 'pronunciation':
            if pron != '':
                if termHeader != '':
                    termHeader += ' '
                termHeader  += pron + ' '
    termHeader += entry['starCount']
    return termHeader

def formatDefinitions(results, th,dh, fb, bb):
    definitions = []
    for idx, r in enumerate(results):
        text = ''
        if dh == 0:
           
            text = getTermHeaderText(th, r, fb, bb) + '<br>' + r['definition']
        else:
            stars = r['starCount']
            text =  r['definition'] 
            if '】' in text:
                text = text.replace('】',  '】' + stars + ' ', 1)
            elif '<br>' in text:
                text = text.replace('<br>', stars+ '<br>', 1);
            else:
                text = stars + '<br>' + text
        definitions.append(text)
    return '<br><br>'.join(definitions).replace('<br><br><br>', '<br><br>')

googleImager = None

def initImager():
    global googleImager
    googleImager = googleimages.Google()
    googleImager.setSearchRegion(mw.addonManager.getConfig(__name__)['googleSearchRegion'])

def exportGoogleImages(term, howMany):
    config = mw.addonManager.getConfig(__name__)
    maxW = config['maxWidth']
    maxH = config['maxHeight']
    if not googleImager:
        initImager()
    imgSeparator = ''
    imgs = []
    urls = googleImager.search(term, 80)
    if len(urls) < 1:
        time.sleep(.1)
        urls = googleImager.search(term, 80, 'countryUS')
    for url in urls:
        time.sleep(.1)
        img = downloadImage(url, maxW, maxH)
        if img:
            imgs.append(img)
        if len(imgs) == howMany:
            break
    return imgSeparator.join(imgs)

def downloadImage(url, maxW, maxH):
    try:
        filename = str(time.time()).replace('.', '') + '.png'
        req = Request(url , headers={'User-Agent':  'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.47 Safari/537.36'})
        file = urlopen(req).read()
        image = QImage()
        image.loadFromData(file)
        image = image.scaled(QSize(maxW,maxH), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        image.save(filename)
        return '<img src="' + filename + '">'
    except:
        return False

forvoDler = False;
def initForvo():
    global forvoDler
    forvoDler= Forvo(mw.addonManager.getConfig(__name__)['ForvoLanguage'])


import base64
def decodeURL(url1, url2, protocol, audiohost, server):
    url2 = protocol + "//" + server + "/player-mp3-highHandler.php?path=" + url2;
    url1 = protocol + "//" + audiohost + "/mp3/" + base64.b64decode(url1).decode("utf-8", "strict")
    return url1, url2

    

def generateURLS(results, language):
    audio = re.findall(r'var pronunciations = \[([\w\W\n]*?)\];', results)
    if not audio:
        return []
    audio = audio[0]
    data = re.findall(language + r'.*?Pronunciation by (?:<a.*?>)?(\w+).*?class="lang_xx"\>(.*?)\<.*?,.*?,.*?,.*?,\'(.+?)\',.*?,.*?,.*?\'(.+?)\'', audio)     
    if data:
        server = re.search(r"var _SERVER_HOST=\'(.+?)\';", results).group(1)
        audiohost = re.search(r'var _AUDIO_HTTP_HOST=\'(.+?)\';', results).group(1)
        protocol = 'https:'
        urls = []
        for datum in data:
            urls.append(decodeURL(datum[2],datum[3],protocol, audiohost, server))
        return urls
        


def exportForvoAudio(term, howMany, lang):
    if not forvoDler:
        initForvo()
    audioSeparator = ''
    urls = forvoDler.search(term, lang)
    if len(urls) < 1:
        time.sleep(.1)
        urls = forvoDler.search(term)
    tags = downloadForvoAudio(urls, howMany)
    return audioSeparator.join(tags)

def downloadForvoAudio( urls, howMany):
    tags = []
    for url in urls:
        if len(tags) == howMany:
            break
        try:
            req = Request(url[3] , headers={'User-Agent':  'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.47 Safari/537.36'})
            file = urlopen(req).read()
            filename = str(time.time()) + '.mp3'
            open(join(mw.col.media.dir(), filename), 'wb').write(file)
            tags.append('[sound:' + filename + ']')
            success = True
        except: 
            success = True
        if success:
            continue
        else:
            try:
                req = Request(url[2] , headers={'User-Agent':  'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.47 Safari/537.36'})
                file = urlopen(req).read()
                filename = str(time.time()) + '.mp3'
                open(join(mw.col.media.dir(), filename), 'wb').write(file)
                tags.append('[sound:' + filename + ']')
            except:
                continue
    return tags



def closeBar(event):
    mw.MIAExportingDefinitions = False
    event.accept()


def exportDefinitions(og, dest, addType, dictNs, howMany, notes, generateWidget, rawNames):
    mw.checkpoint('Definition Export')
    if not miAsk('Are you sure you want to export definitions for the "'+ og + '" field into the "' + dest +'" field?'):
        return
    progWid, bar = getProgressWidgetDefs()   
    progWid.closeEvent = closeBar
    bar.setMinimum(0)
    bar.setMaximum(len(notes))
    val = 0;
    config = mw.addonManager.getConfig(__name__)
    fb = config['frontBracket']
    bb = config['backBracket']
    lang = mw.addonManager.getConfig(__name__)['ForvoLanguage']
    mw.MIAExportingDefinitions = True
    for nid in notes:
        if not mw.MIAExportingDefinitions:
            break
        note = mw.col.getNote(nid)
        fields = mw.col.models.fieldNames(note.model())
        if og in fields and dest in fields:
            term = re.sub(r'<[^>]+>', '', note[og]) 
            term = re.sub(r'\[[^\]]+?\]', '', term)
            if term == '':
                continue
            tresults = []
            dCount = 0
            for dictN in dictNs:
                if dictN == 'Google Images':
                    tresults.append(exportGoogleImages( term, howMany))
                elif dictN == 'Forvo':
                    tresults.append(exportForvoAudio( term, howMany, lang))
                elif dictN != 'None':
                    dresults, dh, th = mw.miDictDB.getDefForMassExp(term, dictN, str(howMany), rawNames[dCount])
                    tresults.append(formatDefinitions(dresults, th, dh, fb, bb))
                dCount+= 1
            results = '<br><br>'.join([i for i in tresults if i != ''])      
            if addType == 'If Empty':
                if note[dest] == '':
                    note[dest] = results
            elif addType == 'Add':
                if note[dest] == '':
                    note[dest] = results
                else:
                    note[dest] += '<br><br>' + results
            else:
                note[dest] = results
            note.flush()
        val+=1;
        bar.setValue(val)
        mw.app.processEvents()
    mw.progress.finish()
    mw.reset()
    generateWidget.hide()
    generateWidget.deleteLater()

def dictOnStart():
    if mw.addonManager.getConfig(__name__)['dictOnStart']:
        mw.dictionaryInit()

def setupMenu(browser):
    a = QAction("Export Definitions", browser)
    a.triggered.connect(lambda: exportDefinitionsWidget(browser))
    browser.form.menuEdit.addSeparator()
    browser.form.menuEdit.addAction(a)

def closeDictionary():
    if mw.miaDictionary and mw.miaDictionary.isVisible():
        mw.miaDictionary.saveSizeAndPos()
        mw.miaDictionary.hide()
        mw.openMiDict.setText("Open Dictionary (Ctrl+W)")

def checkInstalledDicts():
    dicts = mw.miDictDB.getAllDicts()
    if len(dicts) == 0:
        miInfo('You currently have 0 dictionaries installed. For instructions on how to install dictionaries, and a link to open source dictionaries in the correct format, please refer to the user guide tab of the settings menu.')


addHook("unloadProfile", closeDictionary)
AnkiWebView.searchTerm = searchTerm
AnkiWebView.searchCol = searchCol
addHook("EditorWebView.contextMenuEvent", addToContextMenu)
addHook("AnkiWebView.contextMenuEvent", addToContextMenu)
addHook("profileLoaded", dictOnStart)
addHook("profileLoaded", checkForNewDictDir)
addHook("profileLoaded", checkInstalledDicts)
addHook("browser.setupMenus", setupMenu)

def bridgeReroute(self, cmd):
    if cmd == "bodyClick":
        if mw.miaDictionary and mw.miaDictionary.isVisible() and self.note:
            widget = type(self.widget.parentWidget()).__name__
            if widget == 'QWidget':
                widget = 'Browser'
            target = getTarget(widget)
            mw.miaDictionary.dict.setCurrentEditor(self, target)
    else:
        if cmd.startswith("focus"):
            
            if mw.miaDictionary and mw.miaDictionary.isVisible() and self.note:
                widget = type(self.widget.parentWidget()).__name__
                if widget == 'QWidget':
                    widget = 'Browser'
                target = getTarget(widget)
                mw.miaDictionary.dict.setCurrentEditor(self, target)
        ogReroute(self, cmd)
    
ogReroute = aqt.editor.Editor.onBridgeCmd 
aqt.editor.Editor.onBridgeCmd = bridgeReroute

def setBrowserEditor(browser, c , p):
    if mw.miaDictionary and mw.miaDictionary.isVisible():
        if browser.editor.note:
            mw.miaDictionary.dict.setCurrentEditor(browser.editor, 'Browser')
        else:
            mw.miaDictionary.dict.closeEditor()

def checkCurrentEditor(self):
    if mw.miaDictionary and mw.miaDictionary.isVisible():
        mw.miaDictionary.dict.checkEditorClose(self.editor)

Browser._onRowChanged = wrap(Browser._onRowChanged, setBrowserEditor)

AddCards._reject = wrap(AddCards._reject, checkCurrentEditor)
EditCurrent._saveAndClose = wrap(EditCurrent._saveAndClose, checkCurrentEditor)
Browser._closeWindow = wrap(Browser._closeWindow, checkCurrentEditor)

def addEditActivated(self, event = False):
    if mw.miaDictionary and mw.miaDictionary.isVisible():
        mw.miaDictionary.dict.setCurrentEditor(self.editor, getTarget(type(self).__name__))

bodyClick = '''document.addEventListener("click", function (ev) {
        pycmd("bodyClick")
    }, false);'''

def addBodyClick(self):
    self.web.eval(bodyClick)

def addClickEvent(self):
    self.historyButton.clicked.connect(lambda: attention(self))

AddCards.addCards = wrap(AddCards.addCards, addEditActivated)
AddCards.onHistory = wrap(AddCards.onHistory, addEditActivated)


def addHotkeys(self):
    self.parentWindow.hotkeyS = QShortcut(QKeySequence("Ctrl+S"), self.parentWindow)
    self.parentWindow.hotkeyS.activated.connect(lambda: searchTerm(self.web))
    self.parentWindow.hotkeyW = QShortcut(QKeySequence("Ctrl+W"), self.parentWindow)
    self.parentWindow.hotkeyW.activated.connect(dictionaryInit)


def addHotkeysToPreview(self):
    self._previewWeb.hotkeyS = QShortcut(QKeySequence("Ctrl+S"), self._previewWeb)
    self._previewWeb.hotkeyS.activated.connect(lambda: searchTerm(self._previewWeb))
    self._previewWeb.hotkeyW = QShortcut(QKeySequence("Ctrl+W"), self._previewWeb)
    self._previewWeb.hotkeyW.activated.connect(dictionaryInit)

Browser._openPreview = wrap(Browser._openPreview, addHotkeysToPreview)


def addEditorFunctionality(self):
    self.web.parentEditor = self
    addBodyClick(self)
    addHotkeys(self)
    
def gt(obj):
    return type(obj).__name__

def getTarget(name):
    if name == 'AddCards':
        return 'Add'
    elif name == "EditCurrent":
        return 'Edit'
    elif name == 'Browser':
        return name

def announceParent(self, event = False):
    if mw.miaDictionary and mw.miaDictionary.isVisible():
        parent = self.parentWidget().parentWidget().parentWidget()
        pName = gt(parent)
        if gt(parent) not in ['AddCards', 'EditCurrent']:
            parent =  aqt.DialogManager._dialogs["Browser"][1]
            pName = 'Browser'
            if not parent:
                return
        mw.miaDictionary.dict.setCurrentEditor(parent.editor, getTarget(pName))
            
def addClickToTags(self):
    self.tags.clicked.connect(lambda: announceParent(self))

TagEdit.focusInEvent = wrap(TagEdit.focusInEvent, announceParent)
aqt.editor.Editor.setupWeb = wrap(aqt.editor.Editor.setupWeb, addEditorFunctionality)
AddCards.mousePressEvent = addEditActivated
EditCurrent.mousePressEvent = addEditActivated

def miLinks(self, cmd):
    if mw.miaDictionary and mw.miaDictionary.isVisible():
        mw.miaDictionary.dict.setReviewer(self)
    return ogLinks(self, cmd)

ogLinks = Reviewer._linkHandler
Reviewer._linkHandler = miLinks
Reviewer.show = wrap(Reviewer.show, addBodyClick)
