(function () {
  const menuToggle = document.querySelector("[data-menu-toggle]");
  const navigation = document.querySelector("[data-navigation]");

  if (menuToggle && navigation) {
    function closeMenu() {
      navigation.classList.remove("is-open");
      menuToggle.setAttribute("aria-expanded", "false");
      menuToggle.setAttribute("aria-label", "Menyuni ochish");
      menuToggle.innerHTML = '<i class="fa-solid fa-bars" aria-hidden="true"></i>';
    }

    menuToggle.addEventListener("click", function () {
      const isOpen = navigation.classList.toggle("is-open");
      menuToggle.setAttribute("aria-expanded", String(isOpen));
      menuToggle.setAttribute("aria-label", isOpen ? "Menyuni yopish" : "Menyuni ochish");
      menuToggle.innerHTML = isOpen
        ? '<i class="fa-solid fa-xmark" aria-hidden="true"></i>'
        : '<i class="fa-solid fa-bars" aria-hidden="true"></i>';
    });

    navigation.querySelectorAll("a").forEach(function (link) {
      link.addEventListener("click", closeMenu);
    });

    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape") closeMenu();
    });
  }

  const clock = document.querySelector("[data-live-clock]");
  if (clock) {
    const updateClock = function () {
      clock.textContent = new Intl.DateTimeFormat("uz-UZ", {
        timeZone: "Asia/Tashkent",
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
        hour12: false,
      }).format(new Date());
    };
    updateClock();
    window.setInterval(updateClock, 1000);
  }

  const searchInput = document.querySelector("[data-card-search]");
  const categoryFilter = document.querySelector("[data-announcement-filter]");
  const announcementCards = Array.from(document.querySelectorAll("[data-search-card]"));
  const emptySearch = document.querySelector("[data-search-empty]");

  function filterAnnouncements() {
    const query = searchInput ? searchInput.value.trim().toLocaleLowerCase() : "";
    const category = categoryFilter ? categoryFilter.value : "all";
    let visibleCount = 0;

    announcementCards.forEach(function (card) {
      const matchesText = card.textContent.toLocaleLowerCase().includes(query);
      const matchesCategory = category === "all" || card.dataset.level === category;
      const isVisible = matchesText && matchesCategory;
      card.hidden = !isVisible;
      if (isVisible) visibleCount += 1;
    });

    if (emptySearch) emptySearch.hidden = visibleCount > 0 || announcementCards.length === 0;
  }

  if (searchInput) searchInput.addEventListener("input", filterAnnouncements);
  if (categoryFilter) categoryFilter.addEventListener("change", filterAnnouncements);

  const deleteOverlay = document.getElementById("delete-confirm-overlay");
  if (deleteOverlay) {
    let opener = null;
    const openButtons = document.querySelectorAll("[data-delete-modal-open='true']");
    const closeButtons = document.querySelectorAll("[data-delete-modal-close='true']");

    function setDeleteModalOpen(isOpen) {
      deleteOverlay.classList.toggle("active", isOpen);
      deleteOverlay.setAttribute("aria-hidden", String(!isOpen));
      document.body.style.overflow = isOpen ? "hidden" : "";
      if (isOpen) {
        opener = document.activeElement;
        const passwordField = deleteOverlay.querySelector("input[type='password']");
        if (passwordField) passwordField.focus();
      } else if (opener && typeof opener.focus === "function") {
        opener.focus();
      }
    }

    openButtons.forEach(function (button) {
      button.addEventListener("click", function () {
        setDeleteModalOpen(true);
      });
    });

    closeButtons.forEach(function (button) {
      button.addEventListener("click", function () {
        setDeleteModalOpen(false);
      });
    });

    deleteOverlay.addEventListener("click", function (event) {
      if (event.target === deleteOverlay) setDeleteModalOpen(false);
    });

    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape" && deleteOverlay.classList.contains("active")) {
        setDeleteModalOpen(false);
      }
    });
  }

  const bookmarkStorageKey = "tinchlik24-bookmarks-v1";
  let savedBookmarks = {};
  try {
    savedBookmarks = JSON.parse(window.localStorage.getItem(bookmarkStorageKey) || "{}");
  } catch (error) {
    savedBookmarks = {};
  }

  document.querySelectorAll("[data-bookmark]").forEach(function (button) {
    const key = button.dataset.bookmarkKey;
    if (!key) return;

    const icon = button.querySelector("i");
    const isHeart = button.dataset.bookmarkIcon === "heart";
    const setPressed = function (pressed) {
      button.setAttribute("aria-pressed", String(pressed));
      button.setAttribute("aria-label", pressed
        ? (isHeart ? "Sevimlilardan olib tashlash" : "Saqlanganlardan olib tashlash")
        : (isHeart ? "Sevimlilarga qo‘shish" : "Saqlanganlarga qo‘shish"));
      if (icon) icon.className = isHeart
        ? (pressed ? "fa-solid fa-heart" : "fa-regular fa-heart")
        : (pressed ? "fa-solid fa-bookmark" : "fa-regular fa-bookmark");
    };

    setPressed(Boolean(savedBookmarks[key]));
    button.addEventListener("click", function () {
      if (savedBookmarks[key]) delete savedBookmarks[key];
      else savedBookmarks[key] = true;
      setPressed(Boolean(savedBookmarks[key]));
      try {
        window.localStorage.setItem(bookmarkStorageKey, JSON.stringify(savedBookmarks));
      } catch (error) {
        button.title = "Brauzerda saqlash imkoni bo‘lmadi";
      }
    });
  });

  document.querySelectorAll("[data-profile-tab]").forEach(function (tab) {
    tab.addEventListener("click", function () {
      const selectedId = tab.getAttribute("aria-controls");
      const tabList = tab.closest("[role='tablist']");
      if (!tabList) return;

      tabList.querySelectorAll("[data-profile-tab]").forEach(function (otherTab) {
        const isSelected = otherTab === tab;
        otherTab.setAttribute("aria-selected", String(isSelected));
        otherTab.tabIndex = isSelected ? 0 : -1;
        const panel = document.getElementById(otherTab.getAttribute("aria-controls"));
        if (panel) panel.hidden = !isSelected;
      });

      const selectedPanel = document.getElementById(selectedId);
      if (selectedPanel) selectedPanel.focus({ preventScroll: true });
    });
  });

  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const revealSelector = [
    ".home-hero",
    ".services-section",
    ".news-section",
    ".market-section",
    ".service-card",
    ".announcement-card",
    ".account-strip",
    ".profile-header",
    ".profile-card",
    ".history-card",
    ".admin-card",
    ".market-create-header",
    ".editor-section",
    ".panel-card",
    ".listing-card",
    ".seller-card",
    ".chat-shell",
    ".site-footer",
  ].join(",");

  if (!reduceMotion && "IntersectionObserver" in window) {
    const revealElements = Array.from(document.querySelectorAll(revealSelector));
    if (revealElements.length) {
      document.documentElement.classList.add("motion-ready");

      revealElements.forEach(function (element) {
        element.setAttribute("data-scroll-reveal", "");
        const siblings = Array.from(element.parentElement.children).filter(function (sibling) {
          return sibling.matches(revealSelector);
        });
        element.style.setProperty("--reveal-delay", Math.min(siblings.indexOf(element) * 60, 180) + "ms");
      });

      const revealObserver = new IntersectionObserver(function (entries, observer) {
        entries.forEach(function (entry) {
          if (!entry.isIntersecting) return;
          entry.target.classList.add("is-visible");
          observer.unobserve(entry.target);
        });
      }, { threshold: 0.12, rootMargin: "0px 0px -6% 0px" });

      revealElements.forEach(function (element) { revealObserver.observe(element); });
    }
  }

  document.querySelectorAll("img").forEach(function (image) {
    if (image.complete) return;

    image.classList.add("image-motion-pending");
    const finishImageLoad = function () { image.classList.remove("image-motion-pending"); };
    image.addEventListener("load", finishImageLoad, { once: true });
    image.addEventListener("error", finishImageLoad, { once: true });
  });
})();
