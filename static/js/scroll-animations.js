(function () {
  if (typeof window.anime === 'undefined') return;

  const prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  function parseTarget(text) {
    const t = String(text).trim();
    let numeric = 0;
    let suffix = '';
    if (t.indexOf('/') !== -1) {
      const parts = t.split('/');
      numeric = parseFloat(parts[0].replace(/[^\d.]/g, '')) || 0;
      suffix = '/' + (parts[1] || '');
      return { numeric: numeric, suffix: suffix, raw: t };
    }
    if (/[kK]$/.test(t)) {
      numeric = parseFloat(t.replace(/[kK]|[^\d.]/g, '')) || 0;
      numeric = Math.round(numeric * 1000);
      suffix = 'k';
      return { numeric: numeric, suffix: suffix, raw: t };
    }
    if (/\+$/.test(t)) {
      numeric = parseFloat(t.replace(/[^\d.]/g, '')) || 0;
      suffix = '+';
      return { numeric: numeric, suffix: suffix, raw: t };
    }
    if (/\%$/.test(t)) {
      numeric = parseFloat(t.replace(/[^\d.]/g, '')) || 0;
      suffix = '%';
      return { numeric: numeric, suffix: suffix, raw: t };
    }
    numeric = parseFloat(t.replace(/[^\d.]/g, '')) || 0;
    return { numeric: numeric, suffix: '', raw: t };
  }

  function formatValue(n, suffix, raw) {
    if (suffix === 'k') {
      return Math.round(n / 1000) + 'k';
    }
    if (suffix === '+') {
      return Math.round(n) + '+';
    }
    if (suffix === '%') {
      return Math.round(n) + '%';
    }
    if (suffix && suffix[0] === '/') {
      return Math.round(n) + suffix;
    }
    return String(Math.round(n));
  }

  // COUNTERS: stats-strip
  const stats = document.querySelector('.stats-strip');
  if (stats) {
    const statItems = Array.from(stats.querySelectorAll('.stat-item'));

    const startCounters = function () {
      // animate cards in with stagger
      anime({
        targets: '.stats-strip .stat-item',
        translateY: [20, 0],
        opacity: [0, 1],
        easing: 'easeOutCubic',
        duration: 650,
        delay: anime.stagger(70)
      });

      statItems.forEach(function (item, i) {
        const strong = item.querySelector('strong');
        if (!strong) return;
        if (strong.dataset.animated) return;
        strong.dataset.animated = '1';

        const orig = strong.textContent.trim();
        const parsed = parseTarget(orig);

        if (prefersReduced) {
          strong.textContent = orig; // show final state immediately
          return;
        }

        const target = parsed.numeric;
        if (!isFinite(target) || target <= 0) {
          // nothing to animate
          strong.textContent = orig;
          return;
        }

        // build keyframe steps for a "fast digital" feel
        const phases = [0.12, 0.38, 0.66, 0.9, 1];
        const durations = [100, 220, 240, 200, 140]; // sum ~900
        const keyframes = phases.map(function (p, idx) {
          return { value: Math.round(target * p), duration: durations[idx] };
        });

        const obj = { value: 0 };

        anime({
          targets: obj,
          keyframes: keyframes,
          easing: 'easeOutExpo',
          round: 1,
          update: function () {
            // update displayed text according to suffix
            strong.textContent = formatValue(obj.value, parsed.suffix, orig);
          },
          complete: function () {
            // ensure exact final
            strong.textContent = orig;
          }
        });
      });
    };

    const observer = new IntersectionObserver(function (entries, obs) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting && entry.intersectionRatio > 0.3) {
          startCounters();
          obs.unobserve(entry.target);
        }
      });
    }, { threshold: [0.3] });

    observer.observe(stats);
  }

  // REVEAL: generic section reveals
  const revealSelectors = [
    '.hero-copy',
    '.hero-visual',
    '.section-heading',
    '.const-box-small',
    '.const-box-big',
    '.update-card',
    '.mini-panel',
    '.community-copy',
    '.visual-window',
    '.preview-panel-main',
    '.consider',
    '.dashboard-main',
    '.cta-inner'
  ];

  const revealElements = [];
  revealSelectors.forEach(function (sel) {
    document.querySelectorAll(sel).forEach(function (el) { revealElements.push(el); });
  });

  if (revealElements.length) {
    const revealObserver = new IntersectionObserver(function (entries, obs) {
      entries.forEach(function (entry) {
        const el = entry.target;
        if (entry.isIntersecting && entry.intersectionRatio > 0.18) {
          if (el.dataset.revealed) {
            obs.unobserve(el);
            return;
          }
          el.dataset.revealed = '1';

          // small direction tweaks for hero copy / visual
          const isHeroCopy = el.classList.contains('hero-copy');
          const isHeroVisual = el.classList.contains('hero-visual') || el.classList.contains('visual-window');

          if (prefersReduced) {
            el.style.opacity = 1;
            el.style.transform = 'none';
            obs.unobserve(el);
            return;
          }

          anime({
            targets: el,
            opacity: [0, 1],
            translateX: isHeroCopy ? [-18, 0] : isHeroVisual ? [18, 0] : undefined,
            translateY: !isHeroCopy && !isHeroVisual ? [18, 0] : undefined,
            easing: 'easeOutCubic',
            duration: 700,
            // small stagger per element in group
            delay: function (t, i) { return 0; }
          });

          obs.unobserve(el);
        }
      });
    }, { threshold: [0.18] });

    revealElements.forEach(function (el) { revealObserver.observe(el); });
  }

  // HERO initial timeline (one-time)
  (function heroIntro() {
    const hero = document.querySelector('.hero');
    if (!hero) return;
    const badge = hero.querySelector('.eyebrow');
    const h1 = hero.querySelector('h1');
    const p = hero.querySelector('p');
    const actions = hero.querySelector('.hero-actions');
    const visual = hero.querySelector('.hero-visual');

    if (prefersReduced) {
      [badge, h1, p, actions, visual].forEach(function (el) { if (el) { el.style.opacity = 1; el.style.transform = 'none'; } });
      return;
    }

    const tl = anime.timeline({ autoplay: true });
    if (badge) tl.add({ targets: badge, opacity: [0, 1], translateY: [-8, 0], duration: 320, easing: 'easeOutCubic' });
    if (h1) tl.add({ targets: h1, opacity: [0, 1], translateY: [-12, 0], duration: 420, easing: 'easeOutCubic' }, '-=200');
    if (p) tl.add({ targets: p, opacity: [0, 1], translateY: [-10, 0], duration: 420, easing: 'easeOutCubic' }, '-=320');
    if (actions) tl.add({ targets: actions, opacity: [0, 1], translateY: [-8, 0], duration: 360, easing: 'easeOutCubic' }, '-=280');
    if (visual) tl.add({ targets: visual, opacity: [0, 1], translateX: [12, 0], duration: 640, easing: 'easeOutExpo' }, '-=520');
  })();

})();
