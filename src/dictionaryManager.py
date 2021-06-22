import aqt
import json
import zipfile
import sip
import re
import operator
import shutil
from aqt.qt import *
from aqt import mw
from .dictionaryWebInstallWizard import DictionaryWebInstallWizard
from .freqConjWebWindow import FreqConjWebWindow



class DictionaryManagerWidget(QWidget):
    
    def __init__(self, parent=None):
        super(DictionaryManagerWidget, self).__init__(parent)

        lyt = QVBoxLayout()
        lyt.setContentsMargins(0, 0, 0, 0)
        self.setLayout(lyt)

        splitter = QSplitter()
        splitter.setChildrenCollapsible(False)
        lyt.addWidget(splitter)


        left_side = QWidget()
        splitter.addWidget(left_side)
        left_lyt = QVBoxLayout()
        left_side.setLayout(left_lyt)

        self.dict_tree = QTreeWidget()
        self.dict_tree.setHeaderHidden(True)
        self.dict_tree.currentItemChanged.connect(self.on_current_item_change)
        left_lyt.addWidget(self.dict_tree)

        add_lang_btn = QPushButton('Add a Language')
        add_lang_btn.clicked.connect(self.add_lang)
        left_lyt.addWidget(add_lang_btn)

        web_installer_btn = QPushButton('Install Languages in Wizard')
        web_installer_btn.clicked.connect(self.web_installer)
        left_lyt.addWidget(web_installer_btn)


        right_side = QWidget()
        splitter.addWidget(right_side)
        right_lyt = QVBoxLayout()
        right_side.setLayout(right_lyt)


        self.lang_grp = QGroupBox('Language Options')
        right_lyt.addWidget(self.lang_grp)

        lang_lyt = QVBoxLayout()
        self.lang_grp.setLayout(lang_lyt)

        lang_lyt1 = QHBoxLayout()
        lang_lyt2 = QHBoxLayout()
        lang_lyt.addLayout(lang_lyt2)
        lang_lyt3 = QHBoxLayout()
        lang_lyt.addLayout(lang_lyt3)
        lang_lyt4 = QHBoxLayout()
        lang_lyt.addLayout(lang_lyt4)
        lang_lyt.addLayout(lang_lyt1)

        remove_lang_btn = QPushButton('Remove Language')
        remove_lang_btn.clicked.connect(self.remove_lang)
        lang_lyt1.addWidget(remove_lang_btn)

        web_installer_lang_btn = QPushButton('Install Dictionary in Wizard')
        web_installer_lang_btn.clicked.connect(self.web_installer_lang)
        lang_lyt2.addWidget(web_installer_lang_btn)

        import_dict_btn = QPushButton('Install Dictionary From File')
        import_dict_btn.clicked.connect(self.import_dict)
        lang_lyt2.addWidget(import_dict_btn)

        web_freq_data_btn = QPushButton('Install Frequency Data in Wizard')
        web_freq_data_btn.clicked.connect(self.web_freq_data)
        lang_lyt3.addWidget(web_freq_data_btn)

        set_freq_data_btn = QPushButton('Install Frequency Data From File')
        set_freq_data_btn.clicked.connect(self.set_freq_data)
        lang_lyt3.addWidget(set_freq_data_btn)

        web_conj_data_btn = QPushButton('Install Conjugation Data in Wizard')
        web_conj_data_btn.clicked.connect(self.web_conj_data)
        lang_lyt4.addWidget(web_conj_data_btn)

        set_conj_data_btn = QPushButton('Install Conjugation Data From File')
        set_conj_data_btn.clicked.connect(self.set_conj_data)
        lang_lyt4.addWidget(set_conj_data_btn)

        lang_lyt1.addStretch()
        lang_lyt2.addStretch()
        lang_lyt3.addStretch()
        lang_lyt4.addStretch()


        self.dict_grp = QGroupBox('Dictionary Options')
        right_lyt.addWidget(self.dict_grp)

        dict_lyt = QHBoxLayout()
        self.dict_grp.setLayout(dict_lyt)

        remove_dict_btn = QPushButton('Remove Dictionary')
        remove_dict_btn.clicked.connect(self.remove_dict)
        dict_lyt.addWidget(remove_dict_btn)

        set_term_headers_btn = QPushButton('Edit Definition Header')
        set_term_headers_btn.clicked.connect(self.set_term_header)
        dict_lyt.addWidget(set_term_headers_btn)

        dict_lyt.addStretch()

    
        right_lyt.addStretch()


        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)


        self.reload_tree_widget()

        self.on_current_item_change(None, None)


    def info(self, text):
        dlg = QMessageBox(QMessageBox.Information, 'Migaku Dictioanry', text, QMessageBox.Ok, self)
        return dlg.exec_()


    def get_string(self, text, default_text=''):
        dlg = QInputDialog(self)
        dlg.setWindowTitle('Migaku Dictionary')
        dlg.setLabelText(text + ':')
        dlg.setTextValue(default_text)
        dlg.resize(350, dlg.sizeHint().height())
        ok = dlg.exec_()
        txt = dlg.textValue()
        return txt, ok


    def reload_tree_widget(self):
        db = aqt.mw.miDictDB

        langs = db.getCurrentDbLangs()
        dicts_by_langs = {}

        for info in db.getAllDictsWithLang():
            lang = info['lang']

            dict_list = dicts_by_langs.get(lang, [])
            dict_list.append(info['dict'])
            dicts_by_langs[lang] = dict_list

        self.dict_tree.clear()

        for lang in langs:
            lang_item = QTreeWidgetItem([lang])
            lang_item.setData(0, Qt.UserRole+0, lang)
            lang_item.setData(0, Qt.UserRole+1, None)
            
            self.dict_tree.addTopLevelItem(lang_item)

            for d in dicts_by_langs.get(lang, []):
                dict_name = db.cleanDictName(d)
                dict_name = dict_name.replace('_', ' ')
                dict_item = QTreeWidgetItem([dict_name])
                dict_item.setData(0, Qt.UserRole+0, lang)
                dict_item.setData(0, Qt.UserRole+1, d)
                lang_item.addChild(dict_item)

            lang_item.setExpanded(True)


    def on_current_item_change(self, new_sel, old_sel):

        lang, dict_ = self.get_current_lang_dict()

        self.lang_grp.setEnabled(lang is not None)
        self.dict_grp.setEnabled(dict_ is not None)


    def get_current_lang_dict(self):

        curr_item = self.dict_tree.currentItem()

        lang = None
        dict_ = None

        if curr_item:
            lang = curr_item.data(0, Qt.UserRole+0)
            dict_ = curr_item.data(0, Qt.UserRole+1)

        return lang, dict_


    def get_current_lang_item(self):

        curr_item = self.dict_tree.currentItem()

        if curr_item:
            curr_item_parent = curr_item.parent()
            if curr_item_parent:
                return curr_item_parent
        
        return curr_item


    def get_current_dict_item(self):

        curr_item = self.dict_tree.currentItem()

        if curr_item:
            curr_item_parent = curr_item.parent()
            if curr_item_parent is None:
                return None
        
        return curr_item


    def web_installer(self):

        DictionaryWebInstallWizard.execute_modal()
        self.reload_tree_widget()


    def add_lang(self):
        db = aqt.mw.miDictDB

        text, ok = self.get_string('Select name of new language')
        if not ok:
            return

        name = text.strip()
        if not name:
            self.info('Language names may not be empty.')
            return

        try:
            db.addLanguages([name])
        except Exception as e:
            self.info('Adding language failed.')
            return

        lang_item = QTreeWidgetItem([name])
        lang_item.setData(0, Qt.UserRole+0, name)
        lang_item.setData(0, Qt.UserRole+1, None)

        self.dict_tree.addTopLevelItem(lang_item)
        self.dict_tree.setCurrentItem(lang_item)


    def remove_lang(self):
        db = aqt.mw.miDictDB

        lang_item = self.get_current_lang_item()
        if lang_item is None:
            return
        lang_name = lang_item.data(0, Qt.UserRole+0)

        dlg = QMessageBox(QMessageBox.Question, 'Migaku Dictioanry',
                          'Do you really want to remove the language "%s"?\n\nAll settings and dictionaries for it will be removed.' % lang_name,
                          QMessageBox.Yes | QMessageBox.No, self)
        r = dlg.exec_()

        if r != QMessageBox.Yes:
            return

        # Remove language from db
        db.deleteLanguage(lang_name)

        # Remove frequency data
        try:
            path = os.path.join(addon_path, 'user_files', 'db', 'frequency', '%s.json' % lang_name)
            os.remove(path)
        except OSError:
            pass

        # Remove conjugation data
        try:
            path = os.path.join(addon_path, 'user_files', 'db', 'conjugation', '%s.json' % lang_name)
            os.remove(path)
        except OSError:
            pass

        sip.delete(lang_item)


    def set_freq_data(self):
        lang_name = self.get_current_lang_dict()[0]
        if lang_name is None:
            return

        path = QFileDialog.getOpenFileName(self, 'Select the frequency list you want to import', os.path.expanduser('~'), 'JSON Files (*.json);;All Files (*.*)')[0]
        if not path:
            return

        freq_path = os.path.join(addon_path, 'user_files', 'db', 'frequency')
        os.makedirs(freq_path, exist_ok=True)

        dst_path = os.path.join(freq_path, '%s.json' % lang_name)

        try:
            shutil.copy(path, dst_path)
        except shutil.Error:
            self.info('Importing frequency data failed.')
            return

        self.info('Imported frequency data for "%s".\n\nNote that the frequency data is only applied to newly imported dictionaries for this language.' % lang_name)


    def web_freq_data(self):
        lang_item = self.get_current_lang_item()
        if lang_item is None:
            return
        lang_name = lang_item.data(0, Qt.UserRole+0)

        FreqConjWebWindow.execute_modal(lang_name, FreqConjWebWindow.Mode.Freq)


    def set_conj_data(self):
        lang_name = self.get_current_lang_dict()[0]
        if lang_name is None:
            return

        path = QFileDialog.getOpenFileName(self, 'Select the conjugation data you want to import', os.path.expanduser('~'), 'JSON Files (*.json);;All Files (*.*)')[0]
        if not path:
            return

        conj_path = os.path.join(addon_path, 'user_files', 'db', 'conjugation')
        os.makedirs(conj_path, exist_ok=True)

        dst_path = os.path.join(conj_path, '%s.json' % lang_name)

        try:
            shutil.copy(path, dst_path)
        except shutil.Error:
            self.info('Importing conjugation data failed.')
            return

        self.info('Imported conjugation data for "%s".' % lang_name)


    def web_conj_data(self):
        lang_item = self.get_current_lang_item()
        if lang_item is None:
            return
        lang_name = lang_item.data(0, Qt.UserRole+0)

        FreqConjWebWindow.execute_modal(lang_name, FreqConjWebWindow.Mode.Conj)


    def import_dict(self):
        lang_item = self.get_current_lang_item()
        if lang_item is None:
            return
        lang_name = lang_item.data(0, Qt.UserRole+0)

        path = QFileDialog.getOpenFileName(self, 'Select the dictionary you want to import',
                                           os.path.expanduser('~'), 'ZIP Files (*.zip);;All Files (*.*)')[0]
        if not path:
            return
        
        dict_name = os.path.splitext(os.path.basename(path))[0]
        dict_name, ok = self.get_string('Set name of dictionary', dict_name)

        try:
            importDict(lang_name, path, dict_name)
        except ValueError as e:
            self.info(str(e))
            return

        dict_item = QTreeWidgetItem([dict_name.replace('_', ' ')])
        dict_item.setData(0, Qt.UserRole+0, lang_name)
        dict_item.setData(0, Qt.UserRole+1, dict_name)

        lang_item.addChild(dict_item)
        self.dict_tree.setCurrentItem(dict_item)


    def web_installer_lang(self):
        lang_item = self.get_current_lang_item()
        if lang_item is None:
            return
        lang_name = lang_item.data(0, Qt.UserRole+0)

        DictionaryWebInstallWizard.execute_modal(lang_name)
        self.reload_tree_widget()


    def remove_dict(self):
        db = aqt.mw.miDictDB
        
        dict_item = self.get_current_dict_item()
        if dict_item is None:
            return
        dict_name = dict_item.data(0, Qt.UserRole+1)
        dict_display = dict_item.data(0, Qt.DisplayRole)

        dlg = QMessageBox(QMessageBox.Question, 'Migaku Dictioanry',
                          'Do you really want to remove the dictionary "%s"?' % dict_display,
                          QMessageBox.Yes | QMessageBox.No, self)
        r = dlg.exec_()

        if r != QMessageBox.Yes:
            return

        db.deleteDict(dict_name)
        sip.delete(dict_item)


    def set_term_header(self):
        db = aqt.mw.miDictDB

        dict_name = self.get_current_lang_dict()[1]
        if dict_name is None:
            return

        dict_clean = db.cleanDictName(dict_name)

        term_txt = ', '.join(json.loads(db.getDictTermHeader(dict_clean)))

        term_txt, ok = self.get_string('Set term header for dictionary "%s"' % dict_clean.replace('_', ' '), term_txt)

        if not ok:
            return

        parts_txt = term_txt.split(',')
        parts = []
        valid_parts = ['term', 'altterm', 'pronunciation']

        for part_txt in parts_txt:
            part = part_txt.strip().lower()
            if part not in valid_parts:
                self.info('The term header part "%s" is not valid.' % part_txt)
                return
            parts.append(part)

        db.setDictTermHeader(dict_clean, json.dumps(parts))




addon_path = os.path.dirname(__file__)

def importDict(lang_name, file, dict_name):
    db = aqt.mw.miDictDB

    # Load ZIP file
    try:
        zfile = zipfile.ZipFile(file)
    except zipfile.BadZipFile:
        raise ValueError('Dictionary archive is invalid.')

    # Check if dict is yomichan or has index.json
    is_yomichan = any(fn.startswith('term_bank_') for fn in zfile.namelist())
    has_index = any(fn == 'index.json' for fn in zfile.namelist())

    # Load frequency table
    frequency_dict = getFrequencyList(lang_name)

    # Create dictionary
    dict_name = dict_name.replace(' ', '_')
    table_name = 'l' + str(db.getLangId(lang_name)) + 'name' + dict_name

    term_header = json.dumps(['term', 'altterm', 'pronunciation'])

    try:
        db.addDict(dict_name, lang_name, term_header)
    except Exception:
        raise ValueError('Creating dictioanry failed. Make sure that no other dictionary with the same name exists. Several special characters are also no supported in dictionary names.')

    # Load dict entries
    dict_files = []

    for fn in zfile.namelist():
        if not fn.endswith('.json'):
            continue
        if is_yomichan and not fn.startswith('term_bank_'):
            continue
        dict_files.append(fn)

    dict_files = natural_sort(dict_files)

    loadDict(zfile, dict_files, lang_name, dict_name, frequency_dict, not is_yomichan)

def natural_sort(l): 
    convert = lambda text: int(text) if text.isdigit() else text.lower() 
    alphanum_key = lambda key: [convert(c) for c in re.split('([0-9]+)', key)] 
    return sorted(l, key=alphanum_key)

def loadDict(zfile, filenames, lang, dictName, frequencyDict, miDict = False):
    tableName = 'l' + str(mw.miDictDB.getLangId(lang)) + 'name' + dictName
    jsonDict = []
    for filename in filenames:
        with zfile.open(filename, 'r') as jsonDictFile:
            jsonDict += json.loads(jsonDictFile.read())
    freq = False
    if frequencyDict:
        freq = True
        if miDict:
            jsonDict = organizeDictionaryByFrequency(jsonDict, frequencyDict, dictName, lang, True)
        else:
            jsonDict = organizeDictionaryByFrequency(jsonDict, frequencyDict, dictName, lang)
    for count, entry in enumerate(jsonDict):
        if miDict:
            handleMiDictEntry(jsonDict, count, entry, freq)
        else: 
            handleYomiDictEntry(jsonDict, count, entry, freq)
    mw.miDictDB.importToDict(tableName, jsonDict)
    mw.miDictDB.commitChanges()

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
    for idx, entry in enumerate(jsonDict):
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
    if miDict:
        return sorted(jsonDict, key = lambda i: i['frequency'])
    else:
        return sorted(jsonDict, key=operator.itemgetter(8))

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

def getFrequencyList(lang):
    filePath = os.path.join(addon_path, 'user_files', 'db', 'frequency', '%s.json' % lang)
    frequencyDict = {}
    if os.path.exists(filePath):
        frequencyList = json.load(open(filePath, 'r', encoding='utf-8-sig'))
        if isinstance(frequencyList[0], str):
            yomi = False
            frequencyDict['readingDictionaryType'] = False 
        elif isinstance(frequencyList[0], list) and len(frequencyList[0]) == 2 and isinstance(frequencyList[0][0], str) and isinstance(frequencyList[0][1], str):
            yomi = True
            frequencyDict['readingDictionaryType'] = True 
        else:
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