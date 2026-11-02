# ==============================================================================
# PROYECTO: NEXODIGITAL - FORMULARIO DE PRODUCTO / SERVICIO
# ==============================================================================
# Alias compatible para cumplir con la nomenclatura de la guía académica
# (producto_form.py / ProductoForm), apuntando a ServicioForm.
# ==============================================================================
from forms.servicio_form import ServicioForm

class ProductoForm(ServicioForm):
    """
    Formulario de productos/servicios del catálogo.
    Hereda directamente de ServicioForm garantizando total compatibilidad.
    """
    pass
