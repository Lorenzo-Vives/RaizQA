from PySide6.QtWidgets import QDialog, QVBoxLayout, QTextEdit, QDialogButtonBox, QMenu
from PySide6.QtGui import QTextCharFormat, QSyntaxHighlighter, QTextCursor
from PySide6.QtCore import Qt
from spellchecker import SpellChecker

class SpellHighlighter(QSyntaxHighlighter):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.spell_es = SpellChecker(language='es')
        self.spell_en = SpellChecker(language='en')
        self.error_format = QTextCharFormat()
        self.error_format.setUnderlineColor(Qt.red)
        self.error_format.setUnderlineStyle(QTextCharFormat.SpellCheckUnderline)

    def highlightBlock(self, text):
        for word in text.split():
            clean = ''.join([c for c in word if c.isalpha()])
            if clean and (clean.lower() not in self.spell_es and clean.lower() not in self.spell_en):
                start = text.find(word)
                if start >= 0:
                    self.setFormat(start, len(word), self.error_format)

class MemoDialog(QDialog):
    def __init__(self, code_label, memo_text=""):
        super().__init__()
        self.setWindowTitle(f"Memo para '{code_label}'")
        self.resize(400, 300)

        layout = QVBoxLayout(self)
        self.text_edit = QTextEdit()
        self.text_edit.setText(memo_text)
        self.highlighter = SpellHighlighter(self.text_edit.document())
        self.text_edit.setContextMenuPolicy(Qt.CustomContextMenu)
        self.text_edit.customContextMenuRequested.connect(self.show_context_menu)
        layout.addWidget(self.text_edit)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def show_context_menu(self, pos):
        cursor = self.text_edit.cursorForPosition(pos)
        cursor.select(QTextCursor.WordUnderCursor)
        word = cursor.selectedText().strip()
        if not word:
            return self.text_edit.createStandardContextMenu().exec(self.text_edit.mapToGlobal(pos))
        if (word.lower() in self.highlighter.spell_es or word.lower() in self.highlighter.spell_en):
            return self.text_edit.createStandardContextMenu().exec(self.text_edit.mapToGlobal(pos))
        suggestions = (
            self.highlighter.spell_es.candidates(word)
            or self.highlighter.spell_en.candidates(word)
        )
        menu = QMenu(self)
        if suggestions:
            for s in list(suggestions)[:5]:
                action = menu.addAction(s)
                action.triggered.connect(lambda checked=False, sug=s: self.replace_word(cursor, sug))
        else:
            menu.addAction("(Sin sugerencias)").setEnabled(False)
        menu.addSeparator()
        menu.addAction("Ignorar palabra")
        menu.exec(self.text_edit.mapToGlobal(pos))

    def replace_word(self, cursor, suggestion):
        cursor.beginEditBlock()
        cursor.removeSelectedText()
        cursor.insertText(suggestion)
        cursor.endEditBlock()

    def get_memo(self):
        return self.text_edit.toPlainText()
