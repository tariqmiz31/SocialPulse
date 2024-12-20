import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ContentCreator } from "@/components/ContentCreator";
import { PlatformSelector } from "@/components/PlatformSelector";
import { platforms } from "@/lib/platforms";

export default function Dashboard() {
  return (
    <div className="container mx-auto p-6 space-y-6">
      <h1 className="text-3xl font-bold">Content Dashboard</h1>
      
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {platforms.map(platform => (
          <Card key={platform.id}>
            <CardHeader className="flex flex-row items-center space-x-4">
              <platform.icon className="w-8 h-8" style={{ color: platform.color }} />
              <CardTitle>{platform.name}</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-2xl font-bold">{platform.stats.posts}</p>
              <p className="text-muted-foreground">Posts this month</p>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div>
          <h2 className="text-2xl font-bold mb-4">Create Content</h2>
          <Card>
            <CardContent className="p-6">
              <ContentCreator />
            </CardContent>
          </Card>
        </div>
        
        <div>
          <h2 className="text-2xl font-bold mb-4">Connected Platforms</h2>
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
