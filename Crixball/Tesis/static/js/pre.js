    // Función para abrir el modal de previsualización
    function openImagePreview(imgSrc) {
        const modal = document.getElementById('imageModal');
        const modalImg = document.getElementById('modalImage');
        modal.style.display = "flex";  // Usamos flex para centrar la imagen
        modalImg.src = imgSrc;  // Establecemos la fuente de la imagen en el modal
    }
    
    // Función para cerrar el modal
    document.querySelector('.close-modal').onclick = function() {
        document.getElementById('imageModal').style.display = "none";
    }
    
    // Cerrar modal al hacer clic fuera de la imagen
    window.onclick = function(event) {
        const modal = document.getElementById('imageModal');
        if (event.target == modal) {
            modal.style.display = "none";
        }
    }