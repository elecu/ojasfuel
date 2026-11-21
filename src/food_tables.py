"""
Generic, table-driven client for the official food composition tables.

One FoodTable per table, all reading the same compact JSON format
(src/<table>_db.json, built by scripts/parse_*.py):

    usda    USDA FoodData Central, SR Legacy (US; also the fallback for every
            country without an own table)
    cofid   UK: McCance and Widdowson's Composition of Foods Integrated Dataset 2021
    ciqual  France: ANSES-CIQUAL 2020 (French and English names)

SMAE (Mexico) has its own client (smae_client.py). table_for_country() picks the
table of the user's country. Carbohydrates are AVAILABLE carbohydrates in every
table (USDA is converted at build time; CoFID and CIQUAL already report them so).
"""

import json
import re
import unicodedata
from functools import lru_cache
from pathlib import Path

_DIR = Path(__file__).parent

# short key in the *_db.json files -> app display key
_NUTRIENT_KEYS = {
    'kcal': 'Energy (kcal)', 'p': 'Protein (g)', 'f': 'Fat (g)', 'c': 'Carbohydrates (g)',
    'fib': 'Fiber (g)', 'sug': 'Sugars (g)', 'sat': 'Saturated Fat (g)', 'na': 'Sodium (mg)',
    'k': 'Potassium (mg)', 'ca': 'Calcium (mg)', 'fe': 'Iron (mg)', 'mg': 'Magnesium (mg)',
    'zn': 'Zinc (mg)', 'vc': 'Vitamin C (mg)', 'va': 'Vitamin A (µg)', 'b9': 'Vitamin B9 (µg)',
    'b12': 'Vitamin B12 (µg)', 'vd': 'Vitamin D (µg)', 'chol': 'Cholesterol (mg)',
    'alc': 'Alcohol (g)', 'caf': 'Caffeine (mg)',
}


def _normalize(text: str) -> str:
    nfkd = unicodedata.normalize("NFKD", (text or "").lower().replace('œ', 'oe').replace('æ', 'ae'))
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", _normalize(text))


@lru_cache(maxsize=8)
def _load_json(path: str) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# ── Diet tags ────────────────────────────────────────────────────────────────
# USDA ----------------------------------------------------------------------
_PLANT = (True, True)
_USDA_CATEGORY_TAGS = {
    'Cereal Grains and Pasta': _PLANT,
    'Legumes and Legume Products': _PLANT,
    'Fruits and Fruit Juices': _PLANT,
    'Vegetables and Vegetable Products': _PLANT,
    'Nut and Seed Products': _PLANT,
    'Spices and Herbs': _PLANT,
    'Dairy and Egg Products': (False, True),
}
# Mixed categories: meat/fish/gelatin names were already dropped by
# scripts/parse_usda.py, so they are vegetarian; but they may hide egg / milk /
# honey, so vegan is only claimed for clearly plant-based names (below) and stays
# "uncertain" otherwise (resolve_diet turns uncertain into unknown, never "ok").
_USDA_MIXED = {'Fats and Oils', 'Baked Products', 'Breakfast Cereals', 'Snacks',
               'Sweets', 'Beverages', 'Soups, Sauces, and Gravies'}
_DAIRY_EGG = re.compile(
    r"\b(milks?|cheeses?|cream|creams|creamer|yogurts?|whey|casein|lactose|eggs?|custard|"
    r"pudding|cakes?|cookies?|brownies|pies?|muffins?|doughnuts?|donuts?|pastry|pastries|"
    r"croissants?|waffles?|pancakes?|biscuits?|honey|mayonnaise|fudge|toffee|butterscotch|"
    r"caramels?|butter|ghee|ice|sherbet|eggnog|milkshake|buttermilk|cocoa|chocolate|candies|"
    r"candy|margarine|spread|frosting|icing|danish|scones?|buns?|rolls?|bagels?|crackers?|"
    r"snack|snacks|mix|dessert|pizza|quiche|souffle|cheesecake|tiramisu)\b", re.I)
_DAIRY_NOT = re.compile(r"\b(soy|almond|rice|coconut|oat|hemp|cashew|peanut|nut|shea|"
                        r"cocoa|apple|sunflower|seed|sesame|tahini|fruit) (milk|butter)\b|"
                        r"cream of tartar|cream of wheat|cream of rice|ice tea|iced tea", re.I)
_USDA_PLANT_NAME = re.compile(
    r"^(oil|vinegar|sugars?|syrups?|molasses|beverages?, (tea|coffee|water|carbonated|"
    r"lemonade|alcoholic|fruit|citrus|orange|grape)|alcoholic beverage|cereals? ready-to-eat,? "
    r"(oat|corn|rice|wheat|bran|puffed|shredded)|cereals, (oats|quaker|cream of)|popcorn|"
    r"pretzels|chips|tortilla|bread|snacks, (potato|corn|rice|tortilla|popcorn|pretzels|trail|"
    r"banana|taro|vegetable|pork rind)|soup, (tomato|vegetable|lentil|minestrone|split pea|"
    r"onion|gazpacho|bean)|sauce, (tomato|soy|hot|salsa|chili|pasta|teriyaki)|salsa|"
    r"ketchup|mustard|jams|jellies|candies, (hard|jellybeans|gumdrops))", re.I)


def _usda_tags(entry: dict) -> dict:
    category, name = entry.get('c', ''), entry['n']
    tags = _USDA_CATEGORY_TAGS.get(category)
    if tags:
        return {"is_vegan": tags[0], "is_vegetarian": tags[1]}
    if category in _USDA_MIXED:
        if _DAIRY_EGG.search(_DAIRY_NOT.sub(' ', name)) and not _USDA_PLANT_NAME.search(name):
            return {"is_vegan": False, "is_vegetarian": True}
        if _USDA_PLANT_NAME.search(name) and not _DAIRY_EGG.search(_DAIRY_NOT.sub(' ', name)):
            return {"is_vegan": True, "is_vegetarian": True}
        return {"is_vegan": None, "is_vegetarian": True, "vegan_uncertain": True}
    return {"is_vegan": None, "is_vegetarian": None}


def _usda_gluten_free(entry: dict) -> bool:
    return entry.get('c') in {'Fruits and Fruit Juices', 'Vegetables and Vegetable Products',
                              'Legumes and Legume Products', 'Nut and Seed Products',
                              'Dairy and Egg Products'}


# CoFID + CIQUAL (English and French names) ---------------------------------
# Meat/fish/gelatin names were already dropped by the parsers, so every food is
# vegetarian unless it hides an animal ingredient (dishes, soups, sandwiches...).
_G_DAIRY_EGG = re.compile(
    r"\b(milks?|cheeses?|cheddar|stilton|brie|mozzarella|parmesan|feta|halloumi|ricotta|"
    r"quark|cream|yogh?urts?|whey|casein|lactose|eggs?|omelettes?|quiches?|custard|meringues?|"
    r"mayonnaise|honey|butter|ghee|ice cream|milkshake|rarebit|yorkshire|fromages?|lait|laits|"
    r"lactees?|lactes?|laitiers?|laitieres?|beurre|creme|cremes|yaourts?|yogourts?|oeufs?|"
    r"miel|glaces?|flan|bechamel|gratin|dauphinois|dauphine|duchesse|souffle|fondue|"
    r"raclette|chantilly|brioches?|croissants?|viennoiseries?|kefir|lassi|raita|tiramisu|"
    r"cheesecake|blancmange|panna cotta|clafoutis|ovaltine|horlicks|petit suisse|"
    r"mascarpone|camembert|emmental|comte|roquefort|gruyere|maroilles|tomme|chevre|brebis|"
    r"skimmed|semi skimmed|latte|cappuccino|gaufres?|waffles?|madeleines?|financiers?)\b", re.I)
_G_PLANT_ALT = re.compile(
    r"\b(lait|boisson|creme|yaourt|yogourt|dessert|fromage|beurre)s? (de |d |au |aux |a l |a la |"
    r"vegetal(e|aux)? ?(a base )?(de |d )?)?(soja|coco|amande|avoine|riz|noisette|chataigne|"
    r"cacahuete|cacao|karite|sesame|vegetal\w*|amandes)\b|"
    r"\b(soy|soya|soybean|almond|coconut|oat|rice|hazelnut|cashew|hemp|plant|vegetable|veggie) "
    r"(based )?(milk|cream|yogh?urts?|butter|drink|dessert|cheese)|"
    r"\b(peanut|cocoa|shea|nut|almond|cashew|seed|apple|sesame) butter|butter beans?|butternut|"
    r"buttercup|cream of (tartar|wheat|rice)|creamed coconut|coconut (milk|cream)|ice tea|"
    r"iced tea|honeydew|melon miel|creme de tartre|cremor", re.I)
_G_GELATIN_RISK = re.compile(
    r"\b(mousses?|bavarois|trifle|cheesecake|panna cotta|gelifie\w*|jellies|jelly|gelee|aspic|"
    r"entremets|charlotte|liegeois|dessert lacte|creme dessert|marshmallows?|guimauves?)\b", re.I)
_G_DISH_CUE = re.compile(
    r"\b(legumes?|vegetables?|veg|veggie|vegetari\w*|vegetal\w*|vegan\w*|tomates?|tomatoes|"
    r"fromages?|cheese|cheeses|oeufs?|eggs?|champignons?|mushrooms?|margherita|soja|soy\w*|"
    r"tofu|lentilles?|lentils?|pois|peas?|haricots?|beans?|epinards?|spinach|aubergines?|"
    r"eggplant|courgettes?|zucchini|poireaux?|leeks?|ratatouille|falafel|tempeh|taboule|"
    r"potiron|pumpkin|carottes?|carrots?|asperges?|cresson|watercress|gaspacho|gazpacho|"
    r"minestrone|pistou|pommes? de terre|potatoes?|oignons?|onions?|chou|cabbage|"
    r"patates?|dahl|dhal|curry|pasta|pates|noodles?|rice|riz)\b", re.I)
_G_AVERAGE = re.compile(r"aliment moyen|\(average|average\)|\(average food\)", re.I)
_G_PLANT_NAME = re.compile(
    r"^(bread|rice cakes?|crispbread|pitta|chapati|tortilla|naan|popcorn|oil|vinegar|sugars?|"
    r"syrup|molasses|treacle|jam|marmalade|mustard|salt|yeast|baking powder|bicarbonate|water|"
    r"tea|coffee|cola|lemonade|squash|cordial|juice|spirits|crisps|potato crisps|chutney|"
    r"pickle|ketchup|brown sauce|apple sauce|sauce, (tomato|soy|chilli|barbecue)|"
    r"soup, (vegetable|tomato|lentil|minestrone|gazpacho|potato|carrot|mushroom)|"
    r"pain|baguette|farine|sucre|sirop|vinaigre|sel\b|moutarde|confiture|huile|cafe|the\b|"
    r"eau|jus|soda|limonade|tortilla|cornichons?|ketchup|sauce soja|sauce tomate)", re.I)

_CIQUAL_PLANT_SUBS = {
    'vegetables', 'potatoes and other tubers', 'legumes', 'fruits', 'nuts and seeds',
    'pasta, rice and grains', 'vegetable oils', 'herbs', 'spices', 'seaweed', 'water', 'jam',
    'salts'}
_CIQUAL_DAIRY_SUBS = {'milk', 'dairy products and similar', 'cheese and similar',
                      'cream and similar', 'eggs', 'butters'}
_CIQUAL_DISH_SUBS = {'dishes', 'pizzas, crepe and pies', 'sandwiches', 'soups',
                     'savoury pastries and other starters'}
_COFID_PLANT_CODES = ('AA', 'AC', 'AD', 'DAE', 'DAM', 'DAP', 'DAR', 'DB', 'DF', 'DG', 'DI',
                      'F', 'G', 'H', 'OC', 'OE')
_COFID_DAIRY_CODES = ('BA', 'BC', 'BJ', 'BL', 'BN', 'BP', 'BR', 'CA', 'CD')


def _generic_tags(texts, *, plant: bool, dairy: bool, dish: bool) -> dict:
    """Diet tags for a CoFID/CIQUAL food from its name(s) and group."""
    text = _normalize(' '.join(t for t in texts if t)).replace("'", ' ')
    alt = _G_PLANT_ALT.search(text)
    stripped = _G_PLANT_ALT.sub(' ', text)
    risky = bool(_G_GELATIN_RISK.search(text))
    if _G_DAIRY_EGG.search(stripped):
        return ({"is_vegan": False, "is_vegetarian": None, "vegetarian_uncertain": True}
                if risky else {"is_vegan": False, "is_vegetarian": True})
    unknown = {"is_vegan": None, "is_vegetarian": None, "vegan_uncertain": True,
               "vegetarian_uncertain": True}  # may hide meat/fish/gelatin: never "ok"
    if risky:
        return unknown
    if dish:
        if _G_AVERAGE.search(text) or not _G_DISH_CUE.search(text):
            return unknown
        return {"is_vegan": None, "is_vegetarian": True, "vegan_uncertain": True}
    if dairy and not alt:
        return {"is_vegan": False, "is_vegetarian": True}
    if plant or alt or _G_PLANT_NAME.search(text):
        return {"is_vegan": True, "is_vegetarian": True}
    return {"is_vegan": None, "is_vegetarian": True, "vegan_uncertain": True}


def _cofid_tags(entry: dict) -> dict:
    g = entry.get('g', '')
    return _generic_tags(
        [entry['n']],
        plant=g.startswith(_COFID_PLANT_CODES),
        dairy=g.startswith(_COFID_DAIRY_CODES),
        dish=False)


def _ciqual_tags(entry: dict) -> dict:
    sub = entry.get('s', '')
    return _generic_tags(
        [entry['n'], entry.get('nf', '')],
        plant=sub in _CIQUAL_PLANT_SUBS, dairy=sub in _CIQUAL_DAIRY_SUBS,
        dish=sub in _CIQUAL_DISH_SUBS)


def _cofid_gluten_free(entry: dict) -> bool:
    return entry.get('g', '').startswith(('DAE', 'DAM', 'DB', 'DF', 'DG', 'DI', 'F', 'G', 'BA', 'BC',
                                          'BJ', 'BL', 'BN', 'CA', 'H'))


def _ciqual_gluten_free(entry: dict) -> bool:
    return entry.get('s') in {'vegetables', 'potatoes and other tubers', 'legumes', 'fruits',
                              'nuts and seeds', 'milk', 'cheese and similar', 'cream and similar',
                              'eggs', 'butters', 'vegetable oils'}



# ── Query translation (Spanish / UK English → USDA American English) ────────
_STOP = {'de', 'del', 'la', 'el', 'los', 'las', 'con', 'sin', 'al', 'en', 'y', 'o', 'un', 'una'}

_ES_EN = {
    'arroz': 'rice', 'cocido': 'cooked', 'cocida': 'cooked', 'cocidos': 'cooked',
    'cocidas': 'cooked', 'hervido': 'boiled', 'hervida': 'boiled', 'hervidos': 'boiled',
    'hervidas': 'boiled', 'crudo': 'raw', 'cruda': 'raw', 'crudos': 'raw', 'crudas': 'raw',
    'horneado': 'baked', 'horneada': 'baked', 'asado': 'roasted', 'asada': 'roasted',
    'frito': 'fried', 'frita': 'fried', 'fritos': 'fried', 'fritas': 'fried',
    'tostado': 'toasted', 'tostada': 'toasted', 'enlatado': 'canned', 'enlatada': 'canned',
    'congelado': 'frozen', 'congelada': 'frozen', 'seco': 'dry', 'seca': 'dry',
    'secos': 'dry', 'secas': 'dry', 'integral': 'whole', 'blanco': 'white', 'blanca': 'white',
    'negro': 'black', 'negra': 'black', 'negros': 'black', 'rojo': 'red', 'roja': 'red',
    'rojos': 'red', 'verde': 'green', 'verdes': 'green', 'dulce': 'sweet', 'dulces': 'sweet',
    'papa': 'potato', 'papas': 'potato', 'patata': 'potato', 'patatas': 'potato',
    'plátano': 'banana', 'platano': 'banana', 'banano': 'banana', 'manzana': 'apple',
    'frijol': 'beans', 'frijoles': 'beans', 'judía': 'beans', 'judia': 'beans',
    'judías': 'beans', 'judias': 'beans', 'alubia': 'beans', 'alubias': 'beans',
    'habichuela': 'beans', 'habichuelas': 'beans', 'poroto': 'beans', 'porotos': 'beans',
    'ejote': 'snap beans', 'ejotes': 'snap beans', 'lenteja': 'lentils', 'lentejas': 'lentils',
    'garbanzo': 'chickpeas', 'garbanzos': 'chickpeas', 'chícharo': 'peas', 'chicharo': 'peas',
    'chícharos': 'peas', 'guisante': 'peas', 'guisantes': 'peas', 'arveja': 'peas',
    'arvejas': 'peas', 'haba': 'broad beans', 'habas': 'broad beans',
    'pan': 'bread', 'avena': 'oats', 'leche': 'milk', 'queso': 'cheese', 'huevo': 'egg',
    'huevos': 'egg', 'aguacate': 'avocado', 'palta': 'avocado', 'zanahoria': 'carrots',
    'zanahorias': 'carrots', 'brócoli': 'broccoli', 'brocoli': 'broccoli',
    'espinaca': 'spinach', 'espinacas': 'spinach', 'jitomate': 'tomatoes',
    'tomate': 'tomatoes', 'cebolla': 'onions', 'ajo': 'garlic', 'nuez': 'walnuts',
    'nueces': 'walnuts', 'almendra': 'almonds', 'almendras': 'almonds',
    'cacahuate': 'peanuts', 'cacahuates': 'peanuts', 'cacahuete': 'peanuts',
    'cacahuetes': 'peanuts', 'maní': 'peanuts', 'mani': 'peanuts', 'pistache': 'pistachio',
    'pistachos': 'pistachio', 'avellana': 'hazelnuts', 'avellanas': 'hazelnuts',
    'castaña': 'chestnuts', 'aceite': 'oil', 'mantequilla': 'butter', 'yogur': 'yogurt',
    'yogurt': 'yogurt', 'maíz': 'corn', 'maiz': 'corn', 'elote': 'corn', 'choclo': 'corn',
    'tortilla': 'tortilla', 'pasta': 'pasta', 'espagueti': 'spaghetti', 'espaguetis': 'spaghetti',
    'espagueti': 'spaghetti', 'macarrones': 'macaroni', 'macarrón': 'macaroni',
    'fideos': 'noodles', 'fideo': 'noodles', 'quinoa': 'quinoa', 'quinua': 'quinoa',
    'camote': 'sweet potato', 'boniato': 'sweet potato', 'batata': 'sweet potato',
    'calabacita': 'zucchini', 'calabacín': 'zucchini', 'calabacin': 'zucchini',
    'calabaza': 'squash', 'berenjena': 'eggplant', 'pimiento': 'pepper', 'pimientos': 'pepper',
    'chile': 'peppers', 'champiñón': 'mushrooms', 'champiñon': 'mushrooms',
    'champinon': 'mushrooms', 'champiñones': 'mushrooms', 'hongos': 'mushrooms',
    'hongo': 'mushrooms', 'setas': 'mushrooms', 'seta': 'mushrooms',
    'naranja': 'orange', 'fresa': 'strawberries', 'fresas': 'strawberries',
    'uva': 'grapes', 'uvas': 'grapes', 'piña': 'pineapple', 'pina': 'pineapple',
    'mango': 'mango', 'sandía': 'watermelon', 'sandia': 'watermelon', 'melón': 'melons',
    'melon': 'melons', 'pera': 'pears', 'durazno': 'peaches', 'melocotón': 'peaches',
    'melocoton': 'peaches', 'limón': 'lemon', 'limon': 'lemon', 'lima': 'lime',
    'toronja': 'grapefruit', 'pomelo': 'grapefruit', 'cereza': 'cherries',
    'cerezas': 'cherries', 'ciruela': 'plums', 'ciruelas': 'plums', 'coco': 'coconut',
    'dátil': 'dates', 'datil': 'dates', 'dátiles': 'dates', 'higo': 'figs', 'higos': 'figs',
    'arándano': 'blueberries', 'arandano': 'blueberries', 'arándanos': 'blueberries',
    'frambuesa': 'raspberries', 'frambuesas': 'raspberries', 'mora': 'blackberries',
    'moras': 'blackberries', 'albaricoque': 'apricots', 'chabacano': 'apricots',
    'lechuga': 'lettuce', 'pepino': 'cucumber', 'coliflor': 'cauliflower', 'col': 'cabbage',
    'repollo': 'cabbage', 'apio': 'celery', 'rábano': 'radishes', 'rabano': 'radishes',
    'betabel': 'beets', 'remolacha': 'beets', 'nabo': 'turnips', 'puerro': 'leeks',
    'alcachofa': 'artichokes', 'espárrago': 'asparagus', 'esparrago': 'asparagus',
    'espárragos': 'asparagus', 'acelga': 'chard', 'perejil': 'parsley', 'albahaca': 'basil',
    'jengibre': 'ginger', 'canela': 'cinnamon', 'vinagre': 'vinegar', 'mostaza': 'mustard',
    'mayonesa': 'mayonnaise', 'azúcar': 'sugar', 'azucar': 'sugar', 'sal': 'salt',
    'harina': 'flour', 'trigo': 'wheat', 'cebada': 'barley', 'centeno': 'rye',
    'soya': 'soy', 'soja': 'soy', 'miel': 'honey', 'mermelada': 'jams', 'galleta': 'cookies',
    'galletas': 'cookies', 'jugo': 'juice', 'zumo': 'juice', 'café': 'coffee', 'cafe': 'coffee',
    'té': 'tea', 'te': 'tea', 'agua': 'water', 'cerveza': 'beer', 'vino': 'wine',
    'crema': 'cream', 'nata': 'cream', 'requesón': 'cottage', 'requeson': 'cottage',
    'helado': 'ice cream', 'palomitas': 'popcorn', 'cereal': 'cereal', 'semilla': 'seeds',
    'semillas': 'seeds', 'girasol': 'sunflower', 'ajonjolí': 'sesame', 'ajonjoli': 'sesame',
    'sésamo': 'sesame', 'sesamo': 'sesame', 'linaza': 'flaxseed', 'chocolate': 'chocolate',
    'tofu': 'tofu', 'hummus': 'hummus', 'galleta': 'cookies', 'pastel': 'cake',
    'tarta': 'cake', 'donas': 'doughnuts', 'sopa': 'soup', 'salsa': 'sauce',
    'aceituna': 'olives', 'aceitunas': 'olives', 'ciruela pasa': 'prunes',
    'chayote': 'chayote', 'nopal': 'cactus', 'nopales': 'cactus', 'jícama': 'jicama',
}

_ES_PHRASES = {
    'col de bruselas': 'brussels sprouts', 'coles de bruselas': 'brussels sprouts',
    'papa dulce': 'sweet potato', 'frijol negro': 'black beans', 'frijoles negros': 'black beans',
    'leche de soya': 'soy milk', 'leche de soja': 'soy milk', 'leche de almendra': 'almond milk',
    'aceite de oliva': 'olive oil', 'mantequilla de cacahuate': 'peanut butter',
    'mantequilla de maní': 'peanut butter', 'pan integral': 'whole wheat bread',
    'pan blanco': 'white bread', 'arroz integral': 'brown rice', 'arroz blanco': 'white rice',
    'papas fritas': 'french fried', 'patatas fritas': 'french fried',
}

# UK/AU English → American English (the words USDA uses)
_UK_US = {
    'aubergine': 'eggplant', 'aubergines': 'eggplant', 'courgette': 'zucchini',
    'courgettes': 'zucchini', 'porridge': 'oatmeal', 'swede': 'rutabaga',
    'rocket': 'arugula', 'coriander': 'cilantro', 'biscuits': 'cookies', 'biscuit': 'cookies',
    'jam': 'jams', 'sweetcorn': 'corn', 'beetroot': 'beets', 'mangetout': 'snow peas',
    'yoghurt': 'yogurt', 'wholemeal': 'whole wheat', 'wholegrain': 'whole grain',
    'icing': 'frosting', 'prawn': 'shrimp', 'cornflour': 'cornstarch', 'maize': 'corn',
    'capsicum': 'peppers', 'chickpea': 'chickpeas', 'minced': 'ground', 'scone': 'biscuits',
}
_UK_PHRASES = {
    'jacket potato': 'baked potato', 'mange tout': 'snow peas', 'spring onion': 'onions spring',
    'spring onions': 'onions spring', 'sweet corn': 'corn', 'broad beans': 'broadbeans',
    'baked beans': 'baked beans', 'caster sugar': 'sugar', 'icing sugar': 'powdered sugar',
    'double cream': 'cream heavy', 'single cream': 'cream light', 'plain flour': 'wheat flour white',
    'self raising flour': 'wheat flour white self-rising', 'green pepper': 'peppers green',
}
# words that mean different things in UK vs US; only applied for UK-style countries
_UK_ONLY = {'chips': 'french fried', 'crisps': 'potato chips'}
_UK_COUNTRIES = {'gb', 'uk', 'ie', 'au', 'nz', 'za', 'in', 'sg', 'my', 'mt', 'cy'}

# US → UK vocabulary (CoFID and CIQUAL's English names are British)
_US_UK = {
    'eggplant': 'aubergine', 'zucchini': 'courgette', 'cilantro': 'coriander',
    'arugula': 'rocket', 'cookies': 'biscuits', 'cookie': 'biscuits', 'rutabaga': 'swede',
    'beets': 'beetroot', 'shrimp': 'prawn', 'cornstarch': 'cornflour', 'frosting': 'icing',
    'oatmeal': 'porridge', 'candy': 'sweets', 'candies': 'sweets',
    'jams': 'jam', 'peppers': 'pepper', 'chickpeas': 'chick peas', 'chickpea': 'chick peas',
}
_US_UK_PHRASES = {'potato chips': 'crisps', 'french fried': 'chips', 'french fries': 'chips',
                  'sweet potato': 'sweet potato', 'snow peas': 'mangetout', 'ice cream': 'ice cream'}

# preparation-state synonyms: a query word also matches these name words
_STATE_SYNONYMS = {
    'cooked': {'cooked', 'boiled', 'baked', 'roasted', 'steamed', 'stewed', 'grilled',
               'microwaved', 'fried', 'braised', 'poached'},
    'cuit': {'cuit', 'cuite', 'bouilli', 'bouillie', 'roti', 'rotie', 'grille', 'grillee',
             'vapeur', 'poele', 'poelee', 'saute', 'sautee', 'braise', 'braisee', 'frit',
             'frite', 'four', 'poche', 'pochee'},
}


def translate_query(query: str, cc: str | None = None, to_uk: bool = False) -> str:
    """Rewrite a Spanish / UK-English food query into USDA's American English
    (or, with to_uk, into British English for CoFID / CIQUAL's English names).

    Unknown words (e.g. French ones) are kept as they are. Single pass: a
    translated word is never translated again (crisps -> chips, not -> french fries).
    """
    words = _normalize((query or '').replace('-', ' ')).split()
    uk = (cc or '').lower() in _UK_COUNTRIES
    # phrase table keys are accent-stripped for comparison
    phrases = {_normalize(k): v for k, v in {**_ES_PHRASES, **_UK_PHRASES}.items()}
    # strip accents on the single-word tables too
    es = {_normalize(k): v for k, v in _ES_EN.items()}
    ukus = {_normalize(k): v for k, v in _UK_US.items()}
    out, i = [], 0
    while i < len(words):
        if i + 2 < len(words) + 0 and ' '.join(words[i:i + 3]) in phrases:
            out.append(phrases[' '.join(words[i:i + 3])])
            i += 3
            continue
        if i + 1 < len(words) and ' '.join(words[i:i + 2]) in phrases:
            out.append(phrases[' '.join(words[i:i + 2])])
            i += 2
            continue
        w = words[i]
        i += 1
        if w in _STOP:
            continue
        if uk and w in _UK_ONLY:
            out.append(_UK_ONLY[w])
        elif w in ukus:
            out.append(ukus[w])
        elif w in es:
            out.append(es[w])
        else:
            out.append(w)
    res = ' '.join(out) if out else _normalize(query or '')
    if to_uk:
        res = _to_uk(res)
    return res


def _to_uk(text: str) -> str:
    for k, v in _US_UK_PHRASES.items():
        text = re.sub(r'\b' + re.escape(k) + r'\b', v, text)
    return ' '.join(_US_UK.get(w, w) for w in text.split())


def _variants(w: str) -> set[str]:
    v = {w}
    if len(w) > 3:
        if w.endswith('ies'):
            v.add(w[:-3] + 'y')
        if w.endswith('es'):
            v.add(w[:-2])
        if w.endswith('s'):
            v.add(w[:-1])
    return v


def _same_word(w: str, t: str, synonyms: dict | None = None) -> bool:
    """Query word w is the name token t, a plural/gender form of it, or a state synonym."""
    if t in _variants(w) or t in (synonyms or {}).get(w, ()):
        return True
    return t.startswith(w) and t[len(w):] in ('e', 's', 'es', 'x')


def _word_in(w: str, name_tokens: list[str], synonyms: dict | None = None) -> int | None:
    """Index of the first name token that the query word matches (prefix, plural-aware,
    optionally with preparation-state synonyms)."""
    vs = _variants(w)
    syn = (synonyms or {}).get(w)
    for idx, t in enumerate(name_tokens):
        if any(t.startswith(x) for x in vs) or (syn and t in syn):
            return idx
    return None


# descriptor words that do not make a food "less generic" (English and French)
_FREE = {'white', 'regular', 'enriched', 'long', 'grain', 'whole', 'plain', 'without', 'salt',
         'added', 'drained', 'solids', 'and', 'liquids', 'all', 'types', 'commercially',
         'prepared', 'mature', 'seeds', 'fat', 'not', 'nfs', 'ns', 'as', 'to', 'form',
         'with', 'in', 'a', 'of', 'or'}
_FREE_EXTRA = {'flesh', 'only', 'average', 'unsalted', 'salted', 'water', 'old', 'raw',
               'blanc', 'blanche', 'non', 'sale', 'sel', 'sans', 'de', 'du', 'des', 'la', 'le',
               'les', 'au', 'aux', 'a', 'l', 'd', 'et', 'ou', 'en', 'moyen', 'aliment', 'nature',
               'pulpe', 'pulp', 'unsalted', 'general', 'type'}
_PENALTY = {'parboiled', 'instant', 'precooked', 'unenriched', 'fortified', 'imitation',
            'substitute', 'flavored', 'sweetened', 'frosting', 'candied', 'pickled',
            'dehydrated', 'powder', 'mix', 'babyfood', 'frozen', 'canned', 'dried'}
_PENALTY_EXTRA = {'flavoured', 'flavour', 'tinned', 'ready', 'retail', 'takeaway', 'deshydrate',
                  'deshydratee', 'instantane', 'surgele', 'surgelee', 'appertise', 'appertisee',
                  'prepacked', 'preemballe', 'preemballee', 'aromatise', 'aromatisee',
                  'sucre', 'sucree', 'reconstituee', 'poudre', 'enrichi', 'enrichie'}


class FoodTable:
    """One official food composition table (see module docstring)."""

    def __init__(self, source, filename, brand, tags_fn, gluten_fn, *, to_uk=False,
                 synonyms=None, free=None, penalty=None, strict=False):
        self.source = source
        self.path = str(_DIR / filename)
        self.brand = brand
        self._tags_fn = tags_fn
        self._gluten_fn = gluten_fn
        self.to_uk = to_uk
        self.synonyms = synonyms
        self.free = _FREE | (free or set())
        self.penalty = _PENALTY | (penalty or set())
        # strict (CoFID, CIQUAL): a query word that only matches the START of a longer
        # word ("lait" ~ "laitue", "bread" ~ "breadfruit") costs extra, and a different
        # compound head ("Lentil pie" for "lentils") costs more
        self.strict = strict
        self.head_penalty = 2.5 if strict else 1.5

    # ── data ──
    def load(self) -> list[dict]:
        return _load_json(self.path)

    @property
    def index(self) -> list[tuple]:
        return _index(self.source)

    def entry(self, food_id: str) -> dict | None:
        return next((e for e in self.load() if e['i'] == food_id), None)

    def gluten_free(self, product: dict) -> bool:
        return bool(self._gluten_fn(product.get('_raw') or {}))

    # ── conversion ──
    def to_product(self, entry: dict, lang: str = 'en') -> dict:
        """Convert a database entry to the shape of api_client.format_product()."""
        category = entry.get('c', '')
        name = (entry.get('nf') or entry['n']) if lang == 'fr' else entry['n']
        nutrition = {_NUTRIENT_KEYS[k]: v for k, v in (entry.get('nu') or {}).items()
                     if k in _NUTRIENT_KEYS}
        portion_g = entry.get('pg')
        hint = name
        if entry.get('nf'):  # both languages help the allergen / diet classifier
            hint = f"{entry['n']} / {entry['nf']}"
        if category in ('Dairy and Egg Products',):
            hint += f' {category}'
        sub = entry.get('s', '')
        p = {
            "id": entry["i"],
            "name": name,
            "brand": self.brand,
            "ingredients": hint,
            "image_url": None,
            "url": None,
            "nutrition": nutrition,
            "labels": f"{self.brand}: {category}",
            "categories": f"{category}, {sub}" if sub else category,
            "quantity": entry.get('pl', ''),
            "serving_size": entry.get('pl', ''),
            "nutriscore": None,
            "countries_tags": [],
            "_off_tags": self._tags_fn(entry),
            "_classification": None,
            "_needs_full_load": False,
            "_raw": entry,
            "_source": self.source,
            "_table_category": category,
            "_table_subgroup": sub,
            "_table_portion_g": portion_g,
            "_name_lang": lang,
        }
        if self.source == 'usda':  # backward-compatible keys
            p["_usda_portion_g"] = portion_g
            p["_usda_category"] = category
        return p

    # ── search ──
    def _rank(self, q_words, q_norm, name_tokens, name_norm, raw_name):
        exact = 0 if name_norm == q_norm else 1
        idxs = [_word_in(w, name_tokens, self.synonyms) for w in q_words]
        first = 0 if 0 in idxs else 1
        matched = {i for i in idxs if i is not None}
        cost = 0.0
        if self.strict:
            for w, i in zip(q_words, idxs):
                if i is not None and not _same_word(w, name_tokens[i], self.synonyms):
                    cost += 3
            if ('white' in name_tokens or 'blanc' in name_tokens) and \
                    {'egg', 'eggs', 'oeuf', 'oeufs'} & set(name_tokens):
                cost += 3  # egg white is not "the" egg
        for i, t in enumerate(name_tokens):
            if i in matched:
                continue
            if t in self.penalty:
                cost += 3
            elif t == 'with' and 'salt' in name_tokens and 'without' not in name_tokens:
                cost += 3
            elif t not in self.free:
                cost += 1
        # compound head ("Rice crackers, ...", "Potato salad") is a different food
        seg0 = _tokens(raw_name.split(',')[0])
        if len([t for i, t in enumerate(seg0) if i not in matched and t not in self.free]) > 0:
            cost += self.head_penalty
        # brand names are written in capitals (UNCLE BEN'S)
        if re.search(r"\b[A-Z]{3,}\b", raw_name):
            cost += 4
        return (exact, first, cost, len(name_tokens), name_norm)

    def _queries(self, query: str, cc) -> list[str]:
        translated = translate_query(query, cc, to_uk=self.to_uk)
        attempts = [translated]
        orig = _normalize(query.strip())
        if orig != translated:
            attempts.append(orig)
        return attempts

    def search_by_name(self, query: str, page_size: int = 20, cc: str | None = None) -> list[dict]:
        """Every word of the (translated) query must appear in the name."""
        if not query or not query.strip():
            return []
        for q in self._queries(query, cc):
            q_words = q.split()
            if not q_words:
                continue
            best: dict[str, tuple] = {}
            for toks, norm, e, lang, raw in self.index:
                if all(_word_in(w, toks, self.synonyms) is not None for w in q_words):
                    rk = self._rank(q_words, q, toks, norm, raw)
                    cur = best.get(e['i'])
                    if cur is None or rk < cur[0]:
                        best[e['i']] = (rk, e, lang)
            if best:
                hits = sorted(best.values(), key=lambda x: x[0])
                return [self.to_product(e, lang) for _, e, lang in hits[:page_size]]
        return []

    def fuzzy(self, query: str, limit: int = 10, cc: str | None = None) -> list[dict]:
        """Typo-tolerant search: every query word must closely match a name word."""
        from src.search_smart import _word_close
        q = translate_query(query or '', cc, to_uk=self.to_uk)
        q_words = q.split()
        if not q_words:
            return []
        best: dict[str, tuple] = {}
        for toks, norm, e, lang, raw in self.index:
            if all(any(_word_close(qw, t) or _word_close(qw.rstrip('s'), t) for t in toks)
                   for qw in q_words):
                rk = self._rank(q_words, q, toks, norm, raw)
                cur = best.get(e['i'])
                if cur is None or rk < cur[0]:
                    best[e['i']] = (rk, e, lang)
        hits = sorted(best.values(), key=lambda x: x[0])
        return [self.to_product(e, lang) for _, e, lang in hits[:limit]]

    def by_category(self, category: str, limit: int = 400, subgroup: str | None = None,
                    lang: str = 'en') -> list[dict]:
        """Products of one food category (and subgroup when given)."""
        out = []
        for e in self.load():
            if e.get('c') == category and (subgroup is None or e.get('s') == subgroup):
                out.append(self.to_product(e, lang))
                if len(out) >= limit:
                    break
        return out


@lru_cache(maxsize=8)
def _index(source: str) -> list[tuple]:
    """[(name tokens, normalized name, entry, lang, raw name)], one row per language."""
    t = TABLES[source]
    rows = []
    for e in t.load():
        rows.append((_tokens(e['n']), _normalize(e['n']), e, 'en', e['n']))
        nf = e.get('nf')
        if nf and nf != e['n']:
            rows.append((_tokens(nf), _normalize(nf), e, 'fr', nf))
    return rows


TABLES: dict[str, FoodTable] = {
    'usda': FoodTable('usda', 'usda_db.json', 'USDA FoodData Central', _usda_tags, _usda_gluten_free),
    'cofid': FoodTable('cofid', 'cofid_db.json', 'UK CoFID (McCance & Widdowson)', _cofid_tags,
                       _cofid_gluten_free, to_uk=True, synonyms=_STATE_SYNONYMS),
    'ciqual': FoodTable('ciqual', 'ciqual_db.json', 'ANSES-CIQUAL', _ciqual_tags,
                        _ciqual_gluten_free, to_uk=True, synonyms=_STATE_SYNONYMS,
                        penalty=_PENALTY_EXTRA),
}
_COFID_FREE = {'boiled', 'green', 'brown', 'red', 'new', 'pasteurised', 'whole'}
for _t in ('cofid', 'ciqual'):
    TABLES[_t].strict = True
    TABLES[_t].free |= _FREE_EXTRA | _COFID_FREE
    TABLES[_t].penalty |= _PENALTY_EXTRA
TABLES['cofid'].head_penalty = 2.5
TABLES['cofid'].free |= {'dried'}
TABLES['ciqual'].head_penalty = 0.5  # French: "Lait entier, ...", "Riz basmati, ..."
TABLES['cofid'].penalty |= {'salted'}
TABLES['cofid'].penalty -= {'dried', 'canned', 'frozen'}
TABLES['ciqual'].penalty -= {'dried'}

GENERIC_SOURCES = tuple(TABLES)          # sources handled by FoodTable
TABLE_SOURCES = ('smae',) + GENERIC_SOURCES  # every "official table" source


def get_table(source: str) -> FoodTable:
    return TABLES[source]


# country (OFF cc) -> official table; everything else falls back to USDA (US reference)
_COUNTRY_TABLE = {'mx': 'smae', 'gb': 'cofid', 'fr': 'ciqual', 'us': 'usda'}


def table_for_country(cc: str | None) -> str:
    return _COUNTRY_TABLE.get((cc or '').lower(), 'usda')


def is_reference_only(source: str, cc: str | None) -> bool:
    """True when USDA values are shown to someone whose country has another table
    (or none): they are US reference values, not their national table."""
    return source == 'usda' and bool(cc) and cc.lower() != 'us'
