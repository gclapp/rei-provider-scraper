# REI Provider Scraper

## Overview

Mobile-first web scraper to collect Reproductive Endocrinology and Infertility (REI) specialist data from Healthgrades and Cigna.

## Data Sources

| Priority | Source | Data |
|----------|--------|------|
| 1 | Healthgrades | Provider names, locations, clinics, ratings |
| 2 | Cigna | In-network providers, plans covered |

## Data Fields

- Provider Name
- Location (Address, City, State, Zip)
- Clinic/Facility Name
- Insurance Plans Accepted
- Healthgrades Score/Rating
- Specialties
- NPI (if available)

## Architecture

```
┌─────────────┐      ┌─────────────┐      ┌─────────────┐
│   Mobile    │─────►│   Scraper   │─────►│   SQLite    │
│   App       │      │   Engine    │      │   DB        │
│  (React     │      │  (Python)   │      │             │
│   Native)   │      │             │      │             │
└─────────────┘      └──────┬──────┘      └─────────────┘
                            │
                   ┌────────┴────────┐
                   │                 │
                   ▼                 ▼
            ┌──────────┐      ┌──────────┐
            │Healthgrades│     │  Cigna   │
            │   API      │      │  Portal  │
            └──────────┘      └──────────┘
```

## Tech Stack

- **Mobile:** React Native (Expo)
- **Backend:** Python + FastAPI
- **Scraping:** Playwright / Scrapy
- **Database:** SQLite (local) + PostgreSQL (cloud)
- **Export:** CSV, JSON, Excel

## Project Status

See [REQUIREMENTS.md](REQUIREMENTS.md) for detailed specifications.

See [TESTING.md](TESTING.md) for testing strategy.

## Quick Start

```bash
# Backend
cd backend
pip install -r requirements.txt
python main.py

# Mobile
cd mobile
npm install
npx expo start
```

## License

Private - PGNY Internal Tool
