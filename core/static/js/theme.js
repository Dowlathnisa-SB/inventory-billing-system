(function () {
    function getPreferredTheme() {
        var savedTheme = localStorage.getItem("inventory-theme");
        if (savedTheme === "light" || savedTheme === "dark") {
            return savedTheme;
        }
        return window.matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark";
    }

    function applyTheme(theme) {
        document.documentElement.setAttribute("data-theme", theme);
        var toggles = document.querySelectorAll("[data-theme-toggle]");
        toggles.forEach(function (toggle) {
            toggle.textContent = theme === "dark" ? "Switch to light" : "Switch to dark";
        });
    }

    function toggleTheme() {
        var nextTheme = document.documentElement.getAttribute("data-theme") === "dark" ? "light" : "dark";
        localStorage.setItem("inventory-theme", nextTheme);
        applyTheme(nextTheme);
    }

    applyTheme(getPreferredTheme());

    document.addEventListener("DOMContentLoaded", function () {
        applyTheme(getPreferredTheme());
        document.querySelectorAll("[data-theme-toggle]").forEach(function (toggle) {
            toggle.addEventListener("click", toggleTheme);
        });
    });
})();
