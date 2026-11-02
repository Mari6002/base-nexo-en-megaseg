# ==============================================================================
# PROYECTO: NEXODIGITAL - FORMULARIO DE REGISTRO SEGURIZADO
# ==============================================================================
from flask_wtf import FlaskForm
from wtforms import (
    StringField, PasswordField, SelectField, SubmitField, HiddenField,
    DateField, BooleanField
)
from wtforms.validators import DataRequired, Length, EqualTo, Email, Optional, Regexp


class UsuarioForm(FlaskForm):
    """
    Formulario completo para el registro de nuevos usuarios.
    Incluye datos básicos, validación de edad adulta, consentimiento y
    comprobación anti-bot en servidor.
    """
    nombres = StringField(
        'Nombres',
        validators=[
            DataRequired(message='Ingresa tus nombres.'),
            Length(min=4, max=80, message='Los nombres deben tener al menos 4 caracteres.'),
            Regexp(r'^[A-Za-zÁÉÍÓÚáéíóúÑñ\s]+$', message='Los nombres solo pueden contener letras y espacios.')
        ]
    )

    apellidos = StringField(
        'Apellidos',
        validators=[
            DataRequired(message='Ingresa tus apellidos.'),
            Length(min=4, max=80, message='Los apellidos deben tener al menos 4 caracteres.'),
            Regexp(r'^[A-Za-zÁÉÍÓÚáéíóúÑñ\s]+$', message='Los apellidos solo pueden contener letras y espacios.')
        ]
    )

    usuario = StringField(
        'Nombre de Usuario',
        validators=[
            DataRequired(message='El nombre de usuario es obligatorio.'),
            Length(min=3, max=50, message='El usuario debe tener entre 3 y 50 caracteres.')
        ]
    )

    correo = StringField(
        'Correo Electrónico',
        validators=[
            DataRequired(message='El correo electrónico es obligatorio.'),
            Email(message='Ingresa un formato de correo válido (ej: usuario@empresa.com).')
        ]
    )

    telefono = StringField(
        'Teléfono',
        validators=[
            DataRequired(message='El teléfono es obligatorio.'),
            Regexp(r'^\d{10}$', message='El teléfono debe contener exactamente 10 dígitos numéricos.')
        ]
    )

    fecha_nacimiento = DateField(
        'Fecha de Nacimiento',
        format='%Y-%m-%d',
        validators=[DataRequired(message='Debes indicar tu fecha de nacimiento.')]
    )

    rol_id = SelectField(
        'Rol Solicitado en el Sistema',
        coerce=int,
        validators=[DataRequired(message='Selecciona el rol correspondiente.')]
    )

    password = PasswordField(
        'Contraseña',
        validators=[
            DataRequired(message='La contraseña es obligatoria.'),
            Length(min=8, message='La contraseña debe tener al menos 8 caracteres.')
        ]
    )

    confirm_password = PasswordField(
        'Confirmar Contraseña',
        validators=[
            DataRequired(message='Por favor confirma tu contraseña.'),
            EqualTo('password', message='Las contraseñas ingresadas no coinciden.')
        ]
    )

    mayor_edad = BooleanField('Declaro que soy mayor de edad (18+)')
    acepta_terminos = BooleanField('Acepto los términos y condiciones y autorizo el tratamiento de mis datos.')

    recaptcha_token = HiddenField('reCAPTCHA')
    captcha_pregunta = HiddenField('Pregunta CAPTCHA')
    captcha_respuesta = StringField(
        'Verificación de Seguridad (anti-bot)',
        validators=[
            DataRequired(message='Responde la pregunta de seguridad para demostrar que eres humano.')
        ]
    )

    submit = SubmitField('Registrar Cuenta')
