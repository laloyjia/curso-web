// 1. Seleccionamos el botón por su ID
const boton = document.getElementById('boton-modo');

// 2. Escuchamos el evento 'click'
boton.addEventListener('click', function() {
    
    // 3. Modificamos el BODY agregando/quitando la clase
    document.body.classList.toggle('modo-oscuro');

    // Opcional: Cambiar el texto del botón
    if (document.body.classList.contains('modo-oscuro')) {
        boton.textContent = '☀️ Modo Claro';
    } else {
        boton.textContent = '🌙 Modo Oscuro';
    }
});

// Manejo del formulario
const formulario = document.getElementById('form-contacto');

formulario.addEventListener('submit', function(evento) {
    // 1. IMPORTANTE: Prevenir que la página se recargue
    evento.preventDefault();
    
    // 2. Aquí iría el código para enviar los datos a un servidor real
    
    // 3. Feedback al usuario
    alert('Gracias por tu mensaje. Nos pondremos en contacto pronto.');
    
    // 4. Limpiar los campos
    formulario.reset();
});
// 1. Seleccionamos los elementos
const contenedorUsuario = document.getElementById('usuario-tarjeta');
const botonUsuario = document.getElementById('btn-cargar-usuario');

// 2. Función para pedir los datos a la API
async function obtenerUsuario() {
    try {
        contenedorUsuario.innerHTML = "<p>Buscando datos...</p>"; // Feedback visual

        // EL MESERO SALE A BUSCAR:
        // Hacemos la petición a la URL de la API
        const respuesta = await fetch('https://randomuser.me/api/');
        
        // EL MESERO VUELVE CON LOS DATOS (en formato JSON):
        const datos = await respuesta.json();
        
        // Sacamos la info que nos interesa (el primer resultado)
        const usuario = datos.results[0];

        // 3. Pintamos la info en el HTML
        contenedorUsuario.innerHTML = `
            <img src="${usuario.picture.large}" alt="Foto de usuario">
            <h3>${usuario.name.first} ${usuario.name.last}</h3>
            <p>📧 ${usuario.email}</p>
            <p>📍 ${usuario.location.city}, ${usuario.location.country}</p>
        `;

    } catch (error) {
        // Si algo falla (ej: sin internet)
        console.error(error);
        contenedorUsuario.innerHTML = "<p>❌ Error al cargar usuario.</p>";
    }
}

// 4. Agregamos el evento al botón
botonUsuario.addEventListener('click', obtenerUsuario);

// 5. Cargar uno automáticamente al entrar a la página
obtenerUsuario();