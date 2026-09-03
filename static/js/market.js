document.addEventListener('DOMContentLoaded', () => {
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
