#!/bin/bash

echo "بدء عملية النشر..."

# التحقق من المتغيرات البيئية الضرورية
if [ -z "$DATABASE_URL" ]; then
    echo "خطأ: DATABASE_URL غير موجود"
    exit 1
fi

# تحديث التطبيق وتثبيت الاعتماديات
echo "تثبيت الاعتماديات..."
npm install
npm install -g pm2

# بناء التطبيق
echo "بناء التطبيق..."
npm run build

# التحقق من صحة البناء
if [ ! -d "dist" ]; then
    echo "خطأ: فشل البناء"
    exit 1
fi

# إيقاف التطبيق القديم إذا كان قيد التشغيل
pm2 delete socialpulse 2>/dev/null || true

# تنظيف السجلات القديمة
rm -f /tmp/socialpulse-err.log /tmp/socialpulse-out.log

# بدء التطبيق باستخدام PM2
echo "بدء التطبيق..."
NODE_ENV=production pm2 start pm2.config.cjs --env production

# انتظار بدء التطبيق
echo "انتظار بدء التطبيق..."
sleep 20

# التحقق من صحة النشر
echo "التحقق من صحة النشر..."
STATUS_URL="http://localhost:5000/api/monitoring/status"
RETRY_COUNT=0
MAX_RETRIES=15
RETRY_INTERVAL=10

verify_deployment() {
    HTTP_RESPONSE=$(curl -s -w "\n%{http_code}" $STATUS_URL)
    HTTP_BODY=$(echo "$HTTP_RESPONSE" | head -n 1)
    HTTP_STATUS=$(echo "$HTTP_RESPONSE" | tail -n 1)

    if [ "$HTTP_STATUS" -eq 200 ]; then
        # التحقق من حالة الخادم وقاعدة البيانات
        SERVER_STATUS=$(echo "$HTTP_BODY" | grep -o '"server":"[^"]*"' | cut -d'"' -f4)
        DB_STATUS=$(echo "$HTTP_BODY" | grep -o '"database":"[^"]*"' | cut -d'"' -f4)

        if [ "$SERVER_STATUS" = "running" ] && [ "$DB_STATUS" = "connected" ]; then
            return 0
        fi
    fi
    return 1
}

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if verify_deployment; then
        echo "تم النشر بنجاح!"
        echo "حالة التطبيق:"
        curl -s $STATUS_URL | json_pp
        echo "معلومات عمليات التشغيل:"
        pm2 list
        echo "تم اكتمال عملية النشر بنجاح!"
        exit 0
    else
        RETRY_COUNT=$((RETRY_COUNT + 1))
        if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
            echo "خطأ: فشل التحقق من صحة النشر بعد $MAX_RETRIES محاولة"
            echo "آخر استجابة:"
            curl -s $STATUS_URL || echo "لا يمكن الوصول إلى نقطة النهاية"
            echo "سجلات التطبيق:"
            pm2 logs socialpulse --lines 100
            exit 1
        fi
        echo "محاولة $RETRY_COUNT من $MAX_RETRIES - انتظار..."
        sleep $RETRY_INTERVAL
    fi
done