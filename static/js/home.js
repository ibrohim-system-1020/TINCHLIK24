const items = document.querySelectorAll(".list li");
const navToggles = document.querySelectorAll("[data-nav-toggle]");
const navPanels = document.querySelectorAll(".nav-panel");
const audioContext = window.AudioContext || window.webkitAudioContext;

function playUISound(index) {
  if (!audioContext) return;

  const context = new audioContext();
  const osc = context.createOscillator();
  const gain = context.createGain();

  osc.connect(gain);
  gain.connect(context.destination);

  osc.frequency.value = 520 + index * 80;
  osc.type = "sine";

  gain.gain.setValueAtTime(0.08, context.currentTime);
  gain.gain.exponentialRampToValueAtTime(0.001, context.currentTime + 0.12);

  osc.start();
  osc.stop(context.currentTime + 0.12);
}

function animateNavItems() {
  if (!window.gsap) return;
  if (items.length === 0) return;

  window.gsap.from(items, {
    y: -28,
    opacity: 0,
    scale: 0.95,
    duration: 0.75,
    ease: "power3.out",
    stagger: 0.12,
    onComplete: () => {
      items.forEach((item, index) => {
        if (index === 0) return;
        playUISound(index);
      });
    },
  });
}

document.addEventListener("click", function () {
  if (!audioContext) return animateNavItems();

  const context = new audioContext();
  context.resume().then(animateNavItems).catch(() => animateNavItems());
}, { once: true });

const links = document.querySelectorAll(".list li a");
links.forEach((link) => {
  link.addEventListener("mouseenter", () => {
    if (!window.gsap) return;
    window.gsap.to(link, { y: -4, scale: 1.05, duration: 0.18, ease: "power2.out" });
  });
  link.addEventListener("mouseleave", () => {
    if (!window.gsap) return;
    window.gsap.to(link, { y: 0, scale: 1, duration: 0.18, ease: "power2.out" });
  });
});

navToggles.forEach((toggle) => {
  toggle.addEventListener("click", () => {
    const nav = toggle.closest(".bar");
    if (!nav) return;

    const panel = nav.querySelector(".nav-panel");
    if (!panel) return;

    const isOpen = panel.classList.toggle("is-open");
    toggle.setAttribute("aria-expanded", String(isOpen));
    nav.classList.toggle("menu-open", isOpen);
  });
});

navPanels.forEach((panel) => {
  panel.querySelectorAll("a").forEach((link) => {
    link.addEventListener("click", () => {
      const nav = panel.closest(".bar");
      const toggle = nav ? nav.querySelector("[data-nav-toggle]") : null;
      if (toggle) {
        panel.classList.remove("is-open");
        nav.classList.remove("menu-open");
        toggle.setAttribute("aria-expanded", "false");
      }
    });
  });
});

