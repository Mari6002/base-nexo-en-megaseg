-- Sincronización segura de la base de datos de Render con NexoDigital local.
-- No borra tablas, usuarios, facturas ni contraseñas existentes.
-- Ejecutar completo en la base PostgreSQL de Render.

BEGIN;
SET client_encoding = 'UTF8';

-- Activa el segundo factor para las cuentas existentes. Las cuentas nuevas
-- ya se registran con dos_factores_activo = TRUE desde la aplicación.
UPDATE usuarios
SET dos_factores_activo = TRUE,
    dos_factores_codigo = NULL;

-- Las cuentas operativas no necesitan aprobación manual. Se mantiene la
-- aprobación para las cuentas con privilegios de Administrador.
UPDATE usuarios u
SET aprobado = TRUE
FROM roles r
WHERE u.rol_id = r.id
  AND r.nombre <> 'Administrador'
  AND u.activo = TRUE;

-- Estructura agregada después de la primera versión del esquema.
ALTER TABLE solicitudes
    ADD COLUMN IF NOT EXISTS estado VARCHAR(30) NOT NULL DEFAULT 'Pendiente',
    ADD COLUMN IF NOT EXISTS responsable_id INT REFERENCES usuarios(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS respuesta_cliente TEXT,
    ADD COLUMN IF NOT EXISTS trabajo_realizado TEXT,
    ADD COLUMN IF NOT EXISTS evidencia_url TEXT;
ALTER TABLE solicitudes
    ADD COLUMN IF NOT EXISTS resuelto_por_id INT REFERENCES usuarios(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS fecha_resolucion TIMESTAMP;

-- Conserva el significado de estados usados por versiones anteriores.
UPDATE solicitudes
SET estado = 'Resuelta'
WHERE estado = 'Finalizada';
UPDATE solicitudes
SET estado = 'Descartada'
WHERE estado = 'Cancelada';

CREATE INDEX IF NOT EXISTS idx_solicitudes_estado
    ON solicitudes (estado);
CREATE INDEX IF NOT EXISTS idx_solicitudes_responsable
    ON solicitudes (responsable_id);
CREATE INDEX IF NOT EXISTS idx_solicitudes_finalizadas
    ON solicitudes (estado, responsable_id);
CREATE INDEX IF NOT EXISTS idx_solicitudes_resuelto_por
    ON solicitudes (resuelto_por_id);

-- Permiso que permite a Soporte técnico editar el catálogo, sin permitirle
-- borrar servicios ni acceder a la administración de usuarios.
INSERT INTO permisos (codigo, descripcion)
VALUES ('servicios.editar', 'Modificación de precios y descripción de servicios')
ON CONFLICT (codigo) DO UPDATE
SET descripcion = EXCLUDED.descripcion;

INSERT INTO rol_permisos (rol_id, permiso_id)
SELECT r.id, p.id
FROM roles r
JOIN permisos p ON p.codigo = 'servicios.editar'
WHERE r.nombre = 'Soporte técnico'
ON CONFLICT DO NOTHING;

-- El Usuario interno no tiene acceso a la facturación completa.
DELETE FROM rol_permisos rp
USING roles r, permisos p
WHERE rp.rol_id = r.id
  AND rp.permiso_id = p.id
  AND r.nombre = 'Usuario interno'
  AND p.codigo IN ('facturas.ver', 'facturas.crear', 'facturas.editar', 'facturas.eliminar');

-- Catálogo igual al catálogo local. Solo actualiza los seis servicios base;
-- no elimina servicios personalizados agregados en Render.
UPDATE servicios
SET precio_base = datos.precio,
    nombre = datos.nombre,
    descripcion = datos.descripcion
FROM (VALUES
    (1, 'Páginas Web para Negocios', 250.00::numeric,
     'Diseño de sitios web claros, rápidos y adaptados para celulares y computadoras.'),
    (2, 'Catálogo Digital de Productos', 120.00::numeric,
     'Muestra tus productos con fotos, precios y botón para hacer pedidos por WhatsApp.'),
    (3, 'Menú Digital con Código QR', 65.00::numeric,
     'Menú interactivo para restaurantes y cafeterías accesible escaneando un código QR.'),
    (4, 'Formularios de Contacto y Pedidos', 85.00::numeric,
     'Formularios personalizados para recibir solicitudes, cotizaciones y reservas.'),
    (5, 'Botón de WhatsApp y Redes Sociales', 45.00::numeric,
     'Integración de enlaces directos a WhatsApp, Instagram, Facebook y TikTok.'),
    (6, 'Asesoría y Optimización Web', 110.00::numeric,
     'Revisión técnica de páginas web para mejorar su velocidad y accesibilidad.')
) AS datos(id, nombre, precio, descripcion)
WHERE servicios.id = datos.id;

-- Mantiene los correlativos de facturas y cotizaciones por delante de los
-- documentos existentes para evitar números duplicados.
SELECT setval(
    'secuencia_facturas',
    GREATEST(
        COALESCE((SELECT MAX(substring(numero FROM '[0-9]+$')::BIGINT)
                  FROM facturacion
                  WHERE tipo = 'Factura' AND numero ~ '[0-9]+$'), 1),
        1
    ),
    true
);

SELECT setval(
    'secuencia_cotizaciones',
    GREATEST(
        COALESCE((SELECT MAX(substring(numero FROM '[0-9]+$')::BIGINT)
                  FROM facturacion
                  WHERE tipo = 'Cotizacion' AND numero ~ '[0-9]+$'), 1),
        1
    ),
    true
);

COMMIT;

-- Comprobación segura: no muestra contraseñas.
SELECT usuario, activo, aprobado,
       CASE
           WHEN password ~ '^\$2[aby]\$[0-9]{2}\$' THEN 'bcrypt'
           WHEN password LIKE 'scrypt:%' OR password LIKE 'pbkdf2:%' THEN 'werkzeug'
           ELSE 'REVISAR'
       END AS estado_password
FROM usuarios
ORDER BY id;

SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_name IN (
      'roles', 'usuarios', 'clientes', 'servicios',
      'facturacion', 'detalle_factura', 'solicitudes', 'proveedores'
  )
ORDER BY table_name;
