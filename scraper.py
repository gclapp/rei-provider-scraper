"""
REI Provider Scraper
Multi-source scraper for REI specialists

Data Sources:
1. Healthgrades (via Thunderbit AI Scraper)
2. Cigna Provider Directory (FHIR API)
3. BetterDoctor API (planned - see Todoist task)
"""

import requests
import time
import re
import os
from typing import List, Dict, Optional
from dataclasses import dataclass
from urllib.parse import urljoin

@dataclass
class Provider:
    first_name: str
    last_name: str
    title: str
    full_name: str
    photo_url: Optional[str]
    expertise: List[str]
    healthgrades_rating: Optional[float]
    review_count: Optional[int]
    office_location: str
    city: str
    state: str
    zip_code: str
    phone: Optional[str]
    bio: str
    profile_url: str
    source: str
    insurance_accepted: List[str]

    def to_dict(self):
        return {
            'first_name': self.first_name,
            'last_name': self.last_name,
            'title': self.title,
            'full_name': self.full_name,
            'photo_url': self.photo_url,
            'expertise': self.expertise,
            'healthgrades_rating': self.healthgrades_rating,
            'review_count': self.review_count,
            'office_location': self.office_location,
            'city': self.city,
            'state': self.state,
            'zip_code': self.zip_code,
            'phone': self.phone,
            'bio': self.bio,
            'profile_url': self.profile_url,
            'source': self.source,
            'insurance_accepted': self.insurance_accepted
        }


class HealthgradesScraper:
    """
    Healthgrades scraper - PLACEHOLDER
    
    NOTE: Requires Thunderbit API (paid) or manual Chrome extension use.
    See Todoist task for Thunderbit research.
    
    Free alternative: Use Chrome extension manually at:
    https://chromewebstore.google.com/detail/thunderbit-ai-web-scraper/hbkblmodhbmcakopfckopccgp
    """

    BASE_URL = "https://www.healthgrades.com"

    def __init__(self):
        pass

    def search_providers(self, state: str, specialty: str = "Reproductive Endocrinology & Infertility",
                         limit: int = 20) -> List[Provider]:
        """Healthgrades scraping - requires Thunderbit (see Todoist)"""
        print("[Healthgrades] Skipped - requires Thunderbit API key")
        print("[Healthgrades] See Todoist task 'Research Thunderbit API' for details")
        print("[Healthgrades] Or use Cigna Provider Directory (selected by default)")
        return []


class CignaProviderDirectoryScraper:
    """
    Cigna Provider Directory scraper
    
    Two methods:
    1. FHIR API (requires credentials from developer.cigna.com)
    2. Web scraping (works immediately, no API key needed)
    
    API Endpoint: https://fhir.cigna.com/ProviderDirectory/v1
    Web Directory: https://hcpdirectory.cigna.com
    """

    BASE_URL = "https://fhir.cigna.com/ProviderDirectory/v1"
    WEB_URL = "https://hcpdirectory.cigna.com"

    def __init__(self, client_id: Optional[str] = None, client_secret: Optional[str] = None):
        self.client_id = client_id or os.environ.get('CIGNA_CLIENT_ID')
        self.client_secret = client_secret or os.environ.get('CIGNA_CLIENT_SECRET')
        self.access_token = None
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Accept': 'application/fhir+json',
            'Content-Type': 'application/fhir+json'
        })

    def _authenticate(self):
        """Get OAuth2 access token from Cigna"""
        if not self.client_id or not self.client_secret:
            print("[Cigna] No API credentials configured")
            return False
            
        try:
            auth_url = "https://developer.cigna.com/oauth2/token"
            
            payload = {
                'grant_type': 'client_credentials',
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'scope': 'provider_directory'
            }
            
            response = self.session.post(auth_url, data=payload, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                self.access_token = data.get('access_token')
                self.session.headers['Authorization'] = f'Bearer {self.access_token}'
                return True
            else:
                print(f"[Cigna] Auth failed: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"[Cigna] Auth error: {e}")
            return False

    def search_providers(self, state: str, specialty: str = "Reproductive Endocrinology",
                         limit: int = 20) -> List[Provider]:
        """Search Cigna Provider Directory for REI specialists"""
        providers = []
        
        print(f"[Cigna] Searching for {specialty} in {state}...")
        
        # Try FHIR API first if credentials available
        if self.client_id and self.client_secret:
            print("[Cigna] Attempting FHIR API...")
            providers = self._search_fhir_api(state, specialty, limit)
            if providers:
                print(f"[Cigna] FHIR API returned {len(providers)} providers")
                return providers
        
        # Fallback to web scraping
        print("[Cigna] Using web scraping (no API credentials needed)...")
        providers = self._search_web_directory(state, specialty, limit)
        
        return providers

    def _search_fhir_api(self, state: str, specialty: str, limit: int) -> List[Provider]:
        """Search using Cigna FHIR API"""
        providers = []
        
        if not self._authenticate():
            return providers
        
        try:
            # FHIR Practitioner search
            url = f"{self.BASE_URL}/Practitioner"
            
            params = {
                'address-state': state,
                'specialty': specialty,
                '_count': min(limit, 50)
            }
            
            response = self.session.get(url, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                entries = data.get('entry', [])
                
                for entry in entries[:limit]:
                    resource = entry.get('resource', {})
                    provider = self._parse_fhir_practitioner(resource)
                    if provider:
                        providers.append(provider)
            else:
                print(f"[Cigna FHIR] API error: {response.status_code}")
                
        except Exception as e:
            print(f"[Cigna FHIR] Error: {e}")
            
        return providers

    def _search_web_directory(self, state: str, specialty: str, limit: int) -> List[Provider]:
        """Search using Cigna web directory with requests-based scraping"""
        providers = []
        
        try:
            # Cigna web search uses a different approach
            # Try to use their search endpoint directly
            search_url = f"{self.WEB_URL}/web/public/consumer/directory/search-results"
            
            params = {
                'location': state,
                'specialty': specialty,
                'type': 'provider',
                'page': 1
            }
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Referer': f'{self.WEB_URL}/web/public/consumer/directory/search'
            }
            
            print(f"[Cigna Web] Searching: {search_url}")
            
            response = self.session.get(search_url, params=params, headers=headers, timeout=30)
            
            if response.status_code == 200:
                # Parse HTML for provider listings
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Look for provider cards (adjust selectors based on actual HTML structure)
                provider_cards = soup.find_all('div', class_=re.compile('provider-card|search-result|provider-item'))
                
                if not provider_cards:
                    # Try alternative selectors
                    provider_cards = soup.find_all('article') or soup.find_all('div', {'data-testid': True})
                
                print(f"[Cigna Web] Found {len(provider_cards)} provider cards")
                
                for card in provider_cards[:limit]:
                    provider = self._parse_web_provider_card(card)
                    if provider:
                        providers.append(provider)
                        
            else:
                print(f"[Cigna Web] HTTP {response.status_code}")
                
        except Exception as e:
            print(f"[Cigna Web] Error: {e}")
            import traceback
            traceback.print_exc()
            
        return providers

    def _parse_web_provider_card(self, card) -> Optional[Provider]:
        """Parse a provider card from Cigna web directory"""
        try:
            # Extract name
            name_elem = card.find(['h2', 'h3', 'a'], class_=re.compile('name|title'))
            if not name_elem:
                name_elem = card.find(string=re.compile('Dr\.|MD|DO'))
                if name_elem:
                    name_elem = name_elem.parent
                    
            full_name = name_elem.get_text(strip=True) if name_elem else "Unknown Provider"
            
            # Parse name
            name_parts = self._parse_name(full_name)
            
            # Extract specialty
            specialty_elem = card.find(class_=re.compile('specialty'))
            expertise = [specialty_elem.get_text(strip=True)] if specialty_elem else ['Reproductive Endocrinology']
            
            # Extract location
            location_elem = card.find(class_=re.compile('location|address'))
            office_location = location_elem.get_text(strip=True) if location_elem else ''
            
            # Parse city/state from location
            city, state, zip_code = '', '', ''
            if office_location:
                match = re.search(r'([^,]+),\s*([A-Z]{2})\s*(\d{5}(-\d{4})?)?', office_location)
                if match:
                    city = match.group(1).strip()
                    state = match.group(2)
                    zip_code = match.group(3) if match.group(3) else ''
            
            # Extract phone
            phone_elem = card.find('a', href=re.compile('tel:'))
            phone = phone_elem.get_text(strip=True) if phone_elem else None
            
            # Extract profile URL
            profile_link = card.find('a', href=re.compile('/provider/|/doctor/'))
            profile_url = ''
            if profile_link and profile_link.get('href'):
                profile_url = urljoin(self.WEB_URL, profile_link['href'])
            
            return Provider(
                first_name=name_parts['first'],
                last_name=name_parts['last'],
                title=name_parts['title'],
                full_name=full_name,
                photo_url=None,
                expertise=expertise,
                healthgrades_rating=None,
                review_count=None,
                office_location=office_location,
                city=city,
                state=state,
                zip_code=zip_code,
                phone=phone,
                bio='',
                profile_url=profile_url,
                source='cigna',
                insurance_accepted=['Cigna']
            )
            
        except Exception as e:
            print(f"[Cigna Web] Parse error: {e}")
            return None

    def _parse_name(self, full_name: str) -> Dict:
        """Parse full name into components"""
        title = ""
        titles = ['MD', 'DO', 'PhD', 'Dr.', 'Dr', 'NP', 'PA', 'RN']
        
        for t in titles:
            if f", {t}" in full_name or full_name.endswith(f" {t}"):
                title = t
                full_name = full_name.replace(f", {t}", "").replace(f" {t}", "").strip()
                break
        
        parts = full_name.replace('Dr. ', '').replace('Dr ', '').split()
        if len(parts) >= 2:
            return {'first': parts[0], 'last': ' '.join(parts[1:]), 'title': title}
        return {'first': full_name, 'last': '', 'title': title}

    def _parse_fhir_practitioner(self, resource: Dict) -> Optional[Provider]:
        """Parse FHIR Practitioner resource"""
        try:
            # Extract name
            name_data = resource.get('name', [{}])[0]
            first_name = name_data.get('given', [''])[0]
            last_name = name_data.get('family', '')
            full_name = f"{first_name} {last_name}".strip()
            
            # Extract address
            address_data = resource.get('address', [{}])[0]
            city = address_data.get('city', '')
            state = address_data.get('state', '')
            zip_code = address_data.get('postalCode', '')
            street = ' '.join(address_data.get('line', []))
            office_location = f"{street}, {city}, {state} {zip_code}".strip(', ')
            
            # Extract telecom (phone)
            phone = None
            for telecom in resource.get('telecom', []):
                if telecom.get('system') == 'phone':
                    phone = telecom.get('value')
                    break
            
            # Extract specialty
            expertise = []
            for coding in resource.get('specialty', []):
                for code in coding.get('coding', []):
                    if code.get('display'):
                        expertise.append(code['display'])
            
            # Build profile URL
            practitioner_id = resource.get('id', '')
            profile_url = f"{self.WEB_URL}/provider/{practitioner_id}"
            
            return Provider(
                first_name=first_name,
                last_name=last_name,
                title='MD',
                full_name=full_name,
                photo_url=None,
                expertise=expertise,
                healthgrades_rating=None,
                review_count=None,
                office_location=office_location,
                city=city,
                state=state,
                zip_code=zip_code,
                phone=phone,
                bio='',
                profile_url=profile_url,
                source='cigna',
                insurance_accepted=['Cigna']
            )
            
        except Exception as e:
            print(f"[Cigna] Parse error: {e}")
            return None


class BetterDoctorScraper:
    """
    BetterDoctor API scraper
    
    TODO: Implement BetterDoctor API integration
    Task ID: See Todoist task "Implement BetterDoctor API search for REI Provider Scraper"
    
    API Docs: https://developer.betterdoctor.com/
    """
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get('BETTERDOCTOR_API_KEY')
        self.base_url = "https://api.betterdoctor.com"
        
    def search_providers(self, state: str, specialty: str = "reproductive-endocrinology",
                         limit: int = 20) -> List[Provider]:
        """Search BetterDoctor API - NOT YET IMPLEMENTED"""
        print("[BetterDoctor] API integration not yet implemented")
        print("[BetterDoctor] See Todoist task for implementation")
        return []


class REIScraper:
    """Main scraper that combines multiple sources"""

    def __init__(self):
        self.healthgrades = HealthgradesScraper()
        self.cigna = CignaProviderDirectoryScraper()
        self.betterdoctor = BetterDoctorScraper()

    def scrape(self, state: str, sources: List[str] = None, network: str = None) -> List[Provider]:
        """
        Scrape REI providers from selected sources
        
        Args:
            state: US state abbreviation (e.g., 'CA', 'NY')
            sources: List of sources ['healthgrades', 'cigna', 'betterdoctor']
            network: Insurance network filter (legacy, now uses source selection)
        """
        # Default to Cigna if no sources specified (it's free and doesn't require API key)
        if sources is None or len(sources) == 0:
            sources = ['cigna']

        providers = []

        if 'healthgrades' in sources:
            print(f"[Scraper] Querying Healthgrades for {state}...")
            hg_providers = self.healthgrades.search_providers(state)
            providers.extend(hg_providers)

        if 'cigna' in sources:
            print(f"[Scraper] Querying Cigna Provider Directory for {state}...")
            cigna_providers = self.cigna.search_providers(state)
            providers.extend(cigna_providers)
            
        if 'betterdoctor' in sources:
            print(f"[Scraper] Querying BetterDoctor for {state}...")
            bd_providers = self.betterdoctor.search_providers(state)
            providers.extend(bd_providers)

        return providers
