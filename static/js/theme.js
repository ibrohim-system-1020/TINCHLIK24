(function () {
  const toggle = document.getElementById("themeToggle");
  if (!toggle) return;

  const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
  const savedTheme = localStorage.getItem("theme");
  const activeTheme = savedTheme || (prefersDark ? "dark" : "light");

  function applyTheme(theme) {
    document.documentElement.dataset.theme = theme;
    toggle.textContent = theme === "dark" ? "☀️" : "🌙";
    toggle.setAttribute(
      "aria-label",
      theme === "dark" ? "Switch to light theme" : "Switch to dark theme",
    );
    localStorage.setItem("theme", theme);
  }

  toggle.addEventListener("click", function () {
    const currentTheme = document.documentElement.dataset.theme || activeTheme;
    applyTheme(currentTheme === "dark" ? "light" : "dark");
  });

  applyTheme(activeTheme);
})();
