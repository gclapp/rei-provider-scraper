# REI Provider Search Tool - Product Requirements Document

**Version:** 2.0  
**Last Updated:** May 18, 2026  
**Status:** In Development (MVP Complete, Enhancement Phase)

---

## 1. Executive Summary

The REI (Reproductive Endocrinology & Infertility) Provider Search Tool is a unified platform for discovering, analyzing, and comparing fertility specialists across multiple data sources. It combines web scraping, API integrations, and intelligent data merging to provide comprehensive provider profiles.

### Current State
- ✅ Healthgrades scraper operational (1,000+ providers in database)
- ✅ Web interface for browsing/filtering providers
- 🚧 Cigna scraper in development
- ⏳ Cigna API integration pending approval
- ⏳ Advanced deduplication and merging algorithms

---

## 2. Goals & Objectives

### Primary Goals
1. **Comprehensive Coverage** - Aggregate provider data from all major fertility directories
2. **Data Quality** - Eliminate duplicates, validate information, maintain freshness
3. **User Experience** - Fast, intuitive search with powerful filtering
4. **Actionable Insights** - Help patients make informed decisions about fertility care

### Success Metrics
| Metric | Target | Current |
|--------|--------|---------|
| Total unique REI providers | 2,000+ | 1,050 |
| Data freshness | < 30 days | 3 days |
| Search response time | < 2 seconds | < 1 second |
| Duplicate rate | < 5% | ~15% |
| Source coverage | 3+ sources | 1 source |

---

## 3. User Personas

### Primary: Fertility Patient (Sarah, 34)
- Recently diagnosed with infertility
- Needs to find specialists in her area
- Wants to compare credentials, reviews, availability
- Values: Insurance acceptance, location, success rates

### Secondary: Healthcare Administrator (Michael, 45)
- Manages fertility clinic network
- Needs market analysis and competitor research
- Values: Comprehensive data exports, trend analysis

### Tertiary: Researcher (Dr. Chen, 38)
- Studying fertility treatment outcomes
- Needs aggregate data for studies
- Values: Data completeness, API access, provenance

---

## 4. Features & Requirements

### 4.1 Data Sources (Priority Order)

| Source | Method | Status | Priority | Notes |
|--------|--------|--------|----------|-------|
| **Healthgrades** | Playwright Scraping | ✅ Active | P1 | 1,050 providers, national coverage |
| **Cigna** | Playwright Scraping | 🚧 Dev | P1 | In-network verification critical |
| **Cigna API** | Official REST API | ⏳ Pending | P1 | Applied, awaiting developer access |
| **ASRM** | Scraping/API | 📋 Planned | P2 | Professional society directory |
| **SART** | Scraping | 📋 Planned | P2 | Clinic success rate data |
| **Yelp/Google** | API | 📋 Backlog | P3 | Patient reviews |

### 4.2 Core Features

#### MVP (Completed)
- [x] Healthgrades scraper with pagination
- [x] SQLite database with standardized schema
- [x] Flask web interface for browsing
- [x] Basic filtering (state, city, name search)
- [x] Provider detail view
- [x] Statistics dashboard

#### Phase 1 (Current Sprint)
- [ ] Cigna scraper completion
- [ ] Cross-source deduplication
- [ ] Provider merging algorithm
- [ ] Insurance network verification
- [ ] Advanced filtering (specialty, accepting patients)

#### Phase 2 (Next Quarter)
- [ ] Cigna API integration
- [ ] Real-time availability checking
- [ ] Patient review aggregation
- [ ] Success rate data from SART
- [ ] API for external integrations

#### Phase 3 (Future)
- [ ] Machine learning for provider matching
- [ ] Predictive outcome modeling
- [ ] Telehealth availability
- [ ] Cost estimation integration

### 4.3 Data Schema

```python
class Provider:
    # Identity
    id: str                          # UUID v4
    name: str                        # Full name
    credentials: List[str]           # MD, PhD, FACOG, etc.
    
    # Specialization
    specialties: List[str]           # REI, OB/GYN, etc.
    subspecialties: List[str]        # Male infertility, PCOS, etc.
    
    # Location
    primary_address: Address
    additional_locations: List[Address]
    
    # Contact
    phone: str
    fax: Optional[str]
    email: Optional[str]
    website: Optional[str]
    
    # Practice
    accepting_new_patients: bool
    languages: List[str]
    hospital_affiliations: List[str]
    
    # Education & Training
    medical_school: Optional[str]
    residency: Optional[str]
    fellowship: Optional[str]
    board_certifications: List[str]
    
    # Insurance
    insurance_networks: List[str]    # Cigna, Aetna, etc.
    
    # Reviews & Ratings
    healthgrades_rating: Optional[float]
    review_count: int
    
    # Metadata
    sources: List[str]               # Where data came from
    source_urls: List[str]           # Original URLs
    first_seen: datetime
    last_updated: datetime
    
class Address:
    street: str
    city: str
    state: str
    zip: str
    latitude: Optional[float]
    longitude: Optional[float]
```

### 4.4 Search & Filter Requirements

**Basic Search:**
- Name (fuzzy matching)
- Location (city, state, ZIP)
- Distance radius from ZIP

**Advanced Filters:**
- Specialty (REI, OB/GYN, Urologist)
- Insurance network
- Accepting new patients
- Languages spoken
- Hospital affiliation
- Board certifications

**Sorting Options:**
- Distance (nearest first)
- Rating (highest first)
- Name (A-Z)
- Last updated (newest first)

---

## 5. Technical Architecture

### 5.1 System Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                      Web Interface                          │
│  (Flask + HTML/Templates → Future: React/Vue SPA)          │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    API Gateway (Future)                     │
│              Rate limiting, authentication                  │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌──────────────┐    ┌─────────────────┐    ┌──────────────┐
│   Search     │    │  Data Processor │    │   Export     │
│   Engine     │    │  (Merge/Dedupe) │    │   Service    │
└──────────────┘    └─────────────────┘    └──────────────┘
        │                     │                     │
        └─────────────────────┼─────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              Data Layer (SQLite → Future: PostgreSQL)      │
│                    Redis (caching layer)                    │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌──────────────┐    ┌─────────────────┐    ┌──────────────┐
│  Healthgrades│    │  Cigna Scraper  │    │   Cigna API  │
│   Scraper    │    │   (Playwright)  │    │  (REST API)  │
└──────────────┘    └─────────────────┘    └──────────────┘
```

### 5.2 Technology Stack

| Component | Current | Future |
|-----------|---------|--------|
| Backend | Flask | FastAPI |
| Database | SQLite | PostgreSQL |
| Caching | None | Redis |
| Scraping | Playwright | Playwright + Thunderbit |
| Search | SQL LIKE | Elasticsearch |
| Frontend | Jinja2 Templates | React SPA |
| Deployment | Docker | Kubernetes |

### 5.3 Scraping Infrastructure

**Rate Limiting:**
- Healthgrades: 1 request/second
- Cigna: 20 requests/minute
- Retry with exponential backoff
- Rotate user agents

**Session Management:**
- Persistent cookies for authenticated sources
- Automatic re-authentication
- Session state encryption

**Monitoring:**
- Success/failure rates per source
- Response time tracking
- Data quality alerts

---

## 6. Data Quality & Deduplication

### 6.1 Deduplication Strategy

**Primary Key Generation:**
```python
def generate_provider_key(provider):
    """Generate unique key for deduplication."""
    # Normalize name
    name = normalize_name(provider.name)
    
    # Use NPI if available (most reliable)
    if provider.npi:
        return f"npi:{provider.npi}"
    
    # Fallback to name + location hash
    location_hash = hash(f"{provider.city}{provider.state}")
    return f"name_loc:{name}:{location_hash}"
```

**Matching Algorithm (v1):**
1. Exact NPI match → Same provider
2. Name similarity > 90% + Same city → Likely same
3. Name similarity > 80% + Same state + Same specialty → Possible match
4. Manual review queue for uncertain matches

**Field Merging Rules:**
- Name: Longest version (includes middle initial)
- Address: Most complete (includes suite/floor)
- Phone: Format consistently, prefer source with area code
- Insurance: Union of all sources
- Ratings: Weighted average by review count

### 6.2 Data Validation

**Required Fields:**
- Name (non-empty)
- State (valid 2-letter code)
- At least one source URL

**Validation Rules:**
- Phone: E.164 format
- ZIP: Valid USPS ZIP
- State: Standardized to 2-letter code
- Names: Title case, no credentials in name field

---

## 7. User Interface

### 7.1 Current Interface (MVP)

**Pages:**
1. **Home/Search** - Main search interface
2. **Results** - Paginated provider list
3. **Provider Detail** - Full profile view
4. **Statistics** - Data quality dashboard

**Components:**
- Search bar with autocomplete
- Filter sidebar
- Provider cards with key info
- Map view (future)

### 7.2 Future Enhancements

**Patient-Facing Features:**
- Save/compare providers
- Appointment request integration
- Insurance verification widget
- Review submission

**Admin Features:**
- Data quality dashboard
- Source health monitoring
- Manual provider editing
- Export tools (CSV, JSON, API)

---

## 8. Security & Compliance

### 8.1 Data Protection

**PII Handling:**
- No patient data stored
- Provider contact info is public business data
- Encrypt credentials at rest (600 permissions)
- No PHI (Protected Health Information)

**Compliance:**
- robots.txt compliance for all sources
- Rate limiting to avoid being blocked
- Terms of service adherence
- No scraping of password-protected areas

### 8.2 Access Control

**Current:** Public read-only access
**Future:**
- API key authentication
- Role-based access (admin, researcher, public)
- Audit logging

---

## 9. Deployment & Operations

### 9.1 Current Deployment

**Server:** AWS EC2 (16.59.79.163)
**Container:** Docker
**Database:** SQLite (file-based)
**Process:**
```bash
cd /tmp/rei-provider-scraper
git pull origin main
docker build -t rei-provider-scraper:latest .
docker stop rei-provider-scraper 2>/dev/null
docker rm rei-provider-scraper 2>/dev/null
docker run -d \
  --name rei-provider-scraper \
  --restart unless-stopped \
  -p 127.0.0.1:5002:5000 \
  -v /home/ubuntu/.openclaw/workspace/projects/provider-directory/data:/app/data \
  rei-provider-scraper:latest
```

### 9.2 Monitoring

**Health Checks:**
- HTTP endpoint: `/health`
- Database connectivity
- Disk space
- Memory usage

**Alerts:**
- Scraper failure (3 consecutive)
- Database corruption
- Disk space > 80%
- Memory usage > 90%

### 9.3 Backup Strategy

**Database:**
- Daily automated backups
- 30-day retention
- Offsite replication (future)

**Code:**
- GitHub repository
- Tagged releases
- Rollback capability

---

## 10. Roadmap

### Q2 2026 (Current)
- [ ] Complete Cigna scraper
- [ ] Implement deduplication
- [ ] Add insurance filter
- [ ] Improve search performance

### Q3 2026
- [ ] Cigna API integration
- [ ] PostgreSQL migration
- [ ] Redis caching layer
- [ ] API v1 release

### Q4 2026
- [ ] React frontend
- [ ] Real-time availability
- [ ] Patient reviews
- [ ] Mobile app (future consideration)

---

## 11. Open Questions

1. **Cigna API:** Timeline for developer portal approval?
2. **Data Licensing:** Any restrictions on commercial use of scraped data?
3. **Scale:** Expected query volume? (affects caching strategy)
4. **Monetization:** Free public tool vs. premium API access?
5. **Partnerships:** Integration with fertility clinics or patient platforms?

---

## 12. Appendix

### A. Database Schema (SQL)

```sql
CREATE TABLE providers (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    credentials TEXT,
    specialties TEXT,  -- JSON array
    street TEXT,
    city TEXT,
    state TEXT,
    zip TEXT,
    phone TEXT,
    accepting_new_patients BOOLEAN,
    scraped_at TIMESTAMP,
    source TEXT,
    source_url TEXT
);

CREATE INDEX idx_state ON providers(state);
CREATE INDEX idx_city ON providers(city);
CREATE INDEX idx_name ON providers(name);
CREATE INDEX idx_source ON providers(source);
```

### B. API Endpoints (Future)

```
GET /api/providers              # List with filters
GET /api/providers/{id}         # Detail view
GET /api/providers/search       # Full-text search
GET /api/states                 # State list with counts
GET /api/stats                  # Database statistics
POST /api/providers/{id}/flag   # Report inaccurate data
```

### C. Environment Variables

```bash
# Database
DATABASE_PATH=/app/data/providers.db

# Scraping
HEALTHGRADES_RATE_LIMIT=1
CIGNA_RATE_LIMIT=20
CIGNA_USERNAME=
CIGNA_PASSWORD=

# Security
SECRET_KEY=
API_KEY_SALT=

# Monitoring
SENTRY_DSN=
LOG_LEVEL=INFO
```

---

**Document Owner:** Cicero  
**Review Cycle:** Monthly  
**Next Review:** June 18, 2026
