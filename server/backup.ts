import { exec } from 'child_process';
import { promisify } from 'util';
import fs from 'fs/promises';
import path from 'path';
import logger from './logConfig';

const execAsync = promisify(exec);

// تكوين مسار حفظ النسخ الاحتياطية
const BACKUP_DIR = '/tmp/backups';
const BACKUP_RETENTION_DAYS = 7; // الاحتفاظ بالنسخ الاحتياطية لمدة 7 أيام

// إنشاء النسخة الاحتياطية
async function createBackup() {
  const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
  const filename = `backup-${timestamp}.sql`;
  const filepath = path.join(BACKUP_DIR, filename);

  try {
    // التأكد من وجود مجلد النسخ الاحتياطية
    await fs.mkdir(BACKUP_DIR, { recursive: true });

    // إنشاء نسخة احتياطية باستخدام pg_dump
    const command = `PGPASSWORD=${process.env.PGPASSWORD} pg_dump -h ${process.env.PGHOST} -U ${process.env.PGUSER} -d ${process.env.PGDATABASE} -F p -f ${filepath}`;
    
    await execAsync(command);
    
    logger.info(`تم إنشاء نسخة احتياطية بنجاح: ${filename}`);
    
    // حذف النسخ الاحتياطية القديمة
    await cleanOldBackups();
    
    return {
      success: true,
      filename,
      path: filepath
    };
  } catch (error) {
    logger.error('خطأ في إنشاء النسخة الاحتياطية:', error);
    throw error;
  }
}

// حذف النسخ الاحتياطية القديمة
async function cleanOldBackups() {
  try {
    const files = await fs.readdir(BACKUP_DIR);
    const now = new Date();

    for (const file of files) {
      const filePath = path.join(BACKUP_DIR, file);
      const stats = await fs.stat(filePath);
      const daysOld = (now.getTime() - stats.mtime.getTime()) / (1000 * 60 * 60 * 24);

      if (daysOld > BACKUP_RETENTION_DAYS) {
        await fs.unlink(filePath);
        logger.info(`تم حذف النسخة الاحتياطية القديمة: ${file}`);
      }
    }
  } catch (error) {
    logger.error('خطأ في تنظيف النسخ الاحتياطية القديمة:', error);
  }
}

// استعادة قاعدة البيانات من نسخة احتياطية
async function restoreBackup(filename: string) {
  const filepath = path.join(BACKUP_DIR, filename);

  try {
    // التحقق من وجود الملف
    await fs.access(filepath);

    // استعادة قاعدة البيانات
    const command = `PGPASSWORD=${process.env.PGPASSWORD} psql -h ${process.env.PGHOST} -U ${process.env.PGUSER} -d ${process.env.PGDATABASE} -f ${filepath}`;
    
    await execAsync(command);
    
    logger.info(`تم استعادة قاعدة البيانات بنجاح من: ${filename}`);
    
    return {
      success: true,
      filename
    };
  } catch (error) {
    logger.error('خطأ في استعادة قاعدة البيانات:', error);
    throw error;
  }
}

// جدولة النسخ الاحتياطي التلقائي
export function scheduleBackups() {
  // إنشاء نسخة احتياطية كل 24 ساعة
  setInterval(async () => {
    try {
      await createBackup();
      logger.info('تم إكمال النسخ الاحتياطي المجدول');
    } catch (error) {
      logger.error('فشل النسخ الاحتياطي المجدول:', error);
    }
  }, 24 * 60 * 60 * 1000);

  // إنشاء نسخة احتياطية أولية عند بدء التشغيل
  createBackup().catch(error => {
    logger.error('فشل النسخ الاحتياطي الأولي:', error);
  });
}

// تصدير الوظائف
export {
  createBackup,
  restoreBackup,
  cleanOldBackups
};
