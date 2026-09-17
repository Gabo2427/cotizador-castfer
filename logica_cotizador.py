class Ventana:
    def __init__(self, ancho, alto, linea_aluminio, color, diseno="2 hojas", cuadricula=True):
        self.ancho = ancho
        self.alto = alto
        self.linea_aluminio = linea_aluminio
        self.color = color
        self.diseno = diseno # Opciones: "2 hojas" o "Fijo Gigante Centro"
        self.cuadricula = cuadricula
        
        # --- MEDIDAS GENERALES ---
        self.holgura_vidrio = 0.005 # 0.5 cm por lado que entra al perfil
        self.intermedio_frente = 0.036 # 3.6 cm viéndolo de frente
        self.intermedio_fondo = 0.026  # 2.6 cm
        
        # --- REGLAS SEGÚN LA LÍNEA ---
        if self.linea_aluminio == "3 pulgadas":
            self.desc_ancho_hoja = 0.190
            self.perfil_cerco_traslape = 0.065 
            self.perfil_zoclo = 0.085          
            self.perfil_cabezal = 0.045        
            self.descuento_marco_alto = 0.032  
            self.desc_4_hojas = 0.280 # <-- (ESTIMADO: Descuento para sacar 4 hojas)
        else: # 2 Pulgadas
            self.desc_ancho_hoja = 0.151       
            self.perfil_cerco_traslape = 0.043 
            self.perfil_zoclo = 0.070          
            self.perfil_cabezal = 0.035        
            self.descuento_marco_alto = 0.025  
            self.desc_4_hojas = 0.220 # <-- (ESTIMADO)

    def calcular_cortes_marco(self):
        ancho_horizontal = self.ancho - 0.005 
        alto_lateral = self.alto - self.descuento_marco_alto
        return round(ancho_horizontal, 3), round(alto_lateral, 3)

    def calcular_hojas(self):
        # Alto de las hojas
        alto_fija = self.alto - (0.035 if self.linea_aluminio == "3 pulgadas" else 0.030)
        alto_corr = alto_fija - 0.005 # La corrediza es 5mm más chica para que corra bien
        
        # Ancho de las hojas dependiendo del diseño
        if self.diseno == "2 hojas":
            ancho_hoja = (self.ancho - self.desc_ancho_hoja) / 2
            return {
                "fija": (round(alto_fija, 3), round(ancho_hoja, 3)),
                "corrediza": (round(alto_corr, 3), round(ancho_hoja, 3))
            }
            
        elif self.diseno == "Fijo Gigante Centro":
            # Calculamos como si fueran 4 hojas individuales
            ancho_sencillo = (self.ancho - self.desc_4_hojas) / 4
            # La hoja central es exactamente el doble
            ancho_gigante = ancho_sencillo * 2
            
            return {
                "fija_gigante": (round(alto_fija, 3), round(ancho_gigante, 3)),
                "corrediza_izq": (round(alto_corr, 3), round(ancho_sencillo, 3)),
                "corrediza_der": (round(alto_corr, 3), round(ancho_sencillo, 3))
            }

    def calcular_intermedios_aluminio(self, alto_hoja, ancho_hoja, es_gigante=False):
        """ Retorna los cortes exactos de perfil intermedio que requiere la hoja """
        if not self.cuadricula:
            return {"verticales": [], "horizontales": []}
            
        # El intermedio mide lo que mide la luz libre + 1cm para meterse a los canales
        alto_interior = alto_hoja - self.perfil_cabezal - self.perfil_zoclo
        largo_vertical = alto_interior + (self.holgura_vidrio * 2)
        
        ancho_interior = ancho_hoja - (self.perfil_cerco_traslape * 2)
        largo_horizontal = ancho_interior + (self.holgura_vidrio * 2)
        
        if not es_gigante:
            # Hoja normal: 1 Vertical, 2 Horizontales
            return {
                "verticales": [round(largo_vertical, 3)] * 1,
                "horizontales": [round(largo_horizontal, 3)] * 2
            }
        else:
            # Hoja Gigante Centro: Lleva 3 Verticales y 2 Horizontales largos 
            # para que los cuadritos cuadren perfecto con las corredizas.
            return {
                "verticales": [round(largo_vertical, 3)] * 3,
                "horizontales": [round(largo_horizontal, 3)] * 2
            }
