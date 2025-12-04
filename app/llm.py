import os
import logging
from typing import List

OPENAI_KEY = os.environ.get('OPENAI_API_KEY')
logger = logging.getLogger(__name__)


def call_llm_strict(question: str, context: str) -> str:
    """Call OpenAI chat LLM with strict grounding instruction. If no OPENAI_KEY, return 'Not available.'

    Supports both the new `openai.OpenAI()` client API and older `openai.ChatCompletion.create`.
    """
    if not OPENAI_KEY:
        return 'Not available.'
    try:
        import openai
        # Try new OpenAI client first
        client = None
        try:
            client = openai.OpenAI(api_key=OPENAI_KEY)
        except Exception:
            try:
                openai.api_key = OPENAI_KEY
            except Exception:
                pass

        system = (
            "You are a helpful assistant. Use only the provided context to answer. "
            "If information is missing, respond: 'Not available.'"
        )
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {question}"},
        ]

        if client is not None:
            # new client API
            resp = client.chat.completions.create(model='gpt-4o-mini', messages=messages, max_tokens=512)
            # resp.choices[0].message.content or dict style
            choice = resp.choices[0]
            msg = getattr(choice, 'message', None)
            if msg is not None:
                content = getattr(msg, 'content', None)
            else:
                content = choice.get('message', {}).get('content') if isinstance(choice, dict) else str(choice)
            return (content or '').strip()

        # fallback to older openai library interface
        resp = openai.ChatCompletion.create(model='gpt-4o-mini', messages=messages, max_tokens=512)
        return resp['choices'][0]['message']['content'].strip()
    except Exception:
        logger.exception('LLM call failed')
        return 'Not available.'
