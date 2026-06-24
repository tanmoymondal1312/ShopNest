import os
import uuid
import hashlib
import math
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from fastapi import (
    FastAPI, Request, Form, File, UploadFile,
    Depends, HTTPException,
)
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.gzip import GZipMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from database import (
    init_db, get_db, get_settings, save_settings,
    fetch_categories, fetch_category_by_slug,
    insert_category, delete_category,
    fetch_products, count_products, fetch_product_by_slug,
    fetch_product_by_id, insert_product, update_product,
    delete_product, fetch_related_products,
    insert_order, fetch_order, fetch_order_items,
    fetch_orders, count_orders, update_order_status,
    fetch_dashboard_stats, fetch_visitor_stats,
)
from auth import (
    require_admin, get_admin_user, authenticate,
    create_session, SESSION_COOKIE,
    check_rate_limit, record_login_attempt,
    NotAuthenticated,
)

UPLOAD_DIR = Path("static/uploads/products")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


# ─── HEAD request middleware (Facebook/WhatsApp link preview sends HEAD) ──────

class HeadMiddleware(BaseHTTPMiddleware):
    """Return 200 for any HEAD request so Facebook/WhatsApp link previews work."""
    async def dispatch(self, request: Request, call_next):
        if request.method == "HEAD":
            from fastapi.responses import Response as _R
            return _R(status_code=200, headers={"content-type": "text/html; charset=utf-8"})
        return await call_next(request)


# ─── Visitor tracking middleware ──────────────────────────────────────────────

SKIP_PREFIXES = ("/static/", "/admin", "/robots.txt", "/sitemap.xml", "/favicon")


class VisitorMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        skip = any(path.startswith(p) for p in SKIP_PREFIXES)
        response = await call_next(request)
        if not skip and request.method == "GET":
            try:
                ip = request.client.host if request.client else "unknown"
                ip_hash = hashlib.sha256(ip.encode()).hexdigest()[:16]
                referrer = request.headers.get("referer", "")
                ua = request.headers.get("user-agent", "")
                async with __import__("aiosqlite").connect("shop.db") as db:
                    await db.execute(
                        "INSERT INTO visitors (path, referrer, user_agent, ip_hash) VALUES (?, ?, ?, ?)",
                        (path, referrer, ua, ip_hash),
                    )
                    await db.commit()
            except Exception:
                pass
        return response


# ─── App setup ────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None)
app.add_middleware(HeadMiddleware)
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(VisitorMiddleware)
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.middleware("http")
async def static_cache_headers(request: Request, call_next):
    response = await call_next(request)
    if request.url.path.startswith("/static/"):
        if request.url.path.startswith("/static/uploads/"):
            response.headers["Cache-Control"] = "public, max-age=86400, stale-while-revalidate=604800"
        else:
            response.headers["Cache-Control"] = "public, max-age=2592000, immutable"
    return response

templates = Jinja2Templates(directory="templates")


def _darken(hex_color: str, amount: int = 28) -> str:
    """Darken a hex color by subtracting `amount` from each channel."""
    h = hex_color.lstrip("#")
    if len(h) != 6:
        return hex_color
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return "#{:02x}{:02x}{:02x}".format(max(0, r-amount), max(0, g-amount), max(0, b-amount))


def _to_rgb(hex_color: str) -> str:
    """Return 'r,g,b' string for use inside rgba()."""
    h = hex_color.lstrip("#")
    if len(h) != 6:
        return "108,99,255"
    return f"{int(h[0:2],16)},{int(h[2:4],16)},{int(h[4:6],16)}"


templates.env.filters["darken"] = _darken
templates.env.filters["to_rgb"] = _to_rgb

from datetime import datetime as _dt
templates.env.globals["current_year"] = lambda: _dt.now().year

def _file_mtime(path: str) -> int:
    """Return file modification time for cache-busting."""
    try:
        return int(os.path.getmtime(path))
    except OSError:
        return 0

templates.env.globals["file_mtime"] = _file_mtime


def _static_url(path: str) -> str:
    """Return /static/path?v=<mtime> so browsers always fetch updated files."""
    import os
    try:
        mtime = int(os.path.getmtime(f"static/{path}"))
    except OSError:
        mtime = 0
    return f"/static/{path}?v={mtime}"

templates.env.globals["static_url"] = _static_url


@app.exception_handler(NotAuthenticated)
async def not_authenticated_handler(request: Request, exc: NotAuthenticated):
    return RedirectResponse("/admin/login", status_code=302)


def flash(response, message: str, category: str = "info"):
    from urllib.parse import quote
    # max_age=8 — enough for one redirect+load, expires before another tab can see it
    response.set_cookie("flash_msg", quote(message), max_age=8, httponly=True, path="/admin")
    response.set_cookie("flash_cat", category, max_age=8, httponly=True, path="/admin")


def get_flash(request: Request) -> dict:
    from urllib.parse import unquote
    raw = request.cookies.get("flash_msg", "")
    msg = unquote(raw) if raw else ""
    cat = request.cookies.get("flash_cat", "info")
    return {"message": msg, "category": cat} if msg else {}




async def ctx(request: Request, db) -> dict:
    """Base template context for shop pages — no flash (flash is admin-only)."""
    s = await get_settings(db)
    return {"request": request, "settings": s, "flash": {}}


# ─── IMAGE UPLOAD HELPER ──────────────────────────────────────────────────────

async def save_image(file: UploadFile, slug: str) -> str:
    from PIL import Image
    import io

    allowed = {"image/jpeg", "image/png", "image/webp"}
    if file.content_type not in allowed:
        raise HTTPException(400, "Only JPG/PNG/WebP images are allowed")

    data = await file.read()
    if len(data) > 5 * 1024 * 1024:
        raise HTTPException(400, "Image must be under 5 MB")

    img = Image.open(io.BytesIO(data)).convert("RGB")
    img.thumbnail((800, 800))

    filename = f"{slug}.webp"
    path = UPLOAD_DIR / filename
    img.save(path, "WEBP", quality=85, optimize=True)

    # Thumbnail 400×400
    thumb = img.copy()
    thumb.thumbnail((400, 400))
    thumb.save(UPLOAD_DIR / f"{slug}_thumb.webp", "WEBP", quality=80)

    return filename


def make_slug(name: str) -> str:
    import re
    slug = name.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_-]+", "-", slug)
    slug = slug.strip("-")
    return slug or "product"


# ─── robots.txt + sitemap.xml ────────────────────────────────────────────────

@app.get("/robots.txt")
async def robots_txt(request: Request):
    from fastapi.responses import PlainTextResponse
    base = str(request.base_url).rstrip("/")
    content = f"User-agent: *\nAllow: /\nDisallow: /admin\nDisallow: /api/\nSitemap: {base}/sitemap.xml\n"
    return PlainTextResponse(content, media_type="text/plain")


@app.get("/sitemap.xml")
async def sitemap_xml(request: Request):
    from fastapi.responses import Response as FastResponse
    base = str(request.base_url).rstrip("/")
    async for db in get_db():
        products   = await fetch_products(db, limit=1000)
        categories = await fetch_categories(db)
    from datetime import datetime
    today = datetime.now().strftime("%Y-%m-%d")
    entries = [f'  <url><loc>{base}/</loc><lastmod>{today}</lastmod><changefreq>daily</changefreq><priority>1.0</priority></url>']
    for cat in categories:
        entries.append(f'  <url><loc>{base}/category/{cat["slug"]}</loc><lastmod>{today}</lastmod><changefreq>weekly</changefreq><priority>0.8</priority></url>')
    for p in products:
        entries.append(f'  <url><loc>{base}/product/{p["slug"]}</loc><lastmod>{p["created_at"][:10] if p["created_at"] else today}</lastmod><changefreq>weekly</changefreq><priority>0.7</priority></url>')
    entries.append(f'  <url><loc>{base}/search</loc><changefreq>weekly</changefreq><priority>0.5</priority></url>')
    xml = f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + "\n".join(entries) + '\n</urlset>'
    return FastResponse(content=xml, media_type="application/xml")


# ─── Search suggestions API ───────────────────────────────────────────────────

@app.get("/api/suggestions")
async def api_suggestions(q: str = ""):
    if len(q.strip()) < 2:
        return JSONResponse([])
    async for db in get_db():
        products = await fetch_products(db, search=q.strip(), limit=7)
        return JSONResponse([
            {"name": p["name"], "slug": p["slug"], "price": p["price"],
             "image": p["image"] or ""}
            for p in products
        ])


# ═══════════════════════════════════════════════════════════════════════════════
#  SHOP ROUTES
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/", response_class=HTMLResponse)
async def homepage(request: Request):
    async for db in get_db():
        base       = await ctx(request, db)
        categories = await fetch_categories(db)
        # Only fetch the 8 featured — products grid loads via /api/products-grid after page paint
        featured   = await fetch_products(db, featured_only=True, limit=8)

        # Slider: up to 7 (featured first, fill from regular if needed)
        slider = list(featured[:7])
        if len(slider) < 7:
            fids  = {p["id"] for p in slider}
            extra = await fetch_products(db, limit=10)
            for p in extra:
                if p["id"] not in fids:
                    slider.append(p)
                if len(slider) == 7:
                    break

        return templates.TemplateResponse(request, "shop/index.html", {
            **base,
            "categories": categories,
            "featured":   featured,
            "slider":     slider,
        })


# ─── Products grid API (AJAX, used by homepage for deferred loading) ─────────

@app.get("/api/products-grid", response_class=HTMLResponse)
async def api_products_grid(
    request: Request,
    page: int = 1,
    cat:  str = "",
    q:    str = "",
):
    async for db in get_db():
        s        = await get_settings(db)
        per_page = 20
        offset   = (page - 1) * per_page

        cat_id = None
        if cat:
            cat_obj = await fetch_category_by_slug(db, cat)
            cat_id  = cat_obj["id"] if cat_obj else None

        search   = q.strip() or None
        total    = await count_products(db, category_id=cat_id, search=search)
        products = await fetch_products(db, category_id=cat_id, search=search,
                                         limit=per_page, offset=offset)
        pages    = math.ceil(total / per_page) if total else 1

        return templates.TemplateResponse(request,
            "shop/partials/product_grid.html",
            {
                "settings": s,
                "products": products,
                "page":     page,
                "pages":    pages,
                "total":    total,
                "cat":      cat,
                "q":        q,
            }
        )


@app.get("/category/{slug}", response_class=HTMLResponse)
async def category_page(slug: str, request: Request, page: int = 1):
    async for db in get_db():
        base = await ctx(request, db)
        category = await fetch_category_by_slug(db, slug)
        if not category:
            raise HTTPException(404)
        per_page = 20
        offset = (page - 1) * per_page
        total = await count_products(db, category_id=category["id"])
        products = await fetch_products(db, category_id=category["id"], limit=per_page, offset=offset)
        categories = await fetch_categories(db)
        pages = math.ceil(total / per_page)
        return templates.TemplateResponse(request,
            "shop/index.html",
            {
                **base,
                "categories": categories,
                "products": products,
                "category": category,
                "featured": [],
                "page": page,
                "pages": pages,
                "total": total,
            },
        )


@app.get("/product/{slug}", response_class=HTMLResponse)
async def product_detail(slug: str, request: Request):
    async for db in get_db():
        base = await ctx(request, db)
        product = await fetch_product_by_slug(db, slug)
        if not product or not product["is_active"]:
            raise HTTPException(404)
        categories = await fetch_categories(db)
        related = []
        if product["category_id"]:
            related = await fetch_related_products(db, product["category_id"], product["id"])
        return templates.TemplateResponse(request,
            "shop/product.html",
            {**base, "product": product, "categories": categories, "related": related},
        )


@app.get("/search", response_class=HTMLResponse)
async def search_page(request: Request, q: str = "", page: int = 1):
    async for db in get_db():
        base = await ctx(request, db)
        categories = await fetch_categories(db)
        products, total, pages = [], 0, 1
        if q.strip():
            per_page = 20
            offset   = (page - 1) * per_page
            total    = await count_products(db, search=q.strip())
            products = await fetch_products(db, search=q.strip(), limit=per_page, offset=offset)
            pages    = math.ceil(total / per_page) if total else 1
        return templates.TemplateResponse(request,
            "shop/search.html",
            {**base, "products": products, "q": q,
             "categories": categories, "page": page, "pages": pages, "total": total},
        )


@app.post("/order")
async def create_order(request: Request):
    async for db in get_db():
        try:
            body = await request.json()
        except Exception:
            return JSONResponse({"error": "Invalid request"}, status_code=400)

        customer_name = body.get("name", "").strip()
        customer_phone = body.get("phone", "").strip()
        address = body.get("address", "").strip()
        note = body.get("note", "").strip()
        items = body.get("items", [])

        if not customer_name or not customer_phone:
            return JSONResponse({"error": "Name and phone are required"}, status_code=400)
        if not items:
            return JSONResponse({"error": "Cart is empty"}, status_code=400)

        order_id = str(uuid.uuid4())[:8].upper()
        total = sum(item["price"] * item["qty"] for item in items)

        order = {
            "id": order_id,
            "customer_name": customer_name,
            "customer_phone": customer_phone,
            "address": address,
            "total": total,
            "note": note,
        }
        order_items = [
            {
                "order_id": order_id,
                "product_id": item.get("id"),
                "product_name": item["name"],
                "price": item["price"],
                "quantity": item["qty"],
            }
            for item in items
        ]

        await insert_order(db, order, order_items)
        return JSONResponse({"order_id": order_id})


@app.get("/order/{order_id}/confirm", response_class=HTMLResponse)
async def order_confirm(order_id: str, request: Request):
    async for db in get_db():
        base = await ctx(request, db)
        order = await fetch_order(db, order_id)
        if not order:
            raise HTTPException(404)
        items = await fetch_order_items(db, order_id)
        return templates.TemplateResponse(request,
            "shop/order-confirm.html",
            {**base, "order": order, "items": items},
        )


# ═══════════════════════════════════════════════════════════════════════════════
#  ADMIN ROUTES
# ═══════════════════════════════════════════════════════════════════════════════

def admin_ctx(request: Request, settings: dict, extra: dict = None) -> dict:
    base = {"request": request, "settings": settings, "flash": get_flash(request)}
    if extra:
        base.update(extra)
    return base


@app.get("/admin/login", response_class=HTMLResponse)
async def admin_login_form(request: Request):
    if get_admin_user(request):
        return RedirectResponse("/admin", status_code=302)
    async for db in get_db():
        s = await get_settings(db)
    return templates.TemplateResponse(request, "admin/login.html", {"request": request, "settings": s, "error": ""})


@app.post("/admin/login")
async def admin_login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
):
    ip = request.client.host if request.client else "unknown"

    if not check_rate_limit(ip):
        async for db in get_db():
            s = await get_settings(db)
        return templates.TemplateResponse(request,
            "admin/login.html",
            {"request": request, "settings": s, "error": "অনেক বেশি চেষ্টা। ১ মিনিট পরে আবার চেষ্টা করুন।"},
            status_code=429,
        )

    record_login_attempt(ip)

    if not authenticate(username, password):
        async for db in get_db():
            s = await get_settings(db)
        return templates.TemplateResponse(request,
            "admin/login.html",
            {"request": request, "settings": s, "error": "ইউজারনেম বা পাসওয়ার্ড ভুল।"},
            status_code=401,
        )

    token = create_session(username)
    response = RedirectResponse("/admin", status_code=302)
    response.set_cookie(
        SESSION_COOKIE,
        token,
        httponly=True,
        samesite="lax",
        max_age=8 * 3600,
    )
    return response


@app.get("/admin/logout")
async def admin_logout():
    response = RedirectResponse("/admin/login", status_code=302)
    response.delete_cookie(SESSION_COOKIE)
    return response


@app.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(request: Request, admin: str = Depends(require_admin)):
    async for db in get_db():
        s = await get_settings(db)
        stats = await fetch_dashboard_stats(db)
        return templates.TemplateResponse(request,
            "admin/dashboard.html",
            {**admin_ctx(request, s), **stats, "admin": admin},
        )


# ─── Admin Products ───────────────────────────────────────────────────────────

@app.get("/admin/products", response_class=HTMLResponse)
async def admin_products(
    request: Request,
    q: str = "",
    cat: str = "",
    page: int = 1,
    admin: str = Depends(require_admin),
):
    async for db in get_db():
        s = await get_settings(db)
        per_page = 20
        offset = (page - 1) * per_page
        cat_id = int(cat) if cat.isdigit() else None
        total = await count_products(db, category_id=cat_id, search=q or None, active_only=False)
        products = await fetch_products(
            db, category_id=cat_id, search=q or None,
            active_only=False, limit=per_page, offset=offset,
        )
        categories = await fetch_categories(db)
        pages = math.ceil(total / per_page) if total else 1
        return templates.TemplateResponse(request,
            "admin/products/list.html",
            {
                **admin_ctx(request, s),
                "products": products,
                "categories": categories,
                "q": q,
                "cat": cat,
                "page": page,
                "pages": pages,
                "total": total,
            },
        )


@app.get("/admin/products/new", response_class=HTMLResponse)
async def admin_product_new_form(request: Request, admin: str = Depends(require_admin)):
    async for db in get_db():
        s = await get_settings(db)
        categories = await fetch_categories(db)
        return templates.TemplateResponse(request,
            "admin/products/form.html",
            {**admin_ctx(request, s), "product": None, "categories": categories},
        )


@app.post("/admin/products/new")
async def admin_product_new_save(
    request: Request,
    name: str = Form(...),
    slug: str = Form(""),
    description: str = Form(""),
    price: float = Form(...),
    old_price: str = Form(""),
    stock: int = Form(0),
    category_id: str = Form(""),
    is_active: str = Form("0"),
    is_featured: str = Form("0"),
    image: UploadFile = File(None),
    admin: str = Depends(require_admin),
):
    async for db in get_db():
        if not slug.strip():
            slug = make_slug(name)

        image_filename = ""
        if image and image.filename:
            image_filename = await save_image(image, slug)

        data = {
            "name": name.strip(),
            "slug": slug.strip(),
            "description": description.strip(),
            "price": price,
            "old_price": float(old_price) if old_price.strip() else None,
            "stock": stock,
            "category_id": int(category_id) if category_id.isdigit() else None,
            "image": image_filename,
            "is_active": 1 if is_active == "1" else 0,
            "is_featured": 1 if is_featured == "1" else 0,
        }
        await insert_product(db, data)
        response = RedirectResponse("/admin/products", status_code=302)
        flash(response, "পণ্য সফলভাবে যোগ করা হয়েছে!", "success")
        return response


@app.get("/admin/products/{product_id}/edit", response_class=HTMLResponse)
async def admin_product_edit_form(
    product_id: int, request: Request, admin: str = Depends(require_admin)
):
    async for db in get_db():
        s = await get_settings(db)
        product = await fetch_product_by_id(db, product_id)
        if not product:
            raise HTTPException(404)
        categories = await fetch_categories(db)
        return templates.TemplateResponse(request,
            "admin/products/form.html",
            {**admin_ctx(request, s), "product": product, "categories": categories},
        )


@app.post("/admin/products/{product_id}/edit")
async def admin_product_edit_save(
    product_id: int,
    request: Request,
    name: str = Form(...),
    slug: str = Form(""),
    description: str = Form(""),
    price: float = Form(...),
    old_price: str = Form(""),
    stock: int = Form(0),
    category_id: str = Form(""),
    is_active: str = Form("0"),
    is_featured: str = Form("0"),
    image: UploadFile = File(None),
    admin: str = Depends(require_admin),
):
    async for db in get_db():
        existing = await fetch_product_by_id(db, product_id)
        if not existing:
            raise HTTPException(404)

        if not slug.strip():
            slug = make_slug(name)

        image_filename = existing["image"] or ""
        if image and image.filename:
            image_filename = await save_image(image, slug)

        data = {
            "name": name.strip(),
            "slug": slug.strip(),
            "description": description.strip(),
            "price": price,
            "old_price": float(old_price) if old_price.strip() else None,
            "stock": stock,
            "category_id": int(category_id) if category_id.isdigit() else None,
            "image": image_filename,
            "is_active": 1 if is_active == "1" else 0,
            "is_featured": 1 if is_featured == "1" else 0,
        }
        await update_product(db, product_id, data)
        response = RedirectResponse("/admin/products", status_code=302)
        flash(response, "পণ্য আপডেট করা হয়েছে!", "success")
        return response


@app.post("/admin/products/{product_id}/delete")
async def admin_product_delete(
    product_id: int, request: Request, admin: str = Depends(require_admin)
):
    async for db in get_db():
        await delete_product(db, product_id)
    response = RedirectResponse("/admin/products", status_code=302)
    flash(response, "পণ্য মুছে ফেলা হয়েছে।", "info")
    return response


# ─── Admin Orders ─────────────────────────────────────────────────────────────

@app.get("/admin/orders", response_class=HTMLResponse)
async def admin_orders(
    request: Request,
    status_filter: str = "all",
    page: int = 1,
    admin: str = Depends(require_admin),
):
    async for db in get_db():
        s = await get_settings(db)
        per_page = 30
        offset = (page - 1) * per_page
        status_val = None if status_filter == "all" else status_filter
        total = await count_orders(db, status=status_val)
        orders = await fetch_orders(db, status=status_val, limit=per_page, offset=offset)
        pages = math.ceil(total / per_page) if total else 1
        return templates.TemplateResponse(request,
            "admin/orders/list.html",
            {
                **admin_ctx(request, s),
                "orders": orders,
                "status_filter": status_filter,
                "page": page,
                "pages": pages,
                "total": total,
            },
        )


@app.get("/admin/orders/{order_id}", response_class=HTMLResponse)
async def admin_order_detail(
    order_id: str, request: Request, admin: str = Depends(require_admin)
):
    async for db in get_db():
        s = await get_settings(db)
        order = await fetch_order(db, order_id)
        if not order:
            raise HTTPException(404)
        items = await fetch_order_items(db, order_id)
        return templates.TemplateResponse(request,
            "admin/orders/detail.html",
            {**admin_ctx(request, s), "order": order, "items": items},
        )


@app.post("/admin/orders/{order_id}/status")
async def admin_order_status(
    order_id: str,
    request: Request,
    new_status: str = Form(...),
    admin: str = Depends(require_admin),
):
    async for db in get_db():
        await update_order_status(db, order_id, new_status)
    response = RedirectResponse(f"/admin/orders/{order_id}", status_code=302)
    flash(response, "অর্ডার স্ট্যাটাস আপডেট হয়েছে!", "success")
    return response


# ─── Admin Categories ─────────────────────────────────────────────────────────

@app.get("/admin/categories", response_class=HTMLResponse)
async def admin_categories(request: Request, admin: str = Depends(require_admin)):
    async for db in get_db():
        s = await get_settings(db)
        categories = await fetch_categories(db)
        return templates.TemplateResponse(request,
            "admin/categories.html",
            {**admin_ctx(request, s), "categories": categories},
        )


@app.post("/admin/categories")
async def admin_category_add(
    request: Request,
    name: str = Form(...),
    sort_order: int = Form(0),
    admin: str = Depends(require_admin),
):
    slug = make_slug(name)
    async for db in get_db():
        await insert_category(db, name.strip(), slug, sort_order)
    response = RedirectResponse("/admin/categories", status_code=302)
    flash(response, "ক্যাটাগরি যোগ করা হয়েছে!", "success")
    return response


@app.post("/admin/categories/{category_id}/delete")
async def admin_category_delete(
    category_id: int, request: Request, admin: str = Depends(require_admin)
):
    async for db in get_db():
        await delete_category(db, category_id)
    response = RedirectResponse("/admin/categories", status_code=302)
    flash(response, "ক্যাটাগরি মুছে ফেলা হয়েছে।", "info")
    return response


# ─── Admin Visitors ───────────────────────────────────────────────────────────

@app.get("/admin/visitors", response_class=HTMLResponse)
async def admin_visitors(
    request: Request,
    period: str = "today",
    admin: str = Depends(require_admin),
):
    async for db in get_db():
        s = await get_settings(db)
        stats = await fetch_visitor_stats(db, period)
        return templates.TemplateResponse(request,
            "admin/visitors.html",
            {**admin_ctx(request, s), **stats, "period": period},
        )


# ─── Admin Settings ───────────────────────────────────────────────────────────

@app.get("/admin/settings", response_class=HTMLResponse)
async def admin_settings_form(request: Request, admin: str = Depends(require_admin)):
    async for db in get_db():
        s = await get_settings(db)
        return templates.TemplateResponse(request,
            "admin/settings.html",
            {**admin_ctx(request, s), "s": s},
        )


@app.post("/admin/settings")
async def admin_settings_save(
    request: Request,
    store_name: str = Form(...),
    tagline: str = Form(""),
    hero_tagline: str = Form(""),
    whatsapp: str = Form(""),
    currency_symbol: str = Form("৳"),
    accent_color: str = Form("#6c63ff"),
    footer_text: str = Form(""),
    social_facebook:  str = Form(""),
    social_instagram: str = Form(""),
    social_youtube:   str = Form(""),
    social_twitter:   str = Form(""),
    social_tiktok:    str = Form(""),
    seo_title:           str = Form(""),
    seo_description:     str = Form(""),
    seo_keywords:        str = Form(""),
    seo_product_suffix:  str = Form(""),
    seo_category_suffix: str = Form(""),
    seo_alt_suffix:      str = Form(""),
    logo:         UploadFile = File(None),
    social_image: UploadFile = File(None),
    admin: str = Depends(require_admin),
):
    async for db in get_db():
        updates = {
            "store_name":       store_name.strip(),
            "tagline":          tagline.strip(),
            "hero_tagline":     hero_tagline.strip(),
            "whatsapp":         whatsapp.strip(),
            "currency_symbol":  currency_symbol.strip(),
            "accent_color":     accent_color.strip(),
            "footer_text":      footer_text.strip(),
            "social_facebook":  social_facebook.strip(),
            "social_instagram": social_instagram.strip(),
            "social_youtube":   social_youtube.strip(),
            "social_twitter":   social_twitter.strip(),
            "social_tiktok":    social_tiktok.strip(),
            "seo_title":           seo_title.strip(),
            "seo_description":     seo_description.strip(),
            "seo_keywords":        seo_keywords.strip(),
            "seo_product_suffix":  seo_product_suffix.strip(),
            "seo_category_suffix": seo_category_suffix.strip(),
            "seo_alt_suffix":      seo_alt_suffix.strip(),
        }
        if logo and logo.filename:
            from PIL import Image
            import io
            data = await logo.read()
            img = Image.open(io.BytesIO(data)).convert("RGB")
            img.thumbnail((400, 200))
            logo_path = Path("static/uploads") / "logo.webp"
            img.save(logo_path, "WEBP", quality=90)
            updates["logo"] = "uploads/logo.webp"

        if social_image and social_image.filename:
            from PIL import Image
            import io
            data = await social_image.read()
            img = Image.open(io.BytesIO(data)).convert("RGB")
            # OG standard: 1200×630 — must for Facebook/WhatsApp/LinkedIn preview
            img = img.resize((1200, 630), Image.LANCZOS)
            si_path = Path("static/uploads") / "social_image.webp"
            img.save(si_path, "WEBP", quality=90)
            updates["social_image"] = "uploads/social_image.webp"

        await save_settings(db, updates)

    response = RedirectResponse("/admin/settings", status_code=302)
    flash(response, "সেটিংস সংরক্ষণ করা হয়েছে!", "success")
    return response
