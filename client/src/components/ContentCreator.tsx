import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { useMutation } from "@tanstack/react-query";
import { platforms } from "@/lib/platforms";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import { Card } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Sparkles, PieChart } from "lucide-react";

export function ContentCreator() {
  const [content, setContent] = useState("");
  const [selectedPlatforms, setSelectedPlatforms] = useState<string[]>([]);
  const [repurposedContent, setRepurposedContent] = useState<Record<string, string>>({});
  const [contentType, setContentType] = useState("general");
  const [generatedCaption, setGeneratedCaption] = useState<{
    caption: string;
    emojis: string[];
  } | null>(null);
  const [predictions, setPredictions] = useState<Record<string, {
    predicted_engagement: number;
    predicted_reach: number;
    best_posting_time: string;
    content_score: number;
    improvement_suggestions: string[];
  }>>({});

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

      // After repurposing, get predictions for each platform
      const predictionsPromises = selectedPlatforms.map(async (platform) => {
        const predictionResponse = await fetch("/api/predict-performance", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            content: repurposed[platform],
            platform,
            content_type: contentType,
          }),
        });

        if (!predictionResponse.ok) throw new Error(`Failed to get prediction for ${platform}`);

        const prediction = await predictionResponse.json();
        return [platform, prediction];
      });

      const predictionsResults = await Promise.all(predictionsPromises);
      setPredictions(Object.fromEntries(predictionsResults));
    } catch (error) {
      console.error("Error repurposing content:", error);
    }
  };

  const handleGenerateCaption = async () => {
    if (!selectedPlatforms[0]) return;

    try {
      const response = await fetch("/api/generate-caption", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          content_type: contentType,
          platform: selectedPlatforms[0],
        }),
      });

      if (!response.ok) throw new Error("Failed to generate caption");

      const result = await response.json();
      setGeneratedCaption(result);
      setContent(result.caption);
    } catch (error) {
      console.error("Error generating caption:", error);
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
      <div className="flex items-end gap-4">
        <div className="flex-1">
          <Label>Content Type</Label>
          <Select value={contentType} onValueChange={setContentType}>
            <SelectTrigger>
              <SelectValue placeholder="Select content type" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="general">General</SelectItem>
              <SelectItem value="product">Product</SelectItem>
              <SelectItem value="lifestyle">Lifestyle</SelectItem>
              <SelectItem value="announcement">Announcement</SelectItem>
              <SelectItem value="behind_the_scenes">Behind the Scenes</SelectItem>
              <SelectItem value="educational">Educational</SelectItem>
              <SelectItem value="promotional">Promotional</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <Button
          type="button"
          variant="outline"
          onClick={handleGenerateCaption}
          disabled={selectedPlatforms.length === 0}
          className="flex items-center gap-2"
        >
          <Sparkles className="w-4 h-4" />
          Generate AI Caption
        </Button>
      </div>

      <div>
        <Label>Content</Label>
        <Textarea
          value={content}
          onChange={(e) => setContent(e.target.value)}
          placeholder="Write your post content..."
          className="h-32"
        />
      </div>

      {generatedCaption?.emojis.length > 0 && (
        <div className="p-3 bg-muted rounded-md">
          <Label className="mb-2 block">Suggested Emojis</Label>
          <div className="flex flex-wrap gap-2">
            {generatedCaption.emojis.map((emoji, index) => (
              <button
                key={index}
                type="button"
                onClick={() => setContent(prev => prev + emoji)}
                className="text-xl hover:bg-accent p-1 rounded"
              >
                {emoji}
              </button>
            ))}
          </div>
        </div>
      )}

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
          <PieChart className="w-4 h-4 mr-2" />
          Analyze & Preview Content
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
        <div className="mt-6 space-y-6">
          <Label>Content Analysis & Preview</Label>
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
                <div className="space-y-4">
                  {predictions[platformId] && (
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                      <Card className="p-4">
                        <p className="text-sm text-muted-foreground">Engagement</p>
                        <p className="text-2xl font-bold">
                          {predictions[platformId].predicted_engagement.toFixed(1)}%
                        </p>
                      </Card>
                      <Card className="p-4">
                        <p className="text-sm text-muted-foreground">Estimated Reach</p>
                        <p className="text-2xl font-bold">
                          {predictions[platformId].predicted_reach.toLocaleString()}
                        </p>
                      </Card>
                      <Card className="p-4">
                        <p className="text-sm text-muted-foreground">Best Time</p>
                        <p className="text-2xl font-bold">
                          {predictions[platformId].best_posting_time}
                        </p>
                      </Card>
                      <Card className="p-4">
                        <p className="text-sm text-muted-foreground">Content Score</p>
                        <p className="text-2xl font-bold">
                          {predictions[platformId].content_score.toFixed(1)}/10
                        </p>
                      </Card>
                    </div>
                  )}

                  {predictions[platformId]?.improvement_suggestions.length > 0 && (
                    <Card className="p-4">
                      <p className="font-medium mb-2">Suggestions for Improvement</p>
                      <ul className="list-disc pl-5 space-y-1">
                        {predictions[platformId].improvement_suggestions.map((suggestion, index) => (
                          <li key={index} className="text-sm text-muted-foreground">
                            {suggestion}
                          </li>
                        ))}
                      </ul>
                    </Card>
                  )}

                  <Card className="p-4">
                    <p className="font-medium mb-2">Preview Content</p>
                    <pre className="whitespace-pre-wrap font-sans text-sm text-muted-foreground">
                      {repurposedContent[platformId]}
                    </pre>
                  </Card>
                </div>
              </TabsContent>
            ))}
          </Tabs>
        </div>
      )}
    </form>
  );
}