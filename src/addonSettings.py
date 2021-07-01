# -*- coding: utf-8 -*-
# 
# 
import json
import sys
import math
from anki.hooks import addHook, wrap
from aqt.qt import *
from aqt.utils import openLink, tooltip, showInfo, askUser
from anki.utils import isMac, isWin, isLin
from anki.lang import _
from aqt.webview import AnkiWebView
import re
import os
from os.path import dirname, join
import platform
from .addDictGroup import DictGroupEditor
from .addTemplate import TemplateEditor
from .miutils import miInfo, miAsk
from . dictionaryManager import DictionaryManagerWidget
from .ffmpegInstaller import FFMPEGInstaller

verNumber = "1.3.7"


def attemptOpenLink(cmd):
    if cmd.startswith('openLink:'):
        openLink(cmd[9:])



class MigakuSVG(QSvgWidget):
    clicked=pyqtSignal()
    def __init__(self, parent=None):
        QSvgWidget.__init__(self, parent)

    def mousePressEvent(self, ev):
        self.clicked.emit()

class MigakuLabel(QLabel):
    clicked=pyqtSignal()
    def __init__(self, parent=None):
        QLabel.__init__(self, parent)

    def mousePressEvent(self, ev):
        self.clicked.emit()

class SettingsGui(QTabWidget):
    def __init__(self, mw, path, reboot):
        super(SettingsGui, self).__init__()
        self.mw = mw
        self.ffmpegInstaller = FFMPEGInstaller(self.mw)
        self.reboot = reboot
        self.googleCountries = ["Afghanistan" ,"Albania","Algeria","American Samoa","Andorra","Angola","Anguilla","Antarctica","Antigua and Barbuda","Argentina","Armenia","Aruba","Australia","Austria","Azerbaijan","Bahamas","Bahrain","Bangladesh","Barbados","Belarus","Belgium","Belize","Benin","Bermuda","Bhutan","Bolivia","Bosnia and Herzegovina","Botswana","Bouvet Island","Brazil","British Indian Ocean Territory","Brunei Darussalam","Bulgaria","Burkina Faso","Burundi","Cambodia","Cameroon","Canada","Cape Verde","Cayman Islands","Central African Republic","Chad","Chile","China","Christmas Island","Cocos (Keeling) Islands","Colombia","Comoros","Congo","Congo, the Democratic Republic of the","Cook Islands","Costa Rica","Cote D'ivoire","Croatia (Hrvatska)","Cuba","Cyprus","Czech Republic","Denmark","Djibouti","Dominica","Dominican Republic","East Timor","Ecuador","Egypt","El Salvador","Equatorial Guinea","Eritrea","Estonia","Ethiopia","European Union","Falkland Islands (Malvinas)","Faroe Islands","Fiji","Finland","France","France, Metropolitan","French Guiana","French Polynesia","French Southern Territories","Gabon","Gambia","Georgia","Germany","Ghana","Gibraltar","Greece","Greenland","Grenada","Guadeloupe","Guam","Guatemala","Guinea","Guinea-Bissau","Guyana","Haiti","Heard Island and Mcdonald Islands","Holy See (Vatican City State)","Honduras","Hong Kong","Hungary","Iceland","India","Indonesia","Iran, Islamic Republic of","Iraq","Ireland","Israel","Italy","Jamaica","Japan","Jordan","Kazakhstan","Kenya","Kiribati","Korea, Democratic People's Republic of","Korea, Republic of","Kuwait","Kyrgyzstan","Lao People's Democratic Republic","Latvia","Lebanon","Lesotho","Liberia","Libyan Arab Jamahiriya","Liechtenstein","Lithuania","Luxembourg","Macao","Macedonia, the Former Yugosalv Republic of","Madagascar","Malawi","Malaysia","Maldives","Mali","Malta","Marshall Islands","Martinique","Mauritania","Mauritius","Mayotte","Mexico","Micronesia, Federated States of","Moldova, Republic of","Monaco","Mongolia","Montserrat","Morocco","Mozambique","Myanmar","Namibia","Nauru","Nepal","Netherlands","Netherlands Antilles","New Caledonia","New Zealand","Nicaragua","Niger","Nigeria","Niue","Norfolk Island","Northern Mariana Islands","Norway","Oman","Pakistan","Palau","Palestinian Territory","Panama","Papua New Guinea","Paraguay","Peru","Philippines","Pitcairn","Poland","Portugal","Puerto Rico","Qatar","Reunion","Romania","Russian Federation","Rwanda","Saint Helena","Saint Kitts and Nevis","Saint Lucia","Saint Pierre and Miquelon","Saint Vincent and the Grenadines","Samoa","San Marino","Sao Tome and Principe","Saudi Arabia","Senegal","Serbia and Montenegro","Seychelles","Sierra Leone","Singapore","Slovakia","Slovenia","Solomon Islands","Somalia","South Africa","South Georgia and the South Sandwich Islands","Spain","Sri Lanka","Sudan","Suriname","Svalbard and Jan Mayen","Swaziland","Sweden","Switzerland","Syrian Arab Republic","Taiwan","Tajikistan","Tanzania, United Republic of","Thailand","Togo","Tokelau","Tonga","Trinidad and Tobago","Tunisia","Turkey","Turkmenistan","Turks and Caicos Islands","Tuvalu","Uganda","Ukraine","United Arab Emirates","United Kingdom","United States","United States Minor Outlying Islands","Uruguay","Uzbekistan","Vanuatu","Venezuela","Vietnam","Virgin Islands, British","Virgin Islands, U.S.","Wallis and Futuna","Western Sahara","Yemen","Yugoslavia","Zambia","Zimbabwe"]
        self.forvoLanguages = ["Afrikaans", "Ancient Greek", "Arabic", "Armenian", "Azerbaijani", "Bashkir", "Basque", "Belarusian", "Bengali", "Bulgarian", "Cantonese", "Catalan", "Chuvash", "Croatian", "Czech", "Danish", "Dutch", "English", "Esperanto", "Estonian", "Finnish", "French", "Galician","German", "Greek", "Hakka", "Hebrew", "Hindi", "Hungarian", "Icelandic", "Indonesian", "Interlingua", "Irish", "Italian", "Japanese", "Kabardian", "Korean", "Kurdish", "Latin", "Latvian", "Lithuanian", "Low German", "Luxembourgish", "Mandarin Chinese", "Mari", "Min Nan", "Northern Sami", "Norwegian Bokmål", "Persian", "Polish", "Portuguese", "Punjabi", "Romanian", "Russian", "Serbian", "Slovak", "Slovenian", "Spanish", "Swedish", "Tagalog", "Tatar", "Thai", "Turkish", "Ukrainian", "Urdu", "Uyghur", "Venetian", "Vietnamese", "Welsh", "Wu Chinese", "Yiddish"]
        self.setMinimumSize(850, 550)
        if not isWin:
            self.resize(1034, 550)
        else:
            self.resize(920, 550)
        self.setContextMenuPolicy(Qt.NoContextMenu)
        self.setWindowTitle("Migaku Dictionary Settings (Ver. " + verNumber + ")")
        self.addonPath = path
        self.setWindowIcon(QIcon(join(self.addonPath, 'icons', 'migaku.png')))
        self.addDictGroup = QPushButton('Add Dictionary Group')
        self.addExportTemplate = QPushButton('Add Export Template')
        self.dictGroups = self.getGroupTemplateTable()
        self.exportTemplates = self.getGroupTemplateTable()
        self.tooltipCB = QCheckBox()
        self.tooltipCB.setFixedHeight(30)
        self.maxImgWidth = QSpinBox()
        self.maxImgWidth.setRange(0, 9999)
        self.maxImgHeight = QSpinBox()
        self.maxImgHeight.setRange(0, 9999)
        self.safeSearch = QCheckBox()
        self.googleCountry = QComboBox()
        self.googleCountry.addItems(self.googleCountries)
        self.forvoLang = QComboBox()
        self.forvoLang.addItems(self.forvoLanguages)
        self.condensedAudioDirectoryLabel = QLabel("Condensed Audio Save Location:")
        self.chooseAudioDirectory = QPushButton("Choose Directory")
        self.convertToMp3 = QCheckBox()
        self.disableCondensedMessages = QCheckBox()
        self.dictOnTop = QCheckBox()
        self.showTarget = QCheckBox()
        self.totalDefs = QSpinBox()
        self.totalDefs.setRange(0, 1000)
        self.dictDefs = QSpinBox()
        self.dictDefs.setRange(0, 100)
        self.genJSExport = QCheckBox()
        self.genJSEdit = QCheckBox()
        self.frontBracket = QLineEdit()
        self.backBracket = QLineEdit()
        self.highlightTarget = QCheckBox()
        self.highlightSentence = QCheckBox()
        self.openOnStart = QCheckBox()
        self.globalHotkeys = QCheckBox()
        self.globalOpen = QCheckBox()
        self.restoreButton = QPushButton('Restore Defaults')
        self.cancelButton = QPushButton('Cancel')
        self.applyButton = QPushButton('Apply')
        self.layout = QVBoxLayout()
        self.settingsTab = QWidget(self)
        self.userGuideTab = self.getUserGuideTab()
        self.setupLayout()
        self.addTab(self.settingsTab, "Settings")
        self.addTab(DictionaryManagerWidget(), "Dictionaries")
        self.addTab(self.userGuideTab, "User Guide")
        self.addTab(self.getAboutTab(), "About")
        self.loadTemplateTable()
        self.loadGroupTable()
        self.initHandlers()
        self.loadConfig()
        self.initTooltips()
        self.hotkeyEsc = QShortcut(QKeySequence("Esc"), self)
        self.hotkeyEsc.activated.connect(self.close)
        
        self.show()

    def hideEvent(self, event):
        self.mw.dictSettings = None
        self.userGuideTab.close()
        self.userGuideTab.deleteLater()
        event.accept()

    def closeEvent(self, event):
        self.mw.dictSettings = None
        self.userGuideTab.close()
        self.userGuideTab.deleteLater()
        event.accept()

    def initTooltips(self):
        self.addDictGroup.setToolTip('Add a new dictionary group.\nDictionary groups allow you to specify which dictionaries to search\nwithin. You can also set a specific font for that group.')
        self.addExportTemplate.setToolTip('Add a new export template.\nExport templates allow you to specify a note type, and fields where\ntarget sentences, target words, definitions, and images will be sent to\n when using the Card Exporter to create cards.')
        self.tooltipCB.setToolTip('Enable/disable tooltips within the dictionary and its sub-windows.')
        self.maxImgWidth.setToolTip('Images will be scaled according to this width.')
        self.maxImgHeight.setToolTip('Images will be scaled according to this height.')
        self.googleCountry.setToolTip('Select the country or region to search Google Images from, the search region\ngreatly impacts search results so choose a location where your target language is spoken.')
        self.forvoLang.setToolTip('Select the language to be used with the Forvo Dictionary.')
        self.showTarget.setToolTip('Show/Hide the Target Identifier from the dictionary window. The Target Identifier\nlets you know which window is currently selected and will be used when sending\ndefinitions to a target field.')
        self.totalDefs.setToolTip('This is the total maximum number of definitions which the dictionary will output.')
        self.dictDefs.setToolTip('This is the maximum number of definitions which the dictionary will output for any given dictionary.')
        self.genJSExport.setToolTip('If this is enabled and you have Migaku Japanese installed in Anki,\nthen when a card is exported, readings and accent information will automatically be generated for all\nactive fields. This generation is based on your Migaku Japanese Sentence Button (文) settings.')
        self.genJSEdit.setToolTip('If this is enabled and you have Migaku Japanese installed in Anki,\nthen when a definition is sent to a field, readings and accent information will automatically be generated for all\nactive fields. This generation is based on your Migaku Japanese Sentence Button (文) settings.')
        self.frontBracket.setToolTip('This is the text that will be placed in front of each term\n in the dictionary.')
        self.backBracket.setToolTip('This is the text that will be placed after each term\nin the dictionary.')
        self.highlightTarget.setToolTip('The dictionary will highlight the searched term in\nthe search results.')
        self.highlightSentence.setToolTip('The dictionary will highlight example sentences in\nthe search results. This feature is experimental and currently only\nfunctions on Japanese monolingual dictionaries.')
        self.openOnStart.setToolTip('Enable/Disable launching the Migaku Dictionary on profile load.')
        linNote = ''
        self.globalHotkeys.setToolTip('Enable/Disable global hotkeys.' + linNote)
        self.globalOpen.setToolTip('If enabled the dictionary will be opened on a global search.')
        self.safeSearch.setToolTip('Whether or not to enable Safe Search for Google Images.')
        self.convertToMp3.setToolTip('When enabled will convert extension WAV files into MP3 files.\nMP3 files are supported across every Anki platform and are much smaller than WAV files.\nWe recommend enabling this option.')
        self.disableCondensedMessages.setToolTip('Disable messages shown when condensed audio files are successfully created.')

    def getConfig(self):
        return self.mw.addonManager.getConfig(__name__)
        
    def loadConfig(self):
        config = self.getConfig()
        self.openOnStart.setChecked(config['dictOnStart'])
        self.highlightSentence.setChecked(config['highlightSentences'])
        self.highlightTarget.setChecked(config['highlightTarget'])
        self.totalDefs.setValue(config['maxSearch'])
        self.dictDefs.setValue(config['dictSearch'])
        self.genJSExport.setChecked(config['jReadingCards'])
        self.genJSEdit.setChecked(config['jReadingEdit'])
        self.googleCountry.setCurrentText(config['googleSearchRegion'])
        self.forvoLang.setCurrentText(config['ForvoLanguage'])
        self.maxImgWidth.setValue(config['maxWidth'])
        self.maxImgHeight.setValue(config['maxHeight'])
        self.frontBracket.setText(config['frontBracket'])
        self.backBracket.setText(config['backBracket'])
        self.showTarget.setChecked(config['showTarget'])
        self.tooltipCB.setChecked(config['tooltips'])
        self.globalHotkeys.setChecked(config['globalHotkeys'])
        self.globalOpen.setChecked(config['openOnGlobal'])
        self.safeSearch.setChecked(config['safeSearch'])
        self.convertToMp3.setChecked(config['mp3Convert'])
        self.disableCondensedMessages.setChecked(config['disableCondensed'])
        self.dictOnTop.setChecked(config['dictAlwaysOnTop'])
        if config.get('condensedAudioDirectory', False) is not False:
            self.chooseAudioDirectory.setText(config['condensedAudioDirectory'])
        else:
            self.chooseAudioDirectory.setText("Choose Directory")

    def saveConfig(self):
        nc = self.getConfig()
        nc['dictOnStart'] = self.openOnStart.isChecked()
        nc['highlightSentences'] = self.highlightSentence.isChecked()
        nc['highlightTarget'] = self.highlightTarget.isChecked()
        nc['maxSearch'] = self.totalDefs.value()
        nc['dictSearch'] = self.dictDefs.value()
        nc['jReadingCards'] = self.genJSExport.isChecked()
        nc['jReadingEdit'] = self.genJSEdit.isChecked()
        nc['googleSearchRegion'] = self.googleCountry.currentText()
        nc['ForvoLanguage'] = self.forvoLang.currentText()
        nc['maxWidth'] = self.maxImgWidth.value()
        nc['maxHeight'] = self.maxImgHeight.value()
        nc['frontBracket'] = self.frontBracket.text()
        nc['backBracket'] = self.backBracket.text()
        nc['showTarget'] = self.showTarget.isChecked()
        nc['tooltips'] = self.tooltipCB.isChecked()
        nc['globalHotkeys'] = self.globalHotkeys.isChecked()
        nc['openOnGlobal'] = self.globalOpen.isChecked()
        nc['mp3Convert'] = self.convertToMp3.isChecked()
        nc['disableCondensed'] = self.disableCondensedMessages.isChecked()
        nc['safeSearch'] = self.safeSearch.isChecked()
        nc['dictAlwaysOnTop']  = self.dictOnTop.isChecked()
        if self.chooseAudioDirectory.text() != "Choose Directory":
            nc ['condensedAudioDirectory'] = self.chooseAudioDirectory.text()
        else:
            nc ['condensedAudioDirectory'] = False
        self.mw.addonManager.writeConfig(__name__, nc)
        self.hide()
        self.mw.refreshMigakuDictConfig()
        if nc['mp3Convert']:
            self.ffmpegInstaller.installFFMPEG()
        if self.mw.migakuDictionary and self.mw.migakuDictionary.isVisible():
            miInfo('Please be aware that the dictionary window will not reflect any setting changes until it is closed and reopened.', level='not')

    def updateAudioDirectory(self):
        directory = str(QFileDialog.getExistingDirectory(None, "Select Condensed Audio Directory"))
        if directory:
            self.chooseAudioDirectory.setText(directory)
        else:
            self.chooseAudioDirectory.setText("Choose Directory")

    def getGroupTemplateTable(self):
        macLin = False
        if isMac  or isLin:
            macLin = True
        groupTemplates = QTableWidget()
        groupTemplates.setColumnCount(3)
        tableHeader = groupTemplates.horizontalHeader()
        tableHeader.setSectionResizeMode(0, QHeaderView.Stretch)
        tableHeader.setSectionResizeMode(1, QHeaderView.Fixed)
        tableHeader.setSectionResizeMode(2, QHeaderView.Fixed)
        groupTemplates.setRowCount(0)
        groupTemplates.setSortingEnabled(False)
        groupTemplates.setEditTriggers(QTableWidget.NoEditTriggers)
        groupTemplates.setSelectionBehavior(QAbstractItemView.SelectRows)
        if macLin:
            groupTemplates.setColumnWidth(1, 50)
            groupTemplates.setColumnWidth(2, 40)
        else:
            groupTemplates.setColumnWidth(1, 40)
            groupTemplates.setColumnWidth(2, 40)
        tableHeader.hide()
        return groupTemplates

    def loadGroupTable(self):
        self.dictGroups.setRowCount(0)
        dictGroups = self.getConfig()['DictionaryGroups']
        for groupName in dictGroups:
            rc = self.dictGroups.rowCount()
            self.dictGroups.setRowCount(rc + 1)
            self.dictGroups.setItem(rc, 0, QTableWidgetItem(groupName))
            editButton =  QPushButton("Edit");
            if isWin:
                editButton.setFixedWidth(40)
            else:
                editButton.setFixedWidth(50)
                editButton.setFixedHeight(30)
            editButton.clicked.connect(self.editGroupRow(rc))
            self.dictGroups.setCellWidget(rc, 1, editButton)   
            deleteButton =  QPushButton("X");
            if isWin:
                deleteButton.setFixedWidth(40)
            else:
                deleteButton.setFixedWidth(40)
                deleteButton.setFixedHeight(30)
            deleteButton.clicked.connect(self.removeGroupRow(rc))
            self.dictGroups.setCellWidget(rc, 2, deleteButton)

    def removeGroupRow(self, x):
        return lambda: self.removeGroup(x)

    def editGroupRow(self, x):
        return lambda: self.editGroup(x)

    def editGroup(self, row):
        groupName  = self.dictGroups.item(row, 0).text()
        dictGroups = self.getConfig()['DictionaryGroups']
        if groupName in dictGroups:
            group = dictGroups[groupName]  
            dictEditor = DictGroupEditor(self.mw, self, self.getDictionaryNames(), group, groupName)
            dictEditor.exec_()

    def removeGroup(self, row ):
        if miAsk('Are you sure you would like to remove this dictionary group? This action will happen immediately and is not un-doable.', self):
            newConfig = self.getConfig()
            dictGroups = newConfig['DictionaryGroups']
            groupName = self.dictGroups.item(row, 0).text()
            del dictGroups[groupName]
            self.mw.addonManager.writeConfig(__name__, newConfig)
            self.dictGroups.removeRow(row)
            self.loadGroupTable()

    def loadTemplateTable(self):
        self.exportTemplates.setRowCount(0)
        exportTemplates = self.getConfig()['ExportTemplates']
        for template in exportTemplates:
            rc = self.exportTemplates.rowCount()
            self.exportTemplates.setRowCount(rc + 1)
            self.exportTemplates.setItem(rc, 0, QTableWidgetItem(template))
            editButton =  QPushButton("Edit");
            if isWin:
                editButton.setFixedWidth(40)
            else:
                editButton.setFixedWidth(50)
                editButton.setFixedHeight(30)
            editButton.clicked.connect(self.editTempRow(rc))
            self.exportTemplates.setCellWidget(rc, 1, editButton)   
            deleteButton =  QPushButton("X");
            if isWin:
                deleteButton.setFixedWidth(40)
            else:
                deleteButton.setFixedWidth(40)
                deleteButton.setFixedHeight(30)
            deleteButton.clicked.connect(self.removeTempRow(rc))
            self.exportTemplates.setCellWidget(rc, 2, deleteButton)

    def removeTemplate(self, row):
        if miAsk('Are you sure you would like to remove this template? This action will happen immediately and is not un-doable.', self):
            newConfig = self.getConfig()
            exportTemplates = newConfig['ExportTemplates']
            templateName = self.exportTemplates.item(row, 0).text()
            del exportTemplates[templateName]
            self.mw.addonManager.writeConfig(__name__, newConfig)
            self.exportTemplates.removeRow(row)
            self.loadTemplateTable()

    def removeTempRow(self, x):
        return lambda: self.removeTemplate(x)

    def editTempRow(self, x):
        return lambda: self.editTemplate(x)

    def editTemplate(self, row):
        templateName = self.exportTemplates.item(row, 0).text()
        exportTemplates = self.getConfig()['ExportTemplates']
        if templateName in exportTemplates:
            template = exportTemplates[templateName]  
            templateEditor = TemplateEditor(self.mw, self, self.getDictionaryNames(), template, templateName)
            templateEditor.loadTemplateEditor(template, templateName)
            templateEditor.exec_()

    def getDictionaryNames(self):
        dictList = self.mw.miDictDB.getAllDictsWithLang()
        dictionaryList = []
        for dictionary in dictList:
            dictName = self.cleanDictName(dictionary['dict'])
            if dictName not in dictionaryList:
                dictionaryList.append(dictName)
        dictionaryList= sorted(dictionaryList, key=str.casefold)
        return dictionaryList


    def initHandlers(self):
        self.addDictGroup.clicked.connect(self.addGroup)
        self.addExportTemplate.clicked.connect(self.addTemplate)
        self.restoreButton.clicked.connect(self.restoreDefaults)
        self.cancelButton.clicked.connect(self.close)
        self.applyButton.clicked.connect(self.saveConfig)
        self.chooseAudioDirectory.clicked.connect(self.updateAudioDirectory)


    def restoreDefaults(self):
        if miAsk('This will remove any export templates and dictionary groups you have created, and is not undoable. Are you sure you would like to restore the default settings?'):
            conf = self.mw.addonManager.addonConfigDefaults(dirname(__file__))
            self.mw.addonManager.writeConfig(__name__, conf)
            self.userGuideTab.close()
            self.userGuideTab.deleteLater()
            self.close()
            self.reboot()

    def addGroup(self):
        dictEditor = DictGroupEditor(self.mw, self, self.getDictionaryNames())
        dictEditor.clearGroupEditor(True)
        dictEditor.exec_()

    def addTemplate(self):
        templateEditor = TemplateEditor(self.mw, self, self.getDictionaryNames())
        templateEditor.exec_()

    def miQLabel(self, text, width):
        label = QLabel(text)
        label.setFixedHeight(30)
        label.setFixedWidth(width)
        return label

    def getLineSeparator(self):
        line = QFrame();
        line.setFrameShape(QFrame.VLine)
        line.setFrameShadow(QFrame.Plain)
        line.setStyleSheet('QFrame[frameShape="5"]{color: #D5DFE5;}')
        return line

    def setupLayout(self):
        groupLayout = QHBoxLayout()
        dictsLayout = QVBoxLayout()
        exportsLayout = QVBoxLayout()

        dictsLayout.addWidget(QLabel('Dictionary Groups'))
        dictsLayout.addWidget(self.addDictGroup)
        dictsLayout.addWidget(self.dictGroups)

        exportsLayout.addWidget(QLabel('Export Templates'))
        exportsLayout.addWidget(self.addExportTemplate)
        exportsLayout.addWidget(self.exportTemplates)

        groupLayout.addLayout(dictsLayout)
        groupLayout.addLayout(exportsLayout)
        self.layout.addLayout(groupLayout)

        optionsBox = QGroupBox('Options')
        optionsLayout = QHBoxLayout()
        optLay1 = QVBoxLayout()
        optLay2 = QVBoxLayout()
        optLay3 = QVBoxLayout()

        startupLay = QHBoxLayout()
        startupLay.addWidget(self.miQLabel('Open on Startup:', 182))
        startupLay.addWidget(self.openOnStart)
        optLay1.addLayout(startupLay)

        highSentLay = QHBoxLayout()
        highSentLay.addWidget(self.miQLabel('Highlight Examples Sentences:', 182))
        highSentLay.addWidget(self.highlightSentence)
        optLay1.addLayout(highSentLay)

        highWordLay = QHBoxLayout()
        highWordLay.addWidget(self.miQLabel('Highlight Searched Term:', 182))
        highWordLay.addWidget(self.highlightTarget)
        optLay1.addLayout(highWordLay)

        expTargetLay = QHBoxLayout()
        expTargetLay.addWidget(self.miQLabel('Show Export Target:', 182))
        expTargetLay.addWidget(self.showTarget)
        optLay1.addLayout(expTargetLay)

        toolTipLay = QHBoxLayout()
        toolTipLay.addWidget(self.miQLabel('Dictionary Tooltips:', 182))
        toolTipLay.addWidget(self.tooltipCB)
        optLay1.addLayout(toolTipLay)

        gHLay = QHBoxLayout()
        gHLay.addWidget(self.miQLabel('Global Hotkeys:', 182))
        gHLay.addWidget(self.globalHotkeys)
        optLay1.addLayout(gHLay)

        extensionMp3Lay = QHBoxLayout()
        extensionMp3Lay.addWidget(self.miQLabel("Convert Extension Audio to MP3", 182))
        extensionMp3Lay.addWidget(self.convertToMp3)
        optLay1.addLayout(extensionMp3Lay)

        disableCondensedLay = QHBoxLayout()
        disableCondensedLay.addWidget(self.miQLabel("Disable Condensed Audio Messages:", 182))
        disableCondensedLay.addWidget(self.disableCondensedMessages)
        optLay1.addLayout(disableCondensedLay)

        globalOpenLay = QHBoxLayout()
        globalOpenLay.addWidget(self.miQLabel('Open on Global Search:', 323))
        globalOpenLay.addWidget(self.globalOpen)
        optLay2.addLayout(globalOpenLay)

        totResLay = QHBoxLayout()
        totResLay.addWidget(self.miQLabel('Max Total Search Results:', 180))
        totResLay.addWidget(self.totalDefs)
        self.totalDefs.setFixedWidth(160)
        optLay2.addLayout(totResLay)

        dictResLay = QHBoxLayout()
        dictResLay.addWidget(self.miQLabel('Max Dictionary Search Results:', 180))
        dictResLay.addWidget(self.dictDefs)
        self.dictDefs.setFixedWidth(160)
        optLay2.addLayout(dictResLay)

        genJSExportLay = QHBoxLayout()
        genJSExportLay.addWidget(self.miQLabel('Add Cards with Japanese Readings:', 323))
        genJSExportLay.addWidget(self.genJSExport)
        optLay2.addLayout(genJSExportLay)

        genJSEditLay = QHBoxLayout()
        genJSEditLay.addWidget(self.miQLabel('Japanese Readings on Edit:', 323))
        genJSEditLay.addWidget(self.genJSEdit)
        optLay2.addLayout(genJSEditLay)

        countryLay = QHBoxLayout()
        countryLay.addWidget(self.miQLabel('Google Images Search Region:', 180))
        countryLay.addWidget(self.googleCountry)
        self.googleCountry.setFixedWidth(160)
        optLay2.addLayout(countryLay)

        safeLay = QHBoxLayout()
        safeLay.addWidget(self.miQLabel('Safe Search:', 323))
        safeLay.addWidget(self.safeSearch)
        optLay2.addLayout(safeLay)

        optLay2.addStretch()
        
        maxWidLay = QHBoxLayout()
        maxWidLay.addWidget(self.miQLabel('Maximum Image Width:', 140))
        maxWidLay.addWidget(self.maxImgWidth)
        optLay3.addLayout(maxWidLay)

        maxHeiLay = QHBoxLayout()
        maxHeiLay.addWidget(self.miQLabel('Maximum Image Height:', 140))
        maxHeiLay.addWidget(self.maxImgHeight)
        optLay3.addLayout(maxHeiLay)

        frontBracketLay = QHBoxLayout()
        frontBracketLay.addWidget(self.miQLabel('Surround Term (Front):', 140))
        frontBracketLay.addWidget(self.frontBracket)
        optLay3.addLayout(frontBracketLay)

        backBracketLay = QHBoxLayout()
        backBracketLay.addWidget(self.miQLabel('Surround Term (Back):', 140))
        backBracketLay.addWidget(self.backBracket)
        optLay3.addLayout(backBracketLay)


        forvoLay = QHBoxLayout()
        forvoLay.addWidget(self.miQLabel('Forvo Language:', 140))
        forvoLay.addWidget(self.forvoLang)
        optLay3.addLayout(forvoLay)

        dictOnTopLay= QHBoxLayout()
        dictOnTopLay.addWidget(self.miQLabel("Always on Top:", 323))
        dictOnTopLay.addWidget(self.dictOnTop)
        optLay3.addLayout(dictOnTopLay)


        extensionAudioLay = QHBoxLayout()
        extensionAudioLay.addWidget(self.condensedAudioDirectoryLabel)
        self.chooseAudioDirectory.setFixedWidth(100)
        extensionAudioLay.addWidget(self.chooseAudioDirectory)
        optLay3.addLayout(extensionAudioLay)

        optLay3.addStretch()


        optionsLayout.addLayout(optLay1)
        optionsLayout.addStretch()
        optionsLayout.addWidget(self.getLineSeparator())
        optionsLayout.addStretch()
        optionsLayout.addLayout(optLay2)
        optionsLayout.addStretch()
        optionsLayout.addWidget(self.getLineSeparator())
        optionsLayout.addStretch()
        optionsLayout.addLayout(optLay3)

        optionsBox.setLayout(optionsLayout)
        self.layout.addWidget(optionsBox)
        self.layout.addStretch()

        buttonsLayout = QHBoxLayout()
        buttonsLayout.addWidget(self.restoreButton)
        buttonsLayout.addStretch()
        buttonsLayout.addWidget(self.cancelButton)
        buttonsLayout.addWidget(self.applyButton)

        self.layout.addLayout(buttonsLayout)
        self.settingsTab.setLayout(self.layout)

    def cleanDictName(self, name):
        return re.sub(r'l\d+name', '', name)

    def getSVGWidget(self,  name):
        widget = MigakuSVG(join(self.addonPath, 'icons', name))
        widget.setFixedSize(27,27)
        return widget

    def getHTML(self):
        htmlPath = join(self.addonPath, 'guide.html')
        url = QUrl.fromLocalFile(htmlPath)
        with open(htmlPath,'r', encoding="utf-8") as fh:
            html = fh.read()
        return html, url

    def getUserGuideTab(self):
        guide = AnkiWebView()
        guide._page.profile().setHttpUserAgent('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.47 Safari/537.36')
        guide._page._bridge.onCmd = attemptOpenLink
        html, url = self.getHTML()
        guide._page.setHtml(html, url)
        guide.setObjectName("tab_4")
        return guide

    def getAboutTab(self):
        tab_4 = QWidget()
        tab_4.setObjectName("tab_4")
        tab4vl = QVBoxLayout()
        migakuAbout = QGroupBox()
        migakuAbout.setTitle('Migaku')
        migakuAboutVL = QVBoxLayout()

        migakuAbout.setStyleSheet("QGroupBox { font-weight: bold; } ")
        migakuAboutText = QLabel("This an original Migaku add-on. Migaku seeks to be a comprehensive platform for acquiring foreign languages. The official Migaku website will be published soon!")
        migakuAboutText.setWordWrap(True);
        migakuAboutText.setOpenExternalLinks(True);
        migakuAbout.setLayout(migakuAboutVL)
        migakuAboutLinksTitle = QLabel("<b>Links<b>")
 
        migakuAboutLinksHL3 = QHBoxLayout()


        migakuInfo = QLabel("Migaku:")
        migakuInfoSite = self.getSVGWidget('migaku.svg')
        migakuInfoSite.setCursor(QCursor(Qt.PointingHandCursor))

        migakuInfoYT = self.getSVGWidget('Youtube.svg')
        migakuInfoYT.setCursor(QCursor(Qt.PointingHandCursor))

        migakuInfoTW = self.getSVGWidget('Twitter.svg')
        migakuInfoTW.setCursor(QCursor(Qt.PointingHandCursor))


        migakuPatreonIcon = self.getSVGWidget('Patreon.svg')
        migakuPatreonIcon.setCursor(QCursor(Qt.PointingHandCursor))
        migakuAboutLinksHL3.addWidget(migakuInfo)
        migakuAboutLinksHL3.addWidget(migakuInfoSite)
        migakuAboutLinksHL3.addWidget(migakuInfoYT)
        migakuAboutLinksHL3.addWidget(migakuInfoTW)
        migakuAboutLinksHL3.addWidget(migakuPatreonIcon)
        migakuAboutLinksHL3.addStretch()

        migakuAboutVL.addWidget(migakuAboutText)
        migakuAboutVL.addWidget(migakuAboutLinksTitle)
        migakuAboutVL.addLayout(migakuAboutLinksHL3)
        
        migakuContact = QGroupBox()
        migakuContact.setTitle('Contact Us')
        migakuContactVL = QVBoxLayout()
        migakuContact.setStyleSheet("QGroupBox { font-weight: bold; } ")
        migakuContactText = QLabel("If you would like to report a bug or contribute to the add-on, the best way to do so is by starting a ticket or pull request on GitHub. If you are looking for personal assistance using the add-on, check out the Migaku Patreon Discord Server.")
        migakuContactText.setWordWrap(True)

        gitHubIcon = self.getSVGWidget('Github.svg')
        gitHubIcon.setCursor(QCursor(Qt.PointingHandCursor))
        
        migakuThanks = QGroupBox()
        migakuThanks.setTitle('A Word of Thanks')
        migakuThanksVL = QVBoxLayout()
        migakuThanks.setStyleSheet("QGroupBox { font-weight: bold; } ")
        migakuThanksText = QLabel("Thanks so much to all Migaku supporters! We would not have been able to develop this add-on or any other Migaku project without your support!")
        migakuThanksText.setOpenExternalLinks(True);
        migakuThanksText.setWordWrap(True);
        migakuThanksVL.addWidget(migakuThanksText)

        migakuContactVL.addWidget(migakuContactText)
        migakuContactVL.addWidget(gitHubIcon)
        migakuContact.setLayout(migakuContactVL)
        migakuThanks.setLayout(migakuThanksVL)
        tab4vl.addWidget(migakuAbout)
        tab4vl.addWidget(migakuContact)
        tab4vl.addWidget(migakuThanks)
        tab4vl.addStretch()
        tab_4.setLayout(tab4vl)

        migakuInfoSite.clicked.connect(lambda: openLink('https://migaku.io'))
        migakuPatreonIcon.clicked.connect(lambda: openLink('https://www.patreon.com/Migaku'))
        migakuInfoYT.clicked.connect(lambda: openLink('https://www.youtube.com/channel/UCQFe3x4WAgm7joN5daMm5Ew'))
        migakuInfoTW.clicked.connect(lambda: openLink('https://twitter.com/Migaku_Yoga'))
        gitHubIcon.clicked.connect(lambda: openLink('https://github.com/migaku-official/Migaku-Dictionary-Addon'))
        return tab_4

