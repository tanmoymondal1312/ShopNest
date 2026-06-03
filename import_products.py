"""
Import 23 products from item-images/ into the database.
Run: python3 import_products.py
"""
import asyncio
import shutil
from pathlib import Path
from PIL import Image
import aiosqlite

DB_PATH   = "shop.db"
SRC_DIR   = Path("item-images")
DEST_DIR  = Path("static/uploads/products")
DEST_DIR.mkdir(parents=True, exist_ok=True)


# ── Helper: process one image ───────────────────────────────────────────────

def process_image(src: Path, slug: str) -> str:
    """Convert, resize to 800×800 max, save as WebP. Returns filename."""
    img = Image.open(src).convert("RGB")
    img.thumbnail((800, 800))
    filename = f"{slug}.webp"
    img.save(DEST_DIR / filename, "WEBP", quality=85, optimize=True)
    # thumbnail 400×400
    thumb = img.copy(); thumb.thumbnail((400, 400))
    thumb.save(DEST_DIR / f"{slug}_thumb.webp", "WEBP", quality=80)
    return filename


# ── Category + product definitions ──────────────────────────────────────────

CATEGORIES = [
    ("পোশাক",            "poshak",          1),
    ("ব্যাগ",             "bag",             2),
    ("ইলেকট্রনিক্স",     "electronics",     3),
    ("এক্সেসরিজ",        "accessories",     4),
    ("স্বাস্থ্য ও সৌন্দর্য", "health-beauty", 5),
    ("জুতা",              "juta",            6),
    ("গৃহস্থালি",         "grihosthali",     7),
    ("আসবাবপত্র",        "furniture",       8),
    ("বই ও ধর্মীয়",     "book-religious",  9),
]

PRODUCTS = [
    {
        "name":      "প্রিমিয়াম কালো পাঞ্জাবি",
        "slug":      "premium-black-panjabi",
        "cat":       "poshak",
        "price":     1200.0, "old_price": 1800.0,
        "stock":     30,
        "featured":  1,
        "desc":      "উচ্চমানের ফ্যাব্রিকে তৈরি প্রিমিয়াম কালো পাঞ্জাবি। মান্দারিন কলার ও মেটালিক বাটন সহ। যেকোনো অনুষ্ঠানের জন্য আদর্শ।",
        "src":       "270079_fold_4_5__20260111094231258_width_1024.webp",
    },
    {
        "name":      "ফ্যাশন ব্যাকপ্যাক (গোলাপি)",
        "slug":      "fashion-backpack-pink",
        "cat":       "bag",
        "price":     850.0, "old_price": 1200.0,
        "stock":     25,
        "featured":  1,
        "desc":      "ট্রেন্ডি অ্যাবস্ট্র্যাক্ট প্রিন্টের গোলাপি-বেগুনি ব্যাকপ্যাক। মাল্টিপল কম্পার্টমেন্ট ও রিফ্লেক্টিভ স্ট্রিপ সহ। স্কুল ও ট্রাভেলের জন্য।",
        "src":       "8366eca4997cd467511452d70efaf594.jpg_720x720q80.jpg",
    },
    {
        "name":      "স্মার্টওয়াচ (কালো)",
        "slug":      "smartwatch-black",
        "cat":       "electronics",
        "price":     3500.0, "old_price": 4500.0,
        "stock":     15,
        "featured":  1,
        "desc":      "স্টাইলিশ কালো স্মার্টওয়াচ। স্বাস্থ্য ট্র্যাকিং, নোটিফিকেশন সাপোর্ট এবং দীর্ঘস্থায়ী ব্যাটারি। স্পোর্টস ব্যান্ড সহ।",
        "src":       "daniel-korpai-hbTKIbuMmBI-unsplash.jpg",
    },
    {
        "name":      "হলুদ ট্র্যাকস্যুট সেট (মহিলা)",
        "slug":      "yellow-tracksuit-women",
        "cat":       "poshak",
        "price":     1500.0, "old_price": 2000.0,
        "stock":     20,
        "featured":  1,
        "desc":      "ভাইব্র্যান্ট হলুদ ক্রপ হুডি ও জগার প্যান্ট সেট। নরম ফ্লিস ফ্যাব্রিক। ক্যাজুয়াল ও স্পোর্টসওয়্যার উভয়ের জন্য।",
        "src":       "dom-hill-nimElTcTNyY-unsplash.jpg",
    },
    {
        "name":      "স্কুল ব্যাকপ্যাক (নীল)",
        "slug":      "school-backpack-blue",
        "cat":       "bag",
        "price":     650.0, "old_price": 900.0,
        "stock":     40,
        "featured":  0,
        "desc":      "টেকসই নীল স্কুল ব্যাকপ্যাক। মাল্টিপল জিপ পকেট, প্যাডেড স্ট্র্যাপ ও ওয়াটার রেজিস্ট্যান্ট ফ্যাব্রিক। ক্লাস থেকে ট্রিপ পর্যন্ত আদর্শ।",
        "src":       "download.jpeg",
    },
    {
        "name":      "রে-ব্যান ওয়েফেরার সানগ্লাস",
        "slug":      "rayban-wayfarer-sunglasses",
        "cat":       "accessories",
        "price":     2800.0, "old_price": 3500.0,
        "stock":     20,
        "featured":  1,
        "desc":      "ক্লাসিক কালো রে-ব্যান নিউ ওয়েফেরার সানগ্লাস। পোলারাইজড লেন্স। UV400 প্রটেকশন। যেকোনো মুখের আকারের জন্য মানানসই।",
        "src":       "giorgio-trovato-K62u25Jk6vo-unsplash.jpg",
    },
    {
        "name":      "পেপসোডেন্ট অ্যান্টি-জার্ম টুথপেস্ট",
        "slug":      "pepsodent-toothpaste",
        "cat":       "health-beauty",
        "price":     85.0, "old_price": 100.0,
        "stock":     100,
        "featured":  0,
        "desc":      "পেপসোডেন্ট অ্যান্টি-জার্ম+ টুথপেস্ট। ৪০টি সর্বাধিক সক্রিয় উপাদান। মাড়ির সুরক্ষা ও তাজা নিঃশ্বাসের জন্য।",
        "src":       "images (1).jpeg",
    },
    {
        "name":      "বানি ব্যাকপ্যাক (বেগুনি)",
        "slug":      "bunny-backpack-purple",
        "cat":       "bag",
        "price":     750.0, "old_price": 1000.0,
        "stock":     30,
        "featured":  0,
        "desc":      "কিউট বানি কান ডিজাইনের বেগুনি ব্যাকপ্যাক। মেয়েদের স্কুল ব্যাগ হিসেবে আদর্শ। মাল্টিপল পকেট ও আরামদায়ক স্ট্র্যাপ সহ।",
        "src":       "images (2).jpeg",
    },
    {
        "name":      "লাল পাঞ্জাবি (পুরুষ)",
        "slug":      "red-panjabi-men",
        "cat":       "poshak",
        "price":     850.0, "old_price": 1200.0,
        "stock":     25,
        "featured":  1,
        "desc":      "উজ্জ্বল লাল রঙের পুরুষের পাঞ্জাবি। মান্দারিন কলার ডিজাইন। ঈদ ও উৎসব অনুষ্ঠানের জন্য আদর্শ। সুতার কোয়ালিটি প্রিমিয়াম।",
        "src":       "images (3).jpeg",
    },
    {
        "name":      "হিমালয়া কমপ্লিট কেয়ার টুথপেস্ট",
        "slug":      "himalaya-complete-care-toothpaste",
        "cat":       "health-beauty",
        "price":     120.0, "old_price": 150.0,
        "stock":     80,
        "featured":  0,
        "desc":      "হিমালয়া হার্বাল কমপ্লিট কেয়ার টুথপেস্ট। প্রাকৃতিক উপাদানে তৈরি। দাঁতের ক্ষয় রোধ, মাড়ির যত্ন ও মুখের দুর্গন্ধ দূর করে।",
        "src":       "images.jpeg",
    },
    {
        "name":      "ফ্লোরাল প্রিন্ট টিউনিক শার্ট (মহিলা)",
        "slug":      "floral-print-tunic-women",
        "cat":       "poshak",
        "price":     950.0, "old_price": 1400.0,
        "stock":     20,
        "featured":  0,
        "desc":      "রঙিন ফ্লোরাল ও পেইসলি প্রিন্টের মহিলার টিউনিক শার্ট। ৩/৪ হাতা ডিজাইন। হালকা ও আরামদায়ক কটন ফ্যাব্রিক। গ্রীষ্মকালীন পোশাক।",
        "src":       "imana-hceDyN0-dTU-unsplash.jpg",
    },
    {
        "name":      "কালারফুল চাঙ্কি রেট্রো স্নিকার",
        "slug":      "colorful-chunky-retro-sneaker",
        "cat":       "juta",
        "price":     2200.0, "old_price": 3000.0,
        "stock":     15,
        "featured":  1,
        "desc":      "বোল্ড মাল্টি-কালার ডিজাইনের রেট্রো চাঙ্কি স্নিকার। লাল লেস ও টিল অ্যাকসেন্ট। ফ্যাশনেবল ও আরামদায়ক। স্ট্রিট স্টাইলের জন্য পারফেক্ট।",
        "src":       "irene-kredenets-dwKiHoqqxk8-unsplash.jpg",
    },
    {
        "name":      "সবুজ ইনসুলেটেড ওয়াটার বোতল",
        "slug":      "green-insulated-water-bottle",
        "cat":       "grihosthali",
        "price":     450.0, "old_price": 600.0,
        "stock":     50,
        "featured":  0,
        "desc":      "ম্যাট ফিনিশের সবুজ স্টেইনলেস স্টিল ওয়াটার বোতল। ১২ ঘণ্টা ঠান্ডা ও ৬ ঘণ্টা গরম রাখে। ৫০০ml ধারণক্ষমতা। BPA মুক্ত।",
        "src":       "joan-tran-reEySFadyJQ-unsplash.jpg",
    },
    {
        "name":      "ওভার-ইয়ার ওয়্যার্ড হেডফোন",
        "slug":      "over-ear-wired-headphones",
        "cat":       "electronics",
        "price":     1800.0, "old_price": 2500.0,
        "stock":     20,
        "featured":  1,
        "desc":      "প্রিমিয়াম ওভার-ইয়ার হেডফোন। লেদার ইয়ার কুশন। ক্রিস্টাল ক্লিয়ার সাউন্ড ও গভীর বেস। স্টুডিও মনিটরিং ও মিউজিক উপভোগের জন্য।",
        "src":       "kiran-ck-LSNJ-pltdu8-unsplash.jpg",
    },
    {
        "name":      "ফ্লোরাল প্রিন্ট স্টিলেটো হিল জুতা",
        "slug":      "floral-print-stiletto-heels",
        "cat":       "juta",
        "price":     1600.0, "old_price": 2200.0,
        "stock":     12,
        "featured":  0,
        "desc":      "নীল ফ্লোরাল প্রিন্টের পয়েন্টেড-টো স্টিলেটো হিল। সাটিন ফ্যাব্রিক। পার্টি ও ফর্মাল অনুষ্ঠানের জন্য পারফেক্ট। Aldo ব্র্যান্ড।",
        "src":       "mohammad-metri-E-0ON3VGrBc-unsplash.jpg",
    },
    {
        "name":      "ভিটামিন সি ব্রাইটেনিং স্কিনকেয়ার সেট",
        "slug":      "vitamin-c-skincare-set",
        "cat":       "health-beauty",
        "price":     1200.0, "old_price": 1600.0,
        "stock":     25,
        "featured":  1,
        "desc":      "Bioglow ভিটামিন C ফেস ক্রিম ও সিরাম সেট। ত্বক উজ্জ্বল করে ও ডার্ক স্পট কমায়। অ্যান্টি-অক্সিডেন্ট সমৃদ্ধ। সব ধরনের ত্বকের জন্য।",
        "src":       "nataliya-melnychuk-PdzMmdHqN2c-unsplash.jpg",
    },
    {
        "name":      "স্মার্টওয়াচ (সাদা রাউন্ড ডায়াল)",
        "slug":      "smartwatch-white-round",
        "cat":       "electronics",
        "price":     2800.0, "old_price": 3800.0,
        "stock":     18,
        "featured":  0,
        "desc":      "মিনিমালিস্ট ডিজাইনের সাদা রাউন্ড ডায়াল স্মার্টওয়াচ। সিলিকন ব্যান্ড। হেলথ মনিটর, স্টেপ কাউন্টার ও স্লিপ ট্র্যাকিং ফিচার সহ।",
        "src":       "rachit-tank-2cFZ_FB08UM-unsplash.jpg",
    },
    {
        "name":      "Timex সিলভার অ্যানালগ ঘড়ি",
        "slug":      "timex-silver-analog-watch",
        "cat":       "accessories",
        "price":     3200.0, "old_price": 4000.0,
        "stock":     10,
        "featured":  1,
        "desc":      "ক্লাসিক Timex সিলভার স্টেইনলেস স্টিল অ্যানালগ ঘড়ি। ডায়মন্ড প্যাটার্ন ডায়াল। ৩০m ওয়াটার রেজিস্ট্যান্ট। অফিস ও ফর্মাল ইভেন্টে মানানসই।",
        "src":       "rohit-jawalkar-hdd5ft0Bjo8-unsplash.jpg",
    },
    {
        "name":      "কাঠের বার স্টুল (সাদা)",
        "slug":      "wooden-bar-stool-white",
        "cat":       "furniture",
        "price":     2500.0, "old_price": 3200.0,
        "stock":     8,
        "featured":  0,
        "desc":      "স্ক্যান্ডিনেভিয়ান ডিজাইনের সাদা কাঠের বার স্টুল। স্কোয়ার সিট ও স্লিম লেগ ডিজাইন। উচ্চতা ৭৫cm। কিচেন কাউন্টার ও ব্রেকফাস্ট বারের জন্য।",
        "src":       "ruslan-bardash-4kTbAMRAHtQ-unsplash.jpg",
    },
    {
        "name":      "Nike ফ্লাইনিট রানিং শু (লাল)",
        "slug":      "nike-flyknit-running-shoe-red",
        "cat":       "juta",
        "price":     4500.0, "old_price": 5500.0,
        "stock":     15,
        "featured":  1,
        "desc":      "Nike Free RN Flyknit রানিং শু। লাইটওয়েট ফ্লাইনিট আপার। ফ্লেক্সিবল সোল। দৌড়ানো ও ব্যায়ামের জন্য সর্বোত্তম। পুরুষ ও মহিলা উভয়ের জন্য।",
        "src":       "ryan-waring-164_6wVEHfI-unsplash.jpg",
    },
    {
        "name":      "Mediplus DS হোয়াইটেনিং টুথপেস্ট",
        "slug":      "mediplus-ds-whitening-toothpaste",
        "cat":       "health-beauty",
        "price":     95.0, "old_price": 120.0,
        "stock":     75,
        "featured":  0,
        "desc":      "Mediplus DS জেন্টেল হোয়াইটেনিং টুথপেস্ট। সেনসিটিভ দাঁতের জন্য বিশেষভাবে তৈরি। ক্যারিজ ও সেনসিটিভিটি থেকে সুরক্ষা দেয়।",
        "src":       "too.webp",
    },
    {
        "name":      "আল-কোরআন (হার্ডকভার, অর্নেট)",
        "slug":      "al-quran-hardcover-ornate",
        "cat":       "book-religious",
        "price":     450.0, "old_price": 600.0,
        "stock":     30,
        "featured":  1,
        "desc":      "সোনালি অর্নেটাল ডিজাইনের হার্ডকভার আল-কোরআন শরিফ। উচ্চমানের বাইন্ডিং ও ছাপা। পরিষ্কার ও স্পষ্ট আরবি ফন্ট। উপহার হিসেবেও আদর্শ।",
        "src":       "unsplash-image-lKbz2ejxYbA.jpg",
    },
    {
        "name":      "Nike SuperRep ট্রেনিং শু (নিয়ন)",
        "slug":      "nike-superrep-training-shoe-neon",
        "cat":       "juta",
        "price":     5200.0, "old_price": 6500.0,
        "stock":     12,
        "featured":  1,
        "desc":      "Nike SuperRep Go হাই-ইন্টেন্সিটি ট্রেনিং শু। নিয়ন হলুদ-সবুজ কালার। রিঅ্যাক্টিভ ফোম কুশনিং। HIIT, সার্কিট ট্রেনিং ও জিমের জন্য পারফেক্ট।",
        "src":       "usama-akram-kP6knT7tjn4-unsplash.jpg",
    },
]


# ── Main import ──────────────────────────────────────────────────────────────

async def main():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row

        # ── 1. Create categories (INSERT OR IGNORE) ──────────────────────────
        print("Creating categories…")
        cat_id_map = {}
        for name, slug, order in CATEGORIES:
            await db.execute(
                "INSERT OR IGNORE INTO categories (name, slug, sort_order) VALUES (?, ?, ?)",
                (name, slug, order)
            )
        await db.commit()

        # Build slug→id map
        cursor = await db.execute("SELECT id, slug FROM categories")
        for row in await cursor.fetchall():
            cat_id_map[row["slug"]] = row["id"]
        print(f"  ✓ {len(cat_id_map)} categories ready")

        # ── 2. Process images & create products ──────────────────────────────
        print("\nProcessing images & creating products…")
        created = 0
        skipped = 0

        for p in PRODUCTS:
            src_path = SRC_DIR / p["src"]
            if not src_path.exists():
                print(f"  ✗ Image not found: {p['src']}")
                skipped += 1
                continue

            # Check if slug already exists
            cur = await db.execute("SELECT id FROM products WHERE slug = ?", (p["slug"],))
            if await cur.fetchone():
                print(f"  ~ Already exists: {p['slug']}")
                skipped += 1
                continue

            # Process image
            try:
                filename = process_image(src_path, p["slug"])
            except Exception as e:
                print(f"  ✗ Image error {p['src']}: {e}")
                skipped += 1
                continue

            cat_id = cat_id_map.get(p["cat"])
            await db.execute(
                """INSERT INTO products
                   (name, slug, description, price, old_price, stock,
                    category_id, image, is_active, is_featured)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?)""",
                (
                    p["name"], p["slug"], p["desc"],
                    p["price"], p.get("old_price"), p["stock"],
                    cat_id, filename, p.get("featured", 0)
                )
            )
            created += 1
            print(f"  ✓ {p['name']}")

        await db.commit()

        print(f"\n{'='*50}")
        print(f"✅ Done! {created} products created, {skipped} skipped.")
        print(f"{'='*50}")
        print("\nStart the server: uvicorn main:app --reload --port 9000")


if __name__ == "__main__":
    asyncio.run(main())
