import json
from base64 import b64decode
from urllib.parse import quote, unquote

import aiohttp
from aiohttp import web
from bs4 import BeautifulSoup as Soup

from config import Config

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Origin": "https://animelib.org",
    "Referer": "https://animelib.org/",
    "Accept": "application/json, text/plain, */*",
}
KODIK_HEADERS = {
    "User-Agent": HEADERS["User-Agent"],
    "Referer": "https://kodikplayer.com/",
}

_kodik_crypt_step = {"rot": None}
_post_link_cache = {}

# ---------------------------------------------------------------------------
# CSS — flexbox вместо grid для совместимости со старыми TV-браузерами
# ---------------------------------------------------------------------------
CSS = """
* { box-sizing: border-box; }
body { background:#0f0f12; color:#eaeaf0; font-family:"Segoe UI",Arial,sans-serif; margin:0; padding:0 0 40px; }
a { text-decoration:none; color:inherit; }
html.no-js body, html.js body { padding-top: 78px; }
.header { width:100%; display:flex; justify-content:space-between; align-items:center; gap:20px; padding:18px 30px; background:#17171b; border-bottom:1px solid #26262c; position:fixed; top:0; z-index:10; flex-wrap:wrap; }
.logo { font-size:22px; font-weight:800; color:#00d68f; white-space:nowrap; }
.search-form { display:flex; gap:10px; flex-grow:1; max-width:500px; min-width:220px; }
.search-input { flex-grow:1; padding:10px 16px; font-size:16px; background:#0f0f12; border:2px solid #2a2a30; color:white; border-radius:8px; min-width:0; }
.search-input:focus { border-color:#00d68f; }
.btn { padding:10px 20px; font-size:15px; background:#00875f; color:white; border:none; border-radius:8px; cursor:pointer; font-weight:600; display:inline-block; white-space:nowrap; }
.btn:hover, .btn:focus { background:#00a876; }
.btn-outline { background:transparent; border:2px solid #00d68f; color:#00d68f; }
.btn-outline:hover, .btn-outline:focus { background:rgba(0,214,143,0.12); }
.container { padding:30px; max-width:1400px; margin:0 auto; }
h2 { font-weight:700; margin-bottom:20px; }
h3 { font-weight:700; margin:24px 0 12px; font-size:17px; color:#9a9aa5; }

/* --- Сетка карточек: flexbox с фиксированной шириной, надёжно на TV --- */
.grid { display:flex; flex-wrap:wrap; gap:22px; }
.card { flex:0 0 200px; width:200px; background:#1a1a1f; border-radius:12px; overflow:hidden; border:2px solid transparent; transition:transform .15s,border-color .15s; }
.card:hover, .card:focus { border-color:#00d68f; transform:translateY(-4px); }
.card img { width:100%; height:270px; object-fit:cover; display:block; background:#26262c; }
.card-title { padding:12px; font-size:15px; font-weight:600; line-height:1.3; min-height:40px; }
.badge { display:inline-block; background:#26262c; color:#9a9aa5; font-size:12px; padding:3px 8px; border-radius:6px; margin:0 12px 10px; }

/* --- Список серий: тоже flexbox с фиксированной шириной --- */
.ep-list { display:flex; flex-wrap:wrap; gap:12px; margin-top:20px; }
.ep-btn { flex:0 0 160px; width:160px; background:#1a1a1f; padding:14px 16px; border-radius:10px; border:2px solid #2a2a30; text-align:center; font-size:15px; font-weight:600; }
.ep-btn:hover, .ep-btn:focus { border-color:#00d68f; background:#22222a; }

.pill-list { display:flex; flex-wrap:wrap; gap:10px; margin:0 0 20px; }
.pill { background:#1a1a1f; padding:8px 16px; border-radius:20px; border:2px solid #2a2a30; font-size:14px; white-space:nowrap; }
.pill.active { border-color:#00d68f; color:#00d68f; background:rgba(0,214,143,0.1); }

.player-wrap { text-align:center; }
.player-shell { max-width:1100px; margin:0 auto; background:#17171b; border-radius:20px; padding:20px; box-shadow:0 20px 60px rgba(0,0,0,0.5); }
.player-shell video { width:100%; max-height:70vh; border-radius:14px; display:block; background:black; }
.info { color:#9a9aa5; font-size:14px; margin-top:14px; }
.empty { color:#9a9aa5; padding:40px; text-align:center; font-size:17px; }
.back-link { display:inline-block; margin-bottom:16px; color:#00d68f; font-weight:600; }
.actions { display:flex; gap:12px; justify-content:center; margin-top:16px; flex-wrap:wrap; }
.pager { display:flex; gap:10px; justify-content:center; margin-top:30px; }

.search-wrap { position: relative; flex-grow: 1; max-width: 500px; min-width: 220px; }
.suggest-box {
    display: none;
    position: absolute;
    top: 110%;
    left: 0;
    right: 0;
    background: #1a1a1f;
    border: 2px solid #2a2a30;
    border-radius: 10px;
    overflow: hidden;
    z-index: 200;
    max-height: 400px;
    overflow-y: auto;
}
html.js .suggest-box.active { display: block; }
.suggest-item {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 10px 14px;
    font-size: 14px;
}
.suggest-item:hover { background: #26262c; }
.suggest-item img { width: 32px; height: 44px; object-fit: cover; border-radius: 4px; flex-shrink: 0; }
.ep-nav {
    display: flex;
    justify-content: center;
    align-items: center;
    gap: 14px;
    margin-top: 28px;
    flex-wrap: wrap;
}
.btn-disabled {
    padding: 10px 20px;
    font-size: 15px;
    background: #1a1a1f;
    color: #55555c;
    border: 2px solid #26262c;
    border-radius: 8px;
    cursor: default;
    font-weight: 600;
    display: inline-block;
}
"""

# ---------------------------------------------------------------------------
# API animelib/hentaicdn
# ---------------------------------------------------------------------------

async def api_request(session, url):
    try:
        async with session.get(url, headers=HEADERS, timeout=aiohttp.ClientTimeout(total=15)) as resp:
            return await resp.json()
    except Exception as e:
        print(f"[API ERROR] {url} -> {e}")
        return None


async def search_anime(session, query):
    url = f"https://hapi.hentaicdn.org/api/anime?fields[]=rate_avg&fields[]=rate&fields[]=releaseDate&q={quote(query)}"
    res = await api_request(session, url)
    return res.get("data", []) if res else []


async def get_catalog(session, page=1):
    url = (f"https://hapi.hentaicdn.org/api/anime?fields[]=rate&fields[]=rate_avg"
           f"&fields[]=userBookmark&site_id[]=5&page={page}")
    res = await api_request(session, url)
    if not res:
        return [], 1, False
    meta = res.get("meta", {})
    links = res.get("links", {})
    return res.get("data", []), meta.get("current_page", 1), bool(links.get("next"))


async def get_episodes(session, anime_id):
    res = await api_request(session, f"https://hapi.hentaicdn.org/api/episodes?anime_id={anime_id}")
    return res.get("data", []) if res else []


async def get_episode_details(session, episode_id):
    res = await api_request(session, f"https://hapi.hentaicdn.org/api/episodes/{episode_id}")
    return res.get("data", {}) if res else {}


async def get_anime_details(session, anime_id):
    res = await api_request(session, f"https://hapi.hentaicdn.org/api/anime/{anime_id}")
    return res.get("data", {}) if res else {}

# ---------------------------------------------------------------------------
# Kodik resolver
# ---------------------------------------------------------------------------

def _convert_char(ch, num):
    low = ch.islower()
    alph = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    if ch.upper() in alph:
        out = alph[(alph.index(ch.upper()) + num) % 26]
        return out.lower() if low else out
    return ch


def _decrypt_kodik_string(string):
    rot = _kodik_crypt_step["rot"]
    candidates = [rot] if rot is not None else range(26)
    for r in candidates:
        shifted = "".join(_convert_char(c, r) for c in string)
        pad = (4 - len(shifted) % 4) % 4
        shifted += "=" * pad
        try:
            result = b64decode(shifted).decode("utf-8")
            if "mp4:hls:manifest" in result:
                _kodik_crypt_step["rot"] = r
                return result
        except Exception:
            continue
    raise ValueError("Не удалось расшифровать ссылку Kodik")


async def _get_post_link(session, script_url):
    if script_url in _post_link_cache:
        return _post_link_cache[script_url]
    async with session.get(f"https://kodikplayer.com{script_url}", headers=KODIK_HEADERS, timeout=aiohttp.ClientTimeout(total=15)) as resp:
        resp.raise_for_status()
        text = await resp.text()
    b64_part = text[text.find("$.ajax") + 30: text.find("cache:!1") - 3]
    result = b64decode(b64_part.encode()).decode()
    _post_link_cache[script_url] = result
    return result


def _extract_vinfo_field(hash_container, field):
    marker = f".{field} = '"
    idx = hash_container.find(marker)
    raw = hash_container[idx + len(marker):]
    return raw[: raw.find("'")]


async def resolve_kodik_links(session, kodik_src):
    url = f"https:{kodik_src}" if kodik_src.startswith("//") else kodik_src

    async with session.get(url, headers=KODIK_HEADERS, timeout=aiohttp.ClientTimeout(total=15)) as resp:
        resp.raise_for_status()
        html = await resp.text()

    url_params_raw = html[html.find("urlParams") + 13:]
    url_params = json.loads(url_params_raw[: url_params_raw.find(";") - 1])

    soup = Soup(html, "html.parser")
    scripts = soup.find_all("script")
    script_url = scripts[1].get("src")
    hash_container = scripts[4].text

    video_type = _extract_vinfo_field(hash_container, "type")
    video_hash = _extract_vinfo_field(hash_container, "hash")
    video_id = _extract_vinfo_field(hash_container, "id")

    params = {
        "hash": video_hash, "id": video_id, "type": video_type,
        "d": url_params["d"], "d_sign": url_params["d_sign"],
        "pd": url_params["pd"], "pd_sign": url_params["pd_sign"],
        "ref": unquote(url_params["ref"]), "ref_sign": url_params["ref_sign"],
        "bad_user": "false", "cdn_is_working": "true",
    }

    post_link = await _get_post_link(session, script_url)
    async with session.post(
        f"https://kodikplayer.com{post_link}", data=params,
        headers={**KODIK_HEADERS, "Content-Type": "application/x-www-form-urlencoded"},
        timeout=aiohttp.ClientTimeout(total=15),
    ) as resp:
        if resp.status != 200:
            text = await resp.text()
            raise ValueError(f"Kodik HTTP {resp.status}: {text[:200]}")
        try:
            data = await resp.json(content_type=None)
        except Exception:
            text = await resp.text()
            raise ValueError(f"Kodik вернул не JSON: {text[:200]}")

    if "error" in data:
        raise ValueError(f"Kodik error: {data['error']}")

    raw_360 = data["links"]["360"][0]["src"]
    decoded = raw_360 if "mp4:hls:manifest" in raw_360 else _decrypt_kodik_string(raw_360)

    if decoded.startswith("//"):
        decoded = "https:" + decoded
    elif not decoded.startswith("http"):
        decoded = "https://" + decoded

    folder = decoded[: decoded.rfind("/") + 1]
    available = sorted((int(q) for q in data["links"].keys()), reverse=True)
    return {q: f"{folder}{q}.mp4:hls:manifest.m3u8" for q in available}

# ---------------------------------------------------------------------------
# Плееры
# ---------------------------------------------------------------------------

def extract_players(players):
    result = []
    for p in players:
        team_name = (p.get("team") or {}).get("name", "??")
        tr_label = (p.get("translation_type") or {}).get("label", "")
        label = f"{team_name} ({tr_label})" if tr_label else team_name

        if p.get("player") in ("Animelib", "Hentailib") and "video" in p:
            qualities = p["video"].get("quality", [])
            if qualities:
                sorted_q = sorted(qualities, key=lambda x: int(x.get("quality", 0)), reverse=True)
                href = sorted_q[0].get("href", "")
                if href.startswith("//"):
                    href = f"https:{href}"
                elif href.startswith("/"):
                    href = f"https://hentaicdn.org{href}"
                result.append({"label": label, "kind": "direct", "src": href})
                continue

        if p.get("player") == "Kodik" and "src" in p:
            result.append({"label": label, "kind": "kodik", "src": p["src"]})
    return result

# ---------------------------------------------------------------------------
# HTML
# ---------------------------------------------------------------------------

def render_page(content, title="AniProxy"):
    return f"""<!DOCTYPE html>
<html lang="ru" class="no-js">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>{CSS}</style>
</head>
<body>
<div class="header">
    <a href="/" class="logo">🎬 AniProxy</a>
    <form action="/search" method="GET" class="search-form" id="search-form">
        <div class="search-wrap">
            <input type="text" name="q" id="search-input" class="search-input" placeholder="Поиск аниме..." autocomplete="off" required>
            <div class="suggest-box" id="suggest-box"></div>
        </div>
        <button type="submit" class="btn">Найти</button>
    </form>
</div>
<div class="container">{content}</div>

<script>
document.documentElement.classList.replace('no-js', 'js');

(function() {{
    var input = document.getElementById('search-input');
    var box = document.getElementById('suggest-box');
    var timer = null;

    function renderSuggestions(items) {{
        if (!items || !items.length) {{
            box.classList.remove('active');
            box.innerHTML = '';
            return;
        }}
        box.innerHTML = items.map(function(item) {{
            return '<a class="suggest-item" href="/anime?id=' + item.id + '">' +
                   '<img src="' + item.cover + '" alt="">' +
                   '<span>' + item.title + '</span></a>';
        }}).join('');
        box.classList.add('active');
    }}

    input.addEventListener('input', function() {{
        var q = input.value.trim();
        clearTimeout(timer);
        if (q.length < 2) {{
            box.classList.remove('active');
            return;
        }}
        timer = setTimeout(function() {{
            fetch('/api/suggest?q=' + encodeURIComponent(q))
                .then(function(r) {{ return r.json(); }})
                .then(renderSuggestions)
                .catch(function() {{ box.classList.remove('active'); }});
        }}, 250);
    }});

    document.addEventListener('click', function(e) {{
        if (!box.contains(e.target) && e.target !== input) {{
            box.classList.remove('active');
        }}
    }});
}})();
</script>
</body>
</html>"""


def proxy_img(url):
    """Оборачивает URL картинки в собственный прокси-эндпоинт"""
    if not url:
        return ""
    return f"/img_proxy?url={quote(url)}"


def render_cards(items):
    cards = ""
    for item in items:
        cover_url = (item.get("cover", {}).get("thumbnail") or item.get("cover", {}).get("default") or "")
        title = item.get("rus_name") or item.get("name") or "Без названия"
        anime_id = item.get("id")
        rating = item.get("rating", {}) or {}
        rate = rating.get("averageFormated") or item.get("rate_avg")
        rate_html = f'<span class="badge">⭐ {rate}</span>' if rate else ""
        cards += f"""
        <a href="/anime?id={anime_id}" class="card">
            <img src="{proxy_img(cover_url)}" alt="" loading="lazy">
            <div class="card-title">{title}</div>
            {rate_html}
        </a>"""
    return cards

# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

async def handle_home(request):
    page = int(request.query.get("page", "1"))
    session = request.app["session"]
    items, current, has_next = await get_catalog(session, page)
    pager = f"""
    <div class="pager">
        {f'<a href="/?page={current-1}" class="btn btn-outline">← Пред.</a>' if current > 1 else ''}
        <span class="info">Страница {current}</span>
        {f'<a href="/?page={current+1}" class="btn btn-outline">След. →</a>' if has_next else ''}
    </div>"""
    content = f"""
    <h2>Каталог аниме</h2>
    <div class="grid">{render_cards(items) or '<div class="empty">Каталог пуст</div>'}</div>
    {pager}"""
    return web.Response(text=render_page(content, "AniProxy — Каталог"), content_type="text/html")


async def handle_search(request):
    q = request.query.get("q", "")
    session = request.app["session"]
    results = await search_anime(session, q)
    content = f"""
    <a href="/" class="back-link">← На главную</a>
    <h2>Результаты поиска: «{q}»</h2>
    <div class="grid">{render_cards(results) or '<div class="empty">Ничего не найдено</div>'}</div>"""
    return web.Response(text=render_page(content, f"Поиск: {q}"), content_type="text/html")


async def handle_anime(request):
    anime_id = request.query.get("id")
    session = request.app["session"]
    anime = await get_anime_details(session, anime_id)
    episodes = await get_episodes(session, anime_id)
    title = anime.get("rus_name") or anime.get("name") or "Аниме"

    ep_links = ""
    for ep in sorted(episodes, key=lambda x: float(x.get("number") or 0)):
        num, name, ep_id = ep.get("number"), ep.get("name"), ep.get("id")
        ep_title = f"Серия {num}" + (f": {name}" if name else "")
        ep_links += f'<a href="/watch?id={ep_id}" class="ep-btn">{ep_title}</a>'

    content = f"""
    <a href="/" class="back-link">← Назад</a>
    <h2>{title}</h2>
    <div class="ep-list">{ep_links or '<div class="empty">Серии не найдены</div>'}</div>"""
    return web.Response(text=render_page(content, title), content_type="text/html")


async def handle_watch(request):
    ep_id = request.query.get("id")
    team_idx = int(request.query.get("team", "0"))
    quality = int(request.query.get("q", "720"))
    session = request.app["session"]

    details = await get_episode_details(session, ep_id)
    sources = extract_players(details.get("players", []))
    ep_num, ep_name = details.get("number", ""), details.get("name") or ""
    anime_id = details.get("anime_id")

    # --- Находим соседние серии ---
    prev_ep, next_ep = None, None
    if anime_id:
        episodes = await get_episodes(session, anime_id)
        sorted_eps = sorted(episodes, key=lambda x: float(x.get("number") or 0))
        current_idx = next((i for i, e in enumerate(sorted_eps) if str(e.get("id")) == str(ep_id)), None)
        if current_idx is not None:
            if current_idx > 0:
                prev_ep = sorted_eps[current_idx - 1]
            if current_idx < len(sorted_eps) - 1:
                next_ep = sorted_eps[current_idx + 1]

    team_buttons = ""
    for i, s in enumerate(sources):
        active = "active" if i == team_idx else ""
        team_buttons += f'<a href="/watch?id={ep_id}&team={i}" class="pill {active}">{s["label"]}</a>'

    player_html = '<div class="empty">Нет доступных источников</div>'
    quality_buttons = ""

    if sources and 0 <= team_idx < len(sources):
        source = sources[team_idx]

        if source["kind"] == "direct":
            proxied = f"/stream_proxy?url={quote(source['src'])}"
            player_html = f"""
            <div class="player-shell">
                <video controls autoplay>
                    <source src="{proxied}" type="video/mp4">
                </video>
            </div>"""

        elif source["kind"] == "kodik":
            try:
                links = await resolve_kodik_links(session, source["src"])
                available_qualities = sorted(links.keys(), reverse=True)
                selected_q = quality if quality in available_qualities else available_qualities[0]
                m3u8_url = links[selected_q]

                for qv in available_qualities:
                    active = "active" if qv == selected_q else ""
                    quality_buttons += f'<a href="/watch?id={ep_id}&team={team_idx}&q={qv}" class="pill {active}">{qv}p</a>'

                player_html = f"""
                <div class="player-shell">
                    <video controls autoplay>
                        <source src="{m3u8_url}" type="application/x-mpegURL">
                        <source src="{m3u8_url}" type="video/mp4">
                    </video>
                    <p class="info">Источник: Kodik ({source['label']}) · {selected_q}p</p>
                    <div class="actions">
                        <a href="{m3u8_url}" target="_blank" rel="noopener" class="btn btn-outline">🔗 Открыть m3u8 в новой вкладке</a>
                    </div>
                </div>"""
            except Exception as e:
                player_html = f'<div class="empty">Не удалось получить видео с Kodik: {e}</div>'

    # --- Кнопки навигации между сериями ---
    nav_buttons = '<div class="ep-nav">'
    if prev_ep:
        nav_buttons += f'<a href="/watch?id={prev_ep["id"]}" class="btn btn-outline">← Пред. серия</a>'
    else:
        nav_buttons += '<span class="btn btn-disabled">← Пред. серия</span>'

    if anime_id:
        nav_buttons += f'<a href="/anime?id={anime_id}" class="btn btn-outline">📋 Список серий</a>'

    if next_ep:
        nav_buttons += f'<a href="/watch?id={next_ep["id"]}" class="btn">Следующая серия →</a>'
    else:
        nav_buttons += '<span class="btn btn-disabled">Следующая серия →</span>'
    nav_buttons += '</div>'

    content = f"""
    <a href="javascript:history.back()" class="back-link">← Назад</a>
    <h2>Серия {ep_num} {ep_name}</h2>
    <h3>Озвучка / субтитры</h3>
    <div class="pill-list">{team_buttons}</div>
    {f'<h3>Качество</h3><div class="pill-list">{quality_buttons}</div>' if quality_buttons else ''}
    <div class="player-wrap">{player_html}</div>
    {nav_buttons}"""
    return web.Response(text=render_page(content, f"Серия {ep_num}"), content_type="text/html")


async def handle_direct_stream(request):
    video_url = request.query.get("url")
    if not video_url:
        raise web.HTTPBadRequest(text="No URL provided")

    session = request.app["session"]
    req_headers = {
        "User-Agent": HEADERS["User-Agent"],
        "Referer": HEADERS["Referer"],
        "Origin": HEADERS["Origin"],
    }
    if "Range" in request.headers:
        req_headers["Range"] = request.headers["Range"]

    async with session.get(video_url, headers=req_headers, timeout=aiohttp.ClientTimeout(total=None)) as upstream:
        resp = web.StreamResponse(status=upstream.status)
        for h in ["Content-Type", "Content-Length", "Content-Range", "Accept-Ranges"]:
            val = upstream.headers.get(h)
            if val:
                resp.headers[h] = val
        await resp.prepare(request)
        async for chunk in upstream.content.iter_chunked(64 * 1024):
            await resp.write(chunk)
        return resp


async def handle_img_proxy(request):
    """Прокси картинок обложек — на некоторых TV прямой доступ к hentaicdn.org лагает или блокируется"""
    img_url = request.query.get("url")
    if not img_url:
        raise web.HTTPBadRequest(text="No URL provided")

    session = request.app["session"]
    req_headers = {
        "User-Agent": HEADERS["User-Agent"],
        "Referer": HEADERS["Referer"],
    }

    async with session.get(img_url, headers=req_headers, timeout=aiohttp.ClientTimeout(total=15)) as upstream:
        body = await upstream.read()
        resp = web.Response(
            body=body,
            status=upstream.status,
            content_type=upstream.headers.get("Content-Type", "image/jpeg"),
        )
        resp.headers["Cache-Control"] = "public, max-age=86400"
        return resp
    
async def handle_suggest(request):
    q = request.query.get("q", "").strip()
    if len(q) < 2:
        return web.json_response([])

    session = request.app["session"]
    results = await search_anime(session, q)

    suggestions = []
    for item in results[:8]:
        cover_url = (item.get("cover", {}).get("thumbnail") or item.get("cover", {}).get("default") or "")
        title = item.get("rus_name") or item.get("name") or "Без названия"
        suggestions.append({
            "id": item.get("id"),
            "title": title,
            "cover": proxy_img(cover_url),
        })

    return web.json_response(suggestions)

# ---------------------------------------------------------------------------
# App bootstrap
# ---------------------------------------------------------------------------

async def on_startup(app):
    app["session"] = aiohttp.ClientSession()


async def on_cleanup(app):
    await app["session"].close()


def create_app():
    app = web.Application()
    app.on_startup.append(on_startup)
    app.on_cleanup.append(on_cleanup)
    app.router.add_get("/", handle_home)
    app.router.add_get("/search", handle_search)
    app.router.add_get("/anime", handle_anime)
    app.router.add_get("/watch", handle_watch)
    # app.router.add_get("/stream_proxy", handle_direct_stream)
    app.router.add_get("/img_proxy", handle_img_proxy)
    app.router.add_get("/api/suggest", handle_suggest) 
    return app


if __name__ == "__main__":
    web.run_app(create_app(), host=Config.HOST, port=Config.PORT)
