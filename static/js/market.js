document.addEventListener('DOMContentLoaded', () => {
  // Gallery thumbnail swap on listing detail
  const mainImage = document.getElementById('main-image');
  if (mainImage) {
    document.querySelectorAll('.thumb').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.preventDefault();
        const src = btn.dataset.src;
        if (src) mainImage.src = src;
      });
    });
  }

  // Image previews on create/edit form
  const imagesInput = document.querySelector('input[name="images"]');
  const previews = document.getElementById('image-previews');
  if (imagesInput && previews) {
    imagesInput.addEventListener('change', () => {
      previews.innerHTML = '';
      const files = imagesInput.files || [];
      Array.from(files).slice(0,8).forEach((file, i) => {
        const reader = new FileReader();
        const wrap = document.createElement('div');
        wrap.className = 'preview-item';
        reader.onload = (ev) => {
          wrap.innerHTML = `<img src="${ev.target.result}" alt="Preview ${i+1}" />`;
        };
        reader.readAsDataURL(file);
        previews.appendChild(wrap);
      });
    });
  }

  // Prevent double submit
  const form = document.querySelector('.create-form');
  const submit = document.getElementById('submit-button');
  if (form && submit) {
    form.addEventListener('submit', () => {
      submit.disabled = true;
      submit.textContent = 'Joylanmoqda...';
    });
  }
});
