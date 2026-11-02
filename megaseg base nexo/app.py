# ==============================================================================
# PROYECTO: NEXODIGITAL - SOLUCIONES WEB Y COMERCIALES
# Control Principal de la AplicaciÃ³n Flask (Backend)
# ==============================================================================
# Este archivo contiene la configuraciÃ³n central del servidor y los controladores
# (rutas y vistas) que gestionan la lÃ³gica de negocio para:
# 1. PÃ¡gina de inicio y presentaciÃ³n de la empresa
# 2. CatÃ¡logo y gestiÃ³n de Servicios (CRUD) y sus CategorÃ­as (CRUD)
# 3. Directorio de Proveedores e infraestructura (CRUD)
# 4. Directorio de Clientes y cartera comercial (CRUD)
# 5. EmisiÃ³n de Facturas y Cotizaciones (CRUD) con detalle relacional real
#
# Persistencia de datos: PostgreSQL, mediante conexion/conexion.py (conexiÃ³n centralizada).
# Todas las tablas estÃ¡n relacionadas mediante claves primarias y forÃ¡neas:
#   clientes  <--(cliente_cedula)--  facturacion  --(factura_numero)-->  detalle_factura
#   tipos_servicio <--(tipo_servicio_id)--  servicios  <--(servicio_id)--  detalle_factura
# ==============================================================================

import os
import json
import random
import re
import secrets
import psycopg2
from html.parser import HTMLParser
from functools import wraps
from datetime import date, datetime, timedelta
from urllib.parse import urljoin, urlencode, urlparse
from urllib.request import Request, urlopen
from flask import Flask, render_template, redirect, url_for, flash, request, session, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
import bcrypt
from werkzeug.security import generate_password_hash, check_password_hash

# Modelos de Usuario, Roles, Permisos y Logs de AuditorÃ­a (RBAC)
from models import Usuario, User, Role, ActivityLog

# ImportaciÃ³n de clases de formularios creadas con Flask-WTF
from forms.cliente_form import ClienteForm
from forms.tipo_negocio_form import TipoNegocioForm
from forms.servicio_form import ServicioForm
from forms.tipo_servicio_form import TipoServicioForm
from forms.proveedor_form import ProveedorForm
from forms.categoria_proveedor_form import CategoriaProveedorForm
from forms.facturacion_form import FacturacionForm
from forms.login_form import LoginForm
from forms.usuario_form import UsuarioForm
from forms.producto_form import ProductoForm
from forms.dos_factores_form import DosFactoresForm

# MÃ³dulo propio de conexiÃ³n centralizada a PostgreSQL (carpeta conexion/)
from conexion.conexion import close_db_connection, get_db_connection


class _ImagenMetaParser(HTMLParser):
    """Obtiene la imagen principal declarada por una pÃ¡gina web."""

    def __init__(self):
        super().__init__()
        self.imagen_url = None

    def handle_starttag(self, tag, attrs):
        if tag.lower() != 'meta' or self.imagen_url:
            return

        atributos = {clave.lower(): valor for clave, valor in attrs}
        referencia = (atributos.get('property') or atributos.get('name') or '').lower()
        if referencia in ('og:image', 'og:image:url', 'twitter:image', 'twitter:image:src'):
            self.imagen_url = atributos.get('content')


def resolver_url_imagen(valor):
    """Resuelve una imagen, conservando enlaces HTTPS vÃ¡lidos como respaldo."""
    url = (valor or '').strip()
    partes = urlparse(url)
    if partes.scheme not in ('http', 'https') or not partes.netloc:
        return None

    try:
        solicitud = Request(url, headers={'User-Agent': 'NexoDigital/1.0'})
        with urlopen(solicitud, timeout=8) as respuesta:
            tipo_contenido = respuesta.headers.get_content_type().lower()
            if tipo_contenido.startswith('image/'):
                return url

            if tipo_contenido in ('application/octet-stream', 'binary/octet-stream') and \
                    partes.path.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp', '.avif')):
                return url

            if not (tipo_contenido.startswith('text/html') or tipo_contenido == 'application/xhtml+xml'):
                return None

            contenido = respuesta.read(2_000_000).decode(
                respuesta.headers.get_content_charset() or 'utf-8',
                errors='replace'
            )
            parser = _ImagenMetaParser()
            parser.feed(contenido)
            if parser.imagen_url:
                imagen = urljoin(url, parser.imagen_url.strip())
                imagen_partes = urlparse(imagen)
                if imagen_partes.scheme in ('http', 'https') and imagen_partes.netloc:
                    return imagen
    except Exception:
        # El enlace puede ser vÃ¡lido aunque el servidor remoto bloquee la
        # verificaciÃ³n desde backend. El navegador aÃºn puede cargarlo.
        return url

    return url

# ------------------------------------------------------------------------------
# INICIALIZACIÃN DE LA APLICACIÃN FLASK
# ------------------------------------------------------------------------------
app = Flask(__name__)

# Clave secreta para la protecciÃ³n de sesiones y seguridad contra ataques CSRF en formularios
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
if not app.config['SECRET_KEY']:
    if os.getenv('FLASK_ENV', 'development').lower() != 'production':
        app.config['SECRET_KEY'] = 'clave-local-nexodigital-2026'
    else:
        raise RuntimeError('SECRET_KEY es obligatoria fuera del modo de desarrollo.')

# ExpiraciÃ³n automÃ¡tica de sesiÃ³n tras 30 minutos de inactividad
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_SECURE'] = os.getenv('FLASK_ENV', 'development').lower() == 'production'
app.teardown_appcontext(close_db_connection)


@app.after_request
def asegurar_codificacion_utf8(response):
    """Declara UTF-8 explÃ­citamente para que los textos en espaÃ±ol no se deformen."""
    if response.mimetype == 'text/html':
        response.headers['Content-Type'] = 'text/html; charset=utf-8'
    return response


# ------------------------------------------------------------------------------
# CONFIGURACIÃN DE AUTENTICACIÃN (Flask-Login)
# ------------------------------------------------------------------------------
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Por favor inicia sesiÃ³n para acceder a esta pÃ¡gina.'
login_manager.login_message_category = 'warning'


@login_manager.user_loader
def load_user(user_id):
    """
    FunciÃ³n de callback requerida por Flask-Login para recuperar la instancia del
    usuario autenticado desde la base de datos a partir de su ID de sesiÃ³n.
    """
    return Usuario.get_by_id(user_id)


# ------------------------------------------------------------------------------
# FUNCIONES AUXILIARES: CAPTCHA, AUDITORÃA Y CONTROL DE ACCESO (RBAC)
# ------------------------------------------------------------------------------

def generar_captcha():
    """Genera una operaciÃ³n aritmÃ©tica aleatoria sencilla para verificaciÃ³n humana."""
    num1 = random.randint(1, 9)
    num2 = random.randint(1, 9)
    session['captcha_respuesta'] = str(num1 + num2)
    session['captcha_pregunta'] = f"{num1} + {num2} = ?"
    return session['captcha_pregunta']


def validar_password_segura(password):
    """Valida que la contraseÃ±a tenga longitud y complejidad suficientes."""
    if len(password) < 8:
        return False
    if not re.search(r'[A-Z]', password):
        return False
    if not re.search(r'[a-z]', password):
        return False
    if not re.search(r'\d', password):
        return False
    if not re.search(r'[^A-Za-z0-9]', password):
        return False
    return True


def validar_nombre_persona(valor):
    """Valida que un nombre o apellido contenga solo letras y espacios."""
    if not valor:
        return False
    return bool(re.fullmatch(r'[A-Za-zÃÃÃÃÃÃ¡Ã©Ã­Ã³ÃºÃÃ±\s]+', valor.strip()))


def validar_telefono_10_digitos(valor):
    """Valida que el telÃ©fono tenga exactamente 10 dÃ­gitos numÃ©ricos."""
    if not valor:
        return False
    return bool(re.fullmatch(r'\d{10}', valor.strip()))


def verificar_recaptcha(token):
    """Valida reCAPTCHA si estÃ¡ configurado; si no, acepta la verificaciÃ³n local."""
    if not token:
        return True
    secret_key = os.getenv('RECAPTCHA_SECRET_KEY')
    if not secret_key:
        return True
    try:
        payload = urlencode({'secret': secret_key, 'response': token}).encode('utf-8')
        req = Request(
            'https://www.google.com/recaptcha/api/siteverify',
            data=payload,
            headers={'Content-Type': 'application/x-www-form-urlencoded'}
        )
        with urlopen(req, timeout=8) as response:
            data = json.loads(response.read().decode('utf-8'))
        return bool(data.get('success'))
    except Exception:
        return False


def registrar_log(accion, detalles=None):
    """Registra un evento en la tabla logs_actividad para auditorÃ­a de seguridad."""
    try:
        user_id = current_user.id if current_user.is_authenticated else None
        user_name = current_user.usuario if current_user.is_authenticated else session.get('temp_user_nombre', 'AnÃ³nimo')
        ip = request.remote_addr or '127.0.0.1'
        ActivityLog.registrar(user_id, user_name, accion, ip, detalles)
    except Exception as e:
        app.logger.warning(f"Error registrando log de auditorÃ­a: {e}")


def role_required(*roles_permitidos):
    """
    Decorador para proteger rutas segÃºn los roles asignados al usuario actual.
    Si el usuario no estÃ¡ autenticado, redirige al login.
    Si no posee los roles permitidos, registra la denegaciÃ³n en la auditorÃ­a y redirige.
    """
    def decorador(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('Por favor inicia sesiÃ³n para acceder a esta pÃ¡gina.', 'warning')
                return redirect(url_for('login', next=request.path))

            if current_user.rol_nombre not in roles_permitidos:
                registrar_log(
                    'ACCESO_DENEGADO_ROL',
                    f"Ruta: {request.path} | Rol actual: {current_user.rol_nombre} | Roles permitidos: {list(roles_permitidos)}"
                )
                flash(f'Acceso denegado: tu rol actual ({current_user.rol_nombre}) no tiene permisos para esta acciÃ³n.', 'danger')
                return redirect(url_for('dashboard'))

            return f(*args, **kwargs)
        return wrapper
    return decorador


def permission_required(codigo_permiso):
    """
    Decorador para proteger rutas segÃºn la tabla relacional rol_permisos.
    Verifica que el rol asignado al usuario cuente con el permiso granular requerido.
    """
    def decorador(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('Por favor inicia sesiÃ³n para acceder a esta pÃ¡gina.', 'warning')
                return redirect(url_for('login', next=request.path))

            if not current_user.has_permission(codigo_permiso):
                registrar_log(
                    'ACCESO_DENEGADO_PERMISO',
                    f"Ruta: {request.path} | Permiso requerido: {codigo_permiso} | Rol: {current_user.rol_nombre}"
                )
                flash('Acceso denegado: no dispones de los permisos granulares necesarios para esta operaciÃ³n.', 'danger')
                return redirect(url_for('dashboard'))

            return f(*args, **kwargs)
        return wrapper
    return decorador


# ==============================================================================
# RUTAS PÃBLICAS Y VISTAS GENERALES
# ==============================================================================

def asegurar_servicios_minimos(cursor):
    """Garantiza que el catÃ¡logo persistido tenga al menos dos servicios."""
    cursor.execute('SELECT COUNT(*) AS total FROM servicios')
    faltantes = max(0, 2 - cursor.fetchone()['total'])
    if not faltantes:
        return

    catalogo_base = (
        ('Sistemas de Alarma', 'Alarma Inteligente con Monitoreo Móvil', 180.00,
         'Sistema de alarma inteligente con detección inmediata de intrusos, alertas en tiempo real al celular y monitoreo remoto.',
         'https://images.unsplash.com/photo-1558002038-1055907df827'),
        ('Videovigilancia y CCTV', 'Kit de Cámaras de Seguridad HD/4K', 220.00,
         'Cámaras de vigilancia IP de alta definición con visión nocturna, detección de movimiento y acceso remoto 24/7.',
         'https://images.unsplash.com/photo-1557597774-9d273605dfa9'),
    )
    for tipo_nombre, nombre, precio, descripcion, imagen in catalogo_base[:faltantes]:
        cursor.execute(
            '''INSERT INTO tipos_servicio (nombre) VALUES (%s)
               ON CONFLICT (nombre) DO NOTHING''',
            (tipo_nombre,)
        )
        cursor.execute('SELECT id FROM tipos_servicio WHERE nombre = %s', (tipo_nombre,))
        tipo_id = cursor.fetchone()['id']
        cursor.execute(
            '''INSERT INTO servicios
               (tipo_servicio_id, nombre, precio_base, imagen, descripcion, disponible)
               VALUES (%s, %s, %s, %s, %s, TRUE)''',
            (tipo_id, nombre, precio, imagen, descripcion)
        )


@app.route('/')
def inicio():
    """
    Ruta raÃ­z del sitio web (PÃºblica).
    Renderiza la vista principal con informaciÃ³n de la empresa y catÃ¡logo destacado.
    Accesible libremente para visitantes no autenticados y usuarios con sesiÃ³n activa.
    Los visitantes no autenticados ven solo servicios disponibles.
    Los usuarios autenticados pueden ver tambiÃ©n los servicios que se darÃ¡n mÃ¡s adelante.
    """
    mensaje = "Sistemas de alarma inteligentes con detección inmediata de intrusos, alertas en tiempo real al celular y monitoreo remoto en Lago Agrio (Nueva Loja)"
    empresa = {
        "nombre": "MEGASEG CIA. LTDA.",
        "ubicacion": "Calle José María Urbina y Tungurahua, Lago Agrio - Sucumbíos",
        "modalidad": "Monitoreo remoto 24/7 y soporte técnico especializado",
        "direccion": "Calle José María Urbina y Tungurahua, Lago Agrio",
        "telefonos": "099 140 2860 / 098 290 0705",
        "telefono_principal": "099 140 2860",
        "telefono_secundario": "098 290 0705",
        "whatsapp_url": "https://wa.me/593991402860?text=Hola%20MEGASEG%20CIA.%20LTDA.,%20deseo%20m%C3%A1s%20informaci%C3%B3n%20sobre%20sus%20sistemas%20de%20alarma%20y%20soluciones%20de%20seguridad.",
        "facebook_url": "https://www.facebook.com"
    }
    tipos_servicio = []
    servicios_destacados = []
    base_datos_disponible = False
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        asegurar_servicios_minimos(cursor)
        conn.commit()
        base_datos_disponible = True
        cursor.execute('SELECT * FROM tipos_servicio ORDER BY nombre')
        tipos_servicio = cursor.fetchall()

        # La portada muestra solo los tres servicios vigentes con mayor
        # demanda; el catÃ¡logo completo queda en /servicios.
        cursor.execute('''
            SELECT s.*, t.nombre AS tipo_nombre,
                   COUNT(d.id) AS unidades_solicitadas
            FROM servicios s
            JOIN tipos_servicio t ON s.tipo_servicio_id = t.id
            LEFT JOIN detalle_factura d ON d.servicio_id = s.id
            WHERE s.disponible = TRUE
            GROUP BY s.id, t.nombre
            ORDER BY unidades_solicitadas DESC, s.id ASC
            LIMIT 3
        ''')
        servicios_destacados = cursor.fetchall()
        cursor.close()
        conn.close()
    except psycopg2.Error:
        app.logger.exception('No se pudo cargar el catÃ¡logo de la portada.')

    return render_template(
        'index.html',
        mensaje=mensaje,
        empresa=empresa,
        servicios=servicios_destacados,
        tipos_servicio=tipos_servicio,
        base_datos_disponible=base_datos_disponible
    )



# ==============================================================================
# MÃDULO DE AUTENTICACIÃN, REGISTRO Y SEGURIDAD (Semana 14 & RBAC)
# ==============================================================================

@app.route('/registro', methods=['GET', 'POST'])
def registro():
    """
    Ruta para el registro de nuevos usuarios con validaciÃ³n de seguridad,
    mayorÃ­a de edad y formulario completo.
    """
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    form = UsuarioForm()
    try:
        roles_bd = Role.get_all()
    except Exception:
        app.logger.exception('No se pudieron cargar los roles durante el registro.')
        flash('No se pudo conectar con la base de datos. Revisa DATABASE_URL y los logs de Render.', 'danger')
        return render_template(
            '500.html',
            diagnostico='La base de datos no respondiÃ³ al cargar los roles.'
        ), 503
    form.rol_id.choices = [(r['id'], r['nombre']) for r in roles_bd]

    if request.method == 'GET':
        pregunta = generar_captcha()
        form.captcha_pregunta.data = pregunta
        return render_template('registro.html', form=form, captcha_pregunta_texto=pregunta)

    if form.validate_on_submit():
        token_recaptcha = (form.recaptcha_token.data or request.form.get('g-recaptcha-response') or '').strip()
        if not verificar_recaptcha(token_recaptcha):
            flash('La validaciÃ³n anti-bot fallÃ³. IntÃ©ntalo nuevamente.', 'danger')
            pregunta = generar_captcha()
            form.captcha_pregunta.data = pregunta
            return render_template('registro.html', form=form, captcha_pregunta_texto=pregunta)

        respuesta_esperada = session.get('captcha_respuesta')
        respuesta_usuario = (form.captcha_respuesta.data or '').strip()
        if not respuesta_esperada or respuesta_usuario != respuesta_esperada:
            flash('La respuesta de verificaciÃ³n anti-bot es incorrecta.', 'danger')
            pregunta = generar_captcha()
            form.captcha_pregunta.data = pregunta
            return render_template('registro.html', form=form, captcha_pregunta_texto=pregunta)

        usuario_limpio = form.usuario.data.strip()
        correo_limpio = form.correo.data.strip().lower()
        nombres_limpios = form.nombres.data.strip()
        apellidos_limpios = form.apellidos.data.strip()
        telefono_limpio = (form.telefono.data or '').strip()

        if not validar_nombre_persona(nombres_limpios):
            flash('Los nombres solo pueden contener letras y espacios.', 'danger')
            pregunta = generar_captcha()
            form.captcha_pregunta.data = pregunta
            return render_template('registro.html', form=form, captcha_pregunta_texto=pregunta)

        if not validar_nombre_persona(apellidos_limpios):
            flash('Los apellidos solo pueden contener letras y espacios.', 'danger')
            pregunta = generar_captcha()
            form.captcha_pregunta.data = pregunta
            return render_template('registro.html', form=form, captcha_pregunta_texto=pregunta)

        if not validar_telefono_10_digitos(telefono_limpio):
            flash('El telÃ©fono debe contener exactamente 10 dÃ­gitos numÃ©ricos.', 'danger')
            pregunta = generar_captcha()
            form.captcha_pregunta.data = pregunta
            return render_template('registro.html', form=form, captcha_pregunta_texto=pregunta)

        if not form.mayor_edad.data:
            flash('Debes confirmar que eres mayor de edad para registrarte.', 'danger')
            pregunta = generar_captcha()
            form.captcha_pregunta.data = pregunta
            return render_template('registro.html', form=form, captcha_pregunta_texto=pregunta)

        if not form.acepta_terminos.data:
            flash('Debes aceptar los tÃ©rminos y condiciones para continuar.', 'danger')
            pregunta = generar_captcha()
            form.captcha_pregunta.data = pregunta
            return render_template('registro.html', form=form, captcha_pregunta_texto=pregunta)

        try:
            fecha_nacimiento = form.fecha_nacimiento.data
            hoy = date.today()
            edad = hoy.year - fecha_nacimiento.year - ((hoy.month, hoy.day) < (fecha_nacimiento.month, fecha_nacimiento.day))
            if edad < 18:
                raise ValueError
        except Exception:
            flash('La fecha de nacimiento es obligatoria y debes ser mayor de edad.', 'danger')
            pregunta = generar_captcha()
            form.captcha_pregunta.data = pregunta
            return render_template('registro.html', form=form, captcha_pregunta_texto=pregunta)

        if not validar_password_segura(form.password.data):
            flash('La contraseÃ±a debe tener al menos 8 caracteres, incluir mayÃºsculas, minÃºsculas, nÃºmeros y un sÃ­mbolo.', 'danger')
            pregunta = generar_captcha()
            form.captcha_pregunta.data = pregunta
            return render_template('registro.html', form=form, captcha_pregunta_texto=pregunta)

        if Usuario.get_by_usuario(usuario_limpio):
            flash('El nombre de usuario ya se encuentra registrado. Elige otro.', 'danger')
            pregunta = generar_captcha()
            form.captcha_pregunta.data = pregunta
            return render_template('registro.html', form=form, captcha_pregunta_texto=pregunta)

        if Usuario.get_by_correo(correo_limpio):
            flash('Ya existe una cuenta con este correo electrÃ³nico. Inicia sesiÃ³n o usa otro.', 'danger')
            pregunta = generar_captcha()
            form.captcha_pregunta.data = pregunta
            return render_template('registro.html', form=form, captcha_pregunta_texto=pregunta)

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            '''SELECT 1
               FROM information_schema.columns
               WHERE table_name = 'usuarios' AND column_name = 'telefono' '''
        )
        telefono_configurado = cursor.fetchone() is not None
        if not telefono_configurado:
            cursor.close()
            conn.close()
            flash('La base de datos aun no tiene configurado el campo de celular. Ejecuta la migracion indicada.', 'danger')
            pregunta = generar_captcha()
            form.captcha_pregunta.data = pregunta
            return render_template('registro.html', form=form, captcha_pregunta_texto=pregunta)
        cursor.execute(
            'SELECT 1 FROM usuarios WHERE telefono = %s LIMIT 1',
            (telefono_limpio,)
        )
        telefono_repetido = cursor.fetchone() is not None
        cursor.close()
        conn.close()
        if telefono_repetido:
            flash('Ya existe una cuenta con este nÃºmero de celular. Usa otro.', 'danger')
            pregunta = generar_captcha()
            form.captcha_pregunta.data = pregunta
            return render_template('registro.html', form=form, captcha_pregunta_texto=pregunta)

        rol_obj = Role.get_by_id(form.rol_id.data)
        rol_nombre = rol_obj['nombre'] if rol_obj else 'Cliente'
        # Los roles operativos pueden iniciar sesiÃ³n inmediatamente.
        # Solo una cuenta que solicita privilegios de Administrador requiere
        # aprobaciÃ³n explÃ­cita desde el panel administrativo.
        aprobado = (rol_nombre != 'Administrador')
        password_hashed = User.hash_password(form.password.data)

        conn = None
        cursor = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'usuarios' AND column_name IN ('nombres', 'apellidos', 'telefono', 'fecha_nacimiento', 'es_mayor_edad', 'acepta_terminos')")
            columnas_extra = {row['column_name'] for row in cursor.fetchall()}

            campos = ['usuario', 'correo', 'password', 'rol_id', 'activo', 'email_confirmado', 'aprobado', 'dos_factores_activo']
            valores = [usuario_limpio, correo_limpio, password_hashed, form.rol_id.data, True, True, aprobado, False]

            if 'nombres' in columnas_extra:
                campos.append('nombres'); valores.append(nombres_limpios)
            if 'apellidos' in columnas_extra:
                campos.append('apellidos'); valores.append(apellidos_limpios)
            if 'telefono' in columnas_extra:
                campos.append('telefono'); valores.append(telefono_limpio)
            if 'fecha_nacimiento' in columnas_extra:
                campos.append('fecha_nacimiento'); valores.append(form.fecha_nacimiento.data)
            if 'es_mayor_edad' in columnas_extra:
                campos.append('es_mayor_edad'); valores.append(True)
            if 'acepta_terminos' in columnas_extra:
                campos.append('acepta_terminos'); valores.append(True)

            placeholders = ', '.join(['%s'] * len(campos))
            columnas_sql = ', '.join(campos)
            sql = f'''INSERT INTO usuarios ({columnas_sql}) VALUES ({placeholders}) RETURNING id'''
            cursor.execute(sql, tuple(valores))
            nuevo_id = cursor.fetchone()['id']
            conn.commit()
        except psycopg2.IntegrityError:
            if conn:
                conn.rollback()
            app.logger.exception('Registro rechazado por una restricciÃ³n de PostgreSQL.')
            flash('No se pudo guardar: el usuario, correo o telÃ©fono ya existe. Verifica los datos e intÃ©ntalo nuevamente.', 'danger')
            pregunta = generar_captcha()
            form.captcha_pregunta.data = pregunta
            return render_template('registro.html', form=form, captcha_pregunta_texto=pregunta), 409
        except psycopg2.Error:
            if conn:
                conn.rollback()
            app.logger.exception('PostgreSQL fallÃ³ al guardar un nuevo usuario.')
            flash('No se pudo guardar la informaciÃ³n porque la base de datos no respondiÃ³. IntÃ©ntalo nuevamente en unos segundos.', 'danger')
            pregunta = generar_captcha()
            form.captcha_pregunta.data = pregunta
            return render_template('registro.html', form=form, captcha_pregunta_texto=pregunta), 503
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

        ActivityLog.registrar(
            nuevo_id, usuario_limpio, 'REGISTRO_USUARIO',
            request.remote_addr, f"Rol solicitado: {rol_nombre} | Aprobado: {aprobado} | Mayor de edad: true"
        )

        if not aprobado:
            flash(
                f'La informaciÃ³n se ha guardado correctamente. Es un gusto tenerte en MEGASEG CIA. LTDA., '
                f'{usuario_limpio}. Como solicitaste el rol de {rol_nombre}, un Administrador activo '
                'deberÃ¡ aprobar tu acceso antes de poder iniciar sesiÃ³n.',
                'warning'
            )
        else:
            flash(
                f'La informaciÃ³n se ha guardado correctamente. Es un gusto tenerte en MEGASEG CIA. LTDA., '
                f'{usuario_limpio}. Tu cuenta con rol {rol_nombre} ya estÃ¡ lista; puedes iniciar sesiÃ³n.',
                'success'
            )

        return redirect(url_for('login'))

    pregunta = session.get('captcha_pregunta') or generar_captcha()
    form.captcha_pregunta.data = pregunta
    return render_template('registro.html', form=form, captcha_pregunta_texto=pregunta)


@app.route('/health')
def health():
    """ComprobaciÃ³n simple para Render: proceso web y PostgreSQL."""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT 1')
        cursor.fetchone()
        cursor.execute(
            '''SELECT table_name
               FROM information_schema.tables
               WHERE table_schema = 'public'
                 AND table_name IN (
                     'roles', 'usuarios', 'clientes', 'servicios',
                     'facturacion', 'detalle_factura', 'solicitudes',
                     'proveedores'
                 )'''
        )
        tablas = {fila['table_name'] for fila in cursor.fetchall()}
        tablas_requeridas = {
            'roles', 'usuarios', 'clientes', 'servicios',
            'facturacion', 'detalle_factura', 'solicitudes', 'proveedores'
        }
        faltantes = sorted(tablas_requeridas - tablas)
        if faltantes:
            app.logger.error('Esquema incompleto. Faltan tablas: %s', ', '.join(faltantes))
            return {
                'status': 'error',
                'database': 'connected',
                'schema': 'incomplete',
                'missing_tables': faltantes
            }, 503

        cursor.execute(
            '''SELECT table_name, column_name
               FROM information_schema.columns
               WHERE table_schema = 'public'
                 AND (
                     (table_name = 'solicitudes' AND column_name IN
                        ('estado', 'responsable_id', 'trabajo_realizado', 'evidencia_url'))
                     OR
                     (table_name = 'usuarios' AND column_name IN
                        ('activo', 'aprobado', 'rol_id'))
                 )'''
        )
        columnas = {(fila['table_name'], fila['column_name']) for fila in cursor.fetchall()}
        columnas_requeridas = {
            ('solicitudes', 'estado'),
            ('solicitudes', 'responsable_id'),
            ('solicitudes', 'trabajo_realizado'),
            ('solicitudes', 'evidencia_url'),
            ('usuarios', 'activo'),
            ('usuarios', 'aprobado'),
            ('usuarios', 'rol_id')
        }
        columnas_faltantes = sorted(
            f'{tabla}.{columna}'
            for tabla, columna in columnas_requeridas - columnas
        )
        if columnas_faltantes:
            app.logger.error(
                'Columnas requeridas ausentes: %s',
                ', '.join(columnas_faltantes)
            )
            return {
                'status': 'error',
                'database': 'connected',
                'schema': 'incomplete',
                'missing_columns': columnas_faltantes
            }, 503
        return {'status': 'ok', 'database': 'connected', 'schema': 'ready'}, 200
    except Exception:
        app.logger.exception('Healthcheck de PostgreSQL fallido.')
        return {
            'status': 'error',
            'database': 'unavailable',
            'configuration': (
                'Configura DATABASE_URL o DB_PASSWORD en el archivo .env '
                'de la raÃ­z del proyecto.'
            )
        }, 503
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@app.route('/registro/disponibilidad')
def disponibilidad_registro():
    """Comprueba en PostgreSQL si un usuario, correo o telÃ©fono ya existe."""
    campo = (request.args.get('campo') or '').strip().lower()
    valor = (request.args.get('valor') or '').strip()
    columnas_permitidas = {
        'usuario': 'usuario',
        'correo': 'correo',
        'telefono': 'telefono',
    }
    columna = columnas_permitidas.get(campo)
    if not columna or not valor:
        return {'disponible': False, 'mensaje': 'Dato no vÃ¡lido.'}, 400

    if campo == 'correo':
        valor = valor.lower()
    elif campo == 'telefono':
        valor = re.sub(r'\D', '', valor)

    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            '''SELECT 1
               FROM information_schema.columns
               WHERE table_name = 'usuarios' AND column_name = %s''',
            (columna,)
        )
        if cursor.fetchone() is None:
            return {
                'disponible': False,
                'mensaje': 'Este campo aun no esta configurado en la base de datos.'
            }, 503
        cursor.execute(
            f'SELECT 1 FROM usuarios WHERE {columna} = %s LIMIT 1',
            (valor,)
        )
        existe = cursor.fetchone() is not None
        cursor.close()
        return {
            'disponible': not existe,
            'mensaje': (
                'Este dato ya estÃ¡ registrado.'
                if existe else 'Disponible.'
            ),
        }
    finally:
        conn.close()


@app.route('/login', methods=['GET', 'POST'])
def login():
    """
    Ruta para el inicio de sesiÃ³n de usuarios.
    Permite autenticarse por nombre de usuario o por correo electrÃ³nico.
    Verifica contraseÃ±as seguras (Bcrypt con fallback a Werkzeug).
    Bloquea a usuarios con rol Administrador que aÃºn no han sido aprobados por un Administrador activo.
    Gestiona flujo de 2FA si estÃ¡ habilitado y caducidad de sesiÃ³n.
    """
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    form = LoginForm()
    if form.validate_on_submit():
        identificador = (form.usuario.data or '').strip()
        password = form.password.data or ''
        try:
            user = Usuario.get_by_usuario_o_correo(identificador)
        except psycopg2.Error:
            app.logger.exception('No se pudo consultar el usuario durante el login.')
            flash('La base de datos de Render no estÃ¡ disponible en este momento. Espera unos segundos y vuelve a intentarlo.', 'warning')
            return render_template('login.html', form=form), 503

        # La identidad se busca por usuario/correo y la contraseÃ±a se verifica
        # contra su hash; nunca se compara la contraseÃ±a dentro de SQL.
        if user and user.check_password(password):
            # Validar si el usuario estÃ¡ activo
            if not user.activo:
                registrar_log('LOGIN_BLOQUEADO', f"Usuario inactivo: {user.usuario}")
                flash('Tu cuenta se encuentra temporalmente desactivada. Contacta al Administrador.', 'danger')
                return render_template('login.html', form=form)

            # Validar si el usuario requiere aprobaciÃ³n y aÃºn no ha sido autorizado
            if not user.aprobado:
                registrar_log('LOGIN_PENDIENTE_APROBACION', f"Intento de acceso no aprobado ({user.rol_nombre}): {user.usuario}")
                flash(f'Tu solicitud de rol {user.rol_nombre} estÃ¡ pendiente de aprobaciÃ³n por un Administrador activo del sistema.', 'warning')
                return render_template('login.html', form=form)

            # VerificaciÃ³n en dos pasos (2FA) si estÃ¡ activada
            if user.dos_factores_activo:
                codigo_otp = f"{random.randint(100000, 999999)}"
                session['2fa_user_id'] = user.id
                session['2fa_codigo'] = codigo_otp
                session['2fa_remember'] = form.recordarme.data
                session['temp_user_nombre'] = user.usuario

                try:
                    conn = get_db_connection()
                    cur = conn.cursor()
                    cur.execute('UPDATE usuarios SET dos_factores_codigo = %s WHERE id = %s', (codigo_otp, user.id))
                    conn.commit()
                    cur.close()
                    conn.close()
                except psycopg2.Error:
                    if 'cur' in locals() and cur:
                        cur.close()
                    if 'conn' in locals() and conn:
                        conn.close()
                    app.logger.exception('No se pudo guardar el cÃ³digo 2FA durante el login.')
                    flash('La base de datos no pudo preparar la verificaciÃ³n 2FA. IntÃ©ntalo nuevamente.', 'warning')
                    return render_template('login.html', form=form), 503

                registrar_log('SOLICITUD_2FA', f"CÃ³digo 2FA generado para {user.usuario}")
                flash('Ingresa el cÃ³digo de verificaciÃ³n en dos pasos (2FA) para completar el acceso.', 'info')
                return redirect(url_for('verificar_2fa'))

            # Inicio de sesiÃ³n normal
            session.permanent = True
            login_user(user, remember=form.recordarme.data)
            registrar_log('LOGIN_EXITOSO', f"Inicio de sesiÃ³n exitoso como {user.rol_nombre}")
            flash(f'Â¡Bienvenido/a al sistema, {user.usuario}!', 'success')
            next_page = request.args.get('next')
            if not next_page or not next_page.startswith('/'):
                next_page = url_for('dashboard')
            return redirect(next_page)
        else:
            session['temp_user_nombre'] = identificador
            app.logger.warning(
                'Login rechazado: usuario_encontrado=%s | identificador_normalizado=%s',
                user is not None,
                identificador.lower()
            )
            registrar_log('LOGIN_FALLIDO', f"Credenciales incorrectas para: {identificador}")
            flash('Credenciales incorrectas. Verifica tu usuario/correo y contraseÃ±a.', 'danger')

    return render_template('login.html', form=form)


@app.route('/verificar-2fa', methods=['GET', 'POST'])
def verificar_2fa():
    """
    Ruta para validar el segundo factor de autenticaciÃ³n (OTP numÃ©rico de 6 dÃ­gitos).
    """
    user_id = session.get('2fa_user_id')
    codigo_esperado = session.get('2fa_codigo')
    if not user_id or not codigo_esperado:
        flash('No hay una sesiÃ³n 2FA activa. Inicia sesiÃ³n nuevamente.', 'warning')
        return redirect(url_for('login'))

    form = DosFactoresForm()
    if form.validate_on_submit():
        if form.codigo.data.strip() == codigo_esperado:
            user = Usuario.get_by_id(user_id)
            if user:
                session.permanent = True
                login_user(user, remember=session.get('2fa_remember', False))
                # Limpiar variables temporales de 2FA
                session.pop('2fa_user_id', None)
                session.pop('2fa_codigo', None)
                session.pop('2fa_remember', None)
                session.pop('temp_user_nombre', None)

                registrar_log('LOGIN_2FA_EXITOSO', f"2FA validado para {user.usuario}")
                flash(f'Â¡AutenticaciÃ³n en dos pasos exitosa! Bienvenido/a, {user.usuario}.', 'success')
                return redirect(url_for('dashboard'))
        flash('CÃ³digo de verificaciÃ³n 2FA incorrecto o expirado.', 'danger')

    return render_template('verificar_2fa.html', form=form, codigo_simulado=codigo_esperado)


@app.route('/confirmar-correo/<token>')
def confirmar_correo(token):
    """
    SimulaciÃ³n de confirmaciÃ³n de correo electrÃ³nico.
    """
    user = Usuario.get_by_usuario_o_correo(token)
    if user:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('UPDATE usuarios SET email_confirmado = TRUE WHERE id = %s', (user.id,))
        conn.commit()
        cur.close()
        conn.close()
        registrar_log('EMAIL_CONFIRMADO', f"Correo confirmado para {user.usuario}")
        flash('Â¡Tu direcciÃ³n de correo ha sido confirmada con Ã©xito!', 'success')
    else:
        flash('Token o enlace de confirmaciÃ³n invÃ¡lido.', 'danger')
    return redirect(url_for('login'))


@app.route('/logout')
@login_required
def logout():
    """
    Ruta para el cierre de sesiÃ³n seguro.
    Registra el evento en auditorÃ­a, destruye la sesiÃ³n con logout_user y redirige al login.
    """
    registrar_log('LOGOUT', f'SesiÃ³n cerrada por {current_user.usuario}')
    logout_user()
    flash('Has cerrado sesiÃ³n correctamente. Â¡Hasta pronto!', 'info')
    return redirect(url_for('login'))


@app.route('/dashboard')
@login_required
def dashboard():
    """
    Panel administrativo principal protegido por autenticaciÃ³n.
    Muestra mÃ©tricas globales y accesos rÃ¡pidos adaptados al rol del usuario.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    if current_user.rol_nombre == 'Cliente':
        total_clientes = 0
    else:
        cursor.execute('SELECT COUNT(*) AS total FROM clientes')
        total_clientes = cursor.fetchone()['total']

    cursor.execute('SELECT COUNT(*) AS total FROM servicios')
    total_servicios = cursor.fetchone()['total']

    if current_user.rol_nombre == 'Cliente':
        cursor.execute('''
            SELECT COUNT(*) AS total
            FROM facturacion f
            JOIN clientes c ON f.cliente_cedula = c.cedula
            WHERE LOWER(TRIM(c.correo)) = LOWER(TRIM(%s))
               OR c.cedula = %s
        ''', (current_user.correo, current_user.usuario))
    else:
        cursor.execute('SELECT COUNT(*) AS total FROM facturacion')
    total_facturas = cursor.fetchone()['total']

    if current_user.rol_nombre == 'Cliente':
        total_proveedores = 0
    else:
        cursor.execute('SELECT COUNT(*) AS total FROM proveedores')
        total_proveedores = cursor.fetchone()['total']

    # Si es Cliente, muestra Ãºnicamente sus propios documentos comerciales
    if current_user.rol_nombre == 'Cliente':
        cursor.execute('''
            SELECT f.*, c.nombre AS cliente_nombre, e.nombre AS estado_nombre
            FROM facturacion f
            JOIN clientes c ON f.cliente_cedula = c.cedula
            JOIN estados_documento e ON f.estado_id = e.id
            WHERE LOWER(TRIM(c.correo)) = LOWER(TRIM(%s))
               OR c.cedula = %s
            ORDER BY f.fecha DESC, f.numero DESC
            LIMIT 5
        ''', (current_user.correo, current_user.usuario))
    else:
        # Consulta JOIN general para Administrador, Gestor y Soporte
        cursor.execute('''
            SELECT f.*, c.nombre AS cliente_nombre, e.nombre AS estado_nombre
            FROM facturacion f
            JOIN clientes c ON f.cliente_cedula = c.cedula
            JOIN estados_documento e ON f.estado_id = e.id
            ORDER BY f.fecha DESC, f.numero DESC
            LIMIT 5
        ''')
    ultimas_facturas = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        'dashboard.html',
        total_clientes=total_clientes,
        total_servicios=total_servicios,
        total_facturas=total_facturas,
        total_proveedores=total_proveedores,
        ultimas_facturas=ultimas_facturas
    )


# ==============================================================================
# MÃDULO EXCLUSIVO DE ADMINISTRACIÃN (RBAC & AUDITORÃA)
# ==============================================================================

@app.route('/admin/usuarios')
@login_required
@role_required('Administrador')
def admin_usuarios():
    """
    Panel de gestiÃ³n de cuentas y roles de usuario.
    Permite autorizar nuevas solicitudes de rol Administrador y reasignar roles.
    Muestra la matriz de permisos granulares asociada en la tabla rol_permisos.
    """
    usuarios = Usuario.get_all()
    roles = Role.get_all()

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('''
        SELECT r.id AS rol_id, r.nombre AS rol_nombre, p.codigo, p.descripcion
        FROM roles r
        JOIN rol_permisos rp ON r.id = rp.rol_id
        JOIN permisos p ON rp.permiso_id = p.id
        ORDER BY r.id, p.codigo
    ''')
    filas_permisos = cur.fetchall()
    cur.close()
    conn.close()

    permisos_por_rol = {}
    for f in filas_permisos:
        permisos_por_rol.setdefault(f['rol_nombre'], []).append({
            'codigo': f['codigo'],
            'descripcion': f['descripcion']
        })

    return render_template(
        'admin_usuarios.html',
        usuarios=usuarios,
        roles=roles,
        permisos_por_rol=permisos_por_rol
    )


@app.route('/admin/aprobar-usuario/<int:id>', methods=['POST'])
@login_required
@role_required('Administrador')
def admin_aprobar_usuario(id):
    """
    Aprueba una solicitud de rol Administrador pendiente.
    Exclusivo para administradores activos del sistema.
    """
    user = Usuario.get_by_id(id)
    if not user:
        flash('El usuario indicado no existe.', 'danger')
        return redirect(url_for('admin_usuarios'))

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('UPDATE usuarios SET aprobado = TRUE, activo = TRUE WHERE id = %s', (id,))
    conn.commit()
    cur.close()
    conn.close()

    registrar_log('APROBAR_ADMINISTRADOR', f"El administrador {current_user.usuario} aprobÃ³ la cuenta de {user.usuario}")
    flash(f'El usuario {user.usuario} ha sido aprobado exitosamente como Administrador. Ya puede iniciar sesiÃ³n.', 'success')
    return redirect(url_for('admin_usuarios'))


@app.route('/admin/cambiar-rol/<int:id>', methods=['POST'])
@login_required
@role_required('Administrador')
def admin_cambiar_rol(id):
    """
    Modifica el rol asignado a un usuario existente en PostgreSQL.
    """
    nuevo_rol_id = request.form.get('nuevo_rol_id', type=int)
    if not nuevo_rol_id:
        flash('Rol invÃ¡lido.', 'danger')
        return redirect(url_for('admin_usuarios'))

    rol_obj = Role.get_by_id(nuevo_rol_id)
    if not rol_obj:
        flash('El rol seleccionado no es vÃ¡lido.', 'danger')
        return redirect(url_for('admin_usuarios'))

    user = Usuario.get_by_id(id)
    if not user:
        flash('El usuario no existe.', 'danger')
        return redirect(url_for('admin_usuarios'))

    conn = get_db_connection()
    cur = conn.cursor()
    # Si un Administrador activo le asigna el rol Administrador, queda aprobado automÃ¡ticamente
    cur.execute('UPDATE usuarios SET rol_id = %s, aprobado = TRUE WHERE id = %s', (nuevo_rol_id, id))
    conn.commit()
    cur.close()
    conn.close()

    registrar_log('CAMBIO_ROL', f"El administrador {current_user.usuario} cambiÃ³ el rol de {user.usuario} a {rol_obj['nombre']}")
    flash(f'Rol de {user.usuario} actualizado exitosamente a {rol_obj["nombre"]}.', 'success')
    return redirect(url_for('admin_usuarios'))


@app.route('/admin/restablecer-password/<int:id>', methods=['POST'])
@login_required
@role_required('Administrador')
def admin_restablecer_password(id):
    """Genera una contraseÃ±a temporal para una cuenta sin usar correo electrÃ³nico."""
    user = Usuario.get_by_id(id)
    if not user:
        flash('El usuario no existe.', 'danger')
        return redirect(url_for('admin_usuarios'))

    password_temporal = f"Nexo-{secrets.token_urlsafe(6)}!"
    password_hashed = User.hash_password(password_temporal)

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        '''UPDATE usuarios
           SET password = %s, activo = TRUE, aprobado = TRUE,
               dos_factores_activo = TRUE, dos_factores_codigo = NULL
           WHERE id = %s''',
        (password_hashed, id)
    )
    conn.commit()
    cur.close()
    conn.close()

    registrar_log(
        'RESTABLECER_PASSWORD',
        f'El administrador {current_user.usuario} generÃ³ una contraseÃ±a temporal para {user.usuario}'
    )
    flash(
        f'ContraseÃ±a temporal para {user.usuario}: {password_temporal}. '
        'EntrÃ©gala de forma privada y solicita cambiarla despuÃ©s de iniciar sesiÃ³n.',
        'warning'
    )
    return redirect(url_for('admin_usuarios'))


@app.route('/admin/logs')
@login_required
@role_required('Administrador')
def admin_logs():
    """
    Visualiza el registro histÃ³rico de auditorÃ­a de actividad del sistema.
    """
    filtros = {
        'fecha_desde': request.args.get('fecha_desde', '').strip(),
        'fecha_hasta': request.args.get('fecha_hasta', '').strip(),
        'hora_desde': request.args.get('hora_desde', '').strip(),
        'hora_hasta': request.args.get('hora_hasta', '').strip(),
        'persona': request.args.get('persona', '').strip(),
        'accion': request.args.get('accion', '').strip(),
        'ip': request.args.get('ip', '').strip(),
        'detalles': request.args.get('detalles', '').strip(),
    }
    for nombre_filtro, formato in (
        ('fecha_desde', '%Y-%m-%d'),
        ('fecha_hasta', '%Y-%m-%d'),
        ('hora_desde', '%H:%M'),
        ('hora_hasta', '%H:%M'),
    ):
        valor = filtros[nombre_filtro]
        if valor:
            try:
                datetime.strptime(valor, formato)
            except ValueError:
                filtros[nombre_filtro] = ''
                flash(f'El filtro {nombre_filtro.replace("_", " ")} no es vÃ¡lido.', 'warning')
    logs = ActivityLog.buscar(**filtros)
    acciones_disponibles = ActivityLog.acciones_disponibles()
    return render_template(
        'admin_logs.html',
        logs=logs,
        filtros=filtros,
        acciones_disponibles=acciones_disponibles
    )


@app.route('/solicitudes', methods=['GET'])
@login_required
@role_required('Administrador', 'Gestor de proyectos', 'Soporte tÃ©cnico')
def solicitudes():
    """Muestra las peticiones de clientes y permite responderlas y asignarlas."""
    conn = get_db_connection()
    cursor = conn.cursor()
    if current_user.rol_nombre == 'Soporte tÃ©cnico':
        cursor.execute('''
            SELECT s.*, u.usuario AS responsable_nombre,
                   r.usuario AS resuelto_por_nombre
            FROM solicitudes s
            LEFT JOIN usuarios u ON u.id = s.responsable_id
            LEFT JOIN usuarios r ON r.id = s.resuelto_por_id
            WHERE s.responsable_id = %s
            ORDER BY s.fecha DESC, s.id DESC
        ''', (current_user.id,))
    else:
        cursor.execute('''
            SELECT s.*, u.usuario AS responsable_nombre,
                   r.usuario AS resuelto_por_nombre
            FROM solicitudes s
            LEFT JOIN usuarios u ON u.id = s.responsable_id
            LEFT JOIN usuarios r ON r.id = s.resuelto_por_id
            ORDER BY s.fecha DESC, s.id DESC
        ''')
    solicitudes_registradas = cursor.fetchall()
    cursor.execute('''
        SELECT u.id, u.usuario
        FROM usuarios u
        JOIN roles r ON r.id = u.rol_id
        WHERE u.activo = TRUE
          AND r.nombre IN ('Administrador', 'Gestor de proyectos', 'Soporte tÃ©cnico', 'Usuario interno')
        ORDER BY u.usuario
    ''')
    responsables = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template(
        'solicitudes.html',
        solicitudes=solicitudes_registradas,
        responsables=responsables
    )


@app.route('/api/solicitudes', methods=['POST'])
def crear_solicitud():
    """Registra una peticiÃ³n pÃºblica directamente en PostgreSQL."""
    datos = request.get_json(silent=True) or request.form
    nombre = (datos.get('nombre') or '').strip()
    correo = (datos.get('correo') or '').strip().lower()
    telefono = (datos.get('telefono') or '').strip()
    tipo_servicio = (datos.get('tipo_servicio') or '').strip()
    mensaje = (datos.get('mensaje') or '').strip()

    correo_valido = re.fullmatch(r'[^@\s]+@[^@\s]+\.[^@\s]{2,}', correo)
    nombre_valido = re.fullmatch(
        r"[^\W\d_]+(?:[ .'-][^\W\d_]+)*",
        nombre,
        flags=re.UNICODE
    )
    telefono_valido = not telefono or re.fullmatch(r'\d{10}', telefono)
    if (
        not nombre_valido or len(nombre) < 4 or len(nombre) > 150
        or not correo_valido or len(correo) > 150
        or not telefono_valido or len(tipo_servicio) < 2
        or len(mensaje) < 10 or len(mensaje) > 5000
    ):
        return {
            'ok': False,
            'mensaje': 'Revisa nombre, correo, telÃ©fono (10 nÃºmeros), servicio y descripciÃ³n.'
        }, 400

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO solicitudes (nombre, correo, telefono, tipo_servicio, mensaje)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
        ''', (nombre, correo, telefono or None, tipo_servicio, mensaje))
        solicitud_id = cursor.fetchone()['id']
        conn.commit()
        return {'ok': True, 'id': solicitud_id}, 201
    except psycopg2.Error as error:
        if conn:
            conn.rollback()
        app.logger.exception('No se pudo guardar la solicitud en PostgreSQL.')
        if getattr(error, 'pgcode', None) == '42P01':
            mensaje_error = 'La tabla solicitudes no existe en la base de datos conectada.'
        elif getattr(error, 'pgcode', None) == '42703':
            mensaje_error = 'La tabla solicitudes no tiene una columna requerida por la aplicaciÃ³n.'
        else:
            mensaje_error = 'La base de datos rechazÃ³ la solicitud. Revisa la conexiÃ³n y el esquema.'
        return {
            'ok': False,
            'mensaje': mensaje_error
        }, 503
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@app.route('/solicitudes/<int:id>/actualizar', methods=['POST'])
@login_required
@role_required('Administrador', 'Gestor de proyectos', 'Soporte tÃ©cnico')
def actualizar_solicitud(id):
    """Actualiza una peticiÃ³n, su respuesta y el trabajo realizado/evidencia."""
    estado = (request.form.get('estado') or '').strip()
    responsable_id = request.form.get('responsable_id', type=int)
    respuesta_cliente = (request.form.get('respuesta_cliente') or '').strip()
    trabajo_realizado = (request.form.get('trabajo_realizado') or '').strip()
    evidencia_url = (request.form.get('evidencia_url') or '').strip()
    estados_validos = {'Pendiente', 'En revisiÃ³n', 'Asignada', 'En proceso', 'Resuelta', 'Descartada'}
    if estado not in estados_validos:
        flash('El estado seleccionado no es vÃ¡lido.', 'danger')
        return redirect(url_for('solicitudes'))
    if evidencia_url:
        evidencia_partes = urlparse(evidencia_url)
        if evidencia_partes.scheme not in ('http', 'https') or not evidencia_partes.netloc:
            flash('La evidencia debe ser un enlace http(s) vÃ¡lido.', 'danger')
            return redirect(url_for('solicitudes'))
    if estado == 'Resuelta' and not (trabajo_realizado or evidencia_url):
        flash('Para marcar una peticiÃ³n como resuelta agrega el trabajo realizado o un enlace de evidencia.', 'warning')
        return redirect(url_for('solicitudes'))

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT responsable_id FROM solicitudes WHERE id = %s', (id,))
    solicitud_actual = cursor.fetchone()
    if not solicitud_actual:
        cursor.close()
        conn.close()
        flash('La solicitud no existe.', 'danger')
        return redirect(url_for('solicitudes'))
    if current_user.rol_nombre == 'Soporte tÃ©cnico' and solicitud_actual['responsable_id'] != current_user.id:
        cursor.close()
        conn.close()
        flash('Solo puedes actualizar trabajos asignados a tu usuario.', 'danger')
        return redirect(url_for('solicitudes'))
    if current_user.rol_nombre == 'Soporte tÃ©cnico':
        responsable_id = current_user.id
    cursor.execute('''
        UPDATE solicitudes
        SET estado = %s, responsable_id = %s,
            respuesta_cliente = %s, trabajo_realizado = %s, evidencia_url = %s,
            resuelto_por_id = CASE
                WHEN %s IN ('Resuelta', 'Descartada') THEN %s
                ELSE NULL
            END,
            fecha_resolucion = CASE
                WHEN %s IN ('Resuelta', 'Descartada') THEN CURRENT_TIMESTAMP
                ELSE NULL
            END
        WHERE id = %s
    ''', (
        estado, responsable_id or None, respuesta_cliente or None,
        trabajo_realizado or None, evidencia_url or None,
        estado, current_user.id, estado, id
    ))
    if cursor.rowcount == 0:
        conn.rollback()
        cursor.close()
        conn.close()
        flash('La solicitud no existe.', 'danger')
        return redirect(url_for('solicitudes'))
    conn.commit()
    cursor.close()
    conn.close()
    registrar_log('ACTUALIZAR_SOLICITUD', f'Solicitud {id}: {estado}, responsable {responsable_id or "sin asignar"}')
    flash('La solicitud fue actualizada correctamente.', 'success')
    return redirect(url_for('solicitudes'))


# ==============================================================================
# MÃDULOS DE ADMINISTRACIÃN Y GESTIÃN CRUD (Protegidos por Roles y Permisos RBAC)
# ==============================================================================

@app.route('/productos')
@app.route('/servicio')
@app.route('/servicios')
def servicios():
    """
    Ruta del catÃ¡logo completo de servicios (PÃºblica para consulta y lectura).
    Permite que usuarios no autenticados conozcan la oferta y descripciÃ³n de servicios.
    Usa JOIN para mostrar el nombre de la categorÃ­a (tipo_servicio) de cada servicio.
    Soporta motor de bÃºsqueda multicriterio (por nombre, descripciÃ³n y categorÃ­a)
    tanto por parÃ¡metros URL (?q=...&tipo=...) como en tiempo real vÃ­a JavaScript.
    """
    q = request.args.get('q', '').strip()
    tipo = request.args.get('tipo', '').strip()

    tipos_servicio = []
    lista_servicios = []
    base_datos_disponible = False
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        asegurar_servicios_minimos(cursor)
        conn.commit()
        cursor.execute('SELECT * FROM tipos_servicio ORDER BY nombre')
        tipos_servicio = cursor.fetchall()

        params = []
        where_clauses = []
        if q:
            where_clauses.append("(s.nombre ILIKE %s OR s.descripcion ILIKE %s OR t.nombre ILIKE %s)")
            params.extend([f"%{q}%", f"%{q}%", f"%{q}%"])
        if tipo:
            where_clauses.append("t.nombre = %s")
            params.append(tipo)

        sql_where = (" WHERE " + " AND ".join(where_clauses)) if where_clauses else ""
        query = f'''
            SELECT s.*, t.nombre AS tipo_nombre,
                   COUNT(d.id) AS detalles_relacionados
            FROM servicios s
            JOIN tipos_servicio t ON s.tipo_servicio_id = t.id
            LEFT JOIN detalle_factura d ON d.servicio_id = s.id
            {sql_where}
            GROUP BY s.id, t.nombre
            ORDER BY s.disponible DESC, s.id ASC
        '''
        cursor.execute(query, tuple(params))
        lista_servicios = cursor.fetchall()
        base_datos_disponible = True
        cursor.close()
        conn.close()
    except psycopg2.Error:
        app.logger.exception('No se pudo cargar el catÃ¡logo de servicios.')
        flash(
            'No se puede consultar el catÃ¡logo porque la conexiÃ³n con la base de datos no estÃ¡ disponible.',
            'warning'
        )
    return render_template(
        'servicios.html',
        servicios=lista_servicios,
        tipos_servicio=tipos_servicio,
        query_busqueda=q,
        tipo_seleccionado=tipo,
        base_datos_disponible=base_datos_disponible
    ), (200 if base_datos_disponible else 503)



@app.route('/proveedores')
@role_required('Administrador', 'Soporte tÃ©cnico')
def proveedores():
    """
    Ruta del directorio de proveedores tecnolÃ³gicos.
    Acceso para Administrador y Soporte tÃ©cnico (infraestructura).
    Usa JOIN con estados_proveedor y categorias_proveedor para mostrar los nombres relacionados.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT p.*, e.nombre AS estado_nombre, c.nombre AS categoria_nombre
        FROM proveedores p
        JOIN estados_proveedor e ON p.estado_id = e.id
        JOIN categorias_proveedor c ON p.categoria_id = c.id
        ORDER BY p.nombre ASC, p.id ASC
    ''')
    lista_proveedores = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('proveedores.html', proveedores=lista_proveedores)


@app.route('/clientes')
@role_required('Administrador', 'Gestor de proyectos', 'Usuario interno')
def clientes():
    """
    Ruta del directorio de clientes comerciales.
    Acceso restringido a Administrador, Gestor de proyectos y Usuario interno.
    Soporte tÃ©cnico y Clientes NO tienen acceso para proteger datos sensibles.
    Usa JOIN con tipos_negocio para mostrar el nombre de la categorÃ­a de negocio.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT c.*, t.nombre AS negocio_nombre
        FROM clientes c
        JOIN tipos_negocio t ON c.tipo_negocio_id = t.id
    ''')
    lista_clientes = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('clientes.html', clientes=lista_clientes)


def sumar_meses(fecha_base, meses):
    """Suma N meses a una fecha respetando los dÃ­as del mes y aÃ±os bisiestos."""
    if not fecha_base or not meses:
        return fecha_base
    if isinstance(fecha_base, str):
        try:
            fecha_base = datetime.strptime(fecha_base, '%Y-%m-%d').date()
        except ValueError:
            return fecha_base
    mes = fecha_base.month - 1 + int(meses)
    anio = fecha_base.year + mes // 12
    mes = mes % 12 + 1
    dias_en_mes = [31, 29 if (anio % 4 == 0 and (anio % 100 != 0 or anio % 400 == 0)) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    dia = min(fecha_base.day, dias_en_mes[mes - 1])
    return date(anio, mes, dia)


@app.route('/facturacion')
@role_required('Administrador', 'Gestor de proyectos', 'Cliente')
def facturacion():
    """
    Ruta principal del panel comercial de FacturaciÃ³n y Cotizaciones.
    - Administrador, Gestor de proyectos y Usuario interno: ven los documentos del negocio.
    - Cliente: ve Ãºnicamente sus propios proyectos y cotizaciones contratadas.
    Carga documentos con historial de pagos, comprobantes y estado de amortizaciÃ³n.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    if current_user.rol_nombre == 'Cliente':
        cursor.execute('''
            SELECT f.*, c.nombre AS cliente_nombre, c.telefono AS cliente_telefono,
                   c.correo AS cliente_correo, c.ciudad AS cliente_ciudad, e.nombre AS estado_nombre
            FROM facturacion f
            JOIN clientes c ON f.cliente_cedula = c.cedula
            JOIN estados_documento e ON f.estado_id = e.id
            WHERE LOWER(TRIM(c.correo)) = LOWER(TRIM(%s))
               OR c.cedula = %s
            ORDER BY f.numero DESC
        ''', (current_user.correo, current_user.usuario))
    else:
        cursor.execute('''
            SELECT f.*, c.nombre AS cliente_nombre, c.telefono AS cliente_telefono,
                   c.correo AS cliente_correo, c.ciudad AS cliente_ciudad, e.nombre AS estado_nombre
            FROM facturacion f
            JOIN clientes c ON f.cliente_cedula = c.cedula
            JOIN estados_documento e ON f.estado_id = e.id
            ORDER BY f.numero DESC
        ''')
    filas = cursor.fetchall()

    lista_facturas = []
    if filas:
        numeros = [f['numero'] for f in filas]

        # Conteo de servicios por documento
        cursor.execute(
            'SELECT factura_numero, COUNT(*) AS total FROM detalle_factura WHERE factura_numero = ANY(%s) GROUP BY factura_numero',
            (numeros,)
        )
        conteos = {r['factura_numero']: r['total'] for r in cursor.fetchall()}

        # Historial de pagos
        cursor.execute(
            'SELECT * FROM pagos_factura WHERE factura_numero = ANY(%s) ORDER BY factura_numero, numero_pago ASC',
            (numeros,)
        )
        pagos_por_factura = {}
        for p in cursor.fetchall():
            pagos_por_factura.setdefault(p['factura_numero'], []).append(dict(p))

        # Comprobantes de pago
        cursor.execute(
            'SELECT * FROM comprobantes_pago WHERE factura_numero = ANY(%s) ORDER BY factura_numero, id DESC',
            (numeros,)
        )
        comprobantes_por_factura = {}
        for cp in cursor.fetchall():
            comprobantes_por_factura.setdefault(cp['factura_numero'], []).append(dict(cp))

        # Cuotas de amortizaciÃ³n
        cursor.execute(
            'SELECT * FROM cuotas_factura WHERE factura_numero = ANY(%s) ORDER BY factura_numero, numero_cuota ASC',
            (numeros,)
        )
        cuotas_por_factura = {}
        for c in cursor.fetchall():
            cuotas_por_factura.setdefault(c['factura_numero'], []).append(dict(c))

        for f in filas:
            doc = dict(f)
            num = doc['numero']
            doc['servicios_conteo'] = conteos.get(num, 0)
            doc['servicios_detalle'] = [None] * doc['servicios_conteo']

            doc['pagos'] = pagos_por_factura.get(num, [])
            doc['comprobantes'] = comprobantes_por_factura.get(num, [])
            doc['cuotas'] = cuotas_por_factura.get(num, [])

            # Asociar nÃºmero de comprobante a cada pago si existe
            comp_map = {c['pago_id']: c['numero_comprobante'] for c in doc['comprobantes']}
            for p in doc['pagos']:
                p['numero_comprobante'] = comp_map.get(p['id'])

            # Totales y saldos calculados desde base de datos
            total_deuda = float(doc.get('total_con_interes') or doc.get('monto') or 0.0)
            doc['total_deuda'] = total_deuda
            if doc['pagos']:
                total_abonado = sum(float(p['monto']) for p in doc['pagos'])
            else:
                total_abonado = float(doc.get('total_abonado') or doc.get('anticipo') or 0.0)
            doc['total_abonado'] = round(total_abonado, 2)
            doc['saldo_pendiente'] = max(0.0, round(total_deuda - total_abonado, 2))

            # PrÃ³xima cuota pendiente
            cuotas_pendientes = [c for c in doc['cuotas'] if c['estado'] != 'Pagada']
            if cuotas_pendientes:
                prox = cuotas_pendientes[0]
                doc['proxima_cuota'] = prox
                doc['proxima_cuota_texto'] = f"Cuota #{prox['numero_cuota']}: ${float(prox['saldo_cuota']):.2f}"
                doc['proxima_cuota_fecha'] = prox['fecha_vencimiento']
            else:
                doc['proxima_cuota'] = None
                doc['proxima_cuota_texto'] = "Liquidado" if doc['saldo_pendiente'] <= 0 else "Al contado"
                doc['proxima_cuota_fecha'] = doc.get('fecha_limite')

            # Normalizar nombre del estado segÃºn saldo real
            if doc['tipo'] != 'Cotizacion':
                if doc['saldo_pendiente'] <= 0:
                    doc['estado_nombre'] = 'Pagada'
                elif doc['total_abonado'] > 0:
                    doc['estado_nombre'] = 'Parcial'
                else:
                    doc['estado_nombre'] = 'Pendiente'

            doc['ultimo_comprobante'] = doc['comprobantes'][0]['numero_comprobante'] if doc['comprobantes'] else None
            lista_facturas.append(doc)

    cursor.close()
    conn.close()
    return render_template('facturacion.html', facturas=lista_facturas)


# ==============================================================================
# MÃDULO CRUD: CLIENTES
# ==============================================================================

@app.route('/clientes/nuevo', methods=['GET', 'POST'])
@role_required('Administrador', 'Gestor de proyectos')
def nuevo_cliente():
    """
    Crea y registra un nuevo cliente en el sistema. La cÃ©dula es la clave primaria.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM tipos_negocio ORDER BY nombre')
    tipos_negocio = cursor.fetchall()

    form = ClienteForm()
    form.tipo_negocio_id.choices = [(t['id'], t['nombre']) for t in tipos_negocio]

    if form.validate_on_submit():
        cursor.execute('SELECT * FROM clientes WHERE cedula = %s', (form.cedula.data.strip(),))
        existente = cursor.fetchone()
        if existente is not None:
            cursor.close()
            conn.close()
            flash('Ya existe un cliente registrado con esa cÃ©dula.', 'danger')
            return render_template('formulario_cliente.html', form=form, editando=False)

        cursor.execute(
            '''INSERT INTO clientes (cedula, nombre, telefono, correo, tipo_negocio_id, ciudad)
               VALUES (%s, %s, %s, %s, %s, %s)''',
            (form.cedula.data.strip(), form.nombre.data.strip(), form.telefono.data.strip(),
             form.correo.data.strip(), form.tipo_negocio_id.data, form.ciudad.data.strip())
        )
        conn.commit()
        cursor.close()
        conn.close()

        registrar_log('CREAR_CLIENTE', f"Cliente {form.nombre.data.strip()} ({form.cedula.data.strip()}) creado por {current_user.usuario}")
        flash('Cliente registrado correctamente.', 'success')
        return redirect(url_for('clientes'))

    cursor.close()
    conn.close()
    return render_template('formulario_cliente.html', form=form, editando=False)


@app.route('/clientes/editar/<cedula>', methods=['GET', 'POST'])
@role_required('Administrador', 'Gestor de proyectos')
def editar_cliente(cedula):
    """
    Edita la informaciÃ³n de un cliente existente identificado por su cÃ©dula (PK).
    La cÃ©dula no se modifica desde este formulario, ya que otras tablas dependen de ella.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM clientes WHERE cedula = %s', (cedula,))
    cliente = cursor.fetchone()

    if cliente is None:
        cursor.close()
        conn.close()
        flash('El cliente seleccionado no existe.', 'danger')
        return redirect(url_for('clientes'))

    cursor.execute('SELECT * FROM tipos_negocio ORDER BY nombre')
    tipos_negocio = cursor.fetchall()

    form = ClienteForm(data=dict(cliente)) if request.method == 'GET' else ClienteForm()
    form.tipo_negocio_id.choices = [(t['id'], t['nombre']) for t in tipos_negocio]
    if request.method == 'GET':
        form.tipo_negocio_id.data = cliente['tipo_negocio_id']

    if form.validate_on_submit():
        cursor.execute(
            '''UPDATE clientes SET nombre=%s, telefono=%s, correo=%s, tipo_negocio_id=%s, ciudad=%s
               WHERE cedula=%s''',
            (form.nombre.data.strip(), form.telefono.data.strip(),
             form.correo.data.strip(), form.tipo_negocio_id.data, form.ciudad.data.strip(), cedula)
        )
        conn.commit()
        cursor.close()
        conn.close()

        registrar_log('EDITAR_CLIENTE', f"Cliente {form.nombre.data.strip()} ({cedula}) actualizado por {current_user.usuario}")
        flash(f'Cliente "{form.nombre.data.strip()}" actualizado correctamente.', 'success')
        return redirect(url_for('clientes'))

    cursor.close()
    conn.close()
    return render_template('formulario_cliente.html', form=form, editando=True, cedula=cedula)


@app.route('/clientes/eliminar/<cedula>', methods=['POST'])
@role_required('Administrador')
def eliminar_cliente(cedula):
    """
    Elimina un cliente de PostgreSQL segÃºn su cÃ©dula, siempre que no tenga facturas asociadas.
    Acceso exclusivo para el rol Administrador.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM clientes WHERE cedula = %s', (cedula,))
    cliente = cursor.fetchone()

    if cliente is None:
        cursor.close()
        conn.close()
        flash('El cliente seleccionado no existe.', 'danger')
        return redirect(url_for('clientes'))

    cursor.execute(
        'SELECT COUNT(*) AS total FROM facturacion WHERE cliente_cedula = %s', (cedula,)
    )
    facturas_asociadas = cursor.fetchone()['total']

    if facturas_asociadas > 0:
        cursor.close()
        conn.close()
        flash(f'No se puede eliminar a "{cliente["nombre"]}" porque tiene {facturas_asociadas} factura(s) o cotizaciÃ³n(es) registradas.', 'danger')
        return redirect(url_for('clientes'))

    cursor.execute('DELETE FROM clientes WHERE cedula = %s', (cedula,))
    conn.commit()
    cursor.close()
    conn.close()

    registrar_log('ELIMINAR_CLIENTE', f"Cliente {cliente['nombre']} ({cedula}) eliminado por {current_user.usuario}")
    flash(f'Cliente "{cliente["nombre"]}" eliminado correctamente.', 'success')
    return redirect(url_for('clientes'))


# ==============================================================================
# MÃDULO CRUD: TIPOS DE NEGOCIO (categorÃ­as de clientes)
# ==============================================================================

@app.route('/tipos-negocio')
@role_required('Administrador')
def tipos_negocio():
    """
    Lista las categorÃ­as de tipo de negocio disponibles para clasificar clientes.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM tipos_negocio ORDER BY nombre')
    lista_tipos = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('tipos_negocio.html', tipos=lista_tipos)


@app.route('/tipos-negocio/nuevo', methods=['GET', 'POST'])
@role_required('Administrador')
def nuevo_tipo_negocio():
    """
    Registra una nueva categorÃ­a de tipo de negocio.
    """
    form = TipoNegocioForm()
    if form.validate_on_submit():
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('INSERT INTO tipos_negocio (nombre) VALUES (%s)', (form.nombre.data.strip(),))
        conn.commit()
        cursor.close()
        conn.close()
        registrar_log('CREAR_TIPO_NEGOCIO', f"Tipo de negocio {form.nombre.data.strip()} creado por {current_user.usuario}")
        flash('Tipo de negocio registrado correctamente.', 'success')
        return redirect(url_for('tipos_negocio'))
    return render_template('formulario_tipo_negocio.html', form=form, editando=False)


@app.route('/tipos-negocio/editar/<int:id>', methods=['GET', 'POST'])
@role_required('Administrador')
def editar_tipo_negocio(id):
    """
    Edita el nombre de una categorÃ­a de tipo de negocio existente.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM tipos_negocio WHERE id = %s', (id,))
    tipo = cursor.fetchone()

    if tipo is None:
        cursor.close()
        conn.close()
        flash('El tipo de negocio seleccionado no existe.', 'danger')
        return redirect(url_for('tipos_negocio'))

    form = TipoNegocioForm(data=dict(tipo)) if request.method == 'GET' else TipoNegocioForm()

    if form.validate_on_submit():
        cursor.execute('UPDATE tipos_negocio SET nombre=%s WHERE id=%s', (form.nombre.data.strip(), id))
        conn.commit()
        cursor.close()
        conn.close()
        registrar_log('EDITAR_TIPO_NEGOCIO', f"Tipo de negocio ID {id} actualizado a {form.nombre.data.strip()} por {current_user.usuario}")
        flash(f'Tipo de negocio "{form.nombre.data.strip()}" actualizado correctamente.', 'success')
        return redirect(url_for('tipos_negocio'))

    cursor.close()
    conn.close()
    return render_template('formulario_tipo_negocio.html', form=form, editando=True, id=id)


@app.route('/tipos-negocio/eliminar/<int:id>', methods=['POST'])
@role_required('Administrador')
def eliminar_tipo_negocio(id):
    """
    Elimina un tipo de negocio, siempre que ningÃºn cliente lo estÃ© usando.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM tipos_negocio WHERE id = %s', (id,))
    tipo = cursor.fetchone()

    if tipo is None:
        cursor.close()
        conn.close()
        flash('El tipo de negocio seleccionado no existe.', 'danger')
        return redirect(url_for('tipos_negocio'))

    cursor.execute('SELECT COUNT(*) AS total FROM clientes WHERE tipo_negocio_id = %s', (id,))
    en_uso = cursor.fetchone()['total']
    if en_uso > 0:
        cursor.close()
        conn.close()
        flash(f'No se puede eliminar "{tipo["nombre"]}" porque hay clientes asignados a esta categorÃ­a.', 'danger')
        return redirect(url_for('tipos_negocio'))

    cursor.execute('DELETE FROM tipos_negocio WHERE id = %s', (id,))
    conn.commit()
    cursor.close()
    conn.close()
    registrar_log('ELIMINAR_TIPO_NEGOCIO', f"Tipo de negocio {tipo['nombre']} (ID {id}) eliminado por {current_user.usuario}")
    flash(f'Tipo de negocio "{tipo["nombre"]}" eliminado correctamente.', 'success')
    return redirect(url_for('tipos_negocio'))


# ==============================================================================
# MÃDULO CRUD: TIPOS DE SERVICIO (categorÃ­as)
# ==============================================================================

@app.route('/tipos-servicio')
@role_required('Administrador')
def tipos_servicio():
    """
    Lista las categorÃ­as de servicio disponibles en el catÃ¡logo.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM tipos_servicio ORDER BY nombre')
    lista_tipos = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('tipos_servicio.html', tipos=lista_tipos)


@app.route('/tipos-servicio/nuevo', methods=['GET', 'POST'])
@role_required('Administrador')
def nuevo_tipo_servicio():
    """
    Registra una nueva categorÃ­a de servicio.
    """
    form = TipoServicioForm()
    if form.validate_on_submit():
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('INSERT INTO tipos_servicio (nombre) VALUES (%s)', (form.nombre.data.strip(),))
        conn.commit()
        cursor.close()
        conn.close()
        registrar_log('CREAR_TIPO_SERVICIO', f"CategorÃ­a de servicio {form.nombre.data.strip()} creada por {current_user.usuario}")
        flash('CategorÃ­a registrada correctamente.', 'success')
        return redirect(url_for('tipos_servicio'))
    return render_template('formulario_tipo_servicio.html', form=form, editando=False)


@app.route('/tipos-servicio/editar/<int:id>', methods=['GET', 'POST'])
@role_required('Administrador')
def editar_tipo_servicio(id):
    """
    Edita el nombre de una categorÃ­a de servicio existente.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM tipos_servicio WHERE id = %s', (id,))
    tipo = cursor.fetchone()

    if tipo is None:
        cursor.close()
        conn.close()
        flash('La categorÃ­a seleccionada no existe.', 'danger')
        return redirect(url_for('tipos_servicio'))

    form = TipoServicioForm(data=dict(tipo)) if request.method == 'GET' else TipoServicioForm()

    if form.validate_on_submit():
        cursor.execute('UPDATE tipos_servicio SET nombre=%s WHERE id=%s', (form.nombre.data.strip(), id))
        conn.commit()
        cursor.close()
        conn.close()
        registrar_log('EDITAR_TIPO_SERVICIO', f"CategorÃ­a de servicio ID {id} actualizada a {form.nombre.data.strip()} por {current_user.usuario}")
        flash(f'CategorÃ­a "{form.nombre.data.strip()}" actualizada correctamente.', 'success')
        return redirect(url_for('tipos_servicio'))

    cursor.close()
    conn.close()
    return render_template('formulario_tipo_servicio.html', form=form, editando=True, id=id)


@app.route('/tipos-servicio/eliminar/<int:id>', methods=['POST'])
@role_required('Administrador')
def eliminar_tipo_servicio(id):
    """
    Elimina una categorÃ­a de servicio, siempre que ningÃºn servicio la estÃ© usando.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM tipos_servicio WHERE id = %s', (id,))
    tipo = cursor.fetchone()

    if tipo is None:
        cursor.close()
        conn.close()
        flash('La categorÃ­a seleccionada no existe.', 'danger')
        return redirect(url_for('tipos_servicio'))

    cursor.execute('SELECT COUNT(*) AS total FROM servicios WHERE tipo_servicio_id = %s', (id,))
    en_uso = cursor.fetchone()['total']
    if en_uso > 0:
        cursor.close()
        conn.close()
        flash(f'No se puede eliminar "{tipo["nombre"]}" porque hay servicios asignados a esta categorÃ­a.', 'danger')
        return redirect(url_for('tipos_servicio'))

    cursor.execute('DELETE FROM tipos_servicio WHERE id = %s', (id,))
    conn.commit()
    cursor.close()
    conn.close()
    registrar_log('ELIMINAR_TIPO_SERVICIO', f"CategorÃ­a de servicio {tipo['nombre']} (ID {id}) eliminada por {current_user.usuario}")
    flash(f'CategorÃ­a "{tipo["nombre"]}" eliminada correctamente.', 'success')
    return redirect(url_for('tipos_servicio'))


# ==============================================================================
# MÃDULO CRUD: SERVICIOS / PRODUCTOS
# ==============================================================================

@app.route('/productos/nuevo', methods=['GET', 'POST'])
@app.route('/servicio/nuevo', methods=['GET', 'POST'])
@role_required('Administrador', 'Gestor de proyectos')
def nuevo_servicio():
    """
    Registra un nuevo servicio en el catÃ¡logo, asociado a una categorÃ­a (tipo_servicio_id).
    Acceso para Administrador y Gestor de proyectos.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM tipos_servicio ORDER BY nombre')
    tipos = cursor.fetchall()

    form = ServicioForm()
    form.tipo_servicio_id.choices = [(t['id'], t['nombre']) for t in tipos]

    if form.validate_on_submit():
        imagen_ingresada = form.imagen.data.strip() if form.imagen.data else ''
        imagen_url = resolver_url_imagen(imagen_ingresada) if imagen_ingresada else None
        if not imagen_url:
            imagen_url = "https://images.unsplash.com/photo-1460925895917-afdab827c52f"

        cursor.execute(
            '''INSERT INTO servicios (tipo_servicio_id, nombre, precio_base, imagen, descripcion, disponible)
               VALUES (%s, %s, %s, %s, %s, %s)''',
            (form.tipo_servicio_id.data, form.nombre.data.strip(), float(form.precio.data),
             imagen_url, form.descripcion.data.strip(), form.disponible.data)
        )
        conn.commit()
        cursor.close()
        conn.close()

        registrar_log('CREAR_SERVICIO', f"Servicio {form.nombre.data.strip()} creado por {current_user.usuario}")
        flash('Servicio registrado correctamente.', 'success')
        return redirect(url_for('servicios'))

    cursor.close()
    conn.close()
    return render_template('formulario_servicio.html', form=form, editando=False)


@app.route('/productos/editar/<int:id>', methods=['GET', 'POST'])
@app.route('/servicios/editar/<int:id>', methods=['GET', 'POST'])
@app.route('/servicio/editar/<int:id>', methods=['GET', 'POST'])
@role_required('Administrador', 'Gestor de proyectos', 'Soporte tÃ©cnico')
@permission_required('servicios.editar')
def editar_servicio(id):
    """
    Edita un servicio existente identificado por su id real de PostgreSQL.
    Acceso para Administrador y Gestor de proyectos.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM servicios WHERE id = %s', (id,))
    servicio = cursor.fetchone()

    if servicio is None:
        cursor.close()
        conn.close()
        flash('El servicio seleccionado no existe.', 'danger')
        return redirect(url_for('servicios'))

    cursor.execute('SELECT * FROM tipos_servicio ORDER BY nombre')
    tipos = cursor.fetchall()

    datos_form = dict(servicio)
    datos_form['precio'] = servicio['precio_base']  # el form usa 'precio', la BD usa 'precio_base'

    form = ServicioForm(data=datos_form) if request.method == 'GET' else ServicioForm()
    form.tipo_servicio_id.choices = [(t['id'], t['nombre']) for t in tipos]
    if request.method == 'GET':
        form.tipo_servicio_id.data = servicio['tipo_servicio_id']

    if form.validate_on_submit():
        imagen_ingresada = form.imagen.data.strip() if form.imagen.data else ''
        imagen_url = resolver_url_imagen(imagen_ingresada) if imagen_ingresada else servicio['imagen']
        if not imagen_url:
            imagen_url = "https://images.unsplash.com/photo-1460925895917-afdab827c52f"

        cursor.execute(
            '''UPDATE servicios SET tipo_servicio_id=%s, nombre=%s, precio_base=%s, imagen=%s, descripcion=%s, disponible=%s
               WHERE id=%s''',
            (form.tipo_servicio_id.data, form.nombre.data.strip(), float(form.precio.data),
             imagen_url, form.descripcion.data.strip(), form.disponible.data, id)
        )
        conn.commit()
        cursor.close()
        conn.close()

        registrar_log('EDITAR_SERVICIO', f"Servicio {form.nombre.data.strip()} (ID {id}) editado por {current_user.usuario}")
        flash(f'Servicio "{form.nombre.data.strip()}" actualizado correctamente.', 'success')
        return redirect(url_for('servicios'))

    cursor.close()
    conn.close()
    return render_template('formulario_servicio.html', form=form, editando=True, id=id)


@app.route('/productos/eliminar/<int:id>', methods=['POST'])
@app.route('/servicios/eliminar/<int:id>', methods=['POST'])
@app.route('/servicio/eliminar/<int:id>', methods=['POST'])
@role_required('Administrador')
def eliminar_servicio(id):
    """
    Elimina un servicio del catÃ¡logo en PostgreSQL.
    Acceso exclusivo para el rol Administrador.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM servicios WHERE id = %s', (id,))
    servicio = cursor.fetchone()

    if servicio is None:
        cursor.close()
        conn.close()
        flash('El servicio seleccionado no existe.', 'danger')
        return redirect(url_for('servicios'))

    cursor.execute(
        'SELECT COUNT(*) AS total FROM detalle_factura WHERE servicio_id = %s',
        (id,)
    )
    relaciones = cursor.fetchone()['total']
    if relaciones > 0:
        cursor.close()
        conn.close()
        flash(
            f'No se puede eliminar "{servicio["nombre"]}" porque estÃ¡ relacionado '
            f'con {relaciones} detalle(s) de factura o cotizaciÃ³n. Puedes editarlo '
            'o marcarlo como no disponible.',
            'danger'
        )
        return redirect(url_for('servicios'))

    cursor.execute('DELETE FROM servicios WHERE id = %s', (id,))
    conn.commit()
    cursor.close()
    conn.close()

    registrar_log('ELIMINAR_SERVICIO', f"Servicio {servicio['nombre']} (ID {id}) eliminado por {current_user.usuario}")
    flash(f'Servicio "{servicio["nombre"]}" eliminado correctamente.', 'success')
    return redirect(url_for('servicios'))


# ==============================================================================
# MÃDULO CRUD: PROVEEDORES
# ==============================================================================

@app.route('/proveedores/nuevo', methods=['GET', 'POST'])
@role_required('Administrador', 'Soporte tÃ©cnico')
def nuevo_proveedor():
    """
    Registra un nuevo proveedor de servicios o infraestructura en PostgreSQL.
    Acceso para Administrador y Soporte tÃ©cnico.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM estados_proveedor ORDER BY id')
    estados = cursor.fetchall()
    cursor.execute('SELECT * FROM categorias_proveedor ORDER BY nombre')
    categorias = cursor.fetchall()

    form = ProveedorForm()
    form.estado_id.choices = [(e['id'], e['nombre']) for e in estados]
    form.categoria_id.choices = [(c['id'], c['nombre']) for c in categorias]

    if form.validate_on_submit():
        cursor.execute(
            'INSERT INTO proveedores (nombre, categoria_id, sitio, estado_id) VALUES (%s, %s, %s, %s)',
            (form.nombre.data.strip(), form.categoria_id.data,
             form.sitio.data.strip(), form.estado_id.data)
        )
        conn.commit()
        cursor.close()
        conn.close()

        registrar_log('CREAR_PROVEEDOR', f"Proveedor {form.nombre.data.strip()} creado por {current_user.usuario}")
        flash('Proveedor registrado correctamente.', 'success')
        return redirect(url_for('proveedores'))

    cursor.close()
    conn.close()
    return render_template('formulario_proveedor.html', form=form, editando=False)


@app.route('/proveedores/editar/<int:id>', methods=['GET', 'POST'])
@role_required('Administrador', 'Soporte tÃ©cnico')
def editar_proveedor(id):
    """
    Modifica los datos de un proveedor existente en PostgreSQL.
    Acceso para Administrador y Soporte tÃ©cnico.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM proveedores WHERE id = %s', (id,))
    proveedor = cursor.fetchone()

    if proveedor is None:
        cursor.close()
        conn.close()
        flash('El proveedor seleccionado no existe.', 'danger')
        return redirect(url_for('proveedores'))

    cursor.execute('SELECT * FROM estados_proveedor ORDER BY id')
    estados = cursor.fetchall()
    cursor.execute('SELECT * FROM categorias_proveedor ORDER BY nombre')
    categorias = cursor.fetchall()

    form = ProveedorForm(data=dict(proveedor)) if request.method == 'GET' else ProveedorForm()
    form.estado_id.choices = [(e['id'], e['nombre']) for e in estados]
    form.categoria_id.choices = [(c['id'], c['nombre']) for c in categorias]
    if request.method == 'GET':
        form.estado_id.data = proveedor['estado_id']
        form.categoria_id.data = proveedor['categoria_id']

    if form.validate_on_submit():
        cursor.execute(
            'UPDATE proveedores SET nombre=%s, categoria_id=%s, sitio=%s, estado_id=%s WHERE id=%s',
            (form.nombre.data.strip(), form.categoria_id.data,
             form.sitio.data.strip(), form.estado_id.data, id)
        )
        conn.commit()
        cursor.close()
        conn.close()

        registrar_log('EDITAR_PROVEEDOR', f"Proveedor {form.nombre.data.strip()} (ID {id}) actualizado por {current_user.usuario}")
        flash(f'Proveedor "{form.nombre.data.strip()}" actualizado correctamente.', 'success')
        return redirect(url_for('proveedores'))

    cursor.close()
    conn.close()
    return render_template('formulario_proveedor.html', form=form, editando=True, id=id)


@app.route('/proveedores/eliminar/<int:id>', methods=['POST'])
@role_required('Administrador')
def eliminar_proveedor(id):
    """
    Elimina un proveedor de PostgreSQL.
    Acceso exclusivo para el rol Administrador.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM proveedores WHERE id = %s', (id,))
    proveedor = cursor.fetchone()

    if proveedor is None:
        cursor.close()
        conn.close()
        flash('El proveedor seleccionado no existe.', 'danger')
        return redirect(url_for('proveedores'))

    cursor.execute('DELETE FROM proveedores WHERE id = %s', (id,))
    conn.commit()
    cursor.close()
    conn.close()

    registrar_log('ELIMINAR_PROVEEDOR', f"Proveedor {proveedor['nombre']} (ID {id}) eliminado por {current_user.usuario}")
    flash(f'Proveedor "{proveedor["nombre"]}" eliminado correctamente.', 'success')
    return redirect(url_for('proveedores'))


# ==============================================================================
# MÃDULO CRUD: CATEGORÃAS DE PROVEEDOR
# ==============================================================================

@app.route('/categorias-proveedor')
@role_required('Administrador', 'Soporte tÃ©cnico')
def categorias_proveedor():
    """
    Lista las categorÃ­as de infraestructura disponibles para clasificar proveedores.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM categorias_proveedor ORDER BY nombre')
    lista_categorias = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('categorias_proveedor.html', categorias=lista_categorias)


@app.route('/categorias-proveedor/nueva', methods=['GET', 'POST'])
@role_required('Administrador', 'Soporte tÃ©cnico')
def nueva_categoria_proveedor():
    """
    Registra una nueva categorÃ­a de proveedor.
    """
    form = CategoriaProveedorForm()
    if form.validate_on_submit():
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('INSERT INTO categorias_proveedor (nombre) VALUES (%s)', (form.nombre.data.strip(),))
        conn.commit()
        cursor.close()
        conn.close()

        registrar_log('CREAR_CATEGORIA_PROVEEDOR', f"CategorÃ­a {form.nombre.data.strip()} creada por {current_user.usuario}")
        flash('CategorÃ­a registrada correctamente.', 'success')
        return redirect(url_for('categorias_proveedor'))
    return render_template('formulario_categoria_proveedor.html', form=form, editando=False)


@app.route('/categorias-proveedor/editar/<int:id>', methods=['GET', 'POST'])
@role_required('Administrador', 'Soporte tÃ©cnico')
def editar_categoria_proveedor(id):
    """
    Edita el nombre de una categorÃ­a de proveedor existente.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM categorias_proveedor WHERE id = %s', (id,))
    categoria = cursor.fetchone()

    if categoria is None:
        cursor.close()
        conn.close()
        flash('La categorÃ­a seleccionada no existe.', 'danger')
        return redirect(url_for('categorias_proveedor'))

    form = CategoriaProveedorForm(data=dict(categoria)) if request.method == 'GET' else CategoriaProveedorForm()

    if form.validate_on_submit():
        cursor.execute('UPDATE categorias_proveedor SET nombre=%s WHERE id=%s', (form.nombre.data.strip(), id))
        conn.commit()
        cursor.close()
        conn.close()

        registrar_log('EDITAR_CATEGORIA_PROVEEDOR', f"CategorÃ­a ID {id} actualizada a {form.nombre.data.strip()} por {current_user.usuario}")
        flash(f'CategorÃ­a "{form.nombre.data.strip()}" actualizada correctamente.', 'success')
        return redirect(url_for('categorias_proveedor'))

    cursor.close()
    conn.close()
    return render_template('formulario_categoria_proveedor.html', form=form, editando=True, id=id)


@app.route('/categorias-proveedor/eliminar/<int:id>', methods=['POST'])
@role_required('Administrador', 'Soporte tÃ©cnico')
def eliminar_categoria_proveedor(id):
    """
    Elimina una categorÃ­a de proveedor, siempre que ningÃºn proveedor la estÃ© usando.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM categorias_proveedor WHERE id = %s', (id,))
    categoria = cursor.fetchone()

    if categoria is None:
        cursor.close()
        conn.close()
        flash('La categorÃ­a seleccionada no existe.', 'danger')
        return redirect(url_for('categorias_proveedor'))

    cursor.execute('SELECT COUNT(*) AS total FROM proveedores WHERE categoria_id = %s', (id,))
    en_uso = cursor.fetchone()['total']
    if en_uso > 0:
        cursor.close()
        conn.close()
        flash(f'No se puede eliminar "{categoria["nombre"]}" porque hay proveedores asignados a esta categorÃ­a.', 'danger')
        return redirect(url_for('categorias_proveedor'))

    cursor.execute('DELETE FROM categorias_proveedor WHERE id = %s', (id,))
    conn.commit()
    cursor.close()
    conn.close()

    registrar_log('ELIMINAR_CATEGORIA_PROVEEDOR', f"CategorÃ­a {categoria['nombre']} (ID {id}) eliminada por {current_user.usuario}")
    flash(f'CategorÃ­a "{categoria["nombre"]}" eliminada correctamente.', 'success')
    return redirect(url_for('categorias_proveedor'))


# ==============================================================================
# MÃDULO CRUD: FACTURACIÃN
# ==============================================================================

def obtener_siguiente_numero_documento(cursor, tipo_doc):
    """
    Calcula el siguiente nÃºmero secuencial Ãºnico que NO exista en facturacion.
    Garantiza que no haya saltos innecesarios en lecturas (GET) y evita colisiones.
    """
    es_cotizacion = (tipo_doc == 'Cotizacion')
    prefijo = "COT-2026-" if es_cotizacion else "001-001-"

    # 1. Obtener todos los nÃºmeros existentes en facturaciÃ³n con este prefijo
    cursor.execute("SELECT numero FROM facturacion WHERE numero LIKE %s", (f"{prefijo}%",))
    existentes = {r['numero'] for r in cursor.fetchall()}

    max_num = 0
    for num_str in existentes:
        try:
            seg = int(num_str.split('-')[-1])
            if seg > max_num:
                max_num = seg
        except (ValueError, IndexError):
            continue

    proximo = max_num + 1

    # 2. Garantizar que el nÃºmero no colisione con ninguno existente
    while f"{prefijo}{proximo:04d}" in existentes:
        proximo += 1

    return f"{prefijo}{proximo:04d}"


@app.route('/api/siguiente-numero/<tipo>')
@login_required
def api_siguiente_numero(tipo):
    """Retorna el siguiente nÃºmero secuencial disponible para Factura o CotizaciÃ³n."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        num = obtener_siguiente_numero_documento(cursor, tipo)
        return jsonify({'numero': num})
    finally:
        cursor.close()
        conn.close()


@app.route('/facturacion/nueva', methods=['GET', 'POST'])
@role_required('Administrador', 'Gestor de proyectos')
@permission_required('facturas.crear')
def nueva_factura():
    """
    Emite un nuevo documento comercial (Factura o CotizaciÃ³n).
    El cliente se selecciona de una lista real (cliente_cedula), y cada servicio
    incluido se guarda como una fila propia en detalle_factura.
    Soporta planes de pago con amortizaciÃ³n (3 a 24 meses) e intereses.
    """
    form = FacturacionForm()
    tipo_solicitado = request.args.get('tipo', 'Cotizacion' if request.args.get('servicio_id') is not None else 'Factura')

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM clientes ORDER BY nombre')
    clientes_registrados = cursor.fetchall()
    form.cliente_cedula.choices = [(c['cedula'], c['nombre']) for c in clientes_registrados]

    cursor.execute('SELECT * FROM estados_documento ORDER BY id')
    estados = cursor.fetchall()
    form.estado_id.choices = [(e['id'], e['nombre']) for e in estados]
    id_por_nombre = {e['nombre']: e['id'] for e in estados}

    if request.method == 'GET':
        form.tipo.data = tipo_solicitado
        proximo_numero = obtener_siguiente_numero_documento(cursor, tipo_solicitado)
        form.numero.data = proximo_numero
        if tipo_solicitado == 'Cotizacion':
            form.validez.data = "15 dÃ­as"
            form.estado_id.data = id_por_nombre.get('En revision') or id_por_nombre.get('Pendiente', 2)
        else:
            form.validez.data = "30 dÃ­as"
            form.estado_id.data = id_por_nombre.get('Pendiente', 2)
        form.fecha.data = str(date.today())
        form.anticipo.data = 0.00
        form.saldo_pendiente.data = 0.00
        form.tipo_pago.data = 'contado'
        form.plazo_meses.data = 3
        form.con_intereses.data = '0'
        form.tasa_interes.data = 0.0

    if form.validate_on_submit():
        tipo_doc = form.tipo.data
        numero_limpio = form.numero.data.strip() if form.numero.data else ''

        # Si el nÃºmero viene vacÃ­o o ya existe (colisiÃ³n por formulario previo),
        # se asigna automÃ¡ticamente el siguiente nÃºmero Ãºnico disponible
        if not numero_limpio:
            numero_param = obtener_siguiente_numero_documento(cursor, tipo_doc)
        else:
            cursor.execute('SELECT 1 FROM facturacion WHERE numero = %s', (numero_limpio,))
            if cursor.fetchone() is not None:
                numero_param = obtener_siguiente_numero_documento(cursor, tipo_doc)
            else:
                numero_param = numero_limpio

        servicios_detalle = []
        if form.servicios_json.data:
            try:
                servicios_detalle = json.loads(form.servicios_json.data)
            except (TypeError, ValueError, json.JSONDecodeError):
                servicios_detalle = []

        if not servicios_detalle:
            conn.rollback()
            cursor.close()
            conn.close()
            flash('Agrega al menos un servicio antes de guardar el documento.', 'danger')
            cursor_reintento = get_db_connection()
            try:
                with cursor_reintento.cursor() as cursor_catalogo:
                    cursor_catalogo.execute('SELECT * FROM servicios ORDER BY nombre')
                    servicios_catalogo = cursor_catalogo.fetchall()
            finally:
                cursor_reintento.close()
            return render_template(
                'formulario_facturacion.html', form=form, editando=False,
                servicios_catalogo=servicios_catalogo, clientes_registrados=clientes_registrados,
                servicio_seleccionado_id=request.args.get('servicio_id', type=int)
            )

        precios_catalogo = {}
        ids_catalogo = {
            int(item.get('id')) for item in servicios_detalle
            if str(item.get('id', '')).isdigit()
        }
        if ids_catalogo:
            cursor.execute(
                'SELECT id, nombre, precio_base FROM servicios WHERE id = ANY(%s)',
                (list(ids_catalogo),)
            )
            precios_catalogo = {row['id']: row for row in cursor.fetchall()}

        detalles_validados = []
        for item in servicios_detalle:
            servicio_id = int(item.get('id')) if str(item.get('id', '')).isdigit() else None
            catalogo = precios_catalogo.get(servicio_id)
            precio = float(catalogo['precio_base']) if catalogo else float(item.get('precio', 0))
            cantidad = int(item.get('cantidad', 1))
            ajuste = float(item.get('ajuste', 0))
            if cantidad < 1 or precio < 0:
                conn.rollback()
                cursor.close()
                conn.close()
                flash('La cantidad y el precio de cada servicio deben ser vÃ¡lidos.', 'danger')
                return redirect(url_for('nueva_factura', tipo=tipo_doc))
            detalles_validados.append({
                'id': servicio_id,
                'servicio': catalogo['nombre'] if catalogo else str(item.get('servicio', 'Servicio')).strip(),
                'cantidad': cantidad,
                'precio': precio,
                'ajuste': ajuste,
                'total': (precio + ajuste) * cantidad
            })

        # Consolidar servicios si viniera alguno duplicado (solo permite una vez cada servicio)
        servicios_consolidados = {}
        for item in detalles_validados:
            sid = item['id']
            key = (sid, item['servicio'].strip().lower())
            if key in servicios_consolidados:
                servicios_consolidados[key]['cantidad'] += item['cantidad']
                servicios_consolidados[key]['total'] = (servicios_consolidados[key]['precio'] + servicios_consolidados[key]['ajuste']) * servicios_consolidados[key]['cantidad']
            else:
                servicios_consolidados[key] = dict(item)
        servicios_detalle = list(servicios_consolidados.values())

        subtotal_calculado = round(sum(item['total'] for item in servicios_detalle), 2)
        aplica_iva = float(form.iva.data or 0) > 0
        subtotal_val = subtotal_calculado
        iva_val = round(subtotal_val * 0.15, 2) if aplica_iva else 0.0
        total_original = round(subtotal_val + iva_val, 2)
        anticipo_val = float(form.anticipo.data) if form.anticipo.data is not None else 0.00

        # Plan de pagos: FinanciaciÃ³n directa NexoDigital (Sin intereses)
        forma_pago = form.forma_pago.data or 'Transferencia bancaria'
        tipo_pago = form.tipo_pago.data or 'contado'
        plazo_meses = int(form.plazo_meses.data or 3) if tipo_pago == 'plazos' else 1
        con_intereses = False
        tasa_interes = 0.0
        monto_interes = 0.0
        total_con_interes = total_original

        # REGLA CRÃTICA C: No permitir anticipo > total_deuda
        if anticipo_val > total_con_interes and total_con_interes > 0:
            conn.rollback()
            cursor.close()
            conn.close()
            flash(f'El abono recibido (${anticipo_val:.2f}) no puede superar el total de la obligaciÃ³n (${total_con_interes:.2f}).', 'danger')
            return redirect(url_for('nueva_factura', tipo=tipo_doc))

        saldo_val = max(0.0, round(total_con_interes - anticipo_val, 2))

        try:
            fecha_emision = datetime.strptime(str(form.fecha.data), '%Y-%m-%d').date()
        except (ValueError, TypeError):
            fecha_emision = date.today()

        fecha_limite = sumar_meses(fecha_emision, plazo_meses) if tipo_pago == 'plazos' else (fecha_emision + timedelta(days=30))

        # AutogeneraciÃ³n secuencial segura del nÃºmero de documento si no se proporcionÃ³
        if not numero_param or numero_param.strip() == '':
            numero_param = obtener_siguiente_numero_documento(cursor, tipo_doc)

        # REGLA CRÃTICA B: Factura fiscal generada ÃNICAMENTE cuando saldo <= 0
        numero_factura_final = None
        if tipo_doc == 'Cotizacion':
            estado_id_final = id_por_nombre.get('En revision') or id_por_nombre.get('Pendiente', 2)
            numero_factura_final = None
        else:
            if saldo_val <= 0:
                estado_id_final = id_por_nombre.get('Pagada', 1)
                numero_factura_final = numero_param
            else:
                numero_factura_final = None  # Bloqueado hasta liquidaciÃ³n total
                estado_id_final = id_por_nombre.get('Parcial') if anticipo_val > 0 else id_por_nombre.get('Pendiente', 2)

        notas_final = form.notas.data.strip() if form.notas.data else (
            "Propuesta emitida por MEGASEG CIA. LTDA." if tipo_doc == 'Cotizacion' else "Comprobante emitido por MEGASEG CIA. LTDA."
        )

        # InserciÃ³n con autogeneraciÃ³n secuencial atÃ³mica
        cursor.execute(
            '''INSERT INTO facturacion
               (numero, tipo, cliente_cedula, fecha, validez, subtotal, iva, monto, anticipo, saldo_pendiente, estado_id, notas,
                numero_factura, forma_pago, tipo_pago, plazo_meses, con_intereses, tasa_interes, monto_interes, total_con_interes, total_abonado, fecha_limite)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
               RETURNING numero''',
            (numero_param, tipo_doc, form.cliente_cedula.data, str(fecha_emision),
             form.validez.data.strip() if form.validez.data else "15 dÃ­as",
             subtotal_val, iva_val, total_original, anticipo_val, saldo_val, estado_id_final, notas_final,
             numero_factura_final, forma_pago, tipo_pago, plazo_meses, con_intereses, tasa_interes, monto_interes, total_con_interes, anticipo_val, fecha_limite)
        )
        row_insertado = cursor.fetchone()
        numero_limpio = row_insertado['numero']

        # Insertar lÃ­neas de detalle
        for item in servicios_detalle:
            cursor.execute(
                '''INSERT INTO detalle_factura (factura_numero, servicio_id, nombre_servicio, cantidad, precio_base, ajuste, total)
                   VALUES (%s, %s, %s, %s, %s, %s, %s)''',
                (numero_limpio, item.get('id'), item.get('servicio', 'Servicio'),
                 int(item.get('cantidad', 1)), float(item.get('precio', 0)),
                 float(item.get('ajuste', 0)), float(item.get('total', item.get('precio', 0))))
            )

        # Generar cuotas de amortizaciÃ³n si aplica plan de pagos
        if tipo_doc != 'Cotizacion' and tipo_pago == 'plazos' and plazo_meses >= 3:
            saldo_a_financiar = total_con_interes - anticipo_val if anticipo_val > 0 else total_con_interes
            monto_cuota_prom = round(saldo_a_financiar / plazo_meses, 2)
            suma_c = 0
            for i in range(1, plazo_meses + 1):
                f_venc = sumar_meses(fecha_emision, i)
                val_c = round(saldo_a_financiar - suma_c, 2) if i == plazo_meses else monto_cuota_prom
                suma_c += val_c
                cursor.execute(
                    '''INSERT INTO cuotas_factura (factura_numero, numero_cuota, valor_cuota, fecha_vencimiento, monto_pagado, saldo_cuota, estado)
                       VALUES (%s, %s, %s, %s, %s, %s, %s)''',
                    (numero_limpio, i, val_c, f_venc, 0, val_c, 'Pendiente')
                )

        # Si hubo un abono o anticipo inicial > 0, registrar su pago y emitir comprobante
        if tipo_doc != 'Cotizacion' and anticipo_val > 0:
            cursor.execute('''
                INSERT INTO pagos_factura (
                    factura_numero, numero_pago, monto, fecha, metodo_pago, referencia,
                    saldo_anterior, saldo_posterior, total_acumulado, registrado_por, notas
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            ''', (
                numero_limpio, 1, anticipo_val, str(fecha_emision), forma_pago,
                'Anticipo inicial', total_con_interes, saldo_val, anticipo_val, current_user.usuario, 'Abono inicial registrado'
            ))
            pago_id = cursor.fetchone()['id']

            cursor.execute("SELECT nextval('secuencia_comprobantes') AS seq")
            numero_comprobante = f"REC-2026-{cursor.fetchone()['seq']:04d}"

            cursor.execute('''
                INSERT INTO comprobantes_pago (
                    numero_comprobante, pago_id, factura_numero, cliente_cedula, fecha,
                    monto_abonado, total_deuda, total_acumulado_pagado, saldo_pendiente, observaciones
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''', (
                numero_comprobante, pago_id, numero_limpio, form.cliente_cedula.data, str(fecha_emision),
                anticipo_val, total_con_interes, anticipo_val, saldo_val, 'Comprobante de abono inicial'
            ))

        conn.commit()
        cursor.close()
        conn.close()

        nombre_doc = "CotizaciÃ³n" if tipo_doc == 'Cotizacion' else "Documento de Venta"
        registrar_log('EMITIR_FACTURA', f"{nombre_doc} {numero_limpio} emitida por {current_user.usuario} por un monto de ${total_con_interes:.2f}")
        flash(f'{nombre_doc} "{numero_limpio}" guardada correctamente.', 'success')
        return redirect(url_for('facturacion'))

    cursor.execute('SELECT * FROM servicios ORDER BY nombre')
    servicios_catalogo = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template(
        'formulario_facturacion.html',
        form=form,
        editando=False,
        servicios_catalogo=servicios_catalogo,
        clientes_registrados=clientes_registrados,
        servicio_seleccionado_id=request.args.get('servicio_id', type=int)
    )


@app.route('/facturacion/editar/<numero>', methods=['GET', 'POST'])
@role_required('Administrador', 'Gestor de proyectos')
@permission_required('facturas.editar')
def editar_factura(numero):
    """
    Edita un documento comercial existente, identificado por su nÃºmero (clave primaria).
    El nÃºmero no se modifica desde este formulario, ya que detalle_factura y pagos dependen de Ã©l.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM facturacion WHERE numero = %s', (numero,))
    fila = cursor.fetchone()

    if fila is None:
        cursor.close()
        conn.close()
        flash('El documento seleccionado no existe.', 'danger')
        return redirect(url_for('facturacion'))

    factura = dict(fila)
    cursor.execute('SELECT * FROM detalle_factura WHERE factura_numero = %s', (numero,))
    detalle_actual = cursor.fetchall()
    factura['servicios_detalle'] = [
        {'id': d['servicio_id'], 'servicio': d['nombre_servicio'], 'cantidad': int(d['cantidad']),
         'precio': float(d['precio_base']), 'ajuste': float(d['ajuste']), 'total': float(d['total'])}
        for d in detalle_actual
    ]

    cursor.execute('SELECT * FROM clientes ORDER BY nombre')
    clientes_registrados = cursor.fetchall()
    cursor.execute('SELECT * FROM estados_documento ORDER BY id')
    estados = cursor.fetchall()
    id_por_nombre = {e['nombre']: e['id'] for e in estados}

    form = FacturacionForm(data=factura) if request.method == 'GET' else FacturacionForm()
    form.cliente_cedula.choices = [(c['cedula'], c['nombre']) for c in clientes_registrados]
    form.estado_id.choices = [(e['id'], e['nombre']) for e in estados]

    if request.method == 'GET':
        form.cliente_cedula.data = factura['cliente_cedula']
        form.estado_id.data = factura['estado_id']
        form.forma_pago.data = factura.get('forma_pago') or 'Transferencia bancaria'
        form.tipo_pago.data = factura.get('tipo_pago') or 'contado'
        form.plazo_meses.data = int(factura.get('plazo_meses') or 3)
        form.con_intereses.data = '1' if factura.get('con_intereses') else '0'
        form.tasa_interes.data = float(factura.get('tasa_interes') or 0.0)
        form.servicios_json.data = json.dumps(factura['servicios_detalle'])

    if form.validate_on_submit():
        servicios_detalle = []
        if form.servicios_json.data:
            try:
                servicios_detalle = json.loads(form.servicios_json.data)
            except Exception:
                servicios_detalle = factura.get('servicios_detalle', [])

        # Consolidar servicios si viniera alguno duplicado
        servicios_consolidados = {}
        for item in servicios_detalle:
            sid = item.get('id')
            snombre = (item.get('servicio') or '').strip().lower()
            key = (sid, snombre)
            cant = int(item.get('cantidad', 1))
            prec = float(item.get('precio', 0))
            ajust = float(item.get('ajuste', 0))
            if key in servicios_consolidados:
                servicios_consolidados[key]['cantidad'] += cant
                servicios_consolidados[key]['total'] = (servicios_consolidados[key]['precio'] + servicios_consolidados[key]['ajuste']) * servicios_consolidados[key]['cantidad']
            else:
                servicios_consolidados[key] = {
                    'id': sid,
                    'servicio': item.get('servicio', 'Servicio'),
                    'cantidad': cant,
                    'precio': prec,
                    'ajuste': ajust,
                    'total': (prec + ajust) * cant
                }
        servicios_detalle = list(servicios_consolidados.values())

        # Consultar pagos registrados en base de datos (Regla 10 G)
        cursor.execute('SELECT COALESCE(SUM(monto), 0) AS total_pagos FROM pagos_factura WHERE factura_numero = %s', (numero,))
        total_pagos_bd = float(cursor.fetchone()['total_pagos'])

        anticipo_form = float(form.anticipo.data) if form.anticipo.data is not None else 0.00
        total_abonado = max(total_pagos_bd, anticipo_form)

        forma_pago = form.forma_pago.data or factura.get('forma_pago') or 'Transferencia bancaria'
        tipo_pago = form.tipo_pago.data or factura.get('tipo_pago') or 'contado'
        plazo_meses = int(form.plazo_meses.data or factura.get('plazo_meses') or 3) if tipo_pago == 'plazos' else 1
        con_intereses = False
        tasa_interes = 0.0
        monto_interes = 0.0

        subtotal_val = float(form.subtotal.data) if form.subtotal.data is not None else float(form.monto.data)
        iva_val = float(form.iva.data) if form.iva.data is not None else round(subtotal_val * 0.15, 2)
        total_original = float(form.monto.data)
        total_con_interes = total_original

        saldo_val = max(0.0, round(total_con_interes - total_abonado, 2))
        tipo_doc = form.tipo.data
        notas_final = form.notas.data.strip() if form.notas.data else "Documento generado por MEGASEG CIA. LTDA."

        try:
            fecha_emision = datetime.strptime(str(form.fecha.data), '%Y-%m-%d').date()
        except (ValueError, TypeError):
            fecha_emision = date.today()

        fecha_limite = sumar_meses(fecha_emision, plazo_meses) if tipo_pago == 'plazos' else (fecha_emision + timedelta(days=30))

        # REGLA CRÃTICA B: Factura final generada ÃNICAMENTE cuando saldo <= 0
        numero_factura_asignado = factura.get('numero_factura')
        if tipo_doc == 'Factura':
            if saldo_val <= 0:
                estado_id_final = id_por_nombre.get('Pagada', 1)
                if not numero_factura_asignado:
                    numero_factura_asignado = numero
            else:
                numero_factura_asignado = None  # Se revoca nÃºmero oficial si tiene saldo pendiente
                estado_id_final = id_por_nombre.get('Parcial') if total_abonado > 0 else id_por_nombre.get('Pendiente', 2)
        else:
            estado_id_final = form.estado_id.data

        cursor.execute(
            '''UPDATE facturacion SET
               tipo=%s, cliente_cedula=%s, fecha=%s, validez=%s,
               subtotal=%s, iva=%s, monto=%s, anticipo=%s, saldo_pendiente=%s, estado_id=%s, notas=%s,
               numero_factura=%s, forma_pago=%s, tipo_pago=%s, plazo_meses=%s,
               con_intereses=%s, tasa_interes=%s, monto_interes=%s, total_con_interes=%s,
               total_abonado=%s, fecha_limite=%s
               WHERE numero=%s''',
            (tipo_doc, form.cliente_cedula.data, str(fecha_emision),
             form.validez.data.strip() if form.validez.data else "15 dÃ­as",
             subtotal_val, iva_val, total_original, total_abonado, saldo_val, estado_id_final, notas_final,
             numero_factura_asignado, forma_pago, tipo_pago, plazo_meses,
             con_intereses, tasa_interes, monto_interes, total_con_interes,
             total_abonado, fecha_limite, numero)
        )

        cursor.execute('DELETE FROM detalle_factura WHERE factura_numero = %s', (numero,))
        for item in servicios_detalle:
            cursor.execute(
                '''INSERT INTO detalle_factura (factura_numero, servicio_id, nombre_servicio, cantidad, precio_base, ajuste, total)
                   VALUES (%s, %s, %s, %s, %s, %s, %s)''',
                (numero, item.get('id'), item.get('servicio', 'Servicio'),
                 int(item.get('cantidad', 1)), float(item.get('precio', 0)),
                 float(item.get('ajuste', 0)), float(item.get('total', item.get('precio', 0))))
            )

        conn.commit()
        cursor.close()
        conn.close()

        nombre_doc = "CotizaciÃ³n" if tipo_doc == 'Cotizacion' else "Factura"
        registrar_log('EDITAR_FACTURA', f"{nombre_doc} {numero} actualizada por {current_user.usuario}")
        flash(f'{nombre_doc} "{numero}" actualizada correctamente.', 'success')
        return redirect(url_for('facturacion'))

    cursor.execute('SELECT * FROM servicios ORDER BY nombre')
    servicios_catalogo = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template(
        'formulario_facturacion.html',
        form=form,
        editando=True,
        numero=numero,
        servicios_catalogo=servicios_catalogo,
        clientes_registrados=clientes_registrados,
        detalle_existente=factura['servicios_detalle']
    )


@app.route('/facturacion/abono/<numero>', methods=['POST'])
@role_required('Administrador', 'Gestor de proyectos')
@permission_required('facturas.editar')
def registrar_abono(numero):
    """
    Registra un abono/pago parcial o total para una factura comercial.
    Aplica controles crÃ­ticos (Reglas 10 A - 10 I):
    - TransacciÃ³n atÃ³mica en PostgreSQL.
    - ValidaciÃ³n estricta: monto > 0 y monto <= saldo_pendiente.
    - Registro en historial individual (pagos_factura).
    - GeneraciÃ³n atÃ³mica de Comprobante de Pago Ãºnico (comprobantes_pago).
    - AmortizaciÃ³n progresiva de cuotas en cuotas_factura si aplica.
    - EmisiÃ³n y asignaciÃ³n de Factura Final fiscal ÃNICAMENTE cuando saldo == 0.
    """
    monto_str = request.form.get('monto') or (request.json.get('monto') if request.is_json else '')
    fecha_pago = request.form.get('fecha') or (request.json.get('fecha') if request.is_json else '') or str(date.today())
    metodo_pago = request.form.get('metodo_pago') or (request.json.get('metodo_pago') if request.is_json else 'Transferencia bancaria')
    referencia = request.form.get('referencia') or (request.json.get('referencia') if request.is_json else '')
    notas = request.form.get('notas') or (request.json.get('notas') if request.is_json else '')

    try:
        monto_abono = round(float(monto_str), 2)
    except (ValueError, TypeError):
        flash('El monto del abono debe ser un nÃºmero vÃ¡lido.', 'danger')
        return redirect(url_for('facturacion'))

    if monto_abono <= 0:
        flash('El monto del abono debe ser mayor a $0.00.', 'danger')
        return redirect(url_for('facturacion'))

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Bloquear fila con FOR UPDATE para concurrencia segura
        cursor.execute('''
            SELECT f.*, c.cedula AS c_cedula, c.nombre AS c_nombre
            FROM facturacion f
            JOIN clientes c ON f.cliente_cedula = c.cedula
            WHERE f.numero = %s
            FOR UPDATE
        ''', (numero,))
        factura = cursor.fetchone()

        if not factura:
            conn.rollback()
            cursor.close()
            conn.close()
            flash(f'El documento "{numero}" no fue encontrado.', 'danger')
            return redirect(url_for('facturacion'))

        if factura['tipo'] == 'Cotizacion':
            conn.rollback()
            cursor.close()
            conn.close()
            flash('No se pueden registrar pagos sobre una cotizaciÃ³n o proforma comercial. ConviÃ©rtela o emite una factura.', 'warning')
            return redirect(url_for('facturacion'))

        total_deuda = float(factura.get('total_con_interes') or factura.get('monto') or 0.0)

        # Calcular total acumulado previo desde base de datos
        cursor.execute('SELECT COALESCE(SUM(monto), 0) AS total_pagado, COUNT(*) AS conteo FROM pagos_factura WHERE factura_numero = %s', (numero,))
        res_pagos = cursor.fetchone()
        total_pagado_previo = float(res_pagos['total_pagado'])
        if total_pagado_previo == 0 and float(factura.get('anticipo') or 0) > 0:
            total_pagado_previo = float(factura['anticipo'])

        saldo_anterior = round(total_deuda - total_pagado_previo, 2)

        # REGLA CRÃTICA C: No permitir monto_abono > saldo_pendiente (Caso de prueba 4)
        if monto_abono > saldo_anterior:
            conn.rollback()
            cursor.close()
            conn.close()
            flash(f'OperaciÃ³n rechazada: El pago ingresado (${monto_abono:.2f}) supera el saldo pendiente de ${saldo_anterior:.2f}. No se permiten sobrepagos.', 'danger')
            return redirect(url_for('facturacion'))

        saldo_posterior = max(0.0, round(saldo_anterior - monto_abono, 2))
        nuevo_total_abonado = round(total_pagado_previo + monto_abono, 2)
        numero_pago = int(res_pagos['conteo']) + 1

        # 1. Insertar pago individual en el historial (Regla 10 F)
        cursor.execute('''
            INSERT INTO pagos_factura (
                factura_numero, numero_pago, monto, fecha, metodo_pago, referencia,
                saldo_anterior, saldo_posterior, total_acumulado, registrado_por, notas
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        ''', (
            numero, numero_pago, monto_abono, fecha_pago, metodo_pago,
            referencia.strip() if referencia else None, saldo_anterior, saldo_posterior,
            nuevo_total_abonado, current_user.usuario, notas.strip() if notas else None
        ))
        pago_id = cursor.fetchone()['id']

        # 2. Generar nÃºmero Ãºnico de Comprobante de Pago (Regla 10 E)
        cursor.execute("SELECT nextval('secuencia_comprobantes') AS seq")
        seq_comp = cursor.fetchone()['seq']
        numero_comprobante = f"REC-2026-{seq_comp:04d}"

        # 3. Amortizar cuotas pendientes si existen
        cursor.execute('''
            SELECT * FROM cuotas_factura
            WHERE factura_numero = %s
            ORDER BY numero_cuota ASC
            FOR UPDATE
        ''', (numero,))
        cuotas_existentes = cursor.fetchall()

        monto_restante_pago = monto_abono
        for c in cuotas_existentes:
            if c['estado'] == 'Pagada':
                continue
            if monto_restante_pago <= 0:
                break
            saldo_c = float(c['saldo_cuota'])
            pagado_actual = float(c['monto_pagado'])
            if monto_restante_pago >= saldo_c:
                monto_restante_pago = round(monto_restante_pago - saldo_c, 2)
                cursor.execute('''
                    UPDATE cuotas_factura
                    SET monto_pagado = %s, saldo_cuota = 0, estado = 'Pagada', fecha_pago = %s
                    WHERE id = %s
                ''', (float(c['valor_cuota']), fecha_pago, c['id']))
            else:
                nuevo_saldo_c = round(saldo_c - monto_restante_pago, 2)
                nuevo_pagado_c = round(pagado_actual + monto_restante_pago, 2)
                monto_restante_pago = 0.0
                cursor.execute('''
                    UPDATE cuotas_factura
                    SET monto_pagado = %s, saldo_cuota = %s, estado = 'Parcial', fecha_pago = %s
                    WHERE id = %s
                ''', (nuevo_pagado_c, nuevo_saldo_c, fecha_pago, c['id']))

        # Obtener prÃ³xima cuota pendiente
        cursor.execute('''
            SELECT * FROM cuotas_factura
            WHERE factura_numero = %s AND estado != 'Pagada'
            ORDER BY numero_cuota ASC
            LIMIT 1
        ''', (numero,))
        prox_c = cursor.fetchone()
        proxima_cuota_num = prox_c['numero_cuota'] if prox_c else None
        proxima_cuota_fecha = prox_c['fecha_vencimiento'] if prox_c else None
        proxima_cuota_monto = float(prox_c['saldo_cuota']) if prox_c else None

        # 4. Insertar comprobante de pago
        cursor.execute('''
            INSERT INTO comprobantes_pago (
                numero_comprobante, pago_id, factura_numero, cliente_cedula, fecha,
                monto_abonado, total_deuda, total_acumulado_pagado, saldo_pendiente,
                proxima_cuota_num, proxima_cuota_fecha, proxima_cuota_monto, observaciones
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ''', (
            numero_comprobante, pago_id, numero, factura['cliente_cedula'], fecha_pago,
            monto_abono, total_deuda, nuevo_total_abonado, saldo_posterior,
            proxima_cuota_num, proxima_cuota_fecha, proxima_cuota_monto,
            notas.strip() if notas else f'Abono #{numero_pago} registrado vÃ­a {metodo_pago}'
        ))

        cursor.execute('SELECT id, nombre FROM estados_documento')
        estados_dict = {e['nombre']: e['id'] for e in cursor.fetchall()}

        # 5. REGLA CRÃTICA B: Factura final generada ÃNICAMENTE cuando saldo <= 0
        numero_factura_asignado = factura.get('numero_factura')
        if saldo_posterior <= 0:
            estado_id_nuevo = estados_dict.get('Pagada', 1)
            if not numero_factura_asignado:
                numero_factura_asignado = numero
            cursor.execute('''
                UPDATE facturacion
                SET anticipo = %s, total_abonado = %s, saldo_pendiente = 0,
                    estado_id = %s, numero_factura = %s, proxima_cuota_fecha = NULL, proxima_cuota_monto = NULL
                WHERE numero = %s
            ''', (nuevo_total_abonado, nuevo_total_abonado, estado_id_nuevo, numero_factura_asignado, numero))
        else:
            estado_id_nuevo = estados_dict.get('Parcial') or estados_dict.get('Pendiente', 2)
            cursor.execute('''
                UPDATE facturacion
                SET anticipo = %s, total_abonado = %s, saldo_pendiente = %s,
                    estado_id = %s, proxima_cuota_fecha = %s, proxima_cuota_monto = %s
                WHERE numero = %s
            ''', (nuevo_total_abonado, nuevo_total_abonado, saldo_posterior, estado_id_nuevo, proxima_cuota_fecha, proxima_cuota_monto, numero))

        conn.commit()
        cursor.close()
        conn.close()

        registrar_log(
            'REGISTRAR_ABONO',
            f"Abono #{numero_pago} de ${monto_abono:.2f} registrado en {numero}. Comprobante: {numero_comprobante}. Saldo restante: ${saldo_posterior:.2f}"
        )

        if saldo_posterior <= 0:
            flash(
                f'Â¡Abono de ${monto_abono:.2f} registrado exitosamente! Se emitiÃ³ el Comprobante de Pago "{numero_comprobante}". '
                f'La deuda ha sido liquidada al 100% y se ha generado la Factura Fiscal Oficial NÂº "{numero_factura_asignado}".',
                'success'
            )
            return redirect(url_for('ver_factura_fiscal', numero=numero))
        else:
            flash(
                f'Abono de ${monto_abono:.2f} registrado exitosamente. Se emitiÃ³ el Comprobante de Pago "{numero_comprobante}". '
                f'Saldo pendiente actual: ${saldo_posterior:.2f}. Recuerda que la factura oficial se emitirÃ¡ al completar el saldo a $0.00.',
                'info'
            )
            return redirect(url_for('ver_comprobante_pago', numero_comprobante=numero_comprobante))

    except Exception as e:
        conn.rollback()
        cursor.close()
        conn.close()
        flash(f'OcurriÃ³ un error inesperado al procesar el pago: {str(e)}', 'danger')
        return redirect(url_for('facturacion'))


@app.route('/facturacion/comprobante-pago/<numero_comprobante>')
@role_required('Administrador', 'Gestor de proyectos', 'Cliente')
@permission_required('facturas.ver_propias')
def ver_comprobante_pago(numero_comprobante):
    """
    Genera la vista imprimible del Comprobante de Pago emitido por un abono.
    Un comprobante de pago NO es una factura.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT cp.*, p.metodo_pago, p.referencia, p.notas,
               c.nombre AS cliente_nombre, c.correo AS cliente_correo,
               c.telefono AS cliente_telefono, c.ciudad AS cliente_ciudad,
               f.tipo AS doc_tipo
        FROM comprobantes_pago cp
        JOIN pagos_factura p ON cp.pago_id = p.id
        JOIN clientes c ON cp.cliente_cedula = c.cedula
        JOIN facturacion f ON cp.factura_numero = f.numero
        WHERE cp.numero_comprobante = %s
    ''', (numero_comprobante,))
    fila = cursor.fetchone()

    if not fila:
        cursor.close()
        conn.close()
        flash(f'El comprobante de pago "{numero_comprobante}" no fue encontrado.', 'danger')
        return redirect(url_for('facturacion'))

    if current_user.rol_nombre == 'Cliente':
        cliente_correo = (fila.get('cliente_correo') or '').strip().lower()
        cliente_cedula = (fila.get('cliente_cedula') or '').strip()
        usuario_actual = current_user.usuario.strip().lower()
        correo_actual = current_user.correo.strip().lower()
        if (correo_actual != cliente_correo and usuario_actual != cliente_cedula.lower()):
            cursor.close()
            conn.close()
            flash('No tienes autorizaciÃ³n para ver comprobantes de otros clientes.', 'danger')
            return redirect(url_for('facturacion'))

    cursor.close()
    conn.close()
    return render_template('comprobante_pago.html', comprobante=dict(fila))


@app.route('/facturacion/factura/<numero>')
@role_required('Administrador', 'Gestor de proyectos', 'Cliente')
@permission_required('facturas.ver_propias')
def ver_factura_fiscal(numero):
    """
    Genera la vista imprimible de la Factura Final Oficial de venta.
    REGLA CRÃTICA B Y CASO DE PRUEBA 5:
    La factura fiscal ÃNICAMENTE puede generarse o visualizarse si saldo_pendiente <= 0.
    Si existe saldo pendiente > $0.00, el backend bloquea terminantemente el acceso.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT f.*, c.nombre AS cliente_nombre, c.correo AS cliente_correo,
               c.telefono AS cliente_telefono, c.ciudad AS cliente_ciudad,
               e.nombre AS estado_nombre
        FROM facturacion f
        JOIN clientes c ON f.cliente_cedula = c.cedula
        JOIN estados_documento e ON f.estado_id = e.id
        WHERE f.numero = %s
    ''', (numero,))
    fila = cursor.fetchone()

    if not fila:
        cursor.close()
        conn.close()
        flash('El documento seleccionado no existe.', 'danger')
        return redirect(url_for('facturacion'))

    factura = dict(fila)

    # REGLA CRÃTICA B Y CASO DE PRUEBA 5: Bloqueo estricto en backend
    saldo_pendiente = float(factura.get('saldo_pendiente') or 0.0)
    if saldo_pendiente > 0:
        cursor.close()
        conn.close()
        registrar_log(
            'ACCESO_DENEGADO_FACTURA_SALDO_PENDIENTE',
            f"Intento de ver factura para {numero} con saldo pendiente de ${saldo_pendiente:.2f}"
        )
        flash(
            f'Acceso bloqueado: No se puede generar ni visualizar la Factura Fiscal Oficial porque el documento "{numero}" '
            f'tiene un saldo pendiente de ${saldo_pendiente:.2f}. '
            'Un pago parcial genera comprobante de pago, NO factura final. '
            'La factura oficial se emite Ãºnicamente cuando la deuda sea liquidada al 100% ($0.00).',
            'warning'
        )
        return redirect(url_for('facturacion'))

    if current_user.rol_nombre == 'Cliente':
        cliente_correo = (factura.get('cliente_correo') or '').strip().lower()
        cliente_cedula = (factura.get('cliente_cedula') or '').strip()
        usuario_actual = current_user.usuario.strip().lower()
        correo_actual = current_user.correo.strip().lower()
        if (correo_actual != cliente_correo and usuario_actual != cliente_cedula.lower()):
            cursor.close()
            conn.close()
            flash('No tienes autorizaciÃ³n para ver facturas de otros clientes.', 'danger')
            return redirect(url_for('facturacion'))

    cursor.execute('SELECT * FROM detalle_factura WHERE factura_numero = %s', (numero,))
    detalle = cursor.fetchall()
    factura['servicios_detalle'] = [
        {'id': d['servicio_id'], 'servicio': d['nombre_servicio'], 'cantidad': d['cantidad'],
         'precio': d['precio_base'], 'ajuste': d['ajuste'], 'total': d['total']}
        for d in detalle
    ]

    cursor.execute('''
        SELECT p.*, cp.numero_comprobante
        FROM pagos_factura p
        LEFT JOIN comprobantes_pago cp ON cp.pago_id = p.id
        WHERE p.factura_numero = %s
        ORDER BY p.numero_pago ASC
    ''', (numero,))
    factura['pagos'] = cursor.fetchall()

    cursor.close()
    conn.close()
    return render_template('comprobante_factura.html', factura=factura, numero=numero)


@app.route('/facturacion/eliminar/<numero>', methods=['POST'])
@role_required('Administrador')
@permission_required('facturas.eliminar')
def eliminar_factura(numero):
    """
    Elimina un documento comercial identificado por su nÃºmero.
    El detalle, pagos, comprobantes y cuotas asociadas se borran automÃ¡ticamente (ON DELETE CASCADE).
    Acceso exclusivo para el rol Administrador.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM facturacion WHERE numero = %s', (numero,))
    fila = cursor.fetchone()

    if fila is None:
        cursor.close()
        conn.close()
        flash('El documento seleccionado no existe.', 'danger')
        return redirect(url_for('facturacion'))

    tipo_str = "CotizaciÃ³n" if fila['tipo'] == 'Cotizacion' else "Factura"

    cursor.execute('DELETE FROM facturacion WHERE numero = %s', (numero,))
    conn.commit()
    cursor.close()
    conn.close()

    registrar_log('ELIMINAR_FACTURA', f"{tipo_str} {numero} eliminada por {current_user.usuario}")
    flash(f'{tipo_str} "{numero}" eliminada correctamente.', 'success')
    return redirect(url_for('facturacion'))


@app.route('/facturacion/comprobante/<numero>')
@role_required('Administrador', 'Gestor de proyectos', 'Cliente')
@permission_required('facturas.ver_propias')
def ver_comprobante(numero):
    """
    Ruta compatible con accesos directos previos.
    - Si es CotizaciÃ³n: la muestra.
    - Si es Factura con saldo 0: redirige a la Factura Fiscal Oficial.
    - Si es Factura con saldo > 0: redirige al Ãºltimo Comprobante de Pago emitido.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT f.*, c.nombre AS cliente_nombre, c.correo AS cliente_correo,
               c.telefono AS cliente_telefono, c.ciudad AS cliente_ciudad,
               e.nombre AS estado_nombre
        FROM facturacion f
        JOIN clientes c ON f.cliente_cedula = c.cedula
        JOIN estados_documento e ON f.estado_id = e.id
        WHERE f.numero = %s
    ''', (numero,))
    fila = cursor.fetchone()

    if fila is None:
        cursor.close()
        conn.close()
        flash('El documento seleccionado no existe.', 'danger')
        return redirect(url_for('facturacion'))

    factura = dict(fila)

    if factura['tipo'] == 'Cotizacion':
        if current_user.rol_nombre == 'Cliente':
            cliente_correo = (factura.get('cliente_correo') or '').strip().lower()
            cliente_cedula = (factura.get('cliente_cedula') or '').strip()
            usuario_actual = current_user.usuario.strip().lower()
            correo_actual = current_user.correo.strip().lower()
            if (correo_actual != cliente_correo and usuario_actual != cliente_cedula.lower()):
                cursor.close()
                conn.close()
                flash('No tienes autorizaciÃ³n para ver cotizaciones emitidas a otros clientes.', 'danger')
                return redirect(url_for('facturacion'))

        cursor.execute('SELECT * FROM detalle_factura WHERE factura_numero = %s', (numero,))
        detalle = cursor.fetchall()
        cursor.close()
        conn.close()
        factura['servicios_detalle'] = [
            {'id': d['servicio_id'], 'servicio': d['nombre_servicio'], 'cantidad': d['cantidad'],
             'precio': d['precio_base'], 'ajuste': d['ajuste'], 'total': d['total']}
            for d in detalle
        ]
        return render_template('comprobante_factura.html', factura=factura, numero=numero)

    # Es Factura / Venta
    saldo = float(factura.get('saldo_pendiente') or 0.0)
    if saldo <= 0:
        cursor.close()
        conn.close()
        return redirect(url_for('ver_factura_fiscal', numero=numero))
    else:
        cursor.execute(
            'SELECT numero_comprobante FROM comprobantes_pago WHERE factura_numero = %s ORDER BY id DESC LIMIT 1',
            (numero,)
        )
        comp = cursor.fetchone()
        cursor.close()
        conn.close()
        if comp:
            flash('Este documento tiene saldo pendiente. Mostrando el Ãºltimo comprobante de pago emitido.', 'info')
            return redirect(url_for('ver_comprobante_pago', numero_comprobante=comp['numero_comprobante']))
        else:
            flash(f'El documento {numero} tiene un saldo pendiente de ${saldo:.2f} y aÃºn no registra abonos.', 'warning')
            return redirect(url_for('facturacion'))



# ==============================================================================
# MÃDULO: PANEL DE ESTADÃSTICAS (solo lectura)
# ==============================================================================
# Panel de resultados para la toma de decisiones del negocio. Muestra quÃ©
# servicios son los mÃ¡s solicitados, usando una consulta RELACIONADA entre dos
# tablas (detalle_factura y servicios) mediante la clave forÃ¡nea servicio_id.
# Cumple el requisito de "consulta relacionada entre dos tablas con JOIN".

@app.route('/estadisticas')
@role_required('Administrador', 'Gestor de proyectos', 'Cliente')
@permission_required('reportes.ver')
def estadisticas():
    """
    Panel de resultados del negocio y ranking de demanda de servicios.
    Calcula, a partir de las facturas reales:
      - El ranking de servicios mÃ¡s solicitados (JOIN detalle_factura + servicios).
      - Totales generales (servicios vendidos e ingresos para administradores/gestores).
    Permite acceso a Administrador, Gestor de proyectos y Clientes (solo ranking de demanda).
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # Consulta relacionada (JOIN) entre detalle_factura y servicios mediante la
    # clave forÃ¡nea servicio_id. Se agrupa por servicio y se ordena del mÃ¡s
    # solicitado al menos solicitado.
    es_cliente = (current_user.rol_nombre == 'Cliente')
    if es_cliente:
        cursor.execute('''
            SELECT s.nombre AS servicio, t.nombre AS categoria
            FROM detalle_factura d
            JOIN servicios s ON d.servicio_id = s.id
            JOIN tipos_servicio t ON s.tipo_servicio_id = t.id
            GROUP BY s.nombre, t.nombre
            ORDER BY COUNT(*) DESC, s.nombre ASC
        ''')
    else:
        cursor.execute('''
            SELECT s.nombre AS servicio,
                   t.nombre AS categoria,
                   SUM(d.cantidad) AS unidades,
                   SUM(d.total) AS ingresos
            FROM detalle_factura d
            JOIN servicios s ON d.servicio_id = s.id
            JOIN tipos_servicio t ON s.tipo_servicio_id = t.id
            GROUP BY s.nombre, t.nombre
            ORDER BY unidades DESC
        ''')
    ranking = cursor.fetchall()

    if es_cliente:
        fila_totales = {'total_unidades': 0, 'total_ingresos': 0}
    else:
        cursor.execute('''
            SELECT COALESCE(SUM(cantidad), 0) AS total_unidades,
                   COALESCE(SUM(total), 0) AS total_ingresos
            FROM detalle_factura
        ''')
        fila_totales = cursor.fetchone()

    cursor.close()
    conn.close()

    # El servicio mÃ¡s solicitado es el primero del ranking (si existe).
    servicio_top = ranking[0]['servicio'] if ranking else 'Sin datos aÃºn'
    fila_mayor_ingreso = (
        max(ranking, key=lambda fila: fila['ingresos'] or 0)
        if ranking and not es_cliente else None
    )
    servicio_mayor_ingreso = fila_mayor_ingreso['servicio'] if fila_mayor_ingreso else 'Sin datos aÃºn'
    mayor_ingreso_monto = float(fila_mayor_ingreso['ingresos'] or 0.0) if fila_mayor_ingreso else 0.0

    # La unidad mÃ¡xima sirve para dibujar el ancho de las barras en la plantilla.
    max_unidades = ranking[0]['unidades'] if ranking and not es_cliente else 0
    total_ingresos_mostrar = fila_totales['total_ingresos'] if not es_cliente else 0.0

    return render_template(
        'estadisticas.html',
        ranking=ranking,
        total_unidades=fila_totales['total_unidades'],
        total_ingresos=total_ingresos_mostrar,
        servicio_top=servicio_top,
        servicio_mayor_ingreso=servicio_mayor_ingreso,
        mayor_ingreso_monto=mayor_ingreso_monto,
        max_unidades=max_unidades,
        es_cliente=es_cliente
    )


# ==============================================================================
# MANEJADORES DE ERRORES PERSONALIZADOS (404, 403, 500)
# ==============================================================================

@app.errorhandler(404)
def error_404(e):
    """Manejo elegante de rutas inexistentes o recursos no encontrados."""
    return render_template('404.html'), 404


@app.errorhandler(403)
def error_403(e):
    """Manejo de acceso denegado por falta de permisos o roles."""
    registrar_log('ERROR_403_ACCESO_PROHIBIDO', f"Ruta: {request.path}")
    return render_template('403.html'), 403


@app.errorhandler(psycopg2.Error)
def error_postgresql(e):
    """Evita mostrar un 500 genÃ©rico cuando PostgreSQL estÃ¡ temporalmente ocupado."""
    app.logger.exception('Error de PostgreSQL en %s.', request.path)
    return render_template(
        '500.html',
        codigo_http=503,
        titulo_error='Base de datos temporalmente no disponible',
        mensaje_error='La operaciÃ³n no se completÃ³. Tus datos no se guardaron o quedaron a medias; intÃ©ntalo nuevamente en unos segundos.'
    ), 503


@app.errorhandler(500)
def error_500(e):
    """Manejo de errores internos del servidor o desconexiÃ³n de base de datos."""
    registrar_log('ERROR_500_SERVIDOR', f"ExcepciÃ³n interna en {request.path}: {str(e)}")
    return render_template('500.html'), 500


@app.errorhandler(Exception)
def error_general(e):
    """
    Captura global de excepciones no controladas en producciÃ³n.
    Si estamos en modo DEBUG de desarrollo, permite la propagaciÃ³n para que Flask
    muestre el depurador detallado en consola.
    """
    if app.debug:
        raise e
    registrar_log('EXCEPCION_NO_CONTROLADA', f"Error en {request.path}: {str(e)}")
    return render_template('500.html'), 500


# ==============================================================================
# PUNTO DE ENTRADA PRINCIPAL DE LA APLICACIÃN
# ==============================================================================
if __name__ == '__main__':
    # Render proporciona el puerto mediante la variable PORT.
    app.run(
        host='0.0.0.0',
        port=int(os.getenv('PORT', '5000')),
        debug=os.getenv('FLASK_DEBUG', '').lower() == 'true'
    )
