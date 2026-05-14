#!/usr/bin/env python3
"""
REI Provider Scraper - Flask Application
"""

from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import json
import os
from pathlib import Path

from scraper import REIScraper, Provider

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', os.urandom(24))

# Version info
VERSION = "1.0.0"

@app.route('/')
def index():
    """Home page - redirect to search"""
    return redirect(url_for('rei_search'))

@app.route('/rei')
def rei_index():
    """REI Provider Scraper - Search Form"""
    return render_template('rei_search.html', version=VERSION)

@app.route('/rei/search', methods=['POST'])
def rei_search():
    """Handle REI search form submission"""
    state = request.form.get('state', '').upper()
    sources = request.form.getlist('sources')
    network = request.form.get('network')
    
    if not state:
        flash('Please select a state', 'error')
        return redirect(url_for('rei_index'))
    
    if not sources:
        flash('Please select at least one source', 'error')
        return redirect(url_for('rei_index'))
    
    # Perform scrape
    try:
        scraper = REIScraper()
        providers = scraper.scrape(state, sources=sources, network=network)
        
        # Store results in session for display
        session['rei_results'] = [p.to_dict() for p in providers]
        session['rei_search_params'] = {
            'state': state,
            'sources': sources,
            'network': network
        }
        
        return redirect(url_for('rei_results'))
        
    except Exception as e:
        flash(f'Error during search: {str(e)}', 'error')
        return redirect(url_for('rei_index'))

@app.route('/rei/results')
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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
