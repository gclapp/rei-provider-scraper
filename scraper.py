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


class ThunderbitHealthgradesScraper:
    """
    Healthgrades scraper using Thunderbit AI
    
    Note: Requires Thunderbit CLI or Chrome extension
    npm i -g @thunderbit/thunderbit-cli
    
    Or use Thunderbit API with API key
    """

    BASE_URL = "https://www.healthgrades.com"
    SEARCH_URL = "https://www.healthgrades.com/usearch"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get('THUNDERBIT_API_KEY')
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Accept': 'application/json',
        })

    def search_providers(self, state: str, specialty: str = "Reproductive Endocrinology & Infertility",
                         limit: int = 20) -> List[Provider]:
        """Search Healthgrades using Thunderbit AI scraper"""
        providers = []
        
        # Build search URL
        search_term = specialty.replace(' ', '%20')
        url = f"{self.SEARCH_URL}?what={search_term}&where={state}&page=1"
        
        print(f"[Healthgrades via Thunderbit] Searching: {url}")
        
        # If we have Thunderbit API key, use it
        if self.api_key:
            providers = self._scrape_with_api(url, limit)
        else:
            # Fallback to direct scraping with instructions for Thunderbit
            print("[Healthgrades] Thunderbit API key not configured")
            print("[Healthgrades] To use Thunderbit:")
            print("  1. Install Chrome extension: https://chromewebstore.google.com/detail/thunderbit")
            print("  2. Navigate to the search URL above")
            print("  3. Click 'AI Suggest Columns' then 'Scrape'")
            print("  4. Or set THUNDERBIT_API_KEY environment variable")
            
        return providers

    def _scrape_with_api(self, url: str, limit: int) -> List[Provider]:
        """Scrape using Thunderbit API"""
        providers = []
        
        try:
            # Thunderbit API endpoint (hypothetical - check actual docs)
            thunderbit_url = "https://api.thunderbit.com/scrape"
            
            payload = {
                'url': url,
                'selectors': {
                    'provider_name': '[data-testid="provider-name"]',
                    'profile_url': 'a[href*="/physician/"]',
                    'location': '[data-testid="practice-address"]',
                    'phone': '[data-testid="phone-number"]',
                    'rating': '[data-testid="overall-rating"]',
                    'specialty': '[data-testid="specialties-section"]'
                }
            }
            
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
            
            response = self.session.post(thunderbit_url, json=payload, headers=headers, timeout=60)
            
            if response.status_code == 200:
                data = response.json()
                for item in data.get('results', [])[:limit]:
                    provider = self._parse_thunderbit_result(item)
                    if provider:
                        providers.append(provider)
            else:
                print(f"[Thunderbit] API error: {response.status_code}")
                
        except Exception as e:
            print(f"[Thunderbit] Error: {e}")
            
        return providers

    def _parse_thunderbit_result(self, data: Dict) -> Optional[Provider]:
        """Parse Thunderbit scraping result"""
        try:
            full_name = data.get('provider_name', '')
            name_parts = self._parse_name(full_name)
            
            return Provider(
                first_name=name_parts['first'],
                last_name=name_parts['last'],
                title=name_parts['title'],
                full_name=full_name,
                photo_url=data.get('photo_url'),
                expertise=[data.get('specialty', '')] if data.get('specialty') else [],
                healthgrades_rating=data.get('rating'),
                review_count=data.get('review_count'),
                office_location=data.get('location', ''),
                city='',
                state='',
                zip_code='',
                phone=data.get('phone'),
                bio=data.get('bio', ''),
                profile_url=urljoin(self.BASE_URL, data.get('profile_url', '')),
                source='healthgrades',
                insurance_accepted=[]
            )
        except Exception as e:
            print(f"[Thunderbit] Parse error: {e}")
            return None

    def _parse_name(self, full_name: str) -> Dict:
        """Parse full name into components"""
        title = ""
        titles = ['MD', 'DO', 'PhD', 'Dr.', 'Dr', 'NP', 'PA', 'RN']
        
        for t in titles:
            if full_name.endswith(f", {t}") or full_name.endswith(f" {t}"):
                title = t
                full_name = full_name.replace(f", {t}", "").replace(f" {t}", "").strip()
                break
        
        parts = full_name.split()
        if len(parts) >= 2:
            return {'first': parts[0], 'last': ' '.join(parts[1:]), 'title': title}
        return {'first': full_name, 'last': '', 'title': title}


class CignaProviderDirectoryScraper:
    """
    Cigna Provider Directory scraper using FHIR API
    
    API Endpoint: https://fhir.cigna.com/ProviderDirectory/v1
    Documentation: https://developer.cigna.com/
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
        
        # Try FHIR API first
        if self.client_id and self.client_secret:
            providers = self._search_fhir_api(state, specialty, limit)
        
        # Fallback to web scraping if API fails or no credentials
        if not providers:
            print("[Cigna] Falling back to web directory...")
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
        """Search using Cigna web directory (fallback)"""
        providers = []
        
        try:
            # Cigna web search URL
            search_url = f"{self.WEB_URL}/web/public/consumer/directory/search"
            
            params = {
                'location': state,
                'specialty': specialty.replace(' ', '%20'),
                'type': 'provider'
            }
            
            print(f"[Cigna Web] URL: {search_url}?{ '&'.join(f'{k}={v}' for k,v in params.items()) }")
            
            # Note: This would require Selenium/Playwright for JavaScript rendering
            # For now, return empty and instruct user
            print("[Cigna Web] Web scraping requires headless browser (Selenium/Playwright)")
            print("[Cigna Web] Consider using FHIR API with client credentials")
            
        except Exception as e:
            print(f"[Cigna Web] Error: {e}")
            
        return providers

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
        self.healthgrades = ThunderbitHealthgradesScraper()
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
        if sources is None:
            sources = ['healthgrades']

        providers = []

        if 'healthgrades' in sources:
            print(f"[Scraper] Querying Healthgrades via Thunderbit for {state}...")
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
