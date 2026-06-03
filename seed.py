"""
Run once to seed the database with sample categories and products.
  python seed.py
"""

import asyncio
import aiosqlite
from database import init_db, DB_PATH

CATEGORIES = [
    ("পোশাক",       "poshak",      1),
    ("ইলেকট্রনিক্স", "electronics", 2),
    ("গৃহস্থালি",    "grihosthali", 3),
    ("খাদ্য",        "khaddo",      4),
    ("বেকারি",       "bakery",      5),
]

PRODUCTS = [
    {
        "name":        "কটন কুর্তা (সাদা)",
        "slug":        "cotton-kurta-white",
        "description": "উচ্চমানের সুতার তৈরি আরামদায়ক কুর্তা। গরম আবহাওয়ার জন্য আদর্শ।",
        "price":       350.0,
        "old_price":   500.0,
        "stock":       20,
        "cat_slug":    "poshak",
        "is_featured": 1,
    },
    {
        "name":        "সিল্ক শাড়ি (লাল)",
        "slug":        "silk-saree-red",
        "description": "বিশুদ্ধ সিল্কের তৈরি উজ্জ্বল লাল শাড়ি। উৎসব ও অনুষ্ঠানের জন্য।",
        "price":       1200.0,
        "old_price":   None,
        "stock":       8,
        "cat_slug":    "poshak",
        "is_featured": 1,
    },
    {
        "name":        "স্মার্টফোন চার্জার (20W)",
        "slug":        "smartphone-charger-20w",
        "description": "দ্রুত চার্জিং সাপোর্ট সহ 20W USB-C চার্জার। সব ডিভাইসের সাথে কম্প্যাটিবল।",
        "price":       280.0,
        "old_price":   400.0,
        "stock":       50,
        "cat_slug":    "electronics",
        "is_featured": 0,
    },
    {
        "name":        "ব্লুটুথ ইয়ারফোন",
        "slug":        "bluetooth-earphones",
        "description": "ক্রিস্টাল ক্লিয়ার সাউন্ড। 8 ঘণ্টা ব্যাটারি লাইফ। IPX5 ওয়াটারপ্রুফ।",
        "price":       750.0,
        "old_price":   1100.0,
        "stock":       15,
        "cat_slug":    "electronics",
        "is_featured": 1,
    },
    {
        "name":        "স্টিলের তাওয়া (বড়)",
        "slug":        "steel-tawa-large",
        "description": "নন-স্টিক আবরণ সহ ২৬ সেমি স্টিলের তাওয়া। রুটি, পরোটা রান্নায় আদর্শ।",
        "price":       450.0,
        "old_price":   None,
        "stock":       30,
        "cat_slug":    "grihosthali",
        "is_featured": 0,
    },
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
        "name":        "চকোলেট কেক (৫০০গ্রাম)",
        "slug":        "chocolate-cake-500g",
        "description": "তাজা বেলজিয়ান চকোলেট দিয়ে তৈরি নরম ও সুস্বাদু কেক। জন্মদিন বা উৎসবে পাঠান।",
        "price":       380.0,
        "old_price":   None,
        "stock":       10,
        "cat_slug":    "bakery",
        "is_featured": 0,
    },
    {
        "name":        "বাটার কুকিজ (প্যাক)",
        "slug":        "butter-cookies-pack",
        "description": "ক্রিস্পি বাটার কুকিজ। ১২টির প্যাক। চা বা কফির সাথে পরিবেশন করুন।",
        "price":       120.0,
        "old_price":   150.0,
        "stock":       2,
        "cat_slug":    "bakery",
        "is_featured": 0,
    },
]


async def seed():
    await init_db()

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row

        # Insert categories
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

        # Insert products
        inserted = 0
        for p in PRODUCTS:
            cat_id = cat_id_map.get(p["cat_slug"])
            try:
                await db.execute(
                    """INSERT OR IGNORE INTO products
                       (name, slug, description, price, old_price, stock, category_id, image, is_active, is_featured)
                       VALUES (?,?,?,?,?,?,?,?,1,?)""",
                    (
                        p["name"], p["slug"], p["description"],
                        p["price"], p.get("old_price"), p["stock"],
                        cat_id, "",  # no image in seed
                        p.get("is_featured", 0),
                    ),
                )
                inserted += 1
            except Exception as e:
                print(f"Product {p['slug']}: {e}")

        await db.commit()
        print(f"✓ {inserted} পণ্য সিড করা হয়েছে")
        print("\n✅ সিড সম্পূর্ণ! এখন চালু করুন: uvicorn main:app --reload")


if __name__ == "__main__":
    asyncio.run(seed())
