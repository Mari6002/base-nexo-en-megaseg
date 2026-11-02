-- Añade estado y responsable a las peticiones de clientes existentes.
ALTER TABLE solicitudes
    ADD COLUMN IF NOT EXISTS estado VARCHAR(30) NOT NULL DEFAULT 'Pendiente',
    ADD COLUMN IF NOT EXISTS responsable_id INT REFERENCES usuarios(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS respuesta_cliente TEXT;

CREATE INDEX IF NOT EXISTS idx_solicitudes_estado ON solicitudes (estado);
CREATE INDEX IF NOT EXISTS idx_solicitudes_responsable ON solicitudes (responsable_id);
