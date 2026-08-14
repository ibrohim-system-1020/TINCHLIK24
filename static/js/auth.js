document.addEventListener("DOMContentLoaded", function () {
  const overlay = document.getElementById("authOverlay");
  const closeAuth = document.getElementById("closeAuth");
  const tabs = document.querySelectorAll(".auth-tab");
  const registerForm = document.getElementById("registerForm");
  const loginForm = document.getElementById("loginForm");
  const telegramVerification = document.getElementById("telegramVerification");
  const telegramRegister = document.getElementById("telegramRegister");
  const sendTelegramCode = document.getElementById("sendTelegramCode");
  const verifyTelegramCode = document.getElementById("verifyTelegramCode");

  function openRegister() {
    if (!overlay || !registerForm || !loginForm) return;

    overlay.classList.add("active");
    registerForm.classList.add("active");
    loginForm.classList.remove("active");
    telegramVerification?.classList.remove("active");
    tabs[0]?.classList.add("active");
    tabs[1]?.classList.remove("active");
    document.body.style.overflow = "hidden";
  }

  function openLogin() {
    if (!overlay || !registerForm || !loginForm) return;

    overlay.classList.add("active");
    registerForm.classList.remove("active");
    loginForm.classList.add("active");
    telegramVerification?.classList.remove("active");
    tabs[0]?.classList.remove("active");
    tabs[1]?.classList.add("active");
    document.body.style.overflow = "hidden";
  }

  function closeModal() {
    overlay?.classList.remove("active");
    document.body.style.overflow = "";
    if (window.location.pathname !== "/") {
      window.history.pushState({}, "", "/");
    }
  }

  if (closeAuth) {
    closeAuth.addEventListener("click", closeModal);
  }

  if (overlay) {
    overlay.addEventListener("click", function (e) {
      if (e.target === overlay) {
        closeModal();
      }
    });
  }

  tabs.forEach((tab) => {
    tab.addEventListener("click", function () {
      if (this.dataset.tab === "login") {
        openLogin();
      } else {
        openRegister();
      }
    });
  });

  if (telegramRegister) {
    telegramRegister.addEventListener("click", function () {
      registerForm?.classList.remove("active");
      loginForm?.classList.remove("active");
      telegramVerification?.classList.add("active");
    });
  }

  if (sendTelegramCode) {
    sendTelegramCode.addEventListener("click", function () {
      const phone = document.getElementById("telegramPhone")?.value;
      if (!phone) {
        alert("Telefon raqamingizni kiriting!");
        return;
      }
      alert("Tasdiqlash kodi Telegram orqali yuboriladi.");
    });
  }

  if (verifyTelegramCode) {
    verifyTelegramCode.addEventListener("click", function () {
      const code = document.getElementById("telegramCode")?.value;
      if (!code || code.length !== 6) {
        alert("6 xonali tasdiqlash kodini kiriting!");
      }
    });
  }

  window.showPassword = function (id) {
    const input = document.getElementById(id);
    if (!input) return;
    input.type = input.type === "password" ? "text" : "password";
  };

  window.addEventListener("DOMContentLoaded", function () {
    const path = window.location.pathname;
    const params = new URLSearchParams(window.location.search);

    if (path === "/register/" || path === "/register") {
      if (params.get("tab") === "login") {
        openLogin();
      } else {
        openRegister();
      }
    }
  });

  window.addEventListener("popstate", function () {
    if (window.location.pathname === "/register/" || window.location.pathname === "/register") {
      openRegister();
    } else {
      overlay?.classList.remove("active");
      document.body.style.overflow = "";
    }
  });
});
