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
  defaultMeta: { service: 'socialpulse' },
  transports: [
    // تسجيل كل المستويات في ملف مجمع
    new winston.transports.File({ 
      filename: '/tmp/socialpulse-error.log',
      level: 'error',
      maxsize: 5242880, // 5MB
      maxFiles: 5,
    }),
    new winston.transports.File({ 
      filename: '/tmp/socialpulse-combined.log',
      maxsize: 5242880, // 5MB
      maxFiles: 5,
    })
  ]
});

// إضافة تسجيل في وحدة التحكم في بيئة التطوير
if (process.env.NODE_ENV !== 'production') {
  logger.add(new winston.transports.Console({
    format: winston.format.combine(
      winston.format.colorize(),
      winston.format.simple()
    )
  }));
}

// دالة مساعدة لتنسيق رسائل الخطأ
export const formatError = (error: Error) => ({
  message: error.message,
  stack: error.stack,
  name: error.name,
  timestamp: new Date().toISOString()
});

// تصدير الـ logger للاستخدام في بقية التطبيق
export default logger;
