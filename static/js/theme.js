(function () {
  const toggle = document.getElementById("themeToggle");
  if (!toggle) return;

  const savedTheme = localStorage.getItem("theme");
  const activeTheme = savedTheme || "dark";

  function applyTheme(theme) {
    document.documentElement.dataset.theme = theme;
    toggle.innerHTML = theme === "dark"
      ? '<i class="fa-regular fa-sun" aria-hidden="true"></i>'
      : '<i class="fa-regular fa-moon" aria-hidden="true"></i>';
    toggle.setAttribute(
      "aria-label",
      theme === "dark" ? "Yorug‘ mavzuni yoqish" : "Qorong‘i mavzuni yoqish",
    );
    localStorage.setItem("theme", theme);
  }

  toggle.addEventListener("click", function () {
    const currentTheme = document.documentElement.dataset.theme || activeTheme;
    applyTheme(currentTheme === "dark" ? "light" : "dark");
  });

  applyTheme(activeTheme);
})();
