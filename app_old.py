#!/usr/bin/env python3
"""
REI Provider Scraper - Flask Application
"""

from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import json
import os
import sqlite3
from pathlib import Path

from scraper import REIScraper, Provider

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', os.urandom(24))

# Version info
VERSION = "1.0.0"

# Database path for Healthgrades data
DB_PATH = Path('/home/ubuntu/.openclaw/workspace/projects/provider-directory/data/providers.db')

@app.route('/')
def index():
    """REI Provider Scraper - Search Form"""
    return render_template('rei_search.html', version=VERSION)

@app.route('/search', methods=['POST'])
def rei_search():
    """Handle REI search form submission - query Healthgrades database"""
    state = request.form.get('state', '').upper()
    sources = request.form.getlist('sources')
    
    if not state:
        flash('Please select a state', 'error')
        return redirect(url_for('index'))
    
    if not sources:
        flash('Please select at least one source', 'error')
        return redirect(url_for('index'))
    
    # Query Healthgrades database for providers in this state
    try:
        conn = get_db_connection()
        if conn:
            cursor = conn.execute("""
                SELECT name, credentials, specialties, street, city, state, zip, phone,
                       accepting_new_patients, source, scraped_at
                FROM providers
                WHERE source = 'healthgrades' AND state = ?
                ORDER BY city, name
            """, (state,))
            
            rows = cursor.fetchall()
            conn.close()
            
            # Transform to match the results template format
            providers = []
            for row in rows:
                # Parse name into first/last
                name_parts = row['name'].replace('Dr. ', '').replace(', MD', '').replace(', DO', '').split(' ')
                first_name = name_parts[0] if len(name_parts) > 0 else ''
                last_name = name_parts[-1] if len(name_parts) > 1 else ''
                
                providers.append({
                    'first_name': first_name,
                    'last_name': last_name,
                    'full_name': row['name'],
                    'title': row['credentials'] or 'MD',
                    'photo_url': None,
                    'healthgrades_rating': None,
                    'review_count': None,
                    'office_location': row['street'],
                    'city': row['city'],
                    'state': row['state'],
                    'zip_code': row['zip'],
                    'phone': row['phone'],
                    'bio': None,
                    'profile_url': f"https://www.healthgrades.com/usearch?what=Reproductive%20Endocrinology%20%26%20Infertility&entityCode=PS310&searchType=PracticingSpecialty&payors=HPY00006F7&distances=National",
                    'expertise': json.loads(row['specialties']) if row['specialties'] else ['REI'],
                    'source': row['source']
                })
            
            # Store results in session for display
            session['rei_results'] = providers
            session['rei_search_params'] = {
                'state': state,
                'sources': sources,
                'network': 'Cigna In-Network'
            }
            
            return redirect(url_for('rei_results'))
        else:
            flash('Database not found. Please run the scraper first.', 'error')
            return redirect(url_for('index'))
        
    except Exception as e:
        flash(f'Error during search: {str(e)}', 'error')
        return redirect(url_for('index'))

@app.route('/results')
def rei_results():
    """Display REI search results"""
    providers = session.get('rei_results', [])
    search_params = session.get('rei_search_params', {})
    
    return render_template('rei_results.html', 
                         providers=providers,
                         search_params=search_params,
                         count=len(providers),
                         version=VERSION)

@app.route('/api/search', methods=['POST'])
def api_search():
    """API endpoint for REI search"""
    data = request.get_json()
    state = data.get('state', '').upper()
    sources = data.get('sources', ['healthgrades'])
    network = data.get('network')
    
    if not state:
        return jsonify({'error': 'State is required'}), 400
    
    try:
        scraper = REIScraper()
        providers = scraper.scrape(state, sources=sources, network=network)
        
        return jsonify({
            'success': True,
            'count': len(providers),
            'providers': [p.to_dict() for p in providers]
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'version': VERSION,
        'service': 'rei-provider-scraper'
    })


# ============================================================
# Healthgrades Data Viewer Endpoints
# ============================================================

def get_db_connection():
    """Get database connection for Healthgrades data."""
    if not DB_PATH.exists():
        return None
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@app.route('/healthgrades')
def healthgrades_viewer():
    """View all scraped Healthgrades REI providers with Cigna insurance."""
    conn = get_db_connection()
    if not conn:
        flash('Database not found. Please run the scraper first.', 'error')
        return redirect(url_for('index'))
    
    # Get filter parameters
    state = request.args.get('state', '')
    city = request.args.get('city', '')
    search = request.args.get('search', '')
    page = request.args.get('page', 1, type=int)
    per_page = 50
    
    # Build query
    where_clauses = ["source = 'healthgrades'"]
    params = []
    
    if state:
        where_clauses.append("state = ?")
        params.append(state)
    if city:
        where_clauses.append("city LIKE ?")
        params.append(f"%{city}%")
    if search:
        where_clauses.append("name LIKE ?")
        params.append(f"%{search}%")
    
    where_sql = " AND ".join(where_clauses)
    
    # Get total count
    count_sql = f"SELECT COUNT(*) FROM providers WHERE {where_sql}"
    total = conn.execute(count_sql, params).fetchone()[0]
    
    # Get providers for current page
    offset = (page - 1) * per_page
    query = f"""
        SELECT name, credentials, specialties, street, city, state, zip, phone,
               accepting_new_patients, source, scraped_at
        FROM providers
        WHERE {where_sql}
        ORDER BY state, city, name
        LIMIT ? OFFSET ?
    """
    params.extend([per_page, offset])
    
    rows = conn.execute(query, params).fetchall()
    conn.close()
    
    providers = []
    for row in rows:
        providers.append({
            'name': row['name'],
            'credentials': row['credentials'],
            'specialties': json.loads(row['specialties']) if row['specialties'] else [],
            'street': row['street'],
            'city': row['city'],
            'state': row['state'],
            'zip': row['zip'],
            'phone': row['phone'],
            'accepting_new_patients': row['accepting_new_patients'],
            'source': row['source'],
            'scraped_at': row['scraped_at']
        })
    
    total_pages = (total + per_page - 1) // per_page
    
    return render_template('healthgrades_viewer.html',
                         providers=providers,
                         total=total,
                         page=page,
                         total_pages=total_pages,
                         state=state,
                         city=city,
                         search=search,
                         version=VERSION)


@app.route('/api/healthgrades/stats')
def healthgrades_stats():
    """Get statistics about Healthgrades data."""
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database not found'}), 404
    
    # Total providers
    total = conn.execute(
        "SELECT COUNT(*) FROM providers WHERE source = 'healthgrades'"
    ).fetchone()[0]
    
    # Providers by state
    states = conn.execute("""
        SELECT state, COUNT(*) as count
        FROM providers
        WHERE source = 'healthgrades' AND state IS NOT NULL AND state != ''
        GROUP BY state
        ORDER BY count DESC
    """).fetchall()
    
    # Providers by source (to show multiple sources when added)
    sources = conn.execute("""
        SELECT source, COUNT(*) as count
        FROM providers
        GROUP BY source
        ORDER BY count DESC
    """).fetchall()
    
    conn.close()
    
    return jsonify({
        'total_healthgrades': total,
        'states': [{'state': r['state'], 'count': r['count']} for r in states],
        'by_source': [{'source': r['source'], 'count': r['count']} for r in sources]
    })


@app.route('/api/healthgrades/providers')
def api_healthgrades_providers():
    """API endpoint to get Healthgrades providers with filtering."""
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database not found'}), 404
    
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    state = request.args.get('state', '')
    search = request.args.get('search', '')
    
    where_clauses = ["source = 'healthgrades'"]
    params = []
    
    if state:
        where_clauses.append("state = ?")
        params.append(state)
    if search:
        where_clauses.append("name LIKE ?")
        params.append(f"%{search}%")
    
    where_sql = " AND ".join(where_clauses)
    
    # Get total
    count_sql = f"SELECT COUNT(*) FROM providers WHERE {where_sql}"
    total = conn.execute(count_sql, params).fetchone()[0]
    
    # Get providers
    offset = (page - 1) * per_page
    query = f"""
        SELECT name, credentials, specialties, street, city, state, zip, phone,
               accepting_new_patients, source, scraped_at
        FROM providers
        WHERE {where_sql}
        ORDER BY state, city, name
        LIMIT ? OFFSET ?
    """
    params.extend([per_page, offset])
    
    rows = conn.execute(query, params).fetchall()
    conn.close()
    
    providers = []
    for row in rows:
        providers.append({
            'name': row['name'],
            'credentials': row['credentials'],
            'specialties': json.loads(row['specialties']) if row['specialties'] else [],
            'street': row['street'],
            'city': row['city'],
            'state': row['state'],
            'zip': row['zip'],
            'phone': row['phone'],
            'accepting_new_patients': row['accepting_new_patients'],
            'source': row['source'],
            'scraped_at': row['scraped_at']
        })
    
    return jsonify({
        'providers': providers,
        'total': total,
        'page': page,
        'per_page': per_page,
        'pages': (total + per_page - 1) // per_page
    })


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
