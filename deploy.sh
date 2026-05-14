#!/bin/bash
set -e

echo "=== REI Provider Scraper Deployment Script ==="
echo ""

# Configuration
DOMAIN="rei.openclapp.com"
EMAIL="geoff.clapp@gmail.com"

# Check if running as root for certbot
if [ "$EUID" -ne 0 ]; then 
   echo "Please run as root or with sudo for SSL certificate generation"
   exit 1
fi

# Create necessary directories
mkdir -p certbot/conf certbot/www

# Stop any existing containers
docker-compose -f docker-compose.prod.yml down 2>/dev/null || true

# Build and start without SSL first for certbot challenge
echo "Starting services for initial setup..."
docker-compose -f docker-compose.prod.yml up -d rei-scraper

# Wait for app to be ready
echo "Waiting for application to start..."
sleep 5

# Start nginx without SSL for certbot
cat > nginx.conf << 'NGINXEOF'
server {
    listen 80;
    server_name rei.openclapp.com;
    
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }
    
    location / {
        proxy_pass http://rei-scraper:5000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
NGINXEOF

docker-compose -f docker-compose.prod.yml up -d nginx

# Obtain SSL certificate
echo "Obtaining SSL certificate for $DOMAIN..."
docker-compose -f docker-compose.prod.yml run --rm certbot certonly \
    --webroot \
    --webroot-path=/var/www/certbot \
    --email $EMAIL \
    --agree-tos \
    --no-eff-email \
    -d $DOMAIN

# Update nginx config with SSL
cat > nginx.conf << 'NGINXEOF'
server {
    listen 80;
    server_name rei.openclapp.com;
    
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }
    
    location / {
        return 301 https://$host$request_uri;
    }
}

server {
    listen 443 ssl http2;
    server_name rei.openclapp.com;
    
    ssl_certificate /etc/letsencrypt/live/rei.openclapp.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/rei.openclapp.com/privkey.pem;
    
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    
    location / {
        proxy_pass http://rei-scraper:5000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
    }
}
NGINXEOF

# Reload nginx
docker-compose -f docker-compose.prod.yml exec nginx nginx -s reload

# Start certbot auto-renewal
docker-compose -f docker-compose.prod.yml up -d certbot

echo ""
echo "=== Deployment Complete ==="
echo "Application is available at: https://$DOMAIN"
echo "Health check: https://$DOMAIN/health"
echo ""
echo "To view logs: docker-compose -f docker-compose.prod.yml logs -f"
