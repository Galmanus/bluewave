"""Claude CLI Engine — usa claude -p (Pro Max) como motor de inferencia.

Resiliente: retry com backoff, fallback pra Haiku, nunca trava.
"""

import json
import logging
import os
import subprocess
import time
from typing import Optional

logger = logging.getLogger("wave.cli_engine")

CLAUDE_BIN = os.environ.get("CLAUDE_BIN", "claude")
DEFAULT_MODEL = os.environ.get("WAVE_MODEL", "claude-opus-4-20250514")
TIMEOUT = int(os.environ.get("WAVE_CLI_TIMEOUT", "300"))
MAX_RETRIES = 2
RETRY_DELAY = 3


def cli_call(prompt, model=None, retry=0):
    """Chama claude -p com retry e fallback."""
    model = model or DEFAULT_MODEL
    cmd = [CLAUDE_BIN, "-p", "--model", model]

    try:
        result = subprocess.run(
            cmd, input=prompt, capture_output=True, text=True, timeout=TIMEOUT,
        )
        if result.returncode != 0:
            err = result.stderr.strip()[:200]
            logger.error("claude -p failed (rc=%d): %s", result.returncode, err)
            if retry < MAX_RETRIES:
                logger.info("Retrying in %ds (attempt %d/%d)...", RETRY_DELAY, retry + 1, MAX_RETRIES)
                time.sleep(RETRY_DELAY)
                return cli_call(prompt, model=model, retry=retry + 1)
            # Fallback to Haiku if Opus fails
            if model != "claude-haiku-4-5-20251001":
                logger.warning("Opus failed, falling back to Haiku")
                return cli_call(prompt, model="claude-haiku-4-5-20251001", retry=0)
            return "[Wave degradado] Engine temporariamente limitado. Tente novamente em 1 minuto."

        response = result.stdout.strip()
        if not response:
            if retry < MAX_RETRIES:
                time.sleep(RETRY_DELAY)
                return cli_call(prompt, model=model, retry=retry + 1)
            return "[Wave degradado] Resposta vazia do engine."

        logger.info("claude -p OK (%d chars, %s)", len(response), model)
        return response

    except subprocess.TimeoutExpired:
        logger.error("claude -p timeout (%ds)", TIMEOUT)
        if retry < MAX_RETRIES:
            return cli_call(prompt, model=model, retry=retry + 1)
        return "[Wave degradado] Timeout no processamento. Tente com uma mensagem mais curta."
    except FileNotFoundError:
        logger.error("claude binary not found: %s", CLAUDE_BIN)
        return "[Wave degradado] Claude CLI nao encontrado."
    except Exception as e:
        logger.exception("claude -p exception")
        if retry < MAX_RETRIES:
            time.sleep(RETRY_DELAY)
            return cli_call(prompt, model=model, retry=retry + 1)
        return f"[Wave degradado] Erro: {e}"


def cli_call_with_system(system_prompt, user_message, model=None):
    """Chama claude -p com system prompt."""
    combined = f"Instrucoes (siga rigorosamente):\n---\n{system_prompt}\n---\n\nMensagem do usuario:\n{user_message}"
    return cli_call(combined, model=model)


def cli_call_structured(system_prompt, messages, model=None):
    """Chama claude -p com historico de mensagens."""
    parts = [f"Instrucoes:\n---\n{system_prompt}\n---\n"]

    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if isinstance(content, list):
            text_parts = []
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    text_parts.append(block["text"])
                elif isinstance(block, str):
                    text_parts.append(block)
            content = "\n".join(text_parts)

        if role == "user":
            parts.append(f"Human: {content}")
        elif role == "assistant":
            parts.append(f"Assistant: {content}")

    parts.append("Assistant:")
    return cli_call("\n\n".join(parts), model=model)
