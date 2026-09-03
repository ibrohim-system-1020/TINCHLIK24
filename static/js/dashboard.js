(function () {
  function qs(sel, root = document) {
    return root.querySelector(sel);
  }

  function qsa(sel, root = document) {
    return Array.from(root.querySelectorAll(sel));
  }

  const avatarBtn = qs('.avatar-button');
  const dropdown = qs('.profile-dropdown');
  const hamburger = qs('.hamburger');
  const mobilePanel = qs('.mobile-panel');
  const mobileMenu = qs('.mobile-menu');

  function closeDropdown() {
    if (!dropdown) return;
    dropdown.classList.remove('open');
    if (avatarBtn) avatarBtn.setAttribute('aria-expanded', 'false');
  }

  function openDropdown() {
    if (!dropdown || !avatarBtn) return;
    closeMobileMenu();
    dropdown.classList.add('open');
    avatarBtn.setAttribute('aria-expanded', 'true');

    const focusable = dropdown.querySelector('a, button, [tabindex]:not([tabindex="-1"])');
    if (focusable) focusable.focus();
  }

  function setMobileMenuState(isOpen) {
    if (!mobilePanel || !hamburger) return;

    mobilePanel.classList.toggle('open', isOpen);
    mobilePanel.setAttribute('aria-hidden', String(!isOpen));
    hamburger.setAttribute('aria-expanded', String(isOpen));
    document.body.classList.toggle('mobile-menu-open', isOpen);
  }

  function openMobileMenu() {
    closeDropdown();
    setMobileMenuState(true);
  }

  function closeMobileMenu() {
    setMobileMenuState(false);
  }

  function toggleMobileMenu() {
    if (!mobilePanel) return;
    const isOpen = mobilePanel.classList.contains('open');
    if (isOpen) {
      closeMobileMenu();
    } else {
      openMobileMenu();
    }
  }

  function handleResize() {
    if (window.innerWidth > 880) {
      closeMobileMenu();
    }
  }

  if (avatarBtn && dropdown) {
    avatarBtn.addEventListener('click', function (event) {
      event.preventDefault();
      event.stopPropagation();

      if (dropdown.classList.contains('open')) {
        closeDropdown();
      } else {
        openDropdown();
      }
    });

    qsa('.profile-dropdown a', dropdown).forEach(function (link) {
      link.addEventListener('click', function () {
        closeDropdown();
      });
    });
  }

  if (hamburger && mobilePanel && mobileMenu) {
    hamburger.addEventListener('click', function (event) {
      event.preventDefault();
      event.stopPropagation();
      toggleMobileMenu();
    });

    mobilePanel.addEventListener('click', function (event) {
      if (event.target === mobilePanel) {
        closeMobileMenu();
      }
    });

    qsa('.mobile-menu a', mobileMenu).forEach(function (link) {
      link.addEventListener('click', function () {
        closeMobileMenu();
      });
    });
  }

  document.addEventListener('pointerdown', function (event) {
    if (!mobilePanel || !mobilePanel.classList.contains('open')) return;

    const clickedInsideMenu = !!mobileMenu && mobileMenu.contains(event.target);
    const clickedHamburger = !!hamburger && hamburger.contains(event.target);

    if (!clickedInsideMenu && !clickedHamburger) {
      closeMobileMenu();
    }
  });

  document.addEventListener('click', function (event) {
    if (!dropdown) return;

    const clickedInsideDropdown = dropdown.contains(event.target);
    const clickedAvatar = avatarBtn && avatarBtn.contains(event.target);

    if (!clickedInsideDropdown && !clickedAvatar) {
      closeDropdown();
    }
  });

  document.addEventListener('keydown', function (event) {
    if (event.key === 'Escape') {
      closeDropdown();
      closeMobileMenu();
    }
  });

  window.addEventListener('resize', handleResize);
  window.addEventListener('orientationchange', handleResize);

  if (mobilePanel) {
    mobilePanel.setAttribute('aria-hidden', 'true');
  }

  if (hamburger) {
    hamburger.setAttribute('aria-expanded', 'false');
  }
})();
