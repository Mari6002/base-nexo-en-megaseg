-- ==============================================================================
-- PROYECTO: NEXODIGITAL - ESQUEMA DE LA BASE DE DATOS (PostgreSQL)
-- ==============================================================================
-- Este archivo permite volver a crear toda la estructura de la base de datos
-- 'nexodigital' desde cero, junto con sus datos iniciales.
--
-- Uso en pgAdmin:  crear la base 'nexodigital', abrir el Query Tool sobre ella,
--                  pegar este archivo y ejecutar (F5).
-- Uso en terminal: psql -U postgres -d nexodigital -f sql/esquema.sql
--
-- Todas las tablas tienen PRIMARY KEY y las relaciones se establecen con
-- FOREIGN KEY, garantizando la integridad referencial del modelo.
-- ==============================================================================
 
-- ============================
-- CREACIÓN DE TABLAS
-- ============================
 
CREATE TABLE tipos_negocio (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL UNIQUE
);
 
CREATE TABLE clientes (
    id SERIAL UNIQUE,
    cedula VARCHAR(20) PRIMARY KEY,
    nombre VARCHAR(150) NOT NULL,
    telefono VARCHAR(20) NOT NULL,
    correo VARCHAR(150) NOT NULL,
    tipo_negocio_id INT REFERENCES tipos_negocio(id),
    ciudad VARCHAR(100) NOT NULL
);
 
CREATE TABLE tipos_servicio (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL UNIQUE
);
 
CREATE TABLE servicios (
    id SERIAL UNIQUE PRIMARY KEY,
    tipo_servicio_id INT NOT NULL REFERENCES tipos_servicio(id),
    nombre VARCHAR(150) NOT NULL,
    precio_base NUMERIC(12,2) NOT NULL,
    imagen TEXT,
    descripcion TEXT NOT NULL,
    disponible BOOLEAN NOT NULL DEFAULT TRUE
);
 
CREATE TABLE estados_proveedor (
    id SERIAL UNIQUE PRIMARY KEY,
    nombre VARCHAR(50) NOT NULL UNIQUE
);
 
CREATE TABLE categorias_proveedor (
    id SERIAL UNIQUE PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL UNIQUE
);
 
CREATE TABLE proveedores (
    id SERIAL UNIQUE PRIMARY KEY,
    nombre VARCHAR(150) NOT NULL,
    categoria_id INT NOT NULL REFERENCES categorias_proveedor(id),
    sitio VARCHAR(150) NOT NULL,
    estado_id INT NOT NULL REFERENCES estados_proveedor(id)
);
 
CREATE TABLE estados_documento (
    id SERIAL UNIQUE PRIMARY KEY,
    nombre VARCHAR(50) NOT NULL UNIQUE
);
 
CREATE TABLE facturacion (
    id SERIAL PRIMARY KEY,
    numero VARCHAR(30) UNIQUE NOT NULL,
    tipo VARCHAR(50) NOT NULL,
    cliente_cedula VARCHAR(20) NOT NULL REFERENCES clientes(cedula) ON UPDATE CASCADE,
    fecha DATE NOT NULL,
    validez VARCHAR(50),
    subtotal NUMERIC(12,2),
    iva NUMERIC(12,2),
    monto NUMERIC(12,2) NOT NULL,
    anticipo NUMERIC(12,2) DEFAULT 0,
    saldo_pendiente NUMERIC(12,2) DEFAULT 0,
    estado_id INT NOT NULL REFERENCES estados_documento(id),
    notas TEXT,
    numero_factura VARCHAR(30) UNIQUE,
    forma_pago VARCHAR(100) DEFAULT 'Transferencia bancaria',
    tipo_pago VARCHAR(20) DEFAULT 'contado',
    plazo_meses INT DEFAULT 1,
    con_intereses BOOLEAN DEFAULT FALSE,
    tasa_interes NUMERIC(5,2) DEFAULT 0,
    monto_interes NUMERIC(12,2) DEFAULT 0,
    total_con_interes NUMERIC(12,2),
    total_abonado NUMERIC(12,2) DEFAULT 0,
    fecha_limite DATE,
    proxima_cuota_fecha DATE,
    proxima_cuota_monto NUMERIC(12,2)
);
 
CREATE TABLE detalle_factura (
    id SERIAL PRIMARY KEY,
    factura_numero VARCHAR(30) NOT NULL REFERENCES facturacion(numero) ON DELETE CASCADE ON UPDATE CASCADE,
    -- Un servicio usado en una factura/cotización no puede eliminarse.
    servicio_id INT REFERENCES servicios(id) ON DELETE RESTRICT,
    nombre_servicio VARCHAR(150) NOT NULL,
    cantidad INT NOT NULL DEFAULT 1,
    precio_base NUMERIC(12,2) NOT NULL DEFAULT 0,
    ajuste NUMERIC(12,2) NOT NULL DEFAULT 0,
    total NUMERIC(12,2) NOT NULL
);

CREATE TABLE pagos_factura (
    id SERIAL PRIMARY KEY,
    factura_numero VARCHAR(30) NOT NULL REFERENCES facturacion(numero) ON DELETE CASCADE ON UPDATE CASCADE,
    numero_pago INT NOT NULL,
    monto NUMERIC(12,2) NOT NULL CHECK (monto > 0),
    fecha DATE NOT NULL,
    metodo_pago VARCHAR(100) NOT NULL DEFAULT 'Transferencia bancaria',
    referencia VARCHAR(100),
    saldo_anterior NUMERIC(12,2) NOT NULL DEFAULT 0,
    saldo_posterior NUMERIC(12,2) NOT NULL DEFAULT 0,
    total_acumulado NUMERIC(12,2) NOT NULL DEFAULT 0,
    registrado_por VARCHAR(100),
    notas TEXT,
    fecha_registro TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE SEQUENCE IF NOT EXISTS secuencia_comprobantes START WITH 1 INCREMENT BY 1;

CREATE TABLE comprobantes_pago (
    id SERIAL PRIMARY KEY,
    numero_comprobante VARCHAR(40) UNIQUE NOT NULL,
    pago_id INT NOT NULL REFERENCES pagos_factura(id) ON DELETE CASCADE,
    factura_numero VARCHAR(30) NOT NULL REFERENCES facturacion(numero) ON DELETE CASCADE ON UPDATE CASCADE,
    cliente_cedula VARCHAR(20) NOT NULL REFERENCES clientes(cedula) ON UPDATE CASCADE,
    fecha DATE NOT NULL,
    monto_abonado NUMERIC(12,2) NOT NULL,
    total_deuda NUMERIC(12,2) NOT NULL,
    total_acumulado_pagado NUMERIC(12,2) NOT NULL,
    saldo_pendiente NUMERIC(12,2) NOT NULL,
    proxima_cuota_num INT,
    proxima_cuota_fecha DATE,
    proxima_cuota_monto NUMERIC(12,2),
    observaciones TEXT,
    fecha_emision TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE cuotas_factura (
    id SERIAL PRIMARY KEY,
    factura_numero VARCHAR(30) NOT NULL REFERENCES facturacion(numero) ON DELETE CASCADE ON UPDATE CASCADE,
    numero_cuota INT NOT NULL,
    valor_cuota NUMERIC(12,2) NOT NULL,
    fecha_vencimiento DATE NOT NULL,
    monto_pagado NUMERIC(12,2) NOT NULL DEFAULT 0,
    saldo_cuota NUMERIC(12,2) NOT NULL,
    estado VARCHAR(30) NOT NULL DEFAULT 'Pendiente',
    fecha_pago DATE,
    CONSTRAINT uq_cuota_factura UNIQUE (factura_numero, numero_cuota)
);

CREATE TABLE roles (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(50) UNIQUE NOT NULL,
    descripcion TEXT
);

CREATE TABLE permisos (
    id SERIAL PRIMARY KEY,
    codigo VARCHAR(50) UNIQUE NOT NULL,
    descripcion TEXT
);

CREATE TABLE rol_permisos (
    rol_id INT NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    permiso_id INT NOT NULL REFERENCES permisos(id) ON DELETE CASCADE,
    PRIMARY KEY (rol_id, permiso_id)
);

CREATE TABLE usuarios (
    id SERIAL PRIMARY KEY,
    usuario VARCHAR(50) UNIQUE NOT NULL,
    correo VARCHAR(150) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    rol_id INT NOT NULL REFERENCES roles(id),
    nombres VARCHAR(100),
    apellidos VARCHAR(100),
    telefono VARCHAR(30) UNIQUE,
    fecha_nacimiento DATE,
    es_mayor_edad BOOLEAN NOT NULL DEFAULT FALSE,
    acepta_terminos BOOLEAN NOT NULL DEFAULT FALSE,
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    email_confirmado BOOLEAN NOT NULL DEFAULT FALSE,
    aprobado BOOLEAN NOT NULL DEFAULT TRUE,
    dos_factores_activo BOOLEAN NOT NULL DEFAULT TRUE,
    dos_factores_codigo VARCHAR(10),
    fecha_registro TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE logs_actividad (
    id SERIAL PRIMARY KEY,
    usuario_id INT REFERENCES usuarios(id) ON DELETE SET NULL,
    usuario_nombre VARCHAR(50),
    accion VARCHAR(100) NOT NULL,
    ip VARCHAR(50),
    fecha TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    detalles TEXT
);

CREATE TABLE solicitudes (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(150) NOT NULL,
    correo VARCHAR(150) NOT NULL,
    telefono VARCHAR(30),
    tipo_servicio VARCHAR(100),
    mensaje TEXT NOT NULL,
    fecha TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    estado VARCHAR(30) NOT NULL DEFAULT 'Pendiente',
    responsable_id INT REFERENCES usuarios(id) ON DELETE SET NULL,
    respuesta_cliente TEXT,
    trabajo_realizado TEXT,
    evidencia_url TEXT,
    resuelto_por_id INT REFERENCES usuarios(id) ON DELETE SET NULL,
    fecha_resolucion TIMESTAMP
);

-- ==============================================================================
-- SECUENCIAS Y TRIGGERS PARA AUTOGENERACIÓN SECUENCIAL ATÓMICA EN PRODUCCIÓN
-- ==============================================================================
CREATE SEQUENCE IF NOT EXISTS secuencia_facturas START WITH 1 INCREMENT BY 1;
CREATE SEQUENCE IF NOT EXISTS secuencia_cotizaciones START WITH 1 INCREMENT BY 1;

CREATE OR REPLACE FUNCTION fn_autogenerar_numero_factura()
RETURNS TRIGGER AS $$
DECLARE
    nuevo_correlativo BIGINT;
    val_extraido BIGINT;
BEGIN
    -- Si el número no fue especificado o se envía vacío, autogenerarlo de forma secuencial y atómica
    IF NEW.numero IS NULL OR TRIM(NEW.numero) = '' THEN
        IF NEW.tipo = 'Cotizacion' THEN
            nuevo_correlativo := nextval('secuencia_cotizaciones');
            NEW.numero := 'COT-2026-' || LPAD(nuevo_correlativo::TEXT, 4, '0');
        ELSE
            nuevo_correlativo := nextval('secuencia_facturas');
            NEW.numero := '001-001-' || LPAD(nuevo_correlativo::TEXT, 4, '0');
        END IF;
    ELSE
        -- Si se proporciona un número explícito, sincronizar la secuencia hacia adelante si aplica
        BEGIN
            IF NEW.tipo = 'Cotizacion' AND NEW.numero LIKE 'COT-2026-%' THEN
                val_extraido := substring(NEW.numero from '[0-9]+$')::BIGINT;
                IF val_extraido >= currval('secuencia_cotizaciones') THEN
                    PERFORM setval('secuencia_cotizaciones', val_extraido, true);
                END IF;
            ELSIF NEW.tipo = 'Factura' AND NEW.numero LIKE '001-001-%' THEN
                val_extraido := substring(NEW.numero from '[0-9]+$')::BIGINT;
                IF val_extraido >= currval('secuencia_facturas') THEN
                    PERFORM setval('secuencia_facturas', val_extraido, true);
                END IF;
            END IF;
        EXCEPTION WHEN OTHERS THEN
            NULL;
        END;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_autogenerar_numero ON facturacion;
CREATE TRIGGER trg_autogenerar_numero
BEFORE INSERT ON facturacion
FOR EACH ROW
EXECUTE FUNCTION fn_autogenerar_numero_factura();

 
-- ============================
-- DATOS INICIALES
-- ============================
 
INSERT INTO tipos_negocio (nombre) VALUES
('Panadería'), ('Tienda de Ropa'), ('Taller Automotriz'), ('Cafetería');
 
INSERT INTO clientes (cedula, nombre, telefono, correo, tipo_negocio_id, ciudad) VALUES
('1700111222', 'Panadería El Trigal', '0991234567', 'trigal@correo.com', 1, 'Santo Domingo'),
('1700333444', 'Boutique Bella', '0987654321', 'bella@correo.com', 2, 'Quito'),
('1700555666', 'Taller Mecánico RPM', '0976543210', 'rpm@correo.com', 3, 'Santo Domingo'),
('1700777888', 'Café Aroma Amazónico', '0965432109', 'aroma@correo.com', 4, 'Puyo');
 
INSERT INTO tipos_servicio (nombre) VALUES
('Desarrollo Web'), ('Marketing Digital'), ('Diseño y Catálogos'), ('Soporte y Asesoría');
 
INSERT INTO servicios (tipo_servicio_id, nombre, precio_base, imagen, descripcion, disponible) VALUES
(1, 'Páginas Web para Negocios', 250.00, 'https://images.unsplash.com/photo-1547658719-da2b51169166', 'Diseño de sitios web claros, rápidos y adaptados para celulares y computadoras.', TRUE),
(3, 'Catálogo Digital de Productos', 120.00, 'https://images.unsplash.com/photo-1460925895917-afdab827c52f', 'Muestra tus productos con fotos, precios y botón para hacer pedidos por WhatsApp.', TRUE),
(3, 'Menú Digital con Código QR', 65.00, 'https://images.unsplash.com/photo-1595079672139-5470887216e9', 'Menú interactivo para restaurantes y cafeterías accesible escaneando un código QR.', TRUE),
(1, 'Formularios de Contacto y Pedidos', 85.00, 'https://images.unsplash.com/photo-1551288049-bebda4e38f71', 'Formularios personalizados para recibir solicitudes, cotizaciones y reservas.', TRUE),
(2, 'Botón de WhatsApp y Redes Sociales', 45.00, 'https://images.unsplash.com/photo-1611746872915-64382b5c76da', 'Integración de enlaces directos a WhatsApp, Instagram, Facebook y TikTok.', TRUE),
(4, 'Asesoría y Optimización Web', 110.00, 'https://images.unsplash.com/photo-1507238691740-187a5b1d37b8', 'Revisión técnica de páginas web para mejorar su velocidad y accesibilidad.', FALSE);
 
INSERT INTO estados_proveedor (nombre) VALUES
('Activo'), ('Pendiente'), ('Inactivo');
 
INSERT INTO categorias_proveedor (nombre) VALUES
('Servidor y Hosting'), ('Registro de Dominios'), ('Diseño de Interfaces'), ('Certificados SSL y Seguridad');
 
INSERT INTO proveedores (nombre, categoria_id, sitio, estado_id) VALUES
('Hostinger', 1, 'hostinger.com', 1),
('GoDaddy', 2, 'godaddy.com', 1),
('Figma', 3, 'figma.com', 1),
('Cloudflare', 4, 'cloudflare.com', 2);
 
INSERT INTO estados_documento (nombre) VALUES
('Pagada'), ('Pendiente'), ('Parcial'), ('Aprobada'), ('En revision'), ('Vencida');

-- ============================
-- ROLES Y PERMISOS (RBAC)
-- ============================

INSERT INTO roles (nombre, descripcion) VALUES
('Administrador', 'Acceso total a usuarios, proyectos, servicios y configuración.'),
('Gestor de proyectos', 'Acceso a proyectos, facturación, cotizaciones y reportes.'),
('Soporte técnico', 'Acceso a tickets, soporte e infraestructura, sin ver datos sensibles de clientes.'),
('Usuario interno', 'Acceso únicamente a tareas asignadas y catálogo de servicios.'),
('Cliente', 'Acceso a sus propios proyectos, cotizaciones y servicios contratados.');

INSERT INTO permisos (codigo, descripcion) VALUES
('servicios.ver', 'Visualización pública y privada de servicios disponibles'),
('servicios.crear', 'Creación y registro de nuevos servicios en el catálogo'),
('servicios.editar', 'Modificación de precios y descripción de servicios'),
('servicios.eliminar', 'Eliminación de servicios del catálogo'),
('servicios.futuros', 'Visualización de servicios próximos y en desarrollo (exclusivo para usuarios autenticados)'),
('clientes.ver', 'Visualización del listado general de clientes'),
('clientes.crear', 'Registro de nuevos clientes comerciales'),
('clientes.editar', 'Actualización de datos comerciales de clientes'),
('clientes.eliminar', 'Eliminación de clientes sin historial'),
('clientes.sensible', 'Acceso a datos confidenciales y de contacto de clientes'),
('clientes.propio', 'Acceso exclusivo a la información y ficha propia del cliente'),
('facturas.ver', 'Visualización general de facturas y cotizaciones de la empresa'),
('facturas.crear', 'Emisión de nuevas facturas de venta y cotizaciones'),
('facturas.editar', 'Modificación de facturas y cotizaciones emitidas'),
('facturas.eliminar', 'Anulación y eliminación de facturas'),
('facturas.ver_propias', 'Visualización exclusiva de comprobantes emitidos para el cliente'),
('proveedores.ver', 'Visualización del directorio de proveedores tecnológicos'),
('proveedores.crear', 'Alta de nuevos proveedores e infraestructura'),
('proveedores.editar', 'Modificación de proveedores y estados operativos'),
('proveedores.eliminar', 'Eliminación de proveedores'),
('usuarios.ver', 'Visualización de lista de usuarios del sistema'),
('usuarios.crear', 'Alta directa de cuentas de usuario'),
('usuarios.editar', 'Modificación y asignación de roles de usuario'),
('usuarios.eliminar', 'Eliminación o baja de cuentas de usuario'),
('usuarios.aprobar', 'Aprobación de solicitudes de Administrador y activación'),
('reportes.ver', 'Visualización de estadísticas y ranking de demanda de servicios'),
('reportes.financiero', 'Visualización de métricas de ingresos, saldos y balances financieros')
ON CONFLICT (codigo) DO UPDATE SET descripcion = EXCLUDED.descripcion;

-- ============================
-- ASIGNACIÓN GRANULAR DE PERMISOS A ROLES (rol_permisos)
-- ============================
INSERT INTO rol_permisos (rol_id, permiso_id)
SELECT r.id, p.id
FROM (VALUES
    -- Administrador: Acceso total y permisos completos
    ('Administrador', 'servicios.ver'), ('Administrador', 'servicios.crear'), ('Administrador', 'servicios.editar'), ('Administrador', 'servicios.eliminar'), ('Administrador', 'servicios.futuros'),
    ('Administrador', 'clientes.ver'), ('Administrador', 'clientes.crear'), ('Administrador', 'clientes.editar'), ('Administrador', 'clientes.eliminar'), ('Administrador', 'clientes.sensible'), ('Administrador', 'clientes.propio'),
    ('Administrador', 'facturas.ver'), ('Administrador', 'facturas.crear'), ('Administrador', 'facturas.editar'), ('Administrador', 'facturas.eliminar'), ('Administrador', 'facturas.ver_propias'),
    ('Administrador', 'proveedores.ver'), ('Administrador', 'proveedores.crear'), ('Administrador', 'proveedores.editar'), ('Administrador', 'proveedores.eliminar'),
    ('Administrador', 'usuarios.ver'), ('Administrador', 'usuarios.crear'), ('Administrador', 'usuarios.editar'), ('Administrador', 'usuarios.eliminar'), ('Administrador', 'usuarios.aprobar'),
    ('Administrador', 'reportes.ver'), ('Administrador', 'reportes.financiero'),
    -- Gestor de proyectos: Proyectos, clientes, facturación y reportes (sin usuarios ni proveedores)
    ('Gestor de proyectos', 'servicios.ver'), ('Gestor de proyectos', 'servicios.crear'), ('Gestor de proyectos', 'servicios.editar'), ('Gestor de proyectos', 'servicios.futuros'),
    ('Gestor de proyectos', 'clientes.ver'), ('Gestor de proyectos', 'clientes.crear'), ('Gestor de proyectos', 'clientes.editar'), ('Gestor de proyectos', 'clientes.sensible'),
    ('Gestor de proyectos', 'facturas.ver'), ('Gestor de proyectos', 'facturas.crear'), ('Gestor de proyectos', 'facturas.editar'), ('Gestor de proyectos', 'facturas.eliminar'),
    ('Gestor de proyectos', 'reportes.ver'), ('Gestor de proyectos', 'reportes.financiero'),
    -- Soporte técnico: Infraestructura y proveedores (sin ver datos sensibles ni facturación de clientes)
    ('Soporte técnico', 'servicios.ver'), ('Soporte técnico', 'servicios.editar'), ('Soporte técnico', 'servicios.futuros'),
    ('Soporte técnico', 'proveedores.ver'), ('Soporte técnico', 'proveedores.crear'), ('Soporte técnico', 'proveedores.editar'),
    -- Usuario interno: Tareas asignadas y catálogo
    ('Usuario interno', 'servicios.ver'), ('Usuario interno', 'servicios.futuros'),
    ('Usuario interno', 'clientes.ver'),
    -- Cliente: Servicios, servicios futuros, ranking y facturas propias (sin crear facturas ni ver proveedores)
    ('Cliente', 'servicios.ver'), ('Cliente', 'servicios.futuros'),
    ('Cliente', 'clientes.propio'),
    ('Cliente', 'facturas.ver_propias'),
    ('Cliente', 'reportes.ver')
) AS m(rol_nombre, permiso_codigo)
JOIN roles r ON r.nombre = m.rol_nombre
JOIN permisos p ON p.codigo = m.permiso_codigo
ON CONFLICT DO NOTHING;

-- ==============================================================================
-- SINCRONIZACIÓN AUTOMÁTICA DE SECUENCIAS PARA PRODUCCIÓN (SETVAL)
-- ==============================================================================
-- Garantiza que el contador de cada secuencia esté perfectamente alineado con el MAX(id)
-- de cada tabla, evitando errores de 'duplicate key value violates unique constraint'.
DO $$
DECLARE
    r RECORD;
    seq_name TEXT;
    max_id BIGINT;
BEGIN
    FOR r IN (
        SELECT table_name, column_name
        FROM information_schema.columns
        WHERE table_schema = 'public' AND column_default LIKE 'nextval%'
    ) LOOP
        seq_name := pg_get_serial_sequence(r.table_name, r.column_name);
        IF seq_name IS NOT NULL THEN
            EXECUTE format('SELECT COALESCE(MAX(%I), 0) FROM %I', r.column_name, r.table_name) INTO max_id;
            IF max_id > 0 THEN
                EXECUTE format('SELECT setval(%L, %s, true)', seq_name, max_id);
            ELSE
                EXECUTE format('SELECT setval(%L, 1, false)', seq_name);
            END IF;
        END IF;
    END LOOP;
END $$;
