import winston from 'winston';
import path from 'path';

// تكوين Winston logger مع مستويات مختلفة للتسجيل
const logger = winston.createLogger({
  level: process.env.NODE_ENV === 'production' ? 'info' : 'debug',
  format: winston.format.combine(
    winston.format.timestamp({
      format: 'YYYY-MM-DD HH:mm:ss'
    }),
    winston.format.errors({ stack: true }),
    winston.format.splat(),
    winston.format.json()
  ),
  defaultMeta: { service: 'silvarium' },
  transports: [
    // تسجيل كل المستويات في ملف مجمع
    new winston.transports.File({ 
      filename: '/tmp/silvarium-error.log',
      level: 'error',
      maxsize: 5242880, // 5MB
      maxFiles: 5,
      format: winston.format.combine(
        winston.format.timestamp(),
        winston.format.json()
      )
    }),
    new winston.transports.File({ 
      filename: '/tmp/silvarium-combined.log',
      maxsize: 5242880, // 5MB
      maxFiles: 5,
      format: winston.format.combine(
        winston.format.timestamp(),
        winston.format.json()
      )
    })
  ]
});

// إضافة تسجيل في وحدة التحكم في بيئة التطوير
if (process.env.NODE_ENV !== 'production') {
  logger.add(new winston.transports.Console({
    format: winston.format.combine(
      winston.format.colorize(),
      winston.format.simple(),
      winston.format.printf(({ level, message, timestamp, ...metadata }) => {
        let msg = `${timestamp} [${level}] : ${message}`;
        if (Object.keys(metadata).length > 0) {
          msg += ` | ${JSON.stringify(metadata)}`;
        }
        return msg;
      })
    )
  }));
}

// دوال مساعدة لتنسيق السجلات
export const formatError = (error: Error) => ({
  message: error.message,
  stack: error.stack,
  name: error.name,
  timestamp: new Date().toISOString()
});

export const formatRequest = (req: any) => ({
  method: req.method,
  url: req.url,
  headers: req.headers,
  query: req.query,
  body: req.body,
  ip: req.ip
});

// تصدير الـ logger للاستخدام في بقية التطبيق
export default logger;