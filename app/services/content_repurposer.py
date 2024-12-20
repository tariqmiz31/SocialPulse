import re

class ContentRepurposer:
    @staticmethod
    def get_platform_limits():
        return {
            'twitter': {'text': 280, 'hashtags': 5},
            'instagram': {'text': 2200, 'hashtags': 30},
            'facebook': {'text': 63206, 'hashtags': 30},
            'tiktok': {'text': 2200, 'hashtags': 30},
            'youtube': {'text': 5000, 'hashtags': 15},
            'snapchat': {'text': 250, 'hashtags': 1},
            'pinterest': {'text': 500, 'hashtags': 20}
        }

    @staticmethod
    def extract_hashtags(content):
        return re.findall(r'#\w+', content)

    @staticmethod
    def remove_hashtags(content):
        return re.sub(r'#\w+\s*', '', content).strip()

    @staticmethod
    def adapt_for_platform(content, platform):
        limits = ContentRepurposer.get_platform_limits()
        platform_config = limits.get(platform.lower())
        
        if not platform_config:
            return content
            
        hashtags = ContentRepurposer.extract_hashtags(content)
        clean_content = ContentRepurposer.remove_hashtags(content)
        
        # Truncate content if needed
        if len(clean_content) > platform_config['text']:
            clean_content = clean_content[:platform_config['text'] - 3] + '...'
            
        # Limit hashtags
        selected_hashtags = hashtags[:platform_config['hashtags']]
        
        # Combine content and hashtags based on platform
        if platform.lower() == 'twitter':
            # For Twitter, append hashtags inline
            final_content = clean_content + ' ' + ' '.join(selected_hashtags)
            if len(final_content) > platform_config['text']:
                return final_content[:platform_config['text']]
            return final_content
            
        # For other platforms, append hashtags at the end
        return clean_content + '\n\n' + ' '.join(selected_hashtags)

    @staticmethod
    def repurpose_content(content, platforms):
        """
        Repurpose content for multiple platforms
        """
        return {
            platform: ContentRepurposer.adapt_for_platform(content, platform)
            for platform in platforms
        }
