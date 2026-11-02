# Script auxiliar para generar el archivo README.md completo y pedagógico
import pathlib

readme_content = """# ⚡ NEXODIGITAL - Soluciones Web y Plataforma Digital Comercial

> **Manual de Arquitectura, Guía Técnica y Documentación Pedagógica Completa**  
> Proyecto desarrollado con **Python 3**, **Flask**, **Jinja2**, **Flask-WTF / WTForms**, **Bootstrap 5** y **JavaScript (ES6+)**.

---

## 👥 Información Académica y Créditos del Proyecto

- **Institución:** Universidad Estatal Amazónica (UEA)
- **Carrera:** Licenciatura / Ingeniería en Tecnologías de la Información
- **Nivel Académico:** Cuarto Semestre
- **Asignatura:** Desarrollo de Aplicaciones Web
- **Equipo de Desarrollo:**
  1. **Cinthia Mishel Carrión Serrano**
  2. **Aracely Maribel Quintanilla Rumipamba**
  3. **Santiago Andrés Lara Caicedo**

---

## 🎯 ¿Qué es NexoDigital y Cuál es su Propósito?

**NexoDigital** es una iniciativa de emprendimiento tecnológico orientada a la transformación digital de pequeños negocios, comercios locales, emprendimientos y profesionales independientes en el Ecuador (con presencia en Quito, Puyo y atención en línea a nivel nacional).

La plataforma cumple una doble función esencial:
1. **Sitio Web Institucional:** Presenta la empresa, su visión, misión, propuesta de valor, catálogo de servicios con precios transparentes, video demostrativo, formulario de contacto interactivo y módulo de registro de requerimientos rápidos con almacenamiento local.
2. **Panel de Gestión Comercial (Backoffice):** Permite administrar en tiempo real los servicios del catálogo, la cartera de clientes, los proveedores de infraestructura tecnológica y emitir **Facturas de Venta** y **Cotizaciones / Proformas Comerciales** con cálculo dinámico de subtotal, IVA (15% vigente en Ecuador), anticipos recibidos y saldo pendiente de cobro.

---

## 📚 Fundamentos Teóricos: Guía para Aprender y Entender el Código

Esta sección explica los conceptos clave de la ingeniería de software web utilizados en este proyecto, para que cualquier estudiante o evaluador comprenda **el porqué de cada decisión técnica**.

```
                           ARQUITECTURA DE NEXODIGITAL
                           
       NAVEGADOR WEB (Cliente)                      SERVIDOR (Backend Flask)
 ┌───────────────────────────────────┐        ┌──────────────────────────────────┐
 │  • HTML5 Semántico                │        │  • app.py (Rutas y Controladores)│
 │  • CSS3 (Variables, WCAG AAA)     │ HTTP   │  • forms/ (Validación WTForms)   │
 │  • Bootstrap 5 (Grid, Modales)    │◄──────►│  • Base de datos en Memoria      │
 │  • JavaScript (DOM, LocalStorage) │        │  • Jinja2 (Motor de Renderizado) │
 └───────────────────────────────────┘        └──────────────────────────────────┘
```

### 1. El Modelo Cliente-Servidor y el Protocolo HTTP
Una aplicación web funciona mediante una conversación entre dos partes:
- **Cliente (Frontend / Navegador):** Solicita recursos (páginas, estilos, imágenes) y renderiza la interfaz gráfica.
- **Servidor (Backend / Flask):** Escucha las solicitudes entrantes, procesa la lógica de negocio, manipula datos y devuelve una respuesta en formato HTML o JSON.

#### Métodos HTTP Utilizados:
- **`GET`:** Se utiliza para solicitar y consultar información sin alterar el estado del servidor. Ejemplo: al entrar a `/servicios`, el servidor responde con la lista de servicios.
- **`POST`:** Se utiliza para enviar información sensible o crear/modificar registros en el servidor. Ejemplo: al enviar el formulario `/servicios/nuevo`, los datos viajan en el cuerpo de la petición (`Request Body`).

#### Códigos de Estado HTTP:
- `200 OK`: La petición fue exitosa y se entrega la página solicitada.
- `302 Found (Redirección)`: Ocurre cuando guardamos un formulario exitosamente y el servidor nos redirige (usando `redirect(url_for(...))`) a la lista principal.

---

### 2. Patrón de Arquitectura MVC (Modelo - Vista - Controlador)
Flask permite implementar de manera limpia el patrón MVC:
1. **Modelo (M):** Representa los datos y su estructura. En este proyecto se utilizan listas de diccionarios en memoria (`lista_servicios`, `lista_clientes`, `lista_proveedores`, `lista_facturas`) y clases de formularios en `forms/`.
2. **Vista (V):** Es la representación visual con la que interactúa el usuario. En Flask está compuesta por las plantillas Jinja2 dentro de la carpeta `templates/` y los estilos en `static/css/estilo.css`.
3. **Controlador (C):** Son las funciones decoradas con `@app.route` en `app.py`. Reciben la petición del cliente, ejecutan la lógica correspondiente (validar datos, agregar a la lista) y deciden qué plantilla renderizar o a dónde redirigir.

---

### 3. Motor de Plantillas Jinja2
Jinja2 es el motor que permite incrustar código dinámico de Python dentro de archivos HTML estándar:
- **Herencia de Plantillas (`{% extends "base.html" %}`):** Permite tener un esqueleto común (`base.html` con cabecera, navbar, footer y scripts) y que cada página solo defina su contenido propio (`{% block content %}`). Esto evita duplicar código HTML.
- **Inclusión Modular (`{% include "components/navbar.html" %}`):** Separa partes reutilizables como la barra de navegación o el pie de página en archivos independientes para un mantenimiento sencillo.
- **Interpolación de Variables (`{{ variable }}`):** Imprime valores pasados desde Python al HTML.
- **Filtros de Formato:** 
  - `{{ "%.2f"|format(servicio.precio) }}` convierte números flotantes a formato monetario con dos decimales (ej. `250.0` -> `250.00`).
  - `{{ detalle | tojson }}` convierte estructuras de datos Python a formato JSON para ser leídas por JavaScript.
- **Estructuras de Control:**
  - `{% for item in lista %}`: Itera sobre colecciones de datos generando filas o tarjetas HTML.
  - `{% if condicion %}`: Muestra u oculta bloques según el estado (por ejemplo, badges de "Disponible" o "Próximamente").

---

### 4. Formularios Seguros y Protección CSRF con Flask-WTF
El manejo de formularios web requiere altos estándares de seguridad:
- **¿Qué es CSRF (Cross-Site Request Forgery)?:** Es un ataque donde un sitio malicioso engaña al navegador para que envíe peticiones no deseadas a una web donde el usuario tiene una sesión activa.
- **Protección Automática:** Flask-WTF incluye en cada formulario un token criptográfico único (`{{ form.hidden_tag() }}`). Si una petición POST llega sin este token válido, Flask la rechaza inmediatamente.
- **Validación en Dos Capas (Frontend y Backend):**
  - *Frontend:* Mejora la experiencia del usuario avisando si falta un campo antes de enviar.
  - *Backend (WTForms):* Es la verdadera barrera de seguridad. Nunca se debe confiar exclusivamente en el navegador, ya que un usuario avanzado puede manipular el HTML. WTForms verifica en el servidor tipos de datos (`FloatField`), longitudes (`Length`) y obligatoriedad (`DataRequired`).

---

### 5. JavaScript DOM y Web Storage API (LocalStorage)
En el frontend se utiliza JavaScript Vanilla moderno (sin dependencias pesadas):
- **Manipulación del DOM:** Se capturan elementos con `document.getElementById` y se crean dinámicamente nodos en el árbol HTML con `document.createElement`.
- **LocalStorage:** Permite almacenar datos en el navegador del usuario en pares clave-valor que persisten incluso si se recarga la página o se cierra el navegador.
- **Expresiones Regulares (Regex):** Permiten validar patrones de texto (ej. `/^[A-Za-zÁÉÍÓÚáéíóúÑñ\\s]{3,}$/` para nombres y `/^[^\\s@]+@[^\\s@]+\\.[^\\s@]+$/` para correos).

---

### 6. Diseño Responsivo y Accesibilidad WCAG AAA
- **Variables CSS (`:root`):** Centralizan la paleta de colores de la marca para mantener consistencia.
- **Contraste de Texto:** Se definieron colores con un ratio de contraste superior a **7:1** (`#0f172a`, `#334155`, `#047857`, `#92400e`, `#991b1b`), asegurando que **ningún texto quede invisible, cortado o de difícil lectura**.
- **Estilos de Impresión (`@media print`):** Al presionar "Imprimir / Guardar PDF" en un comprobante, el CSS oculta automáticamente la barra de navegación, botones y pie de página, dejando un documento comercial pulcro y profesional.

---

## 📁 Estructura Completa del Proyecto y Descripción de Archivos

```text
NEXODIGITAL/
├── app.py                      # Servidor principal, configuración y rutas (Backend Flask)
├── requirements.txt            # Lista de dependencias del proyecto codificada en UTF-8
├── README.md                   # Manual técnico, pedagógico y guía de instalación
├── index.html                  # Maqueta estática e independiente (para vista previa offline)
│
├── forms/                      # Clases de formularios con validación y CSRF (Flask-WTF)
│   ├── __init__.py             # Inicializador del paquete forms y exportación de clases
│   ├── cliente_form.py         # Formulario de alta y edición de clientes
│   ├── servicio_form.py        # Formulario de alta y edición de servicios
│   ├── proveedor_form.py       # Formulario de proveedores con listas desplegables
│   └── facturacion_form.py     # Formulario unificado de Facturas y Cotizaciones
│
├── static/                     # Archivos estáticos servidos directamente al cliente
│   ├── css/
│   │   └── estilo.css          # Hoja de estilos personalizada (WCAG AAA, Print y Variables)
│   └── js/
│       ├── contacto.js         # Validación interactiva con Regex y modales de contacto
│       └── script.js           # Módulo de solicitudes rápidas con persistencia en localStorage
│
├── templates/                  # Vistas dinámicas renderizadas por Jinja2
│   ├── base.html               # Plantilla maestra con CDN, alerts flash y estructura base
│   ├── index.html              # Vista de inicio (Hero, Nosotros, Servicios, Solicitudes)
│   ├── servicios.html          # Vista de catálogo completo de servicios en tarjetas
│   ├── clientes.html           # Vista de directorio de clientes comerciales en tabla
│   ├── proveedores.html        # Vista de proveedores tecnológicos con enlaces seguros
│   ├── facturacion.html        # Panel de documentos comerciales (Facturas y Cotizaciones)
│   ├── comprobante_factura.html# Comprobante oficial imprimible y exportable a PDF
│   ├── formulario_cliente.html # Vista del formulario de cliente (Crear / Editar)
│   ├── formulario_servicio.html# Vista del formulario de servicio (Crear / Editar)
│   ├── formulario_proveedor.html# Vista del formulario de proveedor (Crear / Editar)
│   ├── formulario_facturacion.html # Constructor interactivo de cotizaciones y facturas
│   └── components/
│       ├── navbar.html         # Barra de navegación modular con detección de ruta activa
│       └── footer.html         # Pie de página modular con créditos institucionales
│
└── scratch/                    # Directorio de scripts y pruebas automatizadas
    └── test_advanced.py        # Suite de pruebas unitarias y de integración (100% pasando)
```

---

## ⚙️ Funcionamiento Lógico de Cada Módulo

### 1. Módulo de Inicio (`/`) y Contacto
1. El usuario ingresa a la raíz del sitio web.
2. `app.py` inyecta información institucional y los primeros 6 servicios del catálogo.
3. El formulario de contacto escucha los eventos `input` y `blur` mediante `contacto.js`.
4. Si los datos son válidos, al pulsar "Enviar", se despliega el modal de confirmación `#statusSuccessModal`.

### 2. Módulo Dinámico de Solicitudes (LocalStorage)
1. Permite al visitante registrar una solicitud rápida indicando nombre, servicio requerido y descripción.
2. Al enviar, `script.js` valida los campos, activa un spinner de carga temporal y serializa el arreglo de solicitudes en el `localStorage` del navegador bajo la clave `nexodigital_solicitudes`.
3. Las solicitudes se muestran inmediatamente como tarjetas en el DOM con botón para eliminarlas.

### 3. Módulo de Servicios (`/servicios`)
1. Lista todos los servicios con precio, tiempo estimado, badge de disponibilidad y portada.
2. Permite:
   - **Crear (`/servicios/nuevo`):** Asigna valores por defecto de imagen y tiempo si el usuario no los ingresa.
   - **Editar (`/servicios/editar/<id>`):** Carga los datos existentes en el formulario y actualiza la lista.
   - **Eliminar (`/servicios/eliminar/<id>`):** Remueve el elemento de la lista previa confirmación del usuario.
   - **Cotizar Directamente:** Cada servicio tiene un botón "Cotizar" que redirige a `/facturacion/nueva?tipo=Cotizacion&servicio_id=X`, cargando el servicio automáticamente.

### 4. Módulo de Clientes (`/clientes`) y Proveedores (`/proveedores`)
1. Administran en tablas estructuradas la información de los negocios atendidos y las herramientas de infraestructura externa (Hostinger, Cloudflare, Figma, GoDaddy).
2. Implementan el ciclo CRUD completo con validaciones y alertas flash informativas (`flash('...', 'success')`).

### 5. Módulo Comercial de Facturación y Cotizaciones Inteligentes (`/facturacion`)
Este es el módulo financiero más avanzado del sistema:
1. **Doble Propósito:** Emite tanto **Facturas Fiscales de Venta** como **Cotizaciones / Proformas Comerciales**.
2. **Constructor Dinámico de Ítems:** Permite seleccionar servicios del catálogo o añadir servicios a la medida, modificando en vivo:
   - *Precio Base ($)*
   - *Cantidad*
   - *Ajuste / Recargo por Complejidad o Urgencia ($)*
3. **Cálculo Financiero en Tiempo Real (JavaScript + Python):**
   $$\\text{Subtotal} = \\sum ((\\text{Precio Base} + \\text{Ajuste}) \\times \\text{Cantidad})$$
   $$\\text{IVA (15\\%)} = \\text{Subtotal} \\times 0.15$$
   $$\\text{Total General} = \\text{Subtotal} + \\text{IVA}$$
   $$\\text{Saldo Pendiente (Diferencia)} = \\max(0, \\text{Total General} - \\text{Anticipo Recibido})$$
4. **Comprobante Imprimible (`/facturacion/comprobante/<id>`):** Presenta el comprobante formal con los datos del cliente, tabla de servicios, notas y el cuadro de liquidación financiera (Anticipo abonado y Saldo pendiente). Permite exportar a PDF con el botón `Imprimir`.

---

## 🚀 Guía de Instalación y Ejecución Paso a Paso

Sigue estos pasos en tu computadora para poner en marcha el proyecto:

### Paso 1: Clonar o Descargar el Proyecto
Abre tu terminal (PowerShell, Command Prompt o Bash) y clona el repositorio:
```bash
git clone https://github.com/AracelyQuinta/NEXODIGITAL.git
cd NEXODIGITAL
```

### Paso 2: Crear el Entorno Virtual de Python
Un entorno virtual aísla las librerías del proyecto para no alterar la instalación global de Python.

- **En Windows (PowerShell):**
  ```powershell
  python -m venv venv
  .\venv\Scripts\Activate.ps1
  ```
  *(Si PowerShell muestra un error de políticas de ejecución, ejecuta antes: `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`)*

- **En macOS o Linux:**
  ```bash
  python3 -m venv venv
  source venv/bin/activate
  ```

### Paso 3: Instalar las Dependencias
Con el entorno virtual activado (verás `(venv)` al inicio de la línea de comandos):
```bash
pip install -r requirements.txt
```

### Paso 4: Ejecutar el Servidor Web Flask
Inicia la aplicación:
```bash
python app.py
```

### Paso 5: Abrir en el Navegador
Abre tu navegador preferido (Chrome, Edge, Firefox) e ingresa a:
👉 **`http://127.0.0.1:5000/`**

---

## 🧪 Verificación y Suite de Pruebas Automatizadas

El proyecto incluye una suite de pruebas automatizadas en `scratch/test_advanced.py` que comprueba:
1. Las 17 rutas GET principales responden con código HTTP `200 OK`.
2. Creación y validación de nuevos servicios con imagen y precios.
3. Creación de cotizaciones con ítems detallados, IVA, anticipo y saldo pendiente.
4. Creación de facturas con liquidación total.
5. Renderizado correcto de comprobantes imprimibles.

Para ejecutar las pruebas:
```powershell
.\venv\Scripts\python.exe scratch\test_advanced.py
```
**Resultado esperado:**
```text
=== 1. VERIFICAR TODAS LAS RUTAS GET ===
GET /                                             -> 200
GET /servicios                                    -> 200
GET /proveedores                                  -> 200
GET /clientes                                     -> 200
GET /facturacion                                  -> 200
...
>>> ¡TODAS LAS PRUEBAS PASARON EXITOSAMENTE (100%)! <<<
```

---

## 🛠️ Preguntas Frecuentes y Solución de Problemas (FAQ)

### 1. ¿Por qué me aparece `Address already in use` (Puerto 5000 ocupado)?
- **Causa:** Hay otra instancia de Python o un servicio del sistema usando el puerto 5000.
- **Solución:** Cierra las terminales previas o cambia el puerto en la última línea de `app.py`:
  ```python
  app.run(debug=True, port=5001)
  ```

### 2. ¿Qué pasa con los datos cuando detengo el servidor?
- **Explicación:** Al estar guardados en listas en memoria en `app.py`, los datos vuelven a su estado inicial al reiniciar el servidor. Esto es ideal para fines pedagógicos y pruebas.

### 3. ¿Cómo migrar los datos a una Base de Datos SQLite permanente?
Para pasar de listas en memoria a una base de datos real con **SQLAlchemy**:
1. Instalar `Flask-SQLAlchemy`:
   ```bash
   pip install Flask-SQLAlchemy
   ```
2. Configurar la base de datos en `app.py`:
   ```python
   from flask_sqlalchemy import SQLAlchemy
   app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///nexodigital.db'
   db = SQLAlchemy(app)
   ```
3. Crear un modelo:
   ```python
   class Cliente(db.Model):
       id = db.Column(db.Integer, primary_key=True)
       nombre = db.Column(db.String(100), nullable=False)
       negocio = db.Column(db.String(100), nullable=False)
       servicio = db.Column(db.String(100), nullable=False)
       ciudad = db.Column(db.String(50), nullable=False)
   ```
4. Reemplazar `lista_clientes.append(...)` por `db.session.add(nuevo_cliente)` y `db.session.commit()`.

---

## 🛡️ Licencia y Declaración de Uso Académico

Este software ha sido diseñado y desarrollado con fines estrictamente formativos y académicos para la asignatura de **Desarrollo de Aplicaciones Web** en la **Universidad Estatal Amazónica**. Todos los derechos patrimoniales y morales pertenecen a sus autores estudiantiles.
"""

pathlib.Path("README.md").write_text(readme_content, encoding="utf-8")
print("README.md generado con éxito en UTF-8.")
