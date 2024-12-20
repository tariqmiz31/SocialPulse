import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { useMutation } from "@tanstack/react-query";
import { platforms } from "@/lib/platforms";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import { Card } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

export function ContentCreator() {
  const [content, setContent] = useState("");
  const [selectedPlatforms, setSelectedPlatforms] = useState<string[]>([]);
  const [repurposedContent, setRepurposedContent] = useState<Record<string, string>>({});

  const createPost = useMutation({
    mutationFn: async (data: { content: string; platforms: string[] }) => {
      const res = await fetch("/api/posts", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      });
      if (!res.ok) throw new Error("Failed to create post");
      return res.json();
    },
  });

  const handleRepurpose = async () => {
    if (!content.trim() || selectedPlatforms.length === 0) return;

    try {
      const response = await fetch("/api/repurpose", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          content,
          platforms: selectedPlatforms,
        }),
      });

      if (!response.ok) throw new Error("Failed to repurpose content");

      const repurposed = await response.json();
      setRepurposedContent(repurposed);
    } catch (error) {
      console.error("Error repurposing content:", error);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!content.trim()) return;

    createPost.mutate({
      content,
      platforms: selectedPlatforms,
    });
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <Label>Content</Label>
        <Textarea
          value={content}
          onChange={(e) => setContent(e.target.value)}
          placeholder="Write your post content..."
          className="h-32"
        />
      </div>

      <div className="space-y-2">
        <Label>Platforms</Label>
        <div className="grid grid-cols-2 gap-4">
          {platforms.map(platform => (
            <div key={platform.id} className="flex items-center space-x-2">
              <Checkbox
                id={platform.id}
                checked={selectedPlatforms.includes(platform.id)}
                onCheckedChange={(checked) => {
                  setSelectedPlatforms(prev => 
                    checked 
                      ? [...prev, platform.id]
                      : prev.filter(id => id !== platform.id)
                  );
                }}
              />
              <Label htmlFor={platform.id} className="flex items-center gap-2">
                <platform.icon className="w-4 h-4" style={{ color: platform.color }} />
                {platform.name}
              </Label>
            </div>
          ))}
        </div>
      </div>

      <div className="flex gap-2">
        <Button 
          type="button" 
          variant="outline" 
          className="flex-1"
          onClick={handleRepurpose}
          disabled={!content.trim() || selectedPlatforms.length === 0}
        >
          Preview Repurposed Content
        </Button>
        <Button 
          type="submit" 
          className="flex-1"
          disabled={!content.trim() || selectedPlatforms.length === 0}
        >
          Schedule Posts
        </Button>
      </div>

      {Object.keys(repurposedContent).length > 0 && (
        <div className="mt-6">
          <Label>Preview Repurposed Content</Label>
          <Tabs defaultValue={selectedPlatforms[0]} className="mt-2">
            <TabsList>
              {selectedPlatforms.map(platformId => (
                <TabsTrigger key={platformId} value={platformId}>
                  {platforms.find(p => p.id === platformId)?.name}
                </TabsTrigger>
              ))}
            </TabsList>
            {selectedPlatforms.map(platformId => (
              <TabsContent key={platformId} value={platformId}>
                <Card className="p-4">
                  <pre className="whitespace-pre-wrap font-sans">
                    {repurposedContent[platformId]}
                  </pre>
                </Card>
              </TabsContent>
            ))}
          </Tabs>
        </div>
      )}
    </form>
  );
}