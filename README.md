TrabajoCasenGrupo2 - Chile desigual: CASEN 2024

Contenido
  ProyectoCasenGrupo2/   Proyecto Django (dashboard con 3 listados y 3 graficos)
  Documentos/            Paso a paso del trabajo y guion de exposicion (PDF)

Como ejecutar el proyecto (Windows)
  1. cd ProyectoCasenGrupo2
  2. python -m venv .venv
  3. .venv\Scripts\python.exe -m pip install -r requirements.txt
  4. .venv\Scripts\python.exe manage.py runserver 8001
  5. Abrir http://127.0.0.1:8001/

La base de datos (db.sqlite3) ya trae los datos cargados.
Si se necesitara recargarlos: python manage.py loaddata casen
