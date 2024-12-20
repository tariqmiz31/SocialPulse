import { SiInstagram, SiFacebook, SiX, SiTiktok, SiYoutube, SiSnapchat, SiPinterest } from "react-icons/si";
import type { Platform } from "./types";

export const platforms: Platform[] = [
  {
    id: "instagram",
    name: "Instagram",
    icon: SiInstagram,
    color: "#E1306C",
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
    stats: {
      posts: 15,
      engagement: 4.1
    }
  }
];