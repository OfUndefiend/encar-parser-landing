# scraper/scraper.py
import json
import re
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

# -------------------- базовые настройки --------------------

# Публичная выдача ENCAR (можешь заменить на свою — фильтры/сортировку и т.п.)
START_URL = (
    "https://car.encar.com/list/car?page=1"
    "&search=%7B%22type%22%3A%22car%22%2C%22action%22%3A%22(And.Hidden.N._.MultiViewHidden.N.)%22,"
    "%22toggle%22%3A%7B%7D,%22layer%22%3A%22%22,%22sort%22%3A%22MobileModifiedDate%22%7D"
)

# Сколько страниц пройти максимально (держи 1–2, чтобы не злоупотреблять)
MAX_PAGES = 1

# Куда писать результат
OUT_PATH = Path(__file__).resolve().parents[1] / "site" / "data" / "cars.json"
OUT_PATH.parent.mkdir(parents=True, exist_ok=True)


# -------------------- утилиты --------------------

def slow_human_pause(sec: float = 1.0):
    time.sleep(sec)

def _to_int(s: str) -> int | None:
    if not s:
        return None
    digits = re.sub(r"[^\d]", "", s)
    return int(digits) if digits else None

def _year_from_korean(s: str) -> int | None:
    """
    Примеры: '21/04식', '2019식' -> 2021 / 2019
    Берём первые 2–4 цифры. Если 2-значный — считаем как 2000+.
    """
    m = re.search(r"(\d{2,4})", s or "")
    if not m:
        return None
    y = int(m.group(1))
    return 2000 + y if y < 100 else y

def _norm_url(u: str) -> str:
    if not u:
        return u
    if u.startswith("//"):
        return "https:" + u
    if u.startswith("/"):
        return "https://car.encar.com" + u
    return u


# -------------------- основной парсинг --------------------

def scrape_list(page, url: str) -> list[dict]:
    page.goto(url, wait_until="networkidle")
    slow_human_pause(1.2)

    # ждём появления карточек листинга
    page.wait_for_selector('div[class^="ItemBigImage_item__"]', timeout=15000)

    items = page.locator('div[class^="ItemBigImage_item__"]')
    n = min(items.count(), 30)  # не жадничаем

    cars: list[dict] = []

    for i in range(n):
        card = items.nth(i)
        try:
            # ссылка на детальную
            href = ""
            link = card.locator('a[class^="ItemBigImage_link_item__"]')
            if link.count():
                href = _norm_url(link.first.get_attribute("href") or "")

            # изображение — берём из слайдера, иначе любой img
            img = ""
            img_loc = card.locator('div[class^="CarPhotoSwiper_swiper_wrap__"] img')
            if img_loc.count() == 0:
                img_loc = card.locator("img")
            if img_loc.count():
                img = _norm_url(
                    img_loc.first.get_attribute("src")
                    or img_loc.first.get_attribute("data-src")
                    or ""
                )

            # бренд/модель — в заголовке несколькими строками
            brand, model = None, None
            title_node = card.locator('strong[class^="ItemBigImage_name__"]')
            if title_node.count():
                lines = [x.strip() for x in title_node.first.inner_text().splitlines() if x.strip()]
                if lines:
                    brand = lines[0]
                if len(lines) > 1:
                    model = lines[1]

            # год и пробег — из списка характеристик
            year, mileage_km = None, None
            info_items = card.locator('ul[class^="ItemBigImage_info__"] > li')
            if info_items.count() >= 1:
                year = _year_from_korean(info_items.nth(0).inner_text().strip())
            if info_items.count() >= 2:
                mileage_km = _to_int(info_items.nth(1).inner_text().strip())

            # цена: цифра в "만원" (десятки тысяч вон) -> умножаем на 10_000
            price_krw = None
            price_num = card.locator('div[class^="ItemBigImage_price_area__"] span[class^="ItemBigImage_num__"]')
            if price_num.count():
                man = _to_int(price_num.first.inner_text().strip())
                if man is not None:
                    price_krw = man * 10_000

            # fallback для бренда/модели из alt у картинки
            if (not brand or not model) and img_loc.count():
                alt = img_loc.first.get_attribute("alt") or ""
                parts = [p for p in alt.split() if p.strip()]
                if parts:
                    brand = brand or parts[0]
                    if not model and len(parts) > 1:
                        model = " ".join(parts[1:3])

            # собираем запись, если есть главное: ссылка и фото
            if href and img:
                cars.append({
                    "brand": brand,
                    "model": model,
                    "year": year,
                    "mileage_km": mileage_km,
                    "price_krw": price_krw,
                    "image": img,
                    "link": href,
                })

        except Exception:
            # молча пропускаем битые карточки, идём дальше
            continue

    return cars


# -------------------- точка входа --------------------

def main():
    with sync_playwright() as p:
        browser = p.firefox.launch(headless=True, slow_mo=80)
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0 Safari/537.36"
            ),
            viewport={"width": 1366, "height": 900},
            locale="ko-KR",
        )
        page = context.new_page()

        all_cars: list[dict] = []
        for page_no in range(1, MAX_PAGES + 1):
            url = re.sub(r"page=\d+", f"page={page_no}", START_URL)
            all_cars.extend(scrape_list(page, url))
            slow_human_pause(1.0)

        # чистим и сохраняем
        cleaned = []
        for c in all_cars:
            if c.get("image") and c.get("link"):
                cleaned.append({
                    "brand": c.get("brand"),
                    "model": c.get("model"),
                    "year": c.get("year"),
                    "mileage_km": c.get("mileage_km"),
                    "price_krw": c.get("price_krw"),
                    "image": c.get("image"),
                    "link": c.get("link"),
                })

        OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(OUT_PATH, "w", encoding="utf-8") as f:
            json.dump({"updated_at": int(time.time()), "cars": cleaned}, f, ensure_ascii=False, indent=2)

        print(f"Saved {len(cleaned)} cars -> {OUT_PATH}")
        browser.close()


if __name__ == "__main__":
    main()
