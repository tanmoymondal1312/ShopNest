// ── Admin JS ──────────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {

  // ── Sidebar mobile toggle ────────────────────────────────────────────────────
  const sidebar  = document.getElementById('sidebar');
  const overlay  = document.getElementById('sidebar-overlay');
  const menuBtn  = document.getElementById('menu-toggle');

  function openSidebar() {
    sidebar?.classList.add('open');
    overlay?.classList.add('show');
    document.body.style.overflow = 'hidden';
  }
  function closeSidebar() {
    sidebar?.classList.remove('open');
    overlay?.classList.remove('show');
    document.body.style.overflow = '';
  }
  menuBtn?.addEventListener('click', openSidebar);
  overlay?.addEventListener('click', closeSidebar);

  // ── Image upload preview ─────────────────────────────────────────────────────
  const fileInput = document.getElementById('product-image-input');
  const preview   = document.getElementById('image-preview');
  const previewImg = document.getElementById('preview-img');
  const uploadZone = document.getElementById('upload-zone');

  if (fileInput) {
    fileInput.addEventListener('change', () => {
      const file = fileInput.files[0];
      if (!file) return;
      if (!file.type.startsWith('image/')) {
        alert('শুধুমাত্র ছবি ফাইল আপলোড করুন।');
        return;
      }
      if (file.size > 5 * 1024 * 1024) {
        alert('ছবির সাইজ সর্বোচ্চ ৫ MB হতে পারবে।');
        return;
      }
      const reader = new FileReader();
      reader.onload = (e) => {
        if (previewImg) previewImg.src = e.target.result;
        if (preview)    preview.style.display = 'flex';
      };
      reader.readAsDataURL(file);
    });

    // Drag-and-drop
    uploadZone?.addEventListener('dragover', (e) => {
      e.preventDefault();
      uploadZone.classList.add('drag-over');
    });
    uploadZone?.addEventListener('dragleave', () => uploadZone.classList.remove('drag-over'));
    uploadZone?.addEventListener('drop', (e) => {
      e.preventDefault();
      uploadZone.classList.remove('drag-over');
      const dt = e.dataTransfer;
      if (dt.files.length) {
        fileInput.files = dt.files;
        fileInput.dispatchEvent(new Event('change'));
      }
    });
  }

  // ── Auto-generate slug from name ─────────────────────────────────────────────
  const nameInput = document.getElementById('product-name');
  const slugInput = document.getElementById('product-slug');
  let slugEdited = slugInput?.value?.length > 0;

  if (slugInput) {
    slugInput.addEventListener('input', () => { slugEdited = true; });
  }

  nameInput?.addEventListener('input', () => {
    if (!slugEdited && slugInput) {
      slugInput.value = toSlug(nameInput.value);
    }
  });

  function toSlug(str) {
    return str
      .toLowerCase()
      .replace(/[^\w\s-]/g, '')
      .replace(/[\s_]+/g, '-')
      .replace(/^-+|-+$/g, '')
      .substring(0, 80);
  }

  // ── Color picker sync ─────────────────────────────────────────────────────────
  const colorPicker = document.getElementById('color-picker');
  const colorText   = document.getElementById('color-text');
  if (colorPicker && colorText) {
    colorPicker.addEventListener('input', () => { colorText.value = colorPicker.value; });
    colorText.addEventListener('input', () => {
      if (/^#[0-9a-fA-F]{6}$/.test(colorText.value)) {
        colorPicker.value = colorText.value;
      }
    });
  }

  // ── Confirm delete dialogs ────────────────────────────────────────────────────
  document.querySelectorAll('.delete-form').forEach(form => {
    form.addEventListener('submit', (e) => {
      if (!confirm('আপনি কি নিশ্চিত? এটি মুছে ফেলা হবে।')) {
        e.preventDefault();
      }
    });
  });

  // ── Generic instant image preview for all upload zones ───────────────────────
  document.querySelectorAll('.upload-zone').forEach(zone => {
    const input   = zone.querySelector('input[type="file"]');
    const preview = zone.querySelector('.uz-preview');
    const img     = zone.querySelector('.uz-preview-img');
    if (!input || !preview || !img) return;

    input.addEventListener('change', () => {
      const file = input.files[0];
      if (!file || !file.type.startsWith('image/')) return;
      const reader = new FileReader();
      reader.onload = e => {
        img.src = e.target.result;
        preview.style.display = 'block';
      };
      reader.readAsDataURL(file);
    });
  });

  // ── Flash auto-dismiss ────────────────────────────────────────────────────────
  const flash = document.querySelector('.flash');
  if (flash) {
    setTimeout(() => {
      flash.style.transition = 'opacity .4s';
      flash.style.opacity = '0';
      setTimeout(() => flash.remove(), 400);
    }, 4000);
  }

  // ── Bar chart renderer ────────────────────────────────────────────────────────
  renderBarChart();
  renderVisitorChart();
});

function renderBarChart() {
  const chart = document.getElementById('orders-chart');
  if (!chart) return;

  const data   = JSON.parse(chart.dataset.values || '[]');
  const labels = JSON.parse(chart.dataset.labels || '[]');
  if (!data.length) return;

  const max = Math.max(...data, 1);

  const container = document.getElementById('orders-chart-container');
  if (!container) return;
  container.innerHTML = '';

  data.forEach((val, i) => {
    const col = document.createElement('div');
    col.className = 'bar-chart-col';

    const barH = Math.max(4, Math.round((val / max) * 100));

    col.innerHTML = `
      <span class="bar-value">${val}</span>
      <div class="bar" style="height:${barH}%;" title="${labels[i] || ''}: ${val}"></div>
      <span class="bar-label">${(labels[i] || '').slice(5)}</span>
    `;
    container.appendChild(col);
  });
}

function renderVisitorChart() {
  const chart = document.getElementById('visitors-chart');
  if (!chart) return;

  const data   = JSON.parse(chart.dataset.values || '[]');
  const labels = JSON.parse(chart.dataset.labels || '[]');
  if (!data.length) return;

  const max = Math.max(...data, 1);
  const container = document.getElementById('visitors-chart-container');
  if (!container) return;
  container.innerHTML = '';

  data.forEach((val, i) => {
    const col = document.createElement('div');
    col.className = 'bar-chart-col';
    const barH = Math.max(4, Math.round((val / max) * 100));
    col.innerHTML = `
      <span class="bar-value">${val}</span>
      <div class="bar" style="height:${barH}%;background:rgba(34,197,94,.7);" title="${labels[i] || ''}: ${val}"></div>
      <span class="bar-label">${(labels[i] || '').slice(5)}</span>
    `;
    container.appendChild(col);
  });
}
