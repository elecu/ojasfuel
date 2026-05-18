---
name: project-smaeuk
description: SMAEUK Streamlit food scanner app — design decisions and constraints
metadata:
  type: project
---

SMAEUK is a Streamlit multi-page food scanner app (vegetarian/vegan classifier) using Open Food Facts data.

**Accent color chosen:** Electric cyan `#00d4ff` (dark) / `#0099cc` (light)
**Font:** Inter (Google Fonts import via CSS)
**Theme system:** CSS variables injected via `src/theme.py` → `inject_theme()`, toggled by `st.session_state['theme']` ('dark'|'light'). Toggle lives in `pages/5_Settings.py`.
**Base Streamlit theme:** `config.toml` set to dark base so pre-hydration flash is dark.

**Why:** CSS variable approach keeps a single source of truth for all color tokens; toggling `session_state['theme']` + `st.rerun()` re-injects the correct variable block instantly.

**How to apply:** Every page calls `inject_theme()` immediately after `init_session()`. Never put theme logic inside business-logic functions.

**Functional code to never touch:** `src/classifier.py`, `src/api_client.py`, `src/blocklists.py`, all API call blocks, form submission handlers, barcode/OCR processing.

**Pages:**
- `app.py` — Home / Search
- `pages/1_Detail.py` — Product Detail
- `pages/2_Portion_Calculator.py` — Portion Calculator
- `pages/3_Equivalents_Finder.py` — Equivalents Finder
- `pages/4_Photo_Upload.py` — Photo Upload + barcode/OCR
- `pages/5_Settings.py` — Settings + theme toggle
