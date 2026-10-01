const onMarketReady = (callback) => {
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', callback, { once: true });
  } else {
    callback();
  }
};

onMarketReady(() => {
  const previewTitle = document.getElementById('preview-title');
  const previewCategory = document.getElementById('preview-category');
  const previewCondition = document.getElementById('preview-condition');
  const previewPrice = document.getElementById('preview-price');
  const completionValue = document.getElementById('completion-value');
  const completionBar = document.getElementById('completion-bar');
  const descCounter = document.getElementById('desc-count');

  const form = document.querySelector('.create-form');
  const submit = document.getElementById('submit-button');

  const titleInput = document.getElementById('id_title');
  const categoryInput = document.getElementById('id_category');
  const conditionInput = document.getElementById('id_condition');
  const priceInput = document.getElementById('id_price');
  const descriptionInput = document.getElementById('id_description');
  const imagesInput = document.getElementById('id_images');
  const previews = document.getElementById('image-previews');

  const formatPrice = (value) => {
    if (!value) return '';
    const digits = String(value).replace(/[^\d]/g, '');
    if (!digits) return '';
    return Number(digits).toLocaleString('uz-UZ');
  };

  const updatePreview = () => {
    const title = titleInput ? titleInput.value.trim() : '';
    const categoryText = categoryInput && categoryInput.options[categoryInput.selectedIndex]
      ? categoryInput.options[categoryInput.selectedIndex].text.trim()
      : 'Kategoriya';
    const conditionText = conditionInput && conditionInput.options[conditionInput.selectedIndex]
      ? conditionInput.options[conditionInput.selectedIndex].text.trim()
      : 'Holat';
    const priceValue = priceInput ? priceInput.value.trim() : '';
    const descriptionText = descriptionInput ? descriptionInput.value.trim() : '';

    if (previewTitle) {
      previewTitle.textContent = title || "E'lon nomi";
    }

    if (previewCategory) {
      previewCategory.textContent = categoryText || 'Kategoriya';
    }

    if (previewCondition) {
      previewCondition.textContent = conditionText || 'Holat';
    }

    if (previewPrice) {
      const formatted = formatPrice(priceValue);
      previewPrice.textContent = formatted ? `${formatted} so'm` : "Narx ko'rsatilmagan";
    }

    let score = 0;
    if (title.length >= 8) score += 25;
    if (categoryInput && categoryInput.value) score += 15;
    if (conditionInput && conditionInput.value) score += 15;
    if (priceValue && Number(String(priceValue).replace(/[^\d]/g, '')) > 0) score += 25;
    if (descriptionText.length >= 30) score += 20;
    if (imagesInput && imagesInput.files && imagesInput.files.length >= 3) score += 10;

    const clampedScore = Math.min(score, 100);

    if (completionValue) completionValue.textContent = `${clampedScore}%`;
    if (completionBar) completionBar.style.width = `${clampedScore}%`;

    if (descCounter) {
      const currentLength = descriptionText.length;
      descCounter.textContent = `${currentLength}/500`;
    }
  };

  if (imagesInput && previews) {
    imagesInput.addEventListener('change', () => {
      previews.innerHTML = '';
      const files = Array.from(imagesInput.files || []).slice(0, 8);

      files.forEach((file, idx) => {
        const reader = new FileReader();
        const wrap = document.createElement('div');
        wrap.className = 'preview-item';

        reader.onload = (event) => {
          wrap.innerHTML = `<img src="${event.target.result}" alt="Preview ${idx + 1}" />`;
        };

        reader.readAsDataURL(file);
        previews.appendChild(wrap);
      });

      updatePreview();
    });
  }

  [titleInput, categoryInput, conditionInput, priceInput, descriptionInput].forEach((field) => {
    if (field) {
      field.addEventListener('input', updatePreview);
      field.addEventListener('change', updatePreview);
    }
  });

  if (form && submit) {
    form.addEventListener('submit', () => {
      submit.disabled = true;
      submit.querySelector('.btn-label').textContent = 'Joylanmoqda...';
    });
  }

  updatePreview();
});

onMarketReady(() => {
  const galleryImage = document.querySelector('[data-gallery-main]');
  const galleryThumbs = Array.from(document.querySelectorAll('[data-gallery-thumb]'));
  const lightbox = document.querySelector('[data-market-lightbox]');
  const lightboxImage = document.querySelector('[data-lightbox-image]');
  const currentCount = document.querySelector('[data-gallery-current]');
  let currentIndex = 0;

  if (galleryImage) {
    const sources = galleryThumbs.length
      ? galleryThumbs.map((thumb) => thumb.dataset.src)
      : [galleryImage.currentSrc || galleryImage.src];

    const showImage = (index) => {
      currentIndex = (index + sources.length) % sources.length;
      galleryImage.src = sources[currentIndex];
      if (lightboxImage) lightboxImage.src = sources[currentIndex];
      if (currentCount) currentCount.textContent = String(currentIndex + 1);
      galleryThumbs.forEach((thumb, thumbIndex) => {
        const isActive = thumbIndex === currentIndex;
        thumb.classList.toggle('is-active', isActive);
        thumb.setAttribute('aria-pressed', String(isActive));
      });
    };

    galleryThumbs.forEach((thumb, index) => {
      thumb.addEventListener('click', () => showImage(index));
    });
    document.querySelectorAll('[data-gallery-prev]').forEach((button) => {
      button.addEventListener('click', () => showImage(currentIndex - 1));
    });
    document.querySelectorAll('[data-gallery-next]').forEach((button) => {
      button.addEventListener('click', () => showImage(currentIndex + 1));
    });

    const openButton = document.querySelector('[data-gallery-open]');
    if (openButton && lightbox) {
      openButton.addEventListener('click', () => {
        if (typeof lightbox.showModal === 'function') lightbox.showModal();
        else lightbox.setAttribute('open', '');
      });
    }
    document.querySelectorAll('[data-gallery-close]').forEach((button) => {
      button.addEventListener('click', () => {
        if (lightbox && typeof lightbox.close === 'function') lightbox.close();
        else if (lightbox) lightbox.removeAttribute('open');
      });
    });
    if (lightbox) {
      lightbox.addEventListener('click', (event) => {
        if (event.target !== lightbox) return;
        if (typeof lightbox.close === 'function') lightbox.close();
        else lightbox.removeAttribute('open');
      });
    }
    document.addEventListener('keydown', (event) => {
      if (!lightbox || !lightbox.open || sources.length < 2) return;
      if (event.key === 'ArrowLeft') showImage(currentIndex - 1);
      if (event.key === 'ArrowRight') showImage(currentIndex + 1);
    });
  }

  const contactDialog = document.querySelector('[data-contact-dialog]');
  let contactOpener = null;
  if (contactDialog) {
    document.querySelectorAll('[data-contact-open]').forEach((button) => {
      button.addEventListener('click', () => {
        contactOpener = button;
        if (typeof contactDialog.showModal === 'function') contactDialog.showModal();
        else contactDialog.setAttribute('open', '');
      });
    });
    document.querySelectorAll('[data-contact-close]').forEach((button) => {
      button.addEventListener('click', () => {
        if (typeof contactDialog.close === 'function') contactDialog.close();
        else contactDialog.removeAttribute('open');
      });
    });
    contactDialog.addEventListener('click', (event) => {
      if (event.target !== contactDialog) return;
      if (typeof contactDialog.close === 'function') contactDialog.close();
      else contactDialog.removeAttribute('open');
    });
    contactDialog.addEventListener('close', () => {
      if (contactOpener) contactOpener.focus();
    });
  }

  document.querySelectorAll('[data-phone-toggle]').forEach((button) => {
    button.addEventListener('click', () => {
      const phone = button.parentElement.querySelector('[data-phone-number]');
      if (!phone) return;
      phone.hidden = false;
      button.hidden = true;
      phone.focus();
    });
  });

  const fallbackCopy = (text) => {
    const field = document.createElement('textarea');
    field.value = text;
    field.setAttribute('readonly', '');
    field.style.position = 'fixed';
    field.style.opacity = '0';
    document.body.appendChild(field);
    field.select();
    const copied = document.execCommand('copy');
    field.remove();
    return copied ? Promise.resolve() : Promise.reject(new Error('Clipboard unavailable'));
  };

  document.querySelectorAll('[data-share-current]').forEach((button) => {
    button.addEventListener('click', async () => {
      const status = document.querySelector('[data-share-status]');
      try {
        if (navigator.clipboard && navigator.clipboard.writeText) {
          await navigator.clipboard.writeText(window.location.href);
        } else {
          await fallbackCopy(window.location.href);
        }
        if (status) status.textContent = 'E’lon havolasi nusxalandi.';
        button.title = 'Havola nusxalandi';
      } catch (error) {
        if (status) status.textContent = 'Havolani nusxalab bo‘lmadi.';
        button.title = 'Havolani nusxalab bo‘lmadi';
      }
    });
  });
});
