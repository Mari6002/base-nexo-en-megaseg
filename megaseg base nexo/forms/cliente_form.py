from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, SubmitField
from wtforms.validators import DataRequired, Length, Regexp


class ClienteForm(FlaskForm):
    """
    Formulario de registro y edición de clientes.
    Contiene únicamente datos propios del cliente; los servicios que contrata
    se gestionan de forma independiente en el módulo de Facturación.
    """
    cedula = StringField(
        'Cédula',
        validators=[
            DataRequired(message='La cédula es obligatoria.'),
            Regexp(r'^\d{10}$', message='La cédula debe tener 10 dígitos numéricos.')
        ]
    )

    nombre = StringField(
        'Nombre / Razón Social',
        validators=[
            DataRequired(message='El nombre es obligatorio.'),
            Length(min=3, max=100, message='Debe contener entre 3 y 100 caracteres.')
        ]
    )

    telefono = StringField(
        'Teléfono',
        validators=[
            DataRequired(message='El teléfono es obligatorio.'),
            Regexp(r'^\d{7,10}$', message='Ingresa un teléfono válido (7 a 10 dígitos).')
        ]
    )

    correo = StringField(
        'Correo electrónico',
        validators=[
            DataRequired(message='El correo es obligatorio.'),
            Regexp(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', message='Ingresa un correo electrónico válido.')
        ]
    )

    # Categoría de negocio: selección real desde tipos_negocio (clave foránea)
    tipo_negocio_id = SelectField(
        'Tipo de negocio',
        coerce=int,
        validators=[DataRequired(message='Selecciona un tipo de negocio.')]
    )

    ciudad = StringField(
        'Ciudad',
        validators=[
            DataRequired(message='La ciudad es obligatoria.'),
            Length(max=50, message='Máximo 50 caracteres.')
        ]
    )

    submit = SubmitField('Guardar Cliente')
