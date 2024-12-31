#!/bin/bash

echo "بدء عملية النشر..."

# التحقق من المتغيرات البيئية الضرورية
if [ -z "$DATABASE_URL" ] || [ -z "$APP_URL" ] || [ -z "$CUSTOM_DOMAIN" ]; then
    echo "خطأ: المتغيرات البيئية مفقودة"
    exit 1
fi

# تثبيت الاعتماديات
echo "تثبيت الاعتماديات..."
npm install
npm install -g pm2 vite drizzle-kit tsx

# بناء التطبيق
echo "بناء التطبيق..."
npm run build

# تحديث قاعدة البيانات
echo "تحديث قاعدة البيانات..."
npm run db:push

# التحقق من صحة البناء
if [ ! -d "dist" ]; then
    echo "خطأ: فشل البناء"
    exit 1
fi

# إيقاف التطبيق القديم إذا كان قيد التشغيل
pm2 delete socialpulse 2>/dev/null || true

# بدء التطبيق باستخدام PM2
echo "بدء التطبيق..."
pm2 start pm2.config.cjs --env production

# التحقق من صحة النشر
echo "التحقق من صحة النشر..."
sleep 5
if curl -f "http://localhost:5000/api/monitoring/health" > /dev/null 2>&1; then
    echo "تم النشر بنجاح!"
else
    echo "خطأ: فشل التحقق من صحة النشر"
    exit 1
fi

# تحديث النسخة الاحتياطية
echo "إنشاء نسخة احتياطية جديدة..."
curl -X POST "http://localhost:5000/api/backup/create"

# تنظيف الملفات المؤقتة
echo "تنظيف الملفات المؤقتة..."
rm -rf .cache tmp/*

echo "اكتمل النشر بنجاح!"