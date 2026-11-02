-- Corrige los textos del catálogo que fueron guardados con caracteres
-- reemplazados durante una carga anterior. Ejecutar en local y en Render.
SET client_encoding = 'UTF8';

UPDATE servicios
SET nombre = CASE id
    WHEN 1 THEN 'Páginas Web para Negocios'
    WHEN 2 THEN 'Catálogo Digital de Productos'
    WHEN 3 THEN 'Menú Digital con Código QR'
    WHEN 4 THEN 'Formularios de Contacto y Pedidos'
    WHEN 5 THEN 'Botón de WhatsApp y Redes Sociales'
    WHEN 6 THEN 'Asesoría y Optimización Web'
    ELSE nombre
END,
descripcion = CASE id
    WHEN 1 THEN 'Diseño de sitios web claros, rápidos y adaptados para celulares y computadoras.'
    WHEN 2 THEN 'Muestra tus productos con fotos, precios y botón para hacer pedidos por WhatsApp.'
    WHEN 3 THEN 'Menú interactivo para restaurantes y cafeterías accesible escaneando un código QR.'
    WHEN 4 THEN 'Formularios personalizados para recibir solicitudes, cotizaciones y reservas.'
    WHEN 5 THEN 'Integración de enlaces directos a WhatsApp, Instagram, Facebook y TikTok.'
    WHEN 6 THEN 'Revisión técnica de páginas web para mejorar su velocidad y accesibilidad.'
    ELSE descripcion
END
WHERE id BETWEEN 1 AND 6;
