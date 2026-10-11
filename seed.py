"""
Run once to seed the database with sample categories and products.
  python seed.py

Safe to re-run (INSERT OR IGNORE) — deploy.sh calls it on every deploy.
Product images are reused from static/uploads/products/ (committed in the repo),
so seeding works fully offline.
"""

import asyncio
import sys
from pathlib import Path

import aiosqlite

from database import init_db, DB_PATH

# Windows consoles default to cp1252 — Bengali output would crash without this.
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

UPLOAD_DIR = Path("static/uploads/products")
STATIC_DIR = Path("static")

CATEGORIES = [
    ("পোশাক",        "poshak",      1),
    ("ইলেকট্রনিক্স", "electronics", 2),
    ("কিডস আইটেম",   "kids-items",  3),
    ("খাদ্য",        "khaddo",      4),
]

PRODUCTS = [
    # ─── পোশাক ────────────────────────────────────────────────────────────
    {
        "name":        "প্রিমিয়াম কটন টি-শার্ট",
        "slug":        "premium-cotton-tshirt",
        "description": "নরম ও আরামদায়ক ১০০% কটন টি-শার্ট। গরমের দিনে পারফেক্ট।",
        "price":       450.0,
        "old_price":   650.0,
        "stock":       35,
        "cat_slug":    "poshak",
        "sizes":       "S,M,L,XL,XXL",
        "is_featured": 1,
    },
    {
        "name":        "ক্লাসিক ডেনিম জ্যাকেট",
        "slug":        "denim-jacket-classic",
        "description": "ক্লাসিক ডেনিম জ্যাকেট। শীতের শুরুতে স্টাইলিশ লুকের জন্য আদর্শ।",
        "price":       1250.0,
        "old_price":   1800.0,
        "stock":       12,
        "cat_slug":    "poshak",
        "sizes":       "M,L,XL",
        "is_featured": 1,
    },
    {
        "name":        "সামার ফ্লোরাল ড্রেস",
        "slug":        "summer-floral-dress",
        "description": "হালকা ফ্লোরাল প্রিন্টের সুন্দর ড্রেস। ক্যাজুয়াল আউটিং-এ পারফেক্ট।",
        "price":       780.0,
        "old_price":   None,
        "stock":       20,
        "cat_slug":    "poshak",
        "sizes":       "S,M,L",
        "is_featured": 0,
    },
    {
        "name":        "ক্যাজুয়াল হুডি (গ্রে)",
        "slug":        "casual-hoodie-grey",
        "description": "ফ্লিস লাইনিং সহ উষ্ণ হুডি। শীতকালে ঘরে-বাইরে আরামদায়ক।",
        "price":       950.0,
        "old_price":   1200.0,
        "stock":       18,
        "cat_slug":    "poshak",
        "sizes":       "M,L,XL",
        "is_featured": 1,
    },
    {
        "name":        "লিনেন শার্ট (সাদা)",
        "slug":        "linen-shirt-white",
        "description": "প্রিমিয়াম লিনেন ফ্যাব্রিকের শার্ট। অফিস বা পার্টিতে এলিগ্যান্ট লুক।",
        "price":       680.0,
        "old_price":   850.0,
        "stock":       25,
        "cat_slug":    "poshak",
        "sizes":       "S,M,L,XL",
        "is_featured": 0,
    },

    # ─── ইলেকট্রনিক্স ─────────────────────────────────────────────────────
    {
        "name":        "ওয়্যারলেস ইয়ারবাড",
        "slug":        "wireless-earbuds-pro",
        "description": "নয়েজ ক্যান্সেলিং সহ TWS ইয়ারবাড। ২৪ ঘণ্টা ব্যাটারি লাইফ।",
        "price":       1450.0,
        "old_price":   2200.0,
        "stock":       40,
        "cat_slug":    "electronics",
        "is_featured": 1,
    },
    {
        "name":        "স্মার্ট ওয়াচ ফিটনেস",
        "slug":        "smart-watch-fitness",
        "description": "হার্ট রেট মনিটর, স্টেপ কাউন্টার ও স্লিপ ট্র্যাকার সহ স্মার্টওয়াচ।",
        "price":       2500.0,
        "old_price":   3500.0,
        "stock":       15,
        "cat_slug":    "electronics",
        "is_featured": 1,
    },
    {
        "name":        "পোর্টেবল ব্লুটুথ স্পিকার",
        "slug":        "portable-bluetooth-speaker",
        "description": "ওয়াটারপ্রুফ মিনি স্পিকার। ১০ ঘণ্টা প্লেটাইম। আউটডোরে পারফেক্ট।",
        "price":       890.0,
        "old_price":   1100.0,
        "stock":       30,
        "cat_slug":    "electronics",
        "is_featured": 0,
    },
    {
        "name":        "২০০০০mAh পাওয়ার ব্যাংক",
        "slug":        "power-bank-20000mah",
        "description": "দ্রুত চার্জিং সাপোর্ট। ২টি USB পোর্ট। ফোন ৪ বার ফুল চার্জ।",
        "price":       1100.0,
        "old_price":   1500.0,
        "stock":       50,
        "cat_slug":    "electronics",
        "is_featured": 1,
    },
    {
        "name":        "LED ডেস্ক ল্যাম্প",
        "slug":        "led-desk-lamp",
        "description": "আই-কেয়ার টেকনোলজি সহ অ্যাডজাস্টেবল ডেস্ক ল্যাম্প। পড়াশোনায় আদর্শ।",
        "price":       650.0,
        "old_price":   None,
        "stock":       22,
        "cat_slug":    "electronics",
        "is_featured": 0,
    },

    # ─── কিডস আইটেম ──────────────────────────────────────────────────────
    {
        "name":        "কালারফুল বিল্ডিং ব্লকস",
        "slug":        "colorful-building-blocks",
        "description": "১০০ পিস বিল্ডিং ব্লক সেট। বাচ্চাদের ক্রিয়েটিভিটি বাড়ায়। ৩+ বছর।",
        "price":       550.0,
        "old_price":   750.0,
        "stock":       28,
        "cat_slug":    "kids-items",
        "is_featured": 1,
    },
    {
        "name":        "কিডস স্কুল ব্যাকপ্যাক",
        "slug":        "kids-school-backpack",
        "description": "হালকা ও টেকসই ব্যাকপ্যাক। একাধিক পকেট ও ওয়াটারপ্রুফ ম্যাটেরিয়াল।",
        "price":       480.0,
        "old_price":   650.0,
        "stock":       35,
        "cat_slug":    "kids-items",
        "is_featured": 1,
    },
    {
        "name":        "সফট টেডি বেয়ার (বড়)",
        "slug":        "soft-teddy-bear-large",
        "description": "নরম ও আলিঙ্গনযোগ্য বড় টেডি বেয়ার। বাচ্চাদের সেরা উপহার।",
        "price":       750.0,
        "old_price":   950.0,
        "stock":       20,
        "cat_slug":    "kids-items",
        "is_featured": 1,
    },
    {
        "name":        "কিডস ওয়াটার বোতল (BPA ফ্রি)",
        "slug":        "kids-water-bottle-bpa-free",
        "description": "লিক-প্রুফ ডিজাইন। আকর্ষণীয় কার্টুন প্রিন্ট। ৫০০ml ক্যাপাসিটি।",
        "price":       320.0,
        "old_price":   450.0,
        "stock":       45,
        "cat_slug":    "kids-items",
        "is_featured": 0,
    },
    {
        "name":        "আর্ট সাপ্লাই কিট (৫০ পিস)",
        "slug":        "art-supply-kit-50pc",
        "description": "ক্রেয়ন, মার্কার, রঙ পেন্সিল সহ কমপ্লিট আর্ট কিট। ছোটদের জন্য আদর্শ।",
        "price":       420.0,
        "old_price":   None,
        "stock":       30,
        "cat_slug":    "kids-items",
        "is_featured": 0,
    },

    # ─── খাদ্য (মুদি) ─────────────────────────────────────────────────────
    {
        "name":        "বাসমতি চাল (৫ কেজি)",
        "slug":        "basmati-rice-5kg",
        "description": "প্রিমিয়াম মানের দীর্ঘ দানার বাসমতি চাল। সুগন্ধি ও স্বাদে অতুলনীয়।",
        "price":       520.0,
        "old_price":   600.0,
        "stock":       100,
        "cat_slug":    "khaddo",
        "is_featured": 1,
    },
    {
        "name":        "মিনিকেট চাল (৫ কেজি)",
        "slug":        "miniket-rice-5kg",
        "description": "দৈনন্দিন রান্নার জন্য আদর্শ মিনিকেট চাল। সাদা ও মসৃণ দানা।",
        "price":       450.0,
        "old_price":   500.0,
        "stock":       60,
        "cat_slug":    "khaddo",
        "is_featured": 0,
    },
    {
        "name":        "মসুর ডাল (১ কেজি)",
        "slug":        "red-lentil-masur-dal-1kg",
        "description": "পরিষ্কার ও মানসম্মত লাল মসুর ডাল। দ্রুত রান্না হয়।",
        "price":       140.0,
        "old_price":   160.0,
        "stock":       80,
        "cat_slug":    "khaddo",
        "is_featured": 0,
    },
    {
        "name":        "গুঁড়া দুধ (৫০০ গ্রাম)",
        "slug":        "milk-powder-500g",
        "description": "ফুলক্রিম গুঁড়া দুধ। চা, দুধপান ও মিষ্টি তৈরিতে ব্যবহারযোগ্য।",
        "price":       450.0,
        "old_price":   500.0,
        "stock":       40,
        "cat_slug":    "khaddo",
        "is_featured": 0,
    },
    {
        "name":        "চিনি (১ কেজি)",
        "slug":        "sugar-1kg",
        "description": "পরিষ্কার সাদা চিনি। চা, মিষ্টি ও রান্নার জন্য।",
        "price":       130.0,
        "old_price":   145.0,
        "stock":       100,
        "cat_slug":    "khaddo",
        "is_featured": 0,
    },
    {
        "name":        "লবণ (১ কেজি)",
        "slug":        "salt-1kg",
        "description": "আয়োডিনযুক্ত পরিষ্কার লবণ। রান্নাঘরের নিত্যপ্রয়োজনীয়।",
        "price":       42.0,
        "old_price":   50.0,
        "stock":       120,
        "cat_slug":    "khaddo",
        "is_featured": 0,
    },
    {
        "name":        "হলুদ গুঁড়া (২০০ গ্রাম)",
        "slug":        "turmeric-powder-200g",
        "description": "প্রাকৃতিক রঙের মশলা হলুদ গুঁড়া। ঝোল ও ভুনার জন্য আদর্শ।",
        "price":       120.0,
        "old_price":   150.0,
        "stock":       60,
        "cat_slug":    "khaddo",
        "is_featured": 0,
    },
    {
        "name":        "মরিচ গুঁড়া (২০০ গ্রাম)",
        "slug":        "chili-powder-200g",
        "description": "ঝাঁঝালো স্বাদের লাল মরিচ গুঁড়া। তাজা মরিচ থেকে তৈরি।",
        "price":       150.0,
        "old_price":   180.0,
        "stock":       55,
        "cat_slug":    "khaddo",
        "is_featured": 0,
    },
    {
        "name":        "সরিষার তেল (১ লিটার)",
        "slug":        "mustard-oil-1ltr",
        "description": "শুদ্ধ সরিষার তেল। ভাজাপোড়া ও মাছের রান্নায় অপরিহার্য।",
        "price":       400.0,
        "old_price":   450.0,
        "stock":       45,
        "cat_slug":    "khaddo",
        "is_featured": 0,
    },
    {
        "name":        "সয়াবিন তেল (৫ লিটার)",
        "slug":        "soybean-oil-5ltr",
        "description": "ভিটামিন A, D ও E সমৃদ্ধ সয়াবিন তেল। পরিবারের দৈনন্দিন ব্যবহারের জন্য।",
        "price":       1000.0,
        "old_price":   1150.0,
        "stock":       25,
        "cat_slug":    "khaddo",
        "is_featured": 0,
    },
]

# Store settings that are shipped as files in the repo — fill them in only when
# they are still empty, so an admin's own choice is never overwritten.
SETTING_IMAGES = {
    "logo":         "uploads/logo.webp",
    "social_image": "uploads/social_image.webp",
}


def image_for(slug: str) -> str:
    """Return the shipped image filename for a product, or "" when absent."""
    return f"{slug}.webp" if (UPLOAD_DIR / f"{slug}.webp").exists() else ""


async def seed():
    await init_db()

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row

        # ── Categories ──────────────────────────────────────────────────────
        cat_id_map = {}
        for name, slug, order in CATEGORIES:
            try:
                cursor = await db.execute(
                    "INSERT OR IGNORE INTO categories (name, slug, sort_order) VALUES (?, ?, ?)",
                    (name, slug, order),
                )
                if cursor.lastrowid:
                    cat_id_map[slug] = cursor.lastrowid
                else:
                    row = await (await db.execute("SELECT id FROM categories WHERE slug=?", (slug,))).fetchone()
                    cat_id_map[slug] = row["id"]
            except Exception as e:
                print(f"Category {slug}: {e}")

        await db.commit()
        print(f"✓ {len(CATEGORIES)} ক্যাটাগরি সিড করা হয়েছে")

        # ── Products ────────────────────────────────────────────────────────
        inserted = 0
        with_image = 0
        for p in PRODUCTS:
            cat_id = cat_id_map.get(p["cat_slug"])
            image = image_for(p["slug"])
            with_image += bool(image)
            try:
                await db.execute(
                    """INSERT OR IGNORE INTO products
                       (name, slug, description, price, old_price, stock, category_id,
                        image, sizes, is_active, is_featured)
                       VALUES (?,?,?,?,?,?,?,?,?,1,?)""",
                    (
                        p["name"], p["slug"], p["description"],
                        p["price"], p.get("old_price"), p["stock"],
                        cat_id, image, p.get("sizes", ""),
                        p.get("is_featured", 0),
                    ),
                )
                inserted += 1
            except Exception as e:
                print(f"Product {p['slug']}: {e}")

        await db.commit()
        print(f"✓ {inserted} পণ্য সিড করা হয়েছে ({with_image}টির ছবিসহ)")

        # ── Backfill: attach shipped images to pre-existing imageless rows ──
        cursor = await db.execute("SELECT id, slug FROM products WHERE image = '' OR image IS NULL")
        healed = 0
        for row in await cursor.fetchall():
            image = image_for(row["slug"])
            if image:
                await db.execute("UPDATE products SET image = ? WHERE id = ?", (image, row["id"]))
                healed += 1
        await db.commit()
        if healed:
            print(f"✓ {healed}টি পুরনো পণ্যে ছবি যোগ হয়েছে")

        # ── Store logo / social image ───────────────────────────────────────
        for key, rel_path in SETTING_IMAGES.items():
            if not (STATIC_DIR / rel_path).exists():
                continue
            await db.execute(
                "INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO NOTHING",
                (key, rel_path),
            )
            await db.execute(
                "UPDATE settings SET value = ? WHERE key = ? AND (value IS NULL OR value = '')",
                (rel_path, key),
            )
        await db.commit()
        print("✓ লোগো ও সোশ্যাল ইমেজ সেটিংস যোগ হয়েছে")

        print("\n✅ সিড সম্পূর্ণ! এখন চালু করুন: uvicorn main:app --reload")


if __name__ == "__main__":
    asyncio.run(seed())
