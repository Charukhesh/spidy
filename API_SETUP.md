# 🔑 Athena Vision AI Setup & Provider Guide

Athena is designed to operate on **100% free multimodal vision models** with zero mandatory subscriptions. This guide walks you through setting up your preferred AI provider.

---

## 🌟 Option 1: Google Gemini (Recommended — 1,000,000 TPM Free)

Google Gemini 3.5 Flash is the recommended provider for Athena. It offers an enormous token quota (1M tokens per minute) and top-tier desktop OCR and coordinate grounding.

### Step-by-Step Instructions:
1. Navigate to **[Google AI Studio](https://aistudio.google.com/app/apikey)**.
2. Sign in with your Google account.
3. Click **"Create API key"**.
4. Copy the generated key.
   > [!NOTE]
   > Google's latest keys begin with **`AQ.`** (e.g. `AQ.xxxxxxxx...`). Older keys start with **`AIza...`**. Athena automatically recognizes and supports both formats.
5. In Athena:
   * Open the control panel (click the glowing blue triangle in your taskbar tray).
   * Paste your key into the **API Key** input box.
   * Click **"Test"** — it will turn green with `Connected successfully to Google Gemini using model gemini-3.5-flash!`.
   * Click **"Save"**.

---

## ⚡ Option 2: Groq Cloud (Free LPU Inference)

If you prefer open-weight models running on Groq's high-speed LPUs:

### Step-by-Step Instructions:
1. Navigate to **[GroqCloud Console](https://console.groq.com/keys)**.
2. Sign up or log in.
3. Click **"Create API Key"**.
4. Copy the key (starts with **`gsk_`**).
5. Paste it into Athena’s control panel.
   * Athena automatically recognizes the `gsk_` prefix and switches to Groq's active vision model: **`qwen/qwen3.8-27b`**.

---

## 🪐 Option 3: xAI Grok (Paid API Credits)

If you want to use the original model from the HeyClicky macOS codebase:

### Step-by-Step Instructions:
1. Navigate to **[xAI Console](https://console.x.ai/)**.
2. Purchase API credits and generate a key starting with **`xai-`**.
3. Paste it into Athena’s control panel. Athena will route directly to **`grok-2-vision-1212`**.

---

## 🛠️ Direct Config File Configuration

You can also set your key directly in your home directory config at `~/.athena/config.json`:

```json
{
  "api_key": "YOUR_ACTUAL_KEY_HERE",
  "model": "auto"
}
```
Or via Windows environment variable:
```powershell
[System.Environment]::SetEnvironmentVariable('GEMINI_API_KEY', 'your_key_here', 'User')
```

