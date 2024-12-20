import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Rectangle
} from "recharts";
import { useMemo } from "react";
import { platforms } from "@/lib/platforms";
import { useQuery } from "@tanstack/react-query";

// Mock data until we connect to the backend
const mockData = [
  { name: "Jan", instagram: 400, facebook: 240, twitter: 320 },
  { name: "Feb", instagram: 300, facebook: 139, twitter: 220 },
  { name: "Mar", instagram: 200, facebook: 980, twitter: 420 },
  { name: "Apr", instagram: 278, facebook: 390, twitter: 520 },
  { name: "May", instagram: 189, facebook: 480, twitter: 380 },
];

const hours = Array.from({ length: 24 }, (_, i) => i);
const days = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

function generateHeatmapData() {
  return days.map(day => ({
    day,
    ...Object.fromEntries(
      hours.map(hour => [
        `${hour}`,
        Math.floor(Math.random() * 100)  // Random engagement score for now
      ])
    )
  }));
}

function Heatmap({ data, platform }: { data: any[]; platform: string }) {
  const maxValue = useMemo(() => {
    return Math.max(...data.flatMap(row => 
      hours.map(hour => row[hour.toString()])
    ));
  }, [data]);

  return (
    <div className="w-full h-[300px] mt-4">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart
          data={data}
          margin={{ top: 20, right: 30, left: 50, bottom: 20 }}
        >
          <XAxis
            dataKey="day"
            type="category"
            interval={0}
            tick={{ fontSize: 12 }}
          />
          <YAxis
            type="category"
            data={hours}
            interval={0}
            tick={{ fontSize: 12 }}
            width={30}
          />
          <Tooltip
            content={({ active, payload }) => {
              if (!active || !payload?.[0]) return null;
              const data = payload[0].payload;
              const hour = payload[0].name;
              const value = data[hour];
              return (
                <div className="bg-background border p-2 rounded-md shadow-md">
                  <p className="text-sm font-medium">
                    {`${data.day} ${hour}:00`}
                  </p>
                  <p className="text-sm text-muted-foreground">
                    {`Engagement: ${value}%`}
                  </p>
                </div>
              );
            }}
          />
          {data.map((entry, index) => (
            hours.map(hour => (
              <Rectangle
                key={`${index}-${hour}`}
                x={index * (100 / 7)}
                y={hour * (250 / 24)}
                width={100 / 7}
                height={250 / 24}
                fill={`hsl(${platforms.find(p => p.id === platform)?.color || '#000'} / ${(entry[hour] / maxValue) * 100}%)`}
              />
            ))
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

export default function Analytics() {
  const { data: analyticsData } = useQuery({
    queryKey: ["/api/analytics"],
  });

  const heatmapData = useMemo(() => generateHeatmapData(), []);

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

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {platforms.map(platform => (
          <Card key={platform.id}>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <platform.icon className="w-5 h-5" style={{ color: platform.color }} />
                {platform.name} Engagement Heatmap
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground mb-4">
                Optimal posting times based on historical engagement
              </p>
              <Heatmap data={heatmapData} platform={platform.id} />
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}