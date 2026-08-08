from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass(slots=True)
class Fragment:
    type: str = "text"
    start: Optional[int] = None
    end: Optional[int] = None
    rect: Optional[list] = None
    image_size: Optional[list] = None
    note: Optional[str] = None

    def to_dict(self) -> dict:
        if self.type == "image":
            return {
                "type": "image",
                "rect": self.rect,
                "image_size": self.image_size,
                "note": self.note,
            }
        return {"type": "text", "start": self.start, "end": self.end}

    @classmethod
    def from_dict(cls, data) -> "Fragment":
        # Formato legacy:
        if isinstance(data, list) and len(data) >= 2:
            return cls(type="text", start=int(data[0]), end=int(data[1]))

        if isinstance(data, dict):
            frag_type = data.get("type", "text")
            if frag_type == "image":
                return cls(
                    type="image",
                    rect=data.get("rect"),
                    image_size=data.get("image_size"),
                    note=data.get("note"),
                )
            return cls(
                type="text",
                start=int(data.get("start", 0)),
                end=int(data.get("end", 0)),
            )

        #Valores por defecto si el formato es desconocido
        logger.warning(f"Formato de fragmento desconocido: {type(data)} - {data}")
        return cls(type="text", start=0, end=0)


@dataclass(slots=True)
class Code:
    """
    Modelar un código de análisis, su jerarquía y los fragmentos asociados.
    """
    hexcolor: str = "#5d9bd3"
    memo: str = ""
    fragments: Dict[str, List[Fragment]] = field(default_factory=dict)
    parent: Optional[str] = None
    children: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "hexcolor": self.hexcolor,
            "memo": self.memo,
            "fragments": {
                doc: [f.to_dict() for f in frags]
                for doc, frags in self.fragments.items()
            },
            "parent": self.parent,
            "children": list(self.children),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Code":
        fragments = {}
        for doc, frags in data.get("fragments", {}).items():
            fragments[doc] = [Fragment.from_dict(f) for f in frags]
        return cls(
            hexcolor=data.get("hexcolor", "#5d9bd3"),
            memo=data.get("memo", ""),
            fragments=fragments,
            parent=data.get("parent"),
            children=data.get("children", []),
        )


@dataclass(slots=True)
class Theme:
    """
    Modelar un tema que puede agrupar múltiples códigos.
    """
    memo: str = ""
    codes: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"memo": self.memo, "codes": list(self.codes)}

    @classmethod
    def from_dict(cls, data: dict) -> "Theme":
        return cls(
            memo=data.get("memo", ""),
            codes=data.get("codes", []),
        )
