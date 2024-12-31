import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ContentCreator } from "@/components/ContentCreator";
import { PlatformSelector } from "@/components/PlatformSelector";
import { MonitoringPanel } from "@/components/monitoring/MonitoringPanel";
import { LogViewer } from "@/components/monitoring/LogViewer";
import { platforms } from "@/lib/platforms";

export default function Dashboard() {
  return (
    <div className="container mx-auto p-6 space-y-6" dir="rtl">
      <h1 className="text-3xl font-bold">لوحة التحكم</h1>

      <MonitoringPanel />

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {platforms.map(platform => (
          <Card key={platform.id}>
            <CardHeader className="flex flex-row items-center space-x-4">
              <platform.icon className="w-8 h-8" style={{ color: platform.color }} />
              <CardTitle>{platform.name}</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-2xl font-bold">{platform.stats.posts}</p>
              <p className="text-muted-foreground">المنشورات هذا الشهر</p>
            </CardContent>
          </Card>
        ))}
      </div>

      <LogViewer />

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div>
          <h2 className="text-2xl font-bold mb-4">إنشاء محتوى</h2>
          <Card>
            <CardContent className="p-6">
              <ContentCreator />
            </CardContent>
          </Card>
        </div>

        <div>
          <h2 className="text-2xl font-bold mb-4">المنصات المتصلة</h2>
          <Card>
            <CardContent className="p-6">
              <PlatformSelector />
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}