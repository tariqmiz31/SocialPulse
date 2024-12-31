import { app } from "./index";
import { log } from "./vite";
import dotenv from "dotenv";
import helmet from "helmet";
import cors from "cors";

dotenv.config();

const PORT = parseInt(process.env.PORT || "5000", 10);
const HOST = "0.0.0.0";
const CUSTOM_DOMAIN = "silvariumsocial.com";

// Enhanced security for production
if (process.env.NODE_ENV === 'production') {
  // Force HTTPS
  app.enable('trust proxy');
  app.use((req, res, next) => {
    if (req.secure) return next();
    res.redirect(`https://${req.headers.host}${req.url}`);
  });
}

// Additional production security headers
app.use(helmet({
  contentSecurityPolicy: {
    directives: {
      defaultSrc: ["'self'"],
      connectSrc: ["'self'", `https://${CUSTOM_DOMAIN}`],
      imgSrc: ["'self'", "data:", "blob:"],
      scriptSrc: ["'self'", "'unsafe-inline'"],
      styleSrc: ["'self'", "'unsafe-inline'"],
      frameSrc: ["'self'"],
      objectSrc: ["'none'"],
      upgradeInsecureRequests: []
    }
  },
  crossOriginEmbedderPolicy: false,
  crossOriginResourcePolicy: { policy: "cross-origin" },
  hsts: {
    maxAge: 31536000,
    includeSubDomains: true,
    preload: true
  }
}));

// CORS configuration for main domain
const allowedOrigins = [
  `https://${CUSTOM_DOMAIN}`,
  `https://www.${CUSTOM_DOMAIN}`,
  process.env.APP_URL
].filter(Boolean);

app.use(cors({
  origin: (origin, callback) => {
    if (!origin || allowedOrigins.includes(origin)) {
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

try {
  app.listen(PORT, HOST, () => {
    log(`Production server running at http://${HOST}:${PORT}`);
    log(`Main domain: ${process.env.APP_URL || CUSTOM_DOMAIN}`);
    log('Security headers and CORS configured for main domain');

    // Log allowed origins for verification
    log(`Allowed origins: ${allowedOrigins.join(', ')}`);
  });
} catch (error) {
  console.error("Failed to start production server:", error);
  process.exit(1);
}