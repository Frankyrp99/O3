# 🗂️ Organizador Inteligente de Archivos

**Organizador Inteligente** es una aplicación de escritorio desarrollada en Python con interfaz gráfica (Tkinter), diseñada para facilitar la clasificación y organización de archivos en masa. Ideal para usuarios que manejan grandes volúmenes de documentos, imágenes o descargas, esta herramienta combina simplicidad y potencia en un solo ejecutable.

---

## 🚀 Características

- 🔍 Clasificación automática por tipo de archivo, extensión o patrones personalizados
- 📁 Organización por carpetas con estructura configurable
- 🧠 Modos de uso: “Solo ordenar” o “Clasificar y ordenar”
- 📊 Barra de progreso y feedback visual durante el procesamiento
- ⚙️ Configuración editable mediante archivos JSON
- 🧱 Arquitectura modular para facilitar mantenimiento y escalabilidad
- 📦 Distribución como `.exe` único usando PyInstaller, sin necesidad de instalar Python

---

## 🧰 Tecnologías utilizadas

- Python 3.x  
- Tkinter (GUI)  
- PyInstaller (empaquetado)  
- Regex para clasificación avanzada  
- JSON para configuración flexible

---

## 📦 Instalación

### Opción 1: Ejecutable (.exe)

1. Descarga el archivo `.exe` desde la carpeta `dist/`.
2. Haz doble clic para ejecutar la aplicación.
3. No se requiere instalación de Python ni dependencias externas.

### Opción 2: Ejecutar desde código fuente

1. Clona el repositorio:

   ```bash
   git clone https://github.com/tu-usuario/organizador-inteligente.git
   cd organizador-inteligente
Instala Python 3.x si no lo tienes.

Ejecuta la app:

bash
python main.py
⚙️ Estructura del proyecto
Code
📂 organizador-inteligente/
├── main.py                  # Script principal con la interfaz
├── organizador_core.py      # Lógica de clasificación y organización
├── config.json              # Configuración editable por el usuario
├── clasificacion.db         # Base de datos local (opcional)
├── app_icon.ico             # Ícono personalizado (opcional)
🛠️ Empaquetado con PyInstaller
Para generar el .exe:

bash
pyinstaller ^
  --onefile ^
  --windowed ^
  --icon=app_icon.ico ^
  --add-data "config.json;." ^
  --add-data "organizador_core.py;." ^
  --add-data "clasificacion.db;." ^
  main.py
Nota: En Linux/Mac reemplaza ; por : en --add-data.

🧪 Uso
Abre la aplicación.

Selecciona la carpeta que deseas organizar.

Elige el modo de operación.

Haz clic en “Ejecutar” y observa el progreso.

📌 Contribuciones
¡Las contribuciones son bienvenidas! Puedes abrir issues para sugerencias o errores, o enviar pull requests con mejoras.
