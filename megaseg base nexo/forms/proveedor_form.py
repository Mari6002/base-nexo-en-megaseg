# ==============================================================================
# FORMULARIO: REGISTRO Y EDICIÓN DE PROVEEDORES
# ==============================================================================
# Modela los campos necesarios para registrar empresas y plataformas proveedoras
# de infraestructura tecnológica (hosting, dominios, SSL, herramientas de diseño).
# ==============================================================================

from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, SubmitField
from wtforms.validators import DataRequired, Length


class ProveedorForm(FlaskForm):
    """
    Formulario para la gestión de proveedores de software e infraestructura.
    """
    # Nombre comercial del proveedor
    nombre = StringField(
        'Nombre del proveedor o plataforma',
        validators=[
            DataRequired(message='El nombre del proveedor es obligatorio.'),
            Length(min=3, max=100, message='Debe contener entre 3 y 100 caracteres.')
        ]
    )

    # Categoría de infraestructura: selección real desde categorias_proveedor (clave foránea)
    categoria_id = SelectField(
        'Tipo de servicio que ofrece',
        coerce=int,
        validators=[DataRequired(message='Selecciona una categoría válida.')]
    )

    # Dominio o dirección web oficial
    sitio = StringField(
        'Sitio web oficial',
        validators=[
            DataRequired(message='El sitio web es obligatorio.'),
            Length(min=3, max=100, message='Debe contener entre 3 y 100 caracteres.')
        ]
    )

    # Estado operativo actual: selección real desde la tabla estados_proveedor (clave foránea)
    estado_id = SelectField(
        'Estado operativo',
        coerce=int,
        validators=[DataRequired(message='Selecciona un estado operativo válido.')]
    )

    # Botón de envío
    submit = SubmitField('Guardar proveedor')
