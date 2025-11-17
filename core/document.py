# core/document.py
class Document:
    def __init__(self, title, content):
        """Representa un documento cargado en el proyecto."""
        self.title = title
        self.content = content
        self.codes = []

    def get_paragraphs(self):
        """Divide el texto en párrafos para facilitar la codificación."""
        return [p.strip() for p in self.content.split("\n") if p.strip()]

    def apply_code(self, text_fragment, code_label):
        """Aplica un código a un fragmento de texto. Permite múltiples códigos por fragmento."""
        for c in self.codes:
            if c["fragment"] == text_fragment:
                # Si el fragmento ya existe, agregamos el nuevo código
                if isinstance(c["code"], list):
                    if code_label not in c["code"]:
                        c["code"].append(code_label)
                else:
                    if c["code"] != code_label:
                        c["code"] = [c["code"], code_label]
                return
        # Si no existe, lo añadimos
        self.codes.append({"fragment": text_fragment, "code": code_label})

    def show_coded_segments(self):
        """Muestra por consola los fragmentos codificados."""
        for c in self.codes:
            codes = c["code"]
            if isinstance(codes, list):
                codes = ", ".join(codes)
            print(f"[{codes}] {c['fragment']}")
