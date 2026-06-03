# ShopNest

A beautiful, blazing-fast single-vendor e-commerce template by **Mediaghor**.

## Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI + Python |
| Templating | Jinja2 (SSR) |
| Database | SQLite + aiosqlite |
| Interactivity | Alpine.js |
| Styling | Vanilla CSS |

## Features

- 🛒 WhatsApp-first checkout (no payment gateway needed)
- 🎨 Dynamic accent color — change the whole site color from admin panel
- 📦 Product management with image upload (auto-converted to WebP)
- 🔍 Live search suggestions
- 📊 Privacy-safe visitor analytics
- 🌐 Social media links manageable from admin
- 📱 Fully responsive (mobile-first)
- ⚡ Sub-1-second loads on 4G

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Seed sample data
python3 seed.py

# Run the server
uvicorn main:app --reload --port 8000
```

- **Shop:** http://localhost:8000  
- **Admin:** http://localhost:8000/admin/login

## Default Admin Credentials

Set in `.env` (copy `.env.example` to `.env` and change before deploying):

```
ADMIN_USER=admin
ADMIN_PASS=shopnest2024
SECRET_KEY=change-this-in-production
```

## Configuration

All store settings are managed from the admin panel:
- Store name, tagline, hero tagline
- Logo & social banner image
- WhatsApp number
- Accent color (controls entire site theme)
- Social media links (Facebook, Instagram, YouTube, X, TikTok)
- Currency symbol
- Footer text

---

Built with ❤️ by [Mediaghor](https://mediaghor.com)
