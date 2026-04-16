from flask import Flask, render_template, request, redirect, url_for
from scrapers.cardekho import scrape_cardekho
from scrapers.cars24 import scrape_cars24
from scrapers.spinny import scrape_spinny

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

def get_recommendation(query, results):
    """Identifies the best value proposition for the user based on search results."""
    if not results:
        return None
        
    # Filter results to ensure relevance (avoiding unrelated platform ads)
    # Use word-based matching to be more flexible (e.g., 'Maruti Swift' matches 'Maruti Suzuki Swift')
    query_words = query.lower().split()
    relevant_results = [r for r in results if all(word in r['title'].lower() for word in query_words)]
    
    # Fallback to all results if filtering is too strict
    target_results = relevant_results if relevant_results else results
    
    # Core Logic: Identify the lowest priced vehicle among relevant listings
    # Filter out results with price 0 (if any)
    valid_results = [r for r in target_results if r['price'] > 0]
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
    
    best_choice = get_recommendation(query, results)
        
    return render_template('results.html', query=query, results=results, best_choice=best_choice)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
