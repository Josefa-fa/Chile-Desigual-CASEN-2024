# Chile desigual: CASEN 2024

Dashboard desarrollado en Django que analiza las desigualdades territoriales, económicas y sociales
de Chile a partir de la Encuesta CASEN 2024.

El sitio cuenta con cuatro gráficos (barras, líneas, dispersión y un gráfico de torta dinámico
filtrable por zona) y cuatro reportes. Cada reporte puede descargarse en PDF y en Excel,
respetando los filtros aplicados.

## Integrantes
- Josefa Espinoza
- Nicolás González
- Cristóbal Rodríguez
- Ángel Larenas
- Vicente Guzmán

## Sitio desplegado
http://100.60.180.45:8000/

## Videos
- Proceso de despliegue:[ _enlace_](https://drive.google.com/drive/folders/1hY4kvOv1jCY5_NZRGu9PPPPfExnKMBL0?usp=sharing)
- Presentación del software y explicación del código: [_enlace_](https://drive.google.com/drive/folders/1hY4kvOv1jCY5_NZRGu9PPPPfExnKMBL0?usp=sharing)

## Funcionalidades
| Sección | Ruta |
|---|---|
| Reporte: pobreza por región | `/listados/regiones/` |
| Reporte: pobreza urbana y rural | `/listados/zonas/` |
| Reporte: educación e ingresos | `/listados/educacion/` |
| Reporte: pobreza según zona (filtro por zona) | `/listados/pobreza-zona/?zona=Todas\|Urbano\|Rural` |
| Gráfico de barras | `/graficos/barras/` |
| Gráfico de líneas | `/graficos/lineas/` |
| Gráfico de dispersión | `/graficos/dispersion/` |
| Gráfico de torta dinámico (filtro por zona) | `/grafico-torta/?zona=Todas\|Urbano\|Rural` |
| Descarga en PDF / Excel | `/reportes/<regiones\|zonas\|educacion\|pobreza_zona>/pdf/` y `/excel/` |

## Estructura del proyecto
| Ruta | Contenido |
|---|---|
| `casen_web/` | Configuración del proyecto (`settings.py`, `urls.py`) |
| `analisis/models.py` | Modelos con los indicadores de CASEN 2024 |
| `analisis/views.py` | Vistas de reportes, gráficos (Matplotlib) y exportación a PDF (ReportLab) y Excel (openpyxl) |
| `analisis/urls.py` | Rutas de la aplicación |
| `analisis/templates/analisis/` | Plantillas HTML con Bootstrap |
| `analisis/fixtures/` | Datos: `casen.json` (indicadores) y `sunburst.json` (hogares por zona y situación de pobreza) |
| `scripts/preparar_datos.py` | Cálculo de indicadores a partir de los microdatos CASEN 2024 |
| `db.sqlite3` | Base de datos SQLite con los datos cargados |

## Dependencias
- Python 3.12 o superior
- Django 6.1.3
- matplotlib 3.11.2
- openpyxl 3.1.5
- reportlab 5.1.0
- gunicorn 27.0.1 (servidor de aplicación en AWS)

## Instalación y ejecución local
```
git clone https://github.com/Josefa-fa/Chile-Desigual-CASEN-2024.git
cd Chile-Desigual-CASEN-2024
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```
El sitio queda disponible en http://127.0.0.1:8000/. La base de datos incluida ya contiene los datos;
para recargarlos se usa `python manage.py loaddata casen sunburst`.

## Despliegue en AWS
La aplicación se ejecuta en una instancia Amazon EC2. Como la base de datos es SQLite (un archivo),
no se requiere un servidor de base de datos aparte: la instancia utiliza el archivo `db.sqlite3`
del repositorio.

### Configuración de la instancia
- Entorno: AWS Academy Learner Lab, región us-east-1 (N. Virginia)
- AMI: Ubuntu Server 24.04 LTS
- Tipo de instancia: t2.micro
- Security Group (reglas de entrada):
  - SSH, puerto 22
  - TCP personalizado, puerto 8000, origen 0.0.0.0/0
- Elastic IP asociada a la instancia: 100.60.180.45 (dirección fija aunque la instancia se detenga)

### Instalación en el servidor
```
sudo apt update
sudo apt install -y python3-venv python3-pip git
git clone https://github.com/Josefa-fa/Chile-Desigual-CASEN-2024.git
cd Chile-Desigual-CASEN-2024
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
```

### Configuración de Django
`casen_web/settings.py` obtiene su configuración de variables de entorno:

| Variable | Valor en el servidor |
|---|---|
| `DJANGO_ALLOWED_HOSTS` | `100.60.180.45` |
| `DJANGO_SECRET_KEY` | Clave secreta generada para el servidor |
| `DJANGO_DEBUG` | `0` (modo de depuración desactivado) |

### Ejecución como servicio
La aplicación se ejecuta con gunicorn como servicio de systemd, lo que la mantiene activa al cerrar
la sesión SSH y la reinicia automáticamente. Archivo `/etc/systemd/system/casen.service`:
```ini
[Unit]
Description=Dashboard CASEN Django
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/Chile-Desigual-CASEN-2024
Environment=DJANGO_ALLOWED_HOSTS=100.60.180.45
Environment=DJANGO_SECRET_KEY=<CLAVE-SECRETA>
Environment=DJANGO_DEBUG=0
ExecStart=/home/ubuntu/Chile-Desigual-CASEN-2024/.venv/bin/gunicorn casen_web.wsgi:application --bind 0.0.0.0:8000 --workers 2
Restart=always

[Install]
WantedBy=multi-user.target
```
Activación del servicio:
```
sudo systemctl daemon-reload
sudo systemctl enable --now casen
```

### Verificación
El sitio se comprobó desde un navegador externo en `http://100.60.180.45:8000/`, revisando los
cuatro gráficos, los cuatro reportes, el filtro por zona y las descargas en PDF y Excel.

## Fuente de los datos
Encuesta de Caracterización Socioeconómica Nacional (CASEN) 2024, Ministerio de Desarrollo Social
y Familia. Los indicadores de los reportes de regiones, zonas y educación están ponderados por el
factor de expansión; el reporte y el gráfico de pobreza según zona usan valores muestrales.
