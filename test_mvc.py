import sys
from PySide6.QtWidgets import QApplication
from core.logica import ControladorLogico
from core.project import Project

app = QApplication(sys.argv)
logica = ControladorLogico()
project = Project("TestProject", "/tmp")
logica.req_set_project(project)

def on_edds_updated(codes, themes):
    print("EDDS UPDATED!")
    print(codes)

logica.edds_updated.connect(on_edds_updated)

print("ADDING CODE")
logica.req_add_code("MyCode", "#ff0000", "")
print("ADDING FRAGMENT")
logica.req_add_fragment("MyCode", "doc1.txt", 0, 10)

