# -*- coding: utf-8 -*-
# 
import argparse
import json
import os
import urllib
from aqt.utils import  showInfo
from bs4 import BeautifulSoup
import requests
import re
import base64
from aqt.qt import QThread, pyqtSignal

languages = {"German" : "de",
 "Tatar" : "tt",
 "Russian" : "ru",
 "English" : "en",
 "Spanish" : "es",
 "Japanese" : "ja",
 "French" : "fr",
 "Portuguese" : "pt",
 "Polish" : "pl",
 "Dutch" : "nl",
 "Italian" : "it",
 "Mandarin Chinese" : "zh",
 "Ancient Greek" : "grc",
 "Swedish" : "sv",
 "Turkish" : "tr",
 "Arabic" : "ar",
 "Hungarian" : "hu",
 "Korean" : "ko",
 "Luxembourgish" : "lb",
 "Czech" : "cs",
 "Ukrainian" : "uk",
 "Greek" : "el",
 "Catalan" : "ca",
 "Hebrew" : "he",
 "Persian" : "fa",
 "Mari" : "chm",
 "Finnish" : "fi",
 "Cantonese" : "yue",
 "Urdu" : "ur",
 "Esperanto" : "eo",
 "Danish" : "da",
 "Bulgarian" : "bg",
 "Latin" : "la",
 "Lithuanian" : "lt",
 "Romanian" : "ro",
 "Min Nan" : "nan",
 "Norwegian Bokmål" : "no",
 "Vietnamese" : "vi",
 "Icelandic" : "is",
 "Croatian" : "hr",
 "Irish" : "ga",
 "Basque" : "eu",
 "Wu Chinese" : "wuu",
 "Belarusian" : "be",
 "Latvian" : "lv",
 "Bashkir" : "ba",
 "Kabardian" : "kbd",
 "Hindi" : "hi",
 "Slovak" : "sk",
 "Punjabi" : "pa",
 "Low German" : "nds",
 "Serbian" : "sr",
 "Hakka" : "hak",
 "Uyghur" : "ug",
 "Azerbaijani" : "az",
 "Thai" : "th",
 "Indonesian" : "ind",
 "Estonian" : "et",
 "Slovenian" : "sl",
 "Tagalog" : "tl",
 "Venetian" : "vec",
 "Northern Sami" : "sme",
 "Yiddish" : "yi",
 "Galician" : "gl",
 "Bengali" : "bn",
 "Afrikaans" : "af",
 "Welsh" : "cy",
 "Interlingua" : "ia",
 "Armenian" : "hy",
 "Chuvash" : "cv",
 "Kurdish" : "ku"}
 

class Forvo(QThread):

    resultsFound = pyqtSignal(list)
    noResults = pyqtSignal(str)

    def __init__(self, language):
        QThread.__init__(self)
        self.selLang = language
        self.term = False
        self.langShortCut = languages[self.selLang]
        self.GOOGLE_SEARCH_URL = "https://forvo.com/word/◳t/#" + self.langShortCut #◳r
        self.session = requests.session()
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:10.0) \
                    Gecko/20100101 Firefox/10.0"
            }
        )

    def setTermIdName(self, term, idName):
        self.term = term
        self.idName = idName

    def run(self):
        if self.term:
            resultList = [self.attemptFetchForvoLinks(self.term), self.idName]
            self.resultsFound.emit(resultList)


    def search(self, term, lang = False):
        if lang and self.selLang != lang:
            self.selLang = lang
            self.langShortCut = languages[self.selLang]
            self.GOOGLE_SEARCH_URL = "https://forvo.com/word/◳t/#" + self.langShortCut
        query = self.GOOGLE_SEARCH_URL.replace('◳t', re.sub(r'[\/\'".,&*@!#()\[\]\{\}]', '', term))
        return self.forvo_search(query)

    def decodeURL(self, url1, url2, protocol, audiohost, server):
        url2 = protocol + "//" + server + "/player-mp3-highHandler.php?path=" + url2;
        url1 = protocol + "//" + audiohost + "/mp3/" + base64.b64decode(url1).decode("utf-8", "strict")
        return url1, url2

    def attemptFetchForvoLinks(self,term):
        urls = self.search(term)
        if len(urls) > 0:
            return json.dumps(urls)
        else:
            return False

    def generateURLS(self, results):
        audio = re.findall(r'var pronunciations = \[([\w\W\n]*?)\];', results)
        if not audio:
            return []
        audio = audio[0]
        data = re.findall(self.selLang + r'.*?Pronunciation by (?:<a.*?>)?(\w+).*?class="lang_xx"\>(.*?)\<.*?,.*?,.*?,.*?,\'(.+?)\',.*?,.*?,.*?\'(.+?)\'', audio)     
        if data:
            server = re.search(r"var _SERVER_HOST=\'(.+?)\';", results).group(1)
            audiohost = re.search(r'var _AUDIO_HTTP_HOST=\'(.+?)\';', results).group(1)
            protocol = 'https:'
            urls = []
            for datum in data:
                url1, url2 = self.decodeURL(datum[2],datum[3],protocol, audiohost, server)
                urls.append([datum[0],datum[1], url1, url2])
            return urls
        else:
            return []

    def setSearchRegion(self, region):
        self.region = region

    def forvo_search(self, query_gen):
        try:
            html = self.session.get(query_gen).text
        except:
            self.noResults.emit('The Forvo Dictionary could not be loaded, please confirm that your are connected to the internet and try again. ')
            return []
        results = html
            
        return self.generateURLS(results)
