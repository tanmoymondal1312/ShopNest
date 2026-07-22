// ── Alpine.js Cart Store ──────────────────────────────────────────────────────
document.addEventListener('alpine:init', () => {
  Alpine.store('cart', {
    items: [],
    open: false,
    checkoutOpen: false,

    init() {
      try {
        const saved = localStorage.getItem('shopnest_cart');
        if (saved) {
          // Backfill fields added after a cart may have been saved
          this.items = JSON.parse(saved).map(i => ({
            ...i,
            key:   i.key || this.lineKey(i.id, i.size),
            size:  i.size || '',
            sizes: i.sizes || [],
          }));
        }
      } catch (e) {
        this.items = [];
      }
    },

    // Same product in two sizes must be two separate cart lines
    lineKey(id, size) {
      return id + '::' + (size || '');
    },

    save() {
      localStorage.setItem('shopnest_cart', JSON.stringify(this.items));
    },

    get count() {
      return this.items.reduce((sum, i) => sum + i.qty, 0);
    },

    get total() {
      return this.items.reduce((sum, i) => sum + i.price * i.qty, 0);
    },

    addItem(product) {
      const key = this.lineKey(product.id, product.size);
      const existing = this.items.find(i => i.key === key);
      if (existing) {
        existing.qty++;
      } else {
        this.items.push({
          ...product,
          size:  product.size || '',
          sizes: product.sizes || [],   // options offered in the checkout dialog
          key,
          qty: 1,
        });
      }
      this.save();
      this.open = true;
      this._bounceBadge();
    },

    removeItem(key) {
      this.items = this.items.filter(i => i.key !== key);
      this.save();
    },

    updateQty(key, qty) {
      const item = this.items.find(i => i.key === key);
      if (!item) return;
      qty = Math.max(1, parseInt(qty) || 1);
      item.qty = qty;
      this.save();
    },

    /** Switch a line to another size, merging if that size is already in the cart. */
    setSize(key, size) {
      const item = this.items.find(i => i.key === key);
      if (!item || item.size === size) return;

      const newKey = this.lineKey(item.id, size);
      const twin = this.items.find(i => i.key === newKey);

      if (twin) {
        twin.qty += item.qty;
        this.items = this.items.filter(i => i.key !== key);
      } else {
        item.size = size;
        item.key = newKey;
      }
      this.save();
    },

    clearCart() {
      this.items = [];
      this.save();
    },

    openDrawer() {
      this.open = true;
      document.body.style.overflow = 'hidden';
    },

    closeDrawer() {
      this.open = false;
      document.body.style.overflow = '';
    },

    openCheckout() {
      this.open = false;
      this.checkoutOpen = true;
      document.body.style.overflow = 'hidden';
    },

    closeCheckout() {
      this.checkoutOpen = false;
      document.body.style.overflow = '';
    },

    _bounceBadge() {
      const badge = document.querySelector('.cart-badge');
      if (badge) {
        badge.classList.remove('bounce');
        void badge.offsetWidth;
        badge.classList.add('bounce');
      }
    },

    formatPrice(price) {
      return window.CURRENCY + price.toFixed(2);
    },
  });
});

// ── Checkout form submission ───────────────────────────────────────────────────
// Resolves to { ok, orderId } or { ok: false, error } — the dialog renders the
// outcome itself rather than navigating away.
window.submitOrder = async function (formEl) {
  const cart = Alpine.store('cart');
  if (cart.items.length === 0) {
    return { ok: false, error: 'আপনার কার্ট খালি।' };
  }

  const name    = formEl.querySelector('[name="name"]').value.trim();
  const phone   = formEl.querySelector('[name="phone"]').value.trim();
  const address = formEl.querySelector('[name="address"]').value.trim();
  const note    = formEl.querySelector('[name="note"]').value.trim();

  if (!name || !phone) {
    return { ok: false, error: 'নাম ও মোবাইল নম্বর আবশ্যক।' };
  }

  const summary = {
    items: cart.items.map(i => ({ ...i })),
    total: cart.total,
  };

  try {
    const res = await fetch('/order', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name,
        phone,
        address,
        note,
        items: cart.items.map(i => ({
          id: i.id,
          name: i.name,
          price: i.price,
          qty: i.qty,
          size: i.size || '',
        })),
      }),
    });

    const data = await res.json();
    if (!res.ok) throw new Error(data.error || 'অর্ডার দেওয়া সম্ভব হয়নি।');

    cart.clearCart();
    return { ok: true, orderId: data.order_id, ...summary };
  } catch (err) {
    return { ok: false, error: err.message };
  }
};

// ── Homepage deferred product grid ────────────────────────────────────────────
const _gridCache = {};
let _currentCat  = '';
let _currentPage = 1;

async function loadProductsGrid(cat = '', page = 1) {
  const key       = `${cat}|${page}`;
  const container = document.getElementById('products-grid-container');
  if (!container) return;

  _currentCat  = cat;
  _currentPage = page;

  // Update pill active states immediately (instant visual feedback)
  document.querySelectorAll('#cat-pills .cat-pill').forEach(pill => {
    pill.classList.toggle('active', pill.dataset.cat === cat);
  });

  // Show skeleton only on first load (cached loads are instant)
  if (!_gridCache[key]) {
    container.innerHTML =
      '<div class="skeleton-grid">' +
      Array(8).fill('<div class="skeleton-card"></div>').join('') +
      '</div>';
    try {
      const res = await fetch(
        `/api/products-grid?cat=${encodeURIComponent(cat)}&page=${page}`
      );
      if (!res.ok) throw new Error();
      _gridCache[key] = await res.text();
    } catch {
      container.innerHTML =
        '<p style="color:var(--text-muted);padding:32px 0;">লোড হয়নি — পুনরায় চেষ্টা করুন।</p>';
      return;
    }
  }

  container.innerHTML = _gridCache[key];

  // Wire pagination links inside the loaded HTML
  container.querySelectorAll('.pg-nav').forEach(link => {
    link.addEventListener('click', e => {
      e.preventDefault();
      const pg = parseInt(link.dataset.page);
      if (pg) loadProductsGrid(_currentCat, pg);
      document.getElementById('all-products')
        ?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
  });
}

// ── Navbar search on Enter ─────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  const searchInput = document.getElementById('navbar-search');
  if (searchInput) {
    searchInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        const q = searchInput.value.trim();
        if (q) window.location.href = `/search?q=${encodeURIComponent(q)}`;
      }
    });
  }

  // ── Category scroll arrow: click scrolls right, hides at end ──────────────
  const catPillsEl = document.getElementById('cat-pills');
  const catWrap    = catPillsEl?.closest('.cat-scroll-wrap');
  const catBtn     = document.getElementById('cat-scroll-btn');

  if (catPillsEl && catWrap && catBtn) {
    const checkEnd = () => {
      const atEnd = catPillsEl.scrollLeft + catPillsEl.clientWidth >= catPillsEl.scrollWidth - 4;
      catWrap.classList.toggle('scroll-end', atEnd);
    };
    catBtn.addEventListener('click', () => {
      catPillsEl.scrollBy({ left: 200, behavior: 'smooth' });
    });
    catPillsEl.addEventListener('scroll', checkEnd, { passive: true });
    window.addEventListener('resize', checkEnd);
    checkEnd(); // run on load
  }

  // ── Homepage: category pill interception + initial grid load ──────────────
  const catPills = document.getElementById('cat-pills');
  if (catPills) {
    catPills.addEventListener('click', e => {
      const pill = e.target.closest('.cat-pill');
      if (pill) loadProductsGrid(pill.dataset.cat || '', 1);
    });
    // Load first page after browser paints the above-the-fold content
    requestAnimationFrame(() => loadProductsGrid('', 1));
  }

  // Close cart on Escape
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      const cart = Alpine.store('cart');
      if (cart.checkoutOpen) cart.closeCheckout();
      else if (cart.open) cart.closeDrawer();
    }
  });
});
