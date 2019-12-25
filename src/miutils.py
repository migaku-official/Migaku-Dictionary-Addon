# -*- coding: utf-8 -*-
# 

import aqt
from aqt.qt import *
from os.path import dirname, join

addon_path = dirname(__file__)

def miInfo(text, parent=False, level = 'msg', day = True):
    if level == 'wrn':
        title = "Dictionary Warning"
    elif level == 'not':
        title = "Dictionary Notice"
    elif level == 'err':
        title = "Dictionary Error"
    else:
        title = "Dictionary"
    if parent is False:
        parent = aqt.mw.app.activeWindow() or aqt.mw
    icon = QIcon(join(addon_path, 'icons', 'mia.png'))
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


def miAsk(text, parent=None, day=True):

    msg = QMessageBox(parent)
    # msg.setPalette(nightPalette)
    msg.setWindowTitle("Dictionary")
    msg.setText(text)
    icon = QIcon(join(addon_path, 'icons', 'mia.png'))
    # msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
    b = msg.addButton(QMessageBox.Yes)
    b.setFixedSize(100, 30)
    b.setDefault(True)
    c = msg.addButton(QMessageBox.No)
    c.setFixedSize(100, 30)
    if not day:
        msg.setStyleSheet(" QMessageBox {background-color: #272828;}")
    msg.setWindowIcon(icon)
    msg.exec_()
    if msg.clickedButton() == b:
        return True
    else:
        return False


# msg = QDialog(parent)

    # msg.setWindowTitle("Dictionary")
    # label = QLabel(msg)
    # label.setText(text)
    # icon = QIcon(join(addon_path, 'icons', 'mia.png'))
    # # msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
    # msg.setStyleSheet(" QDialog {background-color: #272828;}")
    # msg.setWindowIcon(icon)
    # msg.exec_()
    # msg.accept()
