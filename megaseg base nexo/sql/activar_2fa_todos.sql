-- Activa la autenticación de dos factores para todas las cuentas existentes.
-- Ejecutar una sola vez en la base de datos PostgreSQL de Render.
UPDATE usuarios
SET dos_factores_activo = TRUE,
    dos_factores_codigo = NULL;

-- Comprobación: esta consulta debe devolver 0 usuarios desactivados.
SELECT COUNT(*) AS usuarios_sin_2fa
FROM usuarios
WHERE dos_factores_activo IS NOT TRUE;
