import os
import json
import uuid
import glob

class PointerManager:
    """
    Gestor de persistencia atómica mediante sistema de centinelas (Pointers).
    Evita la corrupción de archivos JSON escribiendo siempre en archivos nuevos
    y luego actualizando un puntero que indica cuál es la versión más reciente válida.
    """
    
    @staticmethod
    def atomic_save(base_dir, prefix, data, max_backups=3):
        """
        Guarda `data` (dict) en un nuevo archivo `{prefix}_{uuid}.json`
        y actualiza el archivo puntero `{prefix}_pointer.txt`.
        """
        os.makedirs(base_dir, exist_ok=True)
        
        # 1. Crear nuevo archivo con UUID
        new_id = uuid.uuid4().hex[:8]
        new_filename = f"{prefix}_{new_id}.json"
        new_filepath = os.path.join(base_dir, new_filename)
        
        with open(new_filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
            
        # 2. Actualizar el puntero atómicamente
        pointer_path = os.path.join(base_dir, f"{prefix}_pointer.txt")
        tmp_pointer = pointer_path + ".tmp"
        with open(tmp_pointer, "w", encoding="utf-8") as f:
            f.write(new_filename)
        os.replace(tmp_pointer, pointer_path)
        
        # 3. Limpiar respaldos viejos
        PointerManager._cleanup_backups(base_dir, prefix, max_backups, current_valid=new_filename)
        
    @staticmethod
    def atomic_load(base_dir, prefix, default=None):
        """
        Lee el archivo puntero, y carga el JSON al que apunta.
        Si no existe o falla, busca respaldos atómicos o archivos legacy.
        """
        pointer_path = os.path.join(base_dir, f"{prefix}_pointer.txt")
        if os.path.exists(pointer_path):
            with open(pointer_path, "r", encoding="utf-8") as f:
                target_filename = f.read().strip()
            
            target_filepath = os.path.join(base_dir, target_filename)
            if os.path.exists(target_filepath):
                try:
                    with open(target_filepath, "r", encoding="utf-8") as f:
                        return json.load(f)
                except json.JSONDecodeError:
                    pass # Corrupto, seguir intentando con respaldos
                    
        # Buscar el respaldo más reciente que no esté corrupto
        pattern = os.path.join(base_dir, f"{prefix}_*.json")
        files = glob.glob(pattern)
        files.sort(key=os.path.getmtime, reverse=True)
        
        for f in files:
            try:
                with open(f, "r", encoding="utf-8") as file:
                    return json.load(file)
            except json.JSONDecodeError:
                continue

        # Retrocompatibilidad (Legacy fallback)
        legacy_path = os.path.join(base_dir, f"{prefix}.json")
        if os.path.exists(legacy_path):
            try:
                with open(legacy_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except json.JSONDecodeError:
                pass
                
        return default if default is not None else {}
        
    @staticmethod
    def _cleanup_backups(base_dir, prefix, max_backups, current_valid):
        """Elimina versiones antiguas superando el máximo, ignorando la válida."""
        pattern = os.path.join(base_dir, f"{prefix}_*.json")
        files = glob.glob(pattern)
        files.sort(key=os.path.getmtime, reverse=True)
        
        kept = 0
        for f in files:
            if os.path.basename(f) == current_valid:
                kept += 1
                continue
            
            if kept < max_backups:
                kept += 1
            else:
                try:
                    os.remove(f)
                except OSError:
                    pass
