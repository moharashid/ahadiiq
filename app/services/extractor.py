from abc import ABC, abstractmethod
from app.core.config import settings
import logging
import anthropic
import json
logger = logging.getLogger(__name__)

PROMPT = '''

You are a contract analysis system. Extract structured data from the contract below.

Return ONLY a valid JSON object with this exact structure, and nothing else:

{
  "agreement_type": "lease | employment | vendor | service | other",
  "parties": [
    {"name": "string", "role": "string", "address": "string or null", "phone": "string or null"}
  ],
  "signatories": [
    {"name": "string", "title": "string or null", "date_signed": "YYYY-MM-DD or null"}
  ],
  "effective_date": "YYYY-MM-DD or null",
  "expiry_date": "YYYY-MM-DD or null",
  "term": "string or null",
  "clauses": [
    {
      "type": "renewal | termination | payment | penalty | notice | other",
      "text": "the exact clause language from the contract",
      "notice_period_days": "integer or null",
      "relative_to": "expiry_date | effective_date | null",
      "amount": "number or null"
    }
  ]
}

Rules:
- Return only the JSON. No markdown fences (no ```json at the beginning or end or even ``` at the end, should just start with the JSON object), no commentary. VERY IMPORTANT: The JSON must be valid. Do not include any extra text or commentary.
- Use null for any field not present in the contract.
- For clause "text", quote the actual contract language.
- Classify each clause type from the allowed list only.
- All string values must be valid JSON. Escape any double quotes inside text with a backslash, or rephrase to avoid them.

Contract:
'''

class AIExtractor(ABC):
    @abstractmethod
    def extract(self, text: str):
        pass
    def _parse_json(self, text: str):
      text = text.strip()
      text =  text.replace("```json", "").replace("```", "")
      try:
        parsed = json.loads(text)
        return parsed
      except Exception as e:
        logger.error(f"Failed to parse JSON: {e}")
        return None
    
class AnthropicExtractor(AIExtractor):
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = anthropic.Anthropic(api_key=self.api_key)
    def extract(self, text: str):
        full_prompt = PROMPT + text
        response = self.client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=4096,
            messages=[{"role": "user", "content": full_prompt}]
        )
        result = super()._parse_json(response.content[0].text)
        if result is None:
            logger.error("Failed to parse JSON from AI response.")
            raise ValueError("Failed to parse JSON from AI response.")
        return result
      
    
         
    

anthropic_extractor = AnthropicExtractor(api_key=settings.ANTHROPIC_API_KEY)