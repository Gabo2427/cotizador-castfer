import streamlit as st
import json
import pandas as pd
from datetime import datetime
import gspread

# 1. Pega aquí el link completo de tu hoja de cálculo de Google
URL_HOJA = "https://docs.google.com/spreadsheets/d/1X_hVdUpM_-TxSFGH-DQCWDidkBBtHWVJxOxDu9NqqME/edit?usp=drivesdk"

def obtener_hoja():
    # Tomamos el JSON de tu secrets.toml
    credenciales_dict = json.loads(st.secrets["google_credentials"])
    
    # Nos conectamos a Google de forma directa y nativa
    cliente_google = gspread.service_account_from_dict(credenciales_dict)
    
    # Abrimos tu archivo y seleccionamos la pestaña
    documento = cliente_google.open_by_url(URL_HOJA)
    return documento.worksheet("Hoja 1")

def crear_tablas():
    pass

def guardar_proyecto(cliente, piezas, costo_total, anticipo):
    hoja = obtener_hoja()
    
    # Traemos los datos para ver el último ID
    datos = hoja.get_all_records()
    nuevo_id = 1
    
    if datos:
        df = pd.DataFrame(datos)
        if "ID" in df.columns:
            max_id = pd.to_numeric(df["ID"], errors='coerce').max()
            if pd.notna(max_id):
                nuevo_id = int(max_id) + 1

    fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    proyecto_json = json.dumps(piezas)
    
    # Creamos la fila y la insertamos directamente al final (súper rápido)
    nueva_fila = [nuevo_id, cliente, fecha_actual, proyecto_json, float(costo_total), float(anticipo)]
    hoja.append_row(nueva_fila)

def obtener_proyectos():
    try:
        hoja = obtener_hoja()
        datos = hoja.get_all_records()
        if not datos:
            return []
        
        df = pd.DataFrame(datos)
        proyectos = []
        
        for _, row in df.iterrows():
            if pd.notna(row.get("ID")) and str(row.get("ID")).strip() != "":
                p_id = int(row["ID"])
                cliente = str(row.get("Cliente", ""))
                fecha = str(row.get("Fecha", ""))
                proyecto = str(row.get("Proyecto", "[]"))
                costo = float(row.get("Costo_Total", 0)) if pd.notna(row.get("Costo_Total")) and str(row.get("Costo_Total")).strip() != "" else 0.0
                anticipo = float(row.get("Anticipo", 0)) if pd.notna(row.get("Anticipo")) and str(row.get("Anticipo")).strip() != "" else 0.0
                
                proyectos.append((p_id, cliente, fecha, proyecto, costo, anticipo))
        return proyectos
    except Exception as e:
        st.error(f"Error al leer Google Sheets: {e}")
        return []

def actualizar_proyecto(p_id, cliente, piezas, costo_total, anticipo):
    hoja = obtener_hoja()
    datos = hoja.get_all_records()
    
    if datos:
        df = pd.DataFrame(datos)
        idx = df[df["ID"] == p_id].index
        if not idx.empty:
            # El índice 0 de Pandas es la fila 2 en Excel (por los encabezados)
            fila_excel = int(idx[0]) + 2 
            
            # Actualizamos celda por celda (muy estable)
            hoja.update_acell(f'B{fila_excel}', cliente)
            hoja.update_acell(f'D{fila_excel}', json.dumps(piezas))
            hoja.update_acell(f'E{fila_excel}', float(costo_total))
            hoja.update_acell(f'F{fila_excel}', float(anticipo))

def borrar_proyecto(p_id):
    hoja = obtener_hoja()
    datos = hoja.get_all_records()
    
    if datos:
        df = pd.DataFrame(datos)
        idx = df[df["ID"] == p_id].index
        if not idx.empty:
            fila_excel = int(idx[0]) + 2 
            # Eliminamos la fila completa de la hoja
            hoja.delete_rows(fila_excel)
