import type { IconType } from "react-icons";

export interface Platform {
  id: string;
  name: string;
  icon: IconType;
  color: string;
  stats: {
    posts: number;
    engagement: number;
  };
}

export interface ScheduledPost {
  id: string;
  content: string;
  platforms: string[];
  scheduledFor: Date;
  status: 'scheduled' | 'published' | 'failed';
}
