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
