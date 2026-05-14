# REI Provider Scraper - Deployment Guide

## Deployment Status: ✅ READY (Pending DNS)

The REI Provider Scraper has been deployed to the server at **16.59.79.163** and is ready to serve traffic at **https://rei.openclapp.com**.

---

## What's Been Deployed

### 1. Docker Container
- **Image**: `rei-provider-scraper:latest`
- **Container Name**: `rei-provider-scraper`
- **Internal Port**: 5000
- **External Port**: 127.0.0.1:5002
- **Status**: Running and healthy

### 2. Nginx Reverse Proxy
- **Config**: `/etc/nginx/sites-available/rei.openclapp.com`
- **HTTP**: Redirects to HTTPS
- **HTTPS**: Serves on port 443 with SSL
- **Proxy**: Forwards to localhost:5002

### 3. SSL Certificate
- **Type**: Self-signed (temporary)
- **Location**: `/etc/ssl/rei/`
- **Ready for**: Let's Encrypt replacement once DNS is configured

### 4. Application Files
- Flask app with Gunicorn WSGI server
- HTML templates for search and results pages
- Health check endpoint at `/health`

---

## DNS Configuration Required

To make the site accessible, add this DNS A record in GoDaddy:

| Type | Name | Value | TTL |
|------|------|-------|-----|
| A | rei | 16.59.79.163 | 600 |

### Verification Steps

1. **Check DNS propagation**:
   ```bash
   dig rei.openclapp.com
   ```

2. **Test HTTP access**:
   ```bash
   curl http://rei.openclapp.com/health
   ```

3. **Test HTTPS access** (will show cert warning until Let's Encrypt is set up):
   ```bash
   curl -k https://rei.openclapp.com/health
   ```

---

## SSL Certificate Setup (After DNS)

Once DNS resolves, obtain a proper SSL certificate:

```bash
sudo certbot --nginx -d rei.openclapp.com
```

This will:
- Obtain a certificate from Let's Encrypt
- Update nginx configuration automatically
- Set up auto-renewal

---

## Management Commands

### Check Status
```bash
bash /tmp/rei-provider-scraper/check-deployment.sh
```

### View Logs
```bash
# Application logs
docker logs -f rei-provider-scraper

# Nginx logs
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

### Restart Services
```bash
# Restart app container
docker restart rei-provider-scraper

# Restart nginx
sudo systemctl restart nginx
```

### Update Application
```bash
cd /tmp/rei-provider-scraper
git pull
docker build -t rei-provider-scraper:latest .
docker restart rei-provider-scraper
```

---

## Endpoints

| Endpoint | Description |
|----------|-------------|
| `https://rei.openclapp.com/` | Main search page |
| `https://rei.openclapp.com/health` | Health check (JSON) |
| `https://rei.openclapp.com/api/search` | API endpoint (POST) |

---

## Troubleshooting

### DNS not resolving
- Wait 5-30 minutes after adding DNS record
- Check with: `dig rei.openclapp.com`

### Certificate errors
- Expected with self-signed cert
- Accept the warning in browser, or
- Run certbot after DNS resolves

### Container not starting
```bash
docker logs rei-provider-scraper
docker ps -a
```

### Nginx errors
```bash
sudo nginx -t
sudo systemctl status nginx
```

---

## Files Added to Repository

- `Dockerfile` - Container build instructions
- `docker-compose.yml` - Local development
- `docker-compose.prod.yml` - Production deployment
- `nginx.conf` - Nginx configuration template
- `deploy.sh` - Full deployment script
- `check-deployment.sh` - Status check script
- `setup-dns.sh` - DNS setup instructions
- `templates/rei_search.html` - Search form
- `templates/rei_results.html` - Results page

---

## Current Status

✅ Docker container running  
✅ Nginx configured  
✅ Self-signed SSL certificate  
✅ Application responding on port 5002  
✅ Health check working  
⏳ **Waiting for DNS A record**  
⏳ **Waiting for Let's Encrypt SSL**  
