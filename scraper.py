"""
REI Provider Scraper
Scrapes Healthgrades for REI specialists using their API
"""

import requests
import time
import re
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
            'source': self.source
        }


class HealthgradesScraper:
    """Scraper for Healthgrades.com using their API"""

    BASE_URL = "https://www.healthgrades.com"
    API_BASE = "https://www.healthgrades.com/api"

    def __init__(self, delay: float = 1.0):
        self.delay = delay
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Referer': 'https://www.healthgrades.com/',
            'Origin': 'https://www.healthgrades.com',
            'Connection': 'keep-alive',
        })

    def search_providers(self, state: str, specialty: str = "Reproductive Endocrinology & Infertility",
                         limit: int = 20, insurance: str = None) -> List[Provider]:
        """Search for providers by state using Healthgrades API"""
        providers = []

        # Get coordinates for the state (use state capital or center)
        state_coords = self._get_state_coords(state)
        if not state_coords:
            print(f"Could not get coordinates for state: {state}")
            return providers

        # Build API URL for provider search
        # Use the universal search API
        search_term = specialty.replace(' ', '%20')
        pt = f"{state_coords['lat']},{state_coords['lng']}"

        # Try the provider search endpoint
        url = f"{self.API_BASE}/search/providers"

        params = {
            'what': specialty,
            'where': state,
            'pt': pt,
            'pageNum': 1,
            'pageSize': min(limit, 20),
            'searchType': 'PracticingSpecialty'
        }

        # Add insurance filter if specified
        if insurance:
            params['insurance'] = insurance.capitalize()

        try:
            print(f"Searching Healthgrades API for {specialty} in {state}...")
            print(f"URL: {url}")
            print(f"Params: {params}")

            response = self.session.get(url, params=params, timeout=30)
            print(f"Response status: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                print(f"Response keys: {data.keys() if isinstance(data, dict) else 'Not a dict'}")

                # Extract providers from response
                provider_list = self._extract_providers_from_response(data, state)
                print(f"Found {len(provider_list)} providers from API")

                for provider_data in provider_list[:limit]:
                    provider = self._parse_provider_data(provider_data)
                    if provider:
                        providers.append(provider)
                    time.sleep(self.delay)

            else:
                print(f"API returned status {response.status_code}: {response.text[:500]}")

        except Exception as e:
            print(f"Error searching Healthgrades API: {e}")
            import traceback
            traceback.print_exc()

        return providers

    def _get_state_coords(self, state: str) -> Optional[Dict]:
        """Get approximate coordinates for a state"""
        # State center coordinates (approximate)
        state_centers = {
            'AL': {'lat': 32.806671, 'lng': -86.791130},
            'AK': {'lat': 61.370716, 'lng': -152.404419},
            'AZ': {'lat': 33.729759, 'lng': -111.431221},
            'AR': {'lat': 34.969704, 'lng': -92.373123},
            'CA': {'lat': 36.778259, 'lng': -119.417931},
            'CO': {'lat': 39.059811, 'lng': -105.311104},
            'CT': {'lat': 41.597782, 'lng': -72.755371},
            'DE': {'lat': 39.318523, 'lng': -75.507141},
            'FL': {'lat': 27.766279, 'lng': -81.686783},
            'GA': {'lat': 33.040619, 'lng': -83.643074},
            'HI': {'lat': 21.094318, 'lng': -157.498337},
            'ID': {'lat': 44.240459, 'lng': -114.478828},
            'IL': {'lat': 40.349457, 'lng': -88.986137},
            'IN': {'lat': 39.849426, 'lng': -86.258278},
            'IA': {'lat': 42.011539, 'lng': -93.210526},
            'KS': {'lat': 38.526600, 'lng': -96.726486},
            'KY': {'lat': 37.668140, 'lng': -84.670067},
            'LA': {'lat': 31.169546, 'lng': -91.867805},
            'ME': {'lat': 44.693947, 'lng': -69.381927},
            'MD': {'lat': 39.063946, 'lng': -76.802101},
            'MA': {'lat': 42.230171, 'lng': -71.530106},
            'MI': {'lat': 43.326618, 'lng': -84.536095},
            'MN': {'lat': 45.694454, 'lng': -93.900192},
            'MS': {'lat': 32.741646, 'lng': -89.678696},
            'MO': {'lat': 38.456085, 'lng': -92.288368},
            'MT': {'lat': 46.921925, 'lng': -110.454353},
            'NE': {'lat': 41.125370, 'lng': -98.268082},
            'NV': {'lat': 38.313515, 'lng': -117.055374},
            'NH': {'lat': 43.452492, 'lng': -71.563896},
            'NJ': {'lat': 40.298904, 'lng': -74.521011},
            'NM': {'lat': 34.840515, 'lng': -106.248482},
            'NY': {'lat': 42.165726, 'lng': -74.948051},
            'NC': {'lat': 35.630066, 'lng': -79.806419},
            'ND': {'lat': 47.528912, 'lng': -99.784012},
            'OH': {'lat': 40.388783, 'lng': -82.764915},
            'OK': {'lat': 35.565342, 'lng': -96.928917},
            'OR': {'lat': 44.572021, 'lng': -122.070938},
            'PA': {'lat': 40.590752, 'lng': -77.209755},
            'RI': {'lat': 41.680893, 'lng': -71.511780},
            'SC': {'lat': 33.856892, 'lng': -80.945007},
            'SD': {'lat': 44.299782, 'lng': -99.438828},
            'TN': {'lat': 35.747845, 'lng': -86.692345},
            'TX': {'lat': 31.054487, 'lng': -97.563461},
            'UT': {'lat': 40.150032, 'lng': -111.862434},
            'VT': {'lat': 44.045876, 'lng': -72.710686},
            'VA': {'lat': 37.769337, 'lng': -78.169968},
            'WA': {'lat': 47.400902, 'lng': -121.490494},
            'WV': {'lat': 38.491226, 'lng': -80.954453},
            'WI': {'lat': 44.268543, 'lng': -89.616508},
            'WY': {'lat': 42.755966, 'lng': -107.302490},
            'DC': {'lat': 38.905985, 'lng': -77.033418}
        }
        return state_centers.get(state.upper())

    def _extract_providers_from_response(self, data: Dict, state: str) -> List[Dict]:
        """Extract provider list from API response"""
        providers = []

        # Try different response structures
        if isinstance(data, dict):
            # Try 'results' key
            if 'results' in data:
                providers = data['results']
            # Try 'response' -> 'results'
            elif 'response' in data and isinstance(data['response'], dict):
                if 'results' in data['response']:
                    providers = data['response']['results']
                elif 'providers' in data['response']:
                    providers = data['response']['providers']
            # Try 'data' key
            elif 'data' in data:
                if isinstance(data['data'], list):
                    providers = data['data']
                elif isinstance(data['data'], dict) and 'results' in data['data']:
                    providers = data['data']['results']
            # Try 'providers' key directly
            elif 'providers' in data:
                providers = data['providers']
            # Try 'searchResults'
            elif 'searchResults' in data:
                providers = data['searchResults']

        return providers if isinstance(providers, list) else []

    def _parse_provider_data(self, data: Dict) -> Optional[Provider]:
        """Parse provider data from API response"""
        try:
            # Extract basic info
            full_name = data.get('name', '') or data.get('fullName', '')
            if not full_name:
                return None

            # Parse name
            name_parts = self._parse_name(full_name)

            # Extract photo
            photo_url = None
            if 'imageUrl' in data:
                photo_url = urljoin(self.BASE_URL, data['imageUrl'])
            elif 'photoUrl' in data:
                photo_url = urljoin(self.BASE_URL, data['photoUrl'])

            # Extract rating
            rating = None
            if 'rating' in data:
                rating = float(data['rating']) if isinstance(data['rating'], (int, float, str)) else None
            elif 'overallRating' in data:
                rating = float(data['overallRating']) if isinstance(data['overallRating'], (int, float, str)) else None
            elif 'averageRating' in data:
                rating = float(data['averageRating']) if isinstance(data['averageRating'], (int, float, str)) else None

            # Extract review count
            review_count = None
            if 'reviewCount' in data:
                review_count = int(data['reviewCount']) if isinstance(data['reviewCount'], (int, float, str)) else None
            elif 'numberOfReviews' in data:
                review_count = int(data['numberOfReviews']) if isinstance(data['numberOfReviews'], (int, float, str)) else None

            # Extract expertise/specialties
            expertise = []
            if 'specialties' in data and isinstance(data['specialties'], list):
                expertise = [s.get('name', s) if isinstance(s, dict) else s for s in data['specialties']]
            elif 'specialty' in data:
                expertise = [data['specialty']]

            # Extract location
            office_location = ""
            city = data.get('city', '')
            state = data.get('state', '')
            zip_code = data.get('zip', '') or data.get('zipCode', '')

            if 'address' in data:
                if isinstance(data['address'], dict):
                    office_location = data['address'].get('street', '')
                    city = city or data['address'].get('city', '')
                    state = state or data['address'].get('state', '')
                    zip_code = zip_code or data['address'].get('zip', '')
                else:
                    office_location = data['address']

            if city and state:
                office_location = f"{office_location}, {city}, {state} {zip_code}".strip(', ')

            # Extract phone
            phone = data.get('phone') or data.get('phoneNumber')

            # Extract bio
            bio = data.get('bio', '') or data.get('overview', '') or data.get('description', '')

            # Extract profile URL
            profile_url = ""
            if 'profileUrl' in data:
                profile_url = urljoin(self.BASE_URL, data['profileUrl'])
            elif 'url' in data:
                profile_url = urljoin(self.BASE_URL, data['url'])
            elif 'providerId' in data:
                profile_url = f"{self.BASE_URL}/physician/{data['providerId']}"

            return Provider(
                first_name=name_parts['first'],
                last_name=name_parts['last'],
                title=name_parts['title'],
                full_name=full_name,
                photo_url=photo_url,
                expertise=expertise[:5],
                healthgrades_rating=rating,
                review_count=review_count,
                office_location=office_location,
                city=city,
                state=state,
                zip_code=zip_code,
                phone=phone,
                bio=bio[:500] if bio else "",
                profile_url=profile_url,
                source='healthgrades'
            )

        except Exception as e:
            print(f"Error parsing provider data: {e}")
            return None

    def _parse_name(self, full_name: str) -> Dict:
        """Parse full name into components"""
        title = ""
        titles = ['MD', 'DO', 'PhD', 'Dr.', 'Dr', 'NP', 'PA', 'RN']

        # Check for titles at the end
        for t in titles:
            if full_name.endswith(f", {t}") or full_name.endswith(f" {t}"):
                title = t
                full_name = full_name.replace(f", {t}", "").replace(f" {t}", "").strip()
                break

        # Split name
        parts = full_name.split()
        if len(parts) >= 2:
            return {
                'first': parts[0],
                'last': ' '.join(parts[1:]),
                'title': title
            }
        return {'first': full_name, 'last': '', 'title': title}


class REIScraper:
    """Main scraper that combines multiple sources"""

    def __init__(self):
        self.healthgrades = HealthgradesScraper()

    def scrape(self, state: str, sources: List[str] = None, network: str = None) -> List[Provider]:
        """
        Scrape REI providers

        Args:
            state: US state abbreviation (e.g., 'CA', 'NY')
            sources: List of sources to scrape ['healthgrades']
            network: Insurance network filter ('cigna' or None)
        """
        if sources is None:
            sources = ['healthgrades']

        providers = []

        if 'healthgrades' in sources:
            print(f"Scraping Healthgrades for {state}...")
            hg_providers = self.healthgrades.search_providers(state, insurance=network)
            providers.extend(hg_providers)

        return providers
