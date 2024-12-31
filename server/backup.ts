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
    logger.info(`تم إنشاء/التحقق من وجود مجلد النسخ الاحتياطية: ${BACKUP_DIR}`);

    // إنشاء نسخة احتياطية باستخدام pg_dump مع معلومات تسجيل إضافية
    logger.info('بدء عملية النسخ الاحتياطي باستخدام pg_dump');
    const command = `PGPASSWORD=${process.env.PGPASSWORD} pg_dump -h ${process.env.PGHOST} -U ${process.env.PGUSER} -d ${process.env.PGDATABASE} -F p -f ${filepath}`;

    const { stdout, stderr } = await execAsync(command);
    if (stderr) {
      logger.warn('تحذيرات من pg_dump:', stderr);
    }
    if (stdout) {
      logger.info('مخرجات pg_dump:', stdout);
    }

    // التحقق من إنشاء الملف
    const stats = await fs.stat(filepath);
    logger.info(`تم إنشاء النسخة الاحتياطية بنجاح: ${filename} (${stats.size} bytes)`);

    // حذف النسخ الاحتياطية القديمة
    await cleanOldBackups();

    return {
      success: true,
      filename,
      path: filepath,
      size: stats.size,
      timestamp: new Date().toISOString()
    };
  } catch (error) {
    logger.error('خطأ في إنشاء النسخة الاحتياطية:', error);
    throw new Error(`فشل إنشاء النسخة الاحتياطية: ${error.message}`);
  }
}

// حذف النسخ الاحتياطية القديمة
async function cleanOldBackups() {
  try {
    logger.info('بدء تنظيف النسخ الاحتياطية القديمة');
    const files = await fs.readdir(BACKUP_DIR);
    const now = new Date();

    for (const file of files) {
      if (!file.startsWith('backup-') || !file.endsWith('.sql')) {
        continue;
      }

      const filePath = path.join(BACKUP_DIR, file);
      const stats = await fs.stat(filePath);
      const daysOld = (now.getTime() - stats.mtime.getTime()) / (1000 * 60 * 60 * 24);

      if (daysOld > BACKUP_RETENTION_DAYS) {
        await fs.unlink(filePath);
        logger.info(`تم حذف النسخة الاحتياطية القديمة: ${file} (${daysOld.toFixed(1)} أيام)`);
      }
    }
    logger.info('تم الانتهاء من تنظيف النسخ الاحتياطية القديمة');
  } catch (error) {
    logger.error('خطأ في تنظيف النسخ الاحتياطية القديمة:', error);
    throw error;
  }
}

// استعادة قاعدة البيانات من نسخة احتياطية
async function restoreBackup(filename: string) {
  const filepath = path.join(BACKUP_DIR, filename);

  try {
    // التحقق من وجود الملف
    await fs.access(filepath);
    logger.info(`بدء استعادة النسخة الاحتياطية: ${filename}`);

    // استعادة قاعدة البيانات
    const command = `PGPASSWORD=${process.env.PGPASSWORD} psql -h ${process.env.PGHOST} -U ${process.env.PGUSER} -d ${process.env.PGDATABASE} -f ${filepath}`;

    const { stdout, stderr } = await execAsync(command);
    if (stderr) {
      logger.warn('تحذيرات من عملية الاستعادة:', stderr);
    }
    if (stdout) {
      logger.info('مخرجات عملية الاستعادة:', stdout);
    }

    logger.info(`تم استعادة قاعدة البيانات بنجاح من: ${filename}`);

    return {
      success: true,
      filename,
      timestamp: new Date().toISOString()
    };
  } catch (error) {
    logger.error('خطأ في استعادة قاعدة البيانات:', error);
    throw new Error(`فشل استعادة النسخة الاحتياطية: ${error.message}`);
  }
}

// جدولة النسخ الاحتياطي التلقائي
export function scheduleBackups() {
  const runBackup = async () => {
    try {
      logger.info('بدء النسخ الاحتياطي المجدول');
      await createBackup();
      logger.info('تم إكمال النسخ الاحتياطي المجدول بنجاح');
    } catch (error) {
      logger.error('فشل النسخ الاحتياطي المجدول:', error);
    }
  };

  // حساب الوقت حتى الساعة 4 صباحاً القادمة
  const now = new Date();
  const next4AM = new Date(now);
  next4AM.setHours(4, 0, 0, 0);

  // إذا كان الوقت الحالي بعد 4 صباحاً، نضيف يوم
  if (now.getHours() >= 4) {
    next4AM.setDate(next4AM.getDate() + 1);
  }

  const timeUntil4AM = next4AM.getTime() - now.getTime();

  // جدولة النسخ الاحتياطي الأول في الساعة 4 صباحاً
  setTimeout(() => {
    runBackup();
    // ثم تشغيل النسخ الاحتياطي كل 24 ساعة
    setInterval(runBackup, 24 * 60 * 60 * 1000);
  }, timeUntil4AM);

  // إنشاء نسخة احتياطية أولية عند بدء التشغيل
  createBackup().catch(error => {
    logger.error('فشل النسخ الاحتياطي الأولي:', error);
  });

  logger.info(`تم تكوين جدولة النسخ الاحتياطي اليومي في الساعة 04:00`);
}

// تصدير الوظائف
export {
  createBackup,
  restoreBackup,
  cleanOldBackups
};