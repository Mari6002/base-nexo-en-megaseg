from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired, Length


class CategoriaProveedorForm(FlaskForm):
    """
    Formulario para administrar las categorías de infraestructura que ofrecen
    los proveedores (ej: Servidor y Hosting, Registro de Dominios, SSL).
    """
    nombre = StringField(
        'Nombre de la categoría',
        validators=[
            DataRequired(message='El nombre de la categoría es obligatorio.'),
            Length(min=3, max=60, message='Debe tener entre 3 y 60 caracteres.')
        ]
    )

    submit = SubmitField('Guardar Categoría')
