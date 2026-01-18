---
name: validation-doctor
description: Automates the verification and setup guidance for critical MCP tools (Brave Search, Chrome DevTools). Triggers on "setup", "install tools", "check system", "geo doctor".
---

# Validation Doctor

Your goal is to ensure the **Truth Engine** (Validation Layer) is operational.

## 1. Diagnostics Routine
Run automatically when user asks to "setup" or "check" the system.

### Step 1: Probe Tools (No Guessing)
Do not assume tools exist. Probe with minimal, safe calls and interpret failures.
- **Chrome DevTools MCP:** Try a lightweight call like `mcp6_list_pages`.
- **Brave Search MCP:** Try `brave_web_search` with a trivial query and `count=1`.

### Step 2: Status Report
Output a table:

| Component | Status | Action Required |
|-----------|--------|-----------------|
| Market Validator (Brave) | ✅ / ❌ | [Config Snippet / None] |
| Technical Validator (Chrome) | ✅ / ❌ | [Config Snippet / None] |

## 2. Auto-Fix / Setup Guidance

If tools are missing, DO NOT just say "install them". Provide the EXACT JSON to paste.

**Requirements (Chrome DevTools MCP):** Node.js v20.19+ and current stable Chrome.

### Chrome DevTools Config
```json
"chrome-devtools": {
  "command": "npx",
  "args": ["-y", "chrome-devtools-mcp@latest"]
}
```

### Brave Search Config
```json
"brave-search": {
  "command": "npx",
  "args": ["-y", "@brave/brave-search-mcp-server", "--transport", "stdio"],
  "env": {
    "BRAVE_API_KEY": "YOUR_KEY_HERE"
  }
}
```

## 3. Validation Logic (Internal)
When running validation tasks:
1. **Always validate with the best available tools.**
2. Use `chrome-devtools` for rendered DOM extraction.
   - If unavailable -> Fallback to `fetch` (Text-only) but mark outputs as **Low Confidence**.
3. Use `brave-search` for competitor discovery.
   - If unavailable -> Skip competitor claims and only score based on the page itself.
