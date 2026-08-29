(function () {
  function qs(sel, root = document) {
    return root.querySelector(sel);
  }

  function qsa(sel, root = document) {
    return Array.from(root.querySelectorAll(sel));
  }

  document.addEventListener('DOMContentLoaded', function () {
    const avatarBtn = qs('.avatar-button');
    const dropdown = qs('.profile-dropdown');
    const hamburger = qs('.hamburger');
    const mobilePanel = qs('.mobile-panel');

    function closeDropdown() {
      if (!dropdown) return;
      dropdown.classList.remove('open');
      if (avatarBtn) avatarBtn.setAttribute('aria-expanded', 'false');
    }

    function openDropdown() {
      if (!dropdown || !avatarBtn) return;
      dropdown.classList.add('open');
      avatarBtn.setAttribute('aria-expanded', 'true');
      const focusable = dropdown.querySelector('a, button, [tabindex]:not([tabindex="-1"])');
      if (focusable) focusable.focus();
    }

    function closeMobileMenu() {
      if (!mobilePanel || !hamburger) return;
      mobilePanel.classList.remove('open');
      hamburger.setAttribute('aria-expanded', 'false');
    }

    if (avatarBtn && dropdown) {
      avatarBtn.addEventListener('click', function (event) {
        event.preventDefault();
        event.stopPropagation();
        if (dropdown.classList.contains('open')) {
          closeDropdown();
        } else {
          closeMobileMenu();
          openDropdown();
        }
      });

      qsa('.profile-dropdown a', dropdown).forEach(function (link) {
        link.addEventListener('click', closeDropdown);
      });
    }

    document.addEventListener('click', function (event) {
      const clickedInsideDropdown = dropdown && dropdown.contains(event.target);
      const clickedAvatar = avatarBtn && avatarBtn.contains(event.target);
      if (!clickedInsideDropdown && !clickedAvatar) {
        closeDropdown();
      }

      if (mobilePanel && event.target === mobilePanel) {
        closeMobileMenu();
      }
    });

    document.addEventListener('keydown', function (event) {
      if (event.key === 'Escape') {
        closeDropdown();
        closeMobileMenu();
      }
    });

    if (hamburger && mobilePanel) {
      hamburger.addEventListener('click', function (event) {
        event.preventDefault();
        event.stopPropagation();
        closeDropdown();
        const isOpen = mobilePanel.classList.toggle('open');
        hamburger.setAttribute('aria-expanded', String(isOpen));
      });

      qsa('.mobile-menu a', mobilePanel).forEach(function (link) {
        link.addEventListener('click', closeMobileMenu);
      });
    }
  });
})();
