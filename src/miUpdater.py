from aqt import mw
from aqt import addons
from . import dictdb
from anki.hooks import  wrap, addHook
from .miutils import miInfo
import time
from anki.httpclient import HttpClient

addonId = 1655992655
dledIds = []


def shutdownDB( parent, mgr, ids, on_done, client):
    global dledIds 
    dledIds = ids
    if addonId in ids and hasattr(mw, 'miDictDB'):
        miInfo('The MIA Dictionary database will be diconnected so that the update may proceed. The add-on will not function properly until Anki is restarted after the update.')
        mw.miDictDB.closeConnection()
        mw.miDictDB = False
        if hasattr(mw.miaDictionary, 'db'):
            mw.miaDictionary.db.closeConnection()
            mw.miaDictionary.db = False
        time.sleep(2)
        
        

def restartDB(*args):
    if addonId in dledIds and hasattr(mw, 'miDictDB'):
        mw.miDictDB =  dictdb.DictDB()
        if hasattr(mw.miaDictionary, 'db'):
            mw.miaDictionary.db = dictdb.DictDB()
        miInfo('The MIA Dictionary has been updated, please restart Anki to start using the new version now!')

def wrapOnDone(self, log):
    self.mgr.mw.progress.timer(50, lambda: restartDB(), False)

addons.download_addons = wrap(addons.download_addons, shutdownDB, 'before')
addons.DownloaderInstaller._download_done = wrap(addons.DownloaderInstaller._download_done, wrapOnDone)


