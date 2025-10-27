// Modal para previsualización de imágenes
const modal = document.getElementById("imagenModal");
const modalImg = document.getElementById("imagenGrande");
const descripcionModal = document.getElementById("descripcionModal");
const cerrar = document.getElementsByClassName("cerrar")[0];

// Abre el modal al hacer clic en una imagen
document.querySelectorAll(".producto-imagen").forEach((img) => {
    img.addEventListener("click", (e) => {
        modal.style.display = "block";
        modalImg.src = e.target.src;
        descripcionModal.innerHTML = e.target.alt;
    });
});

// Cierra el modal
cerrar.onclick = () => {
    modal.style.display = "none";
};

window.onclick = (event) => {
    if (event.target === modal) {
        modal.style.display = "none";
    }
};
