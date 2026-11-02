# ==============================================================================
# PROYECTO: NEXODIGITAL - MODELOS DE BASE DE DATOS Y AUTENTICACIÓN (RBAC)
# ==============================================================================
# Este archivo define la estructura de datos ORM (SQLAlchemy) y la clase de
# usuario para Flask-Login con soporte integral para:
# 1. Roles definidos: Administrador, Gestor de proyectos, Soporte técnico,
#    Usuario interno y Cliente.
# 2. Permisos granulares y control de acceso.
# 3. Verificación de contraseñas con Bcrypt (con compatibilidad retroactiva).
# 4. Estado de aprobación para Administradores y confirmación de correo.
# 5. Registro y auditoría de actividad (logs_actividad).
# ==============================================================================

import bcrypt
from datetime import datetime
from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash as werkzeug_check_hash

# Instancia central de SQLAlchemy para la aplicación Flask
db = SQLAlchemy()


def normalizar_nombre_rol(nombre):
    """Mantiene un único nombre visible y funcional para el rol administrador."""
    nombre_limpio = (nombre or '').strip()
    if nombre_limpio.casefold() in {'admin', 'administrador'}:
        return 'Administrador'
    return nombre_limpio


# ==============================================================================
# MODELO: ROLES DEL SISTEMA
# ==============================================================================
class Role(db.Model):
    """
    Representa un rol dentro del sistema de control de acceso RBAC.
    """
    __tablename__ = 'roles'

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50), unique=True, nullable=False)
    descripcion = db.Column(db.Text, nullable=True)

    # Relación inversa con usuarios
    usuarios = db.relationship('User', backref='rol_obj', lazy=True)

    @staticmethod
    def get_all():
        from conexion.conexion import get_db_connection
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT *
            FROM roles
            ORDER BY
                CASE
                    WHEN LOWER(TRIM(nombre)) = 'administrador' THEN 0
                    WHEN LOWER(TRIM(nombre)) = 'admin' THEN 1
                    ELSE 2
                END,
                id
        ''')
        roles = []
        nombres_vistos = set()
        for fila in cursor.fetchall():
            rol = dict(fila)
            rol['nombre'] = normalizar_nombre_rol(rol.get('nombre'))
            clave = rol['nombre'].casefold()
            if clave not in nombres_vistos:
                roles.append(rol)
                nombres_vistos.add(clave)
        cursor.close()
        conn.close()
        return roles

    @staticmethod
    def get_by_id(rol_id):
        from conexion.conexion import get_db_connection
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM roles WHERE id = %s', (rol_id,))
        rol = cursor.fetchone()
        cursor.close()
        conn.close()
        if rol:
            rol = dict(rol)
            rol['nombre'] = normalizar_nombre_rol(rol.get('nombre'))
        return rol


# ==============================================================================
# MODELO: PERMISOS DEL SISTEMA
# ==============================================================================
class Permission(db.Model):
    """
    Define permisos específicos para acciones granulares en el sistema.
    """
    __tablename__ = 'permisos'

    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(50), unique=True, nullable=False)
    descripcion = db.Column(db.Text, nullable=True)


# ==============================================================================
# MODELO: LOGS DE AUDITORÍA Y ACTIVIDAD
# ==============================================================================
class ActivityLog(db.Model):
    """
    Registro histórico de auditoría de acciones realizadas en el sistema.
    """
    __tablename__ = 'logs_actividad'

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=True)
    usuario_nombre = db.Column(db.String(50), nullable=True)
    accion = db.Column(db.String(100), nullable=False)
    ip = db.Column(db.String(50), nullable=True)
    fecha = db.Column(db.DateTime, default=datetime.utcnow)
    detalles = db.Column(db.Text, nullable=True)

    @staticmethod
    def registrar(usuario_id, usuario_nombre, accion, ip=None, detalles=None):
        from conexion.conexion import get_db_connection
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO logs_actividad (usuario_id, usuario_nombre, accion, ip, detalles)
            VALUES (%s, %s, %s, %s, %s)
        ''', (usuario_id, usuario_nombre, accion, ip, detalles))
        conn.commit()
        cursor.close()
        conn.close()

    @staticmethod
    def get_recientes(limit=50):
        from conexion.conexion import get_db_connection
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT l.*, r.nombre AS rol_nombre
            FROM logs_actividad l
            LEFT JOIN usuarios u ON l.usuario_id = u.id
            LEFT JOIN roles r ON u.rol_id = r.id
            ORDER BY l.fecha DESC
            LIMIT %s
        ''', (limit,))
        logs = cursor.fetchall()
        cursor.close()
        conn.close()
        return logs

    @staticmethod
    def buscar(fecha_desde=None, fecha_hasta=None, hora_desde=None,
               hora_hasta=None, persona=None, accion=None, ip=None,
               detalles=None, limit=500):
        """Busca auditoría con filtros aplicados en PostgreSQL."""
        from conexion.conexion import get_db_connection
        conn = get_db_connection()
        cursor = conn.cursor()
        condiciones = []
        parametros = []
        if fecha_desde:
            condiciones.append('l.fecha >= %s::date')
            parametros.append(fecha_desde)
        if fecha_hasta:
            condiciones.append("l.fecha < (%s::date + INTERVAL '1 day')")
            parametros.append(fecha_hasta)
        if hora_desde:
            condiciones.append('l.fecha::time >= %s::time')
            parametros.append(hora_desde)
        if hora_hasta:
            condiciones.append('l.fecha::time <= %s::time')
            parametros.append(hora_hasta)
        for columna, valor in (
            ('l.usuario_nombre', persona),
            ('l.ip', ip),
            ('l.detalles', detalles),
        ):
            if valor:
                condiciones.append(f'COALESCE({columna}, \'\') ILIKE %s')
                parametros.append(f'%{valor}%')
        if accion:
            condiciones.append('l.accion = %s')
            parametros.append(accion)

        where = f"WHERE {' AND '.join(condiciones)}" if condiciones else ''
        parametros.append(limit)
        cursor.execute(f'''
            SELECT l.*, r.nombre AS rol_nombre
            FROM logs_actividad l
            LEFT JOIN usuarios u ON l.usuario_id = u.id
            LEFT JOIN roles r ON u.rol_id = r.id
            {where}
            ORDER BY l.fecha DESC, l.id DESC
            LIMIT %s
        ''', parametros)
        logs = cursor.fetchall()
        cursor.close()
        conn.close()
        return logs

    @staticmethod
    def acciones_disponibles():
        """Obtiene las acciones existentes para el selector de auditoría."""
        from conexion.conexion import get_db_connection
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT DISTINCT accion
            FROM logs_actividad
            WHERE accion IS NOT NULL AND TRIM(accion) <> ''
            ORDER BY accion
        ''')
        acciones = [row['accion'] for row in cursor.fetchall()]
        cursor.close()
        conn.close()
        return acciones


# ==============================================================================
# MODELO Y CLASE DE USUARIO (UserMixin para Flask-Login)
# ==============================================================================
class User(UserMixin, db.Model):
    """
    Representa un usuario del sistema en la base de datos PostgreSQL.
    Incluye campos de auditoría, control de roles (RBAC), verificación
    de correo, aprobación administrativa y 2FA.
    """
    __tablename__ = 'usuarios'

    id = db.Column(db.Integer, primary_key=True)
    usuario = db.Column(db.String(50), unique=True, nullable=False)
    correo = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    rol_id = db.Column(db.Integer, db.ForeignKey('roles.id'), nullable=False)
    activo = db.Column(db.Boolean, default=True, nullable=False)
    email_confirmado = db.Column(db.Boolean, default=False, nullable=False)
    aprobado = db.Column(db.Boolean, default=True, nullable=False)
    dos_factores_activo = db.Column(db.Boolean, default=False, nullable=False)
    dos_factores_codigo = db.Column(db.String(10), nullable=True)
    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow)

    def __init__(self, id, usuario, correo, password, rol_id, rol_nombre=None,
                 activo=True, email_confirmado=False, aprobado=True,
                 dos_factores_activo=False, dos_factores_codigo=None):
        self.id = id
        self.usuario = usuario
        self.correo = correo
        self.password = password
        self.rol_id = rol_id
        self.rol_nombre = rol_nombre or 'Cliente'
        self.activo = activo
        self.email_confirmado = email_confirmado
        self.aprobado = aprobado
        self.dos_factores_activo = dos_factores_activo
        self.dos_factores_codigo = dos_factores_codigo

    @property
    def is_active(self):
        """Retorna si el usuario está activo y habilitado para autenticarse."""
        return self.activo

    def has_role(self, *role_names):
        """Verifica si el usuario posee alguno de los roles solicitados."""
        return self.rol_nombre in role_names

    def is_admin(self):
        """Atajo para comprobar si el usuario es Administrador."""
        return self.rol_nombre == 'Administrador'

    def is_approved(self):
        """Verifica si un usuario con rol Administrador ya fue aprobado."""
        if self.rol_nombre == 'Administrador':
            return self.aprobado
        return True

    def has_permission(self, codigo_permiso):
        """
        Verifica en la tabla rol_permisos si el rol del usuario posee un permiso específico.
        Permite control granular de permisos (RBAC).
        """
        if self.is_admin():
            return True
        from conexion.conexion import get_db_connection
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('''
            SELECT 1 FROM rol_permisos rp
            JOIN permisos p ON rp.permiso_id = p.id
            WHERE rp.rol_id = %s AND p.codigo = %s
        ''', (self.rol_id, codigo_permiso))
        tiene = cur.fetchone() is not None
        cur.close()
        conn.close()
        return tiene

    def get_permissions(self):
        """Retorna la lista de permisos asignados al rol del usuario."""
        from conexion.conexion import get_db_connection
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('''
            SELECT p.codigo, p.descripcion
            FROM rol_permisos rp
            JOIN permisos p ON rp.permiso_id = p.id
            WHERE rp.rol_id = %s
            ORDER BY p.codigo
        ''', (self.rol_id,))
        permisos = cur.fetchall()
        cur.close()
        conn.close()
        return permisos


    def check_password(self, plain_password):
        """
        Verifica la contraseña ingresada contra el hash almacenado.
        Soporta tanto Bcrypt ($2b$) como hashes de Werkzeug (scrypt/pbkdf2)
        para garantizar retrocompatibilidad total.
        """
        try:
            stored_hash = (self.password or '').strip()
            if stored_hash.startswith(('$2a$', '$2b$', '$2y$')):
                # bcrypt usa el mismo formato para $2a$, $2b$ y $2y$.
                # La librería Python acepta $2a$/$2b$, por eso se normaliza
                # solo el prefijo compatible sin cambiar la contraseña.
                if stored_hash.startswith('$2y$'):
                    stored_hash = '$2b$' + stored_hash[4:]
                return bcrypt.checkpw(
                    plain_password.encode('utf-8'),
                    stored_hash.encode('utf-8')
                )
            return werkzeug_check_hash(stored_hash, plain_password)
        except (TypeError, ValueError):
            return False

    @staticmethod
    def hash_password(plain_password):
        """Genera un hash seguro utilizando Bcrypt."""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(plain_password.encode('utf-8'), salt).decode('utf-8')

    @classmethod
    def _from_row(cls, row):
        """Crea una instancia de User a partir de un diccionario de PostgreSQL."""
        if not row:
            return None
        return cls(
            id=row['id'],
            usuario=row['usuario'],
            correo=row.get('correo', f"{row['usuario']}@nexodigital.ec"),
            password=row['password'],
            rol_id=row.get('rol_id', 1),
            rol_nombre=normalizar_nombre_rol(row.get('rol_nombre', 'Administrador')),
            activo=row.get('activo', True),
            email_confirmado=row.get('email_confirmado', True),
            aprobado=row.get('aprobado', True),
            dos_factores_activo=row.get('dos_factores_activo', False),
            dos_factores_codigo=row.get('dos_factores_codigo', None)
        )

    @staticmethod
    def get_by_id(user_id):
        """Recupera un usuario por su identificador primario (ID) con JOIN a roles."""
        from conexion.conexion import get_db_connection
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT u.*, r.nombre AS rol_nombre
            FROM usuarios u
            LEFT JOIN roles r ON u.rol_id = r.id
            WHERE u.id = %s
        ''', (user_id,))
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        return User._from_row(row)

    @staticmethod
    def get_by_usuario(username):
        """Recupera un usuario por su nombre de usuario."""
        from conexion.conexion import get_db_connection
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT u.*, r.nombre AS rol_nombre
            FROM usuarios u
            LEFT JOIN roles r ON u.rol_id = r.id
            WHERE LOWER(TRIM(u.usuario)) = LOWER(TRIM(%s))
        ''', (username,))
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        return User._from_row(row)

    @staticmethod
    def get_by_correo(email):
        """Recupera un usuario por su dirección de correo electrónico."""
        from conexion.conexion import get_db_connection
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT u.*, r.nombre AS rol_nombre
            FROM usuarios u
            LEFT JOIN roles r ON u.rol_id = r.id
            WHERE LOWER(TRIM(u.correo)) = LOWER(TRIM(%s))
        ''', (email,))
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        return User._from_row(row)

    @staticmethod
    def get_by_usuario_o_correo(identificador):
        """Busca indistintamente por nombre de usuario o por correo electrónico."""
        from conexion.conexion import get_db_connection
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT u.*, r.nombre AS rol_nombre
            FROM usuarios u
            LEFT JOIN roles r ON u.rol_id = r.id
            WHERE LOWER(TRIM(u.usuario)) = LOWER(TRIM(%s))
               OR LOWER(TRIM(u.correo)) = LOWER(TRIM(%s))
        ''', (identificador, identificador))
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        return User._from_row(row)

    @staticmethod
    def get_all():
        """Obtiene la lista de todos los usuarios con su rol correspondiente."""
        from conexion.conexion import get_db_connection
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT u.id, u.usuario, u.correo, u.rol_id, r.nombre AS rol_nombre,
                   u.activo, u.email_confirmado, u.aprobado, u.dos_factores_activo, u.fecha_registro
            FROM usuarios u
            LEFT JOIN roles r ON u.rol_id = r.id
            ORDER BY u.id ASC
        ''')
        rows = []
        for fila in cursor.fetchall():
            usuario = dict(fila)
            usuario['rol_nombre'] = normalizar_nombre_rol(usuario.get('rol_nombre'))
            rows.append(usuario)
        cursor.close()
        conn.close()
        return rows


# Alias para mantener compatibilidad total con código previo que importe Usuario
Usuario = User
