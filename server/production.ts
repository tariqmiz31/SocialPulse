import { app } from "./index";
import { log } from "./vite";
import dotenv from "dotenv";
import helmet from "helmet";
import cors from "cors";
import rateLimit from "express-rate-limit";
import compression from "compression";

dotenv.config();

const PORT = parseInt(process.env.PORT || "5000", 10);
const HOST = "0.0.0.0";
const CUSTOM_DOMAIN = process.env.CUSTOM_DOMAIN || "silvariumsocial.com";

// Enable security middleware
app.use(helmet({
  contentSecurityPolicy: {
    directives: {
      defaultSrc: ["'self'"],
      connectSrc: ["'self'", `https://${CUSTOM_DOMAIN}`, `wss://*.${CUSTOM_DOMAIN}`],
      imgSrc: ["'self'", "data:", "blob:", `https://*.${CUSTOM_DOMAIN}`],
      scriptSrc: ["'self'", "'unsafe-inline'"],
      styleSrc: ["'self'", "'unsafe-inline'"],
      frameSrc: ["'self'"],
      objectSrc: ["'none'"],
      upgradeInsecureRequests: []
    }
  }
}));

// Enable compression
app.use(compression());

// Rate limiting
const limiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 minutes
  max: 100 // limit each IP to 100 requests per windowMs
});
app.use(limiter);

// CORS configuration for custom domain
const allowedOrigins = [
  `https://${CUSTOM_DOMAIN}`,
  `https://www.${CUSTOM_DOMAIN}`,
  `https://*.${CUSTOM_DOMAIN}`,
  process.env.APP_URL
].filter(Boolean);

app.use(cors({
  origin: (origin, callback) => {
    if (!origin) {
      callback(null, true);
      return;
    }

    const isAllowed = allowedOrigins.some(allowed => {
      if (allowed && allowed.includes('*')) {
        const pattern = new RegExp(allowed.replace('*.', '.*\\.'));
        return pattern.test(origin);
      }
      return allowed && origin === allowed;
    });

    if (isAllowed) {
      callback(null, true);
    } else {
      callback(new Error('Not allowed by CORS'));
    }
  },
  credentials: true,
  methods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
  allowedHeaders: ['Content-Type', 'Authorization'],
  maxAge: 86400 // CORS preflight cache for 24 hours
}));

// Enhanced security for production
if (process.env.NODE_ENV === 'production') {
  // Force HTTPS
  app.enable('trust proxy');
  app.use((req, res, next) => {
    if (req.secure) return next();
    res.redirect(`https://${req.headers.host}${req.url}`);
  });
}

try {
  app.listen(PORT, HOST, () => {
    log(`Production server running at http://${HOST}:${PORT}`);
    log(`Main domain: ${CUSTOM_DOMAIN}`);
    log('Security headers and CORS configured for domain and subdomains');
    log(`Allowed origins: ${allowedOrigins.join(', ')}`);
  });
} catch (error) {
  console.error("Failed to start production server:", error);
  process.exit(1);
}