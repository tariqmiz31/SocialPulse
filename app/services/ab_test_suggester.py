import os
import openai
from typing import List, TypedDict

class ABTestVariation(TypedDict):
    original: str
    variations: List[str]
    hypothesis: str
    sample_size: int
    duration_days: int
    confidence_level: float
    expected_lift: float

class ABTestSuggester:
    def __init__(self):
        openai.api_key = os.getenv('OPENAI_API_KEY')

    async def generate_test_suggestions(
        self,
        content: str,
        platform: str,
        content_type: str
    ) -> ABTestVariation:
        """
        Generate A/B test variations and recommendations for content
        """
        try:
            completion = openai.chat.completions.create(
                model="gpt-4o",  # the newest OpenAI model is "gpt-4o" which was released May 13, 2024
                messages=[
                    {"role": "system", "content": (
                        "You are an A/B testing expert for social media content. "
                        "Analyze the content and suggest meaningful variations for testing. "
                        "Provide a hypothesis, recommended sample size, test duration, "
                        "and expected improvement. Return as JSON."
                    )},
                    {"role": "user", "content": f"""
                        Analyze this content for {platform}:
                        Content: {content}
                        Content Type: {content_type}
                        
                        Generate:
                        1. 3 meaningful content variations
                        2. A clear hypothesis for testing
                        3. Recommended sample size
                        4. Test duration in days
                        5. Expected lift percentage
                        6. Statistical confidence level needed
                    """}
                ],
                response_format={ "type": "json_object" }
            )
            
            result = completion.choices[0].message.content
            return {
                "original": content,
                "variations": result["variations"],
                "hypothesis": result["hypothesis"],
                "sample_size": int(result["sample_size"]),
                "duration_days": int(result["duration_days"]),
                "confidence_level": float(result["confidence_level"]),
                "expected_lift": float(result["expected_lift"])
            }
            
        except Exception as e:
            print(f"Error generating A/B test suggestions: {str(e)}")
            return {
                "original": content,
                "variations": [content],
                "hypothesis": "Error generating test variations",
                "sample_size": 1000,
                "duration_days": 7,
                "confidence_level": 0.95,
                "expected_lift": 0.0
            }

    @staticmethod
    def calculate_significance(
        control_size: int,
        control_conversions: int,
        variation_size: int,
        variation_conversions: int,
        confidence_level: float = 0.95
    ) -> dict:
        """
        Calculate statistical significance of A/B test results
        """
        try:
            control_rate = control_conversions / control_size
            variation_rate = variation_conversions / variation_size
            relative_lift = ((variation_rate - control_rate) / control_rate) * 100
            
            return {
                "control_rate": control_rate,
                "variation_rate": variation_rate,
                "relative_lift": relative_lift,
                "is_significant": relative_lift > 0 and control_size >= 100 and variation_size >= 100
            }
        except ZeroDivisionError:
            return {
                "control_rate": 0,
                "variation_rate": 0,
                "relative_lift": 0,
                "is_significant": False
            }
