# REI Provider Scraper - Requirements Document

## 1. Project Overview

### Purpose
Build a mobile application that scrapes and aggregates Reproductive Endocrinology and Infertility (REI) specialist data from Healthgrades and Cigna to identify in-network providers for PGNY patients.

### Success Criteria
- [ ] Scrape 1000+ REI providers from Healthgrades
- [ ] Match providers with Cigna in-network status
- [ ] Export clean data with all required fields
- [ ] Mobile app for field data collection

---

## 2. Data Requirements

### 2.1 Provider Data Fields

| Field | Source | Required | Notes |
|-------|--------|----------|-------|
| Full Name | Healthgrades | ✅ | First + Last |
| NPI Number | Healthgrades | ⚠️ | If available |
| Clinic Name | Healthgrades | ✅ | Practice/facility |
| Address | Healthgrades | ✅ | Street, City, State, ZIP |
| Phone | Healthgrades | ✅ | Primary contact |
| Specialties | Healthgrades | ✅ | REI, fertility, etc. |
| Healthgrades Score | Healthgrades | ✅ | 1-5 rating |
| Review Count | Healthgrades | ⚠️ | Number of reviews |
| Years in Practice | Healthgrades | ⚠️ | Experience |
| Education | Healthgrades | ❌ | Nice to have |
| Cigna In-Network | Cigna | ✅ | Yes/No/Unknown |
| Cigna Plans | Cigna | ✅ | List of plans |
| Last Updated | System | ✅ | Timestamp |

### 2.2 Data Quality

- Deduplication by NPI or Name + Address
- Address standardization (USPS format)
- Phone number formatting
- State abbreviation standardization

---

## 3. Functional Requirements

### 3.1 Scraping Engine

#### Healthgrades Scraper
```
Input:  State list, specialty filter (REI)
Process:
  1. Search Healthgrades for "Reproductive Endocrinology" in state
  2. Paginate through results
  3. Visit each provider profile
  4. Extract all data fields
  5. Store in database
Output: Provider records with Healthgrades data
```

#### Cigna Scraper
```
Input:  Provider list from Healthgrades
Process:
  1. Search Cigna provider directory
  2. Match by name + location
  3. Extract in-network status
  4. Extract covered plans
  5. Update provider records
Output: Provider records with insurance data
```

### 3.2 Mobile App

#### Screens

| Screen | Purpose |
|--------|---------|
| Dashboard | Overview stats, last scrape |
| Search | Find providers by name/location |
| Provider Detail | Full provider info |
| Scrape Control | Start/pause scraping jobs |
| Export | Download data (CSV/Excel) |
| Settings | Config, credentials |

#### Features
- [ ] Real-time scrape progress
- [ ] Offline data access
- [ ] Manual provider entry
- [ ] Photo capture (clinic exterior)
- [ ] Notes/annotations
- [ ] Export to email/Slack

### 3.3 API Endpoints

```
GET  /api/providers          # List all providers
GET  /api/providers/:id      # Get provider detail
POST /api/providers/search   # Search providers
POST /api/scrape/start       # Start scraping job
GET  /api/scrape/status      # Get scrape progress
POST /api/export/csv         # Export to CSV
POST /api/export/excel       # Export to Excel
```

---

## 4. Non-Functional Requirements

### 4.1 Performance

- Scrape rate: 1 provider/second (with politeness delay)
- Mobile app load time: < 2 seconds
- Search response: < 500ms
- Export 1000 records: < 10 seconds

### 4.2 Reliability

- Resume interrupted scrapes
- Retry failed requests (3x)
- Handle CAPTCHA (manual solve)
- Data validation before storage

### 4.3 Security

- API key authentication
- No PHI storage
- Encrypted local database
- Secure credential storage

### 4.4 Compliance

- Respect robots.txt
- Rate limiting (don't hammer sites)
- Terms of Service compliance
- No scraping of patient data

---

## 5. Technical Requirements

### 5.1 Backend

```python
# Core stack
Python 3.11+
FastAPI
SQLAlchemy
Playwright (for JS sites)
Scrapy (for structured sites)
Celery (for background jobs)
Redis (for queue)
```

### 5.2 Mobile

```javascript
// Core stack
React Native (Expo)
TypeScript
React Navigation
AsyncStorage (local cache)
Axios (API calls)
```

### 5.3 Database Schema

```sql
-- providers table
CREATE TABLE providers (
    id INTEGER PRIMARY KEY,
    full_name TEXT NOT NULL,
    npi TEXT UNIQUE,
    clinic_name TEXT,
    address_line1 TEXT,
    address_line2 TEXT,
    city TEXT,
    state TEXT,
    zip_code TEXT,
    phone TEXT,
    specialties TEXT, -- JSON array
    healthgrades_score REAL,
    review_count INTEGER,
    years_in_practice INTEGER,
    cigna_in_network BOOLEAN,
    cigna_plans TEXT, -- JSON array
    healthgrades_url TEXT,
    last_updated TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- scrape_jobs table
CREATE TABLE scrape_jobs (
    id INTEGER PRIMARY KEY,
    source TEXT, -- 'healthgrades', 'cigna'
    status TEXT, -- 'running', 'completed', 'failed'
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    providers_found INTEGER,
    providers_scraped INTEGER,
    errors TEXT -- JSON array
);
```

---

## 6. User Stories

### As a PGNY network manager...
- [ ] I want to find all REI providers in California
- [ ] I want to see which providers are Cigna in-network
- [ ] I want to export a list for our sales team
- [ ] I want to update provider data quarterly

### As a field sales rep...
- [ ] I want to look up providers while visiting clinics
- [ ] I want to add notes about clinic quality
- [ ] I want to share provider info with patients

### As a data analyst...
- [ ] I want to analyze provider density by state
- [ ] I want to compare Healthgrades scores vs Cigna coverage
- [ ] I want clean data for reporting

---

## 7. Milestones

### Phase 1: Foundation (Week 1-2)
- [ ] Set up GitHub repo
- [ ] Create database schema
- [ ] Build Healthgrades scraper (basic)
- [ ] Store data locally

### Phase 2: Backend (Week 3-4)
- [ ] FastAPI server
- [ ] Scrape job queue
- [ ] Data validation
- [ ] Export functionality

### Phase 3: Mobile (Week 5-6)
- [ ] React Native app
- [ ] Provider search
- [ ] Scrape control UI
- [ ] Export to device

### Phase 4: Integration (Week 7-8)
- [ ] Cigna scraper
- [ ] Provider matching
- [ ] Mobile-backend sync
- [ ] Testing & refinement

---

## 8. Open Questions

1. Does Cigna have a public API or require scraping?
2. What's the expected total provider count?
3. Do we need real-time updates or batch?
4. Should we store historical data (score changes)?
5. Any other insurance providers to add later?

---

*Document Version: 1.0*  
*Last Updated: May 14, 2026*  
*Owner: Geoffrey Clapp / PGNY*
