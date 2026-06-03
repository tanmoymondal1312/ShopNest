// ── Alpine.js Cart Store ──────────────────────────────────────────────────────
document.addEventListener('alpine:init', () => {
  Alpine.store('cart', {
    items: [],
    open: false,
    checkoutOpen: false,

    init() {
      try {
        const saved = localStorage.getItem('shopnest_cart');
        if (saved) this.items = JSON.parse(saved);
      } catch (e) {
        this.items = [];
      }
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
      const existing = this.items.find(i => i.id === product.id);
      if (existing) {
        existing.qty++;
      } else {
        this.items.push({ ...product, qty: 1 });
      }
      this.save();
      this.open = true;
      this._bounceBadge();
    },

    removeItem(id) {
      this.items = this.items.filter(i => i.id !== id);
      this.save();
    },

    updateQty(id, qty) {
      const item = this.items.find(i => i.id === id);
      if (!item) return;
      qty = Math.max(1, parseInt(qty) || 1);
      item.qty = qty;
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
window.submitOrder = async function (formEl, btnEl) {
  const cart = Alpine.store('cart');
  if (cart.items.length === 0) return;

  const name    = formEl.querySelector('[name="name"]').value.trim();
  const phone   = formEl.querySelector('[name="phone"]').value.trim();
  const address = formEl.querySelector('[name="address"]').value.trim();
  const note    = formEl.querySelector('[name="note"]').value.trim();

  if (!name || !phone) {
    alert('নাম ও ফোন নম্বর আবশ্যক।');
    return;
  }

  btnEl.disabled = true;
  btnEl.textContent = 'অপেক্ষা করুন…';

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
        })),
      }),
    });

    const data = await res.json();
    if (!res.ok) throw new Error(data.error || 'অর্ডার দেওয়া সম্ভব হয়নি।');

    cart.clearCart();
    cart.closeCheckout();
    window.location.href = `/order/${data.order_id}/confirm`;
  } catch (err) {
    alert(err.message);
    btnEl.disabled = false;
    btnEl.textContent = 'অর্ডার দিন';
  }
};

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

  // Close cart on Escape
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      const cart = Alpine.store('cart');
      if (cart.checkoutOpen) cart.closeCheckout();
      else if (cart.open) cart.closeDrawer();
    }
  });
});
