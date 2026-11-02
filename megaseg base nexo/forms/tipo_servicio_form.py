from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired, Length


class TipoServicioForm(FlaskForm):
    """
    Formulario para administrar las categorías del catálogo de servicios
    (ej: Desarrollo Web, Marketing Digital, Diseño y Catálogos).
    """
    nombre = StringField(
        'Nombre de la categoría',
        validators=[
            DataRequired(message='El nombre de la categoría es obligatorio.'),
            Length(min=3, max=60, message='Debe tener entre 3 y 60 caracteres.')
        ]
    )

    submit = SubmitField('Guardar Categoría')
