# -*- coding: utf-8 -*-
# 

import aqt
from aqt.qt import *
from os.path import dirname, join
from aqt.webview import AnkiWebView


addon_path = dirname(__file__)

def miInfo(text, parent=False, level = 'msg', day = True):
    if level == 'wrn':
        title = "Migaku Dictionary Warning"
    elif level == 'not':
        title = "Migaku Dictionary Notice"
    elif level == 'err':
        title = "Migaku Dictionary Error"
    else:
        title = "Migaku Dictionary"
    if parent is False:
        parent = aqt.mw.app.activeWindow() or aqt.mw
    icon = QIcon(join(addon_path, 'icons', 'migaku.png'))
    mb = QMessageBox(parent)
    if not day:
        mb.setStyleSheet(" QMessageBox {background-color: #272828;}")
    mb.setText(text)
    mb.setWindowIcon(icon)
    mb.setWindowTitle(title)
    b = mb.addButton(QMessageBox.Ok)
    b.setFixedSize(100, 30)
    b.setDefault(True)

    return mb.exec_()

def miAsk(text, parent=None, day=True, customText = False):

    msg = QMessageBox(parent)
    msg.setWindowTitle("Migaku Dictionary")
    msg.setText(text)
    icon = QIcon(join(addon_path, 'icons', 'migaku.png'))
    b = msg.addButton(QMessageBox.Yes)
    
    b.setFixedSize(100, 30)
    b.setDefault(True)
    c = msg.addButton(QMessageBox.No)
    c.setFixedSize(100, 30)
    if customText:
        b.setText(customText[0])
        c.setText(customText[1])
        b.setFixedSize(120, 40)
        c.setFixedSize(120, 40)

    
    if not day:
        msg.setStyleSheet(" QMessageBox {background-color: #272828;}")
    msg.setWindowIcon(icon)
    msg.exec_()
    if msg.clickedButton() == b:
        return True
    else:
        return False
