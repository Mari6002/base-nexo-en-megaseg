-- ==============================================================================
-- MIGRACIÓN SEGURA: MÓDULO DE FACTURACIÓN, ABONOS, COMPROBANTES Y CUOTAS
-- NexoDigital - Ecuador
-- ==============================================================================

-- 1. Estado "Parcial" en estados_documento
INSERT INTO estados_documento (nombre)
VALUES ('Parcial')
ON CONFLICT (nombre) DO NOTHING;

-- 2. Nuevos campos en la tabla facturacion (sin perder ningún dato existente)
ALTER TABLE facturacion
    ADD COLUMN IF NOT EXISTS numero_factura VARCHAR(30) UNIQUE,
    ADD COLUMN IF NOT EXISTS forma_pago VARCHAR(100) DEFAULT 'Transferencia bancaria',
    ADD COLUMN IF NOT EXISTS tipo_pago VARCHAR(20) DEFAULT 'contado',
    ADD COLUMN IF NOT EXISTS plazo_meses INT DEFAULT 1,
    ADD COLUMN IF NOT EXISTS con_intereses BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS tasa_interes NUMERIC(5,2) DEFAULT 0,
    ADD COLUMN IF NOT EXISTS monto_interes NUMERIC(12,2) DEFAULT 0,
    ADD COLUMN IF NOT EXISTS total_con_interes NUMERIC(12,2),
    ADD COLUMN IF NOT EXISTS total_abonado NUMERIC(12,2) DEFAULT 0,
    ADD COLUMN IF NOT EXISTS fecha_limite DATE,
    ADD COLUMN IF NOT EXISTS proxima_cuota_fecha DATE,
    ADD COLUMN IF NOT EXISTS proxima_cuota_monto NUMERIC(12,2);

-- 3. Tabla para el historial de abonos y pagos parciales
CREATE TABLE IF NOT EXISTS pagos_factura (
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

-- 4. Secuencia para comprobantes de pago únicos
CREATE SEQUENCE IF NOT EXISTS secuencia_comprobantes START WITH 1 INCREMENT BY 1;

-- 5. Tabla de comprobantes de pago (un comprobante por cada abono)
CREATE TABLE IF NOT EXISTS comprobantes_pago (
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

-- 6. Tabla de cuotas para el plan de pagos / amortización
CREATE TABLE IF NOT EXISTS cuotas_factura (
    id SERIAL PRIMARY KEY,
    factura_numero VARCHAR(30) NOT NULL REFERENCES facturacion(numero) ON DELETE CASCADE ON UPDATE CASCADE,
    numero_cuota INT NOT NULL,
    valor_cuota NUMERIC(12,2) NOT NULL,
    fecha_vencimiento DATE NOT NULL,
    monto_pagado NUMERIC(12,2) NOT NULL DEFAULT 0,
    saldo_cuota NUMERIC(12,2) NOT NULL,
    estado VARCHAR(30) NOT NULL DEFAULT 'Pendiente', -- 'Pendiente', 'Parcial', 'Pagada'
    fecha_pago DATE,
    CONSTRAINT uq_cuota_factura UNIQUE (factura_numero, numero_cuota)
);

-- 7. Actualización retroactiva de datos existentes
UPDATE facturacion
SET total_con_interes = COALESCE(total_con_interes, monto),
    total_abonado = COALESCE(total_abonado, anticipo, 0),
    fecha_limite = COALESCE(fecha_limite, fecha + INTERVAL '30 days')
WHERE total_con_interes IS NULL OR total_abonado IS NULL OR fecha_limite IS NULL;

-- Para facturas ya completamente pagadas históricamente, asegurar número de factura oficial
UPDATE facturacion
SET numero_factura = numero
WHERE tipo = 'Factura' AND saldo_pendiente <= 0 AND numero_factura IS NULL;

-- Si existe anticipo previo en 001-001-0004 y no tiene registro en pagos_factura, registrar su pago inicial
DO $$
DECLARE
    r RECORD;
    nuevo_pago_id INT;
    nuevo_comp_num TEXT;
    estado_parcial_id INT;
BEGIN
    SELECT id INTO estado_parcial_id FROM estados_documento WHERE nombre = 'Parcial';

    FOR r IN (
        SELECT f.*, c.cedula AS c_cedula
        FROM facturacion f
        JOIN clientes c ON f.cliente_cedula = c.cedula
        WHERE f.anticipo > 0
          AND NOT EXISTS (SELECT 1 FROM pagos_factura p WHERE p.factura_numero = f.numero)
    ) LOOP
        -- Insertar pago inicial
        INSERT INTO pagos_factura (
            factura_numero, numero_pago, monto, fecha, metodo_pago,
            saldo_anterior, saldo_posterior, total_acumulado, registrado_por, notas
        ) VALUES (
            r.numero, 1, r.anticipo, r.fecha, 'Transferencia bancaria',
            r.monto, r.saldo_pendiente, r.anticipo, 'Sistema', 'Abono inicial registrado'
        ) RETURNING id INTO nuevo_pago_id;

        -- Generar número de comprobante único
        nuevo_comp_num := 'REC-2026-' || LPAD(nextval('secuencia_comprobantes')::TEXT, 4, '0');

        -- Insertar comprobante de pago
        INSERT INTO comprobantes_pago (
            numero_comprobante, pago_id, factura_numero, cliente_cedula,
            fecha, monto_abonado, total_deuda, total_acumulado_pagado, saldo_pendiente, observaciones
        ) VALUES (
            nuevo_comp_num, nuevo_pago_id, r.numero, r.c_cedula,
            r.fecha, r.anticipo, r.monto, r.anticipo, r.saldo_pendiente, 'Comprobante de abono inicial'
        );

        -- Actualizar estado a Parcial si saldo > 0
        IF r.saldo_pendiente > 0 AND estado_parcial_id IS NOT NULL THEN
            UPDATE facturacion SET estado_id = estado_parcial_id WHERE numero = r.numero;
        END IF;
    END LOOP;
END $$;
