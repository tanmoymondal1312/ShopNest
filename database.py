import aiosqlite
from typing import Optional

DB_PATH = "shop.db"

_settings_cache: Optional[dict] = None


async def get_db():
    db = await aiosqlite.connect(DB_PATH)
    db.row_factory = aiosqlite.Row
    try:
        yield db
    finally:
        await db.close()


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        await db.executescript("""
        PRAGMA journal_mode=WAL;
        PRAGMA foreign_keys=ON;

        CREATE TABLE IF NOT EXISTS categories (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            name       TEXT NOT NULL,
            slug       TEXT UNIQUE NOT NULL,
            sort_order INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS products (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT NOT NULL,
            slug        TEXT UNIQUE NOT NULL,
            description TEXT,
            price       REAL NOT NULL,
            old_price   REAL,
            stock       INTEGER DEFAULT 0,
            category_id INTEGER REFERENCES categories(id),
            image       TEXT,
            sizes       TEXT DEFAULT '',
            is_active   INTEGER DEFAULT 1,
            is_featured INTEGER DEFAULT 0,
            created_at  TEXT DEFAULT (datetime('now'))
        );

        CREATE INDEX IF NOT EXISTS idx_products_slug     ON products(slug);
        CREATE INDEX IF NOT EXISTS idx_products_category ON products(category_id);
        CREATE INDEX IF NOT EXISTS idx_products_active   ON products(is_active);
        CREATE INDEX IF NOT EXISTS idx_products_featured ON products(is_featured);

        CREATE TABLE IF NOT EXISTS orders (
            id             TEXT PRIMARY KEY,
            customer_name  TEXT NOT NULL,
            customer_phone TEXT NOT NULL,
            address        TEXT,
            total          REAL NOT NULL,
            status         TEXT DEFAULT 'pending',
            note           TEXT,
            created_at     TEXT DEFAULT (datetime('now'))
        );

        CREATE INDEX IF NOT EXISTS idx_orders_status  ON orders(status);
        CREATE INDEX IF NOT EXISTS idx_orders_created ON orders(created_at);

        CREATE TABLE IF NOT EXISTS order_items (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id     TEXT REFERENCES orders(id),
            product_id   INTEGER REFERENCES products(id),
            product_name TEXT NOT NULL,
            price        REAL NOT NULL,
            quantity     INTEGER NOT NULL,
            size         TEXT DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS visitors (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            path       TEXT NOT NULL,
            referrer   TEXT,
            user_agent TEXT,
            ip_hash    TEXT,
            visited_at TEXT DEFAULT (datetime('now'))
        );

        CREATE INDEX IF NOT EXISTS idx_visitors_path    ON visitors(path);
        CREATE INDEX IF NOT EXISTS idx_visitors_visited ON visitors(visited_at);

        CREATE TABLE IF NOT EXISTS settings (
            key   TEXT PRIMARY KEY,
            value TEXT
        );

        CREATE TABLE IF NOT EXISTS hero_products (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER REFERENCES products(id) ON DELETE CASCADE,
            sort_order INTEGER DEFAULT 0,
            is_active  INTEGER DEFAULT 1
        );
        CREATE UNIQUE INDEX IF NOT EXISTS idx_hero_product ON hero_products(product_id);
        """)

        # ── Migrations for databases created before a column existed ──
        for table, column, ddl in (
            ("products",    "sizes", "TEXT DEFAULT ''"),
            ("order_items", "size",  "TEXT DEFAULT ''"),
        ):
            cursor = await db.execute(f"PRAGMA table_info({table})")
            existing = {row[1] for row in await cursor.fetchall()}
            if column not in existing:
                await db.execute(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")

        defaults = [
            ("store_name",       "ShopNest"),
            ("tagline",          "Fresh products, fast delivery"),
            ("hero_tagline",     "আপনার পছন্দের পণ্য, সেরা দামে — সারাদেশে দ্রুত ডেলিভারি"),
            ("whatsapp",         ""),
            ("whatsapp_cc",      "880"),
            ("currency_symbol",  "৳"),
            ("logo",             ""),
            ("accent_color",     "#6c63ff"),
            ("footer_text",      ""),
            ("social_image",      ""),
            ("social_facebook",  ""),
            ("social_instagram", ""),
            ("social_youtube",   ""),
            ("social_twitter",   ""),
            ("social_tiktok",    ""),
            # SEO
            ("seo_title",           "ShopNest — সেরা দামে অনলাইন শপিং বাংলাদেশ"),
            ("seo_description",     "ShopNest-এ পোশাক, গ্যাজেট, মুদি পণ্য সেরা দামে কিনুন। সারাদেশে দ্রুত ডেলিভারি ও নিরাপদ পেমেন্ট।"),
            ("seo_keywords",        "অনলাইন শপিং, বাংলাদেশ, পোশাক, গ্যাজেট, মুদি পণ্য, সেরা দাম"),
            ("seo_product_suffix",  "সেরা দামে কিনুন"),
            ("seo_category_suffix", "সেরা দামে কিনুন"),
            ("seo_alt_suffix",      "সেরা দামে কিনুন"),
        ]
        for key, value in defaults:
            await db.execute(
                "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
                (key, value),
            )

        await db.commit()


def invalidate_settings_cache():
    global _settings_cache
    _settings_cache = None


async def get_settings(db) -> dict:
    global _settings_cache
    if _settings_cache is None:
        cursor = await db.execute("SELECT key, value FROM settings")
        rows = await cursor.fetchall()
        _settings_cache = {row["key"]: row["value"] for row in rows}
    return _settings_cache


# ─── Categories ──────────────────────────────────────────────────────────────

async def fetch_categories(db) -> list:
    cursor = await db.execute("SELECT * FROM categories ORDER BY sort_order, name")
    return await cursor.fetchall()


async def fetch_category_by_slug(db, slug: str):
    cursor = await db.execute("SELECT * FROM categories WHERE slug = ?", (slug,))
    return await cursor.fetchone()


async def insert_category(db, name: str, slug: str, sort_order: int = 0):
    await db.execute(
        "INSERT INTO categories (name, slug, sort_order) VALUES (?, ?, ?)",
        (name, slug, sort_order),
    )
    await db.commit()


async def delete_category(db, category_id: int):
    await db.execute("DELETE FROM categories WHERE id = ?", (category_id,))
    await db.commit()


# ─── Products ─────────────────────────────────────────────────────────────────

async def fetch_products(
    db,
    *,
    category_id: Optional[int] = None,
    search: Optional[str] = None,
    active_only: bool = True,
    featured_only: bool = False,
    limit: int = 20,
    offset: int = 0,
) -> list:
    conditions = []
    params: list = []

    if active_only:
        conditions.append("p.is_active = 1")
    if featured_only:
        conditions.append("p.is_featured = 1")
    if category_id is not None:
        conditions.append("p.category_id = ?")
        params.append(category_id)
    if search:
        conditions.append("(p.name LIKE ? OR p.description LIKE ? OR p.slug LIKE ?)")
        params += [f"%{search}%", f"%{search}%", f"%{search}%"]

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    sql = f"""
        SELECT p.*, c.name AS category_name
        FROM products p
        LEFT JOIN categories c ON p.category_id = c.id
        {where}
        ORDER BY p.created_at DESC
        LIMIT ? OFFSET ?
    """
    params += [limit, offset]
    cursor = await db.execute(sql, params)
    return await cursor.fetchall()


async def count_products(
    db,
    *,
    category_id: Optional[int] = None,
    search: Optional[str] = None,
    active_only: bool = True,
) -> int:
    conditions = []
    params: list = []

    if active_only:
        conditions.append("is_active = 1")
    if category_id is not None:
        conditions.append("category_id = ?")
        params.append(category_id)
    if search:
        conditions.append("(name LIKE ? OR description LIKE ? OR slug LIKE ?)")
        params += [f"%{search}%", f"%{search}%", f"%{search}%"]

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    cursor = await db.execute(f"SELECT COUNT(*) FROM products {where}", params)
    row = await cursor.fetchone()
    return row[0]


async def fetch_product_by_slug(db, slug: str):
    cursor = await db.execute(
        """SELECT p.*, c.name AS category_name, c.slug AS category_slug
           FROM products p LEFT JOIN categories c ON p.category_id = c.id
           WHERE p.slug = ?""",
        (slug,),
    )
    return await cursor.fetchone()


async def fetch_product_by_id(db, product_id: int):
    cursor = await db.execute(
        """SELECT p.*, c.name AS category_name
           FROM products p LEFT JOIN categories c ON p.category_id = c.id
           WHERE p.id = ?""",
        (product_id,),
    )
    return await cursor.fetchone()


async def insert_product(db, data: dict) -> int:
    cursor = await db.execute(
        """INSERT INTO products
           (name, slug, description, price, old_price, stock, category_id,
            image, sizes, is_active, is_featured)
           VALUES (:name, :slug, :description, :price, :old_price, :stock,
                   :category_id, :image, :sizes, :is_active, :is_featured)""",
        data,
    )
    await db.commit()
    return cursor.lastrowid


async def update_product(db, product_id: int, data: dict):
    data["id"] = product_id
    await db.execute(
        """UPDATE products SET
           name=:name, slug=:slug, description=:description, price=:price,
           old_price=:old_price, stock=:stock, category_id=:category_id,
           image=:image, sizes=:sizes, is_active=:is_active, is_featured=:is_featured
           WHERE id=:id""",
        data,
    )
    await db.commit()


async def delete_product(db, product_id: int):
    await db.execute("DELETE FROM products WHERE id = ?", (product_id,))
    await db.commit()


async def fetch_related_products(db, category_id: int, exclude_id: int, limit: int = 4) -> list:
    cursor = await db.execute(
        """SELECT * FROM products
           WHERE category_id = ? AND id != ? AND is_active = 1
           ORDER BY RANDOM() LIMIT ?""",
        (category_id, exclude_id, limit),
    )
    return await cursor.fetchall()


# ─── Orders ───────────────────────────────────────────────────────────────────

async def insert_order(db, order: dict, items: list) -> str:
    await db.execute(
        """INSERT INTO orders (id, customer_name, customer_phone, address, total, note)
           VALUES (:id, :customer_name, :customer_phone, :address, :total, :note)""",
        order,
    )
    for item in items:
        await db.execute(
            """INSERT INTO order_items (order_id, product_id, product_name, price, quantity, size)
               VALUES (:order_id, :product_id, :product_name, :price, :quantity, :size)""",
            item,
        )
    await db.commit()
    return order["id"]


async def fetch_order(db, order_id: str):
    cursor = await db.execute("SELECT * FROM orders WHERE id = ?", (order_id,))
    return await cursor.fetchone()


async def fetch_order_items(db, order_id: str) -> list:
    cursor = await db.execute(
        """SELECT oi.*, p.image FROM order_items oi
           LEFT JOIN products p ON oi.product_id = p.id
           WHERE oi.order_id = ?""",
        (order_id,),
    )
    return await cursor.fetchall()


async def fetch_orders(db, status: Optional[str] = None, limit: int = 50, offset: int = 0) -> list:
    if status and status != "all":
        cursor = await db.execute(
            "SELECT * FROM orders WHERE status = ? ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (status, limit, offset),
        )
    else:
        cursor = await db.execute(
            "SELECT * FROM orders ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (limit, offset),
        )
    return await cursor.fetchall()


async def count_orders(db, status: Optional[str] = None) -> int:
    if status and status != "all":
        cursor = await db.execute("SELECT COUNT(*) FROM orders WHERE status = ?", (status,))
    else:
        cursor = await db.execute("SELECT COUNT(*) FROM orders")
    row = await cursor.fetchone()
    return row[0]


async def update_order_status(db, order_id: str, status: str):
    await db.execute("UPDATE orders SET status = ? WHERE id = ?", (status, order_id))
    await db.commit()


# ─── Dashboard stats ──────────────────────────────────────────────────────────

async def fetch_dashboard_stats(db) -> dict:
    today = "date('now')"

    c = await db.execute(f"SELECT COUNT(*) FROM orders WHERE date(created_at) = {today}")
    orders_today = (await c.fetchone())[0]

    c = await db.execute(f"SELECT COALESCE(SUM(total),0) FROM orders WHERE date(created_at) = {today}")
    revenue_today = (await c.fetchone())[0]

    c = await db.execute("SELECT COUNT(*) FROM products WHERE is_active = 1")
    total_products = (await c.fetchone())[0]

    c = await db.execute(f"SELECT COUNT(DISTINCT ip_hash) FROM visitors WHERE date(visited_at) = {today}")
    visitors_today = (await c.fetchone())[0]

    c = await db.execute(
        """SELECT date(created_at) AS day, COUNT(*) AS cnt
           FROM orders
           WHERE created_at >= datetime('now', '-7 days')
           GROUP BY day ORDER BY day""",
    )
    orders_chart = await c.fetchall()

    c = await db.execute(
        "SELECT * FROM orders ORDER BY created_at DESC LIMIT 10"
    )
    recent_orders = await c.fetchall()

    c = await db.execute(
        "SELECT * FROM products WHERE stock < 5 AND is_active = 1 ORDER BY stock ASC LIMIT 10"
    )
    low_stock = await c.fetchall()

    return {
        "orders_today": orders_today,
        "revenue_today": revenue_today,
        "total_products": total_products,
        "visitors_today": visitors_today,
        "orders_chart": orders_chart,
        "recent_orders": recent_orders,
        "low_stock": low_stock,
    }


# ─── Visitors ─────────────────────────────────────────────────────────────────

async def insert_visitor(db, path: str, referrer: str, user_agent: str, ip_hash: str):
    await db.execute(
        "INSERT INTO visitors (path, referrer, user_agent, ip_hash) VALUES (?, ?, ?, ?)",
        (path, referrer, user_agent, ip_hash),
    )
    await db.commit()


async def fetch_visitor_stats(db, period: str = "today") -> dict:
    if period == "today":
        since = "datetime('now', 'start of day')"
    elif period == "week":
        since = "datetime('now', '-7 days')"
    else:
        since = "datetime('now', 'start of month')"

    c = await db.execute(f"SELECT COUNT(*) FROM visitors WHERE visited_at >= {since}")
    total_views = (await c.fetchone())[0]

    c = await db.execute(
        f"SELECT COUNT(DISTINCT ip_hash) FROM visitors WHERE visited_at >= {since}"
    )
    unique_visitors = (await c.fetchone())[0]

    c = await db.execute(
        f"""SELECT path, COUNT(*) AS views
            FROM visitors WHERE visited_at >= {since}
            GROUP BY path ORDER BY views DESC LIMIT 10"""
    )
    top_pages = await c.fetchall()

    c = await db.execute(
        f"""SELECT strftime('%Y-%m-%d %H:%M', visited_at) AS ts, path, referrer, user_agent
            FROM visitors WHERE visited_at >= {since}
            ORDER BY visited_at DESC LIMIT 50"""
    )
    recent = await c.fetchall()

    c = await db.execute(
        f"""SELECT date(visited_at) AS day, COUNT(*) AS cnt
            FROM visitors WHERE visited_at >= {since}
            GROUP BY day ORDER BY day"""
    )
    chart = await c.fetchall()

    return {
        "total_views": total_views,
        "unique_visitors": unique_visitors,
        "top_pages": top_pages,
        "recent": recent,
        "chart": chart,
    }


# ─── Settings ─────────────────────────────────────────────────────────────────

async def save_settings(db, updates: dict):
    for key, value in updates.items():
        await db.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, value),
        )
    await db.commit()
    invalidate_settings_cache()


# ─── Hero Slider ──────────────────────────────────────────────────────────────

async def fetch_hero_products(db) -> list:
    """Active hero items joined with products — for the homepage slider."""
    cursor = await db.execute(
        """SELECT h.id, h.product_id, h.sort_order, h.is_active,
                  p.name, p.slug, p.image, p.price, p.old_price, p.stock
           FROM hero_products h
           JOIN products p ON p.id = h.product_id
           WHERE h.is_active = 1 AND p.is_active = 1
           ORDER BY h.sort_order ASC"""
    )
    return await cursor.fetchall()


async def fetch_all_hero_rows(db) -> list:
    """All hero items (including inactive) — for the admin panel."""
    cursor = await db.execute(
        """SELECT h.id, h.product_id, h.sort_order, h.is_active,
                  p.name, p.slug, p.image, p.price, p.old_price, p.stock
           FROM hero_products h
           JOIN products p ON p.id = h.product_id
           ORDER BY h.sort_order ASC"""
    )
    return await cursor.fetchall()


async def add_hero_product(db, product_id: int):
    cursor = await db.execute("SELECT COALESCE(MAX(sort_order), -1) FROM hero_products")
    row = await cursor.fetchone()
    await db.execute(
        "INSERT OR IGNORE INTO hero_products (product_id, sort_order) VALUES (?, ?)",
        (product_id, row[0] + 1),
    )
    await db.commit()


async def remove_hero_product(db, hero_id: int):
    await db.execute("DELETE FROM hero_products WHERE id = ?", (hero_id,))
    await db.commit()


async def toggle_hero_active(db, hero_id: int):
    await db.execute(
        "UPDATE hero_products SET is_active = 1 - is_active WHERE id = ?", (hero_id,)
    )
    await db.commit()


async def save_hero_order(db, ordered_ids: list):
    for i, hero_id in enumerate(ordered_ids):
        await db.execute("UPDATE hero_products SET sort_order = ? WHERE id = ?", (i, hero_id))
    await db.commit()
