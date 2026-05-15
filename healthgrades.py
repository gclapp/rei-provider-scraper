"""Healthgrades provider directory scraper using Playwright."""

import asyncio
import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Optional, List
from urllib.parse import quote

from playwright.async_api import async_playwright, Page, Browser, BrowserContext

from models import SearchCriteria, SearchResult, SourceInfo, Provider, Address
from sources.base import ProviderSource


class HealthgradesSource(ProviderSource):
    """Healthgrades provider directory scraper using Playwright browser automation."""
    
    # Base URL
    BASE_URL = "https://www.healthgrades.com"
    
    # Cigna insurance code for Healthgrades
    CIGNA_PAYOR_CODE = "HPY00006F7"
    
    # Settings
    DEFAULT_TIMEOUT = 30000
    NAVIGATION_TIMEOUT = 60000
    DELAY_BETWEEN_REQUESTS = 2.5
    
    def __init__(self, headless: bool = True):
        super().__init__()
        self.headless = headless
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.playwright = None
    
    @property
    def info(self) -> SourceInfo:
        return SourceInfo(
            id="healthgrades",
            name="Healthgrades (Browser)",
            description="Playwright-based scraper for Healthgrades provider directory",
            status="beta",
            requires_auth=False,
            auth_type=None,
            rate_limit="20 req/min",
            reliability="medium",
            notes="Uses public directory. No login required."
        )
    
    async def _start_browser(self) -> None:
        """Initialize browser and context."""
        if self.browser:
            return
            
        self.playwright = await async_playwright().start()
        
        self.browser = await self.playwright.chromium.launch(
            headless=self.headless,
            args=['--disable-blink-features=AutomationControlled']
        )
        
        self.context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        
        self.page = await self.context.new_page()
        self.page.set_default_timeout(self.DEFAULT_TIMEOUT)
    
    async def _stop_browser(self) -> None:
        """Clean up browser resources."""
        if self.context:
            await self.context.close()
            self.context = None
        if self.browser:
            await self.browser.close()
            self.browser = None
        if self.playwright:
            await self.playwright.stop()
            self.playwright = None
    
    async def close(self):
        """Clean up resources."""
        await self._stop_browser()
    
    async def authenticate(self, **kwargs) -> bool:
        """Authentication not required for public directory."""
        self._authenticated = True
        return True
    
    async def health_check(self) -> bool:
        """Check if Healthgrades is accessible."""
        try:
            await self._start_browser()
            await self.page.goto(self.BASE_URL, timeout=self.NAVIGATION_TIMEOUT)
            await asyncio.sleep(2)
            
            title = await self.page.title()
            return "healthgrades" in title.lower()
        except Exception as e:
            print(f"Health check failed: {e}")
            return False
    
    def _build_search_url(self, criteria: SearchCriteria) -> str:
        """Build Healthgrades search URL for REIs with Cigna insurance."""
        # Use the exact format from Geoff's search with National distance
        url = (
            f"{self.BASE_URL}/usearch?"
            f"what=Reproductive%20Endocrinology%20%26%20Infertility"
            f"&entityCode=PS310"
            f"&searchType=PracticingSpecialty"
            f"&payors={self.CIGNA_PAYOR_CODE}"
            f"&distances=National"
        )
        
        return url
    
    async def _get_total_results(self) -> int:
        """Get total number of results from page."""
        try:
            # Look for result count in page text
            text = await self.page.text_content('body')
            
            # Patterns to match result counts - look for largest number
            patterns = [
                r'We found (\d+,?\d*)',  # "We found 1,559 doctors"
                r'(\d+,?\d*)\s+doctors?',
                r'(\d+,?\d*)\s+results?',
                r'(\d+,?\d*)\s+providers?',
            ]
            
            max_count = 0
            for pattern in patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                for match in matches:
                    try:
                        count_str = match.replace(',', '')
                        count = int(count_str)
                        if count > max_count:
                            max_count = count
                    except:
                        continue
            
            return max_count
        except Exception as e:
            print(f"  ⚠️  Could not get total results: {e}")
            return 0
    
    async def _extract_providers_from_page(self) -> List[Provider]:
        """Extract provider data from current page."""
        providers = []
        
        try:
            # Wait for results to load
            await asyncio.sleep(2)
            
            # Look for provider cards - try multiple selectors
            provider_cards = await self.page.query_selector_all(
                'article, [data-testid*="provider"], [data-testid*="doctor"], '
                '[class*="provider-card"], [class*="doctor-card"], '
                '[class*="search-result"]'
            )
            
            if not provider_cards:
                # Fallback: look for h3 elements that contain provider names
                # Also look for address elements that are siblings/children
                h3_elements = await self.page.query_selector_all('h3')
                address_elements = await self.page.query_selector_all('address')
                print(f"  Found {len(h3_elements)} h3 elements, {len(address_elements)} address elements")
                
                for i, h3 in enumerate(h3_elements):
                    try:
                        name_text = await h3.text_content()
                        if name_text and len(name_text.strip()) > 2:
                            # Check if it looks like a provider name
                            name = name_text.strip()
                            
                            # Try to find corresponding address (same index)
                            address_text = None
                            if i < len(address_elements):
                                address_text = await address_elements[i].text_content()
                            
                            # Try to find parent card for more info
                            parent = await h3.evaluate('el => el.closest("article, [class*=card], [class*=result], li, div")')
                            
                            specialty = None
                            
                            if parent:
                                # Try to find specialty within parent
                                spec_elem = await self.page.query_selector(
                                    f'[class*="specialty"], [class*="title"], [data-testid*="specialty"]'
                                )
                                if spec_elem:
                                    specialty = await spec_elem.text_content()
                            
                            # Parse address
                            address = None
                            if address_text:
                                address = self._parse_address(address_text.strip())
                            
                            provider = Provider(
                                name=name,
                                specialties=[specialty.strip()] if specialty else ["Reproductive Endocrinology"],
                                address=address,
                                source="healthgrades",
                                search_zip=self.current_zip,
                                search_specialty=self.current_specialty,
                                search_state=self.current_state
                            )
                            providers.append(provider)
                    except Exception as e:
                        continue
            else:
                print(f"  Found {len(provider_cards)} provider cards")
                
                for card in provider_cards:
                    try:
                        # Extract name
                        name_elem = await card.query_selector('h3, [class*="name"], a[href*="/physician/"]')
                        name = await name_elem.text_content() if name_elem else None
                        
                        if not name:
                            continue
                        
                        # Extract specialty
                        specialty_elem = await card.query_selector('[class*="specialty"], [class*="title"], [data-testid*="specialty"]')
                        specialty = await specialty_elem.text_content() if specialty_elem else None
                        
                        # Extract address
                        address_elem = await card.query_selector('[class*="address"], [class*="location"], [data-testid*="address"]')
                        address_text = await address_elem.text_content() if address_elem else None
                        
                        # Parse address
                        address = None
                        if address_text:
                            address = self._parse_address(address_text.strip())
                        
                        # Extract phone
                        phone_elem = await card.query_selector('[class*="phone"], [data-testid*="phone"]')
                        phone = await phone_elem.text_content() if phone_elem else None
                        
                        # Extract rating
                        rating_elem = await card.query_selector('[class*="rating"], [data-testid*="rating"]')
                        rating = await rating_elem.text_content() if rating_elem else None
                        
                        provider = Provider(
                            name=name.strip(),
                            specialties=[specialty.strip()] if specialty else ["Reproductive Endocrinology"],
                            address=address,
                            phone=phone.strip() if phone else None,
                            source="healthgrades",
                            search_zip=self.current_zip,
                            search_specialty=self.current_specialty,
                            search_state=self.current_state
                        )
                        providers.append(provider)
                    except Exception as e:
                        continue
            
            return providers
            
        except Exception as e:
            print(f"  ❌ Error extracting providers: {e}")
            return providers
    
    def _parse_address(self, address_text: str) -> Optional[Address]:
        """Parse address text from Healthgrades into Address object.
        
        Healthgrades format: '123 Main St Ste 100CityName, ST 12345'
        The city name is concatenated directly to the street without separator.
        """
        try:
            if not address_text:
                return None
            
            # Find state and zip pattern
            state_zip_match = re.search(r'([A-Z]{2})\s+(\d{5}(-\d{4})?)', address_text)
            if not state_zip_match:
                # No state/zip found, return as street only
                return Address(street=address_text.strip(), city="", state="", zip="")
            
            state = state_zip_match.group(1)
            zip_code = state_zip_match.group(2)
            
            # Everything before state is street + city
            before_state = address_text[:state_zip_match.start()].strip()
            
            # Remove trailing comma if present
            before_state = before_state.rstrip(',')
            
            # Common US city names that might appear (partial list for major cities)
            common_cities = [
                'New York', 'Los Angeles', 'Chicago', 'Houston', 'Phoenix', 'Philadelphia',
                'San Antonio', 'San Diego', 'Dallas', 'San Jose', 'Austin', 'Jacksonville',
                'Fort Worth', 'Columbus', 'Charlotte', 'San Francisco', 'Indianapolis',
                'Seattle', 'Denver', 'Washington', 'Boston', 'El Paso', 'Nashville',
                'Detroit', 'Oklahoma City', 'Portland', 'Las Vegas', 'Louisville',
                'Baltimore', 'Milwaukee', 'Albuquerque', 'Tucson', 'Fresno', 'Sacramento',
                'Mesa', 'Kansas City', 'Atlanta', 'Long Beach', 'Colorado Springs',
                'Raleigh', 'Miami', 'Virginia Beach', 'Omaha', 'Oakland', 'Minneapolis',
                'Tulsa', 'Arlington', 'Wichita', 'Bakersfield', 'West Chester', 'Chester',
                'Newport Beach', 'Beverly Hills', 'Palo Alto', 'Menlo Park', 'Redwood City',
                'Williamsburg', 'Addison', 'Gilbert', 'Scottsdale', 'Tempe', 'Chandler',
                'Plano', 'Frisco', 'Irving', 'Arlington', 'Fort Worth', 'Denton',
                'McKinney', 'Allen', 'Richardson', 'Garland', 'Mesquite', 'Carrollton'
            ]
            
            # Try to find a known city name in the string
            city = ""
            street = before_state
            
            for city_name in sorted(common_cities, key=len, reverse=True):
                # Look for city name at the end of the string (before state)
                if before_state.endswith(city_name):
                    city = city_name
                    street = before_state[:-len(city_name)].strip()
                    break
            
            # If no known city found, use heuristic
            if not city:
                words = before_state.split()
                street_suffixes = ['Rd', 'St', 'Ave', 'Blvd', 'Dr', 'Ln', 'Way', 'Ct', 'Pl', 
                                  'Ste', 'Unit', 'Suite', 'Bldg', 'Fl', 'Floor', ' Hwy', 'Pkwy']
                
                # Find the last street suffix
                last_suffix_idx = -1
                for i, word in enumerate(words):
                    clean_word = word.rstrip(',.')
                    if any(clean_word.endswith(suffix) or clean_word == suffix for suffix in street_suffixes):
                        last_suffix_idx = i
                
                if last_suffix_idx >= 0 and last_suffix_idx < len(words) - 1:
                    # Everything after the last suffix is likely city
                    # But we need to handle cases like "Ste EColumbus" where there's no space
                    potential_city = ' '.join(words[last_suffix_idx + 1:])
                    
                    # Check if city is mashed with previous word (e.g., "EColumbus")
                    last_word = words[last_suffix_idx]
                    for cn in common_cities:
                        if last_word.endswith(cn) and len(last_word) > len(cn):
                            # Found mashed city name
                            city = cn
                            words[last_suffix_idx] = last_word[:-len(cn)]
                            street = ' '.join(words[:last_suffix_idx + 1])
                            break
                    else:
                        # No mashed city, use potential_city
                        if potential_city:
                            city = potential_city
                            street = ' '.join(words[:last_suffix_idx + 1])
                        else:
                            street = before_state
                else:
                    street = before_state
            
            return Address(
                street=street,
                city=city,
                state=state,
                zip=zip_code
            )
                
        except Exception as e:
            # Return raw text as street if parsing fails
            return Address(street=address_text.strip() if address_text else "", 
                          city="", state="", zip="")
    
    async def _close_modals(self) -> None:
        """Close any popup modals that might be blocking interactions."""
        try:
            # Look for common close buttons
            close_selectors = [
                'button[aria-label="Close"]',
                'button[class*="close"]',
                '[class*="modal"] button',
                '[class*="overlay"]',
                'button:has-text("Close")',
                'button:has-text("✕")',
                'button:has-text("×")',
            ]
            
            for selector in close_selectors:
                try:
                    elements = await self.page.query_selector_all(selector)
                    for elem in elements:
                        is_visible = await elem.is_visible()
                        if is_visible:
                            await elem.click()
                            print("    🗑️  Closed modal")
                            await asyncio.sleep(0.5)
                except:
                    continue
            
            # Press Escape key to close any overlays
            await self.page.keyboard.press("Escape")
            await asyncio.sleep(0.5)
            
        except Exception as e:
            pass
    
    async def _go_to_next_page(self) -> bool:
        """Navigate to next page of results."""
        try:
            # Close any modals first
            await self._close_modals()
            
            # Look for next page button - Healthgrades uses aria-label="Next Page"
            print("  🔍 Looking for next page button...")
            
            # Try the exact selector from debug
            next_btn = await self.page.query_selector('a[aria-label="Next Page"]')
            
            if next_btn:
                is_visible = await next_btn.is_visible()
                print(f"    Found Next Page button, visible={is_visible}")
                
                if is_visible:
                    # Try JavaScript click to avoid overlay issues
                    try:
                        await next_btn.evaluate('el => el.click()')
                        print("  ➡️  Navigated to next page (JS click)")
                    except Exception as e:
                        print(f"    JS click failed: {e}, trying regular click...")
                        try:
                            await next_btn.click()
                            print("  ➡️  Navigated to next page")
                        except Exception as e2:
                            print(f"    Regular click also failed: {e2}")
                            return False
                    
                    await asyncio.sleep(3)
                    return True
            
            # Fallback: try to find page number links and click the next one
            try:
                # Get current page number from URL or active page
                current_url = self.page.url
                import re
                page_match = re.search(r'page=(\d+)', current_url)
                current_page = int(page_match.group(1)) if page_match else 1
                next_page = current_page + 1
                
                # Look for link to next page number
                next_page_link = await self.page.query_selector(f'a[aria-label="Page {next_page}"]')
                if next_page_link:
                    is_visible = await next_page_link.is_visible()
                    if is_visible:
                        try:
                            await next_page_link.evaluate('el => el.click()')
                            print(f"  ➡️  Navigated to page {next_page} (JS click)")
                        except:
                            await next_page_link.click()
                            print(f"  ➡️  Navigated to page {next_page}")
                        await asyncio.sleep(3)
                        return True
            except Exception as e:
                print(f"    Page number navigation failed: {e}")
            
            print("  ✅ No more pages or couldn't find next button")
            return False
            
        except Exception as e:
            print(f"  ⚠️  Error navigating to next page: {e}")
            return False
    
    def _build_page_url(self, page_num: int) -> str:
        """Build URL for a specific page number using exact format from user."""
        base_url = (
            f"{self.BASE_URL}/usearch?"
            f"what=Reproductive%20Endocrinology%20%26%20Infertility"
            f"&entityCode=PS310"
            f"&searchType=PracticingSpecialty"
            f"&pt=32.67194%2C-117.105423"
            f"&distances=National"
            f"&payors={self.CIGNA_PAYOR_CODE}"
            f"&pageNum={page_num}"
            f"&sort.provider=bestmatch"
        )
        
        return base_url
    
    async def search(self, criteria: SearchCriteria) -> SearchResult:
        """Search for REIs on Healthgrades with Cigna insurance."""
        start_time = datetime.utcnow()
        
        # Store for extraction
        self.current_zip = criteria.zip_code
        self.current_specialty = criteria.specialty or "Reproductive Endocrinology"
        self.current_state = criteria.state
        
        all_providers = []
        
        try:
            await self._start_browser()
            
            print(f"🔍 Searching Healthgrades for REIs with Cigna...")
            if criteria.state:
                print(f"   State: {criteria.state}")
            else:
                print(f"   National search")
            
            # Build and navigate to search URL (page 1)
            search_url = self._build_page_url(1)
            print(f"  🌐 Loading: {search_url}")
            
            await self.page.goto(search_url, timeout=self.NAVIGATION_TIMEOUT, wait_until="domcontentloaded")
            await asyncio.sleep(5)  # Wait for results to load
            
            # Get total results count
            total_results = await self._get_total_results()
            print(f"  📊 Total results: {total_results}")
            
            # Take screenshot
            await self.page.screenshot(path="healthgrades_search_start.png", full_page=True)
            
            # Extract all pages using direct URL navigation
            page_num = 1
            max_pages = criteria.max_pages
            
            while page_num <= max_pages:
                print(f"\n  📄 Page {page_num}:")
                
                # If not first page, navigate directly to page URL
                if page_num > 1:
                    page_url = self._build_page_url(page_num)
                    print(f"    🌐 Loading: {page_url}")
                    await self.page.goto(page_url, timeout=self.NAVIGATION_TIMEOUT, wait_until="domcontentloaded")
                    await asyncio.sleep(3)
                
                # Extract providers from current page
                providers = await self._extract_providers_from_page()
                print(f"    Found {len(providers)} providers")
                
                # Filter by state if specified
                if criteria.state:
                    filtered = []
                    for p in providers:
                        if p.address and p.address.state == criteria.state:
                            filtered.append(p)
                        elif not p.address or not p.address.state:
                            # Include if we couldn't parse state
                            filtered.append(p)
                    providers = filtered
                    print(f"    {len(providers)} match state filter")
                
                all_providers.extend(providers)
                
                # Check if we got any providers - if not, might be last page
                if len(providers) == 0:
                    print("  ✅ No more providers found")
                    break
                
                page_num += 1
                
                # Rate limiting
                await asyncio.sleep(self.DELAY_BETWEEN_REQUESTS)
            
            search_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            
            print(f"\n  ✅ Total providers extracted: {len(all_providers)}")
            
            # Take final screenshot
            await self.page.screenshot(path="healthgrades_search_final.png", full_page=True)
            
            return SearchResult(
                source="healthgrades",
                criteria=criteria,
                providers=all_providers,
                total_count=len(all_providers),
                has_more=False,
                search_time_ms=search_time
            )
            
        except Exception as e:
            search_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            # Try to save error screenshot
            try:
                if self.page:
                    await self.page.screenshot(path="healthgrades_error.png")
            except:
                pass
            
            return SearchResult(
                source="healthgrades",
                criteria=criteria,
                providers=all_providers,
                error=str(e),
                search_time_ms=search_time
            )
