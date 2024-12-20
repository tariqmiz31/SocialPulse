# Implementation Guide

## 1. A/B Testing Suggester Service

```python
# app/services/ab_test_suggester.py

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
                model="gpt-4o",  # the newest OpenAI model
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
```

## 2. Internationalization Configuration

### Flask Configuration (app.py)
```python
from flask import Flask, jsonify, request, session
from flask_babel import Babel, gettext

app = Flask(__name__)
babel = Babel(app)

# Supported languages
LANGUAGES = {
    'en': 'English',
    'ar': 'العربية'
}

@babel.localeselector
def get_locale():
    # Try to get the language from the session
    if session.get('lang'):
        return session.get('lang')
    # Otherwise try to guess the language from the user accept header
    return request.accept_languages.best_match(LANGUAGES.keys())

app.config['BABEL_DEFAULT_LOCALE'] = 'en'
app.config['LANGUAGES'] = LANGUAGES
```

### Babel Configuration (babel.cfg)
```ini
[python: **.py]
encoding = utf-8

[jinja2: **/templates/**.html]
encoding = utf-8
extensions=jinja2.ext.autoescape,jinja2.ext.with_
```

## 3. Translation Files

### Arabic Translations (translations/ar/LC_MESSAGES/messages.po)
```po
# Arabic translations for the Social Hub application.
msgid ""
msgstr ""
"Project-Id-Version: 1.0\n"
"POT-Creation-Date: 2024-12-20 10:00+0000\n"
"Content-Type: text/plain; charset=UTF-8\n"
"Content-Transfer-Encoding: 8bit\n"
"Generated-By: Babel 2.9.1\n"

msgid "Post retrieved successfully"
msgstr "تم استرداد المنشور بنجاح"

msgid "Failed to fetch posts"
msgstr "فشل في جلب المنشورات"

msgid "Post created successfully"
msgstr "تم إنشاء المنشور بنجاح"

# Add more translations as needed
```

## 4. API Routes

```python
# Language API route
@app.route('/api/language', methods=['GET', 'POST'])
def language():
    if request.method == 'POST':
        lang = request.json.get('lang')
        if lang and lang in LANGUAGES:
            session['lang'] = lang
            return jsonify({'status': 'success', 'lang': lang})
        return jsonify({'status': 'error', 'message': 'Invalid language'}), 400

    return jsonify({
        'current': session.get('lang', get_locale()),
        'available': LANGUAGES
    })

# A/B Testing API route
@app.route('/api/ab-test-suggestions', methods=['POST'])
def get_ab_test_suggestions():
    try:
        data = request.get_json()
        logger.info(f"Generating A/B test suggestions for platform: {data.get('platform')}")

        suggester = ABTestSuggester()
        result = suggester.generate_test_suggestions(
            content=data.get('content', ''),
            platform=data.get('platform', 'instagram'),
            content_type=data.get('content_type', 'general')
        )

        logger.info("A/B test suggestions generated successfully")
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error generating A/B test suggestions: {str(e)}")
        return jsonify({"error": gettext('Failed to generate A/B test suggestions')}), 500
```

## Setup Instructions

1. Install required packages:
```bash
pip install flask-babel babel
```

2. Initialize the database and create tables:
```python
with app.app_context():
    db.create_all()
```

3. Compile translations:
```bash
pybabel compile -d translations
```

4. Run the application:
```python
app.run(host='0.0.0.0', port=5000)
```
