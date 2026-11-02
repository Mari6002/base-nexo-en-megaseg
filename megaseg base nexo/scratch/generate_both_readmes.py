import pathlib

# ==============================================================================
# 1. README.md: ARCHIVO DE PRESENTACIÓN OFICIAL Y PÚBLICA DEL PROYECTO
# ==============================================================================
readme_publico = """# ⚡ NEXODIGITAL - Soluciones Web y Plataforma Comercial

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg?logo=python&logoColor=white)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Framework-Flask%203.1-black.svg?logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![Bootstrap](https://img.shields.io/badge/UI-Bootstrap%205.3-purple.svg?logo=bootstrap&logoColor=white)](https://getbootstrap.com/)
[![License](https://img.shields.io/badge/License-Educativa%20%2F%20UEA-emerald.svg)]()

Plataforma web institucional y sistema de gestión comercial para el emprendimiento tecnológico **NexoDigital**, orientada a impulsar la presencia en internet de pequeños negocios y emprendedores en Ecuador mediante desarrollo web, catálogos digitales y menús QR.

---

## 👥 Equipo de Desarrollo y Créditos Académicos

- **Institución:** Universidad Estatal Amazónica (UEA) — Sede Puyo / Quito
- **Nivel Académico:** Cuarto Semestre
- **Asignatura:** Desarrollo de Aplicaciones Web
- **Autores:**
  - **Cinthia Mishel Carrión Serrano**
  - **Aracely Maribel Quintanilla Rumipamba**
  - **Santiago Andrés Lara Caicedo**

---

## 📖 Documentación Disponible

Este repositorio cuenta con dos documentos clave:
1. **[README.md](README.md)** *(Este documento)*: Presentación oficial, características generales y guía rápida de ejecución.
2. **[MANUAL_DESARROLLO.md](MANUAL_DESARROLLO.md)**: **Guía Maestra de Aprendizaje y Duplicación Paso a Paso**, que explica a profundidad la teoría, arquitectura, cómo programar cada módulo desde cero y replicar el proyecto.

---

## 🚀 Características y Módulos del Sistema

### 1. Sitio Web Institucional (`/`)
- Presentación de la empresa, misión, visión y propuesta de valor.
- Catálogo de servicios destacados con precios en dólares americanos ($ USD).
- Video explicativo sobre la importancia del desarrollo web para los comercios.
- Formulario de contacto interactivo con validaciones en tiempo real y modales Bootstrap.
- Módulo de **Registro Rápido de Solicitudes** con almacenamiento local en el navegador (`localStorage`).

### 2. Catálogo de Servicios (`/servicios`)
- Directorio de soluciones digitales (Páginas web, Catálogos, Menús QR, Formularios).
- Badges de estado (`Disponible` / `Próximamente`) y tiempos estimados de entrega.
- Operaciones CRUD completas (Crear, Editar, Eliminar y Cotizar directamente).

### 3. Directorio de Clientes (`/clientes`)
- Cartera comercial de clientes atendidos, actividad económica y ubicación geográfica.
- Registro y actualización de clientes con validaciones de seguridad.

### 4. Gestión de Proveedores (`/proveedores`)
- Directorio de infraestructura tecnológica (Hosting, Dominios, Certificados SSL, Figma).
- Enlaces oficiales con directivas de seguridad (`rel="noopener noreferrer"`).

### 5. Facturación y Cotizaciones Inteligentes (`/facturacion`)
- Emisión de **Facturas de Venta** y **Cotizaciones / Proformas Comerciales**.
- Constructor dinámico de ítems: permite agregar servicios del catálogo, modificar cantidades y añadir recargos por urgencia o complejidad.
- **Liquidación Financiera en Tiempo Real:**
  - Subtotal automático.
  - Cálculo de IVA (15% vigente en Ecuador).
  - Total General del proyecto.
  - Registro de Anticipos / Abonos recibidos.
  - **Cálculo de Saldo Pendiente (Diferencia Real a cobrar contra entrega)** con alertas visuales de alto contraste.
- **Comprobante Imprimible / PDF (`/facturacion/comprobante/<id>`):** Vista formal optimizada con estilos `@media print` para exportar a PDF con un solo clic.

---

## 🛠️ Tecnologías Empleadas

| Área | Tecnologías |
|---|---|
| **Backend** | Python 3, Flask 3.1, Werkzeug, itsdangerous |
| **Seguridad y Formularios** | Flask-WTF, WTForms (Protección CSRF y validación de tipos) |
| **Motor de Plantillas** | Jinja2 (Herencia modular, filtros monetarios y de serialización) |
| **Frontend / UI** | HTML5 Semántico, CSS3 Personalizado (WCAG AAA), Bootstrap 5.3, Bootstrap Icons |
| **Interactividad** | JavaScript (ES6+), Web Storage API (`localStorage`), Expresiones Regulares |

---

## ⚡ Guía Rápida de Instalación y Ejecución

### 1. Clonar el Repositorio
```bash
git clone https://github.com/AracelyQuinta/NEXODIGITAL.git
cd NEXODIGITAL
```

### 2. Crear y Activar Entorno Virtual
- **Windows (PowerShell):**
  ```powershell
  python -m venv venv
  .\\venv\\Scripts\\Activate.ps1
  ```
- **macOS / Linux:**
  ```bash
  python3 -m venv venv
  source venv/bin/activate
  ```

### 3. Instalar Dependencias
```bash
pip install -r requirements.txt
```

### 4. Ejecutar el Servidor
```bash
python app.py
```

Abre tu navegador en: **`http://127.0.0.1:5000/`**

---

## 🧪 Pruebas Automatizadas
Para verificar que todas las rutas y operaciones funcionan correctamente:
```powershell
.\\venv\\Scripts\\python.exe scratch\\test_advanced.py
```

---

## 📚 ¿Deseas aprender a construir este proyecto paso a paso?
Consulta la **[Guía de Desarrollo y Duplicación Paso a Paso (MANUAL_DESARROLLO.md)](MANUAL_DESARROLLO.md)** para una explicación detallada de cada línea de código, arquitectura y ejercicios formativos.
"""

# ==============================================================================
# 2. MANUAL_DESARROLLO.md: GUÍA MAESTRA DE APRENDIZAJE Y DUPLICACIÓN PASO A PASO
# ==============================================================================
manual_desarrollo = """# 📘 MANUAL DE DESARROLLO, APRENDIZAJE Y DUPLICACIÓN PASO A PASO
## Proyecto: NEXODIGITAL - Soluciones Web y Facturación Comercial

> Este manual ha sido redactado como una **guía didáctica exhaustiva** para que cualquier estudiante, docente o desarrollador comprenda los fundamentos teóricos, la arquitectura y la secuencia exacta de pasos para **replicar y construir este proyecto desde cero**.

---

## 📑 Tabla de Contenidos

1. [Fundamentos Teóricos del Desarrollo Web](#1-fundamentos-teóricos-del-desarrollo-web)
2. [Arquitectura del Proyecto (Patrón MVC en Flask)](#2-arquitectura-del-proyecto-patrón-mvc-en-flask)
3. [Guía de Construcción Paso a Paso (Cómo Replicar el Proyecto)](#3-guía-de-construcción-paso-a-paso-cómo-replicar-el-proyecto)
   - [Paso 1: Configuración del Entorno y Dependencias](#paso-1-configuración-del-entorno-y-dependencias)
   - [Paso 2: Creación de los Formularios Seguros con WTForms](#paso-2-creación-de-los-formularios-seguros-con-wtforms)
   - [Paso 3: Programación del Backend y Rutas en app.py](#paso-3-programación-del-backend-y-rutas-en-apppy)
   - [Paso 4: Maquetación y Plantillas Dinámicas con Jinja2](#paso-4-maquetación-y-plantillas-dinámicas-con-jinja2)
   - [Paso 5: Estilos CSS de Alto Contraste y Reglas de Impresión](#paso-5-estilos-css-de-alto-contraste-y-reglas-de-impresión)
   - [Paso 6: JavaScript Interactivo (Regex y LocalStorage)](#paso-6-javascript-interactivo-regex-y-localstorage)
4. [Lógica Matemática y Algoritmos Financieros](#4-lógica-matemática-y-algoritmos-financieros)
5. [Aseguramiento de Calidad y Pruebas Unitarias](#5-aseguramiento-de-calidad-y-pruebas-unitarias)
6. [Guía de Extensión a Base de Datos Permanente (SQLite + SQLAlchemy)](#6-guía-de-extensión-a-base-de-datos-permanente-sqlite--sqlalchemy)

---

## 1. Fundamentos Teóricos del Desarrollo Web

Para comprender cómo funciona **NexoDigital**, es indispensable dominar estos cuatro pilares de la ingeniería web:

### A. El Ciclo de Vida HTTP (Petición y Respuesta)
Toda interacción en la web sigue el protocolo HTTP:
1. El usuario interactúa con la interfaz (por ejemplo, hace clic en "Guardar Cliente").
2. El navegador emite una **Petición HTTP** (`Request`) que viaja al servidor:
   - **Método `GET`:** Solicita la entrega de una página o recurso sin modificar datos en el servidor.
   - **Método `POST`:** Envía información desde un formulario para ser procesada o guardada.
3. El servidor recibe los datos, valida las reglas de negocio y devuelve una **Respuesta HTTP** (`Response`):
   - Código `200 OK`: Renderiza la vista HTML solicitada.
   - Código `302 Found`: Redirecciona al navegador hacia otra ruta (ej. tras guardar un cliente exitosamente, lo redirige a la lista `/clientes`).

### B. Patrón MVC (Modelo - Vista - Controlador) en Flask
- **Modelo (M):** Define cómo se estructuran los datos. En este proyecto se utilizan listas de diccionarios en Python y clases formales de validación en `forms/`.
- **Vista (V):** Es la capa visual (HTML + Jinja2 + CSS). Recibe datos desde Python y los transforma en páginas web legibles.
- **Controlador (C):** Son las funciones en `app.py` decoradas con `@app.route()`. Actúan como el "cerebro" intermediario: reciben la petición, consultan o modifican los datos y ordenan qué plantilla mostrar.

### C. Seguridad contra Ataques CSRF (Cross-Site Request Forgery)
- **El Peligro:** Un sitio web malicioso podría intentar enviar una petición oculta a nuestro servidor aprovechando que el usuario tiene la sesión abierta.
- **La Solución:** `Flask-WTF` genera automáticamente un **Token CSRF** secreto e irrepetible en cada formulario (`{{ form.hidden_tag() }}`). Cuando el servidor recibe la petición POST, comprueba que el token coincida con el de la sesión. Si no coincide, la petición es bloqueada.

### D. Accesibilidad y Contraste (WCAG AAA)
- Para que una aplicación sea accesible y visualmente profesional, el ratio de contraste entre el color del texto y su fondo debe ser superior a **7:1**.
- Se evitaron combinaciones de bajo contraste (como texto blanco sobre fondos amarillos claros) utilizando colores oscuros y específicos (`--amber-text: #92400e`, `--rose-text: #991b1b`, `--emerald-text: #065f46`).

---

## 2. Arquitectura del Proyecto (Patrón MVC en Flask)

```
                            ESTRUCTURA DE ARCHIVOS
NEXODIGITAL/
├── app.py                      <-- [Controlador Principal] Rutas, lógica y cálculos
├── requirements.txt            <-- [Dependencias] Librerías necesarias
├── forms/                      <-- [Modelos de Formulario] Validación y CSRF
│   ├── cliente_form.py
│   ├── servicio_form.py
│   ├── proveedor_form.py
│   └── facturacion_form.py
├── static/                     <-- [Recursos Estáticos]
│   ├── css/estilo.css          <-- Estilos, paleta accesible y reglas @media print
│   └── js/
│       ├── contacto.js         <-- Validación Regex de contacto
│       └── script.js           <-- Solicitudes rápidas en localStorage
└── templates/                  <-- [Vistas Jinja2]
    ├── base.html               <-- Plantilla maestra (Layout base)
    ├── components/             <-- Componentes modulares (navbar, footer)
    ├── index.html              <-- Inicio
    ├── servicios.html          <-- Catálogo
    ├── clientes.html           <-- Cartera de clientes
    ├── proveedores.html        <-- Infraestructura
    ├── facturacion.html        <-- Panel de facturas y cotizaciones
    └── comprobante_factura.html<-- Comprobante oficial imprimible
```

---

## 3. Guía de Construcción Paso a Paso (Cómo Replicar el Proyecto)

### Paso 1: Configuración del Entorno y Dependencias
1. Crea una carpeta para el proyecto:
   ```bash
   mkdir NEXODIGITAL
   cd NEXODIGITAL
   ```
2. Crea el entorno virtual de Python:
   ```bash
   python -m venv venv
   .\\venv\\Scripts\\Activate.ps1
   ```
3. Crea el archivo `requirements.txt` con las librerías necesarias:
   ```text
   Flask==3.1.3
   Flask-WTF==1.3.0
   WTForms==3.2.2
   Jinja2==3.1.6
   Werkzeug==3.1.8
   itsdangerous==2.2.0
   MarkupSafe==3.0.3
   blinker==1.9.0
   click==8.4.2
   colorama==0.4.6
   ```
4. Instala las dependencias:
   ```bash
   pip install -r requirements.txt
   ```

---

### Paso 2: Creación de los Formularios Seguros con WTForms
Crea el directorio `forms/` y dentro programa cada archivo:

#### `forms/cliente_form.py`:
```python
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired, Length

class ClienteForm(FlaskForm):
    nombre = StringField('Nombre del cliente', validators=[DataRequired(), Length(min=3, max=100)])
    negocio = StringField('Tipo de negocio', validators=[DataRequired(), Length(min=3, max=100)])
    servicio = StringField('Servicio contratado', validators=[DataRequired(), Length(min=3, max=100)])
    ciudad = StringField('Ciudad', validators=[DataRequired(), Length(min=3, max=50)])
    submit = SubmitField('Guardar cliente')
```

#### `forms/facturacion_form.py`:
Permite manejar Facturas y Cotizaciones, calcular anticipos y serializar los ítems en un campo oculto `servicios_json`:
```python
from flask_wtf import FlaskForm
from wtforms import StringField, FloatField, SelectField, TextAreaField, HiddenField, SubmitField
from wtforms.validators import DataRequired, Length, NumberRange, Optional

class FacturacionForm(FlaskForm):
    tipo = SelectField('Tipo', choices=[('Factura', 'Factura'), ('Cotizacion', 'Cotización')], validators=[DataRequired()])
    numero = StringField('Número', validators=[DataRequired(), Length(min=3, max=40)])
    cliente = StringField('Cliente', validators=[DataRequired(), Length(min=3, max=100)])
    fecha = StringField('Fecha', validators=[DataRequired()])
    validez = StringField('Vigencia', validators=[Optional(), Length(max=50)])
    servicios_json = HiddenField('JSON Ítems')
    subtotal = FloatField('Subtotal', validators=[Optional(), NumberRange(min=0)])
    iva = FloatField('IVA', validators=[Optional(), NumberRange(min=0)])
    monto = FloatField('Total General', validators=[DataRequired(), NumberRange(min=0.01)])
    anticipo = FloatField('Anticipo', default=0.00)
    saldo_pendiente = FloatField('Saldo Pendiente', default=0.00)
    estado = SelectField('Estado', choices=[('Pagada', 'Pagada'), ('Pendiente', 'Pendiente'), ('Aprobada', 'Aprobada'), ('En revision', 'En revisión')], validators=[DataRequired()])
    notas = TextAreaField('Notas', validators=[Optional(), Length(max=400)])
    submit = SubmitField('Guardar Documento')
```

---

### Paso 3: Programación del Backend y Rutas en `app.py`
En `app.py`:
1. Inicializa Flask y asigna una clave secreta (`SECRET_KEY`).
2. Declara las listas de datos iniciales en memoria (`lista_servicios`, `lista_clientes`, `lista_proveedores`, `lista_facturas`).
3. Define las rutas de visualización y las rutas CRUD:

```python
from flask import Flask, render_template, redirect, url_for, flash, request
from forms.cliente_form import ClienteForm
from forms.facturacion_form import FacturacionForm

app = Flask(__name__)
app.config['SECRET_KEY'] = 'clave_secreta_nexodigital_2026'

# Base de datos simulada en memoria
lista_clientes = [
    {"nombre": "Panadería El Trigal", "negocio": "Panadería", "servicio": "Página Web + Menú QR", "ciudad": "Santo Domingo"}
]

@app.route('/')
def inicio():
    return render_template('index.html')

@app.route('/clientes')
def clientes():
    return render_template('clientes.html', clientes=lista_clientes)

@app.route('/clientes/nuevo', methods=['GET', 'POST'])
def nuevo_cliente():
    form = ClienteForm()
    if form.validate_on_submit():
        lista_clientes.append({
            "nombre": form.nombre.data.strip(),
            "negocio": form.negocio.data.strip(),
            "servicio": form.servicio.data.strip(),
            "ciudad": form.ciudad.data.strip()
        })
        flash('Cliente registrado exitosamente.', 'success')
        return redirect(url_for('clientes'))
    return render_template('formulario_cliente.html', form=form, editando=False)

if __name__ == '__main__':
    app.run(debug=True)
```

---

### Paso 4: Maquetación y Plantillas Dinámicas con Jinja2
1. **`templates/base.html`:** Contiene la cabecera HTML, enlaces a Bootstrap 5 CDN, Bootstrap Icons, el bloque de alertas flash (`get_flashed_messages()`) y el bloque dinámico `{% block content %}`.
2. **`templates/components/navbar.html`:** Barra de navegación que detecta la página actual usando `{{ 'active' if request.endpoint == 'inicio' else '' }}`.
3. **`templates/facturacion.html`:** Muestra la tabla de documentos con badges semánticos de estado y saldo.
4. **`templates/comprobante_factura.html`:** Renderiza el comprobante formal imprimible.

---

### Paso 5: Estilos CSS de Alto Contraste y Reglas de Impresión
En `static/css/estilo.css`:
1. Define las variables de color con alto contraste:
   ```css
   :root {
       --navy: #0A2540;
       --emerald: #10b981;
       --emerald-text: #065f46;
       --amber-text: #92400e;
       --rose-text: #991b1b;
   }
   ```
2. Define los badges de saldo con colores visibles y bordes sólidos:
   ```css
   .badge-saldo-pendiente {
       background-color: #fee2e2 !important;
       color: #991b1b !important;
       font-weight: 700 !important;
       border: 1.5px solid #ef4444 !important;
   }
   .badge-saldo-liquidado {
       background-color: #d1fae5 !important;
       color: #065f46 !important;
       font-weight: 700 !important;
       border: 1.5px solid #10b981 !important;
   }
   ```
3. Agrega la regla de impresión `@media print`:
   ```css
   @media print {
       .navbar, .footer-custom, .btn-print-hide, .page-header {
           display: none !important;
       }
       body { background-color: #ffffff !important; font-size: 11pt; }
       .card { border: none !important; box-shadow: none !important; }
   }
   ```

---

### Paso 6: JavaScript Interactivo (Regex y LocalStorage)
1. **`static/js/contacto.js`:**
   - Escucha los eventos `input` y `blur` de los campos.
   - Aplica expresiones regulares:
     - Nombre: `/^[A-Za-zÁÉÍÓÚáéíóúÑñ\\s]{3,}$/`
     - Correo: `/^[^\\s@]+@[^\\s@]+\\.[^\\s@]+$/`
   - Si todo es correcto, despliega el modal de Bootstrap `statusSuccessModal`.
2. **`static/js/script.js`:**
   - Lee y escribe en `localStorage.getItem('nexodigital_solicitudes')`.
   - Crea tarjetas dinámicas en el DOM con `document.createElement('div')`.
   - Ofrece opción para eliminar solicitudes en tiempo real.

---

## 4. Lógica Matemática y Algoritmos Financieros

El módulo de facturación aplica las siguientes fórmulas en tiempo real tanto en el cliente (JavaScript) como en el servidor (Python):

1. **Subtotal por Línea:**
   $$\\text{Total Línea} = (\\text{Precio Base} + \\text{Ajuste por Complejidad}) \\times \\text{Cantidad}$$

2. **Subtotal General:**
   $$\\text{Subtotal} = \\sum \\text{Total Línea}_i$$

3. **Impuesto al Valor Agregado (IVA 15% Ecuador):**
   $$\\text{IVA} = \\text{Subtotal} \\times 0.15$$

4. **Total General:**
   $$\\text{Total General} = \\text{Subtotal} + \\text{IVA}$$

5. **Saldo Pendiente (Diferencia Real por Cobrar):**
   $$\\text{Saldo Pendiente} = \\max(0, \\text{Total General} - \\text{Anticipo Recibido})$$

Si el $\\text{Saldo Pendiente} == 0$, el estado se actualiza automáticamente a **Pagada** o **Liquidada**.

---

## 5. Aseguramiento de Calidad y Pruebas Unitarias

El archivo `scratch/test_advanced.py` utiliza el cliente de pruebas de Flask (`app.test_client()`) para validar que:
1. Las 17 rutas responden con código HTTP `200`.
2. Los formularios procesan peticiones POST y redirigen correctamente con código `302/200`.
3. Los cálculos de IVA, anticipos y saldos pendientes coinciden con los valores esperados.

Para ejecutar la suite de pruebas:
```powershell
.\\venv\\Scripts\\python.exe scratch\\test_advanced.py
```

---

## 6. Guía de Extensión a Base de Datos Permanente (SQLite + SQLAlchemy)

Si deseas migrar los datos desde la memoria a una base de datos relacional permanente en disco:

1. Instala `Flask-SQLAlchemy`:
   ```bash
   pip install Flask-SQLAlchemy
   ```
2. Configura la base de datos en `app.py`:
   ```python
   from flask_sqlalchemy import SQLAlchemy
   
   app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///nexodigital.db'
   app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
   db = SQLAlchemy(app)
   ```
3. Modela la tabla de Clientes:
   ```python
   class Cliente(db.Model):
       __tablename__ = 'clientes'
       id = db.Column(db.Integer, primary_key=True)
       nombre = db.Column(db.String(100), nullable=False)
       negocio = db.Column(db.String(100), nullable=False)
       servicio = db.Column(db.String(100), nullable=False)
       ciudad = db.Column(db.String(50), nullable=False)
   ```
4. Reemplaza las operaciones en las rutas:
   - **Consultar todos:** `clientes = Cliente.query.all()`
   - **Insertar:** 
     ```python
     nuevo = Cliente(nombre=form.nombre.data, negocio=form.negocio.data, servicio=form.servicio.data, ciudad=form.ciudad.data)
     db.session.add(nuevo)
     db.session.commit()
     ```
   - **Actualizar:**
     ```python
     cliente = Cliente.query.get_or_404(id)
     cliente.nombre = form.nombre.data
     db.session.commit()
     ```
   - **Eliminar:**
     ```python
     cliente = Cliente.query.get_or_404(id)
     db.session.delete(cliente)
     db.session.commit()
     ```

---

## 🎓 Conclusión y Recomendaciones Pedagógicas

Con esta arquitectura:
- El código se mantiene modular, seguro y fácil de auditar.
- La interfaz visual cumple con estándares internacionales de accesibilidad (WCAG AAA).
- El proyecto sirve tanto como portafolio académico como una base sólida para un sistema SaaS comercial real.
"""

pathlib.Path("README.md").write_text(readme_publico, encoding="utf-8")
pathlib.Path("MANUAL_DESARROLLO.md").write_text(manual_desarrollo, encoding="utf-8")
print("Ambos archivos generados con éxito: README.md y MANUAL_DESARROLLO.md")
