# Social Media Management Platform

A comprehensive AI-powered social media management platform designed to empower digital creators with intelligent content creation, multilingual support, and cross-platform optimization tools.

## Features

- Content generation and repurposing across platforms
- A/B testing suggestions
- Performance prediction
- Multilingual support
- Analytics and tracking
- Cross-platform posting

## Production Deployment Instructions

1. Build the frontend:
```bash
npm run build
```

2. Set up environment variables:
- Copy `.env.production` to `.env`
- Update the variables with your production values
- Ensure all required API keys are set

3. Install production dependencies:
```bash
pip install -r requirements.txt
```

4. Initialize the database:
```bash
flask db upgrade
```

5. Start the production server:
```bash
python app.py
```

The application will be available on the configured port (default: 5000).

## Security Considerations

- Always use HTTPS in production
- Set proper CORS origins in ALLOWED_ORIGINS
- Keep API keys secure
- Regularly update dependencies
- Monitor logs for suspicious activities

## Environment Variables

Required environment variables:
- DATABASE_URL: PostgreSQL database URL
- OPENAI_API_KEY: OpenAI API key for AI features
- SECRET_KEY: Flask session secret key
- ALLOWED_ORIGINS: Comma-separated list of allowed CORS origins

## Maintenance

- Regular database backups
- Monitor server resources
- Keep dependencies updated
- Check error logs regularly

## License

MIT License. See LICENSE file for details.
