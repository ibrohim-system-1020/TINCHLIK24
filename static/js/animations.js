(function () {
  if (typeof window.gsap === "undefined") return;

  const showPageIntro = function () {
    if (document.querySelector(".logo")) {
      const logo = document.querySelector(".logo");
      const letters = logo.textContent.trim().split("");
      logo.innerHTML = letters.map((letter) => `<span>${letter}</span>`).join("");
      const spans = logo.querySelectorAll("span");
      gsap.from(spans, {
        y: -40,
        opacity: 0,
        rotation: -15,
        duration: 0.9,
        ease: "bounce.out",
        stagger: 0.08,
      });
    }

    if (document.querySelectorAll(".list li").length) {
      gsap.from(".list li", {
        y: -40,
        opacity: 0,
        scale: 0.93,
        duration: 0.8,
        ease: "power3.out",
        stagger: 0.12,
        delay: 0.1,
      });
    }

    if (document.querySelectorAll(".const-box-small, .const-box-big").length) {
      gsap.from(".const-box-small, .const-box-big", {
        y: 30,
        opacity: 0,
        duration: 0.8,
        ease: "power3.out",
        stagger: 0.08,
      });
    }

    if (document.querySelector(".auth-modal")) {
      gsap.from(".auth-modal", {
        opacity: 0,
        y: 20,
        duration: 0.65,
        ease: "power2.out",
      });
    }

    if (document.querySelector(".profile-shell") || document.querySelector(".security-shell")) {
      gsap.from(
        ".profile-shell, .security-shell",
        {
          opacity: 0,
          y: 30,
          duration: 0.75,
          ease: "power2.out",
          stagger: 0.08,
        },
      );
    }

    if (document.querySelector(".telegram-card")) {
      gsap.from(".telegram-card", {
        opacity: 0,
        scale: 0.96,
        duration: 0.7,
        ease: "back.out(1.2)",
      });
    }
  };

  window.addEventListener("DOMContentLoaded", showPageIntro);
})();
