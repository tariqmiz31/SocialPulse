import { Button } from "@/components/ui/button";
import { platforms } from "@/lib/platforms";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";

export function PlatformSelector() {
  return (
    <div className="space-y-4">
      {platforms.map(platform => (
        <div
          key={platform.id}
          className="flex items-center justify-between p-4 rounded-lg border"
        >
          <div className="flex items-center gap-3">
            <platform.icon className="w-6 h-6" style={{ color: platform.color }} />
            <div>
              <p className="font-medium">{platform.name}</p>
              <p className="text-sm text-muted-foreground">Connected as @username</p>
            </div>
          </div>
          
          <div className="flex items-center gap-4">
            <Switch id={`${platform.id}-switch`} />
            <Button variant="outline" size="sm">
              Disconnect
            </Button>
          </div>
        </div>
      ))}
    </div>
  );
}
