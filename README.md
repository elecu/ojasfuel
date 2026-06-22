# OjasFuel

![OjasFuel logo](logo_text2.png)

OjasFuel is a Streamlit web app that helps users check whether a packaged food product fits a vegan, vegetarian, or otherwise restricted diet. Users search by product name or barcode, scan a barcode with their device camera, or upload a photo, and the app returns a diet classification together with nutritional details.

## What it does

- **Product search**: look up products by name or barcode against the Open Food Facts database, with results scoped to a selected country.
- **Live barcode scanning**: in-browser camera scanner (ZXing) with a photo-capture fallback decoded server-side with pyzbar/OpenCV.
- **Photo upload**: detect barcodes and run OCR (EasyOCR) on uploaded product photos when a live scan isn't possible.
- **Diet classification**: a rule-based classifier checks ingredient text against curated blocklists (meat, fish, dairy, eggs, gelatin, honey, alcohol, caffeine, allergens, and more) to flag vegan/vegetarian status and any active dietary restrictions (e.g. Jain, lacto-only, ovo-only, no garlic/onion).
- **Mexico-specific data source**: for Mexican users, results are drawn first from a local dataset built on the SMAE (Sistema Mexicano de Alimentos Equivalentes) food-exchange system, falling back to Open Food Facts Mexico.
- **Portion calculator and equivalents finder**: additional pages to scale serving sizes and find nutritionally similar product substitutes.
- **Contribute flow**: lets users submit a product missing from Open Food Facts directly from the app.
- **Multi-language UI**: interface strings are translated via a lightweight i18n module, with English as the default language.

## How it's built

- **Frontend/runtime**: [Streamlit](https://streamlit.io/), using its native multi-page app structure (`app.py` as the home page, `pages/` for Detail, Portion Calculator, Equivalents Finder, Photo Upload, Settings, and Contribute).
- **Data sources**:
  - [Open Food Facts](https://world.openfoodfacts.org/) via the official `openfoodfacts` Python SDK (`src/api_client.py`), with country-aware API subdomain routing.
  - A local SMAE dataset (`src/smae_db.json`, parsed via `scripts/parse_smae.py`) served through `src/smae_client.py` for Mexico-specific lookups.
- **Classification logic**: `src/classifier.py` runs regex-based matching against ingredient text using pattern lists defined in `src/blocklists.py`, returning a vegan/vegetarian verdict, confidence score, and any filter violations. Open Food Facts' own verified tags are preferred over the classifier when available.
- **Barcode scanning**: a custom HTML/JS Streamlit component embeds the ZXing JavaScript library for live camera decoding, with a Python-side fallback using `pyzbar` and `OpenCV` for photo-based decoding.
- **OCR**: `EasyOCR` is used as a fallback for reading text from product photos when no barcode is detected.
- **State and settings**: user preferences (diet mode, country, active restrictions) are kept in Streamlit's session state and persisted via `src/storage.py`.
- **Internationalisation**: `src/i18n.py` provides a simple translation lookup (`t()`) used throughout the UI.
- **Styling**: a custom dark theme is injected via `src/theme.py`.

## Tech stack

Python, Streamlit, Open Food Facts SDK, OpenCV, pyzbar, EasyOCR, ZXing (JavaScript), deep-translator.
