const { animate, stagger } = anime;

const logo = document.querySelector(".logo");

// TINCHLIK harflarini spanlarga ajratamiz
logo.innerHTML = logo.textContent
    .split("")
    .map(letter => `<span>${letter}</span>`)
    .join("");

const chars = document.querySelectorAll(".logo span");

animate(chars, {
    y: {
        from: -50
    },

    opacity: {
        from: 0
    },

    rotate: {
        from: "-20deg"
    },

    duration: 900,

    delay: stagger(100),

    ease: "outBounce"
});

import { animate } from "https://esm.sh/animejs";

const items = document.querySelectorAll(".list li");

const audioContext = new AudioContext();

function playUISound(index) {
    const osc = audioContext.createOscillator();
    const gain = audioContext.createGain();

    osc.connect(gain);
    gain.connect(audioContext.destination);

    // Har bir elementga biroz boshqa UI sound
    osc.frequency.value = 550 + index * 100;
    osc.type = "sine";

    gain.gain.setValueAtTime(
        0.08,
        audioContext.currentTime
    );

    gain.gain.exponentialRampToValueAtTime(
        0.001,
        audioContext.currentTime + 0.10
    );

    osc.start();
    osc.stop(audioContext.currentTime + 0.10);
}

async function animateMenu() {
    await audioContext.resume();

    for (let i = 0; i < items.length; i++) {

        await new Promise((resolve) => {

            animate(items[i], {
                y: [-80, 0],
                opacity: [0, 1],
                scale: [0.8, 1],

                duration: 650,
                ease: "outExpo",

                onComplete: () => {
                    playUISound(i);

                    setTimeout(resolve, 150);
                }
            });

        });

    }
}

// Birinchi clickdan keyin boshlaydi,
// chunki browser avtomatik soundni bloklaydi
document.addEventListener(
    "click",
    animateMenu,
    { once: true }
);

