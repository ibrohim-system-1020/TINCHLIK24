const items = document.querySelectorAll(".list li");
const audioContext = new AudioContext();

function playUISound(index) {
  const osc = audioContext.createOscillator();
  const gain = audioContext.createGain();

  osc.connect(gain);
  gain.connect(audioContext.destination);

  osc.frequency.value = 520 + index * 80;
  osc.type = "sine";

  gain.gain.setValueAtTime(0.08, audioContext.currentTime);
  gain.gain.exponentialRampToValueAtTime(0.001, audioContext.currentTime + 0.12);

  osc.start();
  osc.stop(audioContext.currentTime + 0.12);
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
  audioContext.resume().then(animateNavItems).catch(() => animateNavItems());
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

