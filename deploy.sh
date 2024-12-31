#!/bin/bash

echo "بدء عملية النشر..."

# التحقق من المتغيرات البيئية الضرورية
if [ -z "$DATABASE_URL" ] || [ -z "$APP_URL" ] || [ -z "$CUSTOM_DOMAIN" ]; then
    echo "خطأ: المتغيرات البيئية مفقودة"
    exit 1
fi

# تثبيت الاعتماديات
echo "تثبيت الاعتماديات..."
npm install --production

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

# بدء التطبيق باستخدام PM2
echo "إعادة تشغيل التطبيق..."
if pm2 list | grep -q "socialpulse"; then
    pm2 reload socialpulse --update-env
else
    pm2 start pm2.config.js --env production
fi

# التحقق من صحة النشر
echo "التحقق من صحة النشر..."
sleep 5
if curl -f "http://localhost:5000/api/monitoring/health" > /dev/null 2>&1; then
    echo "تم النشر بنجاح!"
else
    echo "خطأ: فشل التحقق من صحة النشر"
    exit 1
fi
