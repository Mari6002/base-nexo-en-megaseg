// ==============================================================================
// MÓDULO JS: REGISTRO DINÁMICO DE SOLICITUDES (DOM & LOCALSTORAGE)
// ==============================================================================
// Este script gestiona el módulo interactivo de solicitudes rápidas de clientes.
// Funcionalidades clave:
// 1. Manipulación directa del DOM (creación dinámica de tarjetas HTML).
// 2. Persistencia en el navegador mediante la Web Storage API ('localStorage').
// 3. Validación de formularios en el lado del cliente (Frontend).
// 4. Retroalimentación visual asíncrona con spinner de carga y modales de Bootstrap.
// 5. Operaciones de adición y eliminación de elementos en tiempo real.
// ==============================================================================

document.addEventListener("DOMContentLoaded", () => {
    function normalizarTexto(valor) {
        return (valor || "")
            .toString()
            .toLowerCase()
            .normalize("NFD")
            .replace(/[\u0300-\u036f]/g, "")
            .trim();
    }

    // Mantiene la misma respuesta visual en todos los formularios.
    document.querySelectorAll(".form-card form").forEach((formulario) => {
        formulario.querySelectorAll("input, select, textarea").forEach((campo) => {
            if (campo.type === "hidden") return;

            const actualizarEstado = () => {
                if (campo.classList.contains("is-invalid") && campo.value.trim()) {
                    campo.classList.remove("is-invalid");
                }
                if (campo.value.trim() && campo.checkValidity()) {
                    campo.classList.add("is-valid");
                } else {
                    campo.classList.remove("is-valid");
                }
            };

            campo.addEventListener("input", actualizarEstado);
            campo.addEventListener("change", actualizarEstado);
            campo.addEventListener("blur", actualizarEstado);
        });
    });

    // Filtro común para cualquier tabla que declare data-filter-target.
    document.querySelectorAll("[data-filter-target]").forEach((input) => {
        const selector = input.dataset.filterTarget;
        const filas = Array.from(document.querySelectorAll(selector));
        const contador = input.dataset.filterCount
            ? document.querySelector(input.dataset.filterCount)
            : null;
        if (!filas.length) return;

        const aplicarFiltro = () => {
            const consulta = normalizarTexto(input.value);
            let visibles = 0;

            filas.forEach((fila) => {
                const contenido = normalizarTexto(fila.textContent);
                const visible = !consulta || contenido.includes(consulta);
                fila.classList.toggle("d-none", !visible);
                if (visible) visibles += 1;
            });

            if (contador) contador.textContent = visibles;
        };

        input.addEventListener("input", aplicarFiltro);
        const limpiar = input.dataset.filterClear
            ? document.querySelector(input.dataset.filterClear)
            : null;
        if (limpiar) {
            limpiar.addEventListener("click", () => {
                input.value = "";
                aplicarFiltro();
                input.focus();
            });
        }
    });

    document.querySelectorAll('.password-toggle-btn').forEach((button) => {
        button.addEventListener('click', () => {
            const input = button.closest('.input-group')?.querySelector('.password-toggle');
            if (!input) return;

            const isPassword = input.type === 'password';
            input.type = isPassword ? 'text' : 'password';

            const icon = button.querySelector('i');
            if (icon) {
                icon.classList.toggle('bi-eye', isPassword);
                icon.classList.toggle('bi-eye-slash', !isPassword);
            }

            button.setAttribute('aria-label', isPassword ? 'Ocultar contraseña' : 'Mostrar contraseña');
            button.title = isPassword ? 'Ocultar contraseña' : 'Mostrar contraseña';
        });
    });

    const form2fa = document.getElementById("form2fa");
    if (form2fa) {
        const codigo2fa = document.getElementById("codigo");
        const feedback2fa = document.getElementById("feedback2fa");
        const advertencia2fa = document.getElementById("advertencia2fa");
        const mensaje2fa = document.getElementById("mensaje2fa");
        const modalElemento = document.getElementById("modalAdvertencia2fa");
        const detalleModal = document.getElementById("detalleAdvertencia2fa");
        const mostrarError2fa = (mensaje) => {
            codigo2fa.classList.add("is-invalid");
            codigo2fa.classList.remove("is-valid");
            feedback2fa.textContent = mensaje;
            advertencia2fa.classList.remove("d-none");
            advertencia2fa.classList.add("d-flex");
            mensaje2fa.textContent = mensaje;
            detalleModal.textContent = mensaje;
            if (window.bootstrap && modalElemento) {
                bootstrap.Modal.getOrCreateInstance(modalElemento).show();
            }
        };

        codigo2fa.addEventListener("input", () => {
            codigo2fa.value = codigo2fa.value.replace(/\D/g, "").slice(0, 6);
            const correcto = codigo2fa.value.length === 6;
            codigo2fa.classList.toggle("is-valid", correcto);
            codigo2fa.classList.toggle("is-invalid", !correcto && codigo2fa.value.length > 0);
            feedback2fa.textContent = correcto ? "" : "El código debe contener exactamente 6 dígitos.";
            if (correcto) {
                advertencia2fa.classList.add("d-none");
                advertencia2fa.classList.remove("d-flex");
            }
        });

        codigo2fa.addEventListener("blur", () => {
            if (!codigo2fa.value.trim()) {
                mostrarError2fa("Ingresa el código de 6 dígitos para continuar.");
            }
        });

        form2fa.addEventListener("submit", (evento) => {
            if (!/^\d{6}$/.test(codigo2fa.value.trim())) {
                evento.preventDefault();
                mostrarError2fa("El código debe contener exactamente 6 dígitos.");
                return;
            }

            const boton = document.getElementById("boton2fa");
            if (boton) {
                boton.disabled = true;
                boton.innerHTML = '<span class="spinner-border spinner-border-sm me-2" aria-hidden="true"></span>Verificando...';
            }
        });
    }

    document.querySelectorAll("#formPinRecuperacion input[name='pin']").forEach((campo) => {
        campo.addEventListener("input", () => {
            campo.value = campo.value.replace(/\D/g, "").slice(0, 6);
            campo.classList.toggle("is-valid", /^\d{6}$/.test(campo.value));
            campo.classList.toggle("is-invalid", campo.value.length > 0 && !/^\d{6}$/.test(campo.value));
        });
    });

    const registroForm = document.getElementById("registroForm");
    if (registroForm) {
        const advertencia = document.getElementById("registroAdvertencia");
        const listaAdvertencias = document.getElementById("registroAdvertenciaLista");
        const password = document.getElementById("password");
        const confirmPassword = document.getElementById("confirm_password");
        const confirmPasswordFeedback = document.getElementById("confirmPasswordFeedback");
        const submitButton = document.getElementById("registroSubmit");
        const mayorEdad = document.getElementById("mayor_edad");
        const aceptaTerminos = document.getElementById("acepta_terminos");
        const passwordStrengthBar = document.getElementById("passwordStrengthBar");
        const passwordStrengthText = document.getElementById("passwordStrengthText");
        const passwordRules = {
            length: document.getElementById("ruleLength"),
            upper: document.getElementById("ruleUpper"),
            lower: document.getElementById("ruleLower"),
            number: document.getElementById("ruleNumber"),
            symbol: document.getElementById("ruleSymbol")
        };
        const camposUnicos = [
            {
                campo: "usuario",
                input: document.getElementById("usuario"),
                feedback: document.getElementById("usuarioFeedback"),
                mensaje: "Este nombre de usuario ya está registrado."
            },
            {
                campo: "correo",
                input: document.getElementById("correo"),
                feedback: document.getElementById("correoFeedback"),
                mensaje: "Este correo electrónico ya está registrado."
            },
            {
                campo: "telefono",
                input: document.getElementById("telefono"),
                feedback: document.getElementById("telefonoFeedback"),
                mensaje: "Este número de celular ya está registrado."
            }
        ];
        const datosDuplicados = new Set();
        const nombres = document.getElementById("nombres");
        const apellidos = document.getElementById("apellidos");
        const telefono = document.getElementById("telefono");
        const validacionesTexto = [
            {
                input: nombres,
                feedback: document.getElementById("nombresFeedback"),
                mensaje: "Escribe al menos 4 letras. No uses números ni símbolos."
            },
            {
                input: apellidos,
                feedback: document.getElementById("apellidosFeedback"),
                mensaje: "Escribe al menos 4 letras. No uses números ni símbolos."
            }
        ];

        const mostrarAdvertencias = (mensajes) => {
            listaAdvertencias.innerHTML = "";
            mensajes.forEach((mensaje) => {
                const item = document.createElement("li");
                item.textContent = mensaje;
                listaAdvertencias.appendChild(item);
            });
            advertencia.classList.toggle("d-none", mensajes.length === 0);
            advertencia.classList.toggle("d-flex", mensajes.length > 0);
        };

        const revisarCampo = (campo) => {
            if (!campo) return;
            campo.classList.toggle("is-valid", campo.value.trim() && campo.checkValidity());
            campo.classList.toggle("is-invalid", !campo.checkValidity());
        };

        const revisarTexto = (item) => {
            if (!item.input) return false;
            const valor = item.input.value.trim();
            const valido = /^[A-Za-zÁÉÍÓÚáéíóúÑñ\s]{4,}$/.test(valor);
            item.input.classList.toggle("is-valid", valido);
            item.input.classList.toggle("is-invalid", !valido);
            item.feedback.textContent = valido ? "" : item.mensaje;
            return valido;
        };

        const revisarTelefono = () => {
            if (!telefono) return false;
            telefono.value = telefono.value.replace(/\D/g, "").slice(0, 10);
            const valido = /^\d{10}$/.test(telefono.value);
            telefono.classList.toggle("is-valid", valido);
            telefono.classList.toggle("is-invalid", !valido);
            return valido;
        };

        validacionesTexto.forEach((item) => {
            if (!item.input) return;
            item.input.addEventListener("input", () => revisarTexto(item));
            item.input.addEventListener("blur", () => revisarTexto(item));
        });
        if (telefono) {
            telefono.addEventListener("input", revisarTelefono);
            telefono.addEventListener("blur", revisarTelefono);
        }

        const actualizarReglasPassword = () => {
            if (!password) return false;
            const valor = password.value;
            const reglas = {
                length: valor.length >= 8,
                upper: /[A-Z]/.test(valor),
                lower: /[a-z]/.test(valor),
                number: /\d/.test(valor),
                symbol: /[^A-Za-z0-9]/.test(valor)
            };
            Object.entries(reglas).forEach(([nombre, cumple]) => {
                const regla = passwordRules[nombre];
                if (!regla) return;
                regla.classList.toggle("text-success", cumple);
                regla.classList.toggle("text-muted", !cumple);
                const icono = regla.querySelector("i");
                if (icono) {
                    icono.classList.toggle("bi-check-circle-fill", cumple);
                    icono.classList.toggle("bi-circle", !cumple);
                }
            });
            const puntos = Object.values(reglas).filter(Boolean).length;
            const porcentaje = puntos * 20;
            passwordStrengthBar.style.width = `${porcentaje}%`;
            passwordStrengthBar.setAttribute("aria-valuenow", porcentaje);
            passwordStrengthBar.className = `progress-bar ${puntos < 3 ? "bg-danger" : puntos < 5 ? "bg-warning" : "bg-success"}`;
            passwordStrengthText.textContent = puntos < 3 ? "Débil" : puntos < 5 ? "Media" : "Fuerte";
            passwordStrengthText.className = puntos < 3 ? "text-danger" : puntos < 5 ? "text-warning" : "text-success";
            return puntos === 5;
        };

        const revisarConfirmacion = () => {
            if (!confirmPassword) return false;
            const coincide = confirmPassword.value.length > 0 && confirmPassword.value === password.value;
            confirmPassword.classList.toggle("is-valid", coincide);
            confirmPassword.classList.toggle("is-invalid", !coincide);
            confirmPasswordFeedback.textContent = coincide ? "" : "Las contraseñas no coinciden.";
            return coincide;
        };

        [password, confirmPassword, mayorEdad, aceptaTerminos].forEach((campo) => {
            if (campo) {
                campo.addEventListener("input", () => {
                    revisarCampo(campo);
                    if (campo === password) actualizarReglasPassword();
                    if (campo === confirmPassword || campo === password) revisarConfirmacion();
                });
                campo.addEventListener("change", () => {
                    revisarCampo(campo);
                    if (campo === password) actualizarReglasPassword();
                    if (campo === confirmPassword || campo === password) revisarConfirmacion();
                });
            }
        });
        actualizarReglasPassword();
        if (confirmPassword && confirmPassword.value) revisarConfirmacion();

        const comprobarDisponibilidad = async (item) => {
            const valor = item.input.value.trim();
            if (!valor || !item.input.checkValidity()) return true;

            const parametros = new URLSearchParams({
                campo: item.campo,
                valor: valor
            });
            try {
                const respuesta = await fetch(`/registro/disponibilidad?${parametros.toString()}`, {
                    headers: { "X-Requested-With": "XMLHttpRequest" }
                });
                const resultado = await respuesta.json();
                item.input.classList.toggle("is-invalid", !resultado.disponible);
                item.input.classList.toggle("is-valid", resultado.disponible);
                item.feedback.textContent = resultado.disponible ? "" : (resultado.mensaje || item.mensaje);
                if (resultado.disponible) {
                    datosDuplicados.delete(item.campo);
                } else {
                    datosDuplicados.add(item.campo);
                }
                return resultado.disponible;
            } catch (error) {
                item.feedback.textContent = "No se pudo comprobar este dato. Inténtalo nuevamente.";
                item.input.classList.add("is-invalid");
                datosDuplicados.add(item.campo);
                return false;
            }
        };

        camposUnicos.forEach((item) => {
            if (!item.input) return;
            item.input.addEventListener("blur", () => {
                comprobarDisponibilidad(item);
            });
            item.input.addEventListener("input", () => {
                datosDuplicados.delete(item.campo);
                item.feedback.textContent = "";
            });
        });

        registroForm.addEventListener("submit", async (evento) => {
            evento.preventDefault();
            const mensajes = [];
            const campos = Array.from(registroForm.querySelectorAll("input, select"));

            campos.forEach((campo) => {
                if (campo.type !== "hidden") revisarCampo(campo);
            });

            if (!registroForm.checkValidity()) {
                mensajes.push("Completa correctamente todos los campos obligatorios.");
            }
            validacionesTexto.forEach((item) => {
                if (!revisarTexto(item)) mensajes.push(item.mensaje);
            });
            if (!revisarTelefono()) {
                mensajes.push("El teléfono debe contener exactamente 10 números.");
            }
            const disponibilidad = await Promise.all(
                camposUnicos.map((item) => comprobarDisponibilidad(item))
            );
            if (disponibilidad.includes(false)) {
                mensajes.push("Corrige los datos repetidos o no disponibles antes de continuar.");
            }
            if (password && !/^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^A-Za-z\d]).{8,}$/.test(password.value)) {
                mensajes.push("La contraseña debe incluir mayúscula, minúscula, número y símbolo.");
            }
            if (password && confirmPassword && password.value !== confirmPassword.value) {
                mensajes.push("Las contraseñas no coinciden.");
            }
            if (mayorEdad && !mayorEdad.checked) {
                mensajes.push("Debes confirmar que eres mayor de edad.");
            }
            if (aceptaTerminos && !aceptaTerminos.checked) {
                mensajes.push("Debes aceptar los términos y condiciones.");
            }

            if (mensajes.length) {
                mostrarAdvertencias(mensajes);
                const primerCampoInvalido = registroForm.querySelector(":invalid");
                if (primerCampoInvalido) primerCampoInvalido.focus();
                return;
            }

            mostrarAdvertencias([]);
            if (!window.confirm("Tus datos cumplen las validaciones del formulario. ¿Deseas continuar con el registro?")) {
                return;
            }
            if (submitButton) {
                submitButton.disabled = true;
                submitButton.innerHTML = '<span class="spinner-border spinner-border-sm me-2" aria-hidden="true"></span>Guardando información...';
            }
            registroForm.submit();
        });
    }

    // Validación uniforme para login, 2FA y formularios CRUD.
    document.querySelectorAll(".form-card form:not(#registroForm):not(#form2fa):not(#formSolicitud)").forEach((formulario) => {
        const campos = Array.from(formulario.querySelectorAll("input, select, textarea"))
            .filter((campo) => campo.type !== "hidden" && !campo.disabled);
        const boton = formulario.querySelector('button[type="submit"], input[type="submit"]');

        const actualizarCampo = (campo, mostrarVacio = false) => {
            const tieneValor = campo.type === "checkbox" ? campo.checked : campo.value.trim() !== "";
            const valido = campo.checkValidity() && (tieneValor || !campo.required);
            if (valido && (tieneValor || !campo.required)) {
                campo.classList.add("is-valid");
                campo.classList.remove("is-invalid");
            } else if (mostrarVacio || tieneValor) {
                campo.classList.add("is-invalid");
                campo.classList.remove("is-valid");
            }
        };

        campos.forEach((campo) => {
            campo.addEventListener("input", () => actualizarCampo(campo));
            campo.addEventListener("change", () => actualizarCampo(campo, true));
            campo.addEventListener("blur", () => actualizarCampo(campo, true));
        });

        formulario.addEventListener("submit", (evento) => {
            campos.forEach((campo) => actualizarCampo(campo, true));
            if (!formulario.checkValidity()) {
                evento.preventDefault();
                const primerCampoInvalido = campos.find((campo) => !campo.checkValidity());
                if (primerCampoInvalido) primerCampoInvalido.focus();
                return;
            }

            if (boton) {
                boton.disabled = true;
                if (boton.tagName === "BUTTON") {
                    boton.dataset.textoOriginal = boton.innerHTML;
                    boton.innerHTML = '<span class="spinner-border spinner-border-sm me-2" aria-hidden="true"></span>Guardando información...';
                } else {
                    boton.dataset.textoOriginal = boton.value;
                    boton.value = "Guardando información...";
                }
            }
        });
    });

    // Referencia al formulario de solicitudes
    const formulario = document.getElementById("formSolicitud");

    // Si el formulario no existe en la página actual, salir de forma segura
    if (!formulario) return;

    // Referencias a los elementos del DOM
    const nombreCliente = document.getElementById("nombreCliente");
    const correoSolicitud = document.getElementById("correoSolicitud");
    const telefonoSolicitud = document.getElementById("telefonoSolicitud");
    const tipoServicio = document.getElementById("tipoServicio");
    const descripcionSolicitud = document.getElementById("descripcionSolicitud");
    const listaSolicitudes = document.getElementById("listaSolicitudes");
    const totalSolicitudes = document.getElementById("totalSolicitudes");
    const spinner = document.getElementById("spinnerCarga");

    // Las solicitudes reales se guardan en PostgreSQL; esta lista solo se limpia
    // para no mostrar datos de demostración almacenados en navegadores antiguos.
    const solicitudes = [];

    // --------------------------------------------------------------------------
    // FUNCIONES DE VALIDACIÓN INDIVIDUAL DE CAMPOS
    // --------------------------------------------------------------------------

    /**
     * Valida que el nombre tenga más de 3 caracteres y solo texto.
     */
    function validarNombre() {
        if (!nombreCliente) return false;
        const valor = nombreCliente.value.trim();
        const patron = /^(?=.{4,150}$)[\p{L}]+(?:[ .'-][\p{L}]+)*$/u;

        if (!patron.test(valor)) {
            nombreCliente.classList.add("is-invalid");
            nombreCliente.classList.remove("is-valid");
            return false;
        } else {
            nombreCliente.classList.add("is-valid");
            nombreCliente.classList.remove("is-invalid");
            return true;
        }
    }

    /**
     * Valida que se haya seleccionado un tipo de servicio de la lista desplegable.
     */
    function validarServicio() {
        if (!tipoServicio) return false;
        const valor = tipoServicio.value;

        if (valor === "") {
            tipoServicio.classList.add("is-invalid");
            tipoServicio.classList.remove("is-valid");
            return false;
        } else {
            tipoServicio.classList.add("is-valid");
            tipoServicio.classList.remove("is-invalid");
            return true;
        }
    }

    /**
     * Valida que la descripción contenga al menos 10 caracteres explicativos.
     */
    function validarDescripcion() {
        if (!descripcionSolicitud) return false;
        const valor = descripcionSolicitud.value.trim();

        if (valor.length < 10) {
            descripcionSolicitud.classList.add("is-invalid");
            descripcionSolicitud.classList.remove("is-valid");
            return false;
        } else {
            descripcionSolicitud.classList.add("is-valid");
            descripcionSolicitud.classList.remove("is-invalid");
            return true;
        }
    }

    function normalizarTelefono() {
        if (!telefonoSolicitud) return "";
        telefonoSolicitud.value = telefonoSolicitud.value.replace(/\D/g, "").slice(0, 10);
        return telefonoSolicitud.value;
    }

    function validarCorreo() {
        if (!correoSolicitud) return false;
        const valor = correoSolicitud.value.trim().toLowerCase();
        correoSolicitud.value = valor;
        const valido = valor.length <= 150
            && /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(valor);
        correoSolicitud.classList.toggle("is-valid", valido);
        correoSolicitud.classList.toggle("is-invalid", !valido);
        return valido;
    }

    function validarTelefono() {
        const valor = normalizarTelefono();
        const valido = valor === "" || /^\d{10}$/.test(valor);
        if (telefonoSolicitud) {
            telefonoSolicitud.classList.toggle("is-valid", valido && valor !== "");
            telefonoSolicitud.classList.toggle("is-invalid", !valido);
        }
        return valido;
    }

    // --------------------------------------------------------------------------
    // ESCUCHADORES DE EVENTOS DE VALIDACIÓN ('input', 'change', 'blur')
    // --------------------------------------------------------------------------
    if (nombreCliente) {
        nombreCliente.addEventListener("input", validarNombre);
        nombreCliente.addEventListener("blur", validarNombre);
    }

    if (tipoServicio) {
        tipoServicio.addEventListener("change", validarServicio);
        tipoServicio.addEventListener("blur", validarServicio);
    }

    if (descripcionSolicitud) {
        descripcionSolicitud.addEventListener("input", validarDescripcion);
        descripcionSolicitud.addEventListener("blur", validarDescripcion);
    }
    if (correoSolicitud) {
        correoSolicitud.addEventListener("input", validarCorreo);
        correoSolicitud.addEventListener("blur", validarCorreo);
    }
    if (telefonoSolicitud) {
        telefonoSolicitud.addEventListener("input", validarTelefono);
        telefonoSolicitud.addEventListener("blur", validarTelefono);
    }

    // --------------------------------------------------------------------------
    // RENDERIZADO DE LAS TARJETAS DE SOLICITUDES EN EL DOM
    // --------------------------------------------------------------------------
    /**
     * Limpia y vuelve a generar los elementos visuales de las solicitudes activas.
     */
    window.mostrarSolicitudes = function () {
        if (!listaSolicitudes || !totalSolicitudes) return;

        // Limpiar el contenedor
        listaSolicitudes.innerHTML = "";

        // Si no hay solicitudes, mostrar estado vacío
        if (solicitudes.length === 0) {
            listaSolicitudes.innerHTML = `
                <div class="col-12">
                    <div class="card p-4 text-center border-0 bg-light rounded-4">
                        <i class="bi bi-inbox text-muted fs-1 mb-2"></i>
                        <p class="text-muted mb-0">No hay solicitudes registradas en este momento.</p>
                    </div>
                </div>
            `;
            totalSolicitudes.textContent = "0";
            return;
        }

        // Iterar y crear cada tarjeta de solicitud
        solicitudes.forEach((sol, index) => {
            const columna = document.createElement("div");
            columna.className = "col-md-6 col-lg-4";

            columna.innerHTML = `
                <div class="card h-100 shadow-sm border-0 rounded-4 overflow-hidden">
                    <div class="card-body p-4 d-flex flex-column">
                        <div class="d-flex justify-content-between align-items-start mb-2">
                            <span class="badge bg-emerald-subtle text-emerald fw-semibold px-2 py-1 small rounded-pill">
                                <i class="bi bi-tag-fill me-1"></i>${sol.servicio}
                            </span>
                            <button type="button" class="btn btn-outline-danger btn-sm rounded-circle" style="width: 32px; height: 32px; padding: 0;" title="Eliminar solicitud" onclick="eliminarSolicitud(${index})">
                                <i class="bi bi-trash-fill"></i>
                            </button>
                        </div>
                        <h5 class="card-title fw-bold text-navy mb-2">${sol.nombre}</h5>
                        <p class="card-text text-muted small flex-grow-1 mb-3">${sol.descripcion}</p>
                        <div class="pt-2 border-top d-flex justify-content-between align-items-center">
                            <small class="text-muted"><i class="bi bi-clock-history me-1"></i>Registrado</small>
                            <span class="badge bg-navy text-white small px-2 py-1">En revisión</span>
                        </div>
                    </div>
                </div>
            `;

            listaSolicitudes.appendChild(columna);
        });

        // Actualizar el contador total en el encabezado
        totalSolicitudes.textContent = solicitudes.length.toString();
    };

    // --------------------------------------------------------------------------
    // FUNCIÓN PARA ELIMINAR UNA SOLICITUD
    // --------------------------------------------------------------------------
    /**
     * La eliminación de solicitudes está reservada al gestor en la vista operativa.
     */
    window.eliminarSolicitud = function (index) {
        if (confirm("¿Estás seguro de que deseas eliminar esta solicitud?")) {
            mostrarSolicitudes();
        }
    };

    // --------------------------------------------------------------------------
    // PROCESAMIENTO DEL ENVÍO DEL FORMULARIO DE SOLICITUD
    // --------------------------------------------------------------------------
    formulario.addEventListener("submit", function (e) {
        e.preventDefault();

        const nombreValido = validarNombre();
        const servicioValido = validarServicio();
        const descripcionValida = validarDescripcion();
        const correoValido = validarCorreo();
        const telefonoValido = validarTelefono();

        // Si algún campo no es válido, indicar exactamente qué debe corregirse.
        if (!nombreValido || !servicioValido || !descripcionValida || !correoValido || !telefonoValido) {
            const mensajes = [];
            if (!nombreValido) mensajes.push("El nombre debe tener mínimo 4 letras y solo texto.");
            if (!correoValido) mensajes.push("Escribe un correo electrónico válido.");
            if (!telefonoValido) mensajes.push("El teléfono debe tener exactamente 10 números o quedar vacío.");
            if (!servicioValido) mensajes.push("Selecciona un tipo de servicio.");
            if (!descripcionValida) mensajes.push("La descripción debe tener mínimo 10 caracteres.");
            const errorMensaje = document.getElementById("solicitudErrorMensaje");
            if (errorMensaje) {
                errorMensaje.textContent = `Revisa: ${mensajes.join(" ")}`;
            }
            const errorModalEl = document.getElementById("solicitudErrorModal");
            if (errorModalEl && typeof bootstrap !== "undefined") {
                bootstrap.Modal.getOrCreateInstance(errorModalEl).show();
            }
            const primerCampoInvalido = [
                [nombreCliente, nombreValido],
                [correoSolicitud, correoValido],
                [telefonoSolicitud, telefonoValido],
                [tipoServicio, servicioValido],
                [descripcionSolicitud, descripcionValida]
            ].find(([, valido]) => !valido);
            if (primerCampoInvalido && primerCampoInvalido[0]) {
                primerCampoInvalido[0].focus();
            }
            return;
        }

        if (spinner) spinner.classList.remove("d-none");
        fetch("/api/solicitudes", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({
                nombre: nombreCliente.value.trim(),
                correo: correoSolicitud.value.trim(),
                telefono: normalizarTelefono(),
                tipo_servicio: tipoServicio.value.trim(),
                mensaje: descripcionSolicitud.value.trim()
            })
        })
            .then(respuesta => respuesta.json().then(datos => ({ok: respuesta.ok, datos})))
            .then(resultado => {
                if (!resultado.ok) throw new Error(resultado.datos.mensaje || "No se pudo guardar la petición.");
                const successModalEl = document.getElementById("solicitudSuccessModal");
                if (successModalEl && typeof bootstrap !== "undefined") {
                    bootstrap.Modal.getOrCreateInstance(successModalEl).show();
                }
                formulario.reset();
                mostrarSolicitudes();
            })
            .catch(error => {
                console.error(error);
                const errorMensaje = document.getElementById("solicitudErrorMensaje");
                if (errorMensaje) errorMensaje.textContent = error.message;
                const errorModalEl = document.getElementById("solicitudErrorModal");
                if (errorModalEl && typeof bootstrap !== "undefined") {
                    bootstrap.Modal.getOrCreateInstance(errorModalEl).show();
                }
            })
            .finally(() => {
                if (spinner) spinner.classList.add("d-none");
            });
    });

    // Renderizar solicitudes iniciales al cargar la página
    mostrarSolicitudes();
});
