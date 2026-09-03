(function () {
  function qs(sel, root = document) {
    return root.querySelector(sel);
  }

  function qsa(sel, root = document) {
    return Array.from(root.querySelectorAll(sel));
  }

  const avatarBtn = qs('.avatar-button');
  const dropdown = qs('.profile-dropdown');

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
    }
  });
})();
