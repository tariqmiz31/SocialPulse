import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { useMutation } from "@tanstack/react-query";
import { platforms } from "@/lib/platforms";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";

export function ContentCreator() {
  const [content, setContent] = useState("");
  const [selectedPlatforms, setSelectedPlatforms] = useState<string[]>([]);

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

      <Button type="submit" className="w-full">
        Schedule Post
      </Button>
    </form>
  );
}
