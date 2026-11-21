"""Shared "is this food animal-derived?" filters for the CoFID and CIQUAL parsers.

Extends scripts/parse_usda.py's English rules (meat / fish / gelatin / lard ...)
with British English words (prawn, kipper, dripping ...) and French words (viande,
boeuf, jambon, poisson, thon, gelatine ...). Names are matched accent-insensitively.
Only used at build time; the databases contain no animal-named foods.
"""

import re
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import parse_usda  # noqa: E402  (trusted repo script)

_ANIMAL_EN_EXTRA = re.compile(
    r'\b(prawns?|scampi|whelks?|cockles?|mussels?|winkles?|kippers?|pilchards?|whitebait|plaice|'
    r'skate|eels?|halibut|sprats?|bloaters?|gammon|haggis|faggots?|dripping|pate|steaks?|'
    r'cutlets?|kebabs?|surimi|seafood|poultry|offal|blood|black pudding|bovril|oxo|monkfish|'
    r'swordfish|bream|coley|whiting|dab|cuttlefish|calamari|scallops?|langoustines?|tilapia|'
    r'pangasius|mullet|hake|carp|pike|perch|grouse|partridge|pigeon|hare|gelatine|isinglass|'
    r'shellfish|crustaceans?|sushi|sashimi|mincemeat|pollock|pollack|salmon|haddock|'
    r'moussaka|bolognese|bolognaise|carbonara|shepherd\'?s pie|cottage pie|scotch egg|'
    r'sausage rolls?|toad in the hole|pasties|pasty|chilli con carne|fish|jelly|jellies|'
    r'gums?|pastilles?|marshmallows?|chicken|hot dogs?|spam|corned|brawn|pemmican|rennet|'
    r'cantonese|gelee au madere|cockerels?|cheeseburgers?|dumplings?|miso soup|onion soup|lorraine|pastichio|pastitsio|bouillabaisse|goulash|mulligatawny|christmas pudding|'
    r'mince pies?|french onion|suet|stock cubes?|gravy|worcester(shire)?|caesar)\b|'
    r'complan powder, savoury|soup, instant|build[- ]?up powder, soup|instant, dried',
    re.I)
# plant / dairy uses of otherwise-animal words
_EN_OK = re.compile(
    r"kidney beans?|beans?,? kidney|red kidney|heart(s)? of palm|artichoke hearts?|"
    r"(goats?|sheeps?|ewes?|buffalo)'?s?[ ,]+(milk|cheese|yogh?urt|cream)|"
    r"(milk|cheese|yogh?urt|cream)[ ,]+(of )?(goats?|sheeps?|ewes?)|"
    r"chewing gum|gum arabic|guar gum|xanthan gum|locust bean gum|"
    r"vegetarian (jelly|gums?)|"
    r"\beggs?,? (chicken|duck|goose|quail|hens?|bantam)s?\b|(chicken|duck|goose|quail|hens?)'?s? eggs?|"
    r"meat[- ]?free|vegetarian|vegan|veggie|quorn|soya mince|textured vegetable protein|"
    r"vegetable (burger|sausage|mince)|nut cutlet|bean burger|eggless|fish-free|"
    r"fish sauce substitute|cod liver oil capsules?|jam\b|honey|plum jelly|marmalade", re.I)

_ANIMAL_FR = re.compile(
    r"\b(viandes?|boeufs?|veau|porcs?|poulets?|dindes?|dindon|canards?|oies?|pintade|lapin|agneau|"
    r"mouton|cheval|gibiers?|sanglier|cerf|chevreuil|jambons?|saucisses?|saucissons?|lardons?|"
    r"lard|bacon|chorizo|merguez|mortadelle|rillettes?|terrines?|foies?|boudins?|andouilles?|"
    r"andouillettes?|cervelas|knacks?|hot dog|cordon bleu|nuggets?|steaks?|bifteck|escalopes?|"
    r"gigot|tripes?|rognons?|cervelles?|abats?|poissons?|thons?|saumons?|truites?|sardines?|"
    r"maquereaux?|harengs?|morues?|cabillauds?|colin|merlu|lieu|soles?|raies?|dorades?|daurades?|"
    r"bar|lottes?|eglefin|fletan|espadon|anchois|crevettes?|gambas|langoustines?|homards?|"
    r"crabes?|tourteaux?|moules?|huitres?|coquillages?|fruits de mer|crustaces?|mollusques?|"
    r"calamars?|encornets?|seiches?|poulpes?|escargots?|grenouilles?|surimi|tarama|caviar|"
    r"fumet|gelatines?|saindoux|suif|volailles?|poulardes?|chapon|cailles?|pigeons?|faisans?|"
    r"perdrix|lievres?|biches?|bolognaises?|carbonara|cassoulet|choucroute garnie|pot au feu|"
    r"potee|blanquette|bourguignons?|bourguignonnes?|osso bu?cco|paella|tajines?|hachis|"
    r"quenelles?|bisque|bouillabaisse|brandade|nems?|samoussas?|sushis?|makis?|sashimi|carne|"
    r"piemontaise|nicoise|lorraine|croque monsieur|croque madame|tartiflette|"
    r"cantonais|gelee au madere|hamburgers?|cheeseburgers?|burgers?|coq|coqs|bouchee a la reine|specialite chinoise|bouchee a la vapeur|pate(?=,|\s*$)|soupe miso|soupe a l oignon|4 saisons|quatre saisons|kebab|doner|bouillons?|consommes?|saucisses|jus de viande|demi glace|"
    r"graisse (d oie|de canard|de porc|de boeuf|animale)|pate de (campagne|foie|tete|lapin|canard|"
    r"gibier|volaille|poisson)|pate en croute|nuoc mam|sauce poisson|worcestershire|"
    r"guimauves?|gelifie[es]?|gommes?|gommeux|nounours|marshmallows?|chamallows?|dragibus|"
    r"foie gras|rouleau de printemps|gelee de viande|aspic|fond (brun|blanc)|"
    r"pizza (au|aux|a la) (jambon|chorizo|lardons|viande|thon|saumon|poulet))\b",
    re.I)
_FR_OK = re.compile(
    r"substitut|vegetari|vegetal|vegan|vege\b|sans (viande|poisson|gelatine|porc)|"
    r"a base de (soja|ble|legumineuses|legumes|proteines vegetales)|"
    r"bouillon (de )?legumes?|bouillon vegetal|"
    r"fond de legumes|legumes? (pour|en) (bouillon)|"
    r"lait (de )?(chevre|brebis|bufflonne|jument)|fromage (de )?(chevre|brebis)|"
    r"oeufs?( entiers?)? (de|d) (caille|canard|oie|poule|cane|pintade)|blanc d oeuf|blancs? d'oeufs?|pain de mie|lait (de )?vache", re.I)
_BOUILLON_VEG = re.compile(r"legumes?|vegetal", re.I)


def norm(text: str) -> str:
    """Lower-case, accent-free, oe/ae expanded, apostrophes -> space."""
    t = (text or '').lower().replace('œ', 'oe').replace('æ', 'ae')
    t = unicodedata.normalize('NFKD', t)
    t = ''.join(c for c in t if not unicodedata.combining(c))
    return re.sub(r"[’'`\-]", ' ', t)


def is_animal_en(name: str) -> bool:
    if parse_usda.is_animal(name):
        stripped = _EN_OK.sub(' ', name)
        return parse_usda.is_animal(stripped) or bool(_ANIMAL_EN_EXTRA.search(stripped))
    stripped = _EN_OK.sub(' ', name)
    return bool(_ANIMAL_EN_EXTRA.search(stripped)) or parse_usda.is_animal(stripped)


def is_animal_fr(name_fr: str) -> bool:
    n = norm(name_fr)
    stripped = _FR_OK.sub(' ', n)
    m = _ANIMAL_FR.search(stripped)
    if not m:
        return False
    if re.search(r'\bbouillons?\b|\bconsommes?\b', stripped) and _BOUILLON_VEG.search(n):
        # plant bouillon: re-check without the bouillon word
        rest = re.sub(r'\b(bouillons?|consommes?)\b', ' ', stripped)
        return bool(_ANIMAL_FR.search(rest))
    return True
