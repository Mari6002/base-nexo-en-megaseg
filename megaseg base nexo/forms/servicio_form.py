# ==============================================================================
# FORMULARIO: REGISTRO Y EDICIÓN DE SERVICIOS
# ==============================================================================
# Define la estructura de datos requerida para dar de alta o modificar servicios
# en el catálogo público de la empresa.
# ==============================================================================

from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, FloatField, BooleanField, SubmitField, SelectField
from wtforms.validators import DataRequired, Length, NumberRange, Optional


class ServicioForm(FlaskForm):
    """
    Formulario para la administración de servicios web y soluciones digitales.
    """
    # Categoría a la que pertenece el servicio (clave foránea hacia tipos_servicio)
    tipo_servicio_id = SelectField(
        'Tipo de servicio',
        coerce=int,
        validators=[DataRequired(message='Selecciona una categoría.')]
    )

    # Título descriptivo del servicio
    nombre = StringField(
        'Nombre del servicio',
        validators=[
            DataRequired(message='El nombre del servicio es obligatorio.'),
            Length(min=3, max=100, message='Debe tener entre 3 y 100 caracteres.')
        ]
    )

    # Tarifa base en dólares americanos (USD)
    precio = FloatField(
        'Precio base ($ USD)',
        validators=[
            DataRequired(message='Ingresa un precio numérico válido.'),
            NumberRange(min=0.01, message='El precio debe ser un valor positivo mayor a 0.')
        ]
    )

    # Enlace web a la imagen ilustrativa (opcional)
    imagen = StringField(
        'URL de imagen del servicio (Opcional)',
        validators=[
            Optional(),
            Length(max=500, message='La URL de la imagen no puede exceder 500 caracteres.')
        ]
    )

    # Descripción completa y detallada del servicio
    descripcion = TextAreaField(
        'Descripción detallada',
        validators=[
            DataRequired(message='La descripción del servicio es obligatoria.'),
            Length(min=10, max=500, message='Debe tener entre 10 y 500 caracteres.')
        ]
    )

    # Interruptor booleano de disponibilidad comercial inmediata
    disponible = BooleanField('Disponible para contratación inmediata')

    # Botón de acción
    submit = SubmitField('Guardar servicio')
