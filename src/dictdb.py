# -*- coding: utf-8 -*-

import sqlite3
import os.path
from aqt.utils import showInfo
from .miutils import miInfo
import re
import json
addon_path = os.path.dirname(__file__)
from aqt import mw

class DictDB:
    conn = None
    c = None

    def __init__(self):
        db_file = os.path.join(mw.pm.addonFolder(), addon_path, "user_files", "db", "dictionaries.sqlite")
        self.conn=sqlite3.connect(db_file, check_same_thread=False)
        self.c = self.conn.cursor()
        self.c.execute("PRAGMA foreign_keys = ON")

    def connect(self):
        self.oldConnection = self.c
        db_file = os.path.join(mw.pm.addonFolder(), addon_path, "user_files", "db", "dictionaries.sqlite")
        self.conn=sqlite3.connect(db_file)
        self.c = self.conn.cursor()
        self.c.execute("PRAGMA foreign_keys = ON")

    def reload(self):
        self.c.close()
        self.c = self.oldConnection

    def closeConnection(self):
        self.c.close()
        self = False

    def getLangId(self, lang):
        self.c.execute('SELECT id FROM langnames WHERE langname = ?;',  (lang,))
        try:
            (lid,) = self.c.fetchone()
            return lid
        except:
            return None
    
    def deleteDict(self, d):
        self.c.execute('DELETE FROM dictnames WHERE dictname = ?;', (d,))
       
    def getDictsByLanguage(self, lang):
        lid = self.getLangId(lang)
        self.c.execute('SELECT dictname FROM dictnames WHERE lid = ?;',  (lid,))
        try:
            langs = []
            allLs = self.c.fetchall()
            if len(allLs) > 0:
                for l in allLs:
                    langs.append(l[0])
            return langs
        except:
            return []

    def addDicts(self, dicts, lang, termHeader):
        lid = self.getLangId(lang)
        toRemove = []
        for d in dicts:
            try:
                self.c.execute('INSERT INTO dictnames (dictname, lid, fields, addtype, termHeader, duplicateHeader) VALUES (?, ?, "[]", "add", ?, 0);', (d,lid, termHeader))
                self.createDB(self.formatDictName(lid, d))
            except:
                miInfo('The "' + d + '" dictionary cannot be imported. Please remember that every dictionary must have a unique name, amd cannot contain spaces or punctuation characters.', level='err')
                toRemove.append(d)
        for rem in toRemove:
            dicts.remove(rem)
        self.commitChanges()
        return dicts

    def formatDictName(self, lid, name):
        return 'l' + str(lid) + 'name' + name

    def deleteLanguages(self, lList, progressWidget, bar, textL):
        bar.setMaximum(len(lList))
        for idx ,l in enumerate(lList):
            textL.setText('Removing the "' + l + '" language and all associated dictionaries.')
            mw.app.processEvents() 
            self.dropTables('l' + str(self.getLangId(l)) + 'name%')
            self.c.execute('DELETE FROM langnames WHERE langname = ?;', (l,))
            bar.setValue(idx + 1)
            mw.app.processEvents() 
        self.commitChanges()
        self.c.execute("VACUUM;")

    def addLanguages(self, list):
        for l in list:
            self.c.execute('INSERT INTO langnames (langname) VALUES (?);', (l,))
        self.commitChanges()

    def getCurrentDbLangs(self):
        self.c.execute("SELECT langname FROM langnames;")
        try:
            langs = []
            allLs = self.c.fetchall()
            if len(allLs) > 0:
                for l in allLs:
                    langs.append(l[0])
            return langs
        except:
            return []

    def getUserGroups(self, dicts):
        currentDicts = self.getDictToTable()
        foundDicts = []
        for d in dicts:
            if d in currentDicts or d in ['Google Images', 'Forvo']:
                if d == 'Google Images':
                    foundDicts.append({'dict' : 'Google Images', 'lang' : ''})
                elif d == 'Forvo':
                    foundDicts.append({'dict' : 'Forvo', 'lang' : ''})
                else:
                    foundDicts.append(currentDicts[d])
        return foundDicts

    def getDictToTable(self):
        self.c.execute("SELECT dictname, lid, langname FROM dictnames INNER JOIN langnames ON langnames.id = dictnames.lid;")
        try:
            dicts = {}
            allDs = self.c.fetchall()
            if len(allDs) > 0:
                for d in allDs:
                    dicts[d[0]] = {'dict' : self.formatDictName(d[1], d[0]), 'lang' : d[2]}
            return dicts
        except:
            return []

    def fetchDefs(self):
        self.c.execute("SELECT definition FROM l64name大辞林 LIMIT 10;")
        try:
            langs = []
            allLs = self.c.fetchall()
            if len(allLs) > 0:
                for l in allLs:
                    langs.append(l[0])
            return langs
        except:
            return []

    def getAllDicts(self):
        self.c.execute("SELECT dictname, lid FROM dictnames;")
        try:
            dicts = []
            allDs = self.c.fetchall()
            if len(allDs) > 0:
                for d in allDs:
                    dicts.append(self.formatDictName(d[1], d[0]))
            return dicts
        except:
            return []

    def getAllDictsWithLang(self):
        self.c.execute("SELECT dictname, lid, langname FROM dictnames INNER JOIN langnames ON langnames.id = dictnames.lid;")
        try:
            dicts = []
            allDs = self.c.fetchall()
            if len(allDs) > 0:
                for d in allDs:
                    dicts.append({'dict' : self.formatDictName(d[1], d[0]), 'lang' : d[2]})
            return dicts
        except:
            return []

    def getDefaultGroups(self):
        langs = self.getCurrentDbLangs()
        dictsByLang = {}
        for lang in langs:
            self.c.execute("SELECT dictname, lid FROM dictnames INNER JOIN langnames ON langnames.id = dictnames.lid WHERE langname = ?;", (lang,)) 
            allDs = self.c.fetchall()
            dicts = {}
            dicts['customFont'] = False
            dicts['font'] = False
            dicts['dictionaries'] = []
            if len(allDs) > 0:
                for d in allDs:
                    dicts['dictionaries'].append({'dict' : self.formatDictName(d[1], d[0]), 'lang' : lang})
            if len(dicts['dictionaries']) > 0:
                dictsByLang[lang] = dicts
        return dictsByLang

    def cleanDictName(self, name):
        return re.sub(r'l\d+name', '', name)


    def getDuplicateSetting(self, name):
        self.c.execute('SELECT duplicateHeader, termHeader  FROM dictnames WHERE dictname=?', (name, ))
        try:
            (duplicateHeader,termHeader) = self.c.fetchone()
            return duplicateHeader, json.loads(termHeader)
        except:
            return None

    def getDefEx(self, sT):
        if sT in ['Definition', 'Example']:
            return True
        return False

    def applySearchType(self,terms, sT):
        for idx, term in enumerate(terms):
            if sT in  ['Forward','Pronunciation']:
               terms[idx] = terms[idx] + '%';
            elif sT ==  'Backward':
                terms[idx] = '%_' + terms[idx]
            elif sT ==  'Anywhere':
                terms[idx] = '%' + terms[idx] + '%'
            elif sT ==  'Exact':
                terms[idx] = terms[idx]
            elif sT ==  'Definition':
                terms[idx] = '%' + terms[idx] + '%'
            else:
                terms[idx] = '%「%' + terms[idx] + '%」%'
        return terms;

    def deconjugate(self, term, conjugations):
        deconjugations = []
        for c in conjugations:
            if term.endswith(c['inflected']): 
                for x in c['dict']:
                    deinflected = self.rreplace(term, c['inflected'], x, 1)
                    if 'prefix' in c:
                        prefix = c['prefix']
                        if deinflected.startswith(prefix):
                            deprefixedDeinflected =  deinflected[len(prefix):]
                            if deprefixedDeinflected not in deconjugations:
                                deconjugations.append(deprefixedDeinflected)
                    if deinflected not in deconjugations:
                        deconjugations.append(deinflected)
        deconjugations = list(filter(lambda x: len(x) > 1, deconjugations))  
        deconjugations.insert(0, term)    
        return deconjugations

    def rreplace(self, s, old, new, occurrence):
        li = s.rsplit(old, occurrence)
        return new.join(li)

    def searchTerm(self, term, selectedGroup, conjugations, sT, deinflect, dictLimit, maxDefs):
        alreadyConjTyped = {}
        results = {}
        group = selectedGroup['dictionaries']
        totalDefs = 0
        defEx = self.getDefEx(sT)
        op = 'LIKE'
        if defEx:
            column = 'definition'
        elif sT == 'Pronunciation':
            column = 'pronunciation'
        else:
            column = 'term'
        if sT == 'Exact':
            op = '='
        for dic in group:
            if dic['dict'] == 'Google Images':
                results['Google Images'] = True
                continue
            elif dic['dict'] == 'Forvo':
                results['Forvo'] = True
                continue
            terms = [term]
            if deinflect:
                if dic['lang'] in alreadyConjTyped:
                    terms = alreadyConjTyped[dic['lang']]
                elif dic['lang'] in conjugations:
                    terms = self.deconjugate(term, conjugations[dic['lang']])
                    terms = self.applySearchType(terms, sT)
                    alreadyConjTyped[dic['lang']] = terms
                else:
                    terms = self.applySearchType(terms, sT)
                    alreadyConjTyped[dic['lang']] = terms
            else:
                if term in alreadyConjTyped:
                    terms = alreadyConjTyped[term]
                else:
                    terms = self.applySearchType(terms, sT)
                    alreadyConjTyped[term] = terms

            toQuery = self.getQueryCriteria(column, terms, op)  
            termTuple = tuple(terms)  
            allRs = self.executeSearch(dic['dict'], toQuery, dictLimit, termTuple)
            if len(allRs) > 0:
                dictRes = []
                for r in allRs:
                    totalDefs += 1
                    dictRes.append(self.resultToDict(r))
                    if totalDefs >= maxDefs:
                        results[self.cleanDictName(dic['dict'])] = dictRes
                        return results
                results[self.cleanDictName(dic['dict'])] = dictRes
            elif not defEx and not sT == 'Pronunciation':
                columns = ['altterm', 'pronunciation']
                for col in columns:
                    toQuery = self.getQueryCriteria(col, terms, op)  
                    termTuple = tuple(terms)  
                    allRs = self.executeSearch(dic['dict'], toQuery, dictLimit, termTuple)
                    if len(allRs) > 0:
                        dictRes = []
                        for r in allRs:
                            totalDefs += 1
                            dictRes.append(self.resultToDict(r))
                            if totalDefs >= maxDefs:
                                results[self.cleanDictName(dic['dict'])] = dictRes
                                return results
                        results[self.cleanDictName(dic['dict'])] = dictRes
                        break
        return results

    def resultToDict(self, r):
        return {'term' : r[0], 'altterm' : r[1], 'pronunciation' : r[2], 'pos' : r[3], 'definition' : r[4], 'examples' : r[5], 'audio' : r[6], 'starCount' : r[7]}

    def executeSearch(self, dictName, toQuery, dictLimit, termTuple):
        try:
            self.c.execute("SELECT term, altterm, pronunciation, pos, definition, examples, audio, starCount FROM " + dictName +" WHERE " + toQuery + " ORDER BY LENGTH(term) ASC, frequency ASC LIMIT "+dictLimit +" ;", termTuple)
            return self.c.fetchall()
        except:
            return []

    def getQueryCriteria(self, col, terms, op = 'LIKE'):

        toQuery = ''
        for idx, item in enumerate(terms):
            if idx == 0:
                toQuery += ' ' + col + ' '+ op +' ? '
            else:
                toQuery += ' OR ' + col + ' '+ op +' ? '
        return toQuery

    def getDefForMassExp(self, term, dN, limit, rN):
        duplicateHeader, termHeader = self.getDuplicateSetting(rN)
        results = []
        columns = ['term','altterm', 'pronunciation']
        for col in columns:
            terms = [term]
            toQuery =  ' ' + col + ' = ? '
            termTuple = tuple(terms)  
            allRs = self.executeSearch(dN, toQuery, limit, termTuple)
            if len(allRs) > 0:
                for r in allRs:
                    results.append(self.resultToDict(r))
                break
        return results,  duplicateHeader, termHeader;

    def cleanLT(self,text):
        return re.sub(r'<((?:[^b][^r])|(?:[b][^r]))', r'&lt;\1', str(text))

    def createDB(self, text):
        self.c.execute('CREATE TABLE  IF NOT EXISTS  ' + text +'(term CHAR(40) NOT NULL, altterm CHAR(40), pronunciation CHAR(100), pos CHAR(40), definition TEXT, examples TEXT, audio TEXT, frequency MEDIUMINT, starCount TEXT);')
        self.c.execute("CREATE INDEX IF NOT EXISTS it" + text +" ON " + text +" (term);")
        self.c.execute("CREATE INDEX IF NOT EXISTS itp" + text +" ON " + text +" ( term, pronunciation );")
        self.c.execute("CREATE INDEX IF NOT EXISTS ia" + text +" ON " + text +" (altterm);")
        self.c.execute("CREATE INDEX IF NOT EXISTS iap" + text +" ON " + text +" ( altterm, pronunciation );")
        self.c.execute("CREATE INDEX IF NOT EXISTS ia" + text +" ON " + text +" (pronunciation);")

    def importToDict(self, dictName, dictionaryData):
        self.c.executemany('INSERT INTO ' + dictName + ' (term, altterm, pronunciation, pos, definition, examples, audio, frequency, starCount) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);', dictionaryData)

    def dropTables(self, text):
        self.c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE ?;" , (text, ))
        dicts = self.c.fetchall()
        for name in dicts:
            self.c.execute("DROP TABLE " + name[0] + " ;")

    def setFieldsSetting(self, name, fields):
        self.c.execute('UPDATE dictnames SET fields = ? WHERE dictname=?', (fields, name))
        self.commitChanges()

    def setAddType(self, name, addType):
        self.c.execute('UPDATE dictnames SET addtype = ? WHERE dictname=?', (addType, name))
        self.commitChanges()

    def getFieldsSetting(self, name):
        self.c.execute('SELECT fields FROM dictnames WHERE dictname=?', (name, ))
        try:
            (fields,) = self.c.fetchone()
            return json.loads(fields)
        except:
            return None

    def getAddTypeAndFields(self, dictName):
        self.c.execute('SELECT fields, addtype FROM dictnames WHERE dictname=?', (dictName, ))
        try:
            (fields, addType) = self.c.fetchone()
            return json.loads(fields), addType;
        except:
            return None

    def getDupHeaders(self):
        self.c.execute('SELECT dictname, duplicateHeader FROM dictnames')
        try:
            dictHeaders = self.c.fetchall()
            results = {}
            if len(dictHeaders) > 0:
                for r in dictHeaders:
                    results[r[0]] = r[1]
                return results
        except:
            return None

    def setDupHeader(self,duplicateHeader, name):
        self.c.execute('UPDATE dictnames SET duplicateHeader = ? WHERE dictname=?', (duplicateHeader, name))
        self.commitChanges()

    def getTermHeaders(self):
        self.c.execute('SELECT dictname, termHeader FROM dictnames')
        try:
            dictHeaders = self.c.fetchall()
            results = {}
            if len(dictHeaders) > 0:
                for r in dictHeaders:
                    results[r[0]] = json.loads(r[1])
                return results
        except:
            return None

    def getAddType(self, name):
        self.c.execute('SELECT addtype FROM dictnames WHERE dictname=?', (name, ))
        try:
            (addType,) = self.c.fetchone()
            return addType
        except:
            return None

    def commitChanges(self):
        self.conn.commit()
