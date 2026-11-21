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
  - Generic foods for every country ("cooked rice", "boiled potato"): a local extract of USDA FoodData Central, SR Legacy (`src/usda_db.json`, built by `scripts/parse_usda.py`, served by `src/usda_client.py`). Carbohydrates are stored as available carbs (total minus fiber) to match EU/UK/Mexican labels. Spanish and UK-English food words are translated to USDA terms at query time.
    Citation: U.S. Department of Agriculture, Agricultural Research Service. FoodData Central, SR Legacy (2018). fdc.nal.usda.gov — public domain.
  - Each country uses its OFFICIAL generic food composition table when OjasFuel has one (`src/food_tables.py`: `table_for_country()`): Mexico SMAE, United Kingdom CoFID, France CIQUAL; every other country uses USDA values, flagged in the UI as "US reference values". All three generic tables share one table-driven client (`FoodTable`) and one compact JSON format. Meat, fish and poultry groups and animal-named foods are removed at build time; eggs and dairy are kept. Carbohydrates are always available carbs (fibre excluded).
  - UK: McCance and Widdowson's CoFID 2021 (`src/cofid_db.json`, built by `scripts/parse_cofid.py`; "Tr" trace values are stored as 0, "N" as missing).
    Citation: Public Health England (2021). McCance and Widdowson's The Composition of Foods Integrated Dataset 2021. Contains public sector information licensed under the Open Government Licence v3.0.
  - France: ANSES-CIQUAL 2020 (`src/ciqual_db.json`, built by `scripts/parse_ciqual.py`; French and English names, searchable in French, English and Spanish; "traces" and "< x" values are stored as 0, "-" as missing; energy is computed with the EU 1169/2011 factors where CIQUAL publishes none).
    Citation: Anses (2020). Ciqual French food composition table. ciqual.anses.fr — Licence Ouverte / CC-BY 4.0.
  - Rebuilding the databases needs `openpyxl` (CoFID .xlsx) and `xlrd` (CIQUAL .xls): `python3 -I scripts/parse_cofid.py cofid_2021.xlsx src/cofid_db.json`, `python3 -I scripts/parse_ciqual.py ciqual_2020_fr.xls ciqual_2020_eng.xls src/ciqual_db.json`.
- **Classification logic**: `src/classifier.py` runs regex-based matching against ingredient text using pattern lists defined in `src/blocklists.py`, returning a vegan/vegetarian verdict, confidence score, and any filter violations. Open Food Facts' own verified tags are preferred over the classifier when available.
- **Barcode scanning**: a custom HTML/JS Streamlit component embeds the ZXing JavaScript library for live camera decoding, with a Python-side fallback using `pyzbar` and `OpenCV` for photo-based decoding.
- **OCR**: `EasyOCR` is used as a fallback for reading text from product photos when no barcode is detected.
- **State and settings**: user preferences (diet mode, country, active restrictions) are kept in Streamlit's session state and persisted via `src/storage.py`.
- **Internationalisation**: `src/i18n.py` provides a simple translation lookup (`t()`) used throughout the UI.
- **Styling**: a custom dark theme is injected via `src/theme.py`.

## Tech stack

Python, Streamlit, Open Food Facts SDK, OpenCV, pyzbar, EasyOCR, ZXing (JavaScript), deep-translator.
