import importlib
import models.document

print("Ruta del módulo:", models.document.__file__)
print("Contenido disponible:", dir(models.document))
importlib.reload(models.document)
print("Después de recargar:", dir(models.document))