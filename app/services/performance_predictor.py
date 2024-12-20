import os
import openai
from typing import Dict, List, TypedDict

class PerformanceMetrics(TypedDict):
    predicted_engagement: float
    predicted_reach: int
    best_posting_time: str
    content_score: float
    improvement_suggestions: List[str]

class PerformancePredictor:
    def __init__(self):
        openai.api_key = os.getenv('OPENAI_API_KEY')

    @staticmethod
    def _get_platform_characteristics() -> Dict[str, Dict]:
        return {
            "instagram": {
                "optimal_length": (80, 150),
                "hashtag_limit": 30,
                "best_content_types": ["visual", "lifestyle", "behind-the-scenes"],
            },
            "facebook": {
                "optimal_length": (100, 250),
                "hashtag_limit": 3,
                "best_content_types": ["videos", "questions", "long-form"],
            },
            "twitter": {
                "optimal_length": (100, 280),
                "hashtag_limit": 2,
                "best_content_types": ["news", "opinions", "threads"],
            },
            "tiktok": {
                "optimal_length": (50, 150),
                "hashtag_limit": 5,
                "best_content_types": ["trending", "entertainment", "tutorials"],
            },
            "youtube": {
                "optimal_length": (200, 500),
                "hashtag_limit": 15,
                "best_content_types": ["educational", "entertainment", "vlogs"],
            },
            "pinterest": {
                "optimal_length": (100, 200),
                "hashtag_limit": 20,
                "best_content_types": ["DIY", "inspirational", "visual"],
            },
            "snapchat": {
                "optimal_length": (50, 100),
                "hashtag_limit": 1,
                "best_content_types": ["raw", "behind-the-scenes", "ephemeral"],
            },
        }

    async def predict_performance(
        self, content: str, platform: str, content_type: str
    ) -> PerformanceMetrics:
        """
        Predict content performance using OpenAI's GPT-4
        """
        platform_info = self._get_platform_characteristics().get(platform, {})
        
        try:
            completion = openai.chat.completions.create(
                model="gpt-4o",  # the newest OpenAI model is "gpt-4o" which was released May 13, 2024
                messages=[
                    {"role": "system", "content": (
                        "You are a social media analytics expert. Analyze the content and predict its performance. "
                        "Provide specific metrics and actionable suggestions. "
                        "Return a JSON object with numerical predictions and string arrays for suggestions."
                    )},
                    {"role": "user", "content": f"""
                        Analyze this content for {platform}:
                        Content: {content}
                        Content Type: {content_type}
                        Platform Characteristics: {platform_info}
                        
                        Predict:
                        1. Engagement rate (0-100%)
                        2. Estimated reach
                        3. Best posting time (in format HH:MM)
                        4. Content quality score (0-10)
                        5. List of specific improvement suggestions
                    """}
                ],
                response_format={ "type": "json_object" }
            )
            
            result = completion.choices[0].message.content
            return {
                "predicted_engagement": float(result["engagement_rate"]),
                "predicted_reach": int(result["estimated_reach"]),
                "best_posting_time": result["best_posting_time"],
                "content_score": float(result["content_score"]),
                "improvement_suggestions": result["improvement_suggestions"]
            }
            
        except Exception as e:
            print(f"Error predicting performance: {str(e)}")
            return {
                "predicted_engagement": 0.0,
                "predicted_reach": 0,
                "best_posting_time": "12:00",
                "content_score": 0.0,
                "improvement_suggestions": ["Error analyzing content"]
            }
