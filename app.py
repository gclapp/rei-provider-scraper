#!/usr/bin/env python3
"""
REI Provider Scraper - Merged Flask Application
Combines live scraping with database viewing
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
VERSION = "1.1.0"

# Database path
DB_PATH = Path(__file__).parent / "data" / "providers.db"


def get_db_connection():
    """Get database connection."""
    if not DB_PATH.exists():
        return None
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@app.route('/')
def index():
    """REI Provider Scraper - Search Form"""
    return render_template('rei_search.html', version=VERSION)


@app.route('/search', methods=['POST'])
def rei_search():
    """Handle REI search form submission"""
    state = request.form.get('state', '').upper()
    sources = request.form.getlist('sources')
    data_source = request.form.get('data_source', 'database')  # 'database' or 'live'
    
    if not state:
        flash('Please select a state', 'error')
        return redirect(url_for('index'))
    
    if not sources:
        flash('Please select at least one source', 'error')
        return redirect(url_for('index'))
    
    # Build source filter for database query
    source_filter = []
    if 'healthgrades' in sources:
        source_filter.append('healthgrades')
    if 'cigna' in sources:
        source_filter.append('cigna')
    
    try:
        conn = get_db_connection()
        if not conn:
            flash('Database not found.', 'error')
            return redirect(url_for('index'))
        
        # Build query based on selected sources
        if source_filter:
            placeholders = ','.join(['?' for _ in source_filter])
            query = f"""
                SELECT name, credentials, specialties, street, city, state, zip, phone,
                       accepting_new_patients, source, source_url, scraped_at
                FROM providers
                WHERE state = ? AND source IN ({placeholders})
                ORDER BY source, city, name
            """
            params = [state] + source_filter
        else:
            query = """
                SELECT name, credentials, specialties, street, city, state, zip, phone,
                       accepting_new_patients, source, source_url, scraped_at
                FROM providers
                WHERE state = ?
                ORDER BY source, city, name
            """
            params = [state]
        
        cursor = conn.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        # Transform to match the results template format
        providers = []
        for row in rows:
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
                'bio': f"Source: {row['source']}",
                'profile_url': row['source_url'] or '#',
                'expertise': json.loads(row['specialties']) if row['specialties'] else ['REI'],
                'data_source': row['source'],
                'scraped_at': row['scraped_at']
            })
        
        # Store results in session for display
        session['rei_results'] = providers
        session['rei_search_params'] = {
            'state': state,
            'sources': sources,
            'source_filter': source_filter,
            'count': len(providers)
        }
        
        return redirect(url_for('rei_results'))
        
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
    
    if not state:
        return jsonify({'error': 'State is required'}), 400
    
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database not found'}), 404
        
        # Build source filter
        source_filter = []
        if 'healthgrades' in sources:
            source_filter.append('healthgrades')
        if 'cigna' in sources:
            source_filter.append('cigna')
        
        if source_filter:
            placeholders = ','.join(['?' for _ in source_filter])
            query = f"""
                SELECT name, credentials, specialties, street, city, state, zip, phone,
                       accepting_new_patients, source, scraped_at
                FROM providers
                WHERE state = ? AND source IN ({placeholders})
                ORDER BY city, name
            """
            params = [state] + source_filter
        else:
            query = """
                SELECT name, credentials, specialties, street, city, state, zip, phone,
                       accepting_new_patients, source, scraped_at
                FROM providers
                WHERE state = ?
                ORDER BY city, name
            """
            params = [state]
        
        cursor = conn.execute(query, params)
        rows = cursor.fetchall()
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
            'success': True,
            'count': len(providers),
            'providers': providers
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
# Admin/Data Management Endpoints
# ============================================================

@app.route('/admin/stats')
def admin_stats():
    """Get database statistics"""
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Database not found'}), 404
    
    # Total by source
    sources = conn.execute("""
        SELECT source, COUNT(*) as count
        FROM providers
        GROUP BY source
        ORDER BY count DESC
    """).fetchall()
    
    # By state
    states = conn.execute("""
        SELECT state, COUNT(*) as count
        FROM providers
        WHERE state IS NOT NULL AND state != ''
        GROUP BY state
        ORDER BY count DESC
    """).fetchall()
    
    conn.close()
    
    return jsonify({
        'by_source': [{'source': r['source'], 'count': r['count']} for r in sources],
        'by_state': [{'state': r['state'], 'count': r['count']} for r in states],
        'total': sum(r['count'] for r in sources)
    })


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
