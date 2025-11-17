from pathlib import Path
import sys

def get_memos_dir():
    """Devuelve la ruta de la carpeta memos (compatible con exe o script)."""
    base_path = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).parent
    memos_path = base_path / ".." / "memos" / "memos"
    memos_path = memos_path.resolve()
    memos_path.mkdir(parents=True, exist_ok=True)
    return memos_path
