-- Sincroniza los precios del catálogo de Render con el catálogo local de NexoDigital.
-- Ejecutar una sola vez en la base de datos PostgreSQL conectada a Render.
UPDATE servicios
SET precio_base = datos.precio
FROM (VALUES
    ('Páginas Web para Negocios', 250.00::numeric),
    ('Catálogo Digital de Productos', 120.00::numeric),
    ('Menú Digital con Código QR', 65.00::numeric),
    ('Formularios de Contacto y Pedidos', 85.00::numeric),
    ('Botón de WhatsApp y Redes Sociales', 45.00::numeric),
    ('Asesoría y Optimización Web', 110.00::numeric)
) AS datos(nombre, precio)
WHERE servicios.nombre = datos.nombre;
