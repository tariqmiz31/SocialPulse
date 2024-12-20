import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";
import { platforms } from "@/lib/platforms";

const mockData = [
  { name: "Jan", instagram: 400, facebook: 240, twitter: 320 },
  { name: "Feb", instagram: 300, facebook: 139, twitter: 220 },
  { name: "Mar", instagram: 200, facebook: 980, twitter: 420 },
  { name: "Apr", instagram: 278, facebook: 390, twitter: 520 },
  { name: "May", instagram: 189, facebook: 480, twitter: 380 },
];

export default function Analytics() {
  return (
    <div className="container mx-auto p-6 space-y-6">
      <h1 className="text-3xl font-bold">Analytics Overview</h1>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {platforms.map(platform => (
          <Card key={platform.id}>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <platform.icon className="w-5 h-5" style={{ color: platform.color }} />
                {platform.name}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{platform.stats.engagement}%</div>
              <p className="text-muted-foreground">Engagement Rate</p>
            </CardContent>
          </Card>
        ))}
      </div>

      <Card className="col-span-full">
        <CardHeader>
          <CardTitle>Performance Over Time</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-[400px]">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={mockData}>
                <XAxis dataKey="name" />
                <YAxis />
                <Tooltip />
                {platforms.map(platform => (
                  <Line
                    key={platform.id}
                    type="monotone"
                    dataKey={platform.id}
                    stroke={platform.color}
                    strokeWidth={2}
                  />
                ))}
              </LineChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
