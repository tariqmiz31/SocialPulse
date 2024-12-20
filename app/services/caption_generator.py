import os
import openai

class CaptionGenerator:
    def __init__(self):
        openai.api_key = os.getenv('OPENAI_API_KEY')

    @staticmethod
    def generate_caption(content_type: str, target_platform: str) -> dict:
        """
        Generate social media captions using OpenAI's GPT model
        
        Args:
            content_type: Type of content (e.g., 'product', 'lifestyle', 'announcement')
            target_platform: Target social media platform
            
        Returns:
            dict: Generated caption with emoji suggestions
        """
        try:
            completion = openai.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": (
                        "You are a social media expert specializing in creating engaging captions. "
                        "Generate a caption with appropriate emojis for the specified platform. "
                        "Return a JSON object with 'caption' and 'emojis' fields."
                    )},
                    {"role": "user", "content": (
                        f"Create an engaging {target_platform} caption for a {content_type} post. "
                        "Include relevant emoji suggestions."
                    )}
                ],
                response_format={ "type": "json_object" }
            )
            
            return completion.choices[0].message.content
            
        except Exception as e:
            print(f"Error generating caption: {str(e)}")
            return {
                "caption": "Failed to generate caption",
                "emojis": []
            }

    @staticmethod
    def get_content_types():
        """Return available content types for caption generation"""
        return [
            "product", "lifestyle", "announcement", "behind_the_scenes",
            "user_generated", "educational", "promotional"
        ]
