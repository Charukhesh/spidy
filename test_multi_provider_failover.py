"""Automated Unit Tests for Spidy Multi-Provider Auto-Failover Engine.

Validates:
1. Provider key resolution across config, environment variables, and .env file.
2. Active provider list construction with correct endpoints, models, and headers.
3. Seamless auto-failover: when Provider 1 encounters 429 (Rate Limit) or 503,
   AIVisionClient immediately queries Provider 2 without crashing or dropping the request.
4. Graceful degradation when all providers fail.
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from spidy.config import get_all_provider_keys, set_provider_key, load_config
from spidy.ai_vision_client import AIVisionClient, AIVisionResponse
import httpx


class TestMultiProviderFailover(unittest.TestCase):

    def test_01_provider_key_resolution(self):
        """Verify get_all_provider_keys resolves keys from config and env."""
        keys = get_all_provider_keys()
        self.assertIsInstance(keys, dict)
        for expected in ["gemini", "grok", "openrouter", "nvidia_nim", "groq"]:
            self.assertIn(expected, keys)

    def test_02_active_providers_generation(self):
        """Verify _get_active_providers builds correctly ordered candidate list."""
        client = AIVisionClient()
        # Mock active keys for gemini, grok, openrouter, nvidia_nim
        mock_keys = {
            "gemini": "AIzaSyMockGeminiKey123",
            "grok": "xai-MockGrokKey456",
            "openrouter": "sk-or-MockOpenRouterKey789",
            "nvidia_nim": "nvapi-MockNvidiaKey000",
            "groq": "",
        }

        with patch("spidy.ai_vision_client.get_all_provider_keys", return_value=mock_keys):
            providers = client._get_active_providers()

            self.assertEqual(len(providers), 4)
            prov_ids = [p["id"] for p in providers]
            self.assertEqual(prov_ids, ["gemini", "grok", "openrouter", "nvidia_nim"])

            # Verify endpoints
            self.assertIn("generativelanguage.googleapis.com", providers[0]["endpoint"])
            self.assertIn("api.x.ai", providers[1]["endpoint"])
            self.assertIn("openrouter.ai", providers[2]["endpoint"])
            self.assertIn("integrate.api.nvidia.com", providers[3]["endpoint"])

            # Verify OpenRouter headers
            self.assertIn("HTTP-Referer", providers[2]["headers"])
            self.assertIn("X-Title", providers[2]["headers"])

    def test_03_seamless_failover_on_429_rate_limit(self):
        """Verify automatic failover from Gemini (429) to Grok (200 OK)."""
        client = AIVisionClient()
        mock_keys = {
            "gemini": "AIzaSyGeminiBusy",
            "grok": "xai-GrokAvailable",
            "openrouter": "",
            "nvidia_nim": "",
            "groq": "",
        }

        # Successful Grok mock response
        mock_grok_reply = {
            "choices": [{
                "message": {
                    "content": "[HEARD: hello spidy] Hey there! Grok stepped in to answer you seamlessly. [POINT:none]"
                }
            }]
        }

        # Mock HTTP client responses: 1st call fails with 429, 2nd call succeeds with 200
        req_429 = httpx.Request("POST", "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions")
        resp_429 = httpx.Response(status_code=429, text='{"error": "Resource has been exhausted (e.g. check quota)"}', request=req_429)

        req_200 = httpx.Request("POST", "https://api.x.ai/v1/chat/completions")
        resp_200 = httpx.Response(status_code=200, json=mock_grok_reply, request=req_200)

        with patch("spidy.ai_vision_client.get_all_provider_keys", return_value=mock_keys):
            with patch.object(httpx.Client, "post", side_effect=[resp_429, resp_200]) as mock_post:
                response = client.query("hello spidy", screen_captures=[])

                # Verify both providers were called (Gemini 1st, then Grok 2nd)
                self.assertEqual(mock_post.call_count, 2)
                # Verify successful failover response
                self.assertIn("Grok stepped in to answer you seamlessly", response.spoken_text)
                self.assertEqual(response.heard_prompt, "hello spidy")

    def test_04_triple_failover_gemini_grok_openrouter(self):
        """Verify failover traversing Gemini (503) -> Grok (429) -> OpenRouter (200 OK)."""
        client = AIVisionClient()
        mock_keys = {
            "gemini": "AIzaSyGemini",
            "grok": "xai-Grok",
            "openrouter": "sk-or-OpenRouter",
            "nvidia_nim": "",
            "groq": "",
        }

        mock_or_reply = {
            "choices": [{
                "message": {
                    "content": "[HEARD: status check] OpenRouter delivered the answer cleanly. [POINT:none]"
                }
            }]
        }

        req1 = httpx.Request("POST", "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions")
        resp1 = httpx.Response(status_code=503, text='{"error": "Overloaded"}', request=req1)

        req2 = httpx.Request("POST", "https://api.x.ai/v1/chat/completions")
        resp2 = httpx.Response(status_code=429, text='{"error": "Rate limit"}', request=req2)

        req3 = httpx.Request("POST", "https://openrouter.ai/api/v1/chat/completions")
        resp3 = httpx.Response(status_code=200, json=mock_or_reply, request=req3)

        with patch("spidy.ai_vision_client.get_all_provider_keys", return_value=mock_keys):
            with patch.object(httpx.Client, "post", side_effect=[resp1, resp2, resp3]) as mock_post:
                response = client.query("status check", screen_captures=[])

                self.assertEqual(mock_post.call_count, 3)
                self.assertIn("OpenRouter delivered the answer cleanly", response.spoken_text)

    def test_05_all_providers_exhausted(self):
        """Verify clean error message returned when every single provider fails."""
        client = AIVisionClient()
        mock_keys = {
            "gemini": "AIzaSyGemini",
            "grok": "xai-Grok",
            "openrouter": "",
            "nvidia_nim": "",
            "groq": "",
        }

        req1 = httpx.Request("POST", "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions")
        resp1 = httpx.Response(status_code=429, text='{"error": "Quota"}', request=req1)
        req2 = httpx.Request("POST", "https://api.x.ai/v1/chat/completions")
        resp2 = httpx.Response(status_code=500, text='{"error": "Internal"}', request=req2)

        with patch("spidy.ai_vision_client.get_all_provider_keys", return_value=mock_keys):
            with patch.object(httpx.Client, "post", side_effect=[resp1, resp2]):
                response = client.query("help", screen_captures=[])

                self.assertIn("all configured vision models experienced rate limits or errors", response.spoken_text)


if __name__ == "__main__":
    unittest.main()

