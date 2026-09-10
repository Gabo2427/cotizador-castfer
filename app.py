import streamlit as st
import json
from collections import Counter
from logica_cotizador import Ventana, Puerta
import db_manager

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
# BARRA LATERAL (ROLES Y FINANZAS)
# ==========================================
with st.sidebar:
    st.image("logopagina.png", use_container_width=True)
    st.title("📂 Control de Taller")
    
    # SISTEMA DE LOGIN (PIN)
    pin_acceso = st.text_input("🔑 PIN de Acceso:", type="password")
    
    if pin_acceso == "2026": 
        st.session_state.es_admin = True
        st.success("Modo Administrador: Desbloqueado")
    else:
        st.session_state.es_admin = False
        if pin_acceso != "":
            st.error("PIN incorrecto. Modo Taller activo.")
        else:
            st.info("Modo Taller: Solo cortes y medidas.")

    st.write("---")

    # TODO ESTO SOLO SE MUESTRA SI ES ADMIN
    if st.session_state.get('es_admin', False):
        st.subheader("💰 Finanzas del Proyecto")
        st.session_state.nombre_cliente = st.text_input("Cliente / Proyecto:", value=st.session_state.nombre_cliente)
        
        st.session_state.costo_total = st.number_input("Costo Total a Cobrar ($):", min_value=0.0, value=st.session_state.costo_total, step=100.0)
        st.session_state.anticipo = st.number_input("Anticipo Recibido ($):", min_value=0.0, value=st.session_state.anticipo, step=100.0)
        
        restante = st.session_state.costo_total - st.session_state.anticipo
        if restante > 0:
            st.warning(f"Falta por cobrar: **${restante:,.2f}**")
        elif st.session_state.costo_total > 0 and restante == 0:
            st.success("¡TRABAJO LIQUIDADO! ✅")
        else:
            st.info(f"Falta por cobrar: **${restante:,.2f}**")
        
        st.write("---")
        
        # Lógica de Guardado (Solo Admin)
        if len(st.session_state.proyecto) > 0:
            if st.button("💾 Guardar Trabajo", type="primary"):
                if st.session_state.nombre_cliente.strip() == "":
                    st.error("Ponle un nombre para guardarlo.")
                else:
                    if st.session_state.proyecto_activo_id:
                        db_manager.actualizar_proyecto(st.session_state.proyecto_activo_id, st.session_state.nombre_cliente, st.session_state.proyecto, st.session_state.costo_total, st.session_state.anticipo)
                    else:
                        db_manager.guardar_proyecto(st.session_state.nombre_cliente, st.session_state.proyecto, st.session_state.costo_total, st.session_state.anticipo)
                    st.success("¡Guardado correctamente!")
        else:
            st.info("Agrega piezas para poder guardar.")

        st.write("---")
        
        # Lógica de Apertura de Historial (Solo Admin) - ¡CORREGIDA AQUÍ!
        st.subheader("📁 Abrir Historial")
        proyectos_guardados = db_manager.obtener_proyectos()
        
        if proyectos_guardados:
            # Pasamos la lista directa y le damos formato visual
            seleccion = st.selectbox(
                "Selecciona un proyecto:", 
                options=proyectos_guardados,
                format_func=lambda p: f"👤 {p[1]}  |  📅 {p[2][:10]}",
                key="selector_historial"
            )
            
            col_abrir, col_borrar = st.columns(2)
            with col_abrir:
                if st.button("📂 Abrir", key="btn_abrir"):
                    # Ahora 'seleccion' guarda el proyecto completo directamente
                    st.session_state.proyecto_activo_id = seleccion[0]
                    st.session_state.nombre_cliente = seleccion[1]
                    st.session_state.proyecto = json.loads(seleccion[3])
                    st.session_state.costo_total = float(seleccion[4] if seleccion[4] else 0.0)
                    st.session_state.anticipo = float(seleccion[5] if seleccion[5] else 0.0)
                    st.session_state.edit_index = None
                    st.rerun()
            with col_borrar:
                if st.button("🗑️ Borrar", key="btn_borrar"):
                    # Borramos usando el ID de la selección directa
                    db_manager.borrar_proyecto(seleccion[0])
                    st.rerun()

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
    
    with st.expander("♻️ ¿Tienes pedacería en el taller? (Opcional)"):
        st.info("Ingresa la medida de tus recortes en centímetros, separados por comas. Si no tienes, déjalo en blanco.")
        col_p1, col_p2 = st.columns(2)
        with col_p1:
            ped_chambrana = st.text_input("Recortes de Chambrana:", "")
            ped_cerco = st.text_input("Recortes de Cerco:", "")
            ped_cabezal = st.text_input("Recortes de Cabezal:", "")
        with col_p2:
            ped_riel = st.text_input("Recortes de Riel:", "")
            ped_traslape = st.text_input("Recortes de Traslape:", "")
            ped_zoclo = st.text_input("Recortes de Zoclo:", "")

    st.write("")
    
    if st.button("🚀 Procesar Proyecto Optimizado", type="primary"):
        st.write("---")
        
        tab_cortes, tab_proveedor, tab_whatsapp = st.tabs([
            "🛠️ Cortes Agrupados (Sierra)", 
            "📦 Optimización y Compras", 
            "📱 Exportar a WhatsApp"
        ])
        
        # Diccionarios de rastreo para ventanas
        cortes_chambrana, cortes_riel, cortes_cerco, cortes_traslape, cortes_cabezal, cortes_zoclo = [], [], [], [], [], []
        vidrios_fijos, vidrios_corredizos = [], []

        # Diccionarios de rastreo para Puertas
        cortes_marco_puerta = [] 
        cortes_cerco_puerta = []
        cortes_horizontales_puerta = [] # Cabezal, Zoclo, Intermedio
        cortes_duela_puerta = []
        vidrios_puerta = []
        
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
                
                # Cortes Marco
                agregar_cortes_con_rastreo(cortes_marco_puerta, [round(laterales_marco*100, 1), round(laterales_marco*100, 1)], f"Marco-L{num_pieza}")
                agregar_cortes_con_rastreo(cortes_marco_puerta, [round(cabezal_marco*100, 1)], f"Marco-C{num_pieza}")
                
                # Cortes Hoja
                agregar_cortes_con_rastreo(cortes_cerco_puerta, [round(cerco_hoja*100, 1), round(cerco_hoja*100, 1)], f"Hoja-L{num_pieza}")
                # Zoclo, Cabezal hoja e Intermedio
                agregar_cortes_con_rastreo(cortes_horizontales_puerta, [round(horizontales_hoja*100, 1), round(horizontales_hoja*100, 1), round(horizontales_hoja*100, 1)], f"Hoja-Horiz-P{num_pieza}")
                
                # Relleno (Vidrio y Duelas)
                vidrios_puerta.append({"medida": f"{round(ancho_r*100, 1)} x {round(alto_r*100, 1)}", "etiqueta": f"Vidrio-P{num_pieza}"})
                # Generamos las piezas de duela multiplicadas por la cantidad requerida
                cortes_duela = [round(ancho_r*100, 1)] * cant_duelas
                agregar_cortes_con_rastreo(cortes_duela_puerta, cortes_duela, f"Duela-P{num_pieza}")

        # ==========================================
        # PESTAÑA 1: MESA DE CORTE (ETIQUETAS PRECISAS)
        # ==========================================
        with tab_cortes:
            st.header("📄 Lista para la Mesa de Corte")
            st.info("Corta estas medidas y usa un marcador para anotar la etiqueta.")
            
            def mostrar_grupo_rastreo(nombre, lista_dicts):
                if not lista_dicts: return
                agrupados = {}
                for item in lista_dicts:
                    m = item["medida"]
                    if m not in agrupados: agrupados[m] = []
                    agrupados[m].append(item["etiqueta"])
                    
                st.subheader(f"🔹 {nombre}")
                for medida in sorted(agrupados.keys(), reverse=True):
                    etiquetas = agrupados[medida]
                    cant = len(etiquetas)
                    vent_str = ", ".join(sorted(list(set(etiquetas))))
                    st.markdown(f"* Cortar **{cant}** piezas de `{medida} cm` *(Marcador: {vent_str})*")
            
            if len(cortes_chambrana) > 0:
                st.markdown("### 🪟 VENTANAS")
                mostrar_grupo_rastreo("Chambrana", cortes_chambrana)
                mostrar_grupo_rastreo("Riel", cortes_riel)
                mostrar_grupo_rastreo("Cerco", cortes_cerco)
                mostrar_grupo_rastreo("Traslape", cortes_traslape)
                mostrar_grupo_rastreo("Cabezal de Hoja", cortes_cabezal)
                mostrar_grupo_rastreo("Zoclo (2 Venas)", cortes_zoclo)
                st.markdown("---")
            
            if len(cortes_marco_puerta) > 0:
                st.markdown("### 🚪 PUERTAS")
                mostrar_grupo_rastreo("Marco Puerta", cortes_marco_puerta)
                mostrar_grupo_rastreo("Cerco Puerta", cortes_cerco_puerta)
                mostrar_grupo_rastreo("Horizontales Puerta (Zoclo, Cabezal, Intermedio)", cortes_horizontales_puerta)
                mostrar_grupo_rastreo("Duela Horizontal", cortes_duela_puerta)
                st.markdown("---")
            
            st.subheader("🪟 Medidas de Vidrio")
            mostrar_grupo_rastreo("Vidrios Fijos (Ventana)", vidrios_fijos)
            mostrar_grupo_rastreo("Vidrios Corredizos (Ventana)", vidrios_corredizos)
            mostrar_grupo_rastreo("Vidrios (Puerta)", vidrios_puerta)

        # ==========================================
        # MOTOR DE OPTIMIZACIÓN
        # ==========================================
        def parsear_pedaceria(texto):
            if not texto.strip(): return []
            try: return [float(x.strip()) for x in texto.split(',') if x.strip()]
            except: return []

        def optimizador_inteligente(cortes_num, pedaceria_str, tramo_ideal=600.0):
            pedaceria = parsear_pedaceria(pedaceria_str)
            cortes_ordenados = sorted(cortes_num, reverse=True)
            tramos_nuevos = []
            uso_ped = {i: {"tamano": p, "usados": []} for i, p in enumerate(pedaceria)}
            
            for corte in cortes_ordenados:
                corte_real = corte + 0.3 
                colocado = False
                
                for i in range(len(pedaceria)):
                    usado_ahora = sum(uso_ped[i]["usados"]) + (len(uso_ped[i]["usados"]) * 0.3)
                    if uso_ped[i]["tamano"] - usado_ahora >= corte_real:
                        uso_ped[i]["usados"].append(corte)
                        colocado = True
                        break
                if colocado: continue
                
                for tramo in tramos_nuevos:
                    usado_ahora = sum(tramo) + (len(tramo) * 0.3)
                    if tramo_ideal - usado_ahora >= corte_real:
                        tramo.append(corte)
                        colocado = True
                        break
                
                if not colocado: tramos_nuevos.append([corte])
                    
            return tramos_nuevos, uso_ped

        # ==========================================
        # PESTAÑA 2: OPTIMIZACIÓN Y COMPRAS
        # ==========================================
        with tab_proveedor:
            st.header("📦 Inventario y Tramos Nuevos")
            
            def mostrar_optimizacion(nombre, lista_dicts, ped_str):
                if not lista_dicts: return
                solo_medidas = [item["medida"] for item in lista_dicts]
                
                st.subheader(f"✅ {nombre}")
                tramos, ped_usada = optimizador_inteligente(solo_medidas, ped_str)
                
                pedaceria_activa = [v for v in ped_usada.values() if v["usados"]]
                if pedaceria_activa:
                    st.write("**♻️ Rescatado de la pedacería:**")
                    for p in pedaceria_activa:
                        sobra = p["tamano"] - (sum(p["usados"]) + (len(p["usados"])*0.3))
                        st.write(f"- Del recorte de `{p['tamano']} cm` sacamos: {p['usados']} *(Te sobran {round(sobra,1)} cm)*")
                
                if tramos:
                    st.write(f"**🛒 Comprar {len(tramos)} tramos de 6.00m:**")
                    for i, t in enumerate(tramos):
                        sobra = 600.0 - (sum(t) + (len(t)*0.3))
                        st.write(f"- Tramo {i+1}: {t} *(Sobra {round(sobra,1)} cm)*")
                else:
                    st.success("¡Cero compras! Todo salió de los recortes que tenías.")
                st.write("---")

            # Ventanas
            mostrar_optimizacion("Chambrana", cortes_chambrana, ped_chambrana)
            mostrar_optimizacion("Riel", cortes_riel, ped_riel)
            mostrar_optimizacion("Cercos", cortes_cerco, ped_cerco)
            mostrar_optimizacion("Traslapes", cortes_traslape, ped_traslape)
            mostrar_optimizacion("Cabezal de Hoja", cortes_cabezal, ped_cabezal)
            mostrar_optimizacion("Zoclo", cortes_zoclo, ped_zoclo)
            
            # Puertas
            mostrar_optimizacion("Marco Puerta", cortes_marco_puerta, "")
            mostrar_optimizacion("Cerco Puerta", cortes_cerco_puerta, "")
            mostrar_optimizacion("Horizontales Puerta (Zoclo, Cabezal, Intermedio)", cortes_horizontales_puerta, "")
            mostrar_optimizacion("Duelas", cortes_duela_puerta, "")

        # ==========================================
        # PESTAÑA 3: WHATSAPP
        # ==========================================
        with tab_whatsapp:
            st.header("📱 Exportar a WhatsApp")
            st.info("Haz clic en el ícono de las dos hojas (📋) en la esquina superior derecha para copiar.")
            
            texto_wa = "🪟 *LISTA DE CORTES CASTFER*\n\n"
            def txt_grupo_rastreo(nombre, lista_dicts):
                if not lista_dicts: return ""
                t = f"*{nombre}:*\n"
                agrupados = {}
                for item in lista_dicts:
                    m = item["medida"]
                    if m not in agrupados: agrupados[m] = []
                    agrupados[m].append(item["etiqueta"])
                
                for medida in sorted(agrupados.keys(), reverse=True):
                    etiquetas = agrupados[medida]
                    cant = len(etiquetas)
                    vent_str = ", ".join(sorted(list(set(etiquetas))))
                    t += f"- {cant} pzs de {medida} cm (Marcar: {vent_str})\n"
                return t + "\n"
                
            if len(cortes_chambrana) > 0:
                texto_wa += "--- VENTANAS ---\n"
                texto_wa += txt_grupo_rastreo("MARCO CHAMBRANA", cortes_chambrana)
                texto_wa += txt_grupo_rastreo("MARCO RIEL", cortes_riel)
                texto_wa += txt_grupo_rastreo("CERCOS", cortes_cerco)
                texto_wa += txt_grupo_rastreo("TRASLAPES", cortes_traslape)
                texto_wa += txt_grupo_rastreo("CABEZALES HOJA", cortes_cabezal)
                texto_wa += txt_grupo_rastreo("ZOCLOS", cortes_zoclo)
            
            if len(cortes_marco_puerta) > 0:
                texto_wa += "--- PUERTAS ---\n"
                texto_wa += txt_grupo_rastreo("MARCO PUERTA", cortes_marco_puerta)
                texto_wa += txt_grupo_rastreo("CERCO PUERTA", cortes_cerco_puerta)
                texto_wa += txt_grupo_rastreo("ZOCLO/CABEZAL/INTERMEDIO PUERTA", cortes_horizontales_puerta)
                texto_wa += txt_grupo_rastreo("DUELAS HORIZONTALES", cortes_duela_puerta)
            
            texto_wa += "*VIDRIOS:*\n"
            texto_wa += txt_grupo_rastreo("Fijos Ventana", vidrios_fijos)
            texto_wa += txt_grupo_rastreo("Corredizos Ventana", vidrios_corredizos)
            texto_wa += txt_grupo_rastreo("Vidrios Puerta", vidrios_puerta)

            st.code(texto_wa, language="markdown")
            
