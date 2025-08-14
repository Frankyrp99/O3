import unicodedata
import argparse
import json
import re
import shutil
import sqlite3
import sys
from pathlib import Path
import tkinter as tk
from tkinter import ttk

# -------------------------------
# Utilidades de rutas
# -------------------------------


def procesar_directorio(
    directorio: str, modo: str, db_path: str, config_path: str, parent=None
) -> str:
    ruta = Path(directorio).resolve()
    if not ruta.exists() or not ruta.is_dir():
        raise ValueError(f"Directorio inválido: {directorio}")

    cfg = cargar_config(Path(config_path))
    if modo == "simple":
        return organizar_simple(ruta, [e.lower() for e in cfg["extensiones"]])
    else:
        return organizar_clasificar(ruta, Path(db_path), cfg, parent=parent)


def resource_path(relative_path: str) -> Path:
    if getattr(sys, "frozen", False):
        base_path = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    else:
        base_path = Path(__file__).parent
    return (base_path / relative_path).resolve()


# -------------------------------
# Configuración
# -------------------------------
def cargar_config(path_config: Path) -> dict:
    # Config por defecto si el archivo no existe
    default = {
        "extensiones": [".avi", ".mp4", ".mkv", ".mpg", ".mov", ".wmv", ".mp3"],
        "categorias_peliculas": [
            "Acción",
            "Comedia",
            "Drama",
            "Terror",
            "Ciencia Ficción",
            "Romance",
            "Animación",
            "Documental",
            "Otros",
        ],
        "nacionalidades_novelas": [
            "Mexicana",
            "Colombiana",
            "Turca",
            "Brasileña",
            "Chilena",
            "Argentina",
            "Española",
            "Estadounidense",
            "Otra",
        ],
    }
    try:
        if path_config.exists():
            with path_config.open("r", encoding="utf-8") as f:
                cfg = json.load(f)
                # Mezcla básica para no romper si faltan claves
                default.update({k: v for k, v in cfg.items() if k in default})
        return default
    except Exception:
        # Si hay error al leer JSON, usar default
        return default


# -------------------------------
# Base de datos
# -------------------------------
def inicializar_db(db_path: Path):
    conn = sqlite3.connect(str(db_path))
    c = conn.cursor()
    c.execute(
        """CREATE TABLE IF NOT EXISTS clasificacion (
                 nombre TEXT PRIMARY KEY,
                 tipo TEXT,
                 categoria TEXT,
                 nacionalidad TEXT)"""
    )
    c.execute(
        """CREATE TABLE IF NOT EXISTS palabras_clave (
                 palabra TEXT PRIMARY KEY,
                 tipo TEXT,
                 categoria TEXT,
                 nacionalidad TEXT)"""
    )
    conn.commit()
    conn.close()


def obtener_clasificacion(nombre_base: str, db_path: Path):
    conn = sqlite3.connect(str(db_path))
    c = conn.cursor()
    c.execute(
        "SELECT tipo, categoria, nacionalidad FROM clasificacion WHERE nombre=?",
        (nombre_base,),
    )
    res = c.fetchone()
    if res:
        conn.close()
        return res
    # Búsqueda por palabras clave
    palabras = re.findall(r"\w+", nombre_base.lower())
    for p in palabras:
        if len(p) > 3:
            c.execute(
                "SELECT tipo, categoria, nacionalidad FROM palabras_clave WHERE palabra=?",
                (p,),
            )
            r2 = c.fetchone()
            if r2:
                conn.close()
                return r2
    conn.close()
    return None


def guardar_clasificacion_en_db(
    nombre_base: str, tipo: str, categoria: str, nacionalidad: str, db_path: Path
):
    conn = sqlite3.connect(str(db_path))
    c = conn.cursor()
    c.execute(
        "INSERT OR REPLACE INTO clasificacion VALUES (?, ?, ?, ?)",
        (nombre_base, tipo, categoria, nacionalidad),
    )
    for palabra in re.findall(r"\w+", nombre_base.lower()):
        if len(palabra) > 3:
            c.execute(
                "INSERT OR IGNORE INTO palabras_clave VALUES (?, ?, ?, ?)",
                (palabra, tipo, categoria, nacionalidad),
            )
    conn.commit()
    conn.close()


# -------------------------------
# Normalización y parsing
# -------------------------------


def quitar_acentos(s: str) -> str:
    return "".join(
        ch for ch in unicodedata.normalize("NFKD", s) if not unicodedata.combining(ch)
    )


def normalizar_nombre(nombre: str) -> str:
    # Elimina acentos y caracteres no alfanuméricos, dejando espacios
    nombre = quitar_acentos(nombre)
    nombre = re.sub(r"[^a-zA-Z0-9]+", " ", nombre).strip()
    return nombre.title()


def obtener_nombre_cap(nombre_archivo: str):
    nombre, _ = Path(nombre_archivo).stem, Path(nombre_archivo).suffix
    capitulo = ""
    temporada = ""
    capitulo_patterns = [
        r"\b(\d{1,3}[xX]\d{1,3})\b",  # 1x02
        r"\b([sS]\d{1,3}[eE]\d{1,3})\b",  # S01E03
        r"\b(ep?\s?\d{1,3})\b",  # EP12, Ep5
        r"\b(\d{3,4})\b",  # 103 (S1E03)
    ]
    base = nombre
    for pattern in capitulo_patterns:
        m = re.search(pattern, base)
        if m:
            capitulo = m.group(1).upper()
            base = base.replace(m.group(0), " ")
            break
    temporada_patterns = [
        r"\[TEMP\s*(\d+)\]",  # [TEMP 2]
        r"\bSeason\s*(\d+)\b",  # Season 3
        r"\b[Ss](\d{1,2})\b",  # S02
    ]

    for pattern in temporada_patterns:
        m = re.search(pattern, base, re.IGNORECASE)
        if m:
            temporada = f"Season {m.group(1)}"
            base = re.sub(pattern, " ", base, flags=re.IGNORECASE)
            break
    return normalizar_nombre(base.strip()), capitulo, temporada


# -------------------------------
# Movimiento de archivos
# -------------------------------
def mover_archivo(origen: Path, destino: Path):
    destino.parent.mkdir(parents=True, exist_ok=True)
    if destino.exists():
        base = destino.with_suffix("")  # sin extensión
        ext = destino.suffix
        i = 1
        while True:
            candidato = Path(f"{base} ({i}){ext}")
            if not candidato.exists():
                shutil.move(str(origen), str(candidato))
                return candidato
            i += 1
    else:
        shutil.move(str(origen), str(destino))
        return destino


# -------------------------------
# Clasificación por lote (UI)
# -------------------------------
def clasificar_por_lote(
    pendientes: list, cfg: dict, db_path: Path, parent=None
) -> dict:
    """
    Muestra una ventana modal para clasificar elementos pendientes.
    Retorna un dict nombre_base -> (tipo, categoria, nacionalidad)
    """
    resultados = {}
    if not pendientes:
        return resultados

    # Crear ventana modal sobre la principal si hay parent
    if parent is not None:
        win = tk.Toplevel(parent)
        win.transient(parent)
        win.grab_set()
    else:
        win = tk.Tk()

    win.title("Clasificar contenido")
    win.geometry("420x420")
    win.resizable(False, False)

    idx = {"i": 0}
    total = len(pendientes)

    tipo_var = tk.StringVar(value="serie")
    categoria_var = tk.StringVar(value="")
    nacionalidad_var = tk.StringVar(value="")
    subtipo_var = tk.StringVar(value="audio")  # música

    ttk.Label(win, text="", font=("Arial", 11, "bold")).pack(pady=10)
    label_titulo = win.pack_slaves()[0]  # el último ttk.Label añadido
    label_prog = ttk.Label(win, text=f"0/{total}")
    label_prog.pack()

    frame_tipo = ttk.LabelFrame(win, text="Tipo de contenido")
    frame_tipo.pack(fill="x", padx=10, pady=6)
    for t in ["serie", "pelicula", "novela", "musica", "show"]:
        ttk.Radiobutton(
            frame_tipo, text=t.capitalize(), variable=tipo_var, value=t
        ).pack(side="left", padx=5)

    frame_categoria = ttk.LabelFrame(win, text="Categoría (Películas)")
    frame_categoria.pack(fill="x", padx=10, pady=6)
    combo_categoria = ttk.Combobox(
    frame_categoria,
    textvariable=categoria_var,
    values=cfg.get("categorias_peliculas", []),
    state="readonly",
)
    combo_categoria.pack(fill="x", padx=8, pady=6)

    frame_nacionalidad = ttk.LabelFrame(win, text="Nacionalidad (Novelas)")
    frame_nacionalidad.pack(fill="x", padx=10, pady=6)
    combo_nacionalidad = ttk.Combobox(
    frame_nacionalidad,
    textvariable=nacionalidad_var,
    values=cfg.get("nacionalidades_novelas", []),
    state="readonly",
)
    combo_nacionalidad.pack(fill="x", padx=8, pady=6)

    frame_subtipo = ttk.LabelFrame(win, text="Subtipo (Música)")
    frame_subtipo.pack(fill="x", padx=10, pady=6)
    combo_subtipo = ttk.Combobox(
        frame_subtipo,
        textvariable=subtipo_var,
        values=["audio", "video"],
        state="readonly",
    )
    combo_subtipo.pack(fill="x", padx=8, pady=6)

    def actualizar_campos(*_):
        if tipo_var.get() == "pelicula":
            combo_categoria.config(state="readonly")
            combo_nacionalidad.config(state="disabled")
            combo_subtipo.config(state="disabled")
        elif tipo_var.get() == "novela":
            combo_categoria.config(state="disabled")
            combo_nacionalidad.config(state="readonly")
            combo_subtipo.config(state="disabled")
        elif tipo_var.get() == "musica":
            combo_categoria.config(state="disabled")
            combo_nacionalidad.config(state="disabled")
            combo_subtipo.config(state="readonly")
        else:
            combo_categoria.config(state="disabled")
            combo_nacionalidad.config(state="disabled")
            combo_subtipo.config(state="disabled")

    tipo_var.trace_add("write", lambda *a: actualizar_campos())
    actualizar_campos()

    def cargar_actual():
        i = idx["i"]
        nombre_base = pendientes[i]
        label_titulo.config(text=f"Clasificar: {nombre_base}")
        label_prog.config(text=f"{i+1}/{total}")
        tipo_var.set("serie")
        categoria_var.set("")
        nacionalidad_var.set("")
        subtipo_var.set("audio")
        actualizar_campos()

    def guardar_y_siguiente():
        i = idx["i"]
        nombre_base = pendientes[i]
        t = tipo_var.get()
        if t == "pelicula":
            cat = categoria_var.get() or "Otros"
            nac = ""
        elif t == "novela":
            cat = ""
            nac = nacionalidad_var.get() or "Otra"
        elif t == "musica":
            cat = subtipo_var.get() or "audio"
            nac = ""
        else:
            cat = ""
            nac = ""
        resultados[nombre_base] = (t, cat, nac)
        avanzar()

    def avanzar():
        idx["i"] += 1
        if idx["i"] >= total:
            win.destroy()
        else:
            cargar_actual()

    btns = ttk.Frame(win)
    btns.pack(pady=10)
    ttk.Button(btns, text="Guardar y siguiente", command=guardar_y_siguiente).pack(
        side="left", padx=6
    )
    ttk.Button(btns, text="Omitir", command=avanzar).pack(side="left", padx=6)
    ttk.Button(btns, text="Omitir todos", command=win.destroy).pack(side="left", padx=6)

    cargar_actual()

    if parent is not None:
        win.wait_window(win)
    else:
        win.mainloop()

    return resultados  # dict


# -------------------------------
# Modo: Solo ordenar (v1.0 mejorado)
# -------------------------------
def organizar_simple(ruta: Path, extensiones: list) -> str:
    archivos_por_serie = {}
    for item in ruta.iterdir():
        if item.is_file() and item.suffix.lower() in extensiones:
            nombre, cap, temp = obtener_nombre_cap(item.name)
            clave = (nombre, temp)
            archivos_por_serie.setdefault(clave, []).append(item)

    logs = []
    for (nombre_serie, temporada), archivos in archivos_por_serie.items():
        nombre_carpeta = (
            nombre_serie if not temporada else f"{nombre_serie} - {temporada}"
        )
        carpeta_destino = ruta / nombre_carpeta
        carpeta_destino.mkdir(parents=True, exist_ok=True)

        for archivo in archivos:
            destino = carpeta_destino / archivo.name
            try:
                mover_archivo(archivo, destino)
                logs.append(f"Movido: {archivo.name} -> {carpeta_destino.name}")
            except Exception as e:
                logs.append(f"Error moviendo {archivo.name}: {e}")

        logs.append(
            f"Carpeta creada: {nombre_carpeta} | Total archivos: {len(archivos)}"
        )
        logs.append("=" * 50)

    return "\n".join(logs) if logs else "No se encontraron archivos para ordenar."


# -------------------------------
# Modo: Clasificar y ordenar
# -------------------------------
def organizar_clasificar(ruta: Path, db_path: Path, cfg: dict, parent=None) -> str:

    inicializar_db(db_path)
    extensiones = set(e.lower() for e in cfg["extensiones"])
    archivos = [
        f for f in ruta.iterdir() if f.is_file() and f.suffix.lower() in extensiones
    ]

    # Identificar nombres base a clasificar
    mapa_archivos = []  # lista de tuplas (path, nombre_base, cap, temp, ext)
    nombres_base = set()
    for f in archivos:
        nombre_base, cap, temp = obtener_nombre_cap(f.name)
        # Heurística: MP3 se marcan como música/audio automáticamente
        mapa_archivos.append((f, nombre_base, cap, temp, f.suffix.lower()))
        nombres_base.add(nombre_base)

    # Consultar DB y determinar pendientes
    ya_clasificados = {}
    pendientes = []
    for nb in sorted(nombres_base):
        clasif = obtener_clasificacion(nb, db_path)
        if clasif:
            ya_clasificados[nb] = clasif
        else:
            pendientes.append(nb)

    # Abrir una sola ventana para clasificar los pendientes
    nuevos = clasificar_por_lote(pendientes, cfg, db_path, parent=parent)
    ya_clasificados.update(nuevos)
    for nb, (t, cat, nac) in nuevos.items():
        guardar_clasificacion_en_db(nb, t, cat or "", nac or "", db_path)

    logs = []
    # Aplicar reglas y mover
    for f, nb, cap, temp, ext in mapa_archivos:
        try:
            if ext == ".mp3":
                tipo, categoria, nacionalidad = ("musica", "audio", "")
            else:
                clasif = ya_clasificados.get(nb)
                if not clasif:
                    # Si sigue sin clasificación, no mover
                    logs.append(f"Omitido (sin clasificación): {f.name}")
                    continue
                tipo, categoria, nacionalidad = clasif

            # Construir destino según tipo
            if tipo == "serie":
                destino_dir = ruta / "Series" / nb
                if temp:
                    destino_dir = destino_dir / temp
            elif tipo == "pelicula":
                categoria = categoria or "Otros"
                destino_dir = ruta / "Películas" / categoria / nb
            elif tipo == "novela":
                nacionalidad = nacionalidad or "Otra"
                destino_dir = ruta / "Novelas" / nacionalidad / nb
            elif tipo == "musica":
                destino_dir = ruta / "Audio" / nb
            elif tipo == "show":
                destino_dir = ruta / "Shows" / nb
            else:
                logs.append(f"Omitido (tipo desconocido): {f.name}")
                continue

            destino = destino_dir / f.name
            mover_archivo(f, destino)
            logs.append(f"Movido: {f.name} -> {destino_dir.relative_to(ruta)}")
        except Exception as e:
            logs.append(f"Error moviendo {f.name}: {e}")

    return "\n".join(logs) if logs else "No se movieron archivos."


# -------------------------------
# Main
# -------------------------------
def main():
    parser = argparse.ArgumentParser(description="Organizador de multimedia")
    parser.add_argument("--modo", choices=["simple", "clasificar"], required=True)
    parser.add_argument("--dir", dest="directorio", required=True)
    parser.add_argument("--db", dest="db_path", required=False)
    parser.add_argument("--config", dest="config_path", required=False)
    args = parser.parse_args()

    ruta = Path(args.directorio).resolve()
    if not ruta.exists() or not ruta.is_dir():
        print("Directorio inválido.", file=sys.stderr)
        sys.exit(2)

    cfg = cargar_config(
        Path(args.config_path) if args.config_path else resource_path("config.json")
    )

    if args.modo == "simple":
        salida = organizar_simple(ruta, [e.lower() for e in cfg["extensiones"]])
        print(salida)
        sys.exit(0)

    # Clasificar
    if not args.db_path:
        # Si no se da una ruta, crear la BD junto al ejecutable/script
        db_path = resource_path("clasificacion.db")
    else:
        db_path = Path(args.db_path)
    try:
        salida = organizar_clasificar(ruta, db_path, cfg)
        print(salida)
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
