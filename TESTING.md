# REI Provider Scraper - Testing Document

## 1. Testing Strategy Overview

### Testing Pyramid

```
        ┌─────────┐
        │   E2E   │  <- Mobile app + Backend + Scrapers
        │  (10%)  │
        ├─────────┤
        │Integration│ <- API + Database + External services
        │  (20%)  │
        ├─────────┤
        │  Unit   │  <- Individual functions, scrapers
        │  (70%)  │
        └─────────┘
```

### Test Categories

| Type | Tool | Coverage Target |
|------|------|-----------------|
| Unit | pytest | 80% |
| Integration | pytest + test DB | 60% |
| E2E | Playwright | Critical paths |
| Mobile | Detox | Core flows |
| Performance | Locust | API endpoints |

---

## 2. Unit Testing

### 2.1 Scraper Tests

```python
# tests/test_healthgrades_scraper.py

class TestHealthgradesScraper:
    
    def test_parse_provider_name(self):
        """Extract full name from profile page"""
        html = load_fixture('provider_profile.html')
        name = parse_provider_name(html)
        assert name == 'Dr. Jane Smith, MD'
    
    def test_parse_clinic_name(self):
        """Extract clinic/facility name"""
        html = load_fixture('provider_profile.html')
        clinic = parse_clinic_name(html)
        assert clinic == 'Fertility Center of Excellence'
    
    def test_parse_address(self):
        """Extract and standardize address"""
        html = load_fixture('provider_profile.html')
        address = parse_address(html)
        assert address['city'] == 'Los Angeles'
        assert address['state'] == 'CA'
        assert address['zip'] == '90025'
    
    def test_parse_healthgrades_score(self):
        """Extract rating 1-5"""
        html = load_fixture('provider_profile.html')
        score = parse_healthgrades_score(html)
        assert 1.0 <= score <= 5.0
    
    def test_handle_missing_data(self):
        """Gracefully handle missing fields"""
        html = '<html></html>'
        result = parse_provider(html)
        assert result['name'] is None
        assert result['error'] is not None
    
    def test_rate_limiting(self):
        """Respect rate limits"""
        scraper = HealthgradesScraper(delay=1.0)
        start = time.time()
        scraper.scrape_provider('url1')
        scraper.scrape_provider('url2')
        elapsed = time.time() - start
        assert elapsed >= 1.0  # At least 1 second between requests
```

### 2.2 API Tests

```python
# tests/test_api.py

class TestAPI:
    
    def test_list_providers(self, client):
        """GET /api/providers returns list"""
        response = client.get('/api/providers')
        assert response.status_code == 200
        assert 'providers' in response.json()
    
    def test_search_providers(self, client):
        """POST /api/providers/search filters correctly"""
        response = client.post('/api/providers/search', json={
            'state': 'CA',
            'min_score': 4.0
        })
        assert response.status_code == 200
        for provider in response.json()['providers']:
            assert provider['state'] == 'CA'
            assert provider['healthgrades_score'] >= 4.0
    
    def test_export_csv(self, client):
        """POST /api/export/csv returns file"""
        response = client.post('/api/export/csv')
        assert response.status_code == 200
        assert response.headers['content-type'] == 'text/csv'
    
    def test_start_scrape_job(self, client):
        """POST /api/scrape/start initiates job"""
        response = client.post('/api/scrape/start', json={
            'source': 'healthgrades',
            'state': 'CA'
        })
        assert response.status_code == 202
        assert 'job_id' in response.json()
```

### 2.3 Database Tests

```python
# tests/test_database.py

class TestDatabase:
    
    def test_provider_insert(self, db):
        """Insert provider record"""
        provider = {
            'full_name': 'Dr. Test',
            'city': 'Los Angeles',
            'state': 'CA'
        }
        id = db.insert_provider(provider)
        assert id is not None
    
    def test_provider_deduplication(self, db):
        """Don't insert duplicates"""
        provider = {'npi': '1234567890', 'full_name': 'Dr. Test'}
        db.insert_provider(provider)
        
        # Try to insert again
        with pytest.raises(IntegrityError):
            db.insert_provider(provider)
    
    def test_search_by_state(self, db):
        """Filter providers by state"""
        db.insert_provider({'full_name': 'Dr. CA', 'state': 'CA'})
        db.insert_provider({'full_name': 'Dr. NY', 'state': 'NY'})
        
        results = db.search_providers(state='CA')
        assert len(results) == 1
        assert results[0]['full_name'] == 'Dr. CA'
```

---

## 3. Integration Testing

### 3.1 Scraper + Database

```python
# tests/integration/test_scraper_db.py

class TestScraperDatabaseIntegration:
    
    def test_scrape_and_store(self, test_db):
        """Full flow: scrape → validate → store"""
        scraper = HealthgradesScraper(db=test_db)
        
        # Mock HTTP response
        with responses.RequestsMock() as rsps:
            rsps.add(responses.GET, 'https://healthgrades.com/physician/dr-jane-smith',
                    body=load_fixture('provider_profile.html'), status=200)
            
            provider = scraper.scrape_provider('https://healthgrades.com/physician/dr-jane-smith')
        
        # Verify stored in DB
        stored = test_db.get_provider_by_name('Dr. Jane Smith')
        assert stored is not None
        assert stored['city'] == 'Los Angeles'
    
    def test_scrape_job_tracking(self, test_db):
        """Track scrape job progress"""
        job = ScrapeJob(source='healthgrades', state='CA')
        job.start()
        
        # Simulate scraping
        job.increment_found(100)
        job.increment_scraped(50)
        
        # Verify job status
        status = test_db.get_scrape_job(job.id)
        assert status['providers_found'] == 100
        assert status['providers_scraped'] == 50
```

### 3.2 API + Database

```python
# tests/integration/test_api_db.py

class TestAPIDatabaseIntegration:
    
    def test_full_provider_workflow(self, client, test_db):
        """Create, read, search, export"""
        # Create provider
        response = client.post('/api/providers', json={
            'full_name': 'Dr. Integration Test',
            'city': 'San Francisco',
            'state': 'CA'
        })
        provider_id = response.json()['id']
        
        # Read provider
        response = client.get(f'/api/providers/{provider_id}')
        assert response.json()['full_name'] == 'Dr. Integration Test'
        
        # Search
        response = client.post('/api/providers/search', json={'state': 'CA'})
        assert len(response.json()['providers']) == 1
        
        # Export
        response = client.post('/api/export/csv')
        csv_content = response.content.decode('utf-8')
        assert 'Dr. Integration Test' in csv_content
```

---

## 4. E2E Testing

### 4.1 Scraper E2E

```python
# tests/e2e/test_scraper_e2e.py

class TestScraperE2E:
    """Test against real websites (limited runs)"""
    
    @pytest.mark.e2e
    @pytest.mark.slow
    def test_scrape_single_provider(self):
        """Scrape one real provider (use sparingly)"""
        scraper = HealthgradesScraper()
        
        # Use known provider URL
        url = 'https://www.healthgrades.com/physician/dr-jane-smith-12345'
        provider = scraper.scrape_provider(url)
        
        assert provider['full_name'] is not None
        assert provider['city'] is not None
        assert provider['healthgrades_score'] is not None
    
    @pytest.mark.e2e
    @pytest.mark.slow
    def test_scrape_search_results(self):
        """Scrape search results page"""
        scraper = HealthgradesScraper()
        
        providers = scraper.search_providers(
            specialty='reproductive-endocrinology',
            state='CA',
            limit=5  # Only 5 for testing
        )
        
        assert len(providers) > 0
        assert len(providers) <= 5
```

### 4.2 Mobile E2E

```javascript
// e2e/scrapeFlow.test.js

describe('Scrape Flow', () => {
  beforeAll(async () => {
    await device.launchApp();
  });

  it('should start a scrape job', async () => {
    await element(by.id('scrape-tab')).tap();
    await element(by.id('start-scrape-btn')).tap();
    await element(by.text('Healthgrades')).tap();
    await element(by.text('California')).tap();
    await element(by.id('confirm-btn')).tap();
    
    await expect(element(by.id('progress-bar'))).toBeVisible();
    await expect(element(by.text('Scraping...'))).toBeVisible();
  });

  it('should view provider details', async () => {
    await element(by.id('providers-tab')).tap();
    await element(by.id('provider-0')).tap();
    
    await expect(element(by.id('provider-name'))).toBeVisible();
    await expect(element(by.id('provider-score'))).toBeVisible();
    await expect(element(by.id('cigna-status'))).toBeVisible();
  });

  it('should export data', async () => {
    await element(by.id('export-tab')).tap();
    await element(by.id('export-csv-btn')).tap();
    
    await expect(element(by.text('Export complete'))).toBeVisible();
  });
});
```

---

## 5. Performance Testing

### 5.1 API Load Testing

```python
# tests/performance/test_api_load.py

from locust import HttpUser, task, between

class APIUser(HttpUser):
    wait_time = between(1, 3)
    
    @task(3)
    def search_providers(self):
        self.client.post('/api/providers/search', json={
            'state': 'CA',
            'limit': 50
        })
    
    @task(1)
    def get_provider_detail(self):
        self.client.get('/api/providers/1')
    
    @task(1)
    def export_csv(self):
        self.client.post('/api/export/csv')

# Run: locust -f tests/performance/test_api_load.py
# Target: 100 concurrent users, < 200ms p95 response time
```

### 5.2 Scraper Performance

```python
# tests/performance/test_scraper_perf.py

class TestScraperPerformance:
    
    def test_scrape_100_providers(self):
        """Scrape 100 providers within time limit"""
        scraper = HealthgradesScraper()
        
        start = time.time()
        providers = scraper.scrape_providers(limit=100)
        elapsed = time.time() - start
        
        # Should complete in < 5 minutes (with 1s delay)
        assert elapsed < 300
        assert len(providers) == 100
    
    def test_memory_usage(self):
        """Memory usage stays reasonable"""
        import tracemalloc
        
        tracemalloc.start()
        scraper = HealthgradesScraper()
        scraper.scrape_providers(limit=1000)
        
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        # Peak memory < 500MB
        assert peak < 500 * 1024 * 1024
```

---

## 6. Test Data

### 6.1 Fixtures

```
tests/fixtures/
├── provider_profile.html       # Sample Healthgrades page
├── search_results.html         # Sample search results
├── cigna_provider.html         # Sample Cigna page
├── providers.json              # Mock provider data
└── scrape_job.json             # Mock job data
```

### 6.2 Test Database

```python
# conftest.py

@pytest.fixture
def test_db():
    """Create test database"""
    db = create_engine('sqlite:///:memory:')
    create_tables(db)
    yield db
    db.dispose()

@pytest.fixture
def sample_provider():
    """Return sample provider data"""
    return {
        'full_name': 'Dr. Jane Smith, MD',
        'npi': '1234567890',
        'clinic_name': 'Fertility Center',
        'address_line1': '123 Main St',
        'city': 'Los Angeles',
        'state': 'CA',
        'zip_code': '90025',
        'phone': '(310) 555-1234',
        'specialties': ['Reproductive Endocrinology'],
        'healthgrades_score': 4.5,
        'review_count': 42,
        'cigna_in_network': True,
        'cigna_plans': ['PPO', 'HMO']
    }
```

---

## 7. CI/CD Testing

### 7.1 GitHub Actions

```yaml
# .github/workflows/test.yml

name: Tests

on: [push, pull_request]

jobs:
  unit-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt
      - run: pip install -r requirements-test.txt
      - run: pytest tests/unit -v --cov=src --cov-report=xml
      - uses: codecov/codecov-action@v3

  integration-tests:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: test
    steps:
      - uses: actions/checkout@v3
      - run: pip install -r requirements.txt
      - run: pytest tests/integration -v

  e2e-tests:
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v3
      - run: pip install -r requirements.txt
      - run: pytest tests/e2e -v --e2e
```

---

## 8. Test Checklist

### Before Release

- [ ] All unit tests pass (>80% coverage)
- [ ] All integration tests pass
- [ ] E2E tests pass on staging
- [ ] Performance tests meet targets
- [ ] Security scan clean
- [ ] Mobile tests pass on iOS and Android
- [ ] Export formats validated (CSV, Excel)

### Ongoing

- [ ] Daily: Unit tests on CI
- [ ] Weekly: Full integration test
- [ ] Monthly: E2E test against production
- [ ] Quarterly: Performance benchmark

---

*Document Version: 1.0*  
*Last Updated: May 14, 2026*
