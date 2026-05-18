"""
Ingredient blocklists for dietary classification.
Each list contains regex patterns (case-insensitive) matched against ingredients text.
"""

MEAT_FISH = [
    # Red meat
    r'\bbeef\b', r'\bpork\b', r'\blamb\b', r'\bveal\b', r'\bmutton\b',
    r'\bvenison\b', r'\bboar\b', r'\bdeer\b', r'\bbison\b', r'\bbuffalo\b',
    r'\blard\b', r'\bsuet\b', r'\btallow\b', r'\bdripping\b',
    r'\bham\b', r'\bbacon\b', r'\bsalami\b', r'\bpepperoni\b', r'\bchorizo\b',
    r'\bmortadella\b', r'\bprosciutto\b', r'\bpancetta\b',
    # Poultry
    r'\bchicken\b', r'\bturkey\b', r'\bduck\b', r'\bgoose\b', r'\bquail\b',
    r'\bpartridge\b', r'\bpheasant\b', r'\bguinea fowl\b',
    # Fish
    r'\bfish\b', r'\bsalmon\b', r'\btuna\b', r'\bcod\b', r'\bhaddock\b',
    r'\btrout\b', r'\btilapia\b', r'\bsardine\b', r'\banchov\b',
    r'\bherring\b', r'\bmackerel\b', r'\bbass\b', r'\bsole\b', r'\bplaice\b',
    r'\bhalibut\b', r'\bsnapper\b', r'\bswordfish\b', r'\bmahi\b',
    r'\bpollock\b', r'\bsprat\b', r'\bpilchard\b', r'\bwhiting\b',
    r'\beel\b', r'\bcarp\b', r'\bperch\b', r'\bpike\b',
    # Seafood
    r'\bshrimp\b', r'\bprawn\b', r'\blobster\b', r'\bcrab\b',
    r'\boyster\b', r'\bmussel\b', r'\bclam\b', r'\bscallop\b',
    r'\bsquid\b', r'\boctopus\b', r'\bcuttlefish\b', r'\bseafood\b',
    r'\bcockle\b', r'\bwhelk\b', r'\bwinkle\b',
    # Generic
    r'\bmeat\b', r'\bpoultry\b', r'\bgame\b',
    r'\bcollagen\b',
    # Spanish
    r'\bcarne\b', r'\bpollo\b', r'\bpescado\b', r'\bcerdo\b',
    r'\bternera\b', r'\bvaca\b', r'\bcordero\b', r'\bres\b',
    r'\bmariscos?\b', r'\bcamarón\b', r'\bgamba\b', r'\batún\b',
    r'\bsalmón\b', r'\bmerluza\b', r'\bbacalao\b', r'\bsepia\b',
    r'\bjamón\b', r'\btocino\b',
    # French
    r'\bviande\b', r'\bpoulet\b', r'\bpoisson\b', r'\bsaumon\b',
    r'\bcrevette\b', r'\bmoule\b', r'\bhuître\b',
    # German
    r'\bfleisch\b', r'\bhähnchen\b', r'\bschwein\b', r'\bfisch\b',
    r'\bgarnele\b',
]

DAIRY = [
    r'\bmilk\b', r'\bcream\b', r'\bbutter\b', r'\bghee\b',
    r'\bcheese\b', r'\byogurt\b', r'\byoghurt\b', r'\byogurt\b',
    r'\bwhey\b', r'\bcasein\b', r'\bcaseinate\b', r'\blactose\b',
    r'\blactalbumin\b', r'\blactoglobulin\b', r'\bbuttermilk\b',
    r'\bcurd\b', r'\bquark\b', r'\bfromage\b', r'\bricotta\b',
    r'\bparmesan\b', r'\bcheddar\b', r'\bgouda\b', r'\bbrie\b',
    r'\bemmental\b', r'\bgorgonzola\b', r'\bmozzarella\b', r'\bboursin\b',
    r'\bsour cream\b', r'\bcrème fraîche\b', r'\bcreme fraiche\b',
    r'\bcondensed milk\b', r'\bevaporated milk\b', r'\bpowdered milk\b',
    r'\bskimmed milk\b', r'\bwhole milk\b', r'\bhalf.?fat milk\b',
    r'\bmilk powder\b', r'\bmilk solid\b', r'\bmilk fat\b',
    r'\banhydrous milk fat\b', r'\bmilk protein\b',
    r'\bdairy\b',
    # E-numbers
    r'\bE471\b',  # Mono and diglycerides (often from dairy)
    # Spanish
    r'\bleche\b', r'\bmantequilla\b', r'\bqueso\b', r'\bnata\b',
    r'\bcrema\b', r'\byogur\b', r'\bsuero\b', r'\bcaseína\b',
    r'\blácteo\b', r'\bproducto lácteo\b',
    # French
    r'\blait\b', r'\bbeurre\b', r'\bfromage\b', r'\bcrème\b',
    r'\byaourt\b', r'\bpetit-lait\b',
    # German
    r'\bmilch\b', r'\bbutter\b', r'\bkäse\b', r'\bsahne\b',
    r'\bmolke\b', r'\bjogurt\b',
]

EGGS = [
    r'\begg\b', r'\beggs\b',
    r'\balbumin\b', r'\balbumen\b', r'\bovalbumin\b',
    r'\blysozyme\b',  # E1105 - from egg white
    r'\begg white\b', r'\begg yolk\b', r'\begg powder\b',
    r'\bdried egg\b', r'\bwhole egg\b', r'\bfree.?range egg\b',
    r'\bscrambled egg\b', r'\bpasteurised egg\b',
    r'\bE1105\b',  # Lysozyme
    # Spanish
    r'\bhuevo\b', r'\bhuevos\b', r'\byema\b', r'\bclara\b',
    r'\balbúmina\b',
    # French
    r'\boeuf\b', r'\boeufs\b',
    # German
    r'\bei\b', r'\beier\b', r'\beipulver\b',
]

EGGS_TRACES = [
    r'may contain egg',
    r'may contain traces of egg',
    r'produced in a factory.*egg',
    r'made in a factory.*egg',
    r'manufactured in a facility.*egg',
    r'produced on equipment.*egg',
    r'contains egg traces',
    r'egg traces',
    r'trace.*egg',
    r'egg.*trace',
    # Spanish
    r'puede contener huevo',
    r'trazas de huevo',
    r'puede contener trazas.*huevo',
    r'fabricado en instalaciones.*huevo',
    # French
    r"peut contenir des traces d'oeuf",
    r'peut contenir.*oeuf',
    # German
    r'kann spuren von ei enthalten',
    r'spuren von ei',
]

GELATIN = [
    r'\bgelatin\b', r'\bgelatine\b',
    r'\bE441\b',    # Gelatine
    r'\bcarmine\b', r'\bcarmin\b', r'\bcochineal\b',
    r'\bE120\b',    # Carmine / Cochineal
    r'\bisinglass\b',   # From fish swim bladders (used in beer/wine fining)
    r'\brennet\b',      # From calf stomach
    r'\bchitosan\b',    # From shellfish shells
    r'\bshellac\b',     # E904, from lac bugs
    r'\bE904\b',
    r'\bkeratin\b',
    r'\bL-cysteine\b', r'\bE920\b',  # Often from hair/feathers
    # Spanish
    r'\bgelatina\b', r'\bcarmín\b', r'\bcochinilla\b',
    r'\bcuajo\b',  # Rennet
    # French
    r'\bgélatine\b', r'\bcarmin\b', r'\bcochenille\b',
    r'\bprésure\b',  # Rennet
]

HONEY = [
    r'\bhoney\b', r'\bhoneycomb\b', r'\braw honey\b', r'\bmanuka\b',
    r'\bbeeswax\b', r'\bpropolis\b', r'\broyal jelly\b',
    r'\bpollen\b',
    # Spanish
    r'\bmiel\b', r'\bcera de abeja\b', r'\bjalea real\b',
    # French
    r'\bmiel\b', r'\bcire d.abeille\b',
    # German
    r'\bhonig\b', r'\bbienenwachs\b',
]

ALCOHOL = [
    r'\balcohol\b', r'\bethanol\b',
    r'\bwine\b', r'\bred wine\b', r'\bwhite wine\b', r'\brosé\b',
    r'\bbeer\b', r'\bale\b', r'\bstout\b', r'\blager\b', r'\bbitter\b',
    r'\bwhisk[ey]y\b', r'\bbourbon\b', r'\bscotch\b',
    r'\brum\b', r'\bvodka\b', r'\bgin\b', r'\btequila\b', r'\bmezcal\b',
    r'\bbrandy\b', r'\bcognac\b', r'\barmagnac\b', r'\bport\b',
    r'\bsherry\b', r'\bmarsala\b', r'\bvermouth\b', r'\bchampagne\b',
    r'\bliqueur\b', r'\bschnapps\b', r'\bkirsch\b', r'\bcalvados\b',
    r'\bgrappa\b', r'\bvodka\b', r'\bsake\b', r'\bmirin\b',
    r'\bsangria\b', r'\bcider\b',
    # Spanish
    r'\bvino\b', r'\bcerveza\b', r'\blicor\b', r'\bcoñac\b',
    r'\bmostro\b', r'\baguardiente\b', r'\bsidra\b',
    # French
    r'\bvin\b', r'\bbière\b', r'\beau-de-vie\b',
    # German
    r'\bwein\b', r'\bbier\b', r'\bschnaps\b',
]

CAFFEINE = [
    r'\bcaffeine\b', r'\bcaféine\b', r'\bcafeína\b',
    r'\bcoffee\b', r'\bespresso\b', r'\bcappuccino\b', r'\blatte\b',
    r'\bcafé\b',
    r'\bguarana\b', r'\bguaraná\b',
    r'\bkola nut\b', r'\bcola nut\b', r'\bkola\b',
    r'\bmatcha\b',
    r'\bmate\b', r'\bmaté\b', r'\byerba mate\b',
    r'\bblack tea\b', r'\bgreen tea\b', r'\bwhite tea\b', r'\boolongtea\b',
    r'\btea extract\b', r'\btea powder\b',
    # Spanish
    r'\bcafé\b', r'\bté\b', r'\bté negro\b', r'\bté verde\b',
]

MUSHROOMS = [
    r'\bmushroom\b', r'\bchampignon\b', r'\bportobello\b',
    r'\bshiitake\b', r'\boyster mushroom\b', r'\bporcini\b',
    r'\bmorel\b', r'\bchanterelle\b', r'\btruffle\b', r'\bcèpe\b',
    r'\bgirolle\b', r'\benoki\b', r'\bking oyster\b',
    r'\bmaitake\b', r'\breishi\b', r'\bcordyceps\b',
    r'\bmycoprote[ií]n\b', r'\bquorn\b',  # Quorn is mycoprotein (fungal)
    r'\bfungi\b', r'\bfungus\b',
    # Spanish
    r'\bhongo\b', r'\bchamp[iñ]ón\b', r'\bseta\b', r'\bboletus\b',
    r'\btrufa\b', r'\bnísper[ao]\b',
    # French
    r'\bchampignon\b', r'\btruffe\b', r'\bcèpe\b',
    # German
    r'\bpilz\b', r'\bpilze\b', r'\btrüffel\b',
]

ONION = [
    r'\bonion\b', r'\bonions\b',
    r'\bshallot\b', r'\bscallion\b', r'\bspring onion\b',
    r'\bgreen onion\b', r'\bchive\b', r'\bleek\b',
    r'\bonion powder\b', r'\bonion flakes\b', r'\bonion extract\b',
    r'\bdehydrated onion\b', r'\bdried onion\b',
    r'\bfried onion\b', r'\bcaramelised onion\b',
    # Spanish
    r'\bcebolla\b', r'\bchalota\b', r'\bcebollino\b', r'\bcebolleta\b',
    r'\bpuerro\b',
    # French
    r'\boignon\b', r'\béchalote\b', r'\bciboulette\b', r'\bpoireau\b',
    # German
    r'\bzwiebel\b', r'\bschalotte\b', r'\bschnittlauch\b', r'\blauch\b',
]

GARLIC = [
    r'\bgarlic\b',
    r'\bgarlic powder\b', r'\bgarlic flakes\b', r'\bgarlic extract\b',
    r'\bgarlic oil\b', r'\bgarlic salt\b', r'\bgarlic paste\b',
    r'\bgarlic granules\b', r'\bdried garlic\b', r'\bminced garlic\b',
    r'\bblack garlic\b', r'\broasted garlic\b',
    r'\bAllium sativum\b',
    # Spanish
    r'\bajo\b', r'\bpolvo de ajo\b', r'\bextracto de ajo\b',
    # French
    r'\bail\b', r'\bpoudre d.ail\b',
    # German
    r'\bknoblauch\b', r'\bknoblauchpulver\b',
]

JAIN_EXTRAS = [
    # Root vegetables (Jain diet avoids root/underground vegetables)
    r'\bpotato\b', r'\bpotatoes\b', r'\bsweet potato\b',
    r'\bcarrot\b', r'\bcarrots\b',
    r'\bbeetroot\b', r'\bbeet\b',
    r'\bturnip\b', r'\bparsnip\b', r'\bradish\b',
    r'\byam\b', r'\bcassava\b', r'\btaro\b',
    r'\bginger\b', r'\bturmeric\b',
    r'\bfennel\b',  # Fennel bulb is a root
    r'\bceleriac\b', r'\bcelery root\b',
    r'\bjicama\b', r'\barrowroot\b',
    # Spanish
    r'\bpatata\b', r'\bpapa\b', r'\bzanahoria\b', r'\bremolacha\b',
    r'\bnabo\b', r'\brábano\b', r'\bboniato\b', r'\bjengibre\b',
    r'\bcúrcuma\b',
    # French
    r'\bpomme de terre\b', r'\bcarotte\b', r'\bbetterave\b',
    r'\bnavet\b', r'\bradis\b', r'\bgingembre\b',
    # German
    r'\bkartoffel\b', r'\bmöhre\b', r'\brote bete\b',
    r'\bingwer\b', r'\bgelbwurz\b',
]
