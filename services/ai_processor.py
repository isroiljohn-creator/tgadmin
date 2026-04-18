import os
import json
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

genai.configure(api_key=os.getenv("GEMINI_API_KEY", ""))

MODEL_NAME = "gemini-1.5-pro-latest" # Suitable for complex reasoning and rewriting

ASSESSMENT_PROMPT_TEMPLATE = """
Analyze the following Telegram post. 
Determine its language, primary topic, whether it is an advertisement/spam, and rate its overall quality/relevance on a scale of 0.0 to 1.0. 
Low quality means it provides no value, too promotional, short, off-topic, or duplicated clickbait. 
High quality means it provides useful information, insights, news, or value.

Text to analyze:
\"\"\"{text}\"\"\"

Respond EXACTLY as a JSON object, with no markdown formatting or extra text, with the following schema:
{{
  "language": "string",
  "topic": "string",
  "is_spam_or_ad": boolean,
  "relevance_score": float (0.0 to 1.0),
  "reasoning": "string"
}}
"""

REWRITE_PROMPT_TEMPLATE = """
Rewrite the following Telegram post into our brand style.
Never copy the content word for word. Preserve the primary meaning but rewrite it in a fresh, natural way.
Ensure the formatting is clean and readable, using sensible paragraph breaks and emojis where appropriate.

Brand Style / Tone: {tone_style}
Target Language: {target_language}

Original Text:
\"\"\"{text}\"\"\"

Respond EXACTLY as a JSON object, with no markdown formatting or extra text, with the following schema:
{{
  "headline": "A catchy headline for the post (if applicable, else empty sting)",
  "rewritten_text": "The full rewritten post body in the target language and brand tone",
  "cta": "A call to action at the bottom (if applicable)"
}}
"""

async def assess_content(text: str) -> dict:
    """Returns a dictionary with the assessment results."""
    if not os.getenv("GEMINI_API_KEY"):
        # For development without key
        return {
            "language": "Unknown",
            "topic": "Unknown",
            "is_spam_or_ad": False,
            "relevance_score": 0.5,
            "reasoning": "No API key configured."
        }
        
    try:
        model = genai.GenerativeModel(MODEL_NAME)
        prompt = ASSESSMENT_PROMPT_TEMPLATE.format(text=text)
        response = model.generate_content(prompt)
        # Parse JSON
        result_text = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(result_text)
    except Exception as e:
        print(f"Error assessing content: {e}")
        return {"language": "Unknown", "topic": "Unknown", "is_spam_or_ad": False, "relevance_score": 0.0, "reasoning": str(e)}


async def rewrite_content(text: str, tone_style: str, target_language: str) -> dict:
    """Returns a dictionary with the rewritten headline, body, and CTA."""
    if not os.getenv("GEMINI_API_KEY"):
        return {
            "headline": "Fake Headline",
            "rewritten_text": text,
            "cta": "Join us!"
        }
        
    try:
        model = genai.GenerativeModel(MODEL_NAME)
        prompt = REWRITE_PROMPT_TEMPLATE.format(
            text=text, 
            tone_style=tone_style, 
            target_language=target_language
        )
        response = model.generate_content(prompt)
        result_text = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(result_text)
    except Exception as e:
        print(f"Error rewriting content: {e}")
        return {"headline": "", "rewritten_text": text, "cta": ""}

