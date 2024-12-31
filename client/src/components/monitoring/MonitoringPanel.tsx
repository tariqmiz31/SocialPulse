import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useQuery } from "@tanstack/react-query";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer
} from "recharts";

interface HealthData {
  status: string;
  uptime: number;
  uptimeFormatted: string;
  memory: {
    rss: string;
    heapTotal: string;
    heapUsed: string;
  };
  timestamp: string;
  requestCount: number;
}

interface StatusData {
  server: string;
  database: string;
  environment: string;
  domain: string;
}

export function MonitoringPanel() {
  const [performanceData, setPerformanceData] = useState<any[]>([]);
  
  const { data: healthData, error: healthError } = useQuery<HealthData>({
    queryKey: ["/api/monitoring/health"],
    refetchInterval: 5000 // Refresh every 5 seconds
  });

  const { data: statusData } = useQuery<StatusData>({
    queryKey: ["/api/monitoring/status"],
    refetchInterval: 10000 // Refresh every 10 seconds
  });

  // Update performance chart data
  useEffect(() => {
    if (healthData) {
      setPerformanceData(prev => {
        const newData = [...prev, {
          time: new Date().toLocaleTimeString(),
          memory: parseInt(healthData.memory.heapUsed),
          requests: healthData.requestCount
        }].slice(-20); // Keep last 20 data points
        return newData;
      });
    }
  }, [healthData]);

  if (healthError) {
    return (
      <Card>
        <CardContent className="p-6">
          <div className="text-red-500">خطأ في تحميل بيانات المراقبة</div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="w-full">
      <CardHeader>
        <CardTitle>لوحة المراقبة</CardTitle>
      </CardHeader>
      <CardContent>
        <Tabs defaultValue="overview">
          <TabsList>
            <TabsTrigger value="overview">نظرة عامة</TabsTrigger>
            <TabsTrigger value="performance">الأداء</TabsTrigger>
            <TabsTrigger value="status">الحالة</TabsTrigger>
          </TabsList>

          <TabsContent value="overview">
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
              <Card>
                <CardContent className="p-4">
                  <div className="text-sm font-medium">الحالة</div>
                  <div className="text-2xl font-bold text-green-500">
                    {healthData?.status || 'جاري التحميل...'}
                  </div>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="p-4">
                  <div className="text-sm font-medium">مدة التشغيل</div>
                  <div className="text-2xl font-bold">
                    {healthData?.uptimeFormatted || '0h 0m'}
                  </div>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="p-4">
                  <div className="text-sm font-medium">الذاكرة المستخدمة</div>
                  <div className="text-2xl font-bold">
                    {healthData?.memory.heapUsed || '0MB'}
                  </div>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="p-4">
                  <div className="text-sm font-medium">عدد الطلبات</div>
                  <div className="text-2xl font-bold">
                    {healthData?.requestCount || 0}
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          <TabsContent value="performance">
            <div className="h-[300px]">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={performanceData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="time" />
                  <YAxis yAxisId="left" />
                  <YAxis yAxisId="right" orientation="right" />
                  <Tooltip />
                  <Line 
                    yAxisId="left"
                    type="monotone" 
                    dataKey="memory" 
                    stroke="#8884d8" 
                    name="الذاكرة (MB)" 
                  />
                  <Line 
                    yAxisId="right"
                    type="monotone" 
                    dataKey="requests" 
                    stroke="#82ca9d" 
                    name="الطلبات" 
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </TabsContent>

          <TabsContent value="status">
            <div className="space-y-4">
              <div className="grid gap-4 md:grid-cols-2">
                <Card>
                  <CardContent className="p-4">
                    <div className="text-sm font-medium">حالة الخادم</div>
                    <div className="text-xl font-bold text-green-500">
                      {statusData?.server || 'جاري التحميل...'}
                    </div>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="p-4">
                    <div className="text-sm font-medium">حالة قاعدة البيانات</div>
                    <div className="text-xl font-bold text-green-500">
                      {statusData?.database || 'جاري التحميل...'}
                    </div>
                  </CardContent>
                </Card>
              </div>
              <Card>
                <CardContent className="p-4">
                  <div className="text-sm font-medium">معلومات النظام</div>
                  <div className="mt-2 space-y-2">
                    <div>
                      <span className="font-medium">البيئة:</span>
                      {' '}{statusData?.environment || 'غير معروف'}
                    </div>
                    <div>
                      <span className="font-medium">النطاق:</span>
                      {' '}{statusData?.domain || 'غير معروف'}
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  );
}
