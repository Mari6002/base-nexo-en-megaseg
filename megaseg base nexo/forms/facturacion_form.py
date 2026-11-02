# ==============================================================================
# FORMULARIO: FACTURACIÓN Y COTIZACIONES COMERCIALES
# ==============================================================================
# Gestiona la emisión y edición de comprobantes de venta y propuestas económicas.
# Soporta detalle dinámico de ítems en formato JSON, planes de pago con amortización
# de 3 a 24 meses, intereses y cálculo de anticipos/saldos según normativa Ecuador.
# ==============================================================================

from flask_wtf import FlaskForm
from wtforms import StringField, FloatField, SelectField, TextAreaField, HiddenField, SubmitField, IntegerField
from wtforms.validators import DataRequired, Length, NumberRange, Optional


class FacturacionForm(FlaskForm):
    """
    Formulario unificado para Facturas de Venta y Cotizaciones Comerciales.
    """
    # Clasificación del comprobante
    tipo = SelectField(
        'Tipo de Documento',
        choices=[
            ('Factura', 'Factura de Venta (Comprobante Fiscal)'),
            ('Cotizacion', 'Cotización / Proforma Comercial')
        ],
        validators=[DataRequired(message='Selecciona el tipo de documento.')]
    )

    # Número secuencial o código identificador (se autogenera si se deja vacío)
    numero = StringField(
        'N° Documento / Código (Auto-generado)',
        validators=[
            Optional(),
            Length(max=40, message='Debe contener hasta 40 caracteres.')
        ]
    )

    # Cliente receptor: selección real por su cédula (clave primaria y foránea)
    cliente_cedula = SelectField(
        'Cliente',
        validators=[DataRequired(message='Debes seleccionar un cliente registrado.')]
    )

    # Fecha de emisión del documento (formato YYYY-MM-DD)
    fecha = StringField(
        'Fecha de emisión',
        validators=[
            DataRequired(message='La fecha es obligatoria.'),
            Length(min=8, max=10, message='Formato de fecha no válido.')
        ]
    )

    # Plazo de vigencia de la oferta comercial (aplica principalmente para cotizaciones)
    validez = StringField(
        'Vigencia / Plazo de la oferta',
        validators=[
            Optional(),
            Length(max=50, message='Máximo 50 caracteres para la vigencia.')
        ]
    )

    # Forma de pago (Normativa SRI Ecuador) - Solo aplica a facturas
    forma_pago = SelectField(
        'Forma de Pago',
        choices=[
            ('Transferencia bancaria', 'Transferencia bancaria (Directa / Interbancaria)'),
            ('Efectivo', 'Efectivo (Sin utilización del sistema financiero)'),
            ('Tarjeta de débito', 'Tarjeta de débito'),
            ('Tarjeta de crédito', 'Tarjeta de crédito'),
            ('Depósito bancario', 'Depósito bancario en cuenta')
        ],
        default='Transferencia bancaria',
        validators=[Optional()]
    )

    # Modalidad de cobro: Contado o a Plazos
    tipo_pago = SelectField(
        'Modalidad de Pago',
        choices=[
            ('contado', 'Pago al Contado (1 solo pago)'),
            ('plazos', 'Plan de Pagos en Cuotas (Amortización a Plazos)')
        ],
        default='contado',
        validators=[Optional()]
    )

    # Plazo de amortización (Permite plazos desde 3 hasta 24 meses)
    plazo_meses = SelectField(
        'Plazo de Amortización',
        coerce=int,
        choices=[
            (3, '3 meses (3 cuotas mensuales)'),
            (4, '4 meses (4 cuotas mensuales)'),
            (5, '5 meses (5 cuotas mensuales)'),
            (6, '6 meses (6 cuotas mensuales)'),
            (8, '8 meses (8 cuotas mensuales)'),
            (9, '9 meses (9 cuotas mensuales)'),
            (10, '10 meses (10 cuotas mensuales)'),
            (12, '12 meses (1 año - 12 cuotas)'),
            (18, '18 meses (1.5 años - 18 cuotas)'),
            (24, '24 meses (2 años - 24 cuotas)')
        ],
        default=3,
        validators=[Optional()]
    )

    # Opción CON INTERESES / SIN INTERESES
    con_intereses = SelectField(
        'Financiamiento',
        choices=[
            ('0', 'Sin Intereses (0% financiamiento directo)'),
            ('1', 'Con Intereses')
        ],
        default='0',
        validators=[Optional()]
    )

    # Tasa de interés (%) cuando corresponda
    tasa_interes = FloatField(
        'Tasa de Interés (%)',
        validators=[
            Optional(),
            NumberRange(min=0, max=100, message='La tasa de interés debe estar entre 0% y 100%.')
        ],
        default=0.0
    )

    # Monto total de interés calculado
    monto_interes = FloatField(
        'Intereses Financieros ($)',
        validators=[
            Optional(),
            NumberRange(min=0, message='El monto de interés no puede ser negativo.')
        ],
        default=0.00
    )

    # Total general incluyendo intereses
    total_con_interes = FloatField(
        'Total con Financiamiento ($)',
        validators=[
            Optional(),
            NumberRange(min=0, message='El total no puede ser negativo.')
        ]
    )

    # Fecha límite de pago final calculada
    fecha_limite = StringField(
        'Fecha Límite de Pago',
        validators=[
            Optional(),
            Length(max=20, message='Formato de fecha límite no válido.')
        ]
    )
    
    # Campo oculto que almacena la lista de servicios/ítems serializada en JSON
    servicios_json = HiddenField('Detalle de Servicios JSON')
    
    # Subtotal calculado antes de impuestos
    subtotal = FloatField(
        'Subtotal ($)',
        validators=[
            Optional(),
            NumberRange(min=0, message='El subtotal no puede ser un valor negativo.')
        ]
    )

    # Valor del IVA (15% vigente en Ecuador)
    iva = FloatField(
        'IVA 15% ($)',
        validators=[
            Optional(),
            NumberRange(min=0, message='El IVA no puede ser un valor negativo.')
        ]
    )

    # Monto total general del documento (Total Original)
    monto = FloatField(
        'Total General ($)',
        validators=[
            DataRequired(message='El monto total es obligatorio.'),
            NumberRange(min=0, message='El total no puede ser negativo.')
        ]
    )

    # Valor abonado o anticipo entregado por el cliente
    anticipo = FloatField(
        'Abono Recibido ($)',
        validators=[
            Optional(),
            NumberRange(min=0, message='El anticipo no puede ser negativo.')
        ],
        default=0.00
    )

    # Saldo pendiente de cobro contra entrega
    saldo_pendiente = FloatField(
        'Saldo Pendiente / Diferencia ($)',
        validators=[
            Optional(),
            NumberRange(min=0, message='El saldo no puede ser negativo.')
        ],
        default=0.00
    )
    
    # Estado actual del proceso de cobranza o aprobación (clave foránea hacia estados_documento)
    estado_id = SelectField(
        'Estado del Documento',
        coerce=int,
        validators=[DataRequired(message='Selecciona el estado actual del documento.')]
    )

    # Notas, términos de pago y condiciones comerciales
    notas = TextAreaField(
        'Notas, Términos y Condiciones de Pago',
        validators=[
            Optional(),
            Length(max=500, message='Las notas no pueden exceder 500 caracteres.')
        ]
    )

    # Botón de guardado
    submit = SubmitField('Guardar y Emitir Documento')
