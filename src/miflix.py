import sys
import json 
import re
from .miutils import miInfo
from os.path import join, exists, dirname
sys.path.insert(0, join(dirname(__file__)))
from aqt.qt import QThread, pyqtSignal
import asyncio
import tornado.ioloop
import tornado.web
import os.path
from threading import Thread
from aqt.qt import QThread, pyqtSignal
import os, uuid
from aqt import mw
from anki.collection import Collection
from threading import Timer
from anki.utils import isWin

def getNextBatchOfCards(self, start, incrementor):
    return self.db.all("SELECT c.ivl, n.flds, c.ord, n.mid FROM cards AS c INNER JOIN notes AS n ON c.nid = n.id WHERE c.type != 0 ORDER BY c.ivl LIMIT %s, %s;"%(start, incrementor))

Collection.getNextBatchOfCards = getNextBatchOfCards



class MigakuHTTPHandler(tornado.web.RequestHandler):

    def set_default_headers(self):
        self.set_header("Access-Control-Allow-Origin", "*")
        self.set_header("Access-Control-Allow-Headers", "x-requested-with")
        self.set_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')

    def initialize(self):
        self.mw = self.application.settings.get('mw')
        self.addonDirectory = dirname(__file__)
        self.tempDirectory = join(self.addonDirectory, "temp")
        self.alert = self.application.alert
        self.addCondensedAudioInProgressMessage = self.application.addCondensedAudioInProgressMessage
        self.removeCondensedAudioInProgressMessage  = self.application.removeCondensedAudioInProgressMessage
        suffix = ''     
        if isWin:   
            suffix = '.exe' 
        self.ffmpeg = join(self.addonDirectory, 'user_files', 'ffmpeg', 'ffmpeg' + suffix)

    def checkVersion(self):
        version = int(self.get_body_argument("version", default=False))
        return self.application.checkVersion(version)

    def getConfig(self):
        return self.mw.addonManager.getConfig(__name__)


class ImportHandler(MigakuHTTPHandler):

    def get(self):
        self.finish("ImportHandler")

    def ffmpegExists(self):
        if exists(self.ffmpeg):
            return True
        return False

    def removeTempFiles(self):
        tmpdir = self.tempDirectory
        filelist = [ f for f in os.listdir(tmpdir)]
        for f in filelist:
            path = os.path.join(tmpdir, f)
            try:
                os.remove(path)
            except:
                innerDirFiles = [ df for df in os.listdir(path)]
                for df in innerDirFiles:
                    innerPath = os.path.join(path, df)
                    os.remove(innerPath)
                os.rmdir(path)

    def condenseAudioUsingFFMPEG(self, filename, timestamp, config):
        print("FFMPEG REACHED")
        wavDir = join(self.tempDirectory, timestamp)
        if exists(wavDir):
            config = self.getConfig()
            mp3dir = config.get('condensedAudioDirectory', False)
            wavs = [ f for f in os.listdir(wavDir)]
            wavs.sort()
            wavListFilePath = join(wavDir, "list.txt")
            wavListFile = open(wavListFilePath,"w+")
            print(filename)
            filename = self.cleanFilename(filename+ "\n") + "-condensed.mp3"
            mp3path = join(mp3dir, filename)
            print(wavs)
            for wav in wavs:
                wavListFile.write("file '{}'\n".format(join(wavDir, wav)))
            wavListFile.close()
            import subprocess
            subprocess.call([self.ffmpeg, '-y', '-f', 'concat', '-safe', '0', '-i', wavListFilePath, '-write_xing', '0', mp3path])
            self.removeTempFiles()
            if not config.get('disableCondensed', False):
                self.alert( "A Condensed Audio File has been generated.\n\n The file: " + filename + "\nhas been created in dir: " + mp3dir)

    def cleanFilename(self, filename):
        return re.sub(r"[\n:'\":/\|?*><!]","", filename).strip()

    def post(self):
        if self.checkVersion():
            config = self.getConfig()
            previousBulkTimeStamp = self.application.settings.get('previousBulkTimeStamp')
            if self.parseBoolean(self.get_body_argument("pageRefreshCancelBulkMediaExporting", default=False)):
                self.mw.hkThread.handlePageRefreshDuringBulkMediaImport()
                self.removeCondensedAudioInProgressMessage()
                self.finish("Cancelled through browser.")
                return
            bulk = self.parseBoolean(self.get_body_argument("bulk", default=False))
            bulkExportWasCancelled = self.parseBoolean(self.get_body_argument("bulkExportWasCancelled", default=False))
            timestamp = self.get_body_argument("timestamp", default=0)
            if bulkExportWasCancelled:
                if self.mw.MigakuBulkMediaExportWasCancelled and previousBulkTimeStamp == timestamp:
                    self.finish("yes")
                else:
                    self.finish("no")
                return
            requestType = self.get_body_argument("type", default=False)
            if requestType == 'finishedRecordingCondensedAudio':
                filename = self.get_body_argument('filename', default="audio");
                self.condenseAudioUsingFFMPEG(filename, timestamp, config)
                self.removeCondensedAudioInProgressMessage()
                return

            if bulk and requestType == "text":
                    cards = json.loads(self.get_body_argument("cards", default="[]"))
                    self.mw.hkThread.handleBulkTextExport(cards)
                    self.finish("Bulk Text Export")
                    return

            else:
                if self.mw.MigakuBulkMediaExportWasCancelled and previousBulkTimeStamp == timestamp:
                    self.removeCondensedAudioInProgressMessage()
                    self.finish("Exporting was cancelled.")
                    return
                if previousBulkTimeStamp != timestamp or not bulk:
                    self.application.settings["previousBulkTimeStamp"] = timestamp
                    self.removeCondensedAudioInProgressMessage()
                    self.mw.MigakuBulkMediaExportWasCancelled = False
                condensedAudio = self.parseBoolean(self.get_body_argument("condensedAudio", default=False))  
                total = int(self.get_body_argument("totalToRecord", default=1))     
                print("TOTAL")
                print(total)       
                if condensedAudio:
                    mp3dir = config.get('condensedAudioDirectory', False)
                    if not mp3dir:
                        self.alert("You must specify a Condensed Audio Save Location.\n\nYou can do this by:\n1. Navigating to Migaku->Dictionary Settings in Anki's menu bar.\n2. Clicking \"Choose Directory\" for the \"Condensed Audio Save Location\"  in the bottom right of the settings window.")
                        self.mw.MigakuBulkMediaExportWasCancelled = True
                        self.removeCondensedAudioInProgressMessage()
                        self.finish("Save location not set.")
                    elif self.ffmpegExists():
                        self.handleAudioFileInRequestAndReturnFilename(self.copyFileToCondensedAudioDir)
                        print("File saved in temp dir")
                        self.addCondensedAudioInProgressMessage()
                        self.finish("Exporting Condensed Audio")
                    else:
                        self.alert("The FFMPEG media encoder must be installed in order to export condensedAudio.\n\nIn order to install FFMPEG please enable MP3 Conversion in the Dictionary Settings window and click \"Apply\".\nFFMPEG will then be downloaded and installed automatically.")
                        self.mw.MigakuBulkMediaExportWasCancelled = True
                        self.removeCondensedAudioInProgressMessage()
                        self.finish("FFMPEG not installed.")
                    return
                else: 
                    audioFileName = self.handleAudioFileInRequestAndReturnFilename(self.copyFileToTempDir)
                    primary = self.get_body_argument("primary", default="")
                    secondary = self.get_body_argument("secondary", default="")
                    unknownWords = json.loads(self.get_body_argument("unknown", default="[]"))
                    imageFileName = False
                    if "image" in self.request.files:
                        imageFile = self.request.files['image'][0]
                        imageFileName = imageFile["filename"]
                        self.copyFileToTempDir(imageFile, imageFileName)
                    cardToExport ={
                        "primary" : primary,
                        "secondary" : secondary,
                        "unknownWords" : unknownWords,
                        "bulk" : bulk,
                        "audio" : audioFileName,
                        "image" : imageFileName,
                        "total" : total,
                    }
                    self.mw.hkThread.handleExtensionCardExport(cardToExport)
                    self.finish("Card Exported")
                    return
        self.finish("Invalid Request")
                
    def handleAudioFileInRequestAndReturnFilename(self, copyFileFunction):
        if "audio" in self.request.files:
            audioFile = self.request.files['audio'][0]
            audioFileName = audioFile["filename"]
            copyFileFunction(audioFile, audioFileName)
            return audioFileName
        else:
            return False
            
    def parseBoolean(self, bulk):
        if bulk == "false" or  bulk is False :
            return False 
        return True

    def copyFileToTempDir(self, file, filename):
        filePath = join(self.tempDirectory, filename)
        fh = open(filePath, 'wb')
        fh.write(file['body'])

    def copyFileToCondensedAudioDir(self, file, filename):
        directoryPath = join(self.tempDirectory, self.application.settings.get('previousBulkTimeStamp'))
        if not exists(directoryPath):
            os.mkdir(directoryPath)
        filePath = join(directoryPath, filename)
        fh = open(filePath, 'wb')
        fh.write(file['body'])

class LearningStatusHandler(MigakuHTTPHandler):

    def get(self):
        self.finish("LearningStatusHandler")
   
    def post(self):
        if self.checkVersion():
            fetchModels = self.get_body_argument("fetchModelsAndTemplates", default=False)
            if fetchModels is not False:
                self.finish(self.fetchModelsAndTemplates())
                return
            start = self.get_body_argument("start", default=False)
            if start is not False:
                incrementor = self.get_body_argument("incrementor", default=False)
                self.finish(self.getCards(start, incrementor))
                return
        self.finish("Invalid Request")

    def getFieldOrdinateDictionary(self, fieldEntries):
        fieldOrdinates = {};
        for field in fieldEntries:
          fieldOrdinates[field["name"]] = field["ord"];
        return fieldOrdinates;


    def getFields(self, templateSide, fieldOrdinatesDict) :
        pattern = r"{{([^#^\/][^}]*?)}}";
        matches = re.findall(pattern, templateSide);
        fields = self.getCleanedFieldArray(matches);
        fieldsOrdinates = self.getFieldOrdinates(fields, fieldOrdinatesDict);
        return fieldsOrdinates;


    def getFieldOrdinates(self, fields, fieldOrdinates):
        ordinates = [];
        for field in fields:
            if field in fieldOrdinates:
                ordinates.append(fieldOrdinates[field]);
        return ordinates;
  

    def getCleanedFieldArray(self, fields):
        noDupes = [];
        for field in fields:
          fieldName = self.getCleanedFieldName(field).strip();
          if not fieldName in noDupes and fieldName not in ["FrontSide", "Tags", "Subdeck", "Type", "Deck", "Card"]:
                noDupes.append(fieldName);
        return noDupes;

    def getCleanedFieldName(self, field):
        if ":" in field:
          split = field.split(":");
          return split[len(split) - 1];
        return field;
  

    def fetchModelsAndTemplates(self):
        modelData = {}
        models = self.mw.col.models.all()
        for idx, model in enumerate(models):
            mid = str(model["id"]);
            templates = model["tmpls"];
            templateArray = [];
            fieldOrdinates = self.getFieldOrdinateDictionary(model["flds"]);
            for template in templates:
              frontFields = self.getFields(template["qfmt"], fieldOrdinates);
              name = template["name"];
              backFields = self.getFields(template["afmt"], fieldOrdinates);
              
              templateArray.append({
                "frontFields": frontFields,
                "backFields": backFields,
                "name": name,
              });
            if mid not in modelData:
              modelData[mid] = {
                "templates": templateArray,
                "fields": fieldOrdinates,
                "name": model["name"],
              };
        return json.dumps(modelData)


    def getCards(self, start, incrementor):
        cards = self.mw.col.getNextBatchOfCards(start, incrementor)
        bracketPattern = "\[[^]\n]*?\]"
        for card in cards:
            card[1] = re.sub(bracketPattern, "", card[1])
        return json.dumps(cards)

class SearchHandler(MigakuHTTPHandler):

    def get(self):
        self.finish("SearchHandler")
   
    def post(self):
        if self.checkVersion():
            terms = self.get_body_argument("terms", default=False)
            if terms is not False:
                self.mw.hkThread.handleExtensionSearch(json.loads(terms))  
                self.finish("Searched")
                return
        self.finish("Invalid Request")

class MigakuHTTPServer(tornado.web.Application):

    PROTOCOL_VERSION = 2

    def __init__(self, thread, mw):
        self.mw = mw
        self.previousBulkTimeStamp = 0
        self.thread = thread
        handlers = [ (r"/import", ImportHandler), 
        (r"/learning-statuses", LearningStatusHandler),
        (r"/search", SearchHandler), 
        ]
        settings = {'mw' : mw}
        super().__init__(handlers, **settings)

    def run(self, port=12345):
        self.listen(port)
        tornado.ioloop.IOLoop.instance().start()

    def alert(self, message):
        self.thread.alert(message)

    def addCondensedAudioInProgressMessage(self):
        self.thread.addCondensedAudioInProgressMessage()

    def removeCondensedAudioInProgressMessage(self):
        self.thread.removeCondensedAudioInProgressMessage()

    def checkVersion(self, version):
        if version is False or version < self.PROTOCOL_VERSION:
            self.alert("Your Migaku Dictionary Version is newer than and incompatible with your Immerse with Migaku Browser Extension installation. Please ensure you are using the latest version of the add-on and extension to resolve this issue.")
            return False
        elif version > self.PROTOCOL_VERSION:
            self.alert("Your Immerse with Migaku Browser Extension Version is newer than and incompatible with this Migaku Dictionary installation. Please ensure you are using the latest version of the add-on and extension to resolve this issue.")
            return False
        return True

class MigakuServerThread(QThread):

    alertUser = pyqtSignal(str)
    exportingCondensed = pyqtSignal()
    notExportingCondensed = pyqtSignal()

    def __init__(self, mw):
        self.mw = mw
        QThread.__init__(self)
        self.server = MigakuHTTPServer(self, mw)
        self.start()

    def run(self):
        asyncio.set_event_loop(asyncio.new_event_loop())
        self.server.run()

    def alert(self, message):
        self.alertUser.emit(message)


    def addCondensedAudioInProgressMessage(self):
        self.exportingCondensed.emit()

    def removeCondensedAudioInProgressMessage(self):
        self.notExportingCondensed.emit()




def addCondensedAudioInProgressMessage():
    title = mw.windowTitle()
    msg = " (Condensed Audio Exporting in Progress)"
    if msg not in title:
        mw.setWindowTitle(title + msg)

def removeCondensedAudioInProgressMessage():
    title = mw.windowTitle()
    msg = " (Condensed Audio Exporting in Progress)"
    if msg in title:
        mw.setWindowTitle(title.replace(msg, ""))



serverThread = MigakuServerThread(mw)
serverThread.alertUser.connect(miInfo)
serverThread.exportingCondensed.connect(addCondensedAudioInProgressMessage)
serverThread.notExportingCondensed.connect(removeCondensedAudioInProgressMessage)
