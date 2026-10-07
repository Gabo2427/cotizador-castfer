import math

# =======================================================
# LÓGICA EXCLUSIVA PARA VENTANAS Y FIJOS (LÍNEA NACIONAL)
# =======================================================
class Ventana:
    def __init__(self, ancho, alto, linea_aluminio, color, division_horizontal=False, diseno="2 hojas", cuadricula=False, tipo_cuadricula="2x3"):
        self.ancho = ancho
        self.alto = alto
        self.linea_aluminio = linea_aluminio
        self.color = color
        self.division_horizontal = division_horizontal
        self.diseno = diseno
        self.cuadricula = cuadricula
        self.tipo_cuadricula = tipo_cuadricula
        
        if self.cuadricula:
            try:
                c_str, r_str = self.tipo_cuadricula.split('x')
                self.cols_hoja = int(c_str)
                self.filas_hoja = int(r_str)
            except:
                self.cols_hoja = 2
                self.filas_hoja = 3
        else:
            self.cols_hoja = 1
            self.filas_hoja = 1

        self.intermedio_frente = 0.036 
        self.intermedio_fondo = 0.026  
        
        if self.linea_aluminio == "3 pulgadas":
            self.desc_ancho_hoja = 0.190
            self.perfil_cerco_traslape = 0.065 
            self.perfil_zoclo = 0.060          
            self.perfil_cabezal = 0.036        
            self.descuento_marco_alto = 0.032  
            self.desc_4_hojas = 0.280 
            self.desc_3_hojas = 0.231
        else: # 2 Pulgadas
            self.desc_ancho_hoja = 0.151       
            self.perfil_cerco_traslape = 0.043 
            self.perfil_zoclo = 0.070          
            self.perfil_cabezal = 0.035        
            self.descuento_marco_alto = 0.025  
            self.desc_4_hojas = 0.220 
            self.desc_3_hojas = 0.180 

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

    def calcular_3_hojas(self):
        zoclo_corr = (self.ancho - self.desc_3_hojas) / 3
        zoclo_fija_ext = zoclo_corr + 0.013 
        cerco_fija_ext = self.alto - 0.005
        cerco_corr_normal = self.alto - 0.046
        cerco_corr_doble = self.alto - 0.049

        return {
            "fija_ext": (round(cerco_fija_ext, 3), round(zoclo_fija_ext, 3)),
            "corr_normal": (round(cerco_corr_normal, 3), round(zoclo_corr, 3)),
            "corr_doble": (round(cerco_corr_doble, 3), round(zoclo_corr, 3))
        }

    def calcular_hojas(self):
        if self.diseno == "2 hojas":
            alto_fija, ancho_fija = self.calcular_hoja_fija()
            alto_corr, ancho_corr = self.calcular_hoja_corrediza()
            return {
                "fija": (round(alto_fija, 3), round(ancho_fija, 3)),
                "corrediza": (round(alto_corr, 3), round(ancho_corr, 3))
            }
        elif self.diseno == "Fijo Gigante Centro":
            alto_fija, ancho_fija = self.calcular_hoja_fija()
            alto_corr, ancho_corr = self.calcular_hoja_corrediza()
            return {
                "fija_gigante": (round(alto_fija, 3), round(ancho_fija, 3)),
                "corrediza_izq": (round(alto_corr, 3), round(ancho_corr, 3)),
                "corrediza_der": (round(alto_corr, 3), round(ancho_corr, 3))
            }
        elif self.diseno == "3 hojas (1 Fija Ext, 2 Corr)":
            return self.calcular_3_hojas()

    def calcular_vidrio(self, corte_alto_hoja, corte_ancho_hoja):
        holgura = 0.015
        ancho_vidrio_real = corte_ancho_hoja + holgura
        alto_vidrio_real = corte_alto_hoja - (self.perfil_zoclo + self.perfil_cabezal) + holgura
        area_por_vidrio = alto_vidrio_real * ancho_vidrio_real
        return round(ancho_vidrio_real, 3), round(alto_vidrio_real, 3), round(area_por_vidrio, 3)

    def calcular_intermedios_aluminio(self, alto_hoja, ancho_hoja, es_gigante=False):
        if not self.cuadricula: return {"verticales": [], "horizontales": []}
        largo_vertical = (alto_hoja - self.perfil_zoclo - self.perfil_cabezal) + (0.005 * 2)
        largo_horizontal = ancho_hoja + (0.005 * 2)
        if not es_gigante:
            num_vert = self.cols_hoja - 1
            num_horz = self.filas_hoja - 1
            return {"verticales": [round(largo_vertical, 3)] * num_vert, "horizontales": [round(largo_horizontal, 3)] * num_horz}
        else:
            num_vert = (self.cols_hoja * 2) - 1
            num_horz = self.filas_hoja - 1
            return {"verticales": [round(largo_vertical, 3)] * num_vert, "horizontales": [round(largo_horizontal, 3)] * num_horz}

class FijoNacional:
    def __init__(self, ancho, alto, linea_aluminio):
        self.ancho = ancho
        self.alto = alto
        self.linea_aluminio = linea_aluminio
        
        if self.linea_aluminio == "3 pulgadas":
            self.desc_bolsa_horizontal = 0.005 # 0.5 cm
            self.desc_bolsa_vertical = 0.045   # 4.5 cm
            self.desc_vidrio = 0.021           # 2.1 cm perimetral (Revisar en taller)
        else: # 2 Pulgadas
            self.desc_bolsa_horizontal = 0.005
            self.desc_bolsa_vertical = 0.035
            self.desc_vidrio = 0.015

    def calcular_cortes(self):
        bolsa_horizontal = self.ancho - self.desc_bolsa_horizontal
        bolsa_vertical = self.alto - self.desc_bolsa_vertical
        return round(bolsa_horizontal, 3), round(bolsa_vertical, 3)

    def calcular_vidrio(self):
        ancho_vidrio = self.ancho - self.desc_vidrio
        alto_vidrio = self.alto - self.desc_vidrio
        area = ancho_vidrio * alto_vidrio
        return round(ancho_vidrio, 3), round(alto_vidrio, 3), round(area, 3)

class Puerta:
    def __init__(self, ancho, alto, detalle, color):
        self.ancho = ancho 
        self.alto = alto 
        self.detalle = detalle
        self.color = color

    def calcular_cortes_marco(self):
        return (self.ancho * 100 - 0.2) / 100.0, (self.alto * 100 - 1.8) / 100.0

    def calcular_cortes_hoja(self):
        return (self.alto * 100 - 3.1) / 100.0, (self.ancho * 100 - 13.6) / 100.0

    def calcular_relleno(self):
        cerco_hoja = (self.alto * 100) - 3.1
        horizontal_hoja = (self.ancho * 100) - 13.6
        alto_corte_relleno = ((cerco_hoja - 15.0 - 3.5) / 2.0) + 1.5
        ancho_corte_relleno = horizontal_hoja + 1.5
        cantidad_duelas = math.ceil(alto_corte_relleno / 12.5)
        return ancho_corte_relleno / 100.0, alto_corte_relleno / 100.0, cantidad_duelas


# =======================================================
# LÓGICA EXCLUSIVA LÍNEA PREMIUM (EUROVENT)
# =======================================================

class FijoEurovent:
    def __init__(self, ancho, alto, serie="Serie 35"):
        self.ancho = ancho
        self.alto = alto
        self.serie = serie

    def calcular_cortes(self):
        bolsa_vertical = self.alto
        horizontales = self.ancho - 0.090 
        return round(bolsa_vertical, 3), round(horizontales, 3)

    def calcular_vidrio(self):
        ancho_vidrio = self.ancho - 0.075
        alto_vidrio = self.alto - 0.075
        area = ancho_vidrio * alto_vidrio
        return round(ancho_vidrio, 3), round(alto_vidrio, 3), round(area, 3)

class FijoEuroventS60:
    def __init__(self, ancho, alto):
        self.ancho = ancho
        self.alto = alto

    def calcular_cortes(self):
        vertical = self.alto
        horizontal = self.ancho - 0.045 
        return round(vertical, 3), round(horizontal, 3)

    def calcular_vidrio(self):
        ancho_vidrio = self.ancho - 0.057
        alto_vidrio = self.alto - 0.057
        area = ancho_vidrio * alto_vidrio
        return round(ancho_vidrio, 3), round(alto_vidrio, 3), round(area, 3)

class FijoEuroventS140:
    def __init__(self, ancho, alto):
        self.ancho = ancho
        self.alto = alto

    def calcular_cortes(self):
        vertical = self.alto
        horizontal = self.ancho - 0.102 
        return round(vertical, 3), round(horizontal, 3)

    def calcular_vidrio(self):
        ancho_vidrio = self.ancho - 0.085
        alto_vidrio = self.alto - 0.085
        area = ancho_vidrio * alto_vidrio
        return round(ancho_vidrio, 3), round(alto_vidrio, 3), round(area, 3)

class VentanaEuroventS50:
    def __init__(self, ancho, alto, diseno="2 hojas (X-X / O-X)"):
        self.ancho = ancho
        self.alto = alto
        self.diseno = diseno

    def calcular_cortes_marco(self):
        jamba = self.alto
        riel_cabezal = self.ancho - 0.020 
        return round(riel_cabezal, 3), round(jamba, 3)

    def calcular_hojas(self):
        cerco_traslape = self.alto - 0.066 
        if "3 hojas" in self.diseno: zoclo = (self.ancho / 3.0) + 0.010 
        elif "4 hojas" in self.diseno: zoclo = (self.ancho / 4.0) + 0.015
        else: zoclo = (self.ancho / 2.0) - 0.002 
        return round(cerco_traslape, 3), round(zoclo, 3)

    def calcular_vidrio(self):
        alto_vidrio = self.alto - 0.160 
        if "3 hojas" in self.diseno: ancho_vidrio = (self.ancho / 3.0) - 0.070
        elif "4 hojas" in self.diseno: ancho_vidrio = (self.ancho / 4.0) - 0.075
        else: ancho_vidrio = (self.ancho / 2.0) - 0.084 
        area = ancho_vidrio * alto_vidrio
        return round(ancho_vidrio, 3), round(alto_vidrio, 3), round(area, 3)

class VentanaEuroventS60:
    def __init__(self, ancho, alto, diseno="2 hojas (X-X / O-X)"):
        self.ancho = ancho
        self.alto = alto
        self.diseno = diseno

    def calcular_cortes_marco(self):
        jamba = self.alto
        riel_cabezal = self.ancho 
        return round(riel_cabezal, 3), round(jamba, 3)

    def calcular_hojas(self):
        cerco_traslape = self.alto - 0.057 
        if "3 hojas" in self.diseno: zoclo = (self.ancho / 3.0) + 0.012
        elif "4 hojas" in self.diseno: zoclo = (self.ancho / 4.0) + 0.015
        else: zoclo = (self.ancho / 2.0) 
        return round(cerco_traslape, 3), round(zoclo, 3)

    def calcular_vidrio(self):
        alto_vidrio = self.alto - 0.138 
        if "3 hojas" in self.diseno: ancho_vidrio = (self.ancho / 3.0) - 0.065
        elif "4 hojas" in self.diseno: ancho_vidrio = (self.ancho / 4.0) - 0.072
        else: ancho_vidrio = (self.ancho / 2.0) - 0.082 
        area = ancho_vidrio * alto_vidrio
        return round(ancho_vidrio, 3), round(alto_vidrio, 3), round(area, 3)

class VentanaEuroventS70:
    def __init__(self, ancho, alto, diseno="2 hojas (X-X / O-X)"):
        self.ancho = ancho
        self.alto = alto
        self.diseno = diseno

    def calcular_cortes_marco(self):
        jamba = self.alto
        riel_cabezal = self.ancho - 0.026 
        return round(riel_cabezal, 3), round(jamba, 3)

    def calcular_hojas(self):
        cerco_traslape = self.alto - 0.066 
        if "3 hojas" in self.diseno: zoclo = (self.ancho / 3.0) + 0.015
        elif "4 hojas" in self.diseno: zoclo = (self.ancho / 4.0) + 0.018
        else: zoclo = (self.ancho / 2.0) 
        return round(cerco_traslape, 3), round(zoclo, 3)

    def calcular_vidrio(self):
        alto_vidrio = self.alto - 0.191 
        if "3 hojas" in self.diseno: ancho_vidrio = (self.ancho / 3.0) - 0.085
        elif "4 hojas" in self.diseno: ancho_vidrio = (self.ancho / 4.0) - 0.090
        else: ancho_vidrio = (self.ancho / 2.0) - 0.104 
        area = ancho_vidrio * alto_vidrio
        return round(ancho_vidrio, 3), round(alto_vidrio, 3), round(area, 3)

class VentanaProyeccionBatienteEuroventS35:
    def __init__(self, ancho, alto, diseno="1 hoja (Proyección)", mosquitero=False):
        self.ancho = ancho
        self.alto = alto
        self.diseno = diseno
        self.mosquitero = mosquitero

    def calcular_cortes_marco(self):
        return round(self.ancho, 3), round(self.alto, 3)

    def calcular_hojas(self):
        if "2 hojas" in self.diseno:
            corte_ancho = (self.ancho / 2.0) - 0.038  
            corte_alto = self.alto - 0.040            
            intermedio = self.alto - 0.048            
            return round(corte_alto, 3), round(corte_ancho, 3), round(intermedio, 3)
        else:
            corte_ancho = self.ancho - 0.048          
            corte_alto = self.alto - 0.048            
            return round(corte_alto, 3), round(corte_ancho, 3), 0.0

    def calcular_vidrio(self):
        if "2 hojas" in self.diseno:
            ancho_vidrio = (self.ancho / 2.0) - 0.103 
            alto_vidrio = self.alto - 0.114           
        else:
            ancho_vidrio = self.ancho - 0.115         
            alto_vidrio = self.alto - 0.115           
        area = ancho_vidrio * alto_vidrio
        return round(ancho_vidrio, 3), round(alto_vidrio, 3), round(area, 3)

    def calcular_mosquitero(self):
        if not self.mosquitero: return 0.0, 0.0
        if "2 hojas" in self.diseno:
            alto_mosq = self.alto - 0.068             
            ancho_mosq = (self.ancho / 2.0) - 0.059   
        else:
            alto_mosq = self.alto - 0.069             
            ancho_mosq = self.ancho - 0.069           
        return round(alto_mosq, 3), round(ancho_mosq, 3)

class PuertaComercialEuroventS50:
    def __init__(self, ancho, alto, diseno="1 hoja"):
        self.ancho = ancho
        self.alto = alto
        self.diseno = diseno

    def calcular_cortes_marco(self):
        cabezal = self.ancho - 0.002
        laterales = self.alto - 0.018
        return round(cabezal, 3), round(laterales, 3)

    def calcular_hojas(self):
        cerco = self.alto - 0.044
        if "2 hojas" in self.diseno: horizontal_hoja = (self.ancho / 2.0) - 0.038
        else: horizontal_hoja = self.ancho - 0.051
        return round(cerco, 3), round(horizontal_hoja, 3)

    def calcular_vidrio(self):
        if "2 hojas" in self.diseno:
            ancho_vidrio = (self.ancho / 2.0) - 0.120
            alto_vidrio = self.alto - 0.180
        else:
            ancho_vidrio = self.ancho - 0.171
            alto_vidrio = self.alto - 0.171
        area = ancho_vidrio * alto_vidrio
        return round(ancho_vidrio, 3), round(alto_vidrio, 3), round(area, 3)

class PuertaResidencialEuroventS50:
    def __init__(self, ancho, alto, diseno="1 hoja"):
        self.ancho = ancho
        self.alto = alto
        self.diseno = diseno

    def calcular_cortes_marco(self):
        cabezal = self.ancho - 0.002
        laterales = self.alto - 0.018
        return round(cabezal, 3), round(laterales, 3)

    def calcular_hojas(self):
        cerco = self.alto - 0.044
        if "2 hojas" in self.diseno: horizontal_hoja = (self.ancho / 2.0) - 0.165
        else: horizontal_hoja = self.ancho - 0.268
        return round(cerco, 3), round(horizontal_hoja, 3)

    def calcular_vidrio(self):
        if "2 hojas" in self.diseno:
            ancho_vidrio = (self.ancho / 2.0) - 0.154
            alto_vidrio = self.alto - 0.224 
        else:
            ancho_vidrio = self.ancho - 0.349
            alto_vidrio = self.alto - 0.349
        area = ancho_vidrio * alto_vidrio
        return round(ancho_vidrio, 3), round(alto_vidrio, 3), round(area, 3)
