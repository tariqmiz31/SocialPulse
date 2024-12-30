import { app } from "./index";
import { log } from "./vite";
import dotenv from "dotenv";

dotenv.config();

const PORT = parseInt(process.env.PORT || "5000", 10);
const HOST = "0.0.0.0";

try {
  app.listen(PORT, HOST, () => {
    log(`Production server running at http://${HOST}:${PORT}`);
    log(`Custom domain: ${process.env.APP_URL || 'Not configured'}`);
  });
} catch (error) {
  console.error("Failed to start production server:", error);
  process.exit(1);
}