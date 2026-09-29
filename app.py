import streamlit as st
import json
from collections import Counter
from logica_cotizador import Ventana, Puerta
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
</style>
""", unsafe_allow_html=True)

# Inicializar variables
if 'proyecto' not in st.session_state:
    st.session_state.proyecto = []
if 'edit_index' not in st.session_state:
    st.session_state.edit_index = None
if 'proyecto_activo_id' not in st.session_state:
    st.session_state.proyecto_activo_id = None
if 'costo_total' not in st.session_state:
    st.session_state.costo_total = 0.0
if 'anticipo' not in st.session_state:
    st.session_state.anticipo = 0.0
if 'nombre_cliente' not in st.session_state:
    st.session_state.nombre_cliente = ""

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
            if peso > cap_int:
                continue
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
    
    piezas_exactas = []
    piezas_reducidas = []
    
    for v in vidrios_list:
        try:
            w, h = [float(x.strip()) for x in v['medida'].lower().split('x')]
            piezas_exactas.append({"w": round(w, 1), "h": round(h, 1), "etiqueta": v['etiqueta'], "original": v['medida'], "activo": v.get('activo', True)})
            piezas_reducidas.append({"w": round(w - 1.0, 1), "h": round(h - 1.0, 1), "etiqueta": v['etiqueta'], "original": v['medida'], "activo": v.get('activo', True)})
        except: pass
        
    piezas_rescatadas = []
    pendientes_exactas = []
    pendientes_reducidas = []
    
    for i in range(len(piezas_exactas)):
        p_ex = piezas_exactas[i]
        p_red = piezas_reducidas[i]
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
                self.right = None
                self.bottom = None
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
            hojas_out.append({
                "ancho_usado": ancho_hoja, 
                "columnas": [{"ancho": "Cortes Variados", "alto_usado": "", "piezas": h['piezas']}]
            })
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
    
    # ------------------ ZONA PÚBLICA (TALLER) ------------------
    st.subheader("📚 Proyectos Guardados")
    proyectos_guardados = db_manager.obtener_proyectos()
    
    if proyectos_guardados:
        opciones = {p[0]: f"{p[1]} ({p[2]})" for p in proyectos_guardados}
        seleccion = st.selectbox("Selecciona un proyecto para cargar:", options=list(opciones.keys()), format_func=lambda x: opciones[x])
        
        # Botón cargar público: Cualquiera puede cargar para imprimir PDF
        if st.button("📂 Cargar para Taller", use_container_width=True):
            proyecto_cargado = next((p for p in proyectos_guardados if p[0] == seleccion), None)
            if proyecto_cargado:
                st.session_state.proyecto_activo_id = proyecto_cargado[0]
                st.session_state.nombre_cliente = proyecto_cargado[1]
                st.session_state.proyecto = json.loads(proyecto_cargado[3])
                try: st.session_state.anticipo = float(proyecto_cargado[5])
                except IndexError: st.session_state.anticipo = 0.0
                st.rerun()

    if st.button("✨ Limpiar Pantalla (Nuevo Proyecto)", use_container_width=True):
        st.session_state.proyecto = []
        st.session_state.edit_index = None
        st.session_state.proyecto_activo_id = None
        st.session_state.nombre_cliente = ""
        st.session_state.costo_total = 0.0
        st.session_state.anticipo = 0.0
        st.rerun()

    st.write("---")
    
    # ------------------ ZONA PRIVADA (ADMIN) ------------------
    st.subheader("🔒 Modo Administrador")
    pin_ingresado = st.text_input("🔑 PIN de Acceso (Finanzas):", type="password")

    if pin_ingresado == PIN_SECRETO:
        st.session_state['admin'] = True
        st.success("Modo Administrador activado")
        
        st.write("")
        st.session_state.nombre_cliente = st.text_input("Nombre del Cliente (Para guardar):", value=st.session_state.nombre_cliente)
        
        if st.button("💾 Guardar Proyecto", type="primary", use_container_width=True):
            if st.session_state.nombre_cliente == "":
                st.warning("⚠️ Ingresa el nombre del cliente arriba.")
            elif len(st.session_state.proyecto) == 0:
                st.warning("⚠️ No hay piezas para guardar.")
            else:
                db_manager.guardar_proyecto(
                    st.session_state.nombre_cliente, 
                    st.session_state.proyecto,
                    st.session_state.costo_total,
                    st.session_state.anticipo
                )
                st.success(f"¡Proyecto de {st.session_state.nombre_cliente} guardado!")

        if proyectos_guardados:
            if st.button("🗑️ Borrar Proyecto Seleccionado", use_container_width=True):
                db_manager.borrar_proyecto(seleccion)
                st.rerun()

    elif pin_ingresado != "":
        st.session_state['admin'] = False
        st.error("PIN incorrecto")
    elif pin_ingresado == "":
        st.session_state['admin'] = False

    if not st.session_state.get('admin', False):
        with st.expander("¿Olvidaste el PIN?"):
            respuesta = st.text_input(PREGUNTA_RECUPERACION).lower().strip()
            if respuesta == RESPUESTA_RECUPERACION:
                st.info(f"El PIN de acceso es: {PIN_SECRETO}")
            elif respuesta != "":
                st.error("Respuesta incorrecta")

# ==========================================
# LOGO Y ENCABEZADO PRINCIPAL
# ==========================================
col_logo1, col_logo2, col_logo3 = st.columns([1, 2, 1])
with col_logo2:
    st.image("logopagina.png", use_container_width=True)
st.write("---")

# ==========================================
# SECCIÓN 1: FORMULARIO (AGREGAR / EDITAR)
# ==========================================
is_editing = st.session_state.edit_index is not None

if is_editing:
    st.subheader("✏️ Editar pieza")
    idx = st.session_state.edit_index
    pieza_actual = st.session_state.proyecto[idx]
    def_tipo, def_detalle = pieza_actual['tipo'], pieza_actual['detalle']
    def_ancho, def_alto = float(pieza_actual['ancho'] * 100), float(pieza_actual['alto'] * 100)
    def_diseno = pieza_actual.get('diseno', "2 hojas")
    def_cuadricula = pieza_actual.get('cuadricula', False)
else:
    st.subheader("1. Agregar nueva pieza")
    def_tipo, def_detalle, def_ancho, def_alto = "Ventana Corrediza", "3 pulgadas", 100.0, 210.0
    def_diseno, def_cuadricula = "2 hojas", False

col_tipo, col_detalle = st.columns(2)
tipos_disponibles = ["Ventana Corrediza", "Puerta", "Cancel de Baño"]
idx_tipo = tipos_disponibles.index(def_tipo) if def_tipo in tipos_disponibles else 0

with col_tipo:
    tipo_pieza = st.selectbox("Tipo de estructura:", tipos_disponibles, index=idx_tipo)

opciones_detalle = ["3 pulgadas", "2 pulgadas"] if tipo_pieza == "Ventana Corrediza" else ["Vivienda", "Baño"] if tipo_pieza == "Puerta" else ["Corredizo", "Abatible"]
idx_det = opciones_detalle.index(def_detalle) if def_detalle in opciones_detalle else 0

with col_detalle:
    detalle_pieza = st.selectbox("Línea/Diseño:", opciones_detalle, index=idx_det)

if tipo_pieza == "Ventana Corrediza":
    col_diseno, col_cuadricula = st.columns(2)
    opciones_diseno = ["2 hojas", "Fijo Gigante Centro", "3 hojas (1 Fija Ext, 2 Corr)"]
    idx_diseno = opciones_diseno.index(def_diseno) if def_diseno in opciones_diseno else 0
    with col_diseno:
        diseno_pieza = st.selectbox("Estilo de Apertura:", opciones_diseno, index=idx_diseno)
    with col_cuadricula:
        st.write("")
        cuadricula_pieza = st.checkbox("Agregar intermedios (Cuadrícula)", value=def_cuadricula)
        if cuadricula_pieza:
            opciones_grid = ["2x2", "2x3", "3x2", "3x3", "3x4", "4x4"]
            valor_guardado = pieza_actual.get('tipo_cuadricula', "2x3") if is_editing else "2x3"
            idx_grid = opciones_grid.index(valor_guardado) if valor_guardado in opciones_grid else 1
            tipo_cuadricula_pieza = st.selectbox("Diseño (Columnas x Filas por hoja):", opciones_grid, index=idx_grid)
        else:
            tipo_cuadricula_pieza = "2x3" 
else:
    diseno_pieza = "2 hojas"
    cuadricula_pieza = False
    tipo_cuadricula_pieza = "2x3"

col1, col2 = st.columns(2)
with col1:
    ancho_input_cm = st.number_input("Ancho (cm)", min_value=1.0, value=def_ancho, step=0.1, format="%.1f")
with col2:
    alto_input_cm = st.number_input("Alto (cm)", min_value=1.0, value=def_alto, step=0.1, format="%.1f")

col_btn1, col_btn2 = st.columns([2, 8])
with col_btn1:
    if is_editing:
        if st.button("💾 Guardar Cambios", type="primary"):
            st.session_state.proyecto[st.session_state.edit_index] = {
                "tipo": tipo_pieza, "detalle": detalle_pieza, "ancho": ancho_input_cm / 100.0, "alto": alto_input_cm / 100.0,
                "diseno": diseno_pieza, "cuadricula": cuadricula_pieza, "tipo_cuadricula": tipo_cuadricula_pieza,
                "precio": pieza_actual.get('precio', 0.0)
            }
            st.session_state.edit_index = None
            st.rerun()
    else:
        if st.button("➕ Agregar al proyecto"):
            st.session_state.proyecto.append({
                "tipo": tipo_pieza, "detalle": detalle_pieza, "ancho": ancho_input_cm / 100.0, "alto": alto_input_cm / 100.0,
                "diseno": diseno_pieza, "cuadricula": cuadricula_pieza, "tipo_cuadricula": tipo_cuadricula_pieza,
                "precio": 0.0
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
with st.expander("📝 Editar piezas agregadas al proyecto", expanded=False):
    if len(st.session_state.proyecto) == 0:
        st.info("Aún no hay piezas agregadas. Usa el formulario de arriba.")
    else:
        for i, pieza in enumerate(st.session_state.proyecto):
            col_text, col_edit, col_del = st.columns([0.85, 0.075, 0.075])
            with col_text:
                txt_dis = f" - {pieza.get('diseno', '2 hojas')}" if pieza['tipo'] == "Ventana Corrediza" else ""
                txt_cuad = f" (Cuadrícula {pieza.get('tipo_cuadricula', '2x3')})" if pieza.get('cuadricula', False) else ""
                st.markdown(f"**{i+1}. {pieza['tipo']} ({pieza['detalle']})**{txt_dis}{txt_cuad} - {round(pieza['ancho']*100, 1)} cm x {round(pieza['alto']*100, 1)} cm")
            with col_edit:
                if st.button("✏️", key=f"edit_{i}", type="tertiary", help="Editar pieza"):
                    st.session_state.edit_index = i
                    st.rerun()
            with col_del:
                if st.button("🗑️", key=f"del_{i}", type="tertiary", help="Eliminar pieza"):
                    st.session_state.proyecto.pop(i)
                    if st.session_state.edit_index == i: st.session_state.edit_index = None
                    st.rerun()


# ==========================================
# SECCIÓN 3: FINANZAS Y COTIZACIÓN AL CLIENTE (SÓLO ADMIN)
# ==========================================
if st.session_state.get('admin', False):
    st.write("---")
    st.subheader("💰 Finanzas y Cotización (Proyecto Completo)")
    st.info("Esta sección calcula el total y genera el recibo basado en el PROYECTO GLOBAL para asegurar los anticipos del cliente.")
    
    total_proyecto = 0.0
    
    with st.expander("💵 Asignar precios individuales por pieza", expanded=False):
        st.markdown("**🔄 Distribuidor Automático (Por Área en m²):**")
        col_presup, col_btn_dist = st.columns([3, 1])
        with col_presup:
            presupuesto_global = st.number_input("Presupuesto Total a repartir ($):", min_value=0.0, step=1000.0, value=0.0)
        with col_btn_dist:
            st.write("") 
            if st.button("Repartir", use_container_width=True):
                area_total = sum([(p['ancho'] * p['alto']) for p in st.session_state.proyecto])
                if area_total > 0 and presupuesto_global > 0:
                    precio_por_m2 = presupuesto_global / area_total
                    for i in range(len(st.session_state.proyecto)):
                        area_pieza = st.session_state.proyecto[i]['ancho'] * st.session_state.proyecto[i]['alto']
                        st.session_state.proyecto[i]['precio'] = float(round(area_pieza * precio_por_m2))
                    st.rerun()
                elif area_total == 0:
                    st.warning("No hay piezas o no tienen área.")
        
        st.write("---")
        st.markdown("**Ingresa el precio final (material e instalación) por cada pieza:**")
        
        for i, pieza in enumerate(st.session_state.proyecto):
            col_texto, col_precio = st.columns([3, 1])
            with col_texto:
                area = pieza['ancho'] * pieza['alto']
                st.markdown(f"<br>**Pieza {i+1}:** {pieza['tipo']} ({round(pieza['ancho']*100, 1)} x {round(pieza['alto']*100, 1)} cm) - *{round(area, 2)} m²*", unsafe_allow_html=True)
            with col_precio:
                precio_actual = pieza.get('precio', 0.0)
                precio_pieza = st.number_input("Precio ($)", min_value=0.0, step=100.0, value=float(precio_actual), format="%.2f", key=f"precio_{i}")
                st.session_state.proyecto[i]['precio'] = precio_pieza
                total_proyecto += precio_pieza
    
    st.session_state.costo_total = total_proyecto
    st.write("")
    
    col_total, col_sugerido = st.columns(2)
    with col_total:
        st.metric("Total Cotizado:", f"${total_proyecto:,.2f}")
    with col_sugerido:
        st.metric("Anticipo Sugerido (50%):", f"${(total_proyecto / 2):,.2f}")
        
    st.write("")
    st.markdown("**Control de Pagos:**")
    col_anticipo, col_restante = st.columns(2)
    
    valor_protegido = float(st.session_state.get('anticipo', 0.0))
    ya_hay_anticipo = valor_protegido > 0
    
    with col_anticipo:
        anticipo_real = st.number_input("Anticipo entregado por el cliente ($)", min_value=0.0, step=100.0, value=valor_protegido, disabled=ya_hay_anticipo)
        st.session_state.anticipo = anticipo_real
    with col_restante:
        saldo_pendiente = total_proyecto - st.session_state.anticipo
        st.metric("Saldo Pendiente (A liquidar):", f"${saldo_pendiente:,.2f}")

    if st.button("📄 Generar Recibo para Cliente (PDF)", type="primary", use_container_width=True):
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
            fecha_actual = datetime.now().strftime("%d/%m/%Y")
            pdf.cell(0, 10, f"Fecha: {fecha_actual}", ln=True, align='R')
            pdf.ln(15) 
            
            pdf.set_font("Arial", 'B', 12)
            cliente_pdf = st.session_state.nombre_cliente if st.session_state.nombre_cliente else "Cliente General"
            pdf.cell(0, 10, f"Cliente: {cliente_pdf}", ln=True)
            pdf.ln(5)
            
            pdf.set_font("Arial", '', 10)
            for i, pieza in enumerate(st.session_state.proyecto):
                txt_dis = f" - {pieza.get('diseno', '2 hojas')}" if pieza['tipo'] == "Ventana Corrediza" else ""
                texto_pieza = f"Pieza {i+1}: {pieza['tipo']} {txt_dis} ({round(pieza['ancho']*100,1)} x {round(pieza['alto']*100,1)} cm)"
                precio_ind = st.session_state.get(f"precio_{i}", pieza.get('precio', 0.0))
                pdf.cell(140, 8, texto_pieza, border=1)
                pdf.cell(50, 8, f"${precio_ind:,.2f}", border=1, ln=True, align='R')
            
            pdf.ln(5)
            pdf.set_font("Arial", 'B', 11)
            pdf.cell(140, 8, "Total Cotizado:", border=0, align='R')
            pdf.cell(50, 8, f"${st.session_state.costo_total:,.2f}", border=1, ln=True, align='R')
            pdf.cell(140, 8, "Anticipo Recibido:", border=0, align='R')
            pdf.cell(50, 8, f"${st.session_state.anticipo:,.2f}", border=1, ln=True, align='R')
            pdf.set_font("Arial", 'B', 12)
            saldo_final = st.session_state.costo_total - st.session_state.anticipo
            pdf.cell(140, 8, "Saldo Pendiente:", border=0, align='R')
            pdf.cell(50, 8, f"${saldo_final:,.2f}", border=1, ln=True, align='R')

            pdf_bytes = pdf.output(dest='S').encode('latin-1')
            b64 = base64.b64encode(pdf_bytes).decode()
            
            with st.expander("👁️ Previsualizar Recibo", expanded=True):
                pdf_display = f'<embed src="data:application/pdf;base64,{b64}" width="100%" height="450" type="application/pdf">'
                st.markdown(pdf_display, unsafe_allow_html=True)
            
            href = f'<a href="data:application/pdf;base64,{b64}" download="Cotizacion_CASTFER_{cliente_pdf}.pdf" target="_blank" style="text-decoration: none; padding: 10px; background-color: #ff4b4b; color: white; border-radius: 5px; display: inline-block; text-align: center; width: 100%;">📥 Descargar Recibo PDF</a>'
            st.markdown(href, unsafe_allow_html=True)
        except Exception as e:
            st.error("⚠️ Error generando PDF.")


# ==========================================
# SECCIÓN 4: PRODUCCIÓN DE TALLER (ACCESIBLE PARA TODOS)
# ==========================================
st.write("---")
st.subheader("🚧 Producción de Taller (Optimización Global + Fases)")
st.info("El algoritmo matemático SIEMPRE optimizará el total de las piezas. Al seleccionar fases, los PDFs te dirán exactamente qué piezas cortar HOY y cuáles CORTAR Y GUARDAR para las fases futuras.")

usar_fases = st.checkbox("Activar fabricación parcial (Por Fases)", value=False)
indices_activos = []

if usar_fases:
    st.markdown("**Selecciona las piezas que vas a fabricar HOY en el taller:**")
    for i, pieza in enumerate(st.session_state.proyecto):
        if st.checkbox(f"Fabricar HOY - Pieza {i+1}: {pieza['tipo']} ({round(pieza['ancho']*100,1)}x{round(pieza['alto']*100,1)}cm)", value=True, key=f"fase_taller_{i}"):
            indices_activos.append(i)
else:
    indices_activos = [i for i in range(len(st.session_state.proyecto))]

if len(indices_activos) == 0 and len(st.session_state.proyecto) > 0:
    st.warning("⚠️ No has seleccionado ninguna pieza para fabricar hoy.")

col_prov1, col_prov2 = st.columns([1, 1])

# =============== BOTÓN: PROVEEDOR ===============
with col_prov1:
    if st.button("🛒 Generar Lista Material Proveedor (PDF)", type="secondary", use_container_width=True):
        try:
            from fpdf import FPDF
            import base64
            
            totales = {"jaladera": 0, "carretilla": 0, "vinil": 0.0}
            cortes_chambrana, cortes_riel, cortes_cerco, cortes_traslape, cortes_cabezal, cortes_zoclo, cortes_intermedio = [], [], [], [], [], [], []
            todos_los_vidrios_prov = []
            lista_medidas = []

            def agregar_cortes_prov(lista, medidas, etiqueta, es_activo):
                for m in medidas: lista.append({"medida": m, "etiqueta": etiqueta, "activo": es_activo})

            for i, p in enumerate(st.session_state.proyecto):
                es_activo = i in indices_activos
                num_pieza = i + 1
                
                if es_activo:
                    lista_medidas.append(f"P{num_pieza}: {round(p['ancho']*100,1)}x{round(p['alto']*100,1)}cm")

                if p['tipo'] == "Ventana Corrediza":
                    diseno = p.get('diseno', "2 hojas")
                    cuadricula = p.get('cuadricula', False)
                    t_cuad = p.get('tipo_cuadricula', "2x3")
                    
                    if es_activo:
                        if diseno == "Fijo Gigante Centro" or "3 hojas" in diseno:
                            totales["jaladera"] += 2
                            totales["carretilla"] += 4
                        else:
                            totales["jaladera"] += 1
                            totales["carretilla"] += 2
                    
                    v = Ventana(p['ancho'], p['alto'], p['detalle'], "Blanco", diseno=diseno, cuadricula=cuadricula, tipo_cuadricula=t_cuad)
                    a_m, alt_l = v.calcular_cortes_marco()
                    hojas = v.calcular_hojas()
                    
                    agregar_cortes_prov(cortes_chambrana, [round(alt_l*100, 1), round(alt_l*100, 1), round(a_m*100, 1)], f"L/C-P{num_pieza}", es_activo)
                    
                    if "3 hojas" in diseno:
                        agregar_cortes_prov(cortes_riel, [round(a_m*100, 1), round(a_m*100, 1)], f"P{num_pieza}", es_activo)
                    else:
                        agregar_cortes_prov(cortes_riel, [round(a_m*100, 1)], f"P{num_pieza}", es_activo)
                    
                    def prov_hoja(alto_h, ancho_h, es_gigante):
                        agregar_cortes_prov(cortes_cabezal, [round(ancho_h*100, 1)], f"P{num_pieza}", es_activo)
                        agregar_cortes_prov(cortes_zoclo, [round(ancho_h*100, 1)], f"P{num_pieza}", es_activo)
                        if es_gigante:
                            agregar_cortes_prov(cortes_cerco, [round(alto_h*100, 1)] * 2, f"P{num_pieza}", es_activo)
                        else:
                            agregar_cortes_prov(cortes_cerco, [round(alto_h*100, 1)], f"P{num_pieza}", es_activo)
                            agregar_cortes_prov(cortes_traslape, [round(alto_h*100, 1)], f"P{num_pieza}", es_activo)
                            
                        luz_ancho = (ancho_h * 100) - 10.0
                        luz_alto = (alto_h * 100) - 9.0
                        
                        if cuadricula:
                            ints = v.calcular_intermedios_aluminio(alto_h, ancho_h, es_gigante)
                            if ints["verticales"]:
                                agregar_cortes_prov(cortes_intermedio, [round(x*100, 1) for x in ints["verticales"]], f"Vert-P{num_pieza}", es_activo)
                            if ints["horizontales"]:
                                agregar_cortes_prov(cortes_intermedio, [round(x*100, 1) for x in ints["horizontales"]], f"Horz-P{num_pieza}", es_activo)
                            
                            alto_int = alto_h - v.perfil_cabezal - v.perfil_zoclo
                            ancho_int = ancho_h - (v.perfil_cerco_traslape * 2)
                            filas = v.filas_hoja
                            cols = v.cols_hoja * 2 if es_gigante else v.cols_hoja
                            alto_v = ((alto_int - (filas - 1) * v.intermedio_frente) / filas) + (v.holgura_vidrio * 2)
                            ancho_v = ((ancho_int - (cols - 1) * v.intermedio_frente) / cols) + (v.holgura_vidrio * 2)
                            
                            if es_activo: totales["vinil"] += ((ancho_v*100) + (alto_v*100)) * 2 * (filas * cols)
                            for _ in range(filas * cols):
                                todos_los_vidrios_prov.append({"medida": f"{round(ancho_v*100, 1)} x {round(alto_v*100, 1)}", "etiqueta": f"P{num_pieza}", "activo": es_activo})
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
            fecha_actual = datetime.now().strftime("%d/%m/%Y")
            pdf.cell(0, 6, f"Fecha de emision: {fecha_actual}", ln=True, align='R')
            cliente_pdf = st.session_state.nombre_cliente if st.session_state.nombre_cliente else "Proyecto General"
            pdf.cell(0, 6, f"Cliente / Proyecto: {cliente_pdf}", ln=True, align='R')
            pdf.ln(8)
            pdf.line(10, pdf.get_y(), 200, pdf.get_y())
            pdf.ln(5)

            pdf.set_font("Arial", 'B', 12)
            pdf.set_fill_color(235, 235, 235)
            pdf.cell(0, 8, " 1. PERFILES A COMPRAR HOY (Tiras de 6 metros)", ln=True, fill=True)
            pdf.ln(4)
            pdf.set_font("Arial", '', 11)
            
            pdf.cell(0, 8, f"[   ]   {calcular_tramos_a_comprar(cortes_chambrana)} Chambranas de 6 mts", ln=True)
            pdf.cell(0, 8, f"[   ]   {calcular_tramos_a_comprar(cortes_riel)} Rieles de 6 mts", ln=True)
            pdf.cell(0, 8, f"[   ]   {calcular_tramos_a_comprar(cortes_cerco)} Cercos de 6 mts", ln=True)
            pdf.cell(0, 8, f"[   ]   {calcular_tramos_a_comprar(cortes_traslape)} Traslapes de 6 mts", ln=True)
            pdf.cell(0, 8, f"[   ]   {calcular_tramos_a_comprar(cortes_cabezal)} Cabezales de 6 mts", ln=True)
            pdf.cell(0, 8, f"[   ]   {calcular_tramos_a_comprar(cortes_zoclo)} Zoclos de 6 mts", ln=True)
            pdf.cell(0, 8, f"[   ]   {calcular_tramos_a_comprar(cortes_intermedio)} Intermedios de 6 mts", ln=True)
            pdf.ln(4)

            pdf.set_font("Arial", 'B', 12)
            pdf.cell(0, 8, " 2. HERRAJES Y ACCESORIOS (Para fase actual)", ln=True, fill=True)
            pdf.ln(4)
            pdf.set_font("Arial", '', 11)
            if totales["jaladera"] > 0:
                pdf.cell(0, 8, f"[   ]   {totales['jaladera']} Jaladeras", ln=True)
                pdf.cell(0, 8, f"[   ]   {totales['carretilla']} Carretillas", ln=True)
                botes = max(1, math.ceil(totales['vinil'] / 1000.0)) 
                pdf.cell(0, 8, f"[   ]   {botes} Botes de Sellador", ln=True)
                pdf.cell(0, 8, f"[   ]   {math.ceil(totales['vinil'] / 100.0)} Metros lineales de Vinil", ln=True)
            
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
            pdf.cell(0, 8, " 4. RESUMEN DE VENTANAS ACTIVAS", ln=True, fill=True)
            pdf.ln(4)
            pdf.set_font("Arial", '', 10)
            if lista_medidas:
                pdf.multi_cell(0, 6, "   |   ".join(lista_medidas))

            pdf_bytes = pdf.output(dest='S').encode('latin-1')
            b64 = base64.b64encode(pdf_bytes).decode()
            
            with st.expander("👁️ Previsualizar Lista de Compras", expanded=True):
                pdf_display = f'<embed src="data:application/pdf;base64,{b64}" width="100%" height="450" type="application/pdf">'
                st.markdown(pdf_display, unsafe_allow_html=True)

            href = f'<a href="data:application/pdf;base64,{b64}" download="Compras_CASTFER_{cliente_pdf}.pdf" target="_blank" style="text-decoration: none; padding: 10px; background-color: #6c757d; color: white; border-radius: 5px; display: inline-block; text-align: center; width: 100%;">🛒 Descargar PDF de Compras</a>'
            st.markdown(href, unsafe_allow_html=True)
        except Exception as e:
            st.error(f"⚠️ Error generando PDF: {e}")

# =============== BOTÓN: GUÍA DE CORTES ===============
st.write("")
with st.expander("♻️ ¿Tienes pedacería en el taller? (Opcional)"):
    col_p1, col_p2, col_p3 = st.columns(3)
    with col_p1:
        ped_chambrana = st.text_input("Recortes Chambrana:", "")
        ped_cerco = st.text_input("Recortes Cerco:", "")
    with col_p2:
        ped_riel = st.text_input("Recortes Riel:", "")
        ped_traslape = st.text_input("Recortes Traslape:", "")
        ped_intermedio = st.text_input("Recortes Intermedio:", "")
    with col_p3:
        ped_cabezal = st.text_input("Recortes Cabezal:", "")
        ped_zoclo = st.text_input("Recortes Zoclo:", "")
        ped_vidrio = st.text_input("Recortes Vidrio:", "")

if st.button("✂️ Generar Guía de Cortes para Taller (PDF)", type="primary", use_container_width=True):
    try:
        from fpdf import FPDF
        import base64
        
        cortes_chambrana, cortes_riel, cortes_cerco, cortes_traslape, cortes_cabezal, cortes_zoclo, cortes_intermedio = [], [], [], [], [], [], []
        todos_los_vidrios_taller = []

        def agregar_cortes_taller(lista, medidas, etiqueta, es_activo):
            for m in medidas: lista.append({"medida": m, "etiqueta": etiqueta, "activo": es_activo})
        
        for i, p in enumerate(st.session_state.proyecto):
            es_activo = i in indices_activos
            num_pieza = i + 1  

            if p['tipo'] == "Ventana Corrediza":
                diseno = p.get('diseno', "2 hojas")
                cuadricula = p.get('cuadricula', False)
                t_cuad = p.get('tipo_cuadricula', "2x3")
                v = Ventana(p['ancho'], p['alto'], p['detalle'], "Blanco", diseno=diseno, cuadricula=cuadricula, tipo_cuadricula=t_cuad)
                
                a_m, alt_l = v.calcular_cortes_marco()
                hojas = v.calcular_hojas()
                
                agregar_cortes_taller(cortes_chambrana, [round(alt_l*100, 1), round(alt_l*100, 1), round(a_m*100, 1)], f"L/C-P{num_pieza}", es_activo)
                
                if "3 hojas" in diseno:
                    agregar_cortes_taller(cortes_riel, [round(a_m*100, 1), round(a_m*100, 1)], f"P{num_pieza}", es_activo)
                else:
                    agregar_cortes_taller(cortes_riel, [round(a_m*100, 1)], f"P{num_pieza}", es_activo)
                
                def cortes_hoja_taller(nombre, alto_h, ancho_h, es_gigante):
                    lbl = f"{nombre}-P{num_pieza}"
                    agregar_cortes_taller(cortes_cabezal, [round(ancho_h*100, 1)], lbl, es_activo)
                    agregar_cortes_taller(cortes_zoclo, [round(ancho_h*100, 1)], lbl, es_activo)
                    if es_gigante:
                        agregar_cortes_taller(cortes_cerco, [round(alto_h*100, 1)] * 2, lbl, es_activo)
                    else:
                        agregar_cortes_taller(cortes_cerco, [round(alto_h*100, 1)], lbl, es_activo)
                        agregar_cortes_taller(cortes_traslape, [round(alto_h*100, 1)], lbl, es_activo)
                        
                    if cuadricula:
                        ints = v.calcular_intermedios_aluminio(alto_h, ancho_h, es_gigante)
                        if ints["verticales"]:
                            agregar_cortes_taller(cortes_intermedio, [round(x*100, 1) for x in ints["verticales"]], f"V-{lbl}", es_activo)
                        if ints["horizontales"]:
                            agregar_cortes_taller(cortes_intermedio, [round(x*100, 1) for x in ints["horizontales"]], f"H-{lbl}", es_activo)
                            
                        alto_int = alto_h - v.perfil_cabezal - v.perfil_zoclo
                        ancho_int = ancho_h - (v.perfil_cerco_traslape * 2)
                        filas = v.filas_hoja
                        cols = v.cols_hoja * 2 if es_gigante else v.cols_hoja
                        alto_v = ((alto_int - (filas - 1) * v.intermedio_frente) / filas) + (v.holgura_vidrio * 2)
                        ancho_v = ((ancho_int - (cols - 1) * v.intermedio_frente) / cols) + (v.holgura_vidrio * 2)
                        
                        for _ in range(filas * cols):
                            todos_los_vidrios_taller.append({"medida": f"{round(ancho_v*100, 1)} x {round(alto_v*100, 1)}", "etiqueta": f"{lbl}", "activo": es_activo})
                    else:
                        a_v, alt_v, _ = v.calcular_vidrio(alto_h, ancho_h)
                        todos_los_vidrios_taller.append({"medida": f"{round(a_v*100, 1)} x {round(alt_v*100, 1)}", "etiqueta": lbl, "activo": es_activo})

                if diseno == "2 hojas":
                    cortes_hoja_taller("Fija", hojas["fija"][0], hojas["fija"][1], False)
                    cortes_hoja_taller("Corr", hojas["corrediza"][0], hojas["corrediza"][1], False)
                elif diseno == "Fijo Gigante Centro":
                    cortes_hoja_taller("FijG", hojas["fija_gigante"][0], hojas["fija_gigante"][1], True)
                    cortes_hoja_taller("CoI", hojas["corrediza_izq"][0], hojas["corrediza_izq"][1], False)
                    cortes_hoja_taller("CoD", hojas["corrediza_der"][0], hojas["corrediza_der"][1], False)
                elif "3 hojas" in diseno:
                    cortes_hoja_taller("FijExt", hojas["fija_ext"][0], hojas["fija_ext"][1], False)
                    cortes_hoja_taller("CorNrm", hojas["corr_normal"][0], hojas["corr_normal"][1], False)
                    cortes_hoja_taller("CorDbl", hojas["corr_doble"][0], hojas["corr_doble"][1], False)
            
            elif p['tipo'] == "Puerta":
                puerta = Puerta(p['ancho'], p['alto'], p['detalle'], "Blanco")
                ancho_r, alto_r, cant_duelas = puerta.calcular_relleno()
                todos_los_vidrios_taller.append({"medida": f"{round(ancho_r*100, 1)} x {round(alto_r*100, 1)}", "etiqueta": f"P{num_pieza}", "activo": es_activo})

        pdf = FPDF()
        pdf.add_page()
        
        try: pdf.image("logopagina.png", x=10, y=8, w=54)
        except: pass 
        
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(0, 10, "GUIA DE CORTES - MESA DE TRABAJO", ln=True, align='R')
        pdf.set_font("Arial", '', 11)
        cliente_pdf = st.session_state.nombre_cliente if st.session_state.nombre_cliente else "Proyecto General"
        pdf.cell(0, 6, f"Cliente: {cliente_pdf}", ln=True, align='R')
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
                
                texto = f"  * De tu retazo de {p_data['tamano']}cm:\n      -> CORTA HOY: {usados_act}\n"
                if usados_pend: texto += f"      -> CORTA Y GUARDA (Futuro): {usados_pend}\n"
                texto += f"      -> Sobrante final: {round(sobra,1)}cm"
                pdf.multi_cell(0, 6, texto)
                pdf.ln(1)
            
            for i, tramo in enumerate(tramos):
                activos = [u for u in tramo if u.get('activo', True)]
                pendientes = [u for u in tramo if not u.get('activo', True)]
                if not activos: continue
                
                usados_act = ", ".join([f"{u['medida']}cm ({u['etiqueta']})" for u in activos])
                usados_pend = ", ".join([f"{u['medida']}cm ({u['etiqueta']})" for u in pendientes])
                sobra = 600.0 - (sum([u['medida'] for u in tramo]) + len(tramo)*0.3)
                
                texto = f"  * Tramo {i+1} (6.00m):\n      -> CORTA HOY: {usados_act}\n"
                if usados_pend: texto += f"      -> CORTA Y GUARDA (Futuro): {usados_pend}\n"
                texto += f"      -> Sobrante final: {round(sobra,1)}cm"
                pdf.multi_cell(0, 6, texto)
                pdf.ln(1)

        pdf_imprimir_perfil("Chambranas", cortes_chambrana, ped_chambrana)
        pdf_imprimir_perfil("Rieles", cortes_riel, ped_riel)
        pdf_imprimir_perfil("Cercos", cortes_cerco, ped_cerco)
        pdf_imprimir_perfil("Traslapes", cortes_traslape, ped_traslape)
        pdf_imprimir_perfil("Cabezales de Hoja", cortes_cabezal, ped_cabezal)
        pdf_imprimir_perfil("Zoclos", cortes_zoclo, ped_zoclo)
        pdf_imprimir_perfil("Intermedios (Divisiones)", cortes_intermedio, ped_intermedio)

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
                    p, ped = r["pieza"], r["pedazo"]
                    if p.get('activo', True):
                        pdf.cell(0, 6, f"  - Del retazo {ped['original']}: Cortar HOY {p['w']} x {p['h']} cm (Mrc: {p['etiqueta']})", ln=True)
                    else:
                        pdf.cell(0, 6, f"  - Del retazo {ped['original']}: Cortar Y GUARDAR {p['w']} x {p['h']} cm (Mrc: {p['etiqueta']})", ln=True)
                pdf.ln(3)

            if hojas_vidrio:
                ancho = int(best_config['ancho'])
                texto_red = "(Reduccion 0.5 cm por lado aplicada)" if best_config['reducido'] else "(Medida exacta)"
                pdf.set_font("Arial", 'B', 11)
                pdf.cell(0, 8, f"HOJAS NUEVAS ({ancho}x260 cm) {texto_red}:", ln=True)
                
                pdf.set_font("Arial", '', 10)
                for i, h in enumerate(hojas_vidrio):
                    tiene_activos = any(p.get('activo', True) for col in h['columnas'] for p in col['piezas'])
                    if not tiene_activos: continue
                    
                    pdf.set_font("Arial", 'B', 10)
                    pdf.cell(0, 6, f" >> HOJA {i+1}:", ln=True)
                    pdf.set_font("Arial", '', 10)
                    for j, col in enumerate(h['columnas']):
                        for p in col['piezas']:
                            texto_estado = " [CORTA HOY]" if p.get('activo', True) else " [CORTA Y GUARDA]"
                            pdf.cell(0, 6, f"      [ ] {p['w']} x {p['h']} cm   (Mrc: {p['etiqueta']}){texto_estado}", ln=True)
                    pdf.ln(2)

        pdf_bytes = pdf.output(dest='S').encode('latin-1')
        b64 = base64.b64encode(pdf_bytes).decode()
        
        with st.expander("👁️ Previsualizar Guía de Cortes (Taller)", expanded=True):
            pdf_display = f'<embed src="data:application/pdf;base64,{b64}" width="100%" height="700" type="application/pdf">'
            st.markdown(pdf_display, unsafe_allow_html=True)

        href = f'<a href="data:application/pdf;base64,{b64}" download="Guia_Cortes_{cliente_pdf}.pdf" target="_blank" style="text-decoration: none; padding: 12px; background-color: #007bff; color: white; border-radius: 5px; display: inline-block; text-align: center; width: 100%; font-size: 16px; font-weight: bold;">📥 Descargar Guía de Cortes para Taller</a>'
        st.markdown(href, unsafe_allow_html=True)
        st.balloons()
        
    except Exception as e:
        st.error(f"Error generando la guía de cortes: {e}")
