# -*- coding: utf-8 -*-
# 

from aqt.utils import shortcut, saveGeom, saveSplitter, showInfo, askUser, ensureWidgetInScreenBoundaries
import json
import sys
import math
from anki.hooks import runHook
from aqt.qt import *
from aqt.utils import openLink, tooltip
from anki.utils import isMac, isWin, isLin
from anki.lang import _
from aqt.webview import AnkiWebView
import re
from shutil import copyfile
from . import Pyperclip 
import os, shutil
from os.path import join, exists, dirname
from .history import HistoryBrowser, HistoryModel
from aqt.editor import Editor
from .cardExporter import CardExporter
import time
from . import dictdb
import aqt
from .miJapaneseHandler import miJHandler
from urllib.request import Request, urlopen
import requests
import urllib.request
from . import googleimages
from .addonSettings import SettingsGui
import datetime
import codecs
from .forvodl import Forvo
import ntpath
from .miutils import miInfo

class MIDict(AnkiWebView):

    def __init__(self, dictInt, db, path, day, term):
        AnkiWebView.__init__(self)
        self._page.profile().setHttpUserAgent('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.47 Safari/537.36')
        self.dictInt = dictInt
        self.config = self.dictInt.getConfig()
        self.jSend = self.config['jReadingEdit']
        self.maxW = self.config['maxWidth']
        self.maxH = self.config['maxHeight']
        self.onBridgeCmd = self.handleDictAction
        self.db = db
        self.termHeaders = self.formatTermHeaders(self.db.getTermHeaders())
        self.dupHeaders = self.db.getDupHeaders()
        self.sType = False
        self.radioCount = 0
        self.homeDir = path
        self.conjugations = self.loadConjugations()
        self.deinflect = True
        self.addWindow = False
        self.currentEditor = False
        self.reviewer = False
        self.imager = googleimages.Google()
        self.imager.setSearchRegion(self.config['googleSearchRegion'])
        self.imager.resultsFound.connect(self.loadImageResults)
        self.imager.noResults.connect(self.showGoogleForvoMessage)
        self.forvo =  Forvo(self.config['ForvoLanguage'])
        self.forvo.resultsFound.connect(self.loadForvoResults)
        self.forvo.noResults.connect(self.showGoogleForvoMessage)
        self.customFontsLoaded = []

    def showGoogleForvoMessage(self, message):
        miInfo(message, level='err')

    def loadImageResults(self, results):
        html, idName = results
        self.eval("loadImageForvoHtml('%s', '%s');"%(html.replace('"', '\\"'), idName))

    def loadHTMLURL(self, html, url):
        self._page.setHtml(html, url)

    def formatTermHeaders(self, ths):
        formattedHeaders = {}
        if not ths:
            return None
        for dictname in ths:
            headerString = ''
            sbHeaderString = ''
            for header in ths[dictname]:
                if header == 'term':
                    headerString += '◳f<span class="term mainword">◳t</span>◳b'
                    sbHeaderString += '◳f<span class="listTerm">◳t</span>◳b'
                elif header == 'altterm':
                    headerString += '◳x<span class="altterm  mainword">◳a</span>◳y'
                    sbHeaderString += '◳x<span class="listAltTerm">◳a</span>◳y'
                elif header == 'pronunciation':
                    headerString += '<span class="pronunciation">◳p</span>'
                    sbHeaderString += '<span class="listPronunciation">◳p</span>'
            formattedHeaders[dictname] = [headerString, sbHeaderString]
        return formattedHeaders

    def setSType(self, sType):
        self.sType = sType

    def loadConjugations(self):
        langs = self.db.getCurrentDbLangs()
        conjugations = {}
        for lang in langs:
            filePath = join(self.homeDir, "user_files", 'dictionaries', lang, "conjugations.json")
            if not os.path.exists(filePath):
                continue
            with open(filePath, "r", encoding="utf-8") as conjugationsFile:
                conjugations[lang] = json.loads(conjugationsFile.read())
        return conjugations          

    def cleanTerm(self, term):
        return term.replace("'", "\'").replace('%', '').replace('_', '').replace('「', '').replace('」', '')

    def getFontFamily(self, group):
        if not group['font']:
            return ' '
        if group['customFont']:
            return ' style="font-family:'+ re.sub(r'\..*$', '' , group['font']) + ';" '
        else:
            return ' style="font-family:'+ group['font'] + ';" '

    def injectFont(self, font):
        name = re.sub(r'\..*$', '' , font) 
        self.eval("addCustomFont('%s', '%s');"%(font, name))

    def getTabMode(self):
        if self.dictInt.tabB.singleTab:
            return 'true'
        return 'false'

    def getHTMLResult(self,term, selectedGroup):
        singleTab = self.getTabMode()
        cleaned = self.cleanTerm(term)
        font = self.getFontFamily(selectedGroup)
        dictDefs = self.config['dictSearch']
        maxDefs = self.config['maxSearch']
        html = self.prepareResults(self.db.searchTerm(term, selectedGroup, self.conjugations, self.sType.currentText(), self.deinflect, str(dictDefs), maxDefs), cleaned, font)
        html = html.replace('\n', '')
        return html, cleaned, singleTab;

          
    def addNewTab(self, term, selectedGroup):
        if selectedGroup['customFont'] and selectedGroup['font'] not in self.customFontsLoaded:
            self.customFontsLoaded.append(selectedGroup['font'])
            self.injectFont(selectedGroup['font'])
        html, cleaned, singleTab= self.getHTMLResult(term, selectedGroup)
        # Pyperclip.copy("addNewTab('%s', '%s', %s);"%(html, cleaned, singleTab))
        # showInfo(term)
        self.eval("addNewTab('%s', '%s', %s);"%(html.replace('\r', '<br>').replace('\n','<br>'), cleaned, singleTab))
        
    def addResultWrappers(self, results):
        for idx, result in enumerate(results):
            if 'dictionaryTitleBlock' not in result:
                results[idx] = '<div class="definitionBlock">' + result + '</div>'
        return results

    def escapePunctuation(self, term):
        return re.sub(r'([.*+(\[\]{}\\?)!])', '\\\1', term)

    def highlightTarget(self, text, term):
        if self.config['highlightTarget']:
            return  re.sub(u'('+ self.escapePunctuation(term) + ')', r'<span class="targetTerm">\1</span>', text)
        return text

    def highlightExamples(self, text):
        if self.config['highlightSentences']:
            return re.sub(u'(「[^」]+」)', r'<span class="exampleSentence">\1</span>', text)
        return text

    def getSideBar(self, results, term, font, frontBracket, backBracket):
        html = '<div' + font +'class="definitionSideBar"><div class="innerSideBar">'
        dictCount = 0
        entryCount = 0
        for dictName, dictResults in results.items():
                if dictName == 'Google Images' or dictName == 'Forvo':
                    html += '<div data-index="' + str(dictCount)  +'" class="listTitle">'+ dictName + '</div><ol class="foundEntriesList"><li data-index="' + str(entryCount)  +'">'+ self.getPreparedTermHeader(dictName, frontBracket, backBracket, term, term, term, term, True) +'</li></ol>' 
                    entryCount += 1
                    dictCount += 1
                    continue
                html += '<div data-index="' + str(dictCount)  +'" class="listTitle">'+ dictName + '</div><ol class="foundEntriesList">' 
                dictCount += 1
                for idx, entry in enumerate(dictResults):
                    html += ('<li data-index="' + str(entryCount)  +'">'+ self.getPreparedTermHeader(dictName, frontBracket, backBracket, term, entry['term'], entry['altterm'], entry['pronunciation'], True) +'</li>')
                    entryCount += 1
                html += '</ol>'
        return html + '<br></div><div class="resizeBar" onmousedown="hresize(event)"></div></div>'

    def getPreparedTermHeader(self, dictName, frontBracket, backBracket, target,  term, altterm, pronunciation, sb = False):
        altFB = frontBracket
        altBB = backBracket
        if pronunciation == term:
            pronunciation = ''
        if altterm == term:
            altterm = ''
        if altterm == '':
            altFB = ''
            altBB = ''
        if not self.termHeaders or (dictName == 'Google Images' or dictName == 'Forvo'):
            if sb:
                header = '◳f<span class="term mainword">◳t</span>◳b◳x<span class="altterm  mainword">◳a</span>◳y<span class="pronunciation">◳p</span>'
            else:
                header = '◳f<span class="listTerm">◳t</span>◳b◳x<span class="listAltTerm">◳a</span>◳y<span class="listPronunciation">◳p</span>'
        else:
            if sb:
                header = self.termHeaders[dictName][1]
            else:
                header = self.termHeaders[dictName][0]

        return header.replace('◳t', self.highlightTarget(term, target)).replace('◳a', self.highlightTarget(altterm, target)).replace('◳p', self.highlightTarget(pronunciation, target)).replace('◳f', frontBracket).replace('◳b', backBracket).replace('◳x', altFB).replace('◳y', altBB)

    def prepareResults(self, results, term, font):
        frontBracket = self.config['frontBracket']
        backBracket = self.config['backBracket']
        if len(results) > 0:
            html = self.getSideBar(results, term, font, frontBracket, backBracket)
            html += '<div class="mainDictDisplay">'
            dictCount = 0
            entryCount = 0
            imgTooltip = ''
            clipTooltip = ''
            sendTooltip = ''
            if self.config['tooltips']:
                imgTooltip = ' title="Add this definition, or any selected text and this definition\'s header to the card exporter (opens the card exporter if it is not yet opened)." '
                clipTooltip = ' title="Copy this definition, or any selected text to the clipboard." '
                sendTooltip = ' title="Send this definition, or any selected text and this definition\'s header to the card exporter to this dictionary\'s target fields. It will send it to the current target window, be it an Editor window, or the Review window." '
            for dictName, dictResults in results.items():
                    if dictName == 'Google Images':
                        html += self.getGoogleDictionaryResults(term, dictCount, frontBracket, backBracket,entryCount, font)
                        dictCount += 1
                        entryCount += 1
                        continue
                    if  dictName == 'Forvo':
                        html += self.getForvoDictionaryResults(term, dictCount, frontBracket, backBracket,entryCount, font)
                        dictCount += 1
                        entryCount += 1
                        continue
                    duplicateHeader = self.getDuplicateHeaderCB(dictName)
                    overwrite = self.getOverwriteChecks(dictCount, dictName)
                    select = self.getFieldChecks(dictName)
                    html += '<div data-index="' + str(dictCount)  +'" class="dictionaryTitleBlock"><div  ' + font +'  class="dictionaryTitle">' + dictName.replace('_', ' ') + '</div><div class="dictionarySettings">' + duplicateHeader + overwrite + select + '<div class="dictNav"><div onclick="navigateDict(event, false)" class="prevDict">▲</div><div onclick="navigateDict(event, true)" class="nextDict">▼</div></div></div></div>'
                    dictCount += 1
                    for idx, entry in enumerate(dictResults):
                        html += ('<div data-index="' + str(entryCount)  +'" class="termPronunciation"><span ' + font +' class="tpCont">'+ self.getPreparedTermHeader(dictName, frontBracket, backBracket, term, entry['term'], entry['altterm'], entry['pronunciation']) + 
                        ' <span class="starcount">' + entry['starCount']  +'</span></span><div class="defTools"><div onclick="ankiExport(event, \''+ dictName +'\')" class="ankiExportButton"><img '+ imgTooltip+' src="icons/anki.png"></div><div onclick="clipText(event)" '+ clipTooltip +' class="clipper">✂</div><div ' + sendTooltip +' onclick="sendToField(event, \''+ dictName +'\')" class="sendToField">➠</div><div class="defNav"><div onclick="navigateDef(event, false)" class="prevDef">▲</div><div onclick="navigateDef(event, true)" class="nextDef">▼</div></div></div></div><div' + font +' class="definitionBlock">' + self.highlightTarget(self.highlightExamples(entry['definition']), term)
                             + '</div>')
                        entryCount += 1
            
        else:
            html = '<style>.noresults{font-family: Arial;}.vertical-center{height: 400px; width: 60%; margin: 0 auto; display: flex; justify-content: center; align-items: center;}</style> </head> <div class="vertical-center noresults"> <div align="center"> <img src="icons/searchzero.svg" width="50px" height="40px"> <h3 align="center">No dictionary entries were found for "' + term + '".</h3> </div></div>'
        return html.replace("'", "\\'")

    def attemptFetchForvo(self, term, idName):  
        self.forvo.setTermIdName(term, idName)
        self.forvo.start()
        return 'Loading...'

    def loadForvoResults(self, results):
        forvoData, idName = results
        if forvoData:
            html = "<div class=\\'forvo\\'  data-urls=\\'" + forvoData +"\\'></div>"
        else:
            html = '<div class="no-forvo">No Results Found.</div>'
        self.eval("loadImageForvoHtml('%s', '%s');loadForvoDict(false, '%s');"%(html.replace('"', '\\"'), idName, idName))

    def getForvoDictionaryResults(self, term, dictCount, bracketFront, bracketBack, entryCount, font):
        dictName = 'Forvo'
        overwrite = self.getOverwriteChecks(dictCount, dictName )
        select = self.getFieldChecks(dictName)
        idName = 'fcon' + str(time.time())
        self.attemptFetchForvo(term, idName)
        html = '<div data-index="' + str(dictCount)  +'" class="dictionaryTitleBlock"><div class="dictionaryTitle">'+ dictName +'</div><div class="dictionarySettings">' + overwrite + select + '<div class="dictNav"><div onclick="navigateDict(event, false)" class="prevDict">▲</div><div onclick="navigateDict(event, true)" class="nextDict">▼</div></div></div></div>'
        html += ('<div  data-index="' + str(entryCount)  +'"  class="termPronunciation"><span class="tpCont">' + bracketFront+ '<span ' + font +' class="terms">' +  
                        self.highlightTarget(term, term) +
                        '</span>' + bracketBack + ' <span></span></span><div class="defTools"><div onclick="ankiExport(event, \''+ dictName +'\')" class="ankiExportButton"><img src="icons/anki.png"></div><div onclick="clipText(event)" class="clipper">✂</div><div onclick="sendToField(event, \''+ dictName +'\')" class="sendToField">➠</div><div class="defNav"><div onclick="navigateDef(event, false)" class="prevDef">▲</div><div onclick="navigateDef(event, true)" class="nextDef">▼</div></div></div></div><div id="' + idName + '" class="definitionBlock">' )
        html += 'Loading...'
        html += '</div>'
        return html

    def getGoogleDictionaryResults(self, term, dictCount, bracketFront, bracketBack, entryCount, font):
        dictName = 'Google Images'
        overwrite = self.getOverwriteChecks(dictCount, dictName )
        select = self.getFieldChecks( dictName)
        idName = 'gcon' + str(time.time())
        html = '<div data-index="' + str(dictCount)  +'" class="dictionaryTitleBlock"><div class="dictionaryTitle">Google Images</div><div class="dictionarySettings">' + overwrite + select + '<div class="dictNav"><div onclick="navigateDict(event, false)" class="prevDict">▲</div><div onclick="navigateDict(event, true)" class="nextDict">▼</div></div></div></div>'
        html += ('<div  data-index="' + str(entryCount)  +'" class="termPronunciation"><span class="tpCont">' + bracketFront+ '<span ' + font +' class="terms">' +  
                        self.highlightTarget(term, term) +
                        '</span>' + bracketBack + ' <span></span></span><div class="defTools"><div onclick="ankiExport(event, \''+ dictName +'\')" class="ankiExportButton"><img src="icons/anki.png"></div><div onclick="clipText(event)" class="clipper">✂</div><div onclick="sendToField(event, \''+ dictName +'\')" class="sendToField">➠</div><div class="defNav"><div onclick="navigateDef(event, false)" class="prevDef">▲</div><div onclick="navigateDef(event, true)" class="nextDef">▼</div></div></div></div><div class="definitionBlock"><div class="imageBlock" id="' + idName +'">' + self.getGoogleImages(term, idName)
                         + '</div></div>')
        return html           

    def getGoogleImages(self, term, idName):  
        self.imager.setTermIdName(term, idName)
        self.imager.start()
        return 'Loading...'
        

    def getCleanedUrls(self, urls):
        return [x.replace('\\', '\\\\') for x in urls]

    def getDuplicateHeaderCB(self, dictName):
        tooltip = ''
        if self.config['tooltips']:
            tooltip = ' title="Enable this option if this dictionary has the target word\'s header within the definition. Enabling this will prevent the addon from exporting duplicate header."'
        checked = ' '
        className = 'checkDict' + re.sub(r'\s', '' , dictName)
        if dictName in self.dupHeaders:
            num = self.dupHeaders[dictName]
            if num == 1:
                checked = ' checked '
        return '<div class="dupHeadCB" data-dictname="' + dictName + '">Duplicate Header:<input ' + checked + tooltip + ' class="' + className + '" onclick="handleDupChange(this, \'' + className + '\')" type="checkbox"></div>'

    def handleDictAction(self, dAct):
        if dAct.startswith('forvo:'):
            urls = json.loads(dAct[6:])
            self.downloadForvoAudio(urls)
        elif dAct.startswith('updateTerm:'):
            term = dAct[11:]
            self.dictInt.search.setText(term)
        elif dAct.startswith('saveFS:'):
            f1, f2 = dAct[7:].split(':')
            self.dictInt.writeConfig('fontSizes', [int(f1), int(f2)])
        elif dAct.startswith('setDup:'):
            dup, name =dAct[7:].split('◳')
            dup =  int(dup)
            self.dictInt.db.setDupHeader(dup, name)
            self.dupHeaders = self.db.getDupHeaders()
        elif dAct.startswith('fieldsSetting:'):
            fields = json.loads(dAct[14:])
            if fields['dictName'] == 'Google Images':
                self.dictInt.writeConfig('GoogleImageFields', fields['fields'])
            elif fields['dictName'] == 'Forvo':
                self.dictInt.writeConfig('ForvoFields', fields['fields'])
            else:
                self.dictInt.updateFieldsSetting(fields['dictName'], fields['fields'])
        elif dAct.startswith('overwriteSetting:'):
            addType = json.loads(dAct[17:])
            if addType['name'] == 'Google Images':
                self.dictInt.writeConfig('GoogleImageAddType', addType['type'])
            elif addType['name'] == 'Forvo':
                self.dictInt.writeConfig('ForvoAddType', addType['type'])
            else:
                self.dictInt.updateAddType(addType['name'], addType['type'])
        elif dAct.startswith('clipped:'):
            text = dAct[8:]
            Pyperclip.copy(text.replace('<br>', '\n'))
        elif dAct.startswith('sendToField:'):
            name, text = dAct[12:].split('◳◴')
            self.sendToField(name, text)
        elif dAct.startswith('sendAudioToField:'):
            urls = dAct[17:]
            self.sendAudioToField(urls)
        elif dAct.startswith('sendImgToField:'):
            urls = dAct[15:]
            self.sendImgToField(urls)
        elif dAct.startswith('addDef:'):
            dictName, word, text = dAct[7:].split('◳◴')
            self.addDefToExportWindow(dictName, word, text)
        elif dAct.startswith('audioExport:'):
            word, urls = dAct[12:].split('◳◴')
            self.addAudioToExportWindow( word, urls)    
        elif dAct.startswith('imgExport:'):
            word, urls = dAct[10:].split('◳◴')
            self.addImgsToExportWindow( word, json.loads(urls))
    
    def addImgsToExportWindow(self, word, urls):
        if not self.addWindow:
            self.addWindow = CardExporter(self.dictInt, self)
        imgSeparator = ''
        imgs = []
        rawPaths = []
        for imgurl in urls:
            try:
                url = re.sub(r'\?.*$', '', imgurl)
                filename = str(time.time())[:-4].replace('.', '') + re.sub(r'\..*$', '', url.strip().split('/')[-1]) + '.jpg'
                fullpath = join(self.dictInt.mw.col.media.dir(), filename)
                self.saveQImage(imgurl, filename)
                rawPaths.append(fullpath)
                imgs.append('<img src="' + filename + '">')
            except:
                continue
        if len(imgs) > 0:
            self.addWindow.addImgs(word, imgSeparator.join(imgs), self.getThumbs(rawPaths))
    
    def saveQImage(self, url, filename):
        req = Request(url , headers={'User-Agent':  'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.47 Safari/537.36'})
        file = urlopen(req).read()
        image = QImage()
        image.loadFromData(file)
        image = image.scaled(QSize(self.maxW,self.maxH), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        image.save(filename)

    def getThumbs(self, paths):
        thumbCase = QWidget()
        thumbCase.setContentsMargins(0,0,0,0)
        vLayout = QVBoxLayout()
        vLayout.setContentsMargins(0,0,0,0)
        hLayout = QHBoxLayout()
        hLayout.setContentsMargins(0,0,0,0)
        vLayout.addLayout(hLayout)
        for idx, path in enumerate(paths):
            image = QPixmap(path)
            image = image.scaled(QSize(50,50), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            label = QLabel('')
            label.setPixmap(image)
            label.setFixedSize(40,40)
            hLayout.addWidget(label)
            if idx % 4 == 0:
                hLayout = QHBoxLayout()
                hLayout.setContentsMargins(0,0,0,0)
                vLayout.addLayout(hLayout)       
        thumbCase.setLayout(vLayout)
        return thumbCase

    def addDefToExportWindow(self, dictName, word, text):
        if not self.addWindow:
            self.addWindow = CardExporter(self.dictInt, self)
        self.addWindow.addDefinition(dictName, word, text)

    def exportImage(self, pathAndName):
        self.dictInt.ensureVisible()
        path, name = pathAndName
        if not self.addWindow:
            self.addWindow = CardExporter(self.dictInt, self)
        self.addWindow.window.show()
        self.addWindow.exportImage(path, name)
        

    def exportAudio(self, audioList):
        self.dictInt.ensureVisible()
        temp, tag, name = audioList
        if not self.addWindow:
            self.addWindow = CardExporter(self.dictInt, self)
        self.addWindow.window.show()
        self.addWindow.exportAudio(temp, tag,  name)

    def exportSentence(self, sentence):
        self.dictInt.ensureVisible()
        if not self.addWindow:
            self.addWindow = CardExporter(self.dictInt, self)
        self.addWindow.window.show()
        self.addWindow.exportSentence(sentence)

    def getFieldContent(self, fContent, definition, addType):
        fieldText = False
        if addType == 'overwrite':
            fieldText = definition

        elif addType == 'add':
            if fContent == '':
                fieldText = definition
            else:
                fieldText = fContent + '<br><br>' + definition
        elif addType == 'no':
            if fContent == '':
                fieldText = definition
        return fieldText

    def addAudioToExportWindow(self, word, urls):
        if not self.addWindow:
            self.addWindow = CardExporter(self.dictInt, self)
        audioSeparator = ''
        soundFiles = self.downloadForvoAudio(json.loads(urls))
        if len(soundFiles) > 0:
            self.addWindow.addDefinition('Forvo', word, audioSeparator.join(soundFiles))



    def sendAudioToField(self, urls):
        audioSeparator = ''
        soundFiles = self.downloadForvoAudio(json.loads(urls))
        self.sendToField('Forvo', audioSeparator.join(soundFiles))

    def downloadForvoAudio(self, urls):
        tags = []
        for url in urls:
            try:
                req = Request(url , headers={'User-Agent':  'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.47 Safari/537.36'})
                file = urlopen(req).read()
                filename = str(time.time()) + '.mp3'
                open(join(self.dictInt.mw.col.media.dir(), filename), 'wb').write(file)
                tags.append('[sound:' + filename + ']')
            except: 
                continue
        return tags

    def sendImgToField(self, urls):
        if (self.reviewer and self.reviewer.card) or (self.currentEditor and self.currentEditor.note):
            urlsList = []
            imgSeparator = ''
            urls = json.loads(urls)
            for imgurl in urls:
                try:
                    url = re.sub(r'\?.*$', '', imgurl)
                    filename = str(time.time())[:-4].replace('.', '') + re.sub(r'\..*$', '', url.strip().split('/')[-1]) + '.jpg'
                    self.saveQImage(imgurl, filename)
                    urlsList.append('<img src="' + filename + '">')
                except:
                    continue
            if len(urlsList) > 0 :
                self.sendToField('Google Images', imgSeparator.join(urlsList))
 
    def sendToField(self, name, definition):
        if self.reviewer and self.reviewer.card:
            if name == 'Google Images':
                tFields = self.dictInt.getConfig()['GoogleImageFields']
                addType =  self.dictInt.getConfig()['GoogleImageAddType']
            elif name == 'Forvo':
                tFields = self.dictInt.getConfig()['ForvoFields']
                addType =  self.dictInt.getConfig()['ForvoAddType']
            else:
                tFields, addType = self.db.getAddTypeAndFields(name)
            note = self.reviewer.card.note()
            model = note.model()
            fields = model['flds']
            changed = False
            for field in fields:
                if field['name'] in tFields:
                    newField = self.getFieldContent(note[field['name']], definition, addType)
                    if newField is not False:
                        changed = True
                        if self.jSend:
                            note[field['name']] = self.dictInt.jHandler.attemptFieldGenerate(newField, field['name'], model['name'], note)
                        else:
                            note[field['name']] =  newField
            if not changed:
                return
            note.flush()
            self.dictInt.mw.col.save()
            self.reviewer.card.load()
            if self.reviewer.state == 'answer':
                self.reviewer._showAnswer()
            elif self.reviewer.state == 'question':
                self.reviewer._showQuestion()
        if self.currentEditor and self.currentEditor.note:
            if name == 'Google Images':
                tFields = self.dictInt.getConfig()['GoogleImageFields']
                addType =  self.dictInt.getConfig()['GoogleImageAddType']
            elif name == 'Forvo':
                tFields = self.dictInt.getConfig()['ForvoFields']
                addType =  self.dictInt.getConfig()['ForvoAddType']
            else:
                tFields, addType = self.db.getAddTypeAndFields(name)
            note = self.currentEditor.note

            items = note.items()
            for idx, item in enumerate(items):
                noteField = item[0]
                if noteField in tFields:
                    if self.jSend:
                        self.currentEditor.web.eval(self.dictInt.insertHTMLJS % (self.dictInt.jHandler.attemptFieldGenerate(definition, noteField, note.model()['name'], note).replace('"', '\\"'), str(idx), addType))
                    else:
                        self.currentEditor.web.eval(self.dictInt.insertHTMLJS % (definition.replace('"', '\\"'), str(idx), addType))

    def getOverwriteChecks(self, dictCount,dictName):
        if dictName == 'Google Images':
            addType = self.dictInt.getConfig()['GoogleImageAddType']
        elif dictName == 'Forvo':
            addType = self.dictInt.getConfig()['ForvoAddType']
        else:
            addType = self.db.getAddType(dictName)
        tooltip = ''
        if self.config['tooltips']:
            tooltip = ' title="This determines the conditions for sending a definition (or a Google Image) to a field. Overwrite the target field\'s content. Add to the target field\'s current contents. Only add definitions to the target field if it is empty."'
        if addType == 'add' :
           typeName = '&nbsp;Add'
        elif addType == 'overwrite' :
           typeName = '&nbsp;Overwrite'
        elif addType == 'no' :
           typeName = '&nbsp;If Empty'
        select = ('<div class="overwriteSelectCont"><div '+ tooltip + ' class="overwriteSelect" onclick="showCheckboxes(event)">'+ typeName +'</div>'+
           self.getSelectedOverwriteType(dictName, addType) + '</div>')
        return select

    def getSelectedOverwriteType(self, dictName, addType):
        count = str(self.radioCount)
        checked = ''
        if addType == 'add' :
            checked = ' checked'
        add =  '<label class="inCheckBox"><input' + checked + ' onclick="handleAddTypeCheck(this)" class="inCheckBox radio' + dictName + '" type="radio" name="' +  count + dictName + '" value="add"/>Add</label>'
        checked = ''
        if addType == 'overwrite' :
            checked = ' checked'
        overwrite ='<label class="inCheckBox"><input' + checked + ' onclick="handleAddTypeCheck(this)" class="inCheckBox radio' + dictName + '" type="radio" name="' +  count +  dictName + '" value="overwrite"/>Overwrite</label>' 
        checked = ''
        if addType == 'no' :
            checked = ' checked'
        ifempty = '<label class="inCheckBox"><input' + checked + ' onclick="handleAddTypeCheck(this)" class="inCheckBox radio' + dictName + '" type="radio" name="' +  count +  dictName + '" value="no"/>If Empty</label>'
        checks = ('<div class="overwriteCheckboxes" data-dictname="' + dictName + '">'+ 
        add + overwrite + ifempty + 
        '</div>')
        self.radioCount += 1
        return checks

    def getFieldChecks(self, dictName):
        if dictName == 'Google Images':
            selF = self.dictInt.getConfig()['GoogleImageFields']
        elif dictName == 'Forvo':
            selF = self.dictInt.getConfig()['ForvoFields'] 
        else:
            selF = self.db.getFieldsSetting(dictName);
        tooltip = ''
        if self.config['tooltips']:
            tooltip = ' title="Select this dictionary\'s target fields for when sending a definition(or a Google Image) to a card. If a field does not exist in the target card, then it is ignored, otherwise the definition is added to all fields that exist within the target card."'
        title = '&nbsp;Select Fields ▾'
        length =  len(selF) 
        if length > 0:
            title = '&nbsp;' + str(length) + ' Selected'
        select = ('<div class="fieldSelectCont"><div class="fieldSelect" '+ tooltip +' onclick="showCheckboxes(event)">'+ title +'</div>'+
            self.getCheckBoxes(dictName, selF) +'</div>')
        return select

    def getCheckBoxes(self, dictName, selF):
        fields = self.getFieldNames()
        options = '<div class="fieldCheckboxes"  data-dictname="' + dictName + '">'
        for f in fields:
            checked = ''
            if f in selF:
                checked = ' checked'
            options += '<label class="inCheckBox"><input'+ checked + ' onclick="handleFieldCheck(this)" class="inCheckBox" type="checkbox" value="'+ f + '" />'+ f + '</label>'
        return options + '</div>'

    def getFieldNames(self):
        mw = self.dictInt.mw
        models = mw.col.models.all()
        fields = []
        for model in models:
            for fld in model['flds']:
                if fld['name'] not in fields:
                    fields.append(fld['name'])
        fields.sort()           
        return fields

    def setCurrentEditor(self, editor, target = ''):
        if editor != self.currentEditor:
            self.currentEditor = editor
            self.reviewer = False
            self.dictInt.currentTarget.setText(target)
        
    def setReviewer(self, reviewer):
        self.reviewer = reviewer
        self.currentEditor = False
        self.dictInt.currentTarget.setText('Reviewer')

    def checkEditorClose(self, editor):
        if self.currentEditor == editor:
            self.closeEditor()

    def closeEditor(self):
        self.reviewer = False
        self.currentEditor = False
        self.dictInt.currentTarget.setText('')
    
class HoverButton(QPushButton):
    mouseHover = pyqtSignal(bool)
    mouseOut =  pyqtSignal(bool)
    def __init__(self, parent=None):
        QPushButton.__init__(self, parent)
        self.setMouseTracking(True)

    def enterEvent(self, event):
        self.mouseHover.emit(True)

    def leaveEvent(self, event):
        self.mouseHover.emit(False)
        self.mouseOut.emit(True)

def imageResizer(img):
    width, height = img.size
    maxh = 300
    maxw = 300
    ratio = min(maxw/width, maxh/height)
    height = int(round(ratio * height))
    width = int(round(ratio * width))
    return img.resize((width, height) , Image.ANTIALIAS)

class ClipThread(QObject):
    
    sentence = pyqtSignal(str)
    search = pyqtSignal(str)
    add = pyqtSignal(str)
    image = pyqtSignal(list)
    test = pyqtSignal(list)
    release = pyqtSignal(list)

    def __init__(self, mw, path):
        if isMac:
            import ssl
            ssl._create_default_https_context = ssl._create_unverified_context
            sys.path.insert(0, join(dirname(__file__), 'keyboardMac'))
        elif isLin:
            sys.path.insert(1, join(dirname(__file__), 'linux'))
        sys.path.insert(0, join(dirname(__file__)))
        from pynput import keyboard
        super(ClipThread, self).__init__(mw)
        self.keyboard = keyboard
        self.addonPath = path
        self.mw = mw
        self.config = self.mw.addonManager.getConfig(__name__)
    
    def on_press(self,key):
        self.test.emit([key]) 
    
    def on_release(self, key):
        self.release.emit([key])
        return True

    def run(self):
        if isWin:
            self.listener = self.keyboard.Listener(
                on_press =self.on_press, on_release= self.on_release, mia = self.mw, suppress= True)
        else:
            self.listener = self.keyboard.Listener(
                on_press =self.on_press, on_release= self.on_release)
        self.listener.start()

    def attemptAddCard(self):
        self.add.emit('add') 

    def checkDict(self):
        if not self.mw.miaDictionary or not self.mw.miaDictionary.isVisible():
            return False
        return True

    def handleSystemSearch(self):
        self.search.emit(Pyperclip.paste())

    def handleImageExport(self):
        if self.checkDict():
            mime = self.mw.app.clipboard().mimeData()
            clip = self.mw.app.clipboard().text()
            
            if not clip.endswith('.mp3') and mime.hasImage():
                image = mime.imageData()
                filename = str(time.time()) + '.png'
                fullpath = join(self.addonPath, 'temp', filename)
                maxW = self.config['maxWidth']
                maxH = self.config['maxHeight']
                image = image.scaled(QSize(maxW, maxH), Qt.KeepAspectRatio, Qt.SmoothTransformation)
                image.save(fullpath)
                self.image.emit([fullpath, filename]) 
            elif clip.endswith('.mp3'):
                if not isLin:
                    if isMac:
                        try:
                            clip = str(self.mw.app.clipboard().mimeData().urls()[0].url())
                        except:
                            return
                    if clip.startswith('file:///') and clip.endswith('.mp3'):
                        try:
                            if isMac:
                                path = clip.replace('file://', '', 1)
                            else:
                                path = clip.replace('file:///', '', 1)
                            temp, mp3 = self.moveAudioToTempFolder(path)
                            if mp3:
                                self.image.emit([temp, '[sound:' + mp3 + ']', mp3]) 
                        except:
                            return
                    
    def moveAudioToTempFolder(self, path):
        try:
            if exists(path): 
                filename = str(time.time()).replace('.', '') + '.mp3'
                destpath = join(self.addonPath, 'temp', filename)
                if not exists(destpath): 
                    copyfile(path, destpath)
                    return destpath, filename;
            return False, False;
        except: 
            return False, False;

    def handleSentenceExport(self):
        if self.checkDict():
            self.sentence.emit(Pyperclip.paste())

class DictInterface(QWidget):

    def __init__(self, mw, path, welcome, parent=None, term = False):
        super(DictInterface, self).__init__()
        self.db = dictdb.DictDB()
        self.verticalBar = False
        self.jHandler = miJHandler(mw)
        self.addonPath = path
        self.welcome = welcome
        self.setAutoFillBackground(True);
        self.ogPalette = self.getPalette(QColor('#F0F0F0'))
        self.nightPalette = self.getPalette(QColor('#272828'))
        self.blackBase = self.getFontColor(Qt.black)
        self.blackBase = self.getFontColor(Qt.white)
        self.mw = mw
        self.parent = parent
        self.iconpath = join(path, 'icons')
        self.startUp(term)
        self.setHotkeys()
        ensureWidgetInScreenBoundaries(self)

    def setHotkeys(self):     
        self.hotkeyEsc = QShortcut(QKeySequence("Esc"), self)
        self.hotkeyEsc.activated.connect(self.hide)
        self.hotkeyW = QShortcut(QKeySequence("Ctrl+W"), self)
        self.hotkeyW.activated.connect(self.mw.dictionaryInit)
        self.hotkeyS = QShortcut(QKeySequence("Ctrl+S"), self)
        self.hotkeyS.activated.connect(lambda: self.mw.searchTerm(self.dict._page))

    def getFontColor(self, color):
        pal = QPalette()
        pal.setColor(QPalette.Base, color)
        return pal

    def getPalette(self, color):
        pal = QPalette()
        pal.setColor(QPalette.Background, color)
        return pal

    def getStretchLay(self):
        stretch = QHBoxLayout()
        stretch.setContentsMargins(0,0,0,0)
        stretch.addStretch()
        return stretch

    def startUp(self, term):
        self.allGroups = self.getAllGroups()
        self.db.getAllDictsWithLang()
        self.config = self.getConfig()
        self.defaultGroups = self.db.getDefaultGroups()
        self.userGroups = self.getUserGroups()
        self.searchOptions = ['Forward', 'Backward', 'Exact', 'Anywhere', 'Definition', 'Example', 'Pronunciation']
        self.setWindowTitle("Dictionary")
        self.dictGroups = self.setupDictGroups()
        self.nightModeToggler = self.setupNightModeToggle()
        self.setSvg(self.nightModeToggler, 'theme')
        self.dict = MIDict(self, self.db, self.addonPath, self.nightModeToggler.day, term)
        self.conjToggler = self.setupConjugationMode()
        self.minusB = self.setupMinus()
        self.plusB = self.setupPlus()
        self.tabB = self.setupTabMode()
        self.histB = self.setupOpenHistory()
        self.setB = self.setupOpenSettings()
        self.searchButton = self.setupSearchButton()
        self.insertHTMLJS = self.getInsertHTMLJS()
        self.search = self.setupSearch() 
        self.sType = self.setupSearchType()
        self.openSB = self.setupOpenSB()
        self.openSB.opened = False
        self.currentTarget = QLabel('')
        self.stretch1 = self.getStretchLay()
        self.stretch2 = self.getStretchLay()
        self.layoutH2 = QHBoxLayout()
        self.mainHLay = QHBoxLayout()
        self.mainLayout = self.setupView()
        self.dict.setSType(self.sType)
        self.setLayout(self.mainLayout) 
        self.resize(800,600)
        self.setMinimumSize(350,350)
        self.sbOpened = False
        self.historyModel = HistoryModel(self.getHistory(), self)
        self.historyBrowser = HistoryBrowser(self.historyModel, self)
        self.setWindowIcon(QIcon(join(self.iconpath, 'mia.png'))) 
        self.readyToSearch = False
        self.restoreSizePos()
        self.initTooltips()
        self.show()
        self.search.setFocus()
        if self.nightModeToggler.day:
            self.loadDay()
        else:
            self.loadNight()
        html, url = self.getHTMLURL(term, self.nightModeToggler.day)
        self.dict.loadHTMLURL(html, url)

    def initTooltips(self):
        if self.config['tooltips']:
            self.dictGroups.setToolTip('Select the dictionary group.')
            self.sType.setToolTip('Select the search type.')
            self.openSB.setToolTip('Open/Close the definition sidebar.')
            self.minusB.setToolTip('Decrease the dictionary\'s font size.')
            self.plusB.setToolTip('Increase the dictionary\'s font size.')
            self.tabB.setToolTip('Switch between single and multi-tab modes.')
            self.histB.setToolTip('Open the history viewer.')
            self.conjToggler.setToolTip('Turn deinflection mode on/off.')
            self.nightModeToggler.setToolTip('Enable/Disable night-mode.')
            self.setB.setToolTip('Open the dictionary settings.')


    def restoreSizePos(self):
        sizePos = self.config['dictSizePos']
        if sizePos:
            self.resize(sizePos[2], sizePos[3])
            self.move(sizePos[0], sizePos[1])


    def getHTMLURL(self, term, day):
        nightStyle =  '<style id="nightModeCss">body, .definitionSideBar, .defTools{color: white !important;background: black !important;} .termPronunciation{background: black !important;border-top:1px solid white !important;border-bottom:1px solid white !important;} .overwriteSelect, .fieldSelect, .overwriteCheckboxes, .fieldCheckboxes{background: black !important;} .fieldCheckboxes label:hover, .overwriteCheckboxes label:hover {background-color:   #282828 !important;} #tabs{background:black !important; color: white !important;} .tablinks:hover{background:gray !important;} .tablinks{color: white !important;} .active{background-image: linear-gradient(#272828, black); border-left: 1px solid white !important;border-right: 1px solid white !important;} .dictionaryTitleBlock{border-top: 2px solid white;border-bottom: 1px solid white;} .imageLoader, .forvoLoader{background-image: linear-gradient(#272828, black); color: white; border: 1px solid gray;}.definitionSideBar{border: 2px solid white;}</style>'
        htmlPath = join(self.addonPath, 'dictionaryInit.html')
        with open(htmlPath,'r', encoding="utf-8") as fh:
            html = fh.read()
            fontSizes = self.config['fontSizes']
            f1 = str(fontSizes[0])
            f2 = str(fontSizes[1])
            html = html.replace('var fefs = 12, dbfs = 22;', 'var fefs = '+ f1 + ', dbfs = '+ f2 + ';')
            html = html.replace('<style id="fontSpecs">.foundEntriesList{font-size: 12px;}.termPronunciation,.definitionBlock{font-size: 20px;}</style>', '<style id="fontSpecs">.foundEntriesList{font-size: ' + f1 +'px;}.termPronunciation,.definitionBlock{font-size: ' + f2 + 'px;}.ankiExportButton img{height:' + f2 +'px; width:' + f2 + 'px;}</style>')
            if not day:
                html = html.replace('<style id="nightModeCss"></style>', nightStyle)
                html = html.replace('var nightMode = false;', 'var nightMode = true;')
            if not term:
                html = html.replace('<script id="initialValue"></script>','<script id="initialValue">addNewTab(\'' + self.welcome +'\'); document.getElementsByClassName(\'tablinks\')[0].classList.add(\'active\');</script>')
            else:
                term = term.strip()
                term = self.cleanTermBrackets(term)
                if term == '':
                    html = html.replace('<script id="initialValue"></script>','<script id="initialValue">addNewTab(\'' + self.welcome +'\'); document.getElementsByClassName(\'tablinks\')[0].classList.add(\'active\');</script>')
                else:
                    self.search.setText(term)
                    selectedGroup = self.getSelectedDictGroup()
                    resultHTML, cleaned, singleTab = self.dict.getHTMLResult(term, selectedGroup)
                    html = html.replace('<script id="initialValue"></script>',"<script id='initialValue'>" + "addNewTab('%s', '%s', %s);"%(resultHTML, cleaned, singleTab) + "</script>")
            url = QUrl.fromLocalFile(htmlPath)
        return html, url;



    def getAllGroups(self):
        allGroups = {}
        allGroups['dictionaries'] = self.db.getAllDictsWithLang()
        allGroups['customFont'] = False
        allGroups['font'] = False
        return allGroups

    def getInsertHTMLJS(self):
        insertHTML = join(self.addonPath, "js", "insertHTML.js")
        with open(insertHTML, "r", encoding="utf-8") as insertHTMLFile:
            return insertHTMLFile.read() 

    def focusWindow():
        self.show()
        if self.windowState() == Qt.WindowMinimized:
            self.setWindowState(Qt.WindowNoState)
        self.setFocus()
        self.activateWindow()

    def closeEvent(self, event):
        self.hideOrClose(event)
        

    def hideOrClose(self, event):
        self.currentTarget.setText('')
        self.dict.currentEditor = False
        self.dict.reviewer = False
        self.dict.close()
        self.dict.deleteLater()
        self.deleteLater()
        self.mw.miaDictionary = False
        self.mw.openMiDict.setText("Open Dictionary (Ctrl+W)")
        self.saveSizeAndPos()
        if self.dict.addWindow and self.dict.addWindow.window.isVisible():
            self.dict.addWindow.saveSizeAndPos()
            self.dict.addWindow.window.close()
        event.accept() 

    def saveSizeAndPos(self):
        pos = self.pos()
        x = pos.x()
        y = pos.y()
        size = self.size()
        width = size.width()
        height = size.height()
        posSize = [x,y,width, height]
        self.writeConfig('dictSizePos', posSize)

    def hideCloseEvent(self, event):
        self.hideOrClose( event)

    def getUserGroups(self):
        groups = self.getConfig()['DictionaryGroups']
        userGroups = {}
        for name, group in groups.items():
            dicts = group['dictionaries']
            userGroups[name] = {}
            userGroups[name]['dictionaries'] = self.db.getUserGroups(dicts)
            userGroups[name]['customFont'] = group['customFont']
            userGroups[name]['font']  = group['font']
        return userGroups

    def getConfig(self):
        return self.mw.addonManager.getConfig(__name__)

    def setupView(self):
        layoutV = QVBoxLayout()
        layoutH = QHBoxLayout()
        layoutH.addWidget(self.dictGroups)
        
        layoutH.addWidget(self.sType)
        
        layoutH.addWidget(self.search)
        layoutH.addWidget(self.searchButton)
        if not isWin:
            self.dictGroups.setFixedSize(108,38)
            self.search.setFixedSize(104, 38)
            self.sType.setFixedSize(92,38)

        else: 
            self.sType.setFixedHeight(38)
            self.dictGroups.setFixedSize(110,38)
            self.search.setFixedSize(114, 38)

        layoutH.setContentsMargins(1,1,0,0)
        layoutH.setSpacing(1)
        self.layoutH2.addWidget(self.openSB)
        
        self.layoutH2.addWidget(self.minusB)
        self.layoutH2.addWidget(self.plusB)
        self.layoutH2.addWidget(self.tabB)
        self.layoutH2.addWidget(self.histB)
        self.layoutH2.addWidget(self.conjToggler)
        self.layoutH2.addWidget(self.nightModeToggler)
        self.layoutH2.addWidget(self.setB)
        targetLabel = QLabel(' Target:')
        targetLabel.setFixedHeight(38)
        self.layoutH2.addWidget(targetLabel)
        self.currentTarget.setFixedHeight(38)
        self.layoutH2.addWidget(self.currentTarget)
        if not self.config['showTarget']:
            self.currentTarget.hide()
            targetLabel.hide()
        self.layoutH2.addStretch()
        self.layoutH2.setContentsMargins(0,1,0,0)
        self.layoutH2.setSpacing(1)
        self.mainHLay.setContentsMargins(0,0,0,0)
        self.mainHLay.addLayout(layoutH) 
        self.mainHLay.addLayout(self.layoutH2) 
        self.mainHLay.addStretch()
        layoutV.addLayout(self.mainHLay) 
        layoutV.addWidget(self.dict)
        layoutV.setContentsMargins(0,0,0,0)
        layoutV.setSpacing(1)
        return layoutV

    def toggleMenuBar(self, vertical):
        if vertical:
            self.mainHLay.removeItem(self.layoutH2)
            self.mainLayout.insertLayout(1, self.layoutH2)
        else:
            self.mainLayout.removeItem(self.layoutH2)
            self.mainHLay.insertLayout(1, self.layoutH2)


    def resizeEvent(self, event):
        w = self.width()
        if w < 702 and not self.verticalBar:
            self.verticalBar = True
            self.toggleMenuBar(True)
        elif w > 701 and self.verticalBar:
            self.verticalBar = False
            self.toggleMenuBar(False)
        event.accept()


    def setupSearchButton(self):
        searchB =  SVGPushButton(40,40)
        self.setSvg(searchB, 'search')
        searchB.clicked.connect(self.initSearch)
        return searchB


    def setupOpenSB(self):
        openSB = SVGPushButton(40,40)
        self.setSvg(openSB, 'sidebaropen')
        openSB.clicked.connect(self.toggleSB)
        return openSB

    def toggleSB(self):
        if not self.openSB.opened:
            self.openSB.opened = True
            self.setSvg(self.openSB, 'sidebarclose')
        else:
            self.openSB.opened = False
            self.setSvg(self.openSB, 'sidebaropen')
        self.dict.eval('openSidebar()')
    
    def setupTabMode(self):
        TabMode = SVGPushButton(34,34)
        if self.config['onetab']:
            TabMode.singleTab = True
            icon = 'onetab'
        else:
            TabMode.singleTab = False
            icon = 'tabs'
        self.setSvg(TabMode, icon)
        TabMode.clicked.connect(self.toggleTabMode)
        return TabMode

    def toggleTabMode(self):
        if self.tabB.singleTab:
            self.tabB.singleTab = False
            self.setSvg(self.tabB, 'tabs')
            self.writeConfig('onetab', False)
        else:
            self.tabB.singleTab = True
            self.setSvg(self.tabB, 'onetab')
            self.writeConfig('onetab', True)
       
    def setupConjugationMode(self):
        conjugationMode = SVGPushButton(40,40)
        if self.config['deinflect']:
            self.dict.deinflect = True
            icon = 'conjugation'
        else:
            self.dict.deinflect = False
            icon = 'closedcube'
        self.setSvg(conjugationMode, icon)
        conjugationMode.clicked.connect(self.toggleConjugationMode)
        return conjugationMode

    def setupOpenHistory(self):
        history = SVGPushButton(40,40)
        self.setSvg(history, 'history')
        history.clicked.connect(self.openHistory)
        return history

    def openHistory(self):
        if not self.historyBrowser.isVisible():
            self.historyBrowser.show()
    
    def toggleConjugationMode(self):
        if not self.dict.deinflect:
            self.setSvg(self.conjToggler, 'conjugation')
            self.dict.deinflect = True
            self.writeConfig('deinflect', True)

        else:
            self.setSvg(self.conjToggler, 'closedcube')
            self.dict.deinflect = False
            self.writeConfig('deinflect', False)

    def loadDay(self):
        self.setPalette(self.ogPalette)
        if not isWin:
            self.setStyleSheet(self.getMacOtherStyles())
            self.dictGroups.setStyleSheet(self.getMacComboStyle())
            self.sType.setStyleSheet(self.getMacComboStyle())
            self.setAllIcons()
            
        else:
            self.setStyleSheet("")
            self.dictGroups.setStyleSheet('')
            self.sType.setStyleSheet('')
            self.setAllIcons()
        if self.historyBrowser:
            self.historyBrowser.setColors()
        if self.dict.addWindow:
            self.dict.addWindow.setColors()


    def loadNight(self):
        if not isWin:
            self.setStyleSheet(self.getMacNightStyles())
            self.dictGroups.setStyleSheet(self.getMacNightComboStyle())
            self.sType.setStyleSheet(self.getMacNightComboStyle())
        else:   
            self.setStyleSheet(self.getOtherStyles())
            self.dictGroups.setStyleSheet(self.getComboStyle())
            self.sType.setStyleSheet(self.getComboStyle())
        self.setPalette(self.nightPalette)
        self.setAllIcons()
        if self.dict.addWindow:
            self.dict.addWindow.setColors()
        if self.historyBrowser:
            self.historyBrowser.setColors()

    def toggleNightMode(self):
        if not self.nightModeToggler.day:
            self.nightModeToggler.day = True
            self.writeConfig('day', True)
            self.dict.eval('nightModeToggle(false)')
            self.setSvg(self.nightModeToggler, 'theme')
            self.loadDay() 
        else:
            self.nightModeToggler.day = False
            self.dict.eval('nightModeToggle(true)')
            self.setSvg(self.nightModeToggler, 'theme')
            self.writeConfig('day', False)
            self.loadNight()
     
    def setSvg(self, widget, name):
        if self.nightModeToggler.day:
            return widget.setSvg(join(self.iconpath, 'dictsvgs', name + '.svg'))
        return widget.setSvg(join(self.iconpath, 'dictsvgs', name + 'night.svg'))

    def setAllIcons(self):
        self.setSvg( self.setB, 'settings')
        self.setSvg( self.plusB, 'plus')
        self.setSvg( self.minusB, 'minus')
        self.setSvg( self.histB, 'history')
        self.setSvg( self.searchButton, 'search')
        self.setSvg( self.tabB, self.getTabStatus())
        self.setSvg( self.openSB, self.getSBStatus())
        self.setSvg( self.conjToggler, self.getConjStatus())

    def getConjStatus(self):
        if self.dict.deinflect:
            return 'conjugation'
        return 'closedcube'

    def getSBStatus(self):
        if self.openSB.opened:
           return 'sidebarclose'
        return 'sidebaropen'

    def getTabStatus(self):
        if self.tabB.singleTab:
            return 'onetab'
        return 'tabs'
   
    def setupNightModeToggle(self):
        nightToggle = SVGPushButton(40,40)
        nightToggle.day = self.config['day']
        nightToggle.clicked.connect(self.toggleNightMode)
        return nightToggle

    def setupOpenSettings(self):
        settings = SVGPushButton(40,40)
        self.setSvg(settings, 'settings')
        settings.clicked.connect(self.openDictionarySettings)
        return settings

    def openDictionarySettings(self):
        if not self.mw.dictSettings:
            self.mw.dictSettings = SettingsGui(self.mw, self.addonPath, self.openDictionarySettings)
        self.mw.dictSettings.show()
        if self.mw.dictSettings.windowState() == Qt.WindowMinimized:
                # Window is minimised. Restore it.
               self.mw.dictSettings.setWindowState(Qt.WindowNoState)
        self.mw.dictSettings.setFocus()
        self.mw.dictSettings.activateWindow()
   
    def setupPlus(self):
        plusB = SVGPushButton(40,40)
        self.setSvg(plusB, 'plus')
        plusB.clicked.connect(self.incFont)
        return plusB

    def setupMinus(self):
        minusB = SVGPushButton(40,40)
        self.setSvg(minusB, 'minus')
        minusB.clicked.connect(self.decFont)
        return minusB

    def decFont(self):
        self.dict.eval("scaleFont(false)")

    def incFont(self):
        self.dict.eval("scaleFont(true)")

    def alignCenter(self, dictGroups):
        for i in range(0, dictGroups.count()):
            dictGroups.model().item(i).setTextAlignment(Qt.AlignCenter)

    def setupDictGroups(self):
        dictGroups =  QComboBox()
        ug = sorted(list(self.userGroups.keys()))
        dictGroups.addItems(ug)
        dictGroups.addItem('──────')
        dictGroups.model().item(dictGroups.count() - 1).setEnabled(False)
        dictGroups.model().item(dictGroups.count() - 1).setTextAlignment(Qt.AlignCenter)
        defaults = ['All', 'Google Images', 'Forvo']
        dictGroups.addItems(defaults)
        dictGroups.addItem('──────')
        dictGroups.model().item(dictGroups.count() - 1).setEnabled(False)
        dictGroups.model().item(dictGroups.count() - 1).setTextAlignment(Qt.AlignCenter)
        dg = sorted(list(self.defaultGroups.keys()))
        dictGroups.addItems(dg)
        dictGroups.setFixedHeight(30)
        dictGroups.setFixedWidth(80)
        dictGroups.setContentsMargins(0,0,0,0)
        current = self.config['currentGroup']
        if current in dg or current in ug or current in defaults:
            dictGroups.setCurrentText(current)
        dictGroups.currentIndexChanged.connect(lambda: self.writeConfig('currentGroup', dictGroups.currentText()))
        return dictGroups

    def setupSearchType(self):
        searchTypes =  QComboBox()
        searchTypes.addItems(self.searchOptions)
        current = self.config['searchMode']
        if current in self.searchOptions:
            searchTypes.setCurrentText(current)
        searchTypes.setFixedHeight(30)
        searchTypes.setFixedWidth(80)
        searchTypes.setContentsMargins(0,0,0,0)
        searchTypes.currentIndexChanged.connect(lambda: self.writeConfig('searchMode', searchTypes.currentText()))
        return searchTypes

    def writeConfig(self, attribute, value):
        newConfig = self.getConfig()
        newConfig[attribute] = value
        self.mw.addonManager.writeConfig(__name__, newConfig)
    
    def getSelectedDictGroup(self):
        cur = self.dictGroups.currentText()
        if cur in self.userGroups:
            return self.userGroups[cur]
        if cur == 'All':
            return self.allGroups
        if cur == 'Google Images':
            return {'dictionaries' : [{'dict' : 'Google Images', 'lang' : ''}], 'customFont': False, 'font' : False}
        if cur == 'Forvo':
            return {'dictionaries' : [{'dict' : 'Forvo', 'lang' : ''}], 'customFont': False, 'font' : False}
        if cur in self.defaultGroups:
            return self.defaultGroups[cur]
        
    def ensureVisible(self):
        if not self.isVisible():
            self.show()
        if self.windowState() == Qt.WindowMinimized:
            self.setWindowState(Qt.WindowNoState)
        self.setFocus()
        self.activateWindow()

    def cleanTermBrackets(self, term):
        return re.sub(r'(?:\[.*\])|(?:\(.*\))|(?:《.*》)|(?:（.*）)|\(|\)|\[|\]|《|》|（|）', '', term)[:30]

    def initSearch(self, term = False): 
        self.ensureVisible()
        selectedGroup = self.getSelectedDictGroup()
        if term == False:
            term = self.search.text()
            term = term.strip()
        term = term.strip()
        term = self.cleanTermBrackets(term)
        if term == '':
            return
        self.search.setText(term.strip())
        self.addToHistory(term)
        self.dict.addNewTab(term, selectedGroup)
        self.search.setFocus()


    def addToHistory(self, term):
        date = str(datetime.date.today())
        self.historyModel.insertRows(term=term, date = date)
        self.saveHistory()

    def saveHistory(self):
        path = join(self.mw.col.media.dir(), '_searchHistory.json')
        with codecs.open(path, "w","utf-8") as outfile:
            json.dump(self.historyModel.history, outfile, ensure_ascii=False) 
        return

    def getHistory(self):
        path = join(self.mw.col.media.dir(), '_searchHistory.json')
        try:
            if exists(path):
                with open(path, "r", encoding="utf-8") as histFile:
                    return json.loads(histFile.read())
        except:
            return []
        return []

    def updateFieldsSetting(self, dictName, fields):
        self.db.setFieldsSetting(dictName, json.dumps(fields, ensure_ascii=False));

    def updateAddType(self, dictName, addType):
        self.db.setAddType(dictName, addType);

    def setupSearch(self):
        searchBox = QLineEdit()
        searchBox.setFixedHeight(30)
        searchBox.setFixedWidth(100)
        searchBox.returnPressed.connect(self.initSearch)
        searchBox.setContentsMargins(0,0,0,0)
        return searchBox;

    def getMacOtherStyles(self):
        return '''
            QLabel {color: black;}
            QLineEdit {color: black; background: white;} 
            QPushButton {border: 1px solid black; border-radius: 5px; color: black; background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 white, stop: 1 silver);} 
            QPushButton:hover{background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 white, stop: 1 silver); border-right: 2px solid black; border-bottom: 2px solid black;}"
            '''
    def getMacNightStyles(self):
        return '''
            QLabel {color: white;}
            QLineEdit {color: black;} 
            QPushButton {border: 1px solid gray; border-radius: 5px; color: white; background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #272828, stop: 1 black);} 
            QPushButton:hover{background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #272828, stop: 1 black); border: 1px solid white;}"
            '''

    def getOtherStyles(self):
        return '''
            QLabel {color: white;}
            QLineEdit {color: white; background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #272828, stop: 1 black);} 
            QPushButton {border: 1px solid gray; border-radius: 5px; color: white; background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #272828, stop: 1 black);} 
            QPushButton:hover{background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #272828, stop: 1 black); border: 1px solid white;}"
            '''

    def getMacComboStyle(self):
        return  '''
QComboBox {color: black; border-radius: 3px; border: 1px solid black;}
QComboBox:hover {border: 1px solid black;}
QComboBox:editable {
    background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 white, stop: 1 silver);
}

QComboBox:!editable, QComboBox::drop-down:editable {
     background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 white, stop: 1 silver);

}

QComboBox:!editable:on, QComboBox::drop-down:editable:on {
    background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 white, stop: 1 silver);
     
}

QComboBox:on { 
    padding-top: 3px;
    padding-left: 4px;

}

QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    max-width:20px;
    border-top-right-radius: 3px; 
    border-bottom-right-radius: 3px;

}


QComboBox QAbstractItemView 
    {
    min-width: 130px;
    }

QCombobox:selected{
    background: white;
}

QComboBox::down-arrow {
    image: url(''' + join(self.iconpath, 'blackdown.png').replace('\\', '/') +  ''');
}

QComboBox::down-arrow:on { 
    top: 1px;
    left: 1px;
}

QComboBox QAbstractItemView{ width: 130px !important; background: white; border: 0px;color:black; selection-background-color: silver;}

QAbstractItemView:selected {
background:white;}

QScrollBar:vertical {              
        border: 1px solid black;
        background:white;
        width:17px;    
        margin: 0px 0px 0px 0px;
    }
    QScrollBar::handle:vertical {
        background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 white, stop: 1 silver);
     
    }
    QScrollBar::add-line:vertical {
        background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 white, stop: 1 silver);
     
        height: 0px;
        subcontrol-position: bottom;
        subcontrol-origin: margin;
    }
    QScrollBar::sub-line:vertical {
        background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 white, stop: 1 silver);
     
        height: 0 px;
        subcontrol-position: top;
        subcontrol-origin: margin;
    }'''

    def getMacTableStyle(self):
        return '''
        QAbstractItemView{color:black;}

        QHeaderView {
            color: black;
            background: silver;
            }
        QHeaderView::section
        {
            color:black;
            background-color: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 white, stop: 1 silver);
            border: 1px solid black;
        }

        '''

    def getComboStyle(self):
        return  '''
QComboBox {color: white; border-radius: 3px; border: 1px solid gray;}
QComboBox:hover {border: 1px solid white;}
QComboBox:editable {
    background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #272828, stop: 1 black);
}

QComboBox:!editable, QComboBox::drop-down:editable {
     background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #272828, stop: 1 black);

}

QComboBox:!editable:on, QComboBox::drop-down:editable:on {
    background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #272828, stop: 1 black);
     
}

QComboBox:on { 
    padding-top: 3px;
    padding-left: 4px;
}

QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 15px;
    border-top-right-radius: 3px; 
    border-bottom-right-radius: 3px;
}

QCombobox:selected{
    background: gray;
}

QComboBox::down-arrow {
    image: url(''' + join(self.iconpath, 'down.png').replace('\\', '/') +  ''');
}

QComboBox::down-arrow:on { 
    top: 1px;
    left: 1px;
}

QComboBox QAbstractItemView{background: #272828; border: 0px;color:white; selection-background-color: gray;}

QAbstractItemView:selected {
background:gray;}

QScrollBar:vertical {              
        border: 1px solid white;
        background:white;
        width:17px;    
        margin: 0px 0px 0px 0px;
    }
    QScrollBar::handle:vertical {
        background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #272828, stop: 1 black);
     
    }
    QScrollBar::add-line:vertical {
        background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #272828, stop: 1 black);
     
        height: 0px;
        subcontrol-position: bottom;
        subcontrol-origin: margin;
    }
    QScrollBar::sub-line:vertical {
        background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #272828, stop: 1 black);
     
        height: 0 px;
        subcontrol-position: top;
        subcontrol-origin: margin;
    }'''

    def getTableStyle(self):
        return '''
        QAbstractItemView{color:white;}

        QHeaderView {
            background: black;
            }
        QHeaderView::section
        {
            color:white;
            background-color: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #272828, stop: 1 black);
            border: 1px solid white;
        }
         QTableWidget, QTableView {
         color:white;
         background-color: #272828;
         selection-background-color: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #272828, stop: 1 black);
     }
        QTableWidget QTableCornerButton::section, QTableView QTableCornerButton::section{
         background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #272828, stop: 1 black);
         border: 1px solid white;
     }

        '''

    def getMacNightComboStyle(self):
        return  '''
QComboBox {color: white; border-radius: 3px; border: 1px solid gray;}
QComboBox:hover {border: 1px solid white;}
QComboBox:editable {
    background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #272828, stop: 1 black);
}

QComboBox:!editable, QComboBox::drop-down:editable {
     background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #272828, stop: 1 black);

}

QComboBox:!editable:on, QComboBox::drop-down:editable:on {
    background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #272828, stop: 1 black);
     
}

QComboBox:on { 
    padding-top: 3px;
    padding-left: 4px;
}

QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 15px;
    border-top-right-radius: 3px; 
    border-bottom-right-radius: 3px;
}

QCombobox:selected{
    background: gray;
}

QComboBox QAbstractItemView 
    {
    min-width: 130px;
    }

QComboBox::down-arrow {
    image: url(''' + join(self.iconpath, 'down.png').replace('\\', '/') +  ''');
}

QComboBox::down-arrow:on { 
    top: 1px;
    left: 1px;
}

QComboBox QAbstractItemView{background: #272828; border: 0px;color:white; selection-background-color: gray;}

QAbstractItemView:selected {
background:gray;}

QScrollBar:vertical {              
        border: 1px solid white;
        background:white;
        width:17px;    
        margin: 0px 0px 0px 0px;
    }
    QScrollBar::handle:vertical {
        background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #272828, stop: 1 black);
     
    }
    QScrollBar::add-line:vertical {
        background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #272828, stop: 1 black);
     
        height: 0px;
        subcontrol-position: bottom;
        subcontrol-origin: margin;
    }
    QScrollBar::sub-line:vertical {
        background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #272828, stop: 1 black);
     
        height: 0 px;
        subcontrol-position: top;
        subcontrol-origin: margin;
    }'''

class MIASVG(QSvgWidget):
    clicked=pyqtSignal()
    def __init__(self, parent=None):
        QSvgWidget.__init__(self, parent)

    def mousePressEvent(self, ev):
        self.clicked.emit()


class SVGPushButton(QPushButton):
    def __init__(self, width, height):
        QPushButton.__init__(self)
        # self.setSizePolicy( QSizePolicy.Preferred, QSizePolicy.Preferred )
        self.setFixedHeight(40)
        self.setFixedWidth(43)
        self.svgWidth = width
        self.svgHeight = height
        self.layout = QHBoxLayout()
        self.layout.setContentsMargins(0,0,0,0)
        self.setContentsMargins(0,0,0,0)
        self.setLayout(self.layout)

    def setSvg(self, svgPath):
        for i in reversed(range(self.layout.count())): 
            self.layout.itemAt(i).widget().setParent(None)
        svg = QSvgWidget(svgPath)
        svg.setFixedSize(self.svgWidth, self.svgHeight)
        self.layout.addWidget(svg)


