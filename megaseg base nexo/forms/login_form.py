# ==============================================================================
# PROYECTO: NEXODIGITAL - FORMULARIO DE INICIO DE SESIÓN
# ==============================================================================
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Length


class LoginForm(FlaskForm):
    """
    Formulario de autenticación de usuarios.
    Permite ingresar utilizando indistintamente el Nombre de Usuario o el Correo.
    """
    usuario = StringField(
        'Usuario o Correo Electrónico',
        validators=[
            DataRequired(message='Ingresa tu nombre de usuario o correo electrónico.'),
            Length(min=3, max=150, message='El campo debe tener entre 3 y 150 caracteres.')
        ]
    )

    password = PasswordField(
        'Contraseña',
        validators=[
            DataRequired(message='La contraseña es obligatoria.')
        ]
    )

    recordarme = BooleanField('Mantener sesión iniciada')

    submit = SubmitField('Iniciar Sesión')
