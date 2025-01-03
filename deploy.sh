#!/bin/bash

echo "تحديث تكوين Replit..."

# تأكد من وجود التكوينات المطلوبة
if [ ! -f ".replit" ]; then
  echo "إنشاء ملف .replit..."
  cat > .replit << EOL
run = "python server/start_production.py"
language = "python3"
hidden = [".config", "package-lock.json"]

[env]
XDG_CONFIG_HOME = "/home/runner/.config"

[nix]
channel = "stable-21_11"

[gitHubImport]
requiredFiles = [".replit", "replit.nix", ".config"]
EOL
fi

# تحديث replit.nix إذا لزم الأمر
if [ ! -f "replit.nix" ]; then
  echo "إنشاء ملف replit.nix..."
  cat > replit.nix << EOL
{ pkgs }: {
    deps = [
        pkgs.python39
        pkgs.postgresql
    ];
}
EOL
fi

echo "بدء عملية النشر..."

# التحقق من المتغيرات البيئية
if [ -z "$DATABASE_URL" ]; then
    echo "خطأ: DATABASE_URL غير موجود"
    exit 1
fi

# تثبيت الاعتماديات
echo "تثبيت الاعتماديات..."
pip install -r requirements.txt

# التأكد من إيقاف أي عمليات سابقة على المنفذ 8080
echo "إيقاف العمليات السابقة..."
pkill -f "python server/start_production.py" || true

# انتظار حتى يصبح المنفذ متاحاً
wait_for_port() {
    local port=$1
    local retries=10
    local wait=2
    while [ $retries -gt 0 ]; do
        if ! lsof -i :$port > /dev/null 2>&1; then
            return 0
        fi
        retries=$((retries - 1))
        echo "المنفذ $port مشغول، انتظار..."
        sleep $wait
    done
    return 1
}

if ! wait_for_port 8080; then
    echo "خطأ: المنفذ 8080 لا يزال مشغولاً"
    exit 1
fi

# بدء التطبيق
echo "بدء التطبيق..."
python server/start_production.py &

# انتظار بدء التطبيق
echo "انتظار بدء التطبيق..."
sleep 5

# التحقق من حالة التطبيق
if curl -s http://localhost:8080/api/monitoring/health > /dev/null; then
    echo "تم بدء التطبيق بنجاح!"
    exit 0
else
    echo "فشل بدء التطبيق"
    exit 1
fi