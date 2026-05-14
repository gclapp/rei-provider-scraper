# REI Provider Scraper

A standalone web application for scraping Reproductive Endocrinology & Infertility (REI) specialist data from multiple sources.

## Features

- **Healthgrades Integration**: Scrape provider names, locations, clinics, ratings, and reviews
- **Cigna Network Check**: Verify in-network status and covered plans
- **Web Interface**: Clean, responsive UI for searching and viewing results
- **API Endpoint**: JSON API for programmatic access

## Installation

```bash
pip install -r requirements.txt
```

## Usage

### Development
```bash
python app.py
```

### Production
```bash
gunicorn -c gunicorn.conf.py app:app
```

## API

### Search Providers
```bash
POST /api/search
Content-Type: application/json

{
  "state": "CA",
  "sources": ["healthgrades"],
  "network": "cigna"
}
```

## Data Sources

- **Healthgrades**: Provider information, ratings, reviews
- **Cigna**: Insurance network status

## License

Private - For internal use only
