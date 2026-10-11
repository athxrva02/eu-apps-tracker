"""Explicit live check. Never imported by tests or run during application startup."""

import argparse
import json
import sys

import httpx

from app.config import settings
from app.matching.provider import build_request, unpack_response


def main():
    parser = argparse.ArgumentParser(
        description="Send one small paid OpenRouter request; no candidate data."
    )
    parser.add_argument("--live", action="store_true", required=True)
    parser.parse_args()
    if settings.llm_provider != "openrouter" or not settings.openrouter_api_key:
        sys.exit("Configure LLM_PROVIDER=openrouter and OPENROUTER_API_KEY in .env.")
    schema = {
        "type": "object",
        "properties": {"status": {"type": "string", "enum": ["OK"]}},
        "required": ["status"],
        "additionalProperties": False,
    }
    url, headers, body = build_request("Return status OK. This is a connection check.", schema, 16)
    try:
        with httpx.Client(timeout=40, trust_env=False, follow_redirects=False) as client:
            response = client.post(url, headers=headers, json=body)
        response.raise_for_status()
        content, tokens, cost = unpack_response(response.json())
        if json.loads(content) != {"status": "OK"}:
            raise ValueError("Unexpected structured output")
        print(
            json.dumps(
                {
                    "status": "OK",
                    "http_status": response.status_code,
                    "model": settings.llm_model,
                    "tokens": tokens,
                    "cost_usd": cost,
                    "structured_output_valid": True,
                }
            )
        )
    except Exception as exc:
        # Never print headers, credentials or raw provider payloads.
        sys.exit(
            f"OpenRouter check failed ({type(exc).__name__}). Check credentials, credit and model support."
        )


if __name__ == "__main__":
    main()
