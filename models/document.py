class Document:
    def __init__(self, title, content):
        self.title = title
        self.content = content
        self.codes = []

    def get_paragraphs(self):
        """Divide el texto en párrafos para codificar más fácilmente."""
        return [p.strip() for p in self.content.split("\n") if p.strip()]

    def apply_code(self, text_fragment, code_label):
        """Aplica un código a un fragmento de texto, permitiendo varios códigos por párrafo."""
        # Buscar si ya existe el fragmento codificado
        for c in self.codes:
            if c["fragment"] == text_fragment:
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
        """Muestra los fragmentos codificados."""
        for c in self.codes:
            codes = c["code"]
            if isinstance(codes, list):
                codes = ", ".join(codes)
            print(f"[{codes}] {c['fragment']}")