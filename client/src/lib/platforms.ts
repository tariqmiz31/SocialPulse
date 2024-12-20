import { SiInstagram, SiFacebook, SiX, SiTiktok, SiYoutube, SiSnapchat, SiPinterest } from "react-icons/si";
import type { Platform } from "./types";

export const platforms: Platform[] = [
  {
    id: "instagram",
    name: "Instagram",
    icon: SiInstagram,
    color: "#E1306C",
    contentTypes: [
      { id: "post", name: "Post", description: "Regular photo or carousel post" },
      { id: "story", name: "Story", description: "24-hour visible content" },
      { id: "reel", name: "Reel", description: "Short-form vertical video" }
    ],
    stats: {
      posts: 24,
      engagement: 4.2
    }
  },
  {
    id: "facebook",
    name: "Facebook",
    icon: SiFacebook,
    color: "#1877F2",
    contentTypes: [
      { id: "post", name: "Post", description: "Regular feed post" },
      { id: "story", name: "Story", description: "24-hour visible content" },
      { id: "reel", name: "Reel", description: "Short-form video" }
    ],
    stats: {
      posts: 18,
      engagement: 3.1
    }
  },
  {
    id: "twitter",
    name: "X (Twitter)",
    icon: SiX,
    color: "#000000",
    contentTypes: [
      { id: "tweet", name: "Tweet", description: "Regular text post" },
      { id: "thread", name: "Thread", description: "Connected series of tweets" }
    ],
    stats: {
      posts: 32,
      engagement: 2.8
    }
  },
  {
    id: "pinterest",
    name: "Pinterest",
    icon: SiPinterest,
    color: "#E60023",
    contentTypes: [
      { id: "pin", name: "Pin", description: "Regular pin" },
      { id: "story", name: "Story Pin", description: "Multi-page pin" },
      { id: "idea", name: "Idea Pin", description: "Multi-page creative content" }
    ],
    stats: {
      posts: 20,
      engagement: 4.5
    }
  },
  {
    id: "tiktok",
    name: "TikTok",
    icon: SiTiktok,
    color: "#000000",
    contentTypes: [
      { id: "video", name: "Video", description: "Regular TikTok video" },
      { id: "story", name: "Story", description: "Short-form story content" },
      { id: "live", name: "LIVE", description: "Live streaming" }
    ],
    stats: {
      posts: 12,
      engagement: 5.4
    }
  },
  {
    id: "youtube",
    name: "YouTube",
    icon: SiYoutube,
    color: "#FF0000",
    contentTypes: [
      { id: "video", name: "Video", description: "Regular video" },
      { id: "shorts", name: "Shorts", description: "Short-form vertical video" },
      { id: "live", name: "Live", description: "Live streaming" }
    ],
    stats: {
      posts: 8,
      engagement: 3.7
    }
  },
  {
    id: "snapchat",
    name: "Snapchat",
    icon: SiSnapchat,
    color: "#FFFC00",
    contentTypes: [
      { id: "snap", name: "Snap", description: "Regular snap" },
      { id: "story", name: "Story", description: "24-hour visible content" },
      { id: "spotlight", name: "Spotlight", description: "Featured content" }
    ],
    stats: {
      posts: 15,
      engagement: 4.1
    }
  }
];