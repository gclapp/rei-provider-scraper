"""
REI Provider Scraper
Scrapes Healthgrades for REI specialists with full details
"""

import requests
from bs4 import BeautifulSoup
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
    """Scraper for Healthgrades.com"""

    BASE_URL = "https://www.healthgrades.com"
    SEARCH_URL = "https://www.healthgrades.com/usearch"

    def __init__(self, delay: float = 1.5):
        self.delay = delay
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
        })

    def search_providers(self, state: str, specialty: str = "reproductive-endocrinology", limit: int = 20) -> List[Provider]:
        """Search for providers by state and extract full details"""
        providers = []

        # Healthgrades search URL format
        url = f"{self.SEARCH_URL}?what={specialty.replace('-', '%20')}&where={state}&page=1"

        try:
            print(f"Fetching search results from: {url}")
            response = self.session.get(url, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')

            # Find provider cards - try multiple selectors
            provider_cards = (
                soup.find_all('div', {'data-testid': 'search-provider-card'}) or
                soup.find_all('div', class_=re.compile('provider-card|search-result-card')) or
                soup.find_all('article') or
                soup.find_all('div', class_=re.compile('card'))
            )

            print(f"Found {len(provider_cards)} provider cards")

            for card in provider_cards[:limit]:
                try:
                    # Get the profile URL from the card
                    profile_link = card.find('a', href=re.compile('/physician/'))
                    if not profile_link:
                        continue

                    profile_url = urljoin(self.BASE_URL, profile_link['href'])
                    print(f"Processing: {profile_url}")

                    # Get full details from profile page
                    provider = self._get_provider_details(profile_url)
                    if provider:
                        providers.append(provider)

                    time.sleep(self.delay)

                except Exception as e:
                    print(f"Error processing card: {e}")
                    continue

        except Exception as e:
            print(f"Error searching Healthgrades: {e}")

        return providers

    def _get_provider_details(self, profile_url: str) -> Optional[Provider]:
        """Extract full provider details from profile page"""
        try:
            response = self.session.get(profile_url, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')

            # Extract photo
            photo_url = None
            photo_elem = (
                soup.find('img', {'data-testid': 'provider-photo'}) or
                soup.find('img', class_=re.compile('provider-photo|profile-photo')) or
                soup.find('img', alt=re.compile('photo|profile', re.I))
            )
            if photo_elem and photo_elem.get('src'):
                photo_url = urljoin(self.BASE_URL, photo_elem['src'])

            # Extract name
            full_name = ""
            first_name = ""
            last_name = ""
            title = ""

            name_elem = (
                soup.find('h1', {'data-testid': 'provider-name'}) or
                soup.find('h1', class_=re.compile('provider-name')) or
                soup.find('h1')
            )
            if name_elem:
                full_name = name_elem.get_text(strip=True)
                # Parse name parts
                name_parts = self._parse_name(full_name)
                first_name = name_parts['first']
                last_name = name_parts['last']
                title = name_parts['title']

            # Extract rating
            rating = None
            review_count = None
            rating_elem = (
                soup.find('span', {'data-testid': 'overall-rating'}) or
                soup.find('div', class_=re.compile('rating-score|rating-number'))
            )
            if rating_elem:
                rating_text = rating_elem.get_text(strip=True)
                rating_match = re.search(r'(\d+\.?\d*)', rating_text)
                if rating_match:
                    rating = float(rating_match.group(1))

            # Extract review count
            review_elem = (
                soup.find('span', {'data-testid': 'review-count'}) or
                soup.find('span', text=re.compile(r'\d+\s+reviews?', re.I))
            )
            if review_elem:
                review_text = review_elem.get_text(strip=True)
                review_match = re.search(r'(\d+)', review_text)
                if review_match:
                    review_count = int(review_match.group(1))

            # Extract expertise/specialties
            expertise = []
            expertise_section = (
                soup.find('div', {'data-testid': 'specialties-section'}) or
                soup.find('section', text=re.compile('specialties', re.I)) or
                soup.find('div', class_=re.compile('specialties'))
            )
            if expertise_section:
                specialty_items = expertise_section.find_all(['li', 'span', 'a'])
                for item in specialty_items:
                    text = item.get_text(strip=True)
                    if text and len(text) > 2:
                        expertise.append(text)

            # Extract office location
            office_location = ""
            city = ""
            state = ""
            zip_code = ""
            phone = None

            location_elem = (
                soup.find('address', {'data-testid': 'practice-address'}) or
                soup.find('div', class_=re.compile('practice-address|office-location')) or
                soup.find('address')
            )
            if location_elem:
                office_location = location_elem.get_text(separator=' ', strip=True)
                # Parse location
                location_parts = self._parse_location(office_location)
                city = location_parts['city']
                state = location_parts['state']
                zip_code = location_parts['zip']

            # Extract phone
            phone_elem = (
                soup.find('a', href=re.compile('tel:')) or
                soup.find('span', {'data-testid': 'phone-number'}) or
                soup.find(text=re.compile(r'\(\d{3}\)\s*\d{3}-\d{4}'))
            )
            if phone_elem:
                if phone_elem.name == 'a':
                    phone = phone_elem.get_text(strip=True)
                else:
                    phone_match = re.search(r'\(\d{3}\)\s*\d{3}-\d{4}', str(phone_elem))
                    if phone_match:
                        phone = phone_match.group(0)

            # Extract bio/overview
            bio = ""
            bio_elem = (
                soup.find('div', {'data-testid': 'provider-overview'}) or
                soup.find('div', class_=re.compile('provider-bio|about-section|overview')) or
                soup.find('p', class_=re.compile('description'))
            )
            if bio_elem:
                bio = bio_elem.get_text(separator=' ', strip=True)

            return Provider(
                first_name=first_name,
                last_name=last_name,
                title=title,
                full_name=full_name,
                photo_url=photo_url,
                expertise=expertise[:5],  # Limit to top 5
                healthgrades_rating=rating,
                review_count=review_count,
                office_location=office_location,
                city=city,
                state=state,
                zip_code=zip_code,
                phone=phone,
                bio=bio[:500] if bio else "",  # Limit bio length
                profile_url=profile_url,
                source='healthgrades'
            )

        except Exception as e:
            print(f"Error getting provider details from {profile_url}: {e}")
            return None

    def _parse_name(self, full_name: str) -> Dict:
        """Parse full name into components"""
        # Remove common titles
        title = ""
        titles = ['MD', 'DO', 'PhD', 'Dr.', 'Dr']
        for t in titles:
            if t in full_name:
                title = t
                full_name = full_name.replace(t, '').strip()

        # Split name
        parts = full_name.split()
        if len(parts) >= 2:
            return {
                'first': parts[0],
                'last': ' '.join(parts[1:]),
                'title': title
            }
        return {'first': full_name, 'last': '', 'title': title}

    def _parse_location(self, location_text: str) -> Dict:
        """Parse location text into components"""
        result = {'city': '', 'state': '', 'zip': ''}

        # Try to match City, State ZIP pattern
        match = re.search(r'([^,]+),\s*([A-Z]{2})\s*(\d{5}(-\d{4})?)?', location_text)
        if match:
            result['city'] = match.group(1).strip()
            result['state'] = match.group(2)
            result['zip'] = match.group(3) if match.group(3) else ''

        return result


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
            hg_providers = self.healthgrades.search_providers(state)
            providers.extend(hg_providers)
        
        # Note: Cigna filtering would require checking each provider
        # For now, we return all providers and note that filtering is needed
        if network == 'cigna':
            print(f"Note: Cigna network filtering requested but not yet implemented")
            # TODO: Implement Cigna network checking for each provider
        
        return providers
