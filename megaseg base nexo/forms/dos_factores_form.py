# ==============================================================================
# PROYECTO: NEXODIGITAL - FORMULARIO DE AUTENTICACIÓN EN DOS PASOS (2FA)
# ==============================================================================
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired, Length, Regexp


class DosFactoresForm(FlaskForm):
    """
    Formulario para ingresar el código numérico de 6 dígitos para validación 2FA.
    """
    codigo = StringField(
        'Código de Verificación (6 dígitos)',
        validators=[
            DataRequired(message='Ingresa el código de 6 dígitos.'),
            Length(min=6, max=6, message='El código debe contener exactamente 6 dígitos.'),
            Regexp(r'^\d{6}$', message='El código debe ser exclusivamente numérico.')
        ]
    )

    submit = SubmitField('Verificar Código')
