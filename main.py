# -*- coding: utf-8 -*-
import sys
import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from organizador_core import procesar_directorio


# Obtener la ruta base (compatible con ejecutables)
def resource_path(relative_path: str) -> str:
    if getattr(sys, "frozen", False):
        base_path = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    else:
        base_path = os.path.dirname(__file__)
    return os.path.join(base_path, relative_path)


def seleccionar_directorio():
    directorio = filedialog.askdirectory(
        mustexist=True, title="Selecciona una carpeta", initialdir="./"
    )
    if directorio:
        lista_directorios.insert(tk.END, directorio)


def eliminar_seleccion():
    seleccion = lista_directorios.curselection()
    for index in seleccion[::-1]:
        lista_directorios.delete(index)


def ejecutar_script():
    carpetas = lista_directorios.get(0, tk.END)
    if not carpetas:
        messagebox.showwarning("Atención", "Añade al menos una carpeta.")
        return

    modo = modo_var.get()  # "simple" o "clasificar"
    db_path = resource_path("clasificacion.db")
    config_path = resource_path("config.json")

    progress["maximum"] = len(carpetas)
    progress["value"] = 0

    resultados = []
    for i, directorio in enumerate(carpetas, start=1):
        try:
            salida = procesar_directorio(
                directorio=directorio,
                modo=modo,
                db_path=db_path,
                config_path=config_path,
                parent=ventana,  # para que cualquier UI de clasificación sea modal
            )
            resultados.append(f"[OK] {directorio}\n{salida}\n")
        except Exception as e:
            resultados.append(f"[ERROR] {directorio}\n{e}\n")
        finally:
            progress["value"] = i
            ventana.update_idletasks()

    resumen = "\n".join(resultados)
    messagebox.showinfo(
        "Resultado",
        (
            resumen
            if len(resumen) < 5000
            else resumen[:5000] + "\n...\n(Resumen truncado)"
        ),
    )


def abrir_ayuda():
    mensaje = (
        "Organizador de multimedia\n\n"
        "1. Agrega carpetas con 'Agregar Carpeta'.\n"
        "2. Elimina las que no quieras con 'Eliminar Carpeta'.\n"
        "3. Elige el modo:\n"
        "   - Solo ordenar: agrupa por nombre y temporada (sin clasificar en BD).\n"
        "   - Clasificar y ordenar: usa BD y una ventana única para clasificar ítems desconocidos.\n"
        "4. Pulsa 'Ejecutar' para procesar las carpetas.\n"
    )
    messagebox.showinfo("Ayuda", mensaje)


# GUI principal
ventana = tk.Tk()
ventana.title("Organizador de Videos")
ventana.geometry("520x460")

# Tema
style = ttk.Style()
try:
    style.theme_use("clam")
except tk.TclError:
    pass

# Widgets
label_instrucciones = ttk.Label(
    ventana, text="Añade carpetas y elige cómo procesarlas:"
)
label_instrucciones.grid(
    row=0, column=0, columnspan=3, pady=(12, 6), padx=12, sticky="w"
)

# Modo de operación
modo_var = tk.StringVar(value="simple")  # "simple" o "clasificar"
frame_modo = ttk.LabelFrame(ventana, text="Modo")
frame_modo.grid(row=1, column=0, columnspan=3, padx=12, pady=6, sticky="ew")
ttk.Radiobutton(
    frame_modo, text="Solo ordenar (v1.0)", variable=modo_var, value="simple"
).pack(side="left", padx=8, pady=4)
ttk.Radiobutton(
    frame_modo, text="Clasificar y ordenar", variable=modo_var, value="clasificar"
).pack(side="left", padx=8, pady=4)

label_lista = ttk.Label(ventana, text="Carpetas seleccionadas:")
label_lista.grid(row=2, column=0, columnspan=3, pady=(6, 4), padx=12, sticky="w")

lista_directorios = tk.Listbox(ventana, selectmode=tk.MULTIPLE, height=10)
lista_directorios.grid(row=3, column=0, columnspan=3, pady=6, padx=12, sticky="nsew")

ttk.Button(ventana, text="Agregar Carpeta", command=seleccionar_directorio).grid(
    row=4, column=0, pady=6, padx=12, sticky="ew"
)
ttk.Button(ventana, text="Eliminar Carpeta", command=eliminar_seleccion).grid(
    row=4, column=1, pady=6, padx=6, sticky="ew"
)
ttk.Button(ventana, text="Ayuda", command=abrir_ayuda).grid(
    row=4, column=2, pady=6, padx=(6, 12), sticky="ew"
)

# Barra de progreso y ejecutar
progress = ttk.Progressbar(ventana, mode="determinate")
progress.grid(row=5, column=0, columnspan=3, pady=(6, 0), padx=12, sticky="ew")

ttk.Button(ventana, text="iniciar", command=ejecutar_script).grid(
    row=6, column=0, columnspan=3, pady=10, padx=12, sticky="ew"
)

# Grid weights
ventana.grid_rowconfigure(3, weight=1)
ventana.grid_columnconfigure(0, weight=1)
ventana.grid_columnconfigure(1, weight=1)
ventana.grid_columnconfigure(2, weight=1)

ventana.mainloop()
