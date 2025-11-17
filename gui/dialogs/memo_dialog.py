# raizqa/gui/dialogs/memo_dialog.py

from pathlib import Path
import sys
from spellchecker import SpellChecker
from PySide6.QtGui import QTextCharFormat, QSyntaxHighlighter, QTextCursor
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QVBoxLayout, QTextEdit, QDialogButtonBox, QMenu

# -------------------- FUNCION PARA MEMOS --------------------
def get_memos_dir():
    """Devuelve la ruta de la carpeta memos, válida en Python o .exe"""
    if getattr(sys, "frozen", False):
        base_path = Path(sys.executable).parent
    else:
        base_path = Path(__file__).parent
    memos_path = base_path / "memos"
    memos_path.mkdir(exist_ok=True)
    return memos_path


# -------------------- DIALOGO DE MEMOS --------------------
class SpellHighlighter(QSyntaxHighlighter):
    def __init__(self, parent=None):
        super().__init__(parent)
        try:
            self.spell_es = SpellChecker(language='es')
            self.spell_en = SpellChecker(language='en')
        except Exception as exc:
            print(f"ADVERTENCIA: corrector ortográfico no disponible ({exc})")
            self.spell_es = None
            self.spell_en = None
        self.error_format = QTextCharFormat()
        self.error_format.setUnderlineColor(Qt.red)
        self.error_format.setUnderlineStyle(QTextCharFormat.SpellCheckUnderline)
        self.misspelled_words = {}  # {pos: palabra}

    def highlightBlock(self, text):
        if not self.spell_es or not self.spell_en:
            return
        self.misspelled_words.clear()
        words = text.split()
        for word in words:
            clean = ''.join([c for c in word if c.isalpha()])
            if not clean:
                continue
            if (clean.lower() not in self.spell_es and
                clean.lower() not in self.spell_en):
                start = text.find(word)
                if start >= 0:
                    self.setFormat(start, len(word), self.error_format)
                    self.misspelled_words[start] = clean


class MemoDialog(QDialog):
    def __init__(self, code_label, memo_text=""):
        super().__init__()
        self.setWindowTitle(f"Memo para '{code_label}'")
        self.resize(400, 300)

        layout = QVBoxLayout()
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

        self.setLayout(layout)

    def show_context_menu(self, pos):
        cursor = self.text_edit.cursorForPosition(pos)
        cursor.select(QTextCursor.WordUnderCursor)
        selected_word = cursor.selectedText().strip()

        if not selected_word:
            return self.text_edit.createStandardContextMenu().exec(self.text_edit.mapToGlobal(pos))

        if not self.highlighter.spell_es or not self.highlighter.spell_en:
            return self.text_edit.createStandardContextMenu().exec(self.text_edit.mapToGlobal(pos))

        if (selected_word.lower() in self.highlighter.spell_es or
            selected_word.lower() in self.highlighter.spell_en):
            return self.text_edit.createStandardContextMenu().exec(self.text_edit.mapToGlobal(pos))

        suggestions = (
            self.highlighter.spell_es.candidates(selected_word)
            or self.highlighter.spell_en.candidates(selected_word)
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
