import requests
import json
import re

def scrape_cardekho(query, city='new-delhi'):
    # Convert query and city to CarDekho format
    # Example: https://www.cardekho.com/used-cars+in+new-delhi
    # For specific models: https://www.cardekho.com/used-maruti-swift+cars+in+new-delhi
    
    search_query = query.lower().replace(' ', '-')
    url = f"https://www.cardekho.com/used-{search_query}+cars+in+{(city or 'new-delhi').lower()}"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    cars_list = []
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            html = response.text
            json_text = re.search(r'window\.__INITIAL_STATE__\s*=\s*({.*?});', html, re.DOTALL)
            if json_text:
                data = json.loads(json_text.group(1))
                if 'cars' in data and isinstance(data['cars'], list):
                    for car in data['cars']:
                        if isinstance(car, dict):
                            cars_list.append({
                                'title': f"{car.get('myear', '')} {car.get('model', '')} {car.get('variantName', '')}",
                                'price': car.get('price', 0),
                                'formatted_price': car.get('formattedPrice', 'N/A'),
                                'kms': car.get('km', 'N/A'),
                                'fuel': car.get('ft', 'N/A'),
                                'year': car.get('myear', 'N/A'),
                                'site': 'CarDekho',
                                'link': f"https://www.cardekho.com{car.get('vlink', '')}",
                                'image': car.get('pi', '')
                            })
    except Exception as e:
        print(f"Error scraping CarDekho: {e}")

    return cars_list
