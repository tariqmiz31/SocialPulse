import os
import requests
from typing import Dict, List, Optional
from datetime import datetime

class SocialMediaService:
    def __init__(self):
        # Initialize platform-specific API clients
        self.platform_configs = {
            'twitter': {
                'api_base': 'https://api.twitter.com/2',
                'client_id': os.getenv('TWITTER_CLIENT_ID'),
                'client_secret': os.getenv('TWITTER_CLIENT_SECRET')
            },
            'instagram': {
                'api_base': 'https://graph.instagram.com/v12.0',
                'client_id': os.getenv('INSTAGRAM_CLIENT_ID'),
                'client_secret': os.getenv('INSTAGRAM_CLIENT_SECRET')
            },
            'facebook': {
                'api_base': 'https://graph.facebook.com/v12.0',
                'client_id': os.getenv('FACEBOOK_CLIENT_ID'),
                'client_secret': os.getenv('FACEBOOK_CLIENT_SECRET')
            },
            'tiktok': {
                'api_base': 'https://open-api.tiktok.com/v2',
                'client_id': os.getenv('TIKTOK_CLIENT_ID'),
                'client_secret': os.getenv('TIKTOK_CLIENT_SECRET')
            },
            'youtube': {
                'api_base': 'https://www.googleapis.com/youtube/v3',
                'client_id': os.getenv('YOUTUBE_CLIENT_ID'),
                'client_secret': os.getenv('YOUTUBE_CLIENT_SECRET')
            },
            'snapchat': {
                'api_base': 'https://adsapi.snapchat.com/v1',
                'client_id': os.getenv('SNAPCHAT_CLIENT_ID'),
                'client_secret': os.getenv('SNAPCHAT_CLIENT_SECRET')
            },
            'pinterest': {
                'api_base': 'https://api.pinterest.com/v5',
                'client_id': os.getenv('PINTEREST_CLIENT_ID'),
                'client_secret': os.getenv('PINTEREST_CLIENT_SECRET')
            }
        }

    def get_oauth_url(self, platform: str) -> str:
        """Generate OAuth URL for platform authentication"""
        config = self.platform_configs.get(platform)
        if not config:
            raise ValueError(f"Unsupported platform: {platform}")

        oauth_urls = {
            'twitter': f"https://twitter.com/i/oauth2/authorize?client_id={config['client_id']}&response_type=code&scope=tweet.read+tweet.write+users.read&redirect_uri={os.getenv('APP_URL')}/api/auth/twitter/callback",
            'instagram': f"https://api.instagram.com/oauth/authorize?client_id={config['client_id']}&redirect_uri={os.getenv('APP_URL')}/api/auth/instagram/callback&scope=basic&response_type=code",
            'facebook': f"https://www.facebook.com/v12.0/dialog/oauth?client_id={config['client_id']}&redirect_uri={os.getenv('APP_URL')}/api/auth/facebook/callback&scope=pages_show_list,pages_read_engagement,pages_manage_posts",
            'tiktok': f"https://www.tiktok.com/auth/authorize?client_key={config['client_id']}&redirect_uri={os.getenv('APP_URL')}/api/auth/tiktok/callback&scope=user.info.basic,video.publish&response_type=code",
            'youtube': f"https://accounts.google.com/o/oauth2/v2/auth?client_id={config['client_id']}&redirect_uri={os.getenv('APP_URL')}/api/auth/youtube/callback&scope=https://www.googleapis.com/auth/youtube.upload&response_type=code&access_type=offline",
            'snapchat': f"https://accounts.snapchat.com/login/oauth2/authorize?client_id={config['client_id']}&redirect_uri={os.getenv('APP_URL')}/api/auth/snapchat/callback&response_type=code&scope=snapchat-marketing-api",
            'pinterest': f"https://www.pinterest.com/oauth/?client_id={config['client_id']}&redirect_uri={os.getenv('APP_URL')}/api/auth/pinterest/callback&response_type=code&scope=boards:read,pins:read,pins:write"
        }

        return oauth_urls.get(platform)

    async def handle_oauth_callback(self, platform: str, code: str) -> Dict:
        """Handle OAuth callback and token exchange"""
        config = self.platform_configs.get(platform)
        if not config:
            raise ValueError(f"Unsupported platform: {platform}")

        token_urls = {
            'twitter': 'https://api.twitter.com/2/oauth2/token',
            'instagram': 'https://api.instagram.com/oauth/access_token',
            'facebook': 'https://graph.facebook.com/v12.0/oauth/access_token',
            'tiktok': 'https://open-api.tiktok.com/oauth/access_token/',
            'youtube': 'https://oauth2.googleapis.com/token',
            'snapchat': 'https://accounts.snapchat.com/login/oauth2/access_token',
            'pinterest': 'https://api.pinterest.com/v5/oauth/token'
        }

        data = {
            'client_id': config['client_id'],
            'client_secret': config['client_secret'],
            'code': code,
            'redirect_uri': f"{os.getenv('APP_URL')}/api/auth/{platform}/callback",
            'grant_type': 'authorization_code'
        }

        response = requests.post(token_urls[platform], data=data)
        response.raise_for_status()
        return response.json()

    async def publish_content(self, platform: str, content: str, media_urls: Optional[List[str]] = None, access_token: str = None) -> Dict:
        """Publish content to specified platform"""
        if not access_token:
            raise ValueError("Access token is required")

        platform_publishers = {
            'twitter': self._publish_to_twitter,
            'instagram': self._publish_to_instagram,
            'facebook': self._publish_to_facebook,
            'tiktok': self._publish_to_tiktok,
            'youtube': self._publish_to_youtube,
            'snapchat': self._publish_to_snapchat,
            'pinterest': self._publish_to_pinterest
        }

        publisher = platform_publishers.get(platform)
        if not publisher:
            raise ValueError(f"Unsupported platform: {platform}")

        return await publisher(content, media_urls, access_token)

    async def _publish_to_twitter(self, content: str, media_urls: Optional[List[str]], access_token: str) -> Dict:
        """Publish to Twitter"""
        headers = {'Authorization': f'Bearer {access_token}'}
        data = {'text': content}

        if media_urls:
            # First upload media
            media_ids = []
            for url in media_urls:
                media_response = requests.post(
                    f"{self.platform_configs['twitter']['api_base']}/media/upload",
                    headers=headers,
                    files={'media': requests.get(url).content}
                )
                media_response.raise_for_status()
                media_ids.append(media_response.json()['media_id'])
            data['media'] = {'media_ids': media_ids}

        response = requests.post(
            f"{self.platform_configs['twitter']['api_base']}/tweets",
            headers=headers,
            json=data
        )
        response.raise_for_status()
        return response.json()

    # Similar implementation for other platforms...
    async def _publish_to_instagram(self, content: str, media_urls: Optional[List[str]], access_token: str) -> Dict:
        """Publish to Instagram"""
        try:
            if not media_urls:
                raise ValueError("Instagram requires at least one media file")
            if not access_token:
                raise ValueError("Access token is required")

            headers = {'Authorization': f'Bearer {access_token}'}
            
            # Create a container
            try:
                container_response = requests.post(
                    f"{self.platform_configs['instagram']['api_base']}/media",
                    headers=headers,
                    data={
                        'image_url': media_urls[0],
                        'caption': content
                    }
                )
                container_response.raise_for_status()
                container_id = container_response.json().get('id')
                if not container_id:
                    raise ValueError("Failed to get container ID from response")

                # Publish the container
                publish_response = requests.post(
                    f"{self.platform_configs['instagram']['api_base']}/media_publish",
                    headers=headers,
                    data={'creation_id': container_id}
                )
                publish_response.raise_for_status()
                return publish_response.json()
            except requests.exceptions.RequestException as e:
                raise ValueError(f"Instagram API error: {str(e)}")
        except Exception as e:
            raise ValueError(f"Failed to publish to Instagram: {str(e)}")

    # Implement other platform publishing methods similarly
