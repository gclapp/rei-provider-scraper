#!/bin/bash

echo "=== REI Provider Scraper Deployment Status ==="
echo ""

echo "1. Docker Container Status:"
docker ps --filter "name=rei-provider-scraper" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
echo ""

echo "2. Application Health (direct):"
curl -s http://localhost:5002/health
echo ""
echo ""

echo "3. Nginx Configuration:"
ls -la /etc/nginx/sites-enabled/rei.openclapp.com 2>/dev/null && echo "✓ Nginx config enabled" || echo "✗ Nginx config not enabled"
echo ""

echo "4. SSL Certificate:"
ls -la /etc/ssl/rei/ 2>/dev/null && echo "✓ Self-signed certificate exists" || echo "✗ Certificate not found"
echo ""

echo "5. DNS Resolution:"
host rei.openclapp.com 2>&1 | grep -q "16.59.79.163" && echo "✓ DNS resolves correctly" || echo "✗ DNS not configured yet"
echo ""

echo "6. Local HTTPS Test (self-signed):"
curl -s -k https://localhost/health -H "Host: rei.openclapp.com" 2>&1 | grep -q "healthy" && echo "✓ HTTPS working (self-signed)" || echo "✗ HTTPS test failed"
echo ""

echo "=== Summary ==="
echo "The application is deployed and running on port 5002"
echo "Nginx is configured to proxy rei.openclapp.com to the app"
echo "Self-signed SSL certificate is in place for immediate HTTPS"
echo ""
echo "Next step: Configure DNS A record for rei.openclapp.com -> 16.59.79.163"
echo "Then: Replace self-signed cert with Let's Encrypt: sudo certbot --nginx -d rei.openclapp.com"
