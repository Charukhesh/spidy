"""Configuration manager for Spidy Everyday Desktop Companion.
Stores settings in ~/.spidy/config.json and respects workspace .env files.
"""

import os
import json
import shutil
from pathlib import Path
from typing import Dict, Any, List

SPIDY_DIR = Path.home() / ".spidy"
SPIDY_CONFIG = SPIDY_DIR / "config.json"

LEGACY_CLICKY_DIR = Path.home() / ".clicky"
LEGACY_CLICKY_CONFIG = LEGACY_CLICKY_DIR / "config.json"

DEFAULT_CONFIG: Dict[str, Any] = {
    "api_key": "YOUR_GEMINI_API_KEY_HERE",
    "gemini_api_key": "",
    "grok_api_key": "",
    "openrouter_api_key": "",
    "nvidia_nim_api_key": "",
    "groq_api_key": "",
    "provider_priority": ["gemini", "grok", "openrouter", "nvidia_nim", "groq"],
    "model": "auto",
    "hotkey": "ctrl+alt",
    "sound_effects_enabled": True,
    "context_awareness": True,
    "top_bar_hud_enabled": False,
    "beige_tab_enabled": True,
    "floating_card_enabled": True,
    "tts_voice": "en-US-AvaNeural",
    "tts_rate": "+2%",
    "transient_mode": False,
    "whisper_model": "base.en",
    "cursor_color": "#DC2626",
    "font_family": "Calibri",
    "conversation_history_limit": 10,
    "system_prompt_rules": True,
    "wake_word_enabled": False,
    "memory_enabled": True,
    "desktop_actions_enabled": True,
}


def load_config() -> Dict[str, Any]:
    SPIDY_DIR.mkdir(parents=True, exist_ok=True)

    # Auto-migrate from ~/.spidy or ~/.clicky if Spidy config does not exist
    active_config_path = SPIDY_CONFIG
    if not active_config_path.exists():
        if LEGACY_CLICKY_CONFIG.exists():
            try:
                shutil.copy2(LEGACY_CLICKY_CONFIG, SPIDY_CONFIG)
                active_config_path = SPIDY_CONFIG
            except Exception:
                pass
        else:
            save_config(DEFAULT_CONFIG)
            return DEFAULT_CONFIG.copy()

    try:
        with open(active_config_path, "r", encoding="utf-8") as f:
            user_config = json.load(f)
            merged = DEFAULT_CONFIG.copy()
            merged.update(user_config)
            merged["top_bar_hud_enabled"] = False
            merged["beige_tab_enabled"] = True

            # If no valid API key is present in user config, pull from legacy configs
            current_k = merged.get("api_key") or merged.get("grok_api_key", "")
            if not current_k or current_k.startswith("YOUR_") or "PLACEHOLDER" in current_k.upper():
                for fallback_cfg in (SPIDY_CONFIG, LEGACY_CLICKY_CONFIG):
                    if fallback_cfg.exists():
                        try:
                            with open(fallback_cfg, "r", encoding="utf-8") as lf:
                                l_data = json.load(lf)
                                l_key = l_data.get("api_key") or l_data.get("grok_api_key", "")
                                if l_key and not l_key.startswith("YOUR_") and "PLACEHOLDER" not in l_key.upper():
                                    merged["api_key"] = l_key
                                    merged["grok_api_key"] = l_key
                                    save_config(merged)
                                    break
                        except Exception:
                            pass

            return merged
    except Exception:
        return DEFAULT_CONFIG.copy()


def save_config(config: Dict[str, Any]) -> None:
    SPIDY_DIR.mkdir(parents=True, exist_ok=True)
    # Ensure backwards compatible keys are mirrored
    if "api_key" in config:
        config["grok_api_key"] = config["api_key"]
    if "model" in config:
        config["grok_model"] = config["model"]
    try:
        with open(SPIDY_CONFIG, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
    except Exception:
        pass


def get_all_provider_keys() -> Dict[str, str]:
    """Retrieve all available API keys across config, environment variables, and .env file."""
    cfg = load_config()
    keys: Dict[str, str] = {
        "gemini": "",
        "grok": "",
        "openrouter": "",
        "nvidia_nim": "",
        "groq": "",
    }

    # 1. Pull from .env file FIRST (highest priority for project workspace)
    for env_path in [Path.cwd() / ".env", Path(__file__).resolve().parent.parent / ".env"]:
        if env_path.exists():
            try:
                with open(env_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if "=" in line and not line.startswith("#"):
                            k, v = line.split("=", 1)
                            k = k.strip().upper()
                            v = v.strip().strip('"').strip("'")
                            if v and not v.startswith("YOUR_") and "PLACEHOLDER" not in v.upper():
                                if k in ("GEMINI_API_KEY", "GOOGLE_API_KEY") and not keys["gemini"]:
                                    keys["gemini"] = v
                                elif k in ("GROK_API_KEY", "XAI_API_KEY") and not keys["grok"]:
                                    keys["grok"] = v
                                elif k == "OPENROUTER_API_KEY" and not keys["openrouter"]:
                                    keys["openrouter"] = v
                                elif k in ("NVIDIA_API_KEY", "NVIDIA_NIM_API_KEY") and not keys["nvidia_nim"]:
                                    keys["nvidia_nim"] = v
                                elif k == "GROQ_API_KEY" and not keys["groq"]:
                                    keys["groq"] = v
            except Exception:
                pass

    # 2. Pull from Environment Variables
    env_mappings = {
        "gemini": ["GEMINI_API_KEY", "GOOGLE_API_KEY"],
        "grok": ["XAI_API_KEY", "GROK_API_KEY"],
        "openrouter": ["OPENROUTER_API_KEY"],
        "nvidia_nim": ["NVIDIA_API_KEY", "NVIDIA_NIM_API_KEY"],
        "groq": ["GROQ_API_KEY"],
    }
    for prov, env_vars in env_mappings.items():
        if not keys[prov] or keys[prov].startswith("YOUR_"):
            for ev in env_vars:
                val = os.environ.get(ev, "").strip()
                if val and not val.startswith("YOUR_"):
                    keys[prov] = val
                    break

    # 3. Pull from config (only if not set by .env or environment)
    if not keys["gemini"]:
        if cfg.get("gemini_api_key"):
            keys["gemini"] = str(cfg["gemini_api_key"]).strip()
        elif cfg.get("api_key") and not str(cfg["api_key"]).startswith("YOUR_"):
            k = str(cfg["api_key"]).strip()
            if k.startswith("AQ.") or k.startswith("AIza"):
                keys["gemini"] = k

    if not keys["grok"] and cfg.get("grok_api_key"):
        gk = str(cfg["grok_api_key"]).strip()
        if gk.startswith("xai-") or gk.startswith("grok_"):
            keys["grok"] = gk

    if not keys["openrouter"] and cfg.get("openrouter_api_key"):
        keys["openrouter"] = str(cfg["openrouter_api_key"]).strip()

    if not keys["nvidia_nim"]:
        if cfg.get("nvidia_nim_api_key"):
            keys["nvidia_nim"] = str(cfg["nvidia_nim_api_key"]).strip()
        elif cfg.get("nvidia_api_key"):
            keys["nvidia_nim"] = str(cfg["nvidia_api_key"]).strip()

    if not keys["groq"] and cfg.get("groq_api_key"):
        keys["groq"] = str(cfg["groq_api_key"]).strip()

    # Clean out placeholders
    for p in keys:
        if keys[p].startswith("YOUR_") or "PLACEHOLDER" in keys[p].upper():
            keys[p] = ""

    return keys


def get_api_key() -> str:
    """Returns primary key (for backwards compatibility)."""
    keys = get_all_provider_keys()
    for prov in ["gemini", "grok", "openrouter", "nvidia_nim", "groq"]:
        if keys.get(prov):
            return keys[prov]
    return ""


def set_api_key(key: str) -> None:
    cfg = load_config()
    k = key.strip()
    cfg["api_key"] = k
    if k.startswith("AQ.") or k.startswith("AIza"):
        cfg["gemini_api_key"] = k
    elif k.startswith("xai-"):
        cfg["grok_api_key"] = k
    elif k.startswith("sk-or-"):
        cfg["openrouter_api_key"] = k
    elif k.startswith("nvapi-"):
        cfg["nvidia_nim_api_key"] = k
    elif k.startswith("gsk_"):
        cfg["groq_api_key"] = k
    else:
        cfg["gemini_api_key"] = k
    save_config(cfg)


def set_provider_key(provider: str, key: str) -> None:
    """Save an individual provider key into ~/.spidy/config.json."""
    cfg = load_config()
    key_field = f"{provider.lower()}_api_key"
    cfg[key_field] = key.strip()
    save_config(cfg)


# Backward compatibility aliases
get_grok_api_key = get_api_key
set_grok_api_key = set_api_key
