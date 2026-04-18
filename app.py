from flask import Flask, render_template, request, redirect, url_for
from scrapers.cardekho import scrape_cardekho
from scrapers.cars24 import scrape_cars24
from scrapers.spinny import scrape_spinny

app = Flask(__name__)
DEFAULT_CAR_IMAGE = "https://images.unsplash.com/photo-1503376780353-7e6692767b70?auto=format&fit=crop&w=1200&q=80"

@app.route('/')
def index():
    return render_template('index.html')

def normalize_tokens(value):
    return ''.join(char.lower() if char.isalnum() else ' ' for char in value).split()

def is_relevant_result(query, result):
    query_words = normalize_tokens(query)
    title_words = normalize_tokens(result.get('title', ''))
    return bool(query_words) and all(word in title_words for word in query_words)

def is_clean_listing(result):
    title = (result.get('title') or '').strip()
    title_lower = title.lower()
    banned_phrases = (
        'buy used cars',
        'browse by',
        'change city',
        'used cars in',
        'price range',
        'buy cars online',
        'second hand cars',
        'best match',
        'under 2 lakhs',
        'under 3 lakhs',
        'under 5 lakhs',
    )

    if not title or len(title) > 80:
        return False
    if any(phrase in title_lower for phrase in banned_phrases):
        return False
    if not str(result.get('year', '')).isdigit():
        return False
    if result.get('price', 0) <= 0:
        return False
    return True

def normalize_result(result):
    normalized = result.copy()
    normalized['image'] = normalized.get('image') or DEFAULT_CAR_IMAGE
    normalized['kms'] = normalized.get('kms') or 'N/A'
    normalized['fuel'] = normalized.get('fuel') or 'N/A'
    normalized['formatted_price'] = normalized.get('formatted_price') or 'N/A'
    return normalized

def filter_results(query, results):
    filtered = []
    seen = set()

    for result in results:
        if not is_clean_listing(result):
            continue
        if not is_relevant_result(query, result):
            continue

        result = normalize_result(result)
        dedupe_key = result.get('link') or result.get('title')
        if dedupe_key in seen:
            continue

        filtered.append(result)
        seen.add(dedupe_key)

    return filtered

def build_source_summary(results):
    summary = {
        'CarDekho': 0,
        'Cars24': 0,
        'Spinny': 0,
    }

    for result in results:
        site = result.get('site')
        if site in summary:
            summary[site] += 1

    return summary

def get_recommendation(query, results):
    """Identifies the best value proposition for the user based on search results."""
    if not results:
        return None

    # Core Logic: Identify the lowest priced vehicle among relevant listings
    # Filter out results with price 0 (if any)
    valid_results = [r for r in results if r['price'] > 0]
    if not valid_results:
        return None
        
    best_choice = min(valid_results, key=lambda x: x['price']).copy()
    
    # Platform-specific reasoning to help the user choose
    if best_choice['site'] == 'Spinny':
        best_choice['reason'] = f"Priced at {best_choice['formatted_price']}, this Spinny listing offers excellent value. Spinny's 200-point inspection and 1-year warranty make it a safe choice for quality seekers."
    elif best_choice['site'] == 'Cars24':
        best_choice['reason'] = f"This model from Cars24 ({best_choice['formatted_price']}) provides a perfect balance of reliability and price. Their 7-day return policy ensures you can buy with confidence."
    else:
        best_choice['reason'] = f"CarDekho's extensive network often features the most competitive pricing. At {best_choice['formatted_price']}, this is a top-tier deal through their verified partner network."
    
    return best_choice

@app.route('/search', methods=['POST'])
def search():
    query = request.form.get('car_name')
    city = request.form.get('city', 'new-delhi')
    
    if not query:
        return redirect(url_for('index'))
    
    # In a real app, these would be asynchronous
    results = []
    results.extend(scrape_cardekho(query, city))
    results.extend(scrape_cars24(query, city))
    results.extend(scrape_spinny(query, city))

    results = filter_results(query, results)
    source_summary = build_source_summary(results)
    
    best_choice = get_recommendation(query, results)
        
    return render_template(
        'results.html',
        query=query,
        results=results,
        best_choice=best_choice,
        source_summary=source_summary,
        default_car_image=DEFAULT_CAR_IMAGE,
    )

if __name__ == '__main__':
    app.run(debug=True, port=5001)
