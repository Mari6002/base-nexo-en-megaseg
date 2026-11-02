import os
import sys
from decimal import Decimal

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import psycopg2
from psycopg2.extras import RealDictCursor
from app import app
from models import Usuario

from conexion.conexion import get_db_connection

def get_test_db():
    return get_db_connection()

def ejecutar_pruebas():
    print("=" * 70)
    print("INICIANDO PRUEBAS OBLIGATORIAS DEL MÓDULO DE FACTURACIÓN")
    print("=" * 70)

    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False

    client = app.test_client()

    # Autenticar como administrador
    with app.app_context():
        admin = Usuario.get_by_id(1)

    with client.session_transaction() as sess:
        sess['_user_id'] = str(admin.id)
        sess['_fresh'] = True

    conn = get_test_db()
    cur = conn.cursor()

    # Obtener mapeo de estados_documento
    cur.execute("SELECT id, nombre FROM estados_documento;")
    estados = {r['nombre']: r['id'] for r in cur.fetchall()}
    print(f"Estados disponibles en BD: {estados}")

    id_emitida = estados.get('Emitida', 1)
    id_parcial = estados.get('Parcial')
    id_pagada = estados.get('Pagada')

    # Limpiar datos previos del test si existieran
    doc_test = "TEST-FACT-1000"
    cur.execute("DELETE FROM comprobantes_pago WHERE factura_numero = %s;", (doc_test,))
    cur.execute("DELETE FROM cuotas_factura WHERE factura_numero = %s;", (doc_test,))
    cur.execute("DELETE FROM pagos_factura WHERE factura_numero = %s;", (doc_test,))
    cur.execute("DELETE FROM detalle_factura WHERE factura_numero = %s;", (doc_test,))
    cur.execute("DELETE FROM facturacion WHERE numero = %s;", (doc_test,))
    conn.commit()

    # Insertar documento de prueba con deuda de $1.000,00
    cur.execute("""
        INSERT INTO facturacion (
            numero, fecha, cliente_cedula, tipo, estado_id,
            subtotal, iva, monto, anticipo,
            saldo_pendiente, total_abonado, con_intereses, tasa_interes, monto_interes, total_con_interes,
            tipo_pago, plazo_meses, forma_pago, notas
        ) VALUES (
            %s, CURRENT_DATE, '1700111222', 'Factura', %s,
            1000.00, 0.00, 1000.00, 0.00,
            1000.00, 0.00, FALSE, 0.00, 0.00, 1000.00,
            'plazos', 3, '01', 'Documento de prueba para abonos y comprobantes'
        );
    """, (doc_test, id_emitida))
    conn.commit()
    print(f"-> Documento {doc_test} creado con éxito. Monto total: $1.000,00 | Saldo pendiente: $1.000,00\n")

    # ----------------------------------------------------------------------
    # CASO 1: Deuda de $1.000, abono de $200
    # ----------------------------------------------------------------------
    print("-" * 70)
    print("CASO 1: Deuda de $1.000,00 | Abono de $200,00")
    print("-" * 70)
    resp1 = client.post(f"/facturacion/abono/{doc_test}", data={
        "monto": "200.00",
        "metodo_pago": "01",
        "referencia": "TRANSF-001",
        "observaciones": "Primer abono de prueba"
    }, follow_redirects=True)
    assert resp1.status_code == 200

    conn.commit()
    cur.execute("""
        SELECT f.monto, f.total_abonado, f.saldo_pendiente, ed.nombre AS estado_nombre, f.numero_factura 
        FROM facturacion f
        JOIN estados_documento ed ON ed.id = f.estado_id
        WHERE f.numero = %s;
    """, (doc_test,))
    row1 = cur.fetchone()
    print(f"Estado en BD: Total=${row1['monto']}, Abonado=${row1['total_abonado']}, Saldo=${row1['saldo_pendiente']}, Estado='{row1['estado_nombre']}', NumFactura={row1['numero_factura']}")
    assert Decimal(str(row1['total_abonado'])) == Decimal("200.00"), f"Abonado incorrecto: {row1['total_abonado']}"
    assert Decimal(str(row1['saldo_pendiente'])) == Decimal("800.00"), f"Saldo incorrecto: {row1['saldo_pendiente']}"
    assert row1['estado_nombre'] == 'Parcial', f"Estado incorrecto: {row1['estado_nombre']}"
    assert row1['numero_factura'] is None, f"NO debe tener numero_factura aún: {row1['numero_factura']}"

    # Verificar comprobante de pago
    cur.execute("SELECT numero_comprobante, monto_abonado, saldo_pendiente, total_acumulado_pagado FROM comprobantes_pago WHERE factura_numero = %s ORDER BY id DESC LIMIT 1;", (doc_test,))
    comp1 = cur.fetchone()
    assert comp1 is not None, "Debe generar comprobante de pago"
    print(f"Comprobante generado: {comp1['numero_comprobante']} por ${comp1['monto_abonado']} (Acumulado: ${comp1['total_acumulado_pagado']}, Saldo pendiente: ${comp1['saldo_pendiente']})")
    assert Decimal(str(comp1['monto_abonado'])) == Decimal("200.00")
    assert Decimal(str(comp1['saldo_pendiente'])) == Decimal("800.00")

    # Verificar que el endpoint de comprobante responde 200 OK
    resp_comp1 = client.get(f"/facturacion/comprobante-pago/{comp1['numero_comprobante']}")
    assert resp_comp1.status_code == 200, "El comprobante de pago debe ser visible"
    assert "COMPROBANTE DE PAGO" in resp_comp1.get_data(as_text=True)

    # Verificar que NO genera factura / acceso bloqueado
    resp_fact1 = client.get(f"/facturacion/factura/{doc_test}")
    assert resp_fact1.status_code == 302, "Acceso a factura directa debe ser bloqueado con redirect 302"
    print("Acceso a factura bloqueado correctamente con saldo pendiente.")
    print(">>> CASO 1: EXITOSO [OK]\n")

    # ----------------------------------------------------------------------
    # CASO 2: Segundo abono de $300 a la misma deuda
    # ----------------------------------------------------------------------
    print("-" * 70)
    print("CASO 2: Segundo abono de $300,00 a la misma deuda")
    print("-" * 70)
    resp2 = client.post(f"/facturacion/abono/{doc_test}", data={
        "monto": "300.00",
        "metodo_pago": "20",
        "referencia": "TRANSF-002",
        "observaciones": "Segundo abono de prueba"
    }, follow_redirects=True)
    assert resp2.status_code == 200

    conn.commit()
    cur.execute("""
        SELECT f.monto, f.total_abonado, f.saldo_pendiente, ed.nombre AS estado_nombre, f.numero_factura 
        FROM facturacion f
        JOIN estados_documento ed ON ed.id = f.estado_id
        WHERE f.numero = %s;
    """, (doc_test,))
    row2 = cur.fetchone()
    print(f"Estado en BD: Total=${row2['monto']}, Abonado=${row2['total_abonado']}, Saldo=${row2['saldo_pendiente']}, Estado='{row2['estado_nombre']}', NumFactura={row2['numero_factura']}")
    assert Decimal(str(row2['total_abonado'])) == Decimal("500.00"), f"Abonado incorrecto: {row2['total_abonado']}"
    assert Decimal(str(row2['saldo_pendiente'])) == Decimal("500.00"), f"Saldo incorrecto: {row2['saldo_pendiente']}"
    assert row2['estado_nombre'] == 'Parcial', f"Estado incorrecto: {row2['estado_nombre']}"
    assert row2['numero_factura'] is None, f"NO debe tener numero_factura: {row2['numero_factura']}"

    # Verificar segundo comprobante de pago
    cur.execute("SELECT numero_comprobante, monto_abonado, saldo_pendiente, total_acumulado_pagado FROM comprobantes_pago WHERE factura_numero = %s ORDER BY id DESC LIMIT 1;", (doc_test,))
    comp2 = cur.fetchone()
    assert comp2 is not None
    print(f"Segundo Comprobante generado: {comp2['numero_comprobante']} por ${comp2['monto_abonado']} (Acumulado: ${comp2['total_acumulado_pagado']}, Saldo pendiente: ${comp2['saldo_pendiente']})")
    assert Decimal(str(comp2['monto_abonado'])) == Decimal("300.00")
    assert Decimal(str(comp2['saldo_pendiente'])) == Decimal("500.00")

    # Verificar que aún NO genera factura / acceso bloqueado
    resp_fact2 = client.get(f"/facturacion/factura/{doc_test}")
    assert resp_fact2.status_code == 302, "Acceso a factura directa debe ser bloqueado con redirect 302"
    print("Acceso a factura bloqueado correctamente con saldo pendiente.")
    print(">>> CASO 2: EXITOSO [OK]\n")

    # ----------------------------------------------------------------------
    # CASO 4: Intentar abonar $600 cuando el saldo pendiente es $500
    # ----------------------------------------------------------------------
    print("-" * 70)
    print("CASO 4: Intentar abonar $600,00 cuando el saldo pendiente es $500,00")
    print("-" * 70)
    resp4 = client.post(f"/facturacion/abono/{doc_test}", data={
        "monto": "600.00",
        "metodo_pago": "01",
        "referencia": "TRANSF-003",
        "observaciones": "Intento de sobrepago"
    }, follow_redirects=True)
    assert resp4.status_code == 200

    # Verificar que el mensaje de error se haya enviado
    contenido_resp4 = resp4.get_data(as_text=True)
    assert "no puede ser mayor al saldo pendiente" in contenido_resp4 or "excede" in contenido_resp4, "Debe mostrar mensaje de error de sobrepago"
    print("Mensaje de rechazo verificado en la respuesta (monto excede saldo pendiente).")

    # Verificar que los datos en BD NO hayan cambiado
    conn.commit()
    cur.execute("""
        SELECT f.monto, f.total_abonado, f.saldo_pendiente, ed.nombre AS estado_nombre 
        FROM facturacion f
        JOIN estados_documento ed ON ed.id = f.estado_id
        WHERE f.numero = %s;
    """, (doc_test,))
    row4 = cur.fetchone()
    print(f"Estado en BD sin cambios: Abonado=${row4['total_abonado']}, Saldo=${row4['saldo_pendiente']}, Estado='{row4['estado_nombre']}'")
    assert Decimal(str(row4['total_abonado'])) == Decimal("500.00"), "El total abonado no debió modificarse"
    assert Decimal(str(row4['saldo_pendiente'])) == Decimal("500.00"), "El saldo pendiente no debió modificarse"

    # Verificar que NO se haya insertado un nuevo comprobante
    cur.execute("SELECT COUNT(*) as total_comps FROM comprobantes_pago WHERE factura_numero = %s;", (doc_test,))
    count_comps = cur.fetchone()['total_comps']
    assert count_comps == 2, f"Deben seguir existiendo únicamente 2 comprobantes, encontrados: {count_comps}"
    print(f"Total comprobantes se mantuvo en {count_comps}. Integridad protegida.")
    print(">>> CASO 4: EXITOSO [OK]\n")

    # ----------------------------------------------------------------------
    # CASO 5: Intentar acceder a la URL de la factura directamente con saldo > $0
    # ----------------------------------------------------------------------
    print("-" * 70)
    print("CASO 5: Intentar acceder a la URL de factura directamente con saldo pendiente")
    print("-" * 70)
    resp5 = client.get(f"/facturacion/factura/{doc_test}", follow_redirects=False)
    assert resp5.status_code == 302, f"Esperado redirect 302, obtenido: {resp5.status_code}"
    assert "/facturacion" in resp5.headers['Location'], f"Redirección esperada a /facturacion, obtenida: {resp5.headers['Location']}"

    resp5_follow = client.get(f"/facturacion/factura/{doc_test}", follow_redirects=True)
    contenido_resp5 = resp5_follow.get_data(as_text=True)
    assert "completamente pagada" in contenido_resp5 or "saldo" in contenido_resp5, "Debe mostrar mensaje de restricción"
    print("Acceso bloqueado en backend y mensaje de advertencia desplegado al usuario.")
    print(">>> CASO 5: EXITOSO [OK]\n")

    # ----------------------------------------------------------------------
    # CASO 3: Último abono de $500 a la misma deuda
    # ----------------------------------------------------------------------
    print("-" * 70)
    print("CASO 3: Último abono de $500,00 a la misma deuda (liquidación completa)")
    print("-" * 70)
    resp3 = client.post(f"/facturacion/abono/{doc_test}", data={
        "monto": "500.00",
        "metodo_pago": "01",
        "referencia": "TRANSF-004",
        "observaciones": "Liquidación final"
    }, follow_redirects=True)
    assert resp3.status_code == 200

    conn.commit()
    cur.execute("""
        SELECT f.monto, f.total_abonado, f.saldo_pendiente, ed.nombre AS estado_nombre, f.numero_factura 
        FROM facturacion f
        JOIN estados_documento ed ON ed.id = f.estado_id
        WHERE f.numero = %s;
    """, (doc_test,))
    row3 = cur.fetchone()
    print(f"Estado en BD: Total=${row3['monto']}, Abonado=${row3['total_abonado']}, Saldo=${row3['saldo_pendiente']}, Estado='{row3['estado_nombre']}', NumFactura={row3['numero_factura']}")
    assert Decimal(str(row3['total_abonado'])) == Decimal("1000.00"), f"Abonado incorrecto: {row3['total_abonado']}"
    assert Decimal(str(row3['saldo_pendiente'])) == Decimal("0.00"), f"Saldo incorrecto: {row3['saldo_pendiente']}"
    assert row3['estado_nombre'] == 'Pagada', f"Estado incorrecto: {row3['estado_nombre']}"
    assert row3['numero_factura'] is not None and len(row3['numero_factura']) > 0, f"Debe tener numero_factura asignado: {row3['numero_factura']}"

    # Verificar 3er comprobante de pago generado
    cur.execute("SELECT numero_comprobante, monto_abonado, saldo_pendiente, total_acumulado_pagado FROM comprobantes_pago WHERE factura_numero = %s ORDER BY id DESC LIMIT 1;", (doc_test,))
    comp3 = cur.fetchone()
    assert comp3 is not None
    print(f"Tercer Comprobante generado: {comp3['numero_comprobante']} por ${comp3['monto_abonado']} (Acumulado: ${comp3['total_acumulado_pagado']}, Saldo pendiente: ${comp3['saldo_pendiente']})")
    assert Decimal(str(comp3['monto_abonado'])) == Decimal("500.00")
    assert Decimal(str(comp3['saldo_pendiente'])) == Decimal("0.00")

    # Verificar que AHORA SÍ se puede acceder a la factura fiscal final
    resp_fact3 = client.get(f"/facturacion/factura/{doc_test}")
    assert resp_fact3.status_code == 200, f"Ahora debe responder 200 OK, obtenido: {resp_fact3.status_code}"
    contenido_fact3 = resp_fact3.get_data(as_text=True)
    assert "FACTURA DE VENTA OFICIAL" in contenido_fact3 or "Factura Oficial" in contenido_fact3, "La factura debe mostrarse como FACTURA DE VENTA OFICIAL"
    assert row3['numero_factura'] in contenido_fact3, f"El número de factura {row3['numero_factura']} debe mostrarse"
    assert "100.0% Pagado" in contenido_fact3 or "PAGADA" in contenido_fact3, "Debe mostrar el estado pagado y liquidado"
    print(f"Factura generada y visible con éxito: Número Oficial {row3['numero_factura']}")
    print(">>> CASO 3: EXITOSO [OK]\n")

    # Limpiar datos de prueba al finalizar
    cur.execute("DELETE FROM comprobantes_pago WHERE factura_numero = %s;", (doc_test,))
    cur.execute("DELETE FROM cuotas_factura WHERE factura_numero = %s;", (doc_test,))
    cur.execute("DELETE FROM pagos_factura WHERE factura_numero = %s;", (doc_test,))
    cur.execute("DELETE FROM detalle_factura WHERE factura_numero = %s;", (doc_test,))
    cur.execute("DELETE FROM facturacion WHERE numero = %s;", (doc_test,))
    conn.commit()
    print(f"Limpieza completada: Registro de prueba {doc_test} eliminado.")

    cur.close()
    conn.close()

    print("=" * 70)
    print("TODAS LAS 5 PRUEBAS OBLIGATORIAS PASARON SATISFACTORIAMENTE (100% OK)")
    print("=" * 70)

if __name__ == "__main__":
    ejecutar_pruebas()
