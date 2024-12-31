import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle
} from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ScrollArea } from "@/components/ui/scroll-area";

interface Log {
  timestamp: string;
  level: string;
  message: string;
  service: string;
  [key: string]: any;
}

interface ErrorLog extends Log {
  stack?: string;
  name?: string;
}

export function LogViewer() {
  const [activeTab, setActiveTab] = useState("all");

  const { data: logs, error: logsError } = useQuery<Log[]>({
    queryKey: ["/api/monitoring/logs"],
    refetchInterval: 30000 // تحديث كل 30 ثانية
  });

  const { data: errors, error: errorsError } = useQuery<ErrorLog[]>({
    queryKey: ["/api/monitoring/errors"],
    refetchInterval: 30000
  });

  if (logsError || errorsError) {
    return (
      <Card>
        <CardContent className="p-6">
          <div className="text-red-500">خطأ في تحميل السجلات</div>
        </CardContent>
      </Card>
    );
  }

  const formatTimestamp = (timestamp: string) => {
    return new Date(timestamp).toLocaleString('ar-SA', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    });
  };

  const getLevelColor = (level: string) => {
    switch (level.toLowerCase()) {
      case 'error': return 'text-red-500';
      case 'warn': return 'text-yellow-500';
      case 'info': return 'text-blue-500';
      default: return 'text-gray-500';
    }
  };

  return (
    <Card className="w-full">
      <CardHeader>
        <CardTitle>سجلات النظام</CardTitle>
      </CardHeader>
      <CardContent>
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList>
            <TabsTrigger value="all">جميع السجلات</TabsTrigger>
            <TabsTrigger value="errors">الأخطاء</TabsTrigger>
          </TabsList>

          <TabsContent value="all">
            <ScrollArea className="h-[400px] w-full">
              <div className="space-y-2">
                {logs?.map((log, index) => (
                  <div key={index} className="p-2 border-b">
                    <div className="flex justify-between text-sm">
                      <span className={getLevelColor(log.level)}>
                        {log.level.toUpperCase()}
                      </span>
                      <span className="text-gray-500">
                        {formatTimestamp(log.timestamp)}
                      </span>
                    </div>
                    <div className="mt-1">{log.message}</div>
                  </div>
                ))}
              </div>
            </ScrollArea>
          </TabsContent>

          <TabsContent value="errors">
            <ScrollArea className="h-[400px] w-full">
              <div className="space-y-2">
                {errors?.map((error, index) => (
                  <div key={index} className="p-2 border-b">
                    <div className="flex justify-between text-sm">
                      <span className="text-red-500">
                        {error.name || 'ERROR'}
                      </span>
                      <span className="text-gray-500">
                        {formatTimestamp(error.timestamp)}
                      </span>
                    </div>
                    <div className="mt-1 text-red-600">{error.message}</div>
                    {error.stack && (
                      <pre className="mt-2 text-xs bg-gray-100 p-2 rounded overflow-x-auto">
                        {error.stack}
                      </pre>
                    )}
                  </div>
                ))}
              </div>
            </ScrollArea>
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  );
}
