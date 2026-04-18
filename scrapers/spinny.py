import re

import requests
from bs4 import BeautifulSoup


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}

CITY_ALIASES = {
    "new-delhi": "delhi",
    "delhi-ncr": "delhi",
    "gurugram": "gurgaon",
}

CHROME_BINARY = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
DEFAULT_IMAGE = "https://images.unsplash.com/photo-1503376780353-7e6692767b70?auto=format&fit=crop&w=1200&q=80"


def _normalize_city(city):
    city_slug = (city or "delhi").strip().lower().replace(" ", "-")
    return CITY_ALIASES.get(city_slug, city_slug)


def _slugify(value):
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def _normalize_tokens(value):
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).split()


def _matches_query(title, query):
    query_tokens = _normalize_tokens(query)
    title_tokens = _normalize_tokens(title)
    return bool(query_tokens) and all(token in title_tokens for token in query_tokens)


def _extract_kms(text):
    match = re.search(r"(\d+(?:\.\d+)?)\s*K\s*km", text, re.IGNORECASE)
    if match:
        return f"{int(float(match.group(1)) * 1000):,} km"

    match = re.search(r"(\d[\d,]*)\s*km", text, re.IGNORECASE)
    if match:
        return f"{int(match.group(1).replace(',', '')):,} km"

    return "N/A"


def _extract_image(node):
    image = node.find("img")
    if not image:
        return DEFAULT_IMAGE
    return (
        image.get("src")
        or image.get("data-src")
        or image.get("srcset", "").split(" ")[0]
        or DEFAULT_IMAGE
    )


def _extract_from_anchor(anchor):
    href = anchor.get("href", "").strip()
    title = " ".join(anchor.stripped_strings).strip()

    if not href.startswith("/buy-used-cars/"):
        return None
    if not re.match(r"^\d{4}\s", title):
        return None
    if len(title) > 70:
        return None

    card = anchor
    for _ in range(8):
        if card is None:
            break
        text = " ".join(card.stripped_strings)
        if "Lakh" in text and "km" in text.lower():
            price_match = re.search(r"(\d+(?:\.\d+)?)\s*Lakh", text, re.IGNORECASE)
            fuel_match = re.search(r"\b(petrol|diesel|cng|electric|hybrid)\b", text, re.IGNORECASE)
            if not price_match:
                break
            year = title.split(" ", 1)[0]
            return {
                "title": title,
                "price": int(float(price_match.group(1)) * 100000),
                "formatted_price": f"₹ {float(price_match.group(1)):.2f} Lakh",
                "kms": _extract_kms(text),
                "fuel": fuel_match.group(1).title() if fuel_match else "N/A",
                "year": year,
                "site": "Spinny",
                "link": f"https://www.spinny.com{href}",
                "image": _extract_image(card),
            }
        card = card.parent

    return None


def scrape_spinny(query, city="delhi"):
    city_slug = _normalize_city(city)
    query_slug = _slugify(query)
    urls = [
        f"https://www.spinny.com/used-{query_slug}-cars-in-{city_slug}/s/",
        f"https://www.spinny.com/used-cars-in-{city_slug}/s/",
    ]

    results = []
    seen = set()

    for url in urls:
        try:
            response = requests.get(url, headers=HEADERS, timeout=8)
            response.raise_for_status()
            html = response.text
        except Exception as e:
            print(f"Error scraping Spinny from {url}: {e}")
            html = ""

        if not html:
            continue

        soup = BeautifulSoup(html, "html.parser")
        for anchor in soup.find_all("a", href=re.compile(r"^/buy-used-cars/")):
            listing = _extract_from_anchor(anchor)
            if not listing:
                continue
            if not _matches_query(listing["title"], query):
                continue

            dedupe_key = listing["link"]
            if dedupe_key in seen:
                continue

            seen.add(dedupe_key)
            results.append(listing)

            if len(results) >= 6:
                return results

    return results
