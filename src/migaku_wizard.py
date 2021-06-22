from aqt.qt import *


class MiWizardPage(QWidget):

    def __init__(self, parent=None):
        super(MiWizardPage, self).__init__(parent)

        self.wizard = None
        self.title = None
        self.subtitle = None
        self.pixmap = None

        self.back_text = '< Back'
        self.back_enabled = True
        self.back_visible = True

        self.next_text = 'Next >'
        self.next_enabled = True
        self.next_visible = True
        
        self.cancel_text = 'Cancel'
        self.cancel_enabled = True
        self.cancel_visible = True

    def on_show(self, is_next, is_back):
        pass

    def on_hide(self, is_next, is_back):
        pass

    def on_back(self):
        return True

    def on_next(self):
        return True

    def on_cancel(self):
        return True

    def refresh_wizard_states(self):
        if self.wizard:
            self.wizard.refresh_states()


class MiWizard(QDialog):
    
    def __init__(self, parent=None):
        super(MiWizard, self).__init__(parent)

        self._current_page = None
        self._page_back = {}
        self._page_next = {}

        lyt = QVBoxLayout()
        lyt.setContentsMargins(0, 0, 0, 0)
        self.setLayout(lyt)

        page_frame = QFrame()
        page_frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        page_frame.setBackgroundRole(QPalette.Base)
        page_frame.setAutoFillBackground(True)
        lyt.addWidget(page_frame)

        page_hlyt = QHBoxLayout(page_frame)

        pixmap_lyt = QVBoxLayout()
        page_hlyt.addLayout(pixmap_lyt)

        self._pixmap_lbl = QLabel()
        self._pixmap_lbl.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        pixmap_lyt.addWidget(self._pixmap_lbl)
        pixmap_lyt.addStretch()        

        page_vlyt = QVBoxLayout()
        page_hlyt.addLayout(page_vlyt)

        self._header_lbl = QLabel()
        page_vlyt.addWidget(self._header_lbl)

        self._pages_lyt = QHBoxLayout()
        self._pages_lyt.setSizeConstraint(QLayout.SetMaximumSize)
        page_vlyt.addLayout(self._pages_lyt)

        btn_lyt = QHBoxLayout()
        lyt.addLayout(btn_lyt)
        style = self.style()
        margins = (style.pixelMetric(QStyle.PM_LayoutLeftMargin), style.pixelMetric(QStyle.PM_LayoutTopMargin),
                   style.pixelMetric(QStyle.PM_LayoutRightMargin), style.pixelMetric(QStyle.PM_LayoutBottomMargin))
        btn_lyt.setContentsMargins(*margins)

        btn_lyt.addStretch()

        self._btn_back = QPushButton()
        self._btn_back.setFocusPolicy(Qt.NoFocus)
        self._btn_back.clicked.connect(self.back)
        btn_lyt.addWidget(self._btn_back)

        self._btn_next = QPushButton()
        self._btn_next.setFocusPolicy(Qt.NoFocus)
        self._btn_next.clicked.connect(self.next)
        btn_lyt.addWidget(self._btn_next)

        self._btn_cancel = QPushButton()
        self._btn_cancel.setFocusPolicy(Qt.NoFocus)
        self._btn_cancel.clicked.connect(self.cancel)
        btn_lyt.addWidget(self._btn_cancel)


    def add_page(self, page, back_page=None, next_page=None, back_populate=True):
        page.wizard = self
        page.hide()
        page_lyt = page.layout()
        if page_lyt:
            page_lyt.setContentsMargins(0, 0, 0, 0)
        page.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._pages_lyt.addWidget(page)
        self.set_page_back(page, back_page)
        self.set_page_next(page, next_page)

        if self._current_page is None:
            self.set_current_page(page, is_next=True)

        return page


    def set_page_back(self, page, back_page, back_populate=True):
        self._page_back[page] = back_page
        if back_populate and back_page:
            self.set_page_next(back_page, page, back_populate=False)


    def set_page_next(self, page, next_page, back_populate=True):
        self._page_next[page] = next_page
        if back_populate and next_page:
            self.set_page_back(next_page, page, back_populate=False)


    def set_current_page(self, page, is_next=False, is_back=False):
        if self._current_page:
            self._current_page.on_hide(is_next, is_back)
            self._current_page.hide()
        self._current_page = page

        page.on_show(is_next, is_back)

        self.refresh_states()

        page.show()


    def back(self):
        if self._current_page:
            if not self._current_page.on_back():
                return

        back_page = self._page_back.get(self._current_page)
        if back_page:
            self.set_current_page(back_page, is_back=True)


    def next(self):
        if self._current_page:
            if not self._current_page.on_next():
                return

        next_page = self._page_next.get(self._current_page)
        if next_page:
            self.set_current_page(next_page, is_next=True)
        else:
            self.accept()


    def cancel(self):
        if self._current_page:
            if not self._current_page.on_cancel():
                return

        if not self.on_cancel():
            return

        self.reject()


    def on_cancel(self):
        return True


    def refresh_states(self):
        if self._current_page:
            header_text = ''

            title = self._current_page.title
            if title:
                header_text += '<h2>%s</h2>' % title

            subtitle = self._current_page.subtitle
            if subtitle:
                header_text += '<h4>%s</h4>' % subtitle

            if header_text:
                self._header_lbl.setText(header_text)
                self._header_lbl.setVisible(True)
            else:
                self._header_lbl.clear()
                self._header_lbl.setVisible(False)

            pixmap = self._current_page.pixmap
            if pixmap:
                self._pixmap_lbl.setPixmap(pixmap)
            else:
                self._pixmap_lbl.clear()
            self._pixmap_lbl.setVisible(bool(pixmap))

            self._btn_back.setText(self._current_page.back_text)
            self._btn_back.setEnabled(self._current_page.back_enabled)
            self._btn_back.setVisible(self._current_page.back_visible)
            self._btn_next.setText(self._current_page.next_text)
            self._btn_next.setEnabled(self._current_page.next_enabled)
            self._btn_next.setVisible(self._current_page.next_visible)
            self._btn_cancel.setText(self._current_page.cancel_text)
            self._btn_cancel.setEnabled(self._current_page.cancel_enabled)
            self._btn_cancel.setVisible(self._current_page.cancel_visible)


    def closeEvent(self, e):
        self.cancel()
        e.ignore()
