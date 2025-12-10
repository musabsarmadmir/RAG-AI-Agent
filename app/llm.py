import os
import logging
from typing import List

logger = logging.getLogger(__name__)


def call_llm_strict(question: str, context: str) -> str:
    """Call OpenAI chat LLM with strict grounding instruction. If no OPENAI_KEY, return 'Not available.'

    Supports both the new `openai.OpenAI()` client API and older `openai.ChatCompletion.create`.
    """
    # Read env at call time to pick up keys loaded after import (e.g., via dotenv)
    OPENAI_KEY = os.environ.get('OPENAI_API_KEY')
    if not OPENAI_KEY:
        return 'Not available.'
    try:
        import openai
        # Try new OpenAI client first
        client = None
        try:
            # Respect environment override for LLM model name
            # default model configured in app.config as LLM_MODEL
            from .config import LLM_MODEL
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
            # new client API - use configured model
            model_name = os.environ.get('LLM_MODEL') or 'gpt-4o-mini'
            resp = client.chat.completions.create(model=model_name, messages=messages, max_tokens=512)
            # resp.choices[0].message.content or dict style
            choice = resp.choices[0]
            msg = getattr(choice, 'message', None)
            if msg is not None:
                content = getattr(msg, 'content', None)
            else:
                content = choice.get('message', {}).get('content') if isinstance(choice, dict) else str(choice)
            return (content or '').strip()

        # fallback to older openai library interface
        model_name = os.environ.get('LLM_MODEL') or 'gpt-4o-mini'
        resp = openai.ChatCompletion.create(model=model_name, messages=messages, max_tokens=512)
        return resp['choices'][0]['message']['content'].strip()
    except Exception:
        logger.exception('LLM call failed')
        return 'Not available.'


def call_llm_chat(message: str, context: str | None = None) -> str:
    """General-purpose chat that can converse naturally.

    If context is provided, it may be referenced, but the assistant is not restricted
    to only the context. If no OPENAI key, return a simple canned response.
    """
    OPENAI_KEY = os.environ.get('OPENAI_API_KEY')
    if not OPENAI_KEY:
        # Simple canned response when no key is available
        return "Hi! I'm here to help. Ask me anything about the provider or services."
    try:
        import openai
        client = None
        try:
            client = openai.OpenAI(api_key=OPENAI_KEY)
        except Exception:
            try:
                openai.api_key = OPENAI_KEY
            except Exception:
                pass

        system = (
            "You are a friendly AI assistant. Be conversational, clear, and helpful. "
            "If the user asks about provider-specific info and you have context, use it; "
            "otherwise answer normally. Avoid making up facts about specific documents if uncertain."
        )
        user_content = message if context is None else f"Context (optional):\n{context}\n\nUser: {message}"
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user_content},
        ]

        if client is not None:
            model_name = os.environ.get('LLM_MODEL') or 'gpt-4o-mini'
            resp = client.chat.completions.create(model=model_name, messages=messages, max_tokens=512)
            choice = resp.choices[0]
            msg = getattr(choice, 'message', None)
            if msg is not None:
                content = getattr(msg, 'content', None)
            else:
                content = choice.get('message', {}).get('content') if isinstance(choice, dict) else str(choice)
            return (content or '').strip()

        model_name = os.environ.get('LLM_MODEL') or 'gpt-4o-mini'
        resp = openai.ChatCompletion.create(model=model_name, messages=messages, max_tokens=512)
        return resp['choices'][0]['message']['content'].strip()
    except Exception:
        logger.exception('LLM chat call failed')
        return "Sorry, I'm having trouble responding right now."
