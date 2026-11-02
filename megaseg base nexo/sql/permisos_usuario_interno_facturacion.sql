-- Permite al personal interno consultar y emitir facturas o cotizaciones.
-- No concede editar, eliminar ni administrar usuarios.
INSERT INTO rol_permisos (rol_id, permiso_id)
SELECT r.id, p.id
FROM roles r
JOIN permisos p ON p.codigo IN ('facturas.ver', 'facturas.crear')
WHERE r.nombre = 'Usuario interno'
ON CONFLICT DO NOTHING;

SELECT r.nombre AS rol, p.codigo AS permiso
FROM rol_permisos rp
JOIN roles r ON r.id = rp.rol_id
JOIN permisos p ON p.id = rp.permiso_id
WHERE r.nombre = 'Usuario interno'
  AND p.codigo IN ('facturas.ver', 'facturas.crear')
ORDER BY p.codigo;
