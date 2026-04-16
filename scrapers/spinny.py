import requests
from bs4 import BeautifulSoup
import json
import re

def scrape_spinny(query, city='delhi'):
    # Spinny uses a more complex structure, but sometimes we can find JSON in ld+json
    search_query = query.lower().replace(' ', '-')
    url = f"https://www.spinny.com/used-cars-in-{(city or 'delhi').lower()}/s/"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    cars_list = []
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            # Look for Product ld+json
            scripts = soup.find_all('script', type='application/ld+json')
            for script in scripts:
                try:
                    data = json.loads(script.string)
                    if isinstance(data, list):
                        for item in data:
                            if item.get('@type') == 'Product':
                                name = item.get('name', '')
                                if query.lower() in name.lower():
                                    price = item.get('offers', {}).get('price', 0)
                                    cars_list.append({
                                        'title': name,
                                        'price': int(price) if price else 0,
                                        'formatted_price': f"₹ {price/100000:.2f} Lakh" if price else "N/A",
                                        'kms': 'N/A', # Often not in the basic Product LD
                                        'fuel': 'N/A',
                                        'year': 'N/A',
                                        'site': 'Spinny',
                                        'link': item.get('url', url),
                                        'image': item.get('image', '')
                                    })
                except:
                    continue
    except Exception as e:
        print(f"Error scraping Spinny: {e}")
        
    if not cars_list:
        # Fallback to demo data if scraping is blocked or unsuccessful
        for i in range(1, 4):
            year = 2021 - i
            price = 450000 + (i * 20000)
            cars_list.append({
                'title': f'{year} {query.capitalize()} LXI (Demo)',
                'price': price,
                'formatted_price': f'₹ {price/100000:.2f} Lakh',
                'kms': f'{30000 + (i*10000):,}',
                'fuel': 'Petrol',
                'year': year,
                'site': 'Spinny',
                'link': url,
                'image': 'https://spn-mda.spinny.com/img/C9vkkMJkRBqG1BUXCKg6Jg/raw/file.jpeg'
            })
    
    return cars_list
