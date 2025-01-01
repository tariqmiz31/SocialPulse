import { drizzle } from "drizzle-orm/neon-serverless";
import { sql } from "drizzle-orm";
import ws from "ws";
import * as schema from "@db/schema";
import logger from "../server/logConfig";

const MAX_RETRIES = 10;
const RETRY_INTERVAL = 10000; // 10 seconds between retries

async function createConnection() {
  if (!process.env.DATABASE_URL) {
    throw new Error("DATABASE_URL must be set. Did you forget to provision a database?");
  }

  let retries = 0;
  let lastError = null;

  while (retries < MAX_RETRIES) {
    try {
      logger.info(`Attempting to connect to database (attempt ${retries + 1}/${MAX_RETRIES})`);

      const db = drizzle({
        connection: process.env.DATABASE_URL,
        schema,
        ws: ws,
      });

      // Test the connection
      await db.execute(sql`SELECT 1`);
      logger.info("Database connection established successfully");
      return db;
    } catch (error) {
      lastError = error;
      retries++;
      logger.error(`Failed to connect to database (attempt ${retries}/${MAX_RETRIES}):`, error);

      if (retries === MAX_RETRIES) {
        logger.error("Maximum retry attempts reached, giving up");
        break;
      }

      logger.info(`Waiting ${RETRY_INTERVAL/1000} seconds before next attempt...`);
      await new Promise(resolve => setTimeout(resolve, RETRY_INTERVAL));
    }
  }

  throw new Error(`Failed to connect to database after ${MAX_RETRIES} attempts. Last error: ${lastError?.message}`);
}

async function initializeDatabase() {
  try {
    const db = await createConnection();
    process.on('SIGINT', async () => {
      logger.info('Received SIGINT signal, closing database connection...');
      process.exit(0);
    });

    process.on('SIGTERM', async () => {
      logger.info('Received SIGTERM signal, closing database connection...');
      process.exit(0);
    });

    process.on('unhandledRejection', (reason, promise) => {
      logger.error('Unhandled Rejection at:', promise, 'reason:', reason);
    });

    return db;
  } catch (error) {
    logger.error('Failed to initialize database:', error);
    throw error;
  }
}

export const db = await initializeDatabase();