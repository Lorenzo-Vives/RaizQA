import os
import json
import shutil
import time
import logging

logger = logging.getLogger(__name__)




# ----------------------------------------------------------------------
# Persistencia
# ----------------------------------------------------------------------
class StorageManager:
    """
    Administra la persistencia atómica de datos con respaldo (.bak).
    """

    def __init__(self, state_filename: str = "project_data.json"):
        self.state_filename = state_filename
        
    def save(self, project_path: str, state: dict):
        state_path = os.path.join(project_path, self.state_filename)
        bak_path = state_path + ".bak"
        
        tmp_path = os.path.join(
            project_path, f"{self.state_filename}.{os.getpid()}.{time.time_ns()}.tmp"
        )

        try:
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=4, ensure_ascii=False)

            if os.path.exists(state_path):
                shutil.copy2(state_path, bak_path)

            os.replace(tmp_path, state_path)
            return True

        except OSError as e:
            logger.error(f"Error al guardar el estado del proyecto en {state_path}: {e}")
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass
            return False

            
            
    def load(self, project_path: str) -> dict:
        """
        Carga el estado persistido. Si el archivo principal no existe
        o está corrupto, intenta recuperarlo desde el respaldo (.bak).
        Si ambos fallan, retorna un estado vacío.
        """
        state_path = os.path.join(project_path, self.state_filename)
        bak_path = state_path + ".bak"

        for path in (state_path, bak_path):
            if not os.path.exists(path):
                continue
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (OSError, json.JSONDecodeError) as e:
                logger.warning(f"No se pudo leer {path}: {e}")
                continue
            
        return {}
