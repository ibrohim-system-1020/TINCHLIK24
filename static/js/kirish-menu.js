document.addEventListener("DOMContentLoaded", function () {
    var toggleBtn = document.querySelector(".register");
    var menu = document.querySelector(".kirish-menu");
    if (!toggleBtn || !menu) return;

    toggleBtn.addEventListener("click", function (e) {
        e.preventDefault();
        menu.classList.toggle("open");
    });

    document.addEventListener("click", function (e) {
        if (!menu.contains(e.target) && e.target !== toggleBtn) {
            menu.classList.remove("open");
        }
    });
});