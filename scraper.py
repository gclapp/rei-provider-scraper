"""
REI Provider Scraper
Scrapes Healthgrades and Cigna for REI specialists
"""

import requests
from bs4 import BeautifulSoup
import time
import random
from typing import List, Dict, Optional
from dataclasses import dataclass

@dataclass
class Provider:
    name: str
    clinic: Optional[str]
    address: str
    city: str
    state: str
    zip_code: str
    phone: Optional[str]
    specialties: List[str]
    healthgrades_score: Optional[float]
    review_count: Optional[int]
    cigna_in_network: Optional[bool]
    cigna_plans: List[str]
    source: str
    
    def to_dict(self):
        return {
            'name': self.name,
            'clinic': self.clinic,
            'address': self.address,
            'city': self.city,
            'state': self.state,
            'zip_code': self.zip_code,
            'phone': self.phone,
            'specialties': self.specialties,
            'healthgrades_score': self.healthgrades_score,
            'review_count': self.review_count,
            'cigna_in_network': self.cigna_in_network,
            'cigna_plans': self.cigna_plans,
            'source': self.source
        }


class HealthgradesScraper:
    """Scraper for Healthgrades.com"""
    
    BASE_URL = "https://www.healthgrades.com"
    SEARCH_URL = "https://www.healthgrades.com/usearch"
    
    def __init__(self, delay: float = 1.0):
        self.delay = delay
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def search_providers(self, state: str, specialty: str = "reproductive-endocrinology", limit: int = 50) -> List[Dict]:
        """Search for providers by state"""
        providers = []
        
        # Healthgrades search URL format
        url = f"{self.SEARCH_URL}?what={specialty.replace('-', '%20')}&where={state}"
        
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find provider cards (adjust selectors based on actual HTML)
            provider_cards = soup.find_all('div', class_='provider-card') or soup.find_all('div', {'data-testid': 'provider-card'})
            
            for card in provider_cards[:limit]:
                provider = self._parse_provider_card(card)
                if provider:
                    providers.append(provider)
                
                time.sleep(self.delay)
            
        except Exception as e:
            print(f"Error searching Healthgrades: {e}")
        
        return providers
    
    def _parse_provider_card(self, card) -> Optional[Dict]:
        """Parse a provider card from search results"""
        try:
            # Extract name
            name_elem = card.find('h3') or card.find('a', class_='provider-name')
            name = name_elem.text.strip() if name_elem else "Unknown"
            
            # Extract clinic
            clinic_elem = card.find('div', class_='clinic-name') or card.find('span', class_='practice-name')
            clinic = clinic_elem.text.strip() if clinic_elem else None
            
            # Extract location
            location_elem = card.find('div', class_='location') or card.find('address')
            location_text = location_elem.text.strip() if location_elem else ""
            
            # Parse address components
            city, state, zip_code = self._parse_location(location_text)
            
            # Extract score
            score_elem = card.find('span', class_='score') or card.find('div', class_='rating')
            score = None
            if score_elem:
                try:
                    score = float(score_elem.text.strip().split('/')[0])
                except:
                    pass
            
            return {
                'name': name,
                'clinic': clinic,
                'address': location_text,
                'city': city,
                'state': state,
                'zip_code': zip_code,
                'healthgrades_score': score,
                'source': 'healthgrades'
            }
            
        except Exception as e:
            print(f"Error parsing provider card: {e}")
            return None
    
    def _parse_location(self, location_text: str) -> tuple:
        """Parse city, state, zip from location text"""
        # Simple parsing - enhance as needed
        parts = location_text.split(',')
        city = parts[0].strip() if len(parts) > 0 else ""
        state_zip = parts[1].strip() if len(parts) > 1 else ""
        
        state_parts = state_zip.split()
        state = state_parts[0] if len(state_parts) > 0 else ""
        zip_code = state_parts[1] if len(state_parts) > 1 else ""
        
        return city, state, zip_code


class CignaScraper:
    """Scraper for Cigna provider directory"""
    
    BASE_URL = "https://www.cigna.com"
    
    def __init__(self, delay: float = 1.0):
        self.delay = delay
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def check_provider(self, name: str, state: str) -> Dict:
        """Check if provider is in Cigna network"""
        # Placeholder - implement actual Cigna scraping
        time.sleep(self.delay)
        return {
            'in_network': None,
            'plans': [],
            'source': 'cigna'
        }


class REIScraper:
    """Main scraper that combines multiple sources"""
    
    def __init__(self):
        self.healthgrades = HealthgradesScraper()
        self.cigna = CignaScraper()
    
    def scrape(self, state: str, sources: List[str] = None, network: str = None) -> List[Provider]:
        """
        Scrape REI providers
        
        Args:
            state: US state abbreviation (e.g., 'CA', 'NY')
            sources: List of sources to scrape ['healthgrades', 'cigna']
            network: Insurance network filter ('cigna' or None)
        """
        if sources is None:
            sources = ['healthgrades']
        
        providers = []
        
        if 'healthgrades' in sources:
            print(f"Scraping Healthgrades for {state}...")
            hg_providers = self.healthgrades.search_providers(state)
            for p in hg_providers:
                providers.append(Provider(
                    name=p.get('name', ''),
                    clinic=p.get('clinic'),
                    address=p.get('address', ''),
                    city=p.get('city', ''),
                    state=p.get('state', ''),
                    zip_code=p.get('zip_code', ''),
                    phone=p.get('phone'),
                    specialties=p.get('specialties', ['REI']),
                    healthgrades_score=p.get('healthgrades_score'),
                    review_count=p.get('review_count'),
                    cigna_in_network=None,
                    cigna_plans=[],
                    source='healthgrades'
                ))
        
        if 'cigna' in sources:
            print(f"Checking Cigna network status...")
            for provider in providers:
                cigna_data = self.cigna.check_provider(provider.name, provider.state)
                provider.cigna_in_network = cigna_data.get('in_network')
                provider.cigna_plans = cigna_data.get('plans', [])
        
        # Filter by network if specified
        if network == 'cigna':
            providers = [p for p in providers if p.cigna_in_network]
        
        return providers
