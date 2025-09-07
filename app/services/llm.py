# app/services/llm.py
import json
import os
import time
import re
import logging
from typing import List, Dict, Any

log = logging.getLogger("llm")

try:
    # Official OpenAI 1.x client — with longer timeout & built-in retries
    from openai import OpenAI
    _client = OpenAI(
        timeout=60.0,   # more forgiving network timeout
        max_retries=3,  # let the SDK retry transient failures
    )
    _use_new = True
except Exception:
    # Legacy 0.x fallback
    import openai  # type: ignore
    _client = openai
    _use_new = False

MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

SYSTEM = (
    "You are a rigorous English editor.\n"
    "Fix grammar, clarity, conciseness, and tone.\n"
    "Do NOT change layout, bullets, numbering, or indentation.\n"
    "Do NOT merge or split list items.\n"
    "ONE INPUT SEGMENT = ONE OUTPUT SEGMENT.\n"
    "Return ONLY valid JSON with this exact shape:\n"
    '{"rewrites":[{"index":int,"text":str}]}\n'
    "No prose, no markdown, no extra keys."
)

# grab the last {...} block to be resilient to any prefacing text
_JSON_FENCE = re.compile(r"\{.*\}\s*$", re.DOTALL)


def _extract_json(text: str) -> dict:
    try:
        return json.loads(text)
    except Exception:
        pass
    m = _JSON_FENCE.search(text)
    if m:
        return json.loads(m.group(0))
    raise ValueError("Model output was not valid JSON")


def _chat(messages: list) -> str:
    """Single call to OpenAI Chat Completions."""
    log.info("LLM chat call model=%s, messages=%d", MODEL, len(messages))
    if _use_new:
        # OpenAI 1.x client
        resp = _client.chat.completions.create(model=MODEL, messages=messages)
        return resp.choices[0].message.content or ""
    else:
        # Legacy 0.x fallback
        _client.api_key = os.getenv("OPENAI_API_KEY")
        resp = _client.ChatCompletion.create(model=MODEL, messages=messages)
        return resp["choices"][0]["message"]["content"] or ""


def rewrite_segments_with_gpt(
    segments: List[Dict[str, Any]],
    guidelines: str,
    max_retries: int = 2
) -> List[Dict[str, Any]]:
    """
    segments: [{index:int, kind:str, text:str}, ...]
    returns:  [{index:int, text:str}, ...]
    """
    payload = {
        "guidelines": guidelines,
        "segments": [
            {
                "index": int(s["index"]),
                "kind": s.get("kind", "para"),
                "text": s.get("text", ""),
            }
            for s in segments
        ],
    }

    last_err: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            messages = [
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
            ]
            out = _chat(messages)
            data = _extract_json(out)
            items = data.get("rewrites", [])
            return [
                {"index": int(it["index"]), "text": str(it["text"])}
                for it in items
                if isinstance(it, dict) and "index" in it and "text" in it
            ]
        except Exception as e:
            last_err = e
            # exponential-ish backoff
            time.sleep(1.0 + 0.75 * attempt)
    raise RuntimeError(f"LLM rewrite failed: {last_err}")
