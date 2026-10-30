🪟 Cotizador CASTFER - Sistema Inteligente para Taller de Aluminio
Plataforma web desarrollada en Python y Streamlit diseñada para optimizar y administrar operaciones de un taller de aluminio y vidrio. El sistema abarca desde la cotización inicial para el cliente hasta la generación de algoritmos de pedacería y despiece milimétrico para la mesa de trabajo.

🚀 Características Principales
-Sistemas de Manufactura Integrados: Soporte algorítmico para cálculos de Línea Nacional (Estándar) y Línea Premium (Eurovent S35, S50, S60, S70, S140), incluyendo holguras precisas y perfiles específicos.
-Motor de Optimización (1D y 2D):
  -Aluminio (1D): Algoritmo de corte lineal que maximiza el uso de tramos de 6 metros e incorpora retazos existentes (pedacería) para minimizar el desperdicio.
  -Cristal (2D): Algoritmo tipo Tetris (Bin Packing) para el acomodo inteligente de piezas de vidrio en hojas estándar (ej. 180x260 cm y 230x260 cm).
-Generación Automática de PDFs:
  -Recibo de Cliente: Cotización formal con desglose financiero, anticipos y saldos pendientes.
  -Orden de Compra (Proveedor): Lista exacta de tramos de 6m a comprar, herrajes (carretillas, jaladeras), metros de vinil y hojas de cristal.
  -Guía de Mesa de Trabajo: Documento detallado para el armador con instrucciones de cortes exactos, uso de retazos y sobrantes esperados.
-Control de Producción por Fases: Permite seleccionar qué piezas específicas se van a "Fabricar HOY", ajustando la lista de materiales y cortes dinámicamente.
-Gestión de Base de Datos: Guardado, carga y actualización de proyectos en tiempo real mediante SQLite local, evitando duplicidad de registros.
-Modo Administrador: Acceso protegido mediante PIN de seguridad para gestionar precios por $m^2$, anticipos y finanzas globales.

🛠️ Tecnologías Utilizadas
-Frontend & Framework: Streamlit (UI reactiva e interactiva).
-Backend: Python 3.x
-Base de Datos: SQLite3 (db_manager.py)
-Generación de Reportes: fpdf2 (Renderizado de PDFs en base64 nativo).
-Algoritmos de Cálculo: Lógica orientada a objetos (logica_cotizador.py) con clases especializadas por tipo de ventana y puerta.

⚙️ Instalación y Uso Local

1.-Clonar el repositorio:
git clone https://github.com/Gabo2427/cotizador-castfer.git
cd cotizador-castfer

2.-Instalar dependencias:
  Asegúrate de tener Python instalado y ejecuta:
  pip install streamlit fpdf
  
3.-Ejecutar la aplicación:
  streamlit run app.py
  La aplicación se abrirá automáticamente en tu navegador web por defecto (usualmente en http://localhost:8501).

📂 Estructura del Proyecto
cotizador-castfer/
│
├── app.py                  # Archivo principal de Streamlit (Interfaz y Controladores)
├── db_manager.py           # Gestor de base de datos SQLite (CRUD de proyectos)
├── logica_cotizador.py     # Clases, matemáticas de perfiles, holguras y cálculos de vidrio
├── logopagina.png          # Asset gráfico para la UI y los reportes PDF
└── README.md               # Documentación del proyecto

🏗️ Próximas Mejoras (Roadmap)
Refactorización SRP (Single Responsibility Principle): Migración de toda la lógica de renderizado FPDF hacia un módulo externo (pdf_generator.py) para mantener app.py exclusivamente como capa de vista.

Autenticación en la Nube: Migración de SQLite a una base de datos en la nube (ej. Supabase o Firebase) para accesibilidad multiplataforma en el taller.

Gestión Visual de Retazos: Interfaz gráfica para visualizar cómo quedará el vidrio cortado en la hoja de 260cm.
