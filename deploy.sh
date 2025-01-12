#!/bin/bash

echo "بدء عملية النشر..."

# التحقق من المتغيرات البيئية الضرورية
if [ -z "$DATABASE_URL" ]; then
    echo "خطأ: متغير DATABASE_URL غير موجود"
    exit 1
fi

# تثبيت الاعتماديات
echo "تثبيت الاعتماديات..."
pip install -r requirements.txt

# دالة لانتظار المنفذ
wait_for_port() {
    local port=$1
    local max_attempts=30
    local attempt=1

    echo "انتظار المنفذ $port..."

    while [ $attempt -le $max_attempts ]; do
        if ! lsof -i :$port > /dev/null 2>&1; then
            echo "المنفذ $port متاح"
            return 0
        fi

        echo "محاولة $attempt من $max_attempts - المنفذ $port مشغول"

        # محاولة إنهاء العملية التي تستخدم المنفذ
        local pid=$(lsof -t -i:$port)
        if [ ! -z "$pid" ]; then
            echo "محاولة إنهاء العملية $pid على المنفذ $port"
            kill -9 $pid 2>/dev/null
        fi

        sleep 2
        attempt=$((attempt + 1))
    done

    echo "خطأ: فشل في تحرير المنفذ $port بعد $max_attempts محاولة"
    return 1
}

# تنظيف المنافذ
echo "تنظيف المنافذ..."
PORT=8080
kill $(lsof -t -i:$PORT) 2>/dev/null || true
sleep 2

# انتظار تحرير المنفذ
if ! wait_for_port $PORT; then
    echo "فشل في تحرير المنفذ $PORT"
    exit 1
fi

echo "تم تحرير المنفذ $PORT بنجاح"

# بدء التطبيق
echo "بدء التطبيق..."
export PORT=8080
python server/start_production.py &

# انتظار بدء التطبيق
echo "انتظار بدء التطبيق..."
attempt=1
max_attempts=30

while [ $attempt -le $max_attempts ]; do
    if curl -s http://localhost:$PORT/api/health > /dev/null 2>&1; then
        echo "تم بدء التطبيق بنجاح على المنفذ $PORT!"
        exit 0
    fi
    echo "محاولة $attempt من $max_attempts - انتظار بدء التطبيق..."
    sleep 2
    attempt=$((attempt + 1))
done

echo "فشل في بدء التطبيق بعد $max_attempts محاولة"
exit 1