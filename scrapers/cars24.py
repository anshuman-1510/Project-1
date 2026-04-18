import re
import requests

from bs4 import BeautifulSoup


CITY_ALIASES = {
    "new-delhi": "delhi-ncr",
    "delhi": "delhi-ncr",
    "gurugram": "gurgaon",
}

CHROME_BINARY = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
DEFAULT_IMAGE = "https://images.unsplash.com/photo-1503376780353-7e6692767b70?auto=format&fit=crop&w=1200&q=80"


def _normalize_city(city):
    city_slug = (city or "new-delhi").strip().lower().replace(" ", "-")
    return CITY_ALIASES.get(city_slug, city_slug)


def _normalize_tokens(value):
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).split()


def _matches_query(title, query):
    query_tokens = _normalize_tokens(query)
    title_tokens = _normalize_tokens(title)
    return bool(query_tokens) and all(token in title_tokens for token in query_tokens)


def _build_listing(year, title, variant, kms, fuel, price_lakhs, link, image):
    lakhs = float(price_lakhs)
    clean_title = f"{year} {title.strip()} {variant.strip()}".strip()
    return {
        "title": clean_title,
        "price": int(lakhs * 100000),
        "formatted_price": f"₹ {lakhs:.2f} Lakh",
        "kms": f"{int(kms.replace(',', '')):,} km",
        "fuel": fuel.title(),
        "year": year,
        "site": "Cars24",
        "link": link,
        "image": image or DEFAULT_IMAGE,
    }


def _extract_listings_from_cards(html):
    soup = BeautifulSoup(html, "html.parser")
    listings = []
    seen = set()

    for anchor in soup.find_all("a", href=re.compile(r"^https://www\.cars24\.com/buy-used-.*cars-.*\d+/$")):
        parts = [part.strip() for part in anchor.stripped_strings if part.strip()]
        if len(parts) < 9:
            continue

        text = " | ".join(parts)
        match = re.search(
            r"(?:Cars24 Owned Stock|Verified Direct Seller)\s*\|\s*"
            r"(?P<year>\d{4})\s+"
            r"(?P<title>[A-Za-z0-9 ]+?)\s*\|\s*"
            r"(?P<variant>[A-Za-z0-9 .+\-]+?)\s*\|\s*"
            r"(?P<kms>\d[\d,]*)\s+km\s*\|\s*"
            r"(?P<fuel>Petrol|Diesel|CNG|Electric|Hybrid)\s*\|\s*"
            r"(?:Manual|Auto|Automatic)\s*\|.*?"
            r"₹(?P<price>\d+(?:\.\d+)?)L\b",
            text,
            re.IGNORECASE,
        )
        if not match:
            continue

        image = ""
        for img in anchor.find_all("img"):
            src = img.get("src") or ""
            if "media.cars24.com" in src:
                image = src
                break

        listing = _build_listing(
            year=match.group("year"),
            title=match.group("title"),
            variant=match.group("variant"),
            kms=match.group("kms"),
            fuel=match.group("fuel"),
            price_lakhs=match.group("price"),
            link=anchor.get("href"),
            image=image,
        )
        dedupe_key = listing["link"]
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        listings.append(listing)
    return listings


def scrape_cars24(query, city="new-delhi"):
    city_slug = _normalize_city(city)
    url = f"https://www.cars24.com/buy-used-cars-{city_slug}/"
    try:
        response = requests.get(
            url,
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=5,
        )
        response.raise_for_status()
        html = response.text
    except Exception as e:
        print(f"Error scraping Cars24 from {url}: {e}")
        return []

    matches = []
    for listing in _extract_listings_from_cards(html):
        if _matches_query(listing["title"], query):
            matches.append(listing)
        if len(matches) >= 12:
            break

    return matches
