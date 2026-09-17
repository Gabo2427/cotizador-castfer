# =======================================================
# LÓGICA EXCLUSIVA PARA VENTANAS
# =======================================================
class Ventana:
    def __init__(self, ancho, alto, linea_aluminio, color, division_horizontal=False, diseno="2 hojas", cuadricula=False):
        self.ancho = ancho
        self.alto = alto
        self.linea_aluminio = linea_aluminio
        self.color = color
        self.division_horizontal = division_horizontal
        self.diseno = diseno
        self.cuadricula = cuadricula
        
        # --- MEDIDAS GENERALES ---
        self.holgura_vidrio = 0.005 # 0.5 cm por lado
        self.intermedio_frente = 0.036 # 3.6 cm viéndolo de frente
        self.intermedio_fondo = 0.026  # 2.6 cm
        
        # --- REGLAS SEGÚN LA LÍNEA ---
        if self.linea_aluminio == "3 pulgadas":
            self.desc_ancho_hoja = 0.190
            self.perfil_cerco_traslape = 0.065 
            self.perfil_zoclo = 0.085          
            self.perfil_cabezal = 0.045        
            self.descuento_marco_alto = 0.032  
            self.desc_4_hojas = 0.280 
        else: # 2 Pulgadas
            self.desc_ancho_hoja = 0.151       
            self.perfil_cerco_traslape = 0.043 
            self.perfil_zoclo = 0.070          
            self.perfil_cabezal = 0.035        
            self.descuento_marco_alto = 0.025  
            self.desc_4_hojas = 0.220 

    def calcular_cortes_marco(self):
        ancho_horizontal = self.ancho - 0.005 
        alto_lateral = self.alto - self.descuento_marco_alto
        return round(ancho_horizontal, 3), round(alto_lateral, 3)

    def calcular_hoja_fija(self):
        if self.diseno == "Fijo Gigante Centro":
            ancho_sencillo = (self.ancho - self.desc_4_hojas) / 4
            corte_ancho = ancho_sencillo * 2
        else:
            corte_ancho = (self.ancho - self.desc_ancho_hoja) / 2
        
        if self.division_horizontal:
            luz_libre_total = self.alto - self.descuento_marco_alto - self.intermedio_fondo
            corte_alto = (luz_libre_total / 2) + self.intermedio_fondo
        else:
            corte_alto = self.alto - (0.035 if self.linea_aluminio == "3 pulgadas" else 0.030)
            
        return round(corte_alto, 3), round(corte_ancho, 3)

    def calcular_hoja_corrediza(self):
        alto_fija, ancho_fija = self.calcular_hoja_fija()
        
        if self.diseno == "Fijo Gigante Centro":
            corte_ancho = (self.ancho - self.desc_4_hojas) / 4
        else:
            corte_ancho = ancho_fija
            
        corte_alto = alto_fija - 0.005
        return round(corte_alto, 3), round(corte_ancho, 3)

    def calcular_vidrio(self, corte_alto_hoja, corte_ancho_hoja):
        # Mantenemos esta función intacta para que no rompa app.py 
        # (El cálculo especializado de vidrio de 6 cuadros lo haremos en el siguiente paso)
        alto_interior = corte_alto_hoja - self.perfil_cabezal - self.perfil_zoclo
        ancho_interior = corte_ancho_hoja - (self.perfil_cerco_traslape * 2)
        
        alto_vidrio_real = alto_interior + (self.holgura_vidrio * 2)
        ancho_vidrio_real = ancho_interior + (self.holgura_vidrio * 2)
        area_por_vidrio = alto_vidrio_real * ancho_vidrio_real
        
        return round(ancho_vidrio_real, 3), round(alto_vidrio_real, 3), round(area_por_vidrio, 3)

    def calcular_intermedios_aluminio(self, alto_hoja, ancho_hoja, es_gigante=False):
        if not self.cuadricula:
            return {"verticales": [], "horizontales": []}
            
        alto_interior = alto_hoja - self.perfil_cabezal - self.perfil_zoclo
        largo_vertical = alto_interior + (self.holgura_vidrio * 2)
        
        ancho_interior = ancho_hoja - (self.perfil_cerco_traslape * 2)
        largo_horizontal = ancho_interior + (self.holgura_vidrio * 2)
        
        if not es_gigante:
            return {
                "verticales": [round(largo_vertical, 3)] * 1,
                "horizontales": [round(largo_horizontal, 3)] * 2
            }
        else:
            return {
                "verticales": [round(largo_vertical, 3)] * 3,
                "horizontales": [round(largo_horizontal, 3)] * 2
            }

# =======================================================
# ALGORITMO DE OPTIMIZACIÓN DE CORTES (Bin Packing)
# =======================================================
def optimizar_tramos(lista_cortes_cm, longitud_tramo_cm=610.0, disco_cm=0.3):
    if not lista_cortes_cm:
        return []
    
    cortes_ordenados = sorted(lista_cortes_cm, reverse=True)
    tramos = [] 
    
    for corte in cortes_ordenados:
        colocado = False
        for tramo in tramos:
            espacio_ocupado = sum(tramo) + (len(tramo) * disco_cm)
            if (espacio_ocupado + corte) <= longitud_tramo_cm:
                tramo.append(corte)
                colocado = True
                break
        
        if not colocado:
            tramos.append([corte])
            
    return tramos

# =======================================================
# LÓGICA EXCLUSIVA PARA PUERTAS
# =======================================================
class Puerta:
    def __init__(self, ancho, alto, detalle, color):
        self.ancho = ancho 
        self.alto = alto 
        self.detalle = detalle
        self.color = color

    def calcular_cortes_marco(self):
        ancho_cm = self.ancho * 100
        alto_cm = self.alto * 100
        
        cabezal_marco = ancho_cm - 0.2
        laterales_marco = alto_cm - 1.8
        
        return cabezal_marco / 100.0, laterales_marco / 100.0

    def calcular_cortes_hoja(self):
        ancho_cm = self.ancho * 100
        alto_cm = self.alto * 100
        
        cerco_hoja = alto_cm - 3.1 
        horizontal_hoja = ancho_cm - 13.6
        
        return cerco_hoja / 100.0, horizontal_hoja / 100.0

    def calcular_relleno(self):
        cerco_hoja = (self.alto * 100) - 3.1
        horizontal_hoja = (self.ancho * 100) - 13.6
        
        espacio_libre_vertical = cerco_hoja - 15.0 - 3.5
        alto_mitad_libre = espacio_libre_vertical / 2.0
        
        ancho_corte_relleno = horizontal_hoja + 1.5
        alto_corte_relleno = alto_mitad_libre + 1.5
        
        import math
        cantidad_duelas = math.ceil(alto_corte_relleno / 12.5)
        
        return ancho_corte_relleno / 100.0, alto_corte_relleno / 100.0, cantidad_duelas
