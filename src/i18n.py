"""
Simple dict-based i18n. All UI strings defined here.
Usage: from src.i18n import t, get_lang
"""

import streamlit as st

_EN = {
    # App-wide
    'app_title': 'SMAEUK',
    'app_subtitle': 'Vegetarian & Vegan Food Scanner',
    'settings': 'Settings',
    'search': 'Search',
    'detail': 'Product Detail',
    'portion_calc': 'Portion Calculator',
    'equivalents': 'Equivalents Finder',
    'photo_upload': 'Photo Upload',
    'save': 'Save',
    'cancel': 'Cancel',
    'back': '← Back',
    'loading': 'Loading...',
    'no_results': 'No products found.',
    'error': 'Error',
    'success': 'Success',
    'warning': 'Warning',
    'beta_banner': '⚗️ Beta — data from Open Food Facts',

    # Search page
    'search_placeholder': 'Search by name (e.g. bread) or barcode (e.g. 5012345678901)',
    'search_button': '🔍 Search',
    'searching': 'Searching...',
    'results_count': '{n} products found',
    'filter_active': '🔽 Filters active',
    'filter_inactive': 'No filters',
    'go_to_settings': '⚙️ Settings',
    'scan_barcode': '📷 Scan Barcode',
    'scan_barcode_title': 'Scan a barcode with your camera',
    'scan_barcode_hint': 'Point the camera at the barcode and take a photo.',
    'barcode_detected': '✅ Barcode detected: {code}',
    'barcode_not_detected': '❌ No barcode detected in the image. Try again.',
    'view_detail': 'View Details',
    'vegan_tag': '✨ Vegan',
    'vegetarian_tag': '🥦 Vegetarian',
    'not_vegetarian_tag': '❌ Not Vegetarian',
    'unknown_tag': '❓ Unknown',
    'passes_filter': '✅ Passes your filters',
    'fails_filter': '⚠️ Fails your filters',
    'no_ingredients': 'No ingredients data',
    'confidence': 'Confidence',
    'violations': 'Violations',

    # Detail page
    'product_info': 'Product Information',
    'name': 'Name',
    'brand': 'Brand',
    'quantity': 'Quantity',
    'serving_size': 'Serving size',
    'nutriscore': 'Nutri-Score',
    'ingredients': 'Ingredients',
    'nutrition_facts': 'Nutrition Facts (per 100g)',
    'macronutrients': 'Macronutrients',
    'minerals': 'Minerals',
    'vitamins': 'Vitamins',
    'other_nutrients': 'Other',
    'classification': 'Dietary Classification',
    'reason': 'Reason',
    'calc_portion': '⚖️ Calculate My Portion',
    'find_equivalents': '🔄 Find Equivalents',
    'open_off': '🌐 View on Open Food Facts',
    'no_product_selected': 'No product selected. Go to Search first.',

    # Portion calculator
    'total_weight_g': 'Total product weight (g)',
    'how_much_eating': 'How much will you eat?',
    'enter_weight_g': 'Enter weight (g)',
    'enter_percentage': 'Or enter percentage (%)',
    'number_of_portions': 'Number of portions',
    'weight_per_portion': 'Weight per portion (g)',
    'portion_grams': 'Portion: {g}g',
    'nutrients_for_portion': 'Nutrients for your portion',
    'warning_sodium': '⚠️ High sodium ({v}mg) — limit is ~600mg per meal',
    'warning_sugar': '⚠️ High sugar ({v}g) — over 15g per portion',
    'warning_protein': '⚠️ Low protein ({v}g) — under 5g per portion',
    'save_portion': '💾 Save This Portion',
    'portion_saved': 'Portion saved!',
    'saved_portions': 'Saved Portions',

    # Equivalents
    'original_product': 'Original Product',
    'alternative_product': 'Alternative Product',
    'search_alternative': 'Search for an alternative product',
    'you_need': 'You need {qty} of {name}',
    'comparison': 'Nutrient Comparison',
    'nutrient': 'Nutrient',
    'original': 'Original',
    'alternative': 'Alternative',
    'difference': 'Difference',
    'find_auto': '🔍 Find 5 Equivalents Automatically',
    'threshold_label': 'Match within ±{pct}%',
    'macro_warning': '⚠️ {nutrient} differs by {pct:.1f}%',
    'good_match': '✅ Good match within threshold',

    # Photo upload
    'photo_source': 'Image source',
    'take_photo': '📷 Take Photo',
    'upload_file': '📁 Upload File',
    'detected_barcode': 'Detected Barcode',
    'barcode_found': '✅ Barcode: {code} — searching...',
    'barcode_not_found': 'No barcode detected',
    'ocr_ingredients': 'OCR — Ingredients',
    'ocr_nutrients': 'OCR — Nutrients',
    'edit_before_upload': 'Edit before uploading',
    'translate_to_english': '🌐 Translate to English',
    'translating': 'Translating...',
    'upload_to_off': '⬆️ Upload to Open Food Facts',
    'off_login_required': 'Open Food Facts login required to upload',
    'off_username': 'Username',
    'off_password': 'Password',
    'upload_success': '✅ Uploaded successfully!',
    'upload_failed': '❌ Upload failed: {err}',
    'pyzbar_missing': 'pyzbar not installed — barcode detection unavailable. Run: pip install pyzbar',
    'easyocr_missing': 'easyocr not installed — OCR unavailable. Run: pip install easyocr',
    'libzbar_missing': 'libzbar system library missing. Install: sudo apt install libzbar0',

    # Settings
    'language': 'Language',
    'diet_mode': 'Base Diet Mode',
    'vegan': 'Vegan',
    'vegetarian': 'Vegetarian',
    'both': 'Both (show all)',
    'extra_restrictions': 'Additional Restrictions',
    'no_garlic': 'No garlic',
    'no_onion': 'No onion',
    'no_caffeine': 'No caffeine',
    'no_alcohol': 'No alcohol',
    'no_mushrooms': 'No mushrooms/fungi',
    'no_gelatin': 'No gelatin / E120 / carmine',
    'jain': 'Jain diet (no roots, no onion/garlic)',
    'dairy_variants': 'Dairy & Egg Variants',
    'lacto': 'Lacto-vegetarian (no eggs)',
    'ovo': 'Ovo-vegetarian (no dairy)',
    'ovo_lacto': 'Ovo-lacto-vegetarian',
    'strict_egg_traces': 'Avoid products that may contain egg traces',
    'strict_egg_traces_help': 'Blocks products labelled "may contain egg" or similar cross-contamination warnings',
    'equivalents_threshold': 'Equivalents match threshold',
    'save_settings': '💾 Save Settings',
    'settings_saved': '✅ Settings saved!',
    'reset_settings': 'Reset to defaults',
    'country_filter': 'Country Filter',
    'country_filter_help': 'Only show products sold in the selected countries. Leave empty to show all countries.',
    'country_all': 'All countries',
    # About section
    'about': 'About',
    'version': 'Version',
    'creator': 'Creator',
    'data_source': 'Data Source',
    'data_source_text': 'All product data sourced from [Open Food Facts](https://world.openfoodfacts.org/) — [Open Database Licence (ODbL)](https://opendatacommons.org/licenses/odbl/)',
    'disclaimer': 'This app is not affiliated with Open Food Facts.',
    'off_credit': '© Open Food Facts contributors',
}

_ES = {
    # App-wide
    'app_title': 'SMAEUK',
    'app_subtitle': 'Escáner de Alimentos Vegetarianos y Veganos',
    'settings': 'Configuración',
    'search': 'Buscar',
    'detail': 'Detalle del Producto',
    'portion_calc': 'Calculadora de Porciones',
    'equivalents': 'Buscador de Equivalentes',
    'photo_upload': 'Subir Foto',
    'save': 'Guardar',
    'cancel': 'Cancelar',
    'back': '← Volver',
    'loading': 'Cargando...',
    'no_results': 'No se encontraron productos.',
    'error': 'Error',
    'success': 'Éxito',
    'warning': 'Aviso',
    'beta_banner': '⚗️ Beta — datos de Open Food Facts',

    # Search page
    'search_placeholder': 'Busca por nombre (ej: pan) o código de barras (ej: 5012345678901)',
    'search_button': '🔍 Buscar',
    'searching': 'Buscando...',
    'results_count': '{n} productos encontrados',
    'filter_active': '🔽 Filtros activos',
    'filter_inactive': 'Sin filtros',
    'go_to_settings': '⚙️ Configuración',
    'scan_barcode': '📷 Escanear Código de Barras',
    'scan_barcode_title': 'Escanea un código de barras con tu cámara',
    'scan_barcode_hint': 'Apunta la cámara al código de barras y toma la foto.',
    'barcode_detected': '✅ Código detectado: {code}',
    'barcode_not_detected': '❌ No se detectó código de barras en la imagen. Intenta de nuevo.',
    'view_detail': 'Ver Detalles',
    'vegan_tag': '✨ Vegano',
    'vegetarian_tag': '🥦 Vegetariano',
    'not_vegetarian_tag': '❌ No Vegetariano',
    'unknown_tag': '❓ Desconocido',
    'passes_filter': '✅ Cumple tus filtros',
    'fails_filter': '⚠️ No cumple tus filtros',
    'no_ingredients': 'Sin datos de ingredientes',
    'confidence': 'Confianza',
    'violations': 'Infracciones',

    # Detail page
    'product_info': 'Información del Producto',
    'name': 'Nombre',
    'brand': 'Marca',
    'quantity': 'Cantidad',
    'serving_size': 'Tamaño de porción',
    'nutriscore': 'Nutri-Score',
    'ingredients': 'Ingredientes',
    'nutrition_facts': 'Información Nutricional (por 100g)',
    'macronutrients': 'Macronutrientes',
    'minerals': 'Minerales',
    'vitamins': 'Vitaminas',
    'other_nutrients': 'Otros',
    'classification': 'Clasificación Dietética',
    'reason': 'Motivo',
    'calc_portion': '⚖️ Calcular Mi Porción',
    'find_equivalents': '🔄 Buscar Equivalentes',
    'open_off': '🌐 Ver en Open Food Facts',
    'no_product_selected': 'Ningún producto seleccionado. Ve a Buscar primero.',

    # Portion calculator
    'total_weight_g': 'Peso total del producto (g)',
    'how_much_eating': '¿Cuánto vas a comer?',
    'enter_weight_g': 'Ingresa el peso (g)',
    'enter_percentage': 'O ingresa el porcentaje (%)',
    'number_of_portions': 'Número de porciones',
    'weight_per_portion': 'Peso por porción (g)',
    'portion_grams': 'Porción: {g}g',
    'nutrients_for_portion': 'Nutrientes para tu porción',
    'warning_sodium': '⚠️ Sodio alto ({v}mg) — límite ~600mg por comida',
    'warning_sugar': '⚠️ Azúcar alta ({v}g) — más de 15g por porción',
    'warning_protein': '⚠️ Proteína baja ({v}g) — menos de 5g por porción',
    'save_portion': '💾 Guardar Esta Porción',
    'portion_saved': '¡Porción guardada!',
    'saved_portions': 'Porciones Guardadas',

    # Equivalents
    'original_product': 'Producto Original',
    'alternative_product': 'Producto Alternativo',
    'search_alternative': 'Busca un producto alternativo',
    'you_need': 'Necesitas {qty} de {name}',
    'comparison': 'Comparación de Nutrientes',
    'nutrient': 'Nutriente',
    'original': 'Original',
    'alternative': 'Alternativa',
    'difference': 'Diferencia',
    'find_auto': '🔍 Buscar 5 Equivalentes Automáticamente',
    'threshold_label': 'Coincidencia dentro de ±{pct}%',
    'macro_warning': '⚠️ {nutrient} difiere un {pct:.1f}%',
    'good_match': '✅ Buena coincidencia dentro del umbral',

    # Photo upload
    'photo_source': 'Fuente de imagen',
    'take_photo': '📷 Tomar Foto',
    'upload_file': '📁 Subir Archivo',
    'detected_barcode': 'Código de Barras Detectado',
    'barcode_found': '✅ Código: {code} — buscando...',
    'barcode_not_found': 'No se detectó código de barras',
    'ocr_ingredients': 'OCR — Ingredientes',
    'ocr_nutrients': 'OCR — Nutrientes',
    'edit_before_upload': 'Editar antes de subir',
    'translate_to_english': '🌐 Traducir al inglés',
    'translating': 'Traduciendo...',
    'upload_to_off': '⬆️ Subir a Open Food Facts',
    'off_login_required': 'Se requiere cuenta de Open Food Facts para subir',
    'off_username': 'Usuario',
    'off_password': 'Contraseña',
    'upload_success': '✅ ¡Subido exitosamente!',
    'upload_failed': '❌ Error al subir: {err}',
    'pyzbar_missing': 'pyzbar no instalado — detección de código de barras no disponible. Ejecuta: pip install pyzbar',
    'easyocr_missing': 'easyocr no instalado — OCR no disponible. Ejecuta: pip install easyocr',
    'libzbar_missing': 'Librería del sistema libzbar no encontrada. Instala: sudo apt install libzbar0',

    # Settings
    'language': 'Idioma',
    'diet_mode': 'Modo Dietético Base',
    'vegan': 'Vegano',
    'vegetarian': 'Vegetariano',
    'both': 'Ambos (mostrar todo)',
    'extra_restrictions': 'Restricciones Adicionales',
    'no_garlic': 'Sin ajo',
    'no_onion': 'Sin cebolla',
    'no_caffeine': 'Sin cafeína',
    'no_alcohol': 'Sin alcohol',
    'no_mushrooms': 'Sin hongos/fungi',
    'no_gelatin': 'Sin gelatina / E120 / carmín',
    'jain': 'Dieta Jain (sin raíces, sin cebolla/ajo)',
    'dairy_variants': 'Variantes de Lácteos y Huevos',
    'lacto': 'Lacto-vegetariano (sin huevos)',
    'ovo': 'Ovo-vegetariano (sin lácteos)',
    'ovo_lacto': 'Ovo-lacto-vegetariano',
    'strict_egg_traces': 'Evitar productos que puedan contener trazas de huevo',
    'strict_egg_traces_help': 'Bloquea productos etiquetados como "puede contener huevo" o avisos similares de contaminación cruzada',
    'equivalents_threshold': 'Umbral de coincidencia para equivalentes',
    'save_settings': '💾 Guardar Configuración',
    'settings_saved': '✅ ¡Configuración guardada!',
    'reset_settings': 'Restablecer valores predeterminados',
    'country_filter': 'Filtro de País',
    'country_filter_help': 'Solo mostrar productos vendidos en los países seleccionados. Dejar vacío para ver todos.',
    'country_all': 'Todos los países',
    # About section
    'about': 'Acerca de',
    'version': 'Versión',
    'creator': 'Creador',
    'data_source': 'Fuente de Datos',
    'data_source_text': 'Todos los datos de productos provienen de [Open Food Facts](https://world.openfoodfacts.org/) — [Licencia Open Database (ODbL)](https://opendatacommons.org/licenses/odbl/)',
    'disclaimer': 'Esta aplicación no está afiliada con Open Food Facts.',
    'off_credit': '© Contribuidores de Open Food Facts',
}

_TRANSLATIONS = {'en': _EN, 'es': _ES}

DEFAULT_SETTINGS = {
    'mode': 'vegetarian',
    'no_garlic': False,
    'no_onion': False,
    'no_caffeine': False,
    'no_alcohol': False,
    'no_mushrooms': False,
    'no_gelatin': False,
    'jain': False,
    'lacto': False,
    'ovo': False,
    'ovo_lacto': False,
    'strict_egg_traces': False,
    'equivalents_threshold': 0.10,
    'lang': 'en',
    'countries': {'tags': [], 'cc': None},  # empty = all countries
}


def get_lang() -> str:
    """Return current language from session_state."""
    return st.session_state.get('settings', {}).get('lang', 'en')


def t(key: str, **kwargs) -> str:
    """Return translated string for key, with optional format kwargs."""
    lang = get_lang()
    d = _TRANSLATIONS.get(lang, _EN)
    text = d.get(key, _EN.get(key, key))
    if kwargs:
        try:
            text = text.format(**kwargs)
        except (KeyError, ValueError):
            pass
    return text


def init_session() -> None:
    """Initialise all required session_state keys with defaults, then overlay localStorage."""
    if 'settings' not in st.session_state:
        st.session_state['settings'] = dict(DEFAULT_SETTINGS)
    else:
        for k, v in DEFAULT_SETTINGS.items():
            st.session_state['settings'].setdefault(k, v)

    # Overlay with user's saved settings from browser localStorage
    # (returns None on first Streamlit render — that's fine, defaults are already set)
    if not st.session_state.get('_ls_loaded'):
        try:
            from src.storage import load_from_localstorage
            saved = load_from_localstorage()
            if saved and isinstance(saved, dict):
                for k, v in saved.items():
                    if k in DEFAULT_SETTINGS:
                        st.session_state['settings'][k] = v
                st.session_state['_ls_loaded'] = True
        except Exception:
            pass

    st.session_state.setdefault('selected_product', None)
    st.session_state.setdefault('search_results', [])
    st.session_state.setdefault('saved_portions', [])
    st.session_state.setdefault('portion_product', None)
    st.session_state.setdefault('equiv_original', None)
    # Theme: 'dark' | 'light' — propagated across all pages via session_state
    st.session_state.setdefault('theme', 'dark')
