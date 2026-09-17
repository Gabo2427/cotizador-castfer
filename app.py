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

# NUEVO OPTIMIZADOR DE ALUMINIO: Ahora entiende las etiquetas (Marcadores)
def optimizador_aluminio_taller(cortes_list, pedaceria_str, tramo_ideal=600.0):
    pedaceria = parsear_pedaceria(pedaceria_str)
    # Ordenar de mayor a menor basándose en la medida
    cortes_ordenados = sorted(cortes_list, key=lambda x: x["medida"], reverse=True)
    tramos_nuevos = []
    uso_ped = {i: {"tamano": p, "usados": []} for i, p in enumerate(pedaceria)}
    
    for corte_dict in cortes_ordenados:
        corte_real = corte_dict["medida"] + 0.3 # 3mm del disco de corte
        colocado = False
        
        # 1. Intentar meter en pedacería
        for i in range(len(pedaceria)):
            usado_ahora = sum([u["medida"] for u in uso_ped[i]["usados"]]) + (len(uso_ped[i]["usados"]) * 0.3)
            if uso_ped[i]["tamano"] - usado_ahora >= corte_real:
                uso_ped[i]["usados"].append(corte_dict)
                colocado = True
                break
        if colocado: continue
        
        # 2. Intentar meter en los tramos nuevos abiertos
        for tramo in tramos_nuevos:
            usado_ahora = sum([u["medida"] for u in tramo]) + (len(tramo) * 0.3)
            if tramo_ideal - usado_ahora >= corte_real:
                tramo.append(corte_dict)
                colocado = True
                break
        
        # 3. Abrir nuevo tramo de 6 metros
        if not colocado: tramos_nuevos.append([corte_dict])
            
    return tramos_nuevos, uso_ped

# MOTOR DE VIDRIO CON GUILLOTINA 2D
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
            piezas_exactas.append({"w": round(w, 1), "h": round(h, 1), "etiqueta": v['etiqueta'], "original": v['medida']})
            piezas_reducidas.append({"w": round(w - 1.0, 1), "h": round(h - 1.0, 1), "etiqueta": v['etiqueta'], "original": v['medida']})
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
                    raiz['piezas'].append({"w": pw, "h": ph, "etiqueta": p["etiqueta"]})
                    colocado = True
                    break
                elif raiz['tree'].insert(ph, pw):
                    raiz['piezas'].append({"w": ph, "h": pw, "etiqueta": p["etiqueta"] + " (Rotado)"})
                    colocado = True
                    break
                    
            if not colocado:
                nueva_raiz = Node(0, 0, ancho_hoja, alto_hoja)
                if nueva_raiz.insert(pw, ph):
                    hojas.append({'tree': nueva_raiz, 'piezas': [{"w": pw, "h": ph, "etiqueta": p["etiqueta"]}]})
                elif nueva_raiz.insert(ph, pw):
                    hojas.append({'tree': nueva_raiz, 'piezas': [{"w": ph, "h": pw, "etiqueta": p["etiqueta"] + " (Rotado)"}]})
                    
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
    
    pin_ingresado = st.text_input("🔑 PIN de Acceso:", type="password")

    if pin_ingresado == PIN_SECRETO:
        st.session_state['admin'] = True
        st.success("Modo Administrador activado")
    elif pin_ingresado != "":
        st.session_state['admin'] = False
        st.error("PIN incorrecto")
    elif pin_ingresado == "":
        st.session_state['admin'] = False

    if not st.session_state.get('admin', False):
        with st.expander("¿Olvidaste el PIN?"):
            st.markdown("Responde para ver el PIN:")
            respuesta = st.text_input(PREGUNTA_RECUPERACION).lower().strip()
            
            if respuesta == RESPUESTA_RECUPERACION:
                st.info(f"El PIN de acceso es: {PIN_SECRETO}")
            elif respuesta != "":
                st.error("Respuesta incorrecta")
    
    st.write("---")

    if st.session_state.get('admin', False):
        st.subheader("💾 Gestión de Clientes")
        st.session_state.nombre_cliente = st.text_input("Nombre del Cliente:", value=st.session_state.nombre_cliente)
        
        if st.button("Guardar Proyecto en Historial", use_container_width=True):
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
                st.success(f"¡Proyecto de {st.session_state.nombre_cliente} guardado con éxito!")

        proyectos_guardados = db_manager.obtener_proyectos()
        if proyectos_guardados:
            st.write("")
            st.markdown("**Historial de cotizaciones:**")
            opciones = {p[0]: f"{p[1]} ({p[2]})" for p in proyectos_guardados}
            seleccion = st.selectbox("Selecciona un proyecto:", options=list(opciones.keys()), format_func=lambda x: opciones[x])
            
            col_cargar, col_borrar = st.columns(2)
            with col_cargar:
                if st.button("📂 Cargar", use_container_width=True):
                    proyecto_cargado = next((p for p in proyectos_guardados if p[0] == seleccion), None)
                    if proyecto_cargado:
                        st.session_state.proyecto_activo_id = proyecto_cargado[0]
                        st.session_state.nombre_cliente = proyecto_cargado[1]
                        st.session_state.proyecto = json.loads(proyecto_cargado[3])
                        
                        try:
                            st.session_state.anticipo = float(proyecto_cargado[5])
                        except IndexError:
                            st.session_state.anticipo = 0.0
                            
                        st.rerun()
            with col_borrar:
                if st.button("🗑️ Borrar", use_container_width=True):
                    db_manager.borrar_proyecto(seleccion)
                    st.rerun()

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
else:
    st.subheader("1. Agregar nueva pieza")
    def_tipo, def_detalle, def_ancho, def_alto = "Ventana Corrediza", "3 pulgadas", 100.0, 210.0

col_tipo, col_detalle = st.columns(2)
tipos_disponibles = ["Ventana Corrediza", "Puerta", "Cancel de Baño"]
idx_tipo = tipos_disponibles.index(def_tipo) if def_tipo in tipos_disponibles else 0

with col_tipo:
    tipo_pieza = st.selectbox("Tipo de estructura:", tipos_disponibles, index=idx_tipo)

opciones_detalle = ["3 pulgadas", "2 pulgadas"] if tipo_pieza == "Ventana Corrediza" else ["Vivienda", "Baño"] if tipo_pieza == "Puerta" else ["Corredizo", "Abatible"]
idx_det = opciones_detalle.index(def_detalle) if def_detalle in opciones_detalle else 0

with col_detalle:
    detalle_pieza = st.selectbox("Línea/Diseño:", opciones_detalle, index=idx_det)

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
                "tipo": tipo_pieza, "detalle": detalle_pieza, "ancho": ancho_input_cm / 100.0, "alto": alto_input_cm / 100.0
            }
            st.session_state.edit_index = None
            st.rerun()
    else:
        if st.button("➕ Agregar al proyecto"):
            st.session_state.proyecto.append({
                "tipo": tipo_pieza, "detalle": detalle_pieza, "ancho": ancho_input_cm / 100.0, "alto": alto_input_cm / 100.0
            })
            st.success(f"¡{tipo_pieza} agregada!")

with col_btn2:
    if is_editing and st.button("❌ Cancelar edición"):
        st.session_state.edit_index = None
        st.rerun()

st.write("---")

# ==========================================
# SECCIÓN 2: LISTA DEL CLIENTE E INVENTARIO
# ==========================================
st.subheader("📝 Lista de piezas del proyecto activo:")

if len(st.session_state.proyecto) > 0:
    if st.button("🧹 Limpiar pantalla (Proyecto Nuevo)"):
        st.session_state.proyecto = []
        st.session_state.edit_index = None
        st.session_state.proyecto_activo_id = None
        st.session_state.nombre_cliente = ""
        st.session_state.costo_total = 0.0
        st.session_state.anticipo = 0.0
        st.rerun()
    st.write("")

if len(st.session_state.proyecto) == 0:
    st.info("Aún no hay piezas agregadas. Usa el menú izquierdo para cargar un proyecto o agrega piezas nuevas.")
else:
    for i, pieza in enumerate(st.session_state.proyecto):
        col_text, col_edit, col_del = st.columns([0.85, 0.075, 0.075])
        with col_text:
            st.markdown(f"**{i+1}. {pieza['tipo']} ({pieza['detalle']})** - {round(pieza['ancho']*100, 1)} cm x {round(pieza['alto']*100, 1)} cm")
        with col_edit:
            if st.button("✏️", key=f"edit_{i}", type="tertiary", help="Editar pieza"):
                st.session_state.edit_index = i
                st.rerun()
        with col_del:
            if st.button("🗑️", key=f"del_{i}", type="tertiary", help="Eliminar pieza"):
                st.session_state.proyecto.pop(i)
                if st.session_state.edit_index == i: st.session_state.edit_index = None
                st.rerun()
                
    st.write("---")

    # ==========================================
    # SECCIÓN 3: FINANZAS E IMPRESIÓN (BOTONES PDF)
    # ==========================================
    if st.session_state.get('admin', False):
        st.subheader("💰 Finanzas del Proyecto")
        st.markdown("**Ingresa el precio final (material e instalación) por cada pieza:**")
        
        total_proyecto = 0.0
        
        for i, pieza in enumerate(st.session_state.proyecto):
            col_texto, col_precio = st.columns([3, 1])
            with col_texto:
                st.markdown(f"<br>**Pieza {i+1}:** {pieza['tipo']} ({round(pieza['ancho']*100, 1)} x {round(pieza['alto']*100, 1)} cm) - Línea {pieza['detalle']}", unsafe_allow_html=True)
            with col_precio:
                precio_actual = pieza.get('precio', 0.0)
                precio_pieza = st.number_input("Precio ($)", min_value=0.0, step=100.0, value=float(precio_actual), format="%.2f", key=f"precio_{i}")
                st.session_state.proyecto[i]['precio'] = precio_pieza
                total_proyecto += precio_pieza
        
        st.session_state.costo_total = total_proyecto
        st.write("---")
        
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
        
        st.write("---")
        st.subheader("🖨️ Generación de Documentos")
        col_pdf1, col_pdf2 = st.columns(2)
        
        # ==================== BOTÓN 1: RECIBO ====================
        with col_pdf1:
            if st.button("📄 Recibo para Cliente (PDF)", type="primary", use_container_width=True):
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
                        texto_pieza = f"Pieza {i+1}: {pieza['tipo']} - {pieza['detalle']} ({round(pieza['ancho']*100,1)} x {round(pieza['alto']*100,1)} cm)"
                        precio_ind = st.session_state.get(f"precio_{i}", 0.0)
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
                    href = f'<a href="data:application/pdf;base64,{b64}" download="Cotizacion_CASTFER_{cliente_pdf}.pdf" target="_blank" style="text-decoration: none; padding: 10px; background-color: #ff4b4b; color: white; border-radius: 5px; display: inline-block; text-align: center; width: 100%;">📥 Descargar Recibo PDF</a>'
                    st.markdown(href, unsafe_allow_html=True)
                except Exception as e:
                    st.error("⚠️ Error generando PDF.")

        # ==================== BOTÓN 2: PROVEEDOR ====================
        with col_pdf2:
            if st.button("🛒 Lista Material Proveedor (PDF)", type="secondary", use_container_width=True):
                try:
                    from fpdf import FPDF
                    import base64
                    tot_chambrana = tot_riel = tot_cerco = tot_traslape = tot_cabezal = tot_zoclo = tot_vinil = 0.0
                    num_ventanas = 0
                    lista_medidas = []
                    vidrios_fijos, vidrios_corredizos, vidrios_puerta = [], [], []

                    for i, p in enumerate(st.session_state.proyecto):
                        texto_medida = f"P{i+1}: {round(p['ancho']*100,1)}x{round(p['alto']*100,1)}cm"
                        lista_medidas.append(texto_medida)

                        if p['tipo'] == "Ventana Corrediza":
                            num_ventanas += 1
                            v = Ventana(p['ancho'], p['alto'], p['detalle'], "Blanco")
                            a_m, alt_l = v.calcular_cortes_marco()
                            alt_f, a_h = v.calcular_hoja_fija()
                            alt_c, _ = v.calcular_hoja_corrediza()
                            a_vf, alt_vf, _ = v.calcular_vidrio(alt_f, a_h)
                            a_vc, alt_vc, _ = v.calcular_vidrio(alt_c, a_h)
                            
                            tot_chambrana += (alt_l * 2 + a_m) * 100
                            tot_riel += (a_m) * 100
                            tot_cerco += (alt_f + alt_c) * 100
                            tot_traslape += (alt_f + alt_c) * 100
                            tot_cabezal += (a_h * 2) * 100
                            tot_zoclo += (a_h * 2) * 100
                            luz_ancho = (a_h * 100) - 10.0
                            luz_alto_f = (alt_f * 100) - 9.0
                            luz_alto_c = (alt_c * 100) - 9.0
                            tot_vinil += ((luz_ancho + luz_alto_f) * 2) + ((luz_ancho + luz_alto_c) * 2)
                            
                            vidrios_fijos.append({"medida": f"{round(a_vf*100, 1)} x {round(alt_vf*100, 1)}", "etiqueta": f"P{i+1}"})
                            vidrios_corredizos.append({"medida": f"{round(a_vc*100, 1)} x {round(alt_vc*100, 1)}", "etiqueta": f"P{i+1}"})
                            
                        elif p['tipo'] == "Puerta":
                            puerta = Puerta(p['ancho'], p['alto'], p['detalle'], "Blanco")
                            ancho_r, alto_r, cant_duelas = puerta.calcular_relleno()
                            vidrios_puerta.append({"medida": f"{round(ancho_r*100, 1)} x {round(alto_r*100, 1)}", "etiqueta": f"P{i+1}"})

                    pdf = FPDF()
                    pdf.add_page()
                    try: pdf.image("logopagina.png", x=10, y=8, w=54)
                    except: pass 
                    
                    pdf.set_font("Arial", 'B', 16)
                    pdf.cell(0, 8, "ORDEN DE MATERIALES - TALLER", ln=True, align='R')
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
                    pdf.cell(0, 8, " 1. PERFILES DE ALUMINIO (Tiras de 6 metros)", ln=True, fill=True)
                    pdf.ln(4)
                    pdf.set_font("Arial", '', 11)

                    def agregar_perfil(nombre, total_cm):
                        if total_cm > 0:
                            tiras = math.ceil(total_cm / 600.0)
                            pdf.cell(0, 8, f"[   ]   {tiras} {nombre} de 6 mts   (Total neto: {round(total_cm/100.0,2)} mts)", ln=True)

                    agregar_perfil("Chambranas", tot_chambrana)
                    agregar_perfil("Rieles", tot_riel)
                    agregar_perfil("Cercos", tot_cerco)
                    agregar_perfil("Traslapes", tot_traslape)
                    agregar_perfil("Cabezales", tot_cabezal)
                    agregar_perfil("Zoclos", tot_zoclo)
                    pdf.ln(4)

                    pdf.set_font("Arial", 'B', 12)
                    pdf.cell(0, 8, " 2. HERRAJES Y ACCESORIOS", ln=True, fill=True)
                    pdf.ln(4)
                    pdf.set_font("Arial", '', 11)
                    if num_ventanas > 0:
                        pdf.cell(0, 8, f"[   ]   {num_ventanas} Jaladeras", ln=True)
                        pdf.cell(0, 8, f"[   ]   {num_ventanas * 2} Carretillas", ln=True)
                        pdf.cell(0, 8, f"[   ]   {num_ventanas} Botes de Sellador", ln=True)
                        pdf.cell(0, 8, f"[   ]   {math.ceil(tot_vinil / 100.0)} Metros lineales de Vinil", ln=True)
                    
                    pdf.ln(6)
                    pdf.set_font("Arial", 'B', 12)
                    pdf.cell(0, 8, " 3. CRISTAL / VIDRIO (Optimizacion Automatica)", ln=True, fill=True)
                    pdf.ln(4)
                    pdf.set_font("Arial", '', 11)
                    todos_los_vidrios_pdf = vidrios_fijos + vidrios_corredizos + vidrios_puerta
                    if todos_los_vidrios_pdf:
                        hojas_vidrio_comprar, _, config = optimizador_vidrio(todos_los_vidrios_pdf, "")
                        txt_red = " (Reduccion 0.5cm)" if config['reducido'] else " (Medida exacta)"
                        pdf.cell(0, 8, f"[   ]   {len(hojas_vidrio_comprar)} Hoja(s) de {int(config['ancho'])}x260 cm{txt_red}", ln=True)
                    else:
                        pdf.cell(0, 8, "No se requiere cristal.", ln=True)

                    pdf.ln(6)
                    pdf.set_font("Arial", 'B', 12)
                    pdf.cell(0, 8, " 4. RESUMEN DE MEDIDAS (Ancho x Alto)", ln=True, fill=True)
                    pdf.ln(4)
                    pdf.set_font("Arial", '', 10)
                    if lista_medidas:
                        pdf.multi_cell(0, 6, "   |   ".join(lista_medidas))

                    pdf_bytes = pdf.output(dest='S').encode('latin-1')
                    b64 = base64.b64encode(pdf_bytes).decode()
                    href = f'<a href="data:application/pdf;base64,{b64}" download="Compras_{cliente_pdf}.pdf" target="_blank" style="text-decoration: none; padding: 10px; background-color: #6c757d; color: white; border-radius: 5px; display: inline-block; text-align: center; width: 100%;">🛒 Descargar PDF de Compras</a>'
                    st.markdown(href, unsafe_allow_html=True)
                except Exception as e:
                    st.error("⚠️ Error generando PDF.")

        st.write("---")

    # ==========================================
    # SECCIÓN 4: BOTÓN 3 - GUÍA DE CORTES TALLER
    # ==========================================
    with st.expander("♻️ ¿Tienes pedacería en el taller? (Opcional)"):
        st.info("Ingresa centímetros separados por comas (ej: 120, 80). Para vidrio Ancho x Alto (ej: 90x60).")
        col_p1, col_p2, col_p3 = st.columns(3)
        with col_p1:
            ped_chambrana = st.text_input("Recortes Chambrana:", "")
            ped_cerco = st.text_input("Recortes Cerco:", "")
        with col_p2:
            ped_riel = st.text_input("Recortes Riel:", "")
            ped_traslape = st.text_input("Recortes Traslape:", "")
        with col_p3:
            ped_cabezal = st.text_input("Recortes Cabezal:", "")
            ped_zoclo = st.text_input("Recortes Zoclo:", "")
            ped_vidrio = st.text_input("Recortes Vidrio:", "")

    st.write("")
    
    # EL NUEVO BOTÓN ÚNICO Y MAESTRO PARA EL TALLER
    if st.button("✂️ Generar Guía de Cortes para Taller (PDF)", type="primary", use_container_width=True):
        try:
            from fpdf import FPDF
            import base64
            
            # Recolectar todos los cortes
            cortes_chambrana, cortes_riel, cortes_cerco, cortes_traslape, cortes_cabezal, cortes_zoclo = [], [], [], [], [], []
            vidrios_fijos, vidrios_corredizos, vidrios_puerta = [], [], []

            def agregar_cortes_con_rastreo(lista_destino, medidas, etiqueta):
                for m in medidas:
                    lista_destino.append({"medida": m, "etiqueta": etiqueta})
            
            for i, p in enumerate(st.session_state.proyecto):
                num_pieza = i + 1  
                if p['tipo'] == "Ventana Corrediza":
                    v = Ventana(p['ancho'], p['alto'], p['detalle'], "Blanco")
                    a_m, alt_l = v.calcular_cortes_marco()
                    alt_f, a_h = v.calcular_hoja_fija()
                    alt_c, _ = v.calcular_hoja_corrediza()
                    a_vf, alt_vf, _ = v.calcular_vidrio(alt_f, a_h)
                    a_vc, alt_vc, _ = v.calcular_vidrio(alt_c, a_h)
                    
                    agregar_cortes_con_rastreo(cortes_chambrana, [round(alt_l*100, 1), round(alt_l*100, 1)], f"L{num_pieza}")
                    agregar_cortes_con_rastreo(cortes_chambrana, [round(a_m*100, 1)], f"C{num_pieza}")
                    agregar_cortes_con_rastreo(cortes_riel, [round(a_m*100, 1)], f"P{num_pieza}")
                    agregar_cortes_con_rastreo(cortes_cerco, [round(alt_f*100, 1)], f"Fijo-P{num_pieza}")
                    agregar_cortes_con_rastreo(cortes_cerco, [round(alt_c*100, 1)], f"Corr-P{num_pieza}")
                    agregar_cortes_con_rastreo(cortes_traslape, [round(alt_f*100, 1)], f"Fijo-P{num_pieza}")
                    agregar_cortes_con_rastreo(cortes_traslape, [round(alt_c*100, 1)], f"Corr-P{num_pieza}")
                    agregar_cortes_con_rastreo(cortes_cabezal, [round(a_h*100, 1)], f"Fijo-P{num_pieza}")
                    agregar_cortes_con_rastreo(cortes_cabezal, [round(a_h*100, 1)], f"Corr-P{num_pieza}")
                    agregar_cortes_con_rastreo(cortes_zoclo, [round(a_h*100, 1)], f"Fijo-P{num_pieza}")
                    agregar_cortes_con_rastreo(cortes_zoclo, [round(a_h*100, 1)], f"Corr-P{num_pieza}")
                    
                    vidrios_fijos.append({"medida": f"{round(a_vf*100, 1)} x {round(alt_vf*100, 1)}", "etiqueta": f"P{num_pieza}"})
                    vidrios_corredizos.append({"medida": f"{round(a_vc*100, 1)} x {round(alt_vc*100, 1)}", "etiqueta": f"P{num_pieza}"})
                
                elif p['tipo'] == "Puerta":
                    puerta = Puerta(p['ancho'], p['alto'], p['detalle'], "Blanco")
                    cabezal_marco, laterales_marco = puerta.calcular_cortes_marco()
                    cerco_hoja, horizontales_hoja = puerta.calcular_cortes_hoja()
                    ancho_r, alto_r, cant_duelas = puerta.calcular_relleno()
                    vidrios_puerta.append({"medida": f"{round(ancho_r*100, 1)} x {round(alto_r*100, 1)}", "etiqueta": f"Vidrio-P{num_pieza}"})

            # Iniciar PDF
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

            # FUNCIÓN AUXILIAR PARA IMPRIMIR ALUMINIO EN EL PDF
            def pdf_imprimir_perfil(titulo, lista_cortes, ped_str):
                if not lista_cortes: return
                pdf.set_font("Arial", 'B', 11)
                pdf.set_fill_color(220, 220, 220)
                pdf.cell(0, 8, f" {titulo.upper()}", ln=True, fill=True)
                pdf.set_font("Arial", '', 10)
                
                tramos, ped_usada = optimizador_aluminio_taller(lista_cortes, ped_str)
                
                # Imprimir Pedacería
                for p_idx, p_data in ped_usada.items():
                    if p_data["usados"]:
                        usados_str = ", ".join([f"{u['medida']}cm (Mrc: {u['etiqueta']})" for u in p_data["usados"]])
                        sobra = p_data["tamano"] - (sum([u['medida'] for u in p_data["usados"]]) + len(p_data["usados"])*0.3)
                        pdf.cell(0, 6, f"  * De tu retazo de {p_data['tamano']}cm: Corta {usados_str}. [Sobra: {round(sobra,1)}cm]", ln=True)
                
                # Imprimir Tramos Nuevos
                for i, tramo in enumerate(tramos):
                    usados_str = ", ".join([f"{u['medida']}cm (Mrc: {u['etiqueta']})" for u in tramo])
                    sobra = 600.0 - (sum([u['medida'] for u in tramo]) + len(tramo)*0.3)
                    pdf.multi_cell(0, 6, f"  * Tramo {i+1} (6.00m): Corta {usados_str}. [Sobra: {round(sobra,1)}cm]")
                pdf.ln(4)

            # Escribir Aluminio
            pdf_imprimir_perfil("Chambranas", cortes_chambrana, ped_chambrana)
            pdf_imprimir_perfil("Rieles", cortes_riel, ped_riel)
            pdf_imprimir_perfil("Cercos", cortes_cerco, ped_cerco)
            pdf_imprimir_perfil("Traslapes", cortes_traslape, ped_traslape)
            pdf_imprimir_perfil("Cabezales de Hoja", cortes_cabezal, ped_cabezal)
            pdf_imprimir_perfil("Zoclos", cortes_zoclo, ped_zoclo)

            # Escribir Cristal
            pdf.ln(5)
            pdf.set_font("Arial", 'B', 12)
            pdf.set_fill_color(200, 220, 255)
            pdf.cell(0, 8, " MESA DE CRISTAL / VIDRIO", ln=True, fill=True)
            pdf.ln(4)
            
            todos_los_vidrios = vidrios_fijos + vidrios_corredizos + vidrios_puerta
            if todos_los_vidrios:
                hojas_vidrio, vidrios_rescatados, best_config = optimizador_vidrio(todos_los_vidrios, ped_vidrio)
                
                if vidrios_rescatados:
                    pdf.set_font("Arial", 'B', 10)
                    pdf.cell(0, 6, "RECORTES DEL TALLER:", ln=True)
                    pdf.set_font("Arial", '', 10)
                    for r in vidrios_rescatados:
                        p, ped = r["pieza"], r["pedazo"]
                        pdf.cell(0, 6, f"  - Del retazo {ped['original']}: Cortar {p['w']} x {p['h']} cm (Mrc: {p['etiqueta']})", ln=True)
                    pdf.ln(3)

                if hojas_vidrio:
                    ancho = int(best_config['ancho'])
                    texto_red = "(Reduccion 0.5 cm por lado aplicada)" if best_config['reducido'] else "(Medida exacta de corte)"
                    pdf.set_font("Arial", 'B', 11)
                    pdf.cell(0, 8, f"HOJAS NUEVAS ({ancho}x260 cm) {texto_red}:", ln=True)
                    
                    pdf.set_font("Arial", '', 10)
                    for i, h in enumerate(hojas_vidrio):
                        pdf.set_font("Arial", 'B', 10)
                        pdf.cell(0, 6, f" >> HOJA {i+1}:", ln=True)
                        pdf.set_font("Arial", '', 10)
                        for j, col in enumerate(h['columnas']):
                            for p in col['piezas']:
                                pdf.cell(0, 6, f"      [ ] Cortar: {p['w']} x {p['h']} cm   (Marcador: {p['etiqueta']})", ln=True)
                        pdf.ln(2)
            else:
                pdf.set_font("Arial", '', 10)
                pdf.cell(0, 8, "No se registró cristal en este proyecto.", ln=True)

            pdf_bytes = pdf.output(dest='S').encode('latin-1')
            b64 = base64.b64encode(pdf_bytes).decode()
            href = f'<a href="data:application/pdf;base64,{b64}" download="Guia_Cortes_{cliente_pdf}.pdf" target="_blank" style="text-decoration: none; padding: 12px; background-color: #007bff; color: white; border-radius: 5px; display: inline-block; text-align: center; width: 100%; font-size: 16px; font-weight: bold;">📥 Descargar Guía de Cortes para Taller</a>'
            
            st.markdown(href, unsafe_allow_html=True)
            st.balloons()
            
        except Exception as e:
            st.error(f"Error generando la guía de cortes: {e}")
