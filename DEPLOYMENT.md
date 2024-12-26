# SocialPulse Deployment Guide

## Prerequisites
- A domain configured on Cloudflare
- PostgreSQL database
- Node.js 18+ and Python 3.11+

## 1. Domain Configuration on Cloudflare

1. Log in to your Cloudflare dashboard
2. Add your domain and configure DNS settings:
   - Add an A record pointing to your server's IP
   - Enable Cloudflare proxy (orange cloud)
   - Enable SSL/TLS encryption (Full mode recommended)

## 2. Environment Variables Setup

Copy `.env.production` to `.env` and configure:

```bash
# Server Configuration
PORT=5000
FLASK_ENV=production
FLASK_APP=app.py
APP_URL=https://yourdomain.com  # Replace with your domain

# Security
SECRET_KEY=<generate-a-secure-key>
ALLOWED_ORIGINS=https://yourdomain.com,https://*.yourdomain.com

# Database Configuration
DATABASE_URL=postgresql://user:password@host:port/dbname

# OpenAI API Key
OPENAI_API_KEY=<your-openai-api-key>

# Social Media API Keys
TWITTER_CLIENT_ID=<your-twitter-client-id>
TWITTER_CLIENT_SECRET=<your-twitter-client-secret>
INSTAGRAM_CLIENT_ID=<your-instagram-client-id>
INSTAGRAM_CLIENT_SECRET=<your-instagram-client-secret>
FACEBOOK_CLIENT_ID=<your-facebook-client-id>
FACEBOOK_CLIENT_SECRET=<your-facebook-client-secret>
TIKTOK_CLIENT_ID=<your-tiktok-client-id>
TIKTOK_CLIENT_SECRET=<your-tiktok-client-secret>
YOUTUBE_CLIENT_ID=<your-youtube-client-id>
YOUTUBE_CLIENT_SECRET=<your-youtube-client-secret>
SNAPCHAT_CLIENT_ID=<your-snapchat-client-id>
SNAPCHAT_CLIENT_SECRET=<your-snapchat-client-secret>
PINTEREST_CLIENT_ID=<your-pinterest-client-id>
PINTEREST_CLIENT_SECRET=<your-pinterest-client-secret>
```

## 3. Database Setup

1. Create a PostgreSQL database
2. Run database migrations:
```bash
flask db upgrade
```

## 4. Build Process

1. Install dependencies:
```bash
npm install
pip install -r requirements.txt
```

2. Build the frontend:
```bash
npm run build
```

3. Start the production server:
```bash
python app.py
```

The application uses Waitress as the production WSGI server and will be available on port 5000.

## 5. Nginx Configuration (Optional)

If using Nginx as a reverse proxy:

```nginx
server {
    listen 80;
    server_name yourdomain.com;
    
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## 6. Security Considerations

1. Enable Cloudflare security features:
   - Web Application Firewall (WAF)
   - DDoS protection
   - Rate limiting

2. SSL/TLS Configuration:
   - Enable Full (strict) SSL/TLS encryption
   - Enable HSTS
   - Configure minimum TLS version to 1.2

3. Database Security:
   - Use strong passwords
   - Enable SSL for database connections
   - Restrict database access to application IP

## 7. Monitoring and Maintenance

1. Set up Cloudflare analytics
2. Configure error logging
3. Set up database backups
4. Monitor server resources

## Troubleshooting

1. Check application logs in `/var/log/socialpulse/`
2. Verify database connectivity
3. Check Cloudflare SSL/TLS settings
4. Verify environment variables

For additional support, refer to the documentation or contact support.
