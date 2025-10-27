$(document).ready(function () {
    $(".owl-carousel").owlCarousel({
        loop: true,
        margin: 10,
        nav: false,
        items: 1,
    });

    $("#prevSlide").click(function () {
        $(".owl-carousel").trigger("prev.owl.carousel");
    });

    $("#nextSlide").click(function () {
        $(".owl-carousel").trigger("next.owl.carousel");
    });
});
