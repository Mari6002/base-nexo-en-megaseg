-- Impide duplicar números de celular en las cuentas existentes.
-- Ejecutar en pgAdmin antes de publicar la versión final.
ALTER TABLE usuarios
    ADD COLUMN IF NOT EXISTS telefono VARCHAR(30);

DO $$
BEGIN
    IF EXISTS (
        SELECT telefono
        FROM usuarios
        WHERE telefono IS NOT NULL
        GROUP BY telefono
        HAVING COUNT(*) > 1
    ) THEN
        RAISE EXCEPTION 'No se puede crear la restricción: existen teléfonos duplicados.';
    END IF;

    CREATE UNIQUE INDEX IF NOT EXISTS ux_usuarios_telefono
        ON usuarios (telefono)
        WHERE telefono IS NOT NULL;
END $$;
