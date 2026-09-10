import streamlit as st
import json
from datetime import datetime
import gspread

# 1. Pega aquí el link completo de tu hoja de cálculo de Google
URL_HOJA = "https://docs.google.com/spreadsheets/d/1X_hVdUpM_-TxSFGH-DQCWDidkBBtHWVJxOxDu9NqqME/edit?usp=drivesdk"

def obtener_hoja():
    credenciales_dict = json.loads(st.secrets["google_credentials"])
    cliente_google = gspread.service_account_from_dict(credenciales_dict)
    documento = cliente_google.open_by_url(URL_HOJA)
    return documento.worksheet("Hoja 1")

def crear_tablas():
    pass

def guardar_proyecto(cliente, piezas, costo_total, anticipo):
    hoja = obtener_hoja()
    # Leemos todo por posiciones de columnas, ignorando los nombres de los encabezados
    datos = hoja.get_all_values() 
    
    nuevo_id = 1
    if len(datos) > 1:
        ids = []
        for fila in datos[1:]:
            if len(fila) > 0 and str(fila[0]).strip().isdigit():
                ids.append(int(fila[0]))
        if ids:
            nuevo_id = max(ids) + 1

    fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    proyecto_json = json.dumps(piezas)
    
    nueva_fila = [nuevo_id, cliente, fecha_actual, proyecto_json, float(costo_total), float(anticipo)]
    hoja.append_row(nueva_fila)

def obtener_proyectos():
    try:
        hoja = obtener_hoja()
        datos = hoja.get_all_values()
        if len(datos) <= 1:
            return []
        
        proyectos = []
        for fila in datos[1:]: # Saltamos la fila 1 (los encabezados)
            if len(fila) >= 6 and str(fila[0]).strip() != "":
                p_id = int(fila[0])
                cliente = str(fila[1]) # Extrae el nombre directamente de la Columna B
                fecha = str(fila[2])
                proyecto = str(fila[3])
                costo = float(fila[4]) if str(fila[4]).strip() != "" else 0.0
                anticipo = float(fila[5]) if str(fila[5]).strip() != "" else 0.0
                
                proyectos.append((p_id, cliente, fecha, proyecto, costo, anticipo))
        return proyectos
    except Exception as e:
        st.error(f"Error al leer Google Sheets: {e}")
        return []

def actualizar_proyecto(p_id, cliente, piezas, costo_total, anticipo):
    hoja = obtener_hoja()
    datos = hoja.get_all_values()
    
    for i, fila in enumerate(datos):
        if i > 0 and len(fila) > 0 and str(fila[0]).strip() == str(p_id):
            fila_excel = i + 1 
            hoja.update_acell(f'B{fila_excel}', cliente)
            hoja.update_acell(f'D{fila_excel}', json.dumps(piezas))
            hoja.update_acell(f'E{fila_excel}', float(costo_total))
            hoja.update_acell(f'F{fila_excel}', float(anticipo))
            break

def borrar_proyecto(p_id):
    hoja = obtener_hoja()
    datos = hoja.get_all_values()
    
    for i, fila in enumerate(datos):
        if i > 0 and len(fila) > 0 and str(fila[0]).strip() == str(p_id):
            fila_excel = i + 1 
            hoja.delete_rows(fila_excel)
            break