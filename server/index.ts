import dotenv from "dotenv";
dotenv.config();
import express, { type Request, Response, NextFunction } from "express";
import { registerRoutes } from "./routes";
import { setupVite, serveStatic, log } from "./vite";
import { createServer } from "http";
import helmet from "helmet";
import cors from "cors";
import compression from "compression";

// Create Express app
const app = express();
app.use(express.json());
app.use(express.urlencoded({ extended: false }));

// Security middleware
app.use(helmet());
app.use(compression());

// Configure CORS for our domain
const allowedOrigins = [process.env.APP_URL, process.env.CUSTOM_DOMAIN].filter(Boolean);
app.use(cors({
  origin: allowedOrigins,
  credentials: true
}));

// Request logging middleware
app.use((req, res, next) => {
  const start = Date.now();
  const path = req.path;
  let capturedJsonResponse: Record<string, any> | undefined = undefined;

  const originalResJson = res.json;
  res.json = function (bodyJson, ...args) {
    capturedJsonResponse = bodyJson;
    return originalResJson.apply(res, [bodyJson, ...args]);
  };

  res.on("finish", () => {
    const duration = Date.now() - start;
    if (path.startsWith("/api")) {
      let logLine = `${req.method} ${path} ${res.statusCode} in ${duration}ms`;
      if (capturedJsonResponse) {
        logLine += ` :: ${JSON.stringify(capturedJsonResponse)}`;
      }

      if (logLine.length > 80) {
        logLine = logLine.slice(0, 79) + "…";
      }

      log(logLine);
    }
  });

  next();
});

// Initialize server setup
(async () => {
  try {
    // Create HTTP server
    const server = createServer(app);

    // Register routes with domain configuration
    const domain = process.env.CUSTOM_DOMAIN || process.env.APP_URL;
    app.set('trust proxy', 1);

    // Force HTTPS in production
    app.use((req, res, next) => {
      if (process.env.NODE_ENV === 'production' && !req.secure) {
        return res.redirect(`https://${req.headers.host}${req.url}`);
      }
      next();
    });

    registerRoutes(app);

    // Error handling middleware
    app.use((err: any, _req: Request, res: Response, _next: NextFunction) => {
      const status = err.status || err.statusCode || 500;
      const message = err.message || "Internal Server Error";

      res.status(status).json({ 
        message,
        domain: process.env.CUSTOM_DOMAIN || process.env.APP_URL,
        timestamp: new Date().toISOString()
      });

      if (app.get("env") === "development") {
        console.error(err);
      }
    });

    // Setup Vite in development, static files in production
    if (app.get("env") === "development") {
      await setupVite(app, server);
    } else {
      serveStatic(app);
    }

    // Start server
    const PORT = parseInt(process.env.PORT || "5000", 10);
    server.listen(PORT, "0.0.0.0", () => {
      log(`Server running on port ${PORT}`);
      log(`Main domain: ${domain}`);

      if (domain) {
        log(`Supporting subdomains for: *.${domain}`);
      }
    });
  } catch (error) {
    console.error("Failed to start the server:", error);
    process.exit(1);
  }
})();

export { app };