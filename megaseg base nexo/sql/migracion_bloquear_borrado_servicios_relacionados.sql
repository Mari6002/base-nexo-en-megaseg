-- Impide borrar servicios que ya aparecen en facturas o cotizaciones.
-- Ejecutar una sola vez sobre la base de datos existente.

ALTER TABLE detalle_factura
    DROP CONSTRAINT IF EXISTS detalle_factura_servicio_id_fkey;

ALTER TABLE detalle_factura
    ADD CONSTRAINT detalle_factura_servicio_id_fkey
    FOREIGN KEY (servicio_id)
    REFERENCES servicios(id)
    ON DELETE RESTRICT;
