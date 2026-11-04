"""Configuration manager for Athena Everyday Desktop Companion.
Stores settings in ~/.athena/config.json
"""

import os
import json
import shutil
from pathlib import Path
from typing import Dict, Any

ATHENA_DIR = Path.home() / ".athena"
ATHENA_CONFIG = ATHENA_DIR / "config.json"

SPIDY_DIR = Path.home() / ".spidy"
SPIDY_CONFIG = SPIDY_DIR / "config.json"

LEGACY_CLICKY_DIR = Path.home() / ".clicky"
LEGACY_CLICKY_CONFIG = LEGACY_CLICKY_DIR / "config.json"

DEFAULT_CONFIG: Dict[str, Any] = {
    "api_key": "YOUR_GEMINI_API_KEY_HERE",
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
    ATHENA_DIR.mkdir(parents=True, exist_ok=True)

    # Auto-migrate from ~/.athena or ~/.clicky if Spidy config does not exist
    active_config_path = SPIDY_CONFIG if SPIDY_CONFIG.exists() else ATHENA_CONFIG
    if not active_config_path.exists():
        if ATHENA_CONFIG.exists():
            try:
                shutil.copy2(ATHENA_CONFIG, SPIDY_CONFIG)
                active_config_path = SPIDY_CONFIG
            except Exception:
                pass
        elif LEGACY_CLICKY_CONFIG.exists():
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
            # Top-bar HUD is permanently dropped in Spidy in favor of cursor-spawned beige tab
            merged["top_bar_hud_enabled"] = False
            merged["beige_tab_enabled"] = True
            
            # If no valid API key is present in user config, pull from legacy configs
            current_k = merged.get("api_key") or merged.get("grok_api_key", "")
            if not current_k or current_k.startswith("YOUR_") or "PLACEHOLDER" in current_k.upper():
                for fallback_cfg in (ATHENA_CONFIG, LEGACY_CLICKY_CONFIG):
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
            # Sync alias keys
            if "grok_api_key" in merged and ("api_key" not in merged or merged["api_key"] == DEFAULT_CONFIG["api_key"]):
                merged["api_key"] = merged["grok_api_key"]
            if "grok_model" in merged and ("model" not in merged or merged["model"] == "auto"):
                merged["model"] = merged["grok_model"]
            return merged
    except Exception:
        return DEFAULT_CONFIG.copy()


def save_config(config: Dict[str, Any]) -> None:
    SPIDY_DIR.mkdir(parents=True, exist_ok=True)
    ATHENA_DIR.mkdir(parents=True, exist_ok=True)
    # Ensure backwards compatible keys are mirrored
    if "api_key" in config:
        config["grok_api_key"] = config["api_key"]
    if "model" in config:
        config["grok_model"] = config["model"]
    for out_path in (SPIDY_CONFIG, ATHENA_CONFIG):
        try:
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2)
        except Exception:
            pass


def get_api_key() -> str:
    cfg = load_config()
    key = cfg.get("api_key") or cfg.get("grok_api_key", "")
    key = str(key).strip()
    if key and not key.startswith("YOUR_") and "PLACEHOLDER" not in key.upper():
        return key

    # Check environment variables
    for env_var in ("GEMINI_API_KEY", "GROQ_API_KEY", "XAI_API_KEY", "GROK_API_KEY"):
        val = os.environ.get(env_var, "").strip()
        if val:
            return val

    # Check .env in workspace
    try:
        for env_path in [Path.cwd() / ".env", Path(__file__).resolve().parent.parent / ".env"]:
            if env_path.exists():
                with open(env_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        for prefix in ("GEMINI_API_KEY=", "GROQ_API_KEY=", "XAI_API_KEY=", "GROK_API_KEY="):
                            if line.startswith(prefix):
                                val = line.split("=", 1)[1].strip().strip('"').strip("'")
                                if val:
                                    return val
    except Exception:
        pass

    return key


def set_api_key(key: str) -> None:
    cfg = load_config()
    cfg["api_key"] = key.strip()
    cfg["grok_api_key"] = key.strip()
    save_config(cfg)


# Backward compatibility aliases
get_grok_api_key = get_api_key
set_grok_api_key = set_api_key
