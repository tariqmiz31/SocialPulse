#!/bin/bash

echo "بدء عملية النشر المستمر..."

# التحقق من المتغيرات البيئية المطلوبة
required_env_vars=(
  "DATABASE_URL"
  "PGHOST"
  "PGUSER"
  "PGPASSWORD"
  "PGDATABASE"
  "PGPORT"
  "APP_URL"
  "CUSTOM_DOMAIN"
)

for var in "${required_env_vars[@]}"; do
  if [ -z "${!var}" ]; then
    echo "خطأ: المتغير البيئي $var غير موجود"
    exit 1
  fi
done

# تحديث التطبيق وتثبيت الاعتماديات
echo "تثبيت الاعتماديات..."
npm ci
npm install -g pm2

# بناء التطبيق
echo "بناء التطبيق..."
NODE_ENV=production npm run build

# التحقق من صحة البناء
if [ ! -d "dist" ]; then
  echo "خطأ: فشل البناء"
  exit 1
fi

# دفع تحديثات قاعدة البيانات
echo "تطبيق تحديثات قاعدة البيانات..."
npm run db:push

# التحقق من الاتصال بقاعدة البيانات
echo "التحقق من الاتصال بقاعدة البيانات..."
node -e "
const { db } = require('./dist/db');
async function checkDb() {
  try {
    await db.execute(sql\`SELECT 1\`);
    console.log('تم الاتصال بقاعدة البيانات بنجاح');
    process.exit(0);
  } catch (error) {
    console.error('فشل الاتصال بقاعدة البيانات:', error);
    process.exit(1);
  }
}
checkDb();
"

# إيقاف وإعادة تشغيل التطبيق
echo "إعادة تشغيل التطبيق..."
pm2 delete socialpulse 2>/dev/null || true
NODE_ENV=production pm2 start pm2.config.cjs --env production

# انتظار بدء التطبيق
echo "التحقق من صحة النشر..."
MAX_RETRIES=15
RETRY_COUNT=0
RETRY_INTERVAL=10

verify_deployment() {
  response=$(curl -s "http://localhost:5000/api/monitoring/status")
  if [ $? -eq 0 ]; then
    server_status=$(echo "$response" | grep -o '"server":"[^"]*"' | cut -d'"' -f4)
    db_status=$(echo "$response" | grep -o '"database":"[^"]*"' | cut -d'"' -f4)
    
    if [ "$server_status" = "running" ] && [ "$db_status" = "connected" ]; then
      return 0
    fi
  fi
  return 1
}

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
  if verify_deployment; then
    echo "تم النشر بنجاح!"
    pm2 list
    exit 0
  fi
  
  RETRY_COUNT=$((RETRY_COUNT + 1))
  if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    echo "خطأ: فشل التحقق من صحة النشر بعد $MAX_RETRIES محاولة"
    pm2 logs socialpulse --lines 100
    exit 1
  fi
  
  echo "محاولة $RETRY_COUNT من $MAX_RETRIES - انتظار..."
  sleep $RETRY_INTERVAL
done
