import streamlit as st
import json
from collections import Counter
from logica_cotizador import Ventana, Puerta, VentanaEuroventS50, VentanaEuroventS70, FijoEurovent, VentanaProyeccionBatienteEuroventS35
import db_manager
import math
from datetime import datetime

PIN_SECRETO = "2026"
PREGUNTA_RECUPERACION = "¿Cómo se llamo el primer perro de la casa?"
RESPUESTA_RECUPERACION = "titan" 

st.set_page_config(page_title="Cotizador CastFer", page_icon="🪟", layout="wide")
db_manager.crear_tablas()

st.markdown("""
<style>
    button[kind="tertiary"] { opacity: 0.2; transition: opacity 0.3s ease-in-out; }
    button[kind="tertiary"]:hover { opacity: 1.0; }
    div[data-testid="stRadio"] > div { flex-direction: row; gap: 20px; background-color: #f0f2f6; padding: 10px; border-radius: 10px;}
</style>
""", unsafe_allow_html=True)

if 'proyecto' not in st.session_state: st.session_state.proyecto = []
if 'edit_index' not in st.session_state: st.session_state.edit_index = None
if 'proyecto_activo_id' not in st.session_state: st.session_state.proyecto_activo_id = None
if 'costo_total' not in st.session_state: st.session_state.costo_total = 0.0
if 'anticipo' not in st.session_state: st.session_state.anticipo = 0.0
if 'nombre_cliente' not in st.session_state: st.session_state.nombre_cliente = ""

# ==========================================
# FUNCIONES GLOBALES DE OPTIMIZACIÓN
# ==========================================
def parsear_pedaceria(texto):
    if not texto.strip(): return []
    try: return [float(x.strip()) for x in texto.split(',') if x.strip()]
    except: return []

def optimizador_aluminio_taller(cortes_list, pedaceria_str, tramo_ideal=600.0):
    pedaceria = parsear_pedaceria(pedaceria_str)
    DESPERDICIO_SIERRA = 0.3 
    cortes_pendientes = sorted(cortes_list, key=lambda x: x["medida"], reverse=True)
    pedaceria_ordenada = sorted(pedaceria)
    uso_ped = {i: {"tamano": p, "usados": []} for i, p in enumerate(pedaceria_ordenada)}

    def buscar_mejor_ajuste(cortes, capacidad):
        cap_int = int(round(capacidad * 10))
        dp = [0] * (cap_int + 1)
        elecciones = [[] for _ in range(cap_int + 1)]
        for i, c in enumerate(cortes):
            peso = int(round((c["medida"] + DESPERDICIO_SIERRA) * 10))
            if peso > cap_int: continue
            for w in range(cap_int, peso - 1, -1):
                if dp[w - peso] + peso > dp[w]:
                    dp[w] = dp[w - peso] + peso
                    elecciones[w] = elecciones[w - peso] + [i]
        return elecciones[cap_int]

    for i in range(len(pedaceria_ordenada)):
        if not cortes_pendientes: break
        capacidad_ped = pedaceria_ordenada[i]
        mejores_idx = buscar_mejor_ajuste(cortes_pendientes, capacidad_ped)
        for idx in sorted(mejores_idx, reverse=True):
            uso_ped[i]["usados"].append(cortes_pendientes.pop(idx))

    tramos_nuevos = []
    while cortes_pendientes:
        mejores_idx = buscar_mejor_ajuste(cortes_pendientes, tramo_ideal)
        if not mejores_idx:
            tramos_nuevos.append([cortes_pendientes.pop(0)])
            continue
        tramo_actual = []
        for idx in sorted(mejores_idx, reverse=True):
            tramo_actual.append(cortes_pendientes.pop(idx))
        tramos_nuevos.append(tramo_actual)
    return tramos_nuevos, uso_ped

def optimizador_vidrio(vidrios_list, pedaceria_str):
    pedaceria = []
    if pedaceria_str.strip():
        for t in pedaceria_str.split(','):
            try:
                w, h = [float(x.strip()) for x in t.lower().split('x')]
                pedaceria.append({"w": w, "h": h, "usado": False, "original": t})
            except: pass
    
    piezas_exactas, piezas_reducidas = [], []
    for v in vidrios_list:
        try:
            w, h = [float(x.strip()) for x in v['medida'].lower().split('x')]
            piezas_exactas.append({"w": round(w, 1), "h": round(h, 1), "etiqueta": v['etiqueta'], "original": v['medida'], "activo": v.get('activo', True)})
            piezas_reducidas.append({"w": round(w - 1.0, 1), "h": round(h - 1.0, 1), "etiqueta": v['etiqueta'], "original": v['medida'], "activo": v.get('activo', True)})
        except: pass
        
    piezas_rescatadas, pendientes_exactas, pendientes_reducidas = [], [], []
    for i in range(len(piezas_exactas)):
        p_ex, p_red = piezas_exactas[i], piezas_reducidas[i]
        colocado = False
        for ped in pedaceria:
            if not ped["usado"]:
                if (p_ex["w"] <= ped["w"] and p_ex["h"] <= ped["h"]) or (p_ex["w"] <= ped["h"] and p_ex["h"] <= ped["w"]):
                    ped["usado"] = True
                    piezas_rescatadas.append({"pieza": p_ex, "pedazo": ped})
                    colocado = True
                    break
        if not colocado:
            pendientes_exactas.append(p_ex)
            pendientes_reducidas.append(p_red)
            
    def calcular_tetris(piezas_pendientes, ancho_hoja, alto_hoja):
        lista = sorted(piezas_pendientes, key=lambda p: max(p["w"], p["h"]), reverse=True)
        class Node:
            def __init__(self, x, y, w, h):
                self.x, self.y, self.w, self.h = x, y, w, h
                self.used = False
                self.right, self.bottom = None, None
            def insert(self, pw, ph):
                if self.used:
                    res = self.right.insert(pw, ph)
                    if res: return res
                    return self.bottom.insert(pw, ph)
                elif pw <= self.w and ph <= self.h:
                    self.used = True
                    dw, dh = self.w - pw, self.h - ph
                    if dw > dh: 
                        self.right = Node(self.x + pw, self.y, dw, self.h)
                        self.bottom = Node(self.x, self.y + ph, pw, dh)
                    else: 
                        self.right = Node(self.x + pw, self.y, dw, ph)
                        self.bottom = Node(self.x, self.y + ph, self.w, dh)
                    return self
                return None

        hojas = []
        for p in lista:
            pw, ph = p["w"], p["h"]
            colocado = False
            for raiz in hojas:
                if raiz['tree'].insert(pw, ph):
                    raiz['piezas'].append({"w": pw, "h": ph, "etiqueta": p["etiqueta"], "activo": p["activo"]})
                    colocado = True
                    break
                elif raiz['tree'].insert(ph, pw):
                    raiz['piezas'].append({"w": ph, "h": pw, "etiqueta": p["etiqueta"] + " (Rotado)", "activo": p["activo"]})
                    colocado = True
                    break
            if not colocado:
                nueva_raiz = Node(0, 0, ancho_hoja, alto_hoja)
                if nueva_raiz.insert(pw, ph):
                    hojas.append({'tree': nueva_raiz, 'piezas': [{"w": pw, "h": ph, "etiqueta": p["etiqueta"], "activo": p["activo"]}]})
                elif nueva_raiz.insert(ph, pw):
                    hojas.append({'tree': nueva_raiz, 'piezas': [{"w": ph, "h": pw, "etiqueta": p["etiqueta"] + " (Rotado)", "activo": p["activo"]}]})
                    
        hojas_out = []
        for h in hojas:
            hojas_out.append({"ancho_usado": ancho_hoja, "columnas": [{"ancho": "Cortes Variados", "alto_usado": "", "piezas": h['piezas']}]})
        return hojas_out

    scenarios = []
    if pendientes_exactas:
        h1 = calcular_tetris(pendientes_exactas, 180.0, 260.0)
        scenarios.append({'hojas': h1, 'ancho': 180.0, 'reducido': False, 'score': len(h1)*(180*260)})
        h2 = calcular_tetris(pendientes_exactas, 230.0, 260.0)
        scenarios.append({'hojas': h2, 'ancho': 230.0, 'reducido': False, 'score': len(h2)*(230*260)})
        h3 = calcular_tetris(pendientes_reducidas, 180.0, 260.0)
        scenarios.append({'hojas': h3, 'ancho': 180.0, 'reducido': True, 'score': len(h3)*(180*260)})
        h4 = calcular_tetris(pendientes_reducidas, 230.0, 260.0)
        scenarios.append({'hojas': h4, 'ancho': 230.0, 'reducido': True, 'score': len(h4)*(230*260)})
        scenarios.sort(key=lambda x: (x['score'], x['reducido']))
        best = scenarios[0]
    else:
        best = {'hojas': [], 'ancho': 180.0, 'reducido': False, 'score': 0}

    return best['hojas'], piezas_rescatadas, best

# ==========================================
# BARRA LATERAL (ROLES Y GESTIÓN DE PROYECTOS)
# ==========================================
with st.sidebar:
    st.image("logopagina.png", use_container_width=True)
    st.title("📂 Control de Taller")
    
    st.subheader("📚 Proyectos Guardados")
    proyectos_guardados = db_manager.obtener_proyectos()
    
    if proyectos_guardados:
        opciones = {p[0]: f"{p[1]} ({p[2]})" for p in proyectos_guardados}
        seleccion = st.selectbox("Selecciona un proyecto para cargar:", options=list(opciones.keys()), format_func=lambda x: opciones[x])
        if st.button("📂 Cargar para Taller", use_container_width=True):
            proyecto_cargado = next((p for p in proyectos_guardados if p[0] == seleccion), None)
            if proyecto_cargado:
                st.session_state.proyecto_activo_id = proyecto_cargado[0]
                st.session_state.nombre_cliente = proyecto_cargado[1]
                st.session_state.proyecto = json.loads(proyecto_cargado[3])
                try: st.session_state.anticipo = float(proyecto_cargado[5])
                except IndexError: st.session_state.anticipo = 0.0
                st.rerun()

    if st.button("✨ Limpiar Pantalla (Nuevo)", use_container_width=True):
        st.session_state.proyecto = []
        st.session_state.edit_index = None
        st.session_state.proyecto_activo_id = None
        st.session_state.nombre_cliente = ""
        st.session_state.costo_total = 0.0
        st.session_state.anticipo = 0.0
        st.rerun()

    st.write("---")
    
    st.subheader("🔒 Modo Administrador")
    pin_ingresado = st.text_input("🔑 PIN de Acceso:", type="password")

    if pin_ingresado == PIN_SECRETO:
        st.session_state['admin'] = True
        st.success("Modo Administrador activado")
        st.write("")
        st.session_state.nombre_cliente = st.text_input("Nombre del Cliente:", value=st.session_state.nombre_cliente)
        
        if st.button("💾 Guardar Proyecto", type="primary", use_container_width=True):
            if st.session_state.nombre_cliente == "":
                st.warning("⚠️ Ingresa el nombre del cliente.")
            elif len(st.session_state.proyecto) == 0:
                st.warning("⚠️ No hay piezas.")
            else:
                db_manager.guardar_proyecto(st.session_state.nombre_cliente, st.session_state.proyecto, st.session_state.costo_total, st.session_state.anticipo)
                st.success(f"¡Guardado!")

        if proyectos_guardados:
            if st.button("🗑️ Borrar Seleccionado", use_container_width=True):
                db_manager.borrar_proyecto(seleccion)
                st.rerun()

    elif pin_ingresado != "":
        st.session_state['admin'] = False
        st.error("PIN incorrecto")
    elif pin_ingresado == "":
        st.session_state['admin'] = False

# ==========================================
# SECCIÓN 1: FORMULARIO (AGREGAR / EDITAR)
# ==========================================
col_logo1, col_logo2, col_logo3 = st.columns([1, 2, 1])
with col_logo2: st.image("logopagina.png", use_container_width=True)
st.write("---")

st.subheader("1. Configuración de Estructura")

sistema_seleccionado = st.radio("🛠️ Sistema de Manufactura:", ["Línea Nacional (Estándar)", "Línea Premium (Eurovent)"], horizontal=True)

is_editing = st.session_state.edit_index is not None

if is_editing:
    st.warning("✏️ Modo de edición activo")
    idx = st.session_state.edit_index
    pieza_actual = st.session_state.proyecto[idx]
    sistema_seleccionado = pieza_actual.get('sistema', "Línea Nacional (Estándar)")
    def_tipo, def_detalle = pieza_actual['tipo'], pieza_actual['detalle']
    def_ancho, def_alto = float(pieza_actual['ancho'] * 100), float(pieza_actual['alto'] * 100)
    def_diseno = pieza_actual.get('diseno', "2 hojas")
    def_cuadricula = pieza_actual.get('cuadricula', False)
    def_mosquitero = pieza_actual.get('mosquitero', False)
else:
    def_tipo = "Ventana Corrediza" if sistema_seleccionado == "Línea Nacional (Estándar)" else "Ventana Corrediza S50"
    def_detalle = "3 pulgadas" if sistema_seleccionado == "Línea Nacional (Estándar)" else "Eurovent S50"
    def_ancho, def_alto = 100.0, 210.0
    def_diseno, def_cuadricula, def_mosquitero = "2 hojas", False, False

col_tipo, col_detalle = st.columns(2)

if sistema_seleccionado == "Línea Nacional (Estándar)":
    tipos_disponibles = ["Ventana Corrediza", "Puerta", "Cancel de Baño"]
else:
    tipos_disponibles = ["Ventana Corrediza S50", "Ventana Corrediza S70", "Ventana Batiente S35", "Fijo S35", "Fijo S50", "Fijo S70"]

idx_tipo = tipos_disponibles.index(def_tipo) if def_tipo in tipos_disponibles else 0

with col_tipo:
    tipo_pieza = st.selectbox("Tipo de estructura:", tipos_disponibles, index=idx_tipo)

if sistema_seleccionado == "Línea Nacional (Estándar)":
    opciones_detalle = ["3 pulgadas", "2 pulgadas"] if tipo_pieza == "Ventana Corrediza" else ["Vivienda", "Baño"] if tipo_pieza == "Puerta" else ["Corredizo", "Abatible"]
else:
    if "S50" in tipo_pieza: opciones_detalle = ["Eurovent S50"]
    elif "S70" in tipo_pieza: opciones_detalle = ["Eurovent S70"]
    else: opciones_detalle = ["Eurovent S35"]

idx_det = opciones_detalle.index(def_detalle) if def_detalle in opciones_detalle else 0

with col_detalle:
    detalle_pieza = st.selectbox("Línea/Diseño:", opciones_detalle, index=idx_det)

mosquitero_pieza = False

if tipo_pieza in ["Ventana Corrediza", "Ventana Corrediza S50", "Ventana Corrediza S70"]:
    col_diseno, col_cuadricula = st.columns(2)
    
    if sistema_seleccionado == "Línea Nacional (Estándar)":
        opciones_diseno = ["2 hojas", "Fijo Gigante Centro", "3 hojas (1 Fija Ext, 2 Corr)"]
    else:
        opciones_diseno = ["2 hojas (X-X / O-X)", "3 hojas (X-O-X)", "4 hojas (O-X-X-O)"] 
        
    idx_diseno = opciones_diseno.index(def_diseno) if def_diseno in opciones_diseno else 0
    with col_diseno:
        diseno_pieza = st.selectbox("Estilo de Apertura:", opciones_diseno, index=idx_diseno)
    
    with col_cuadricula:
        if sistema_seleccionado == "Línea Nacional (Estándar)":
            st.write("")
            cuadricula_pieza = st.checkbox("Agregar intermedios (Cuadrícula)", value=def_cuadricula)
            if cuadricula_pieza:
                opciones_grid = ["2x2", "2x3", "3x2", "3x3", "3x4", "4x4"]
                valor_guardado = pieza_actual.get('tipo_cuadricula', "2x3") if is_editing else "2x3"
                idx_grid = opciones_grid.index(valor_guardado) if valor_guardado in opciones_grid else 1
                tipo_cuadricula_pieza = st.selectbox("Diseño (Columnas x Filas):", opciones_grid, index=idx_grid)
            else:
                tipo_cuadricula_pieza = "2x3" 
        else:
            cuadricula_pieza = False
            tipo_cuadricula_pieza = "2x3"

elif tipo_pieza == "Ventana Batiente S35":
    col_diseno, col_mosq = st.columns(2)
    opciones_diseno = ["1 hoja (Proyección)", "2 hojas (Batiente)"]
    idx_diseno = opciones_diseno.index(def_diseno) if def_diseno in opciones_diseno else 0
    with col_diseno:
        diseno_pieza = st.selectbox("Estilo de Apertura:", opciones_diseno, index=idx_diseno)
    with col_mosq:
        st.write("")
        mosquitero_pieza = st.checkbox("Agregar Mosquitero Fijo", value=def_mosquitero)
    cuadricula_pieza = False
    tipo_cuadricula_pieza = "2x3"
    
else:
    diseno_pieza = "Fijo"
    cuadricula_pieza = False
    tipo_cuadricula_pieza = "2x3"

col1, col2 = st.columns(2)
with col1: ancho_input_cm = st.number_input("Ancho (cm)", min_value=1.0, value=def_ancho, step=0.1, format="%.1f")
with col2: alto_input_cm = st.number_input("Alto (cm)", min_value=1.0, value=def_alto, step=0.1, format="%.1f")

col_btn1, col_btn2 = st.columns([2, 8])
with col_btn1:
    if is_editing:
        if st.button("💾 Guardar Cambios", type="primary"):
            st.session_state.proyecto[st.session_state.edit_index] = {
                "sistema": sistema_seleccionado, "tipo": tipo_pieza, "detalle": detalle_pieza, 
                "ancho": ancho_input_cm / 100.0, "alto": alto_input_cm / 100.0,
                "diseno": diseno_pieza, "cuadricula": cuadricula_pieza, "tipo_cuadricula": tipo_cuadricula_pieza,
                "mosquitero": mosquitero_pieza, "precio": pieza_actual.get('precio', 0.0)
            }
            st.session_state.edit_index = None
            st.rerun()
    else:
        if st.button("➕ Agregar al proyecto"):
            st.session_state.proyecto.append({
                "sistema": sistema_seleccionado, "tipo": tipo_pieza, "detalle": detalle_pieza, 
                "ancho": ancho_input_cm / 100.0, "alto": alto_input_cm / 100.0,
                "diseno": diseno_pieza, "cuadricula": cuadricula_pieza, "tipo_cuadricula": tipo_cuadricula_pieza,
                "mosquitero": mosquitero_pieza, "precio": 0.0
            })
            st.success(f"¡{tipo_pieza} agregada!")

with col_btn2:
    if is_editing and st.button("❌ Cancelar edición"):
        st.session_state.edit_index = None
        st.rerun()

st.write("---")

# ==========================================
# SECCIÓN 2: LISTA DEL CLIENTE
# ==========================================
with st.expander("📝 Piezas en el Proyecto", expanded=False):
    if len(st.session_state.proyecto) == 0:
        st.info("Aún no hay piezas agregadas.")
    else:
        for i, pieza in enumerate(st.session_state.proyecto):
            col_text, col_edit, col_del = st.columns([0.85, 0.075, 0.075])
            with col_text:
                txt_sys = "⭐️ Eurovent" if pieza.get('sistema') == "Línea Premium (Eurovent)" else "Nacional"
                txt_dis = f" - {pieza.get('diseno', '')}" if "Fijo" not in pieza['tipo'] else ""
                txt_mosq = " (Mosquitero)" if pieza.get('mosquitero', False) else ""
                st.markdown(f"**{i+1}. [{txt_sys}] {pieza['tipo']}**{txt_dis}{txt_mosq} - {round(pieza['ancho']*100, 1)} x {round(pieza['alto']*100, 1)} cm")
            with col_edit:
                if st.button("✏️", key=f"edit_{i}", type="tertiary"):
                    st.session_state.edit_index = i
                    st.rerun()
            with col_del:
                if st.button("🗑️", key=f"del_{i}", type="tertiary"):
                    st.session_state.proyecto.pop(i)
                    if st.session_state.edit_index == i: st.session_state.edit_index = None
                    st.rerun()

# ==========================================
# SECCIÓN 3: FINANZAS Y COTIZACIÓN AL CLIENTE (SÓLO ADMIN)
# ==========================================
if st.session_state.get('admin', False):
    st.write("---")
    st.subheader("💰 Finanzas y Cotización")
    total_proyecto = 0.0
    
    with st.expander("💵 Asignar precios individuales por pieza", expanded=False):
        col_presup, col_btn_dist = st.columns([3, 1])
        with col_presup:
            presupuesto_global = st.number_input("Presupuesto Total a repartir ($):", min_value=0.0, step=1000.0, value=0.0)
        with col_btn_dist:
            st.write("") 
            if st.button("Repartir Automático", use_container_width=True):
                area_total = sum([(p['ancho'] * p['alto']) for p in st.session_state.proyecto])
                if area_total > 0 and presupuesto_global > 0:
                    precio_por_m2 = presupuesto_global / area_total
                    for i in range(len(st.session_state.proyecto)):
                        area_pieza = st.session_state.proyecto[i]['ancho'] * st.session_state.proyecto[i]['alto']
                        st.session_state.proyecto[i]['precio'] = float(round(area_pieza * precio_por_m2))
                    st.rerun()
        
        st.write("---")
        for i, pieza in enumerate(st.session_state.proyecto):
            col_texto, col_precio = st.columns([3, 1])
            with col_texto:
                area = pieza['ancho'] * pieza['alto']
                st.markdown(f"<br>**P{i+1}:** {pieza['tipo']} ({round(pieza['ancho']*100, 1)}x{round(pieza['alto']*100, 1)}cm) - *{round(area, 2)} m²*", unsafe_allow_html=True)
            with col_precio:
                precio_actual = pieza.get('precio', 0.0)
                precio_pieza = st.number_input("Precio ($)", min_value=0.0, step=100.0, value=float(precio_actual), format="%.2f", key=f"precio_{i}")
                st.session_state.proyecto[i]['precio'] = precio_pieza
                total_proyecto += precio_pieza
    
    st.session_state.costo_total = total_proyecto
    st.write("")
    
    col_total, col_sugerido = st.columns(2)
    with col_total: st.metric("Total Cotizado:", f"${total_proyecto:,.2f}")
    with col_sugerido: st.metric("Anticipo Sugerido (50%):", f"${(total_proyecto / 2):,.2f}")
        
    st.write("")
    col_anticipo, col_restante = st.columns(2)
    valor_protegido = float(st.session_state.get('anticipo', 0.0))
    with col_anticipo:
        st.session_state.anticipo = st.number_input("Anticipo entregado ($)", min_value=0.0, step=100.0, value=valor_protegido, disabled=(valor_protegido > 0))
    with col_restante:
        st.metric("Saldo Pendiente:", f"${(total_proyecto - st.session_state.anticipo):,.2f}")

    if st.button("📄 Generar Recibo (PDF)", type="primary", use_container_width=True):
        try:
            from fpdf import FPDF
            import base64
            pdf = FPDF()
            pdf.add_page()
            try: pdf.image("logopagina.png", x=10, y=8, w=54)
            except: pass 
            pdf.set_font("Arial", 'B', 16)
            pdf.cell(0, 10, "Cotizacion de Proyecto", ln=True, align='R')
            pdf.set_font("Arial", '', 12)
            pdf.cell(0, 10, f"Fecha: {datetime.now().strftime('%d/%m/%Y')}", ln=True, align='R')
            pdf.ln(15) 
            pdf.set_font("Arial", 'B', 12)
            pdf.cell(0, 10, f"Cliente: {st.session_state.nombre_cliente}", ln=True)
            pdf.ln(5)
            pdf.set_font("Arial", '', 10)
            for i, p in enumerate(st.session_state.proyecto):
                texto = f"P{i+1}: {p['tipo']} ({round(p['ancho']*100,1)} x {round(p['alto']*100,1)} cm)"
                pdf.cell(140, 8, texto, border=1)
                pdf.cell(50, 8, f"${p.get('precio', 0.0):,.2f}", border=1, ln=True, align='R')
            pdf.ln(5)
            pdf.set_font("Arial", 'B', 11)
            pdf.cell(140, 8, "Total Cotizado:", border=0, align='R')
            pdf.cell(50, 8, f"${st.session_state.costo_total:,.2f}", border=1, ln=True, align='R')
            pdf.cell(140, 8, "Anticipo:", border=0, align='R')
            pdf.cell(50, 8, f"${st.session_state.anticipo:,.2f}", border=1, ln=True, align='R')
            pdf.cell(140, 8, "Saldo Pendiente:", border=0, align='R')
            pdf.cell(50, 8, f"${(st.session_state.costo_total - st.session_state.anticipo):,.2f}", border=1, ln=True, align='R')

            pdf_bytes = pdf.output(dest='S').encode('latin-1')
            b64 = base64.b64encode(pdf_bytes).decode()
            with st.expander("👁️ Previsualizar Recibo", expanded=True):
                st.markdown(f'<embed src="data:application/pdf;base64,{b64}" width="100%" height="450" type="application/pdf">', unsafe_allow_html=True)
            st.markdown(f'<a href="data:application/pdf;base64,{b64}" download="Cotizacion_CASTFER.pdf" target="_blank" style="text-decoration: none; padding: 10px; background-color: #ff4b4b; color: white; border-radius: 5px; display: inline-block; text-align: center; width: 100%;">📥 Descargar Recibo</a>', unsafe_allow_html=True)
        except Exception as e: st.error("⚠️ Error generando PDF.")

# ==========================================
# SECCIÓN 4: PRODUCCIÓN DE TALLER (ACCESIBLE)
# ==========================================
st.write("---")
st.subheader("🚧 Producción de Taller")

usar_fases = st.checkbox("Activar fabricación parcial (Fases)")
indices_activos = []

if usar_fases:
    for i, pieza in enumerate(st.session_state.proyecto):
        if st.checkbox(f"Fabricar HOY - P{i+1}: {pieza['tipo']} ({round(pieza['ancho']*100,1)}x{round(pieza['alto']*100,1)}cm)", value=True):
            indices_activos.append(i)
else:
    indices_activos = list(range(len(st.session_state.proyecto)))

col_prov1, col_prov2 = st.columns([1, 1])

# =============== LISTA PROVEEDOR ===============
with col_prov1:
    if st.button("🛒 Lista Material Proveedor (PDF)", type="secondary", use_container_width=True):
        try:
            from fpdf import FPDF
            import base64
            
            totales = {"jaladera": 0, "carretilla": 0, "vinil": 0.0}
            cortes_chambrana, cortes_riel, cortes_cerco, cortes_traslape, cortes_cabezal, cortes_zoclo, cortes_intermedio, cortes_mosquitero = [], [], [], [], [], [], [], []
            todos_los_vidrios_prov = []
            lista_medidas = []

            def agregar_cortes_prov(lista, medidas, etiqueta, es_activo):
                for m in medidas: lista.append({"medida": m, "etiqueta": etiqueta, "activo": es_activo})

            for i, p in enumerate(st.session_state.proyecto):
                es_activo = i in indices_activos
                num_pieza = i + 1
                sys = p.get('sistema', "Línea Nacional (Estándar)")
                
                if es_activo: lista_medidas.append(f"P{num_pieza}: {round(p['ancho']*100,1)}x{round(p['alto']*100,1)}cm")

                if sys == "Línea Premium (Eurovent)":
                    if p['tipo'] in ["Ventana Corrediza S50", "Ventana Corrediza S70"]:
                        d_str = p.get('diseno', "2 hojas")
                        if "3 hojas" in d_str: num_hojas = 3
                        elif "4 hojas" in d_str: num_hojas = 4
                        else: num_hojas = 2
                        
                        if es_activo:
                            totales["jaladera"] += (2 if num_hojas >= 3 else 1)
                            totales["carretilla"] += (num_hojas * 2)
                            totales["vinil"] += ((p['ancho'] + p['alto']) * 2) * 100 
                        
                        if p['tipo'] == "Ventana Corrediza S50":
                            v = VentanaEuroventS50(p['ancho'], p['alto'], diseno=d_str)
                        else:
                            v = VentanaEuroventS70(p['ancho'], p['alto'], diseno=d_str)
                            
                        riel, jamba = v.calcular_cortes_marco()
                        cerco, zoclo = v.calcular_hojas()
                        
                        agregar_cortes_prov(cortes_chambrana, [round(jamba*100, 1), round(jamba*100, 1)], f"L(Jam)-P{num_pieza}", es_activo)
                        agregar_cortes_prov(cortes_riel, [round(riel*100, 1), round(riel*100, 1)], f"C(Riel)-P{num_pieza}", es_activo)
                        agregar_cortes_prov(cortes_cerco, [round(cerco*100, 1)]*num_hojas, f"Cerco-P{num_pieza}", es_activo)
                        agregar_cortes_prov(cortes_traslape, [round(cerco*100, 1)]*num_hojas, f"Trasl-P{num_pieza}", es_activo)
                        agregar_cortes_prov(cortes_zoclo, [round(zoclo*100, 1)]*(num_hojas*2), f"Zoclo-P{num_pieza}", es_activo)
                        
                        a_v, alt_v, _ = v.calcular_vidrio()
                        for _ in range(num_hojas):
                            todos_los_vidrios_prov.append({"medida": f"{round(a_v*100, 1)} x {round(alt_v*100, 1)}", "etiqueta": f"P{num_pieza}", "activo": es_activo})
                    
                    elif "Fijo" in p['tipo']:
                        if es_activo: totales["vinil"] += ((p['ancho'] + p['alto']) * 2) * 100
                        v = FijoEurovent(p['ancho'], p['alto'])
                        bolsa_v, bolsa_h = v.calcular_cortes()
                        
                        agregar_cortes_prov(cortes_chambrana, [round(bolsa_v*100, 1), round(bolsa_v*100, 1)], f"L(Bols)-P{num_pieza}", es_activo)
                        agregar_cortes_prov(cortes_riel, [round(bolsa_h*100, 1)], f"C(Bols)-P{num_pieza}", es_activo)
                        agregar_cortes_prov(cortes_zoclo, [round(bolsa_h*100, 1)], f"C(Escal)-P{num_pieza}", es_activo)
                        
                        a_v, alt_v, _ = v.calcular_vidrio()
                        todos_los_vidrios_prov.append({"medida": f"{round(a_v*100, 1)} x {round(alt_v*100, 1)}", "etiqueta": f"P{num_pieza}", "activo": es_activo})

                    elif p['tipo'] == "Ventana Batiente S35":
                        if es_activo: totales["vinil"] += ((p['ancho'] + p['alto']) * 4) * 100
                        v = VentanaProyeccionBatienteEuroventS35(p['ancho'], p['alto'], diseno=p.get('diseno', "1 hoja"), mosquitero=p.get('mosquitero', False))
                        cm_w, cm_h = v.calcular_cortes_marco()
                        c_alto, c_ancho, inter = v.calcular_hojas()
                        m_alto, m_ancho = v.calcular_mosquitero()
                        
                        agregar_cortes_prov(cortes_chambrana, [round(cm_w*100, 1)]*2 + [round(cm_h*100, 1)]*2, f"Contramarco-P{num_pieza}", es_activo)
                        
                        hojas_totales = 2 if "2 hojas" in p.get('diseno', '') else 1
                        agregar_cortes_prov(cortes_cerco, [round(c_alto*100, 1)]*(2*hojas_totales), f"Marco(V)-P{num_pieza}", es_activo)
                        agregar_cortes_prov(cortes_cabezal, [round(c_ancho*100, 1)]*(2*hojas_totales), f"Marco(H)-P{num_pieza}", es_activo)
                        
                        if inter > 0: agregar_cortes_prov(cortes_intermedio, [round(inter*100, 1)], f"Interm-P{num_pieza}", es_activo)
                        
                        if p.get('mosquitero', False):
                            num_mosq = 2 if "2 hojas" in p.get('diseno', '') else 1
                            agregar_cortes_prov(cortes_mosquitero, [round(m_alto*100, 1)]*(2*num_mosq) + [round(m_ancho*100, 1)]*(2*num_mosq), f"Mosq-P{num_pieza}", es_activo)
                            
                        a_v, alt_v, _ = v.calcular_vidrio()
                        for _ in range(hojas_totales): todos_los_vidrios_prov.append({"medida": f"{round(a_v*100, 1)} x {round(alt_v*100, 1)}", "etiqueta": f"P{num_pieza}", "activo": es_activo})

                elif p['tipo'] == "Ventana Corrediza":
                    diseno = p.get('diseno', "2 hojas")
                    cuadricula = p.get('cuadricula', False)
                    t_cuad = p.get('tipo_cuadricula', "2x3")
                    if es_activo:
                        if diseno == "Fijo Gigante Centro" or "3 hojas" in diseno:
                            totales["jaladera"] += 2; totales["carretilla"] += 4
                        else:
                            totales["jaladera"] += 1; totales["carretilla"] += 2
                    
                    v = Ventana(p['ancho'], p['alto'], p['detalle'], "Blanco", diseno=diseno, cuadricula=cuadricula, tipo_cuadricula=t_cuad)
                    a_m, alt_l = v.calcular_cortes_marco()
                    hojas = v.calcular_hojas()
                    
                    agregar_cortes_prov(cortes_chambrana, [round(a_m*100, 1)], f"C-P{num_pieza}", es_activo)
                    agregar_cortes_prov(cortes_chambrana, [round(alt_l*100, 1), round(alt_l*100, 1)], f"L-P{num_pieza}", es_activo)
                    
                    if "3 hojas" in diseno: agregar_cortes_prov(cortes_riel, [round(a_m*100, 1), round(a_m*100, 1)], f"P{num_pieza}", es_activo)
                    else: agregar_cortes_prov(cortes_riel, [round(a_m*100, 1)], f"P{num_pieza}", es_activo)
                    
                    def prov_hoja(alto_h, ancho_h, es_gigante):
                        agregar_cortes_prov(cortes_cabezal, [round(ancho_h*100, 1)], f"P{num_pieza}", es_activo)
                        agregar_cortes_prov(cortes_zoclo, [round(ancho_h*100, 1)], f"P{num_pieza}", es_activo)
                        if es_gigante: agregar_cortes_prov(cortes_cerco, [round(alto_h*100, 1)] * 2, f"P{num_pieza}", es_activo)
                        else:
                            agregar_cortes_prov(cortes_cerco, [round(alto_h*100, 1)], f"P{num_pieza}", es_activo)
                            agregar_cortes_prov(cortes_traslape, [round(alto_h*100, 1)], f"P{num_pieza}", es_activo)
                            
                        luz_ancho = (ancho_h * 100) - 10.0
                        luz_alto = (alto_h * 100) - 9.0
                        
                        if cuadricula:
                            ints = v.calcular_intermedios_aluminio(alto_h, ancho_h, es_gigante)
                            if ints["verticales"]: agregar_cortes_prov(cortes_intermedio, [round(x*100, 1) for x in ints["verticales"]], f"Vert-P{num_pieza}", es_activo)
                            if ints["horizontales"]: agregar_cortes_prov(cortes_intermedio, [round(x*100, 1) for x in ints["horizontales"]], f"Horz-P{num_pieza}", es_activo)
                            
                            alto_int = alto_h - v.perfil_cabezal - v.perfil_zoclo
                            ancho_int = ancho_h - (v.perfil_cerco_traslape * 2)
                            filas = v.filas_hoja
                            cols = v.cols_hoja * 2 if es_gigante else v.cols_hoja
                            alto_v = ((alto_int - (filas - 1) * v.intermedio_frente) / filas) + (v.holgura_vidrio * 2)
                            ancho_v = ((ancho_int - (cols - 1) * v.intermedio_frente) / cols) + (v.holgura_vidrio * 2)
                            
                            if es_activo: totales["vinil"] += ((ancho_v*100) + (alto_v*100)) * 2 * (filas * cols)
                            for _ in range(filas * cols): todos_los_vidrios_prov.append({"medida": f"{round(ancho_v*100, 1)} x {round(alto_v*100, 1)}", "etiqueta": f"P{num_pieza}", "activo": es_activo})
                        else:
                            if es_activo: totales["vinil"] += (luz_ancho + luz_alto) * 2
                            a_v, alt_v, _ = v.calcular_vidrio(alto_h, ancho_h)
                            todos_los_vidrios_prov.append({"medida": f"{round(a_v*100, 1)} x {round(alt_v*100, 1)}", "etiqueta": f"P{num_pieza}", "activo": es_activo})
                            
                    if diseno == "2 hojas":
                        prov_hoja(hojas["fija"][0], hojas["fija"][1], False)
                        prov_hoja(hojas["corrediza"][0], hojas["corrediza"][1], False)
                    elif diseno == "Fijo Gigante Centro":
                        prov_hoja(hojas["fija_gigante"][0], hojas["fija_gigante"][1], True)
                        prov_hoja(hojas["corrediza_izq"][0], hojas["corrediza_izq"][1], False)
                        prov_hoja(hojas["corrediza_der"][0], hojas["corrediza_der"][1], False)
                    elif "3 hojas" in diseno:
                        prov_hoja(hojas["fija_ext"][0], hojas["fija_ext"][1], False)
                        prov_hoja(hojas["corr_normal"][0], hojas["corr_normal"][1], False)
                        prov_hoja(hojas["corr_doble"][0], hojas["corr_doble"][1], False)
                        
                elif p['tipo'] == "Puerta":
                    puerta = Puerta(p['ancho'], p['alto'], p['detalle'], "Blanco")
                    ancho_r, alto_r, cant_duelas = puerta.calcular_relleno()
                    todos_los_vidrios_prov.append({"medida": f"{round(ancho_r*100, 1)} x {round(alto_r*100, 1)}", "etiqueta": f"P{num_pieza}", "activo": es_activo})

            def calcular_tramos_a_comprar(cortes):
                if not cortes: return 0
                tramos, _ = optimizador_aluminio_taller(cortes, "")
                return sum(1 for t in tramos if any(c['activo'] for c in t))

            pdf = FPDF()
            pdf.add_page()
            try: pdf.image("logopagina.png", x=10, y=8, w=54)
            except: pass 
            pdf.set_font("Arial", 'B', 16)
            pdf.cell(0, 8, "ORDEN DE COMPRA PARA PROVEEDOR", ln=True, align='R')
            pdf.set_font("Arial", '', 11)
            pdf.cell(0, 6, f"Fecha: {datetime.now().strftime('%d/%m/%Y')}", ln=True, align='R')
            pdf.cell(0, 6, f"Cliente: {st.session_state.nombre_cliente}", ln=True, align='R')
            pdf.ln(8)
            pdf.line(10, pdf.get_y(), 200, pdf.get_y())
            pdf.ln(5)

            pdf.set_font("Arial", 'B', 12)
            pdf.set_fill_color(235, 235, 235)
            pdf.cell(0, 8, " 1. PERFILES A COMPRAR HOY (Tiras de 6 metros)", ln=True, fill=True)
            pdf.ln(4)
            pdf.set_font("Arial", '', 11)
            
            pdf.cell(0, 8, f"[   ]   {calcular_tramos_a_comprar(cortes_chambrana)} Jambas / Bolsas / Contramarcos (6m)", ln=True)
            pdf.cell(0, 8, f"[   ]   {calcular_tramos_a_comprar(cortes_riel)} Riel-Cabezal / Rieles (6m)", ln=True)
            pdf.cell(0, 8, f"[   ]   {calcular_tramos_a_comprar(cortes_cerco)} Cercos / Marco Hoja V. (6m)", ln=True)
            pdf.cell(0, 8, f"[   ]   {calcular_tramos_a_comprar(cortes_traslape)} Traslapes (6m)", ln=True)
            pdf.cell(0, 8, f"[   ]   {calcular_tramos_a_comprar(cortes_cabezal)} Cabezales de hoja / Marco Hoja H. (6m)", ln=True)
            pdf.cell(0, 8, f"[   ]   {calcular_tramos_a_comprar(cortes_zoclo)} Zoclos / Escalonados (6m)", ln=True)
            pdf.cell(0, 8, f"[   ]   {calcular_tramos_a_comprar(cortes_intermedio)} Intermedios (6m)", ln=True)
            if cortes_mosquitero: pdf.cell(0, 8, f"[   ]   {calcular_tramos_a_comprar(cortes_mosquitero)} Perfiles para Mosquitero Fijo (6m)", ln=True)
            pdf.ln(4)

            pdf.set_font("Arial", 'B', 12)
            pdf.cell(0, 8, " 2. HERRAJES Y ACCESORIOS (Para fase actual)", ln=True, fill=True)
            pdf.ln(4)
            pdf.set_font("Arial", '', 11)
            if totales["jaladera"] > 0:
                pdf.cell(0, 8, f"[   ]   {totales['jaladera']} Cierres Embutidos / Jaladeras", ln=True)
                pdf.cell(0, 8, f"[   ]   {totales['carretilla']} Carretillas", ln=True)
                botes = max(1, math.ceil(totales['vinil'] / 1000.0)) 
                pdf.cell(0, 8, f"[   ]   {botes} Botes de Sellador", ln=True)
                pdf.cell(0, 8, f"[   ]   {math.ceil(totales['vinil'] / 100.0)} Metros lineales de Vinil / Empaque", ln=True)
            
            pdf.ln(6)
            pdf.set_font("Arial", 'B', 12)
            pdf.cell(0, 8, " 3. CRISTAL A COMPRAR HOY (Hojas 260cm)", ln=True, fill=True)
            pdf.ln(4)
            pdf.set_font("Arial", '', 11)
            if todos_los_vidrios_prov:
                hojas_vidrio_comprar, _, config = optimizador_vidrio(todos_los_vidrios_prov, "")
                hojas_activas = sum(1 for h in hojas_vidrio_comprar if any(p['activo'] for col in h['columnas'] for p in col['piezas']))
                txt_red = " (Reduccion 0.5cm)" if config['reducido'] else " (Medida exacta)"
                pdf.cell(0, 8, f"[   ]   {hojas_activas} Hoja(s) de {int(config['ancho'])}x260 cm{txt_red}", ln=True)
            else:
                pdf.cell(0, 8, "No se requiere cristal en esta fase.", ln=True)

            pdf.ln(6)
            pdf.set_font("Arial", 'B', 12)
            pdf.cell(0, 8, " 4. RESUMEN DE PIEZAS ACTIVAS", ln=True, fill=True)
            pdf.ln(4)
            pdf.set_font("Arial", '', 10)
            if lista_medidas: pdf.multi_cell(0, 6, "   |   ".join(lista_medidas))

            pdf_bytes = pdf.output(dest='S').encode('latin-1')
            b64 = base64.b64encode(pdf_bytes).decode()
            with st.expander("👁️ Previsualizar Lista", expanded=True):
                st.markdown(f'<embed src="data:application/pdf;base64,{b64}" width="100%" height="450" type="application/pdf">', unsafe_allow_html=True)
            st.markdown(f'<a href="data:application/pdf;base64,{b64}" download="Compras_CASTFER.pdf" target="_blank" style="text-decoration: none; padding: 10px; background-color: #6c757d; color: white; border-radius: 5px; display: inline-block; text-align: center; width: 100%;">🛒 Descargar PDF de Compras</a>', unsafe_allow_html=True)
        except Exception as e: st.error(f"⚠️ Error generando PDF: {e}")

# =============== GUÍA DE CORTES PDF ===============
with col_prov2:
    st.write("")
    with st.expander("♻️ ¿Pedacería? (Opcional)"):
        col_p1, col_p2, col_p3 = st.columns(3)
        with col_p1:
            ped_chambrana = st.text_input("Recortes Jambas/Chambranas:", "")
            ped_cerco = st.text_input("Recortes Cercos:", "")
        with col_p2:
            ped_riel = st.text_input("Recortes Rieles:", "")
            ped_traslape = st.text_input("Recortes Traslapes:", "")
            ped_intermedio = st.text_input("Recortes Int / Mosq:", "")
        with col_p3:
            ped_cabezal = st.text_input("Recortes Cabezales de Hoja:", "")
            ped_zoclo = st.text_input("Recortes Zóclos/Escalonados:", "")
            ped_vidrio = st.text_input("Recortes Vidrio:", "")

if st.button("✂️ Generar Guía de Cortes para Taller (PDF)", type="primary", use_container_width=True):
    try:
        from fpdf import FPDF
        import base64
        
        cortes_chambrana, cortes_riel, cortes_cerco, cortes_traslape, cortes_cabezal, cortes_zoclo, cortes_intermedio, cortes_mosquitero = [], [], [], [], [], [], [], []
        todos_los_vidrios_taller = []

        def agregar_cortes_taller(lista, medidas, etiqueta, es_activo):
            for m in medidas: lista.append({"medida": m, "etiqueta": etiqueta, "activo": es_activo})
        
        for i, p in enumerate(st.session_state.proyecto):
            es_activo = i in indices_activos
            num_pieza = i + 1  
            sys = p.get('sistema', "Línea Nacional (Estándar)")

            # ------- LÓGICA EUROVENT PREMIUM -------
            if sys == "Línea Premium (Eurovent)":
                if p['tipo'] in ["Ventana Corrediza S50", "Ventana Corrediza S70"]:
                    d_str = p.get('diseno', "2 hojas")
                    if "3 hojas" in d_str: num_hojas = 3
                    elif "4 hojas" in d_str: num_hojas = 4
                    else: num_hojas = 2
                    
                    if p['tipo'] == "Ventana Corrediza S50":
                        v = VentanaEuroventS50(p['ancho'], p['alto'], diseno=d_str)
                    else:
                        v = VentanaEuroventS70(p['ancho'], p['alto'], diseno=d_str)
                        
                    riel, jamba = v.calcular_cortes_marco()
                    cerco, zoclo = v.calcular_hojas()
                    
                    agregar_cortes_taller(cortes_chambrana, [round(jamba*100, 1), round(jamba*100, 1)], f"L(Jam)-P{num_pieza}", es_activo)
                    agregar_cortes_taller(cortes_riel, [round(riel*100, 1), round(riel*100, 1)], f"C(Riel)-P{num_pieza}", es_activo)
                    agregar_cortes_taller(cortes_cerco, [round(cerco*100, 1)]*num_hojas, f"Cerco-P{num_pieza}", es_activo)
                    agregar_cortes_taller(cortes_traslape, [round(cerco*100, 1)]*num_hojas, f"Trasl-P{num_pieza}", es_activo)
                    agregar_cortes_taller(cortes_zoclo, [round(zoclo*100, 1)]*(num_hojas*2), f"Zoclo-P{num_pieza}", es_activo)
                    
                    a_v, alt_v, _ = v.calcular_vidrio()
                    for _ in range(num_hojas):
                        todos_los_vidrios_taller.append({"medida": f"{round(a_v*100, 1)} x {round(alt_v*100, 1)}", "etiqueta": f"P{num_pieza}", "activo": es_activo})
                
                elif "Fijo" in p['tipo']:
                    v = FijoEurovent(p['ancho'], p['alto'])
                    bolsa_v, bolsa_h = v.calcular_cortes()
                    
                    agregar_cortes_taller(cortes_chambrana, [round(bolsa_v*100, 1), round(bolsa_v*100, 1)], f"L(Bols)-P{num_pieza}", es_activo)
                    agregar_cortes_taller(cortes_riel, [round(bolsa_h*100, 1)], f"C(Bols)-P{num_pieza}", es_activo)
                    agregar_cortes_taller(cortes_zoclo, [round(bolsa_h*100, 1)], f"C(Escal)-P{num_pieza}", es_activo)
                    
                    a_v, alt_v, _ = v.calcular_vidrio()
                    todos_los_vidrios_taller.append({"medida": f"{round(a_v*100, 1)} x {round(alt_v*100, 1)}", "etiqueta": f"P{num_pieza}", "activo": es_activo})

                elif p['tipo'] == "Ventana Batiente S35":
                    v = VentanaProyeccionBatienteEuroventS35(p['ancho'], p['alto'], diseno=p.get('diseno', "1 hoja"), mosquitero=p.get('mosquitero', False))
                    cm_w, cm_h = v.calcular_cortes_marco()
                    c_alto, c_ancho, inter = v.calcular_hojas()
                    m_alto, m_ancho = v.calcular_mosquitero()
                    
                    agregar_cortes_taller(cortes_chambrana, [round(cm_w*100, 1)]*2 + [round(cm_h*100, 1)]*2, f"Contramarco-P{num_pieza}", es_activo)
                    
                    hojas_totales = 2 if "2 hojas" in p.get('diseno', '') else 1
                    agregar_cortes_taller(cortes_cerco, [round(c_alto*100, 1)]*(2*hojas_totales), f"Marco(V)-P{num_pieza}", es_activo)
                    agregar_cortes_taller(cortes_cabezal, [round(c_ancho*100, 1)]*(2*hojas_totales), f"Marco(H)-P{num_pieza}", es_activo)
                    
                    if inter > 0: agregar_cortes_taller(cortes_intermedio, [round(inter*100, 1)], f"Interm-P{num_pieza}", es_activo)
                    
                    if p.get('mosquitero', False):
                        num_mosq = 2 if "2 hojas" in p.get('diseno', '') else 1
                        agregar_cortes_taller(cortes_mosquitero, [round(m_alto*100, 1)]*(2*num_mosq) + [round(m_ancho*100, 1)]*(2*num_mosq), f"Mosq-P{num_pieza}", es_activo)
                        
                    a_v, alt_v, _ = v.calcular_vidrio()
                    for _ in range(hojas_totales):
                        todos_los_vidrios_taller.append({"medida": f"{round(a_v*100, 1)} x {round(alt_v*100, 1)}", "etiqueta": f"P{num_pieza}", "activo": es_activo})

            # ------- LÓGICA NACIONAL ESTÁNDAR -------
            elif p['tipo'] == "Ventana Corrediza":
                v = Ventana(p['ancho'], p['alto'], p['detalle'], "Blanco", diseno=p.get('diseno', '2 hojas'))
                a_m, alt_l = v.calcular_cortes_marco()
                hojas = v.calcular_hojas()
                
                agregar_cortes_taller(cortes_chambrana, [round(a_m*100, 1)], f"C-P{num_pieza}", es_activo)
                agregar_cortes_taller(cortes_chambrana, [round(alt_l*100, 1), round(alt_l*100, 1)], f"L-P{num_pieza}", es_activo)
                agregar_cortes_taller(cortes_riel, [round(a_m*100, 1)] * (2 if "3 hojas" in p.get('diseno','') else 1), f"P{num_pieza}", es_activo)
                
                def armar_hoja(lbl, h_dim):
                    agregar_cortes_taller(cortes_cabezal, [round(h_dim[1]*100, 1)], lbl, es_activo)
                    agregar_cortes_taller(cortes_zoclo, [round(h_dim[1]*100, 1)], lbl, es_activo)
                    agregar_cortes_taller(cortes_cerco, [round(h_dim[0]*100, 1)], lbl, es_activo)
                    agregar_cortes_taller(cortes_traslape, [round(h_dim[0]*100, 1)], lbl, es_activo)
                    a_v, alt_v, _ = v.calcular_vidrio(h_dim[0], h_dim[1])
                    todos_los_vidrios_taller.append({"medida": f"{round(a_v*100, 1)} x {round(alt_v*100, 1)}", "etiqueta": lbl, "activo": es_activo})

                if p.get('diseno') == "2 hojas":
                    armar_hoja(f"Fija-P{num_pieza}", hojas["fija"])
                    armar_hoja(f"Corr-P{num_pieza}", hojas["corrediza"])
                elif "3 hojas" in p.get('diseno',''):
                    armar_hoja(f"FijExt-P{num_pieza}", hojas["fija_ext"])
                    armar_hoja(f"CorNrm-P{num_pieza}", hojas["corr_normal"])
                    armar_hoja(f"CorDbl-P{num_pieza}", hojas["corr_doble"])

        pdf = FPDF()
        pdf.add_page()
        try: pdf.image("logopagina.png", x=10, y=8, w=54)
        except: pass 
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(0, 10, "GUIA DE CORTES - MESA DE TRABAJO", ln=True, align='R')
        pdf.set_font("Arial", '', 11)
        pdf.cell(0, 6, f"Cliente: {st.session_state.nombre_cliente}", ln=True, align='R')
        pdf.ln(10)

        def pdf_imprimir_perfil(titulo, lista_cortes, ped_str):
            if not lista_cortes: return
            tramos, ped_usada = optimizador_aluminio_taller(lista_cortes, ped_str)
            if not any(c.get('activo', True) for c in lista_cortes): return
            pdf.set_font("Arial", 'B', 11)
            pdf.set_fill_color(220, 220, 220)
            pdf.cell(0, 8, f" {titulo.upper()}", ln=True, fill=True)
            pdf.set_font("Arial", '', 10)
            
            for p_idx, p_data in ped_usada.items():
                activos = [u for u in p_data["usados"] if u.get('activo', True)]
                pendientes = [u for u in p_data["usados"] if not u.get('activo', True)]
                if not activos: continue
                usados_act = ", ".join([f"{u['medida']}cm ({u['etiqueta']})" for u in activos])
                usados_pend = ", ".join([f"{u['medida']}cm ({u['etiqueta']})" for u in pendientes])
                sobra = p_data["tamano"] - (sum([u['medida'] for u in p_data["usados"]]) + len(p_data["usados"])*0.3)
                texto = f"  * De retazo de {p_data['tamano']}cm:\n      -> CORTA HOY: {usados_act}\n" if usar_fases else f"  * De retazo de {p_data['tamano']}cm:\n      Corta: {usados_act}\n"
                if usar_fases and usados_pend: texto += f"      -> GUARDA (Futuro): {usados_pend}\n"
                texto += f"      -> Sobrante: {round(sobra,1)}cm"
                pdf.multi_cell(0, 6, texto)
                pdf.ln(1)
            
            for i, tramo in enumerate(tramos):
                activos = [u for u in tramo if u.get('activo', True)]
                pendientes = [u for u in tramo if not u.get('activo', True)]
                if not activos: continue
                usados_act = ", ".join([f"{u['medida']}cm ({u['etiqueta']})" for u in activos])
                usados_pend = ", ".join([f"{u['medida']}cm ({u['etiqueta']})" for u in pendientes])
                sobra = 600.0 - (sum([u['medida'] for u in tramo]) + len(tramo)*0.3)
                texto = f"  * Tramo {i+1} (6.00m):\n      -> CORTA HOY: {usados_act}\n" if usar_fases else f"  * Tramo {i+1} (6.00m):\n      Corta: {usados_act}\n"
                if usar_fases and usados_pend: texto += f"      -> GUARDA (Futuro): {usados_pend}\n"
                texto += f"      -> Sobrante: {round(sobra,1)}cm"
                pdf.multi_cell(0, 6, texto)
                pdf.ln(1)

        pdf_imprimir_perfil("Jambas / Bolsas / Contramarcos", cortes_chambrana, ped_chambrana)
        pdf_imprimir_perfil("Rieles / Intermedios", cortes_riel + cortes_intermedio, ped_intermedio)
        pdf_imprimir_perfil("Cercos / Marco Hoja Vertical", cortes_cerco, ped_cerco)
        pdf_imprimir_perfil("Traslapes", cortes_traslape, ped_traslape)
        pdf_imprimir_perfil("Cabezales / Marco Hoja Horizontal", cortes_cabezal, ped_cabezal)
        pdf_imprimir_perfil("Zoclos / Escalonados", cortes_zoclo, ped_cabezal)
        pdf_imprimir_perfil("Perfiles Mosquitero", cortes_mosquitero, ped_intermedio)

        pdf.ln(5)
        pdf.set_font("Arial", 'B', 12)
        pdf.set_fill_color(200, 220, 255)
        pdf.cell(0, 8, " MESA DE CRISTAL / VIDRIO", ln=True, fill=True)
        pdf.ln(4)
        
        if todos_los_vidrios_taller:
            hojas_vidrio, vidrios_rescatados, best_config = optimizador_vidrio(todos_los_vidrios_taller, ped_vidrio)
            
            if any(r['pieza'].get('activo', True) for r in vidrios_rescatados):
                pdf.set_font("Arial", 'B', 10)
                pdf.cell(0, 6, "RECORTES DEL TALLER:", ln=True)
                pdf.set_font("Arial", '', 10)
                for r in vidrios_rescatados:
                    if r["pieza"].get('activo', True) or not usar_fases:
                        pdf.cell(0, 6, f"  - Del retazo {r['pedazo']['original']}: Cortar {r['pieza']['w']} x {r['pieza']['h']} cm ({r['pieza']['etiqueta']})", ln=True)
                pdf.ln(3)

            if hojas_vidrio:
                pdf.set_font("Arial", 'B', 11)
                pdf.cell(0, 8, f"HOJAS NUEVAS ({int(best_config['ancho'])}x260 cm):", ln=True)
                pdf.set_font("Arial", '', 10)
                for i, h in enumerate(hojas_vidrio):
                    if not any(p.get('activo', True) for col in h['columnas'] for p in col['piezas']): continue
                    pdf.set_font("Arial", 'B', 10)
                    pdf.cell(0, 6, f" >> HOJA {i+1}:", ln=True)
                    pdf.set_font("Arial", '', 10)
                    for j, col in enumerate(h['columnas']):
                        for p in col['piezas']:
                            txt_act = " [CORTA HOY]" if usar_fases and p.get('activo') else " [GUARDA]" if usar_fases else ""
                            pdf.cell(0, 6, f"      [ ] {p['w']} x {p['h']} cm   (Mrc: {p['etiqueta']}){txt_act}", ln=True)
                    pdf.ln(2)

        pdf_bytes = pdf.output(dest='S').encode('latin-1')
        b64 = base64.b64encode(pdf_bytes).decode()
        with st.expander("👁️ Previsualizar Guía", expanded=True):
            st.markdown(f'<embed src="data:application/pdf;base64,{b64}" width="100%" height="700" type="application/pdf">', unsafe_allow_html=True)
        st.markdown(f'<a href="data:application/pdf;base64,{b64}" download="Guia_Cortes.pdf" target="_blank" style="text-decoration: none; padding: 12px; background-color: #007bff; color: white; border-radius: 5px; display: inline-block; text-align: center; width: 100%; font-size: 16px; font-weight: bold;">📥 Descargar Guía</a>', unsafe_allow_html=True)
        st.balloons()
    except Exception as e:
        st.error(f"Error: {e}")
