-- Evidencia y descripción del trabajo ejecutado por el responsable de una solicitud.
INSERT INTO permisos (codigo, descripcion)
VALUES ('servicios.editar', 'Modificación de precios y descripción de servicios')
ON CONFLICT (codigo) DO NOTHING;

INSERT INTO rol_permisos (rol_id, permiso_id)
SELECT r.id, p.id
FROM roles r
JOIN permisos p ON p.codigo = 'servicios.editar'
WHERE r.nombre = 'Soporte técnico'
ON CONFLICT DO NOTHING;

ALTER TABLE solicitudes
    ADD COLUMN IF NOT EXISTS trabajo_realizado TEXT,
    ADD COLUMN IF NOT EXISTS evidencia_url TEXT;

CREATE INDEX IF NOT EXISTS idx_solicitudes_finalizadas
    ON solicitudes (estado, responsable_id);
