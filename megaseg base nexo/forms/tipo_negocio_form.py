from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired, Length


class TipoNegocioForm(FlaskForm):
    """
    Formulario para administrar las categorías de tipo de negocio de los clientes
    (ej: Panadería, Tienda de Ropa, Cafetería).
    """
    nombre = StringField(
        'Nombre del tipo de negocio',
        validators=[
            DataRequired(message='El nombre del tipo de negocio es obligatorio.'),
            Length(min=3, max=60, message='Debe tener entre 3 y 60 caracteres.')
        ]
    )

    submit = SubmitField('Guardar Tipo de Negocio')
