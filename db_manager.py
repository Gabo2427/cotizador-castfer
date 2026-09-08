import sqlite3
import json
from datetime import datetime

def obtener_conexion():
    return sqlite3.connect("taller_casfer.db", check_same_thread=False)

def crear_tablas():
    conn = obtener_conexion()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS proyectos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre_cliente TEXT,
            fecha TEXT,
            piezas_json TEXT
        )
    ''')
    
    try:
        cursor.execute("ALTER TABLE proyectos ADD COLUMN costo_total REAL DEFAULT 0.0")
        cursor.execute("ALTER TABLE proyectos ADD COLUMN anticipo REAL DEFAULT 0.0")
    except sqlite3.OperationalError:
        pass 
        
    conn.commit()
    conn.close()

def guardar_proyecto(nombre_cliente, piezas_lista, costo_total=0.0, anticipo=0.0):
    conn = obtener_conexion()
    cursor = conn.cursor()
    fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    piezas_str = json.dumps(piezas_lista)
    
    cursor.execute('''
        INSERT INTO proyectos (nombre_cliente, fecha, piezas_json, costo_total, anticipo) 
        VALUES (?, ?, ?, ?, ?)
    ''', (nombre_cliente, fecha_actual, piezas_str, costo_total, anticipo))
    conn.commit()
    conn.close()

def actualizar_proyecto(id_proyecto, nombre_cliente, piezas_lista, costo_total=0.0, anticipo=0.0):
    conn = obtener_conexion()
    cursor = conn.cursor()
    fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    piezas_str = json.dumps(piezas_lista)
    
    cursor.execute('''
        UPDATE proyectos 
        SET nombre_cliente = ?, fecha = ?, piezas_json = ?, costo_total = ?, anticipo = ?
        WHERE id = ?
    ''', (nombre_cliente, fecha_actual, piezas_str, costo_total, anticipo, id_proyecto))
    conn.commit()
    conn.close()

def obtener_proyectos():
    conn = obtener_conexion()
    cursor = conn.cursor()
    cursor.execute("SELECT id, nombre_cliente, fecha, piezas_json, costo_total, anticipo FROM proyectos ORDER BY id DESC")
    filas = cursor.fetchall()
    conn.close()
    return filas

def borrar_proyecto(id_proyecto):
    conn = obtener_conexion()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM proyectos WHERE id = ?", (id_proyecto,))
    conn.commit()
    conn.close()
