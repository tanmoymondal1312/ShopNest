"""
Seed categories + products with downloaded images.
  .venv/bin/python seed_with_images.py
"""

import asyncio
import aiosqlite
import urllib.request
from pathlib import Path
from PIL import Image
import io

from database import init_db, DB_PATH

UPLOAD_DIR = Path("static/uploads/products")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

CATEGORIES = [
    ("পোশাক", "clothes", 1),
    ("গ্যাজেটস", "gadgets", 2),
    ("কিডস আইটেম", "kids-items", 3),
]

PRODUCTS = [
    # ─── Clothes ──────────────────────────────────────────────────────
    {
        "name": "প্রিমিয়াম কটন টি-শার্ট",
        "slug": "premium-cotton-tshirt",
        "description": "নরম ও আরামদায়ক ১০০% কটন টি-শার্ট। গরমের দিনে পারফেক্ট।",
        "price": 450.0,
        "old_price": 650.0,
        "stock": 35,
        "cat_slug": "clothes",
        "is_featured": 1,
        "image_url": "https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?w=600&q=80&fit=crop",
    },
    {
        "name": "ডেনিম জ্যাকেট",
        "slug": "denim-jacket-classic",
        "description": "ক্লাসিক ডেনিম জ্যাকেট। শীতের শুরুতে স্টাইলিশ লুকের জন্য আদর্শ।",
        "price": 1250.0,
        "old_price": 1800.0,
        "stock": 12,
        "cat_slug": "clothes",
        "is_featured": 1,
        "image_url": "https://images.unsplash.com/photo-1551028719-00167b16eac5?w=600&q=80&fit=crop",
    },
    {
        "name": "সামার ফ্লোরাল ড্রেস",
        "slug": "summer-floral-dress",
        "description": "হালকা ফ্লোরাল প্রিন্টের সুন্দর ড্রেস। ক্যাজুয়াল আউটিং-এ পারফেক্ট।",
        "price": 780.0,
        "old_price": None,
        "stock": 20,
        "cat_slug": "clothes",
        "is_featured": 0,
        "image_url": "https://images.unsplash.com/photo-1572804013309-59a88b7e92f1?w=600&q=80&fit=crop",
    },
    {
        "name": "ক্যাজুয়াল হুডি (গ্রে)",
        "slug": "casual-hoodie-grey",
        "description": "ফ্লিস লাইনিং সহ উষ্ণ হুডি। শীতকালে ঘরে-বাইরে আরামদায়ক।",
        "price": 950.0,
        "old_price": 1200.0,
        "stock": 18,
        "cat_slug": "clothes",
        "is_featured": 1,
        "image_url": "https://images.unsplash.com/photo-1556821840-3a63f95609a7?w=600&q=80&fit=crop",
    },
    {
        "name": "লিনেন শার্ট (সাদা)",
        "slug": "linen-shirt-white",
        "description": "প্রিমিয়াম লিনেন ফ্যাব্রিকের শার্ট। অফিস বা পার্টিতে এলিগ্যান্ট লুক।",
        "price": 680.0,
        "old_price": 850.0,
        "stock": 25,
        "cat_slug": "clothes",
        "is_featured": 0,
        "image_url": "https://images.unsplash.com/photo-1596755094514-f87e34085b2c?w=600&q=80&fit=crop",
    },
    # ─── Gadgets ──────────────────────────────────────────────────────
    {
        "name": "ওয়্যারলেস ইয়ারবাড",
        "slug": "wireless-earbuds-pro",
        "description": "নয়েজ ক্যান্সেলিং সহ TWS ইয়ারবাড। ২৪ ঘণ্টা ব্যাটারি লাইফ।",
        "price": 1450.0,
        "old_price": 2200.0,
        "stock": 40,
        "cat_slug": "gadgets",
        "is_featured": 1,
        "image_url": "https://images.unsplash.com/photo-1590658268037-6bf12f032f55?w=600&q=80&fit=crop",
    },
    {
        "name": "স্মার্ট ওয়াচ ফিটনেস",
        "slug": "smart-watch-fitness",
        "description": "হার্ট রেট মনিটর, স্টেপ কাউন্টার ও স্লিপ ট্র্যাকার সহ স্মার্টওয়াচ।",
        "price": 2500.0,
        "old_price": 3500.0,
        "stock": 15,
        "cat_slug": "gadgets",
        "is_featured": 1,
        "image_url": "https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=600&q=80&fit=crop",
    },
    {
        "name": "পোর্টেবল ব্লুটুথ স্পিকার",
        "slug": "portable-bluetooth-speaker",
        "description": "ওয়াটারপ্রুফ মিনি স্পিকার। ১০ ঘণ্টা প্লেটাইম। আউটডোরে পারফেক্ট।",
        "price": 890.0,
        "old_price": 1100.0,
        "stock": 30,
        "cat_slug": "gadgets",
        "is_featured": 0,
        "image_url": "https://images.unsplash.com/photo-1608043152269-423dbba4e7e1?w=600&q=80&fit=crop",
    },
    {
        "name": "২০০০০mAh পাওয়ার ব্যাংক",
        "slug": "power-bank-20000mah",
        "description": "দ্রুত চার্জিং সাপোর্ট। ২টি USB পোর্ট। ফোন ৪ বার ফুল চার্জ।",
        "price": 1100.0,
        "old_price": 1500.0,
        "stock": 50,
        "cat_slug": "gadgets",
        "is_featured": 1,
        "image_url": "https://images.unsplash.com/photo-1609091839311-d5365f9ff1c5?w=600&q=80&fit=crop",
    },
    {
        "name": "LED ডেস্ক ল্যাম্প",
        "slug": "led-desk-lamp",
        "description": "আই-কেয়ার টেকনোলজি সহ অ্যাডজাস্টেবল ডেস্ক ল্যাম্প। পড়াশোনায় আদর্শ।",
        "price": 650.0,
        "old_price": None,
        "stock": 22,
        "cat_slug": "gadgets",
        "is_featured": 0,
        "image_url": "https://images.unsplash.com/photo-1507473885765-e6ed057ab6fe?w=600&q=80&fit=crop",
    },
    # ─── Kids Items ───────────────────────────────────────────────────
    {
        "name": "কালারফুল বিল্ডিং ব্লকস",
        "slug": "colorful-building-blocks",
        "description": "১০০ পিস বিল্ডিং ব্লক সেট। বাচ্চাদের ক্রিয়েটিভিটি বাড়ায়। ৩+ বছর।",
        "price": 550.0,
        "old_price": 750.0,
        "stock": 28,
        "cat_slug": "kids-items",
        "is_featured": 1,
        "image_url": "https://images.unsplash.com/photo-1596461404969-9ae70f2830c1?w=600&q=80&fit=crop",
    },
    {
        "name": "কিডস স্কুল ব্যাকপ্যাক",
        "slug": "kids-school-backpack",
        "description": "হালকা ও টেকসই ব্যাকপ্যাক। একাধিক পকেট ও ওয়াটারপ্রুফ ম্যাটেরিয়াল।",
        "price": 480.0,
        "old_price": 650.0,
        "stock": 35,
        "cat_slug": "kids-items",
        "is_featured": 1,
        "image_url": "https://images.unsplash.com/photo-1525966222134-fcfa99b8ae77?w=600&q=80&fit=crop",
    },
    {
        "name": "সফট টেডি বেয়ার (বড়)",
        "slug": "soft-teddy-bear-large",
        "description": "নরম ও আলিঙ্গনযোগ্য বড় টেডি বেয়ার। বাচ্চাদের সেরা উপহার।",
        "price": 750.0,
        "old_price": 950.0,
        "stock": 20,
        "cat_slug": "kids-items",
        "is_featured": 1,
        "image_url": "https://images.unsplash.com/photo-1559715541-5daf8a0296d0?w=600&q=80&fit=crop",
    },
    {
        "name": "কিডস ওয়াটার বোতল (BPA ফ্রি)",
        "slug": "kids-water-bottle-bpa-free",
        "description": "লিক-প্রুফ ডিজাইন। আকর্ষণীয় কার্টুন প্রিন্ট। ৫০০ml ক্যাপাসিটি।",
        "price": 320.0,
        "old_price": 450.0,
        "stock": 45,
        "cat_slug": "kids-items",
        "is_featured": 0,
        "image_url": "https://images.unsplash.com/photo-1602143407151-7111542de6e8?w=600&q=80&fit=crop",
    },
    {
        "name": "আর্ট সাপ্লাই কিট (৫০ পিস)",
        "slug": "art-supply-kit-50pc",
        "description": "ক্রেয়ন, মার্কার, রঙ পেন্সিল সহ কমপ্লিট আর্ট কিট। ছোটদের জন্য আদর্শ।",
        "price": 420.0,
        "old_price": None,
        "stock": 30,
        "cat_slug": "kids-items",
        "is_featured": 0,
        "image_url": "https://images.unsplash.com/photo-1513364776144-60967b0f800f?w=600&q=80&fit=crop",
    },
]


def download_and_save(url: str, slug: str) -> str:
    """Download image, convert to WebP, create thumbnail."""
    headers = {"User-Agent": "Mozilla/5.0"}
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = resp.read()

    img = Image.open(io.BytesIO(data)).convert("RGB")

    img.thumbnail((800, 800))
    filename = f"{slug}.webp"
    img.save(UPLOAD_DIR / filename, "WEBP", quality=85, optimize=True)

    thumb = img.copy()
    thumb.thumbnail((400, 400))
    thumb.save(UPLOAD_DIR / f"{slug}_thumb.webp", "WEBP", quality=80)

    size_kb = (UPLOAD_DIR / filename).stat().st_size / 1024
    print(f"  ✓ {filename} ({size_kb:.0f} KB)")
    return filename


async def seed():
    await init_db()

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row

        # Categories
        cat_map = {}
        for name, slug, order in CATEGORIES:
            await db.execute(
                "INSERT OR IGNORE INTO categories (name, slug, sort_order) VALUES (?, ?, ?)",
                (name, slug, order),
            )
            row = await (
                await db.execute("SELECT id FROM categories WHERE slug=?", (slug,))
            ).fetchone()
            cat_map[slug] = row["id"]
        await db.commit()
        print(f"✓ {len(CATEGORIES)} ক্যাটাগরি তৈরি হয়েছে\n")

        # Products
        ok, fail = 0, 0
        for p in PRODUCTS:
            print(f"↓ {p['name']}...")
            image_file = ""
            try:
                image_file = download_and_save(p["image_url"], p["slug"])
            except Exception as e:
                print(f"  ✗ Image failed: {e}")
                fail += 1

            await db.execute(
                """INSERT OR IGNORE INTO products
                   (name, slug, description, price, old_price, stock,
                    category_id, image, is_active, is_featured)
                   VALUES (?,?,?,?,?,?,?,?,1,?)""",
                (
                    p["name"],
                    p["slug"],
                    p["description"],
                    p["price"],
                    p.get("old_price"),
                    p["stock"],
                    cat_map[p["cat_slug"]],
                    image_file,
                    p.get("is_featured", 0),
                ),
            )
            ok += 1

        await db.commit()
        print(f"\n✅ Done! {ok} products added, {fail} image failures")
        print("🚀 Server restart korle dekhte parba: http://localhost:8000")


if __name__ == "__main__":
    asyncio.run(seed())
