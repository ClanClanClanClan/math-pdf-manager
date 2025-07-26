# unicode_constants.py — Full Unicode normalization maps

# -------------------------------
# SUPERSCRIPTS
# -------------------------------
SUPERSCRIPT_MAP = {
    **{str(i): c for i, c in enumerate("\u2070\u00b9\u00b2\u00b3\u2074\u2075\u2076\u2077\u2078\u2079")},
    **{
        "a": "\u1d43", "b": "\u1d47", "c": "\u1d9c", "d": "\u1d48", "e": "\u1d49", "f": "\u1da0", "g": "\u1d4d", "h": "\u02b0", "i": "\u2071",
        "j": "\u02b2", "k": "\u1d4f", "l": "\u02e1", "m": "\u1d50", "n": "\u207f", "o": "\u1d52", "p": "\u1d56", "q": "\u1da0", "r": "\u02b3",
        "s": "\u02e2", "t": "\u1d57", "u": "\u1d58", "v": "\u1d5b", "w": "\u02b7", "x": "\u02e3", "y": "\u02b8", "z": "\u1dbb",
        "A": "\u1d2c", "B": "\u1d2e", "C": "\u1d9c", "D": "\u1d30", "E": "\u1d31", "F": "\u1da0", "G": "\u1d33", "H": "\u1d34", "I": "\u1d35",
        "J": "\u1d36", "K": "\u1d37", "L": "\u1d38", "M": "\u1d39", "N": "\u1d3a", "O": "\u1d3c", "P": "\u1d3e", "Q": "Q", "R": "\u1d3f",
        "S": "\u02e2", "T": "\u1d40", "U": "\u1d41", "V": "\u2c7d", "W": "\u1d42", "X": "\u02e3", "Y": "\u02b8", "Z": "\u1dbb",
    },
    "+": "\u207a", "-": "\u207b", "=": "\u207c", "(": "\u207d", ")": "\u207e", ".": "\u02d9"
}

# -------------------------------
# SUBSCRIPTS
# -------------------------------
SUBSCRIPT_MAP = {
    **{str(i): c for i, c in enumerate("\u2080\u2081\u2082\u2083\u2084\u2085\u2086\u2087\u2088\u2089")},
    "+": "\u208a", "-": "\u208b", "=": "\u208c", "(": "\u208d", ")": "\u208e",
    "a": "\u2090", "e": "\u2091", "h": "\u2095", "i": "\u1d62", "j": "\u2c7c", "k": "\u2096",
    "l": "\u2097", "m": "\u2098", "n": "\u2099", "o": "\u2092", "p": "\u209a", "r": "\u1d63",
    "s": "\u209b", "t": "\u209c", "u": "\u1d64", "v": "\u1d65", "x": "\u2093",
}

# -------------------------------
# MATHBB
# -------------------------------
MATHBB_MAP = {
    **{c: b for c, b in zip(
        "ABCDEFGHIJKLMNOPQRSTUVWXYZ",
        "\U0001d538\U0001d539\u2102\U0001d53b\U0001d53c\U0001d53d\U0001d53e\u210d\U0001d540\U0001d541\U0001d542\U0001d543\U0001d544\u2115\U0001d546\u2119\u211a\u211d\U0001d54a\U0001d54b\U0001d54c\U0001d54d\U0001d54e\U0001d54f\U0001d550\u2124"
    )},
    **{c: b for c, b in zip(
        "abcdefghijklmnopqrstuvwxyz",
        "\U0001d552\U0001d553\U0001d554\U0001d555\U0001d556\U0001d557\U0001d558\U0001d559\U0001d55a\U0001d55b\U0001d55c\U0001d55d\U0001d55e\U0001d55f\U0001d560\U0001d561\U0001d562\U0001d563\U0001d564\U0001d565\U0001d566\U0001d567\U0001d568\U0001d569\U0001d56a\U0001d56b"
    )},
    **{str(i): c for i, c in enumerate("\U0001d7d8\U0001d7d9\U0001d7da\U0001d7db\U0001d7dc\U0001d7dd\U0001d7de\U0001d7df\U0001d7e0\U0001d7e1")}
}

# -------------------------------
# SUFFIXES (strictly pedantic)
# -------------------------------
SUFFIXES = [
    # generational
    "Jr", "Sr", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X",
    "XI", "XII", "XIII", "XIV", "XV", "XVI", "XVII", "XVIII", "XIX", "XX",
    # academic/honorific
    "PhD", "DPhil", "MD", "DDS", "DO", "Esq", "Dr", "Prof",
    "CPA", "MBA", "MSc", "BSc", "JD", "LLM", "LLD", "EdD", "DMus", "DSc", "DTheol"
]

# -------------------------------
# NUMBERS
# -------------------------------
NUMBERS = {
    "0": "zero", "1": "one", "2": "two", "3": "three", "4": "four", "5": "five",
    "6": "six", "7": "seven", "8": "eight", "9": "nine",
    "10": "ten", "11": "eleven", "12": "twelve", "13": "thirteen", "14": "fourteen",
    "15": "fifteen", "16": "sixteen", "17": "seventeen", "18": "eighteen", "19": "nineteen",
    "20": "twenty", "30": "thirty", "40": "forty", "50": "fifty", "60": "sixty",
    "70": "seventy", "80": "eighty", "90": "ninety", "100": "hundred", "1000": "thousand"
}

# -------------------------------
# LIGATURE MAP
# -------------------------------
LIGATURE_MAP = {
    # --- Printing / typographic ligatures (Unicode Presentation Forms) ---
    "\ufb00": "ff",    # ﬀ LATIN SMALL LIGATURE FF
    "\ufb01": "fi",    # ﬁ LATIN SMALL LIGATURE FI
    "\ufb02": "fl",    # ﬂ LATIN SMALL LIGATURE FL
    "\ufb03": "ffi",   # ﬃ LATIN SMALL LIGATURE FFI
    "\ufb04": "ffl",   # ﬄ LATIN SMALL LIGATURE FFL
    "\ufb05": "ct",    # ﬅ LATIN SMALL LIGATURE LONG S T or "ct"
    "\ufb06": "st",    # ﬆ LATIN SMALL LIGATURE ST

    # --- Classical and phonetic digraph/ligature letters (Latin/French) ---
    "\u00c6": "AE",    # Æ LATIN CAPITAL LETTER AE
    "\u00e6": "ae",    # æ LATIN SMALL LETTER AE
    "\u0152": "OE",    # Œ LATIN CAPITAL LIGATURE OE
    "\u0153": "oe",    # œ LATIN SMALL LIGATURE OE
    "\u00df": "ss",    # ß LATIN SMALL LETTER SHARP S (Eszett)
    "\u1e9e": "SS",    # ẞ LATIN CAPITAL LETTER SHARP S

    # --- Historic, Medievalist and Latin Extended-A/B ligatures/digraphs ---
    "\ua730": "AA",    # ꜰ LATIN LETTER AA
    "\ua731": "aa",    # ꜱ LATIN SMALL LETTER AA
    "\ua732": "AO",    # Ꜳ LATIN CAPITAL LETTER AO
    "\ua733": "ao",    # ꜳ LATIN SMALL LETTER AO
    "\ua734": "AU",    # Ꜵ LATIN CAPITAL LETTER AU
    "\ua735": "au",    # ꜵ LATIN SMALL LETTER AU
    "\ua736": "AV",    # Ꜷ LATIN CAPITAL LETTER AV
    "\ua737": "av",    # ꜷ LATIN SMALL LETTER AV
    "\ua738": "AY",    # Ꜹ LATIN CAPITAL LETTER AY
    "\ua739": "ay",    # ꜹ LATIN SMALL LETTER AY
    "\ua73a": "EY",    # Ꜻ LATIN CAPITAL LETTER EY
    "\ua73b": "ey",    # ꜻ LATIN SMALL LETTER EY
    "\ua73c": "OO",    # Ꜽ LATIN CAPITAL LETTER OO
    "\ua73d": "oo",    # ꜽ LATIN SMALL LETTER OO
    "\ua73e": "OU",    # Ꜿ LATIN CAPITAL LETTER OU
    "\ua73f": "ou",    # ꜿ LATIN SMALL LETTER OU
    "\ua74f": "oo",    # ꝏ LATIN SMALL LETTER OO
    "\ua75d": "rr",    # ꝝ LATIN SMALL LETTER R ROTUNDA
    "\ua75f": "um",    # ꝟ LATIN SMALL LETTER UM
    "\ua751": "pp",    # ꝑ LATIN SMALL LETTER PP
    "\ua777": "is",    # ꝷ LATIN SMALL LETTER IS
    "\ua78b": "tt",    # Ꞌ LATIN SMALL LETTER INSULAR T
    "\ua729": "tz",    # ꜩ LATIN SMALL LETTER TZ

    # --- South Slavic and Balkan digraphs ---
    "\u01f1": "DZ",    # Ǳ LATIN CAPITAL LETTER DZ
    "\u01f2": "Dz",    # ǲ LATIN CAPITAL LETTER D WITH SMALL Z
    "\u01f3": "dz",    # ǳ LATIN SMALL LETTER DZ
    "\u01c4": "DZ",    # Ǆ LATIN CAPITAL LETTER DZ WITH CARON
    "\u01c5": "Dz",    # ǅ LATIN CAPITAL LETTER D WITH SMALL Z WITH CARON
    "\u01c6": "dz",    # ǆ LATIN SMALL LETTER DZ WITH CARON
    "\u01c7": "LJ",    # Ǉ LATIN CAPITAL LETTER LJ
    "\u01c8": "Lj",    # ǈ LATIN CAPITAL LETTER L WITH SMALL J
    "\u01c9": "lj",    # ǉ LATIN SMALL LETTER LJ
    "\u01ca": "NJ",    # Ǌ LATIN CAPITAL LETTER NJ
    "\u01cb": "Nj",    # ǋ LATIN CAPITAL LETTER N WITH SMALL J
    "\u01cc": "nj",    # ǌ LATIN SMALL LETTER NJ
    "\u0132": "IJ",    # Ĳ LATIN CAPITAL LIGATURE IJ
    "\u0133": "ij",    # ĳ LATIN SMALL LIGATURE IJ

    # --- Hebrew presentation forms (Yiddish, compatibility) ---
    "\ufb2a": "sh",    # שׁ HEBREW LETTER SHIN WITH SHIN DOT
    "\ufb2b": "sh",    # שׂ HEBREW LETTER SHIN WITH SIN DOT
    "\ufb2c": "sh",    # שּׁ HEBREW LETTER SHIN WITH DAGESH (could also be "ti" in Yiddish context)

    # --- IPA and phonetic digraphs ---
    "\u0238": "db",    # ȸ LATIN SMALL LETTER DB DIGRAPH
    "\u0239": "qp",    # ȹ LATIN SMALL LETTER QP DIGRAPH
    "\u02A3": "dz",    # ʣ LATIN SMALL LETTER DZ DIGRAPH
    "\u02A4": "dz",    # ʤ LATIN SMALL LETTER DZ DIGRAPH WITH CURL ("dʒ" or "dz" depending on tradition)
    "\u02A5": "dz",    # ʥ LATIN SMALL LETTER DZ DIGRAPH WITH CURL
    "\u02A6": "ts",    # ʦ LATIN SMALL LETTER TS DIGRAPH
    "\u02A7": "tc",    # ʧ LATIN SMALL LETTER TC DIGRAPH ("tʃ")
    "\u02A8": "tɕ",    # ʨ LATIN SMALL LETTER TESH DIGRAPH
    "\u02A9": "fn",    # ʩ LATIN SMALL LETTER FENG DIGRAPH
    "\u02AA": "ls",    # ʪ LATIN SMALL LETTER LS DIGRAPH
    "\u02AB": "lz",    # ʫ LATIN SMALL LETTER LZ DIGRAPH

    # --- Historic long-s (U+017F) and variants ---
    "\u017F": "s",     # ſ LATIN SMALL LETTER LONG S

    # --- Tironian et (Insular/medieval abbreviation) ---
    "\u204A": "et",    # ⁊ TIRONIAN SIGN ET

    # --- Armenian (for completeness, in Unicode presentation) ---
    "\uFB13": "mn",    # ﬓ ARMENIAN SMALL LIGATURE MEN NOW
    "\uFB14": "me",    # ﬔ ARMENIAN SMALL LIGATURE MEN ECH
    "\uFB15": "mi",    # ﬕ ARMENIAN SMALL LIGATURE MEN INI
    "\uFB16": "vn",    # ﬖ ARMENIAN SMALL LIGATURE VEW NOW
    "\uFB17": "mkh",   # ﬗ ARMENIAN SMALL LIGATURE MEN XEH
}

LIGATURES_WHITELIST = {
    #EN_LEXICAL
    # --- A ---
    "aegilops": "ægilops",            # grass genus 
    "aegirine": "ægirine",            # sodium-iron silicate mineral
    "aegis": "ægis",                  # protection, shield (classical/poetic) 
    "aeneous": "æneous",              # bronze-coloured 
    "aenigma": "ænigma",              # Latinate spelling of “enigma” 
    "aeolian": "æolian",              # relating to wind or Aeolus 
    "aeolic": "æolic",                # dialect of Ancient Greek 
    "aeon": "æon",                    # age/era (esp. philosophical) 
    "aeonian": "æonian",              # everlasting 
    "aesthetic": "æsthetic",          # BrE historical spelling 
    "aetiological": "ætiological",    # causation-related (medicine) 
    "aetiology": "ætiology",          # study of causes 
    "anaemia": "anæmia",              # low haemoglobin 
    "anaemic": "anæmic",              # relating to anaemia 
    "anapaest": "anapæst",            # metrical foot (poetry) 
    "anapaestic": "anapæstic",        # adj. form 
    "antioedematous": "antiœdematous",# counteracting oedema
    "apnoea": "apnœa",                # temporary cessation of breathing 
    "archaeal": "archæal",            # of the domain Archaea 
    "archaean": "archæan",            # alt. for “archaeal” / geologic eon 
    "archaea": "archæa",              # the microorganisms themselves 
    "archaeobacteria": "archæobacteria", # obsolete taxon name
    "archaeocete": "archæocete",      # early whale sub-order
    "archaeocyte": "archæocyte",      # sponge totipotent cell
    "archaeology": "archæology",      # discipline 
    "archaeopteryx": "archæopteryx",  # Ur-Vogel fossil genus 
    "archaeozoology": "archæozoology", # faunal archaeology

    # --- B ---
    "bathycoelia":        "bathycoælia",      # orthopteran genus, 19 C. entomology
    "bromoacetonaemia":   "bromoacetonæmia",  # chem.–toxicology literature

    # --- C ---
    "caecal":             "cæcal",
    "caecilia":           "cæcilia",
    "caecilian":          "cæcilian",
    "caecum":             "cæcum",
    "caesarian":          "cæsarian",
    "caesium":            "cæsium",
    "caesura":            "cæsura",
    "calycoedema":        "calycœdema",
    "carcinoedema":       "carcinœdema",
    "catalepsia":         "catalæpsia",
    "catapnoea":          "catapnœa",
    "chemoaesthesia":     "chemoæsthesia",
    "chorea":             "choræa",
    "choanae":            "choanæ",
    "claustroaesthesia":  "claustroæsthesia",
    "cladocaera":         "cladocæra",
    "coelenterata":       "cœlenterata",
    "coelenterate":       "cœlenterate",
    "coelenteric":        "cœlenteric",
    "coelenteron":        "cœlenteron",
    "coeliac":            "cœliac",
    "coelom":             "cœlom",
    "coelomic":           "cœlomic",
    "colpocoele":         "colpocœle",
    "conioedema":         "coniœdema",
    "connaesthesia":      "connæsthesia",
    "cysticaemia":        "cysticæmia",

    # --- D ---
    "decaemia":           "decæmia",
    "diarrhoea":          "diarrhœa",
    "diplocaulus":        "diplocæulus",
    "discoedema":         "discœdema",
    "dysaesthesia":       "dysæsthesia",
    "dyspnoea":           "dyspnœa",

    # --- E ---
    "elephantiasis":      "elephantiasīs",
    "emphysema":          "emphysæma",
    "encephalaemia":      "encephalæmia",
    "epicaene":           "epicæne",
    "epiphora":           "epiphœra",
    "erythraemia":        "erythræmia",
    "erythroaesthesia":   "erythroæsthesia",
    "erythrocythaemia":   "erythrocythæmia",
    "exanthema":          "exanthæma",
    "exocaecal":          "exocæcal",
    "exophthalmia":       "exophthalmīa",

    # --- F ---
    "faecal":             "fæcal",
    "faeces":             "fæces",
    "foetation":          "fœtation",
    "foeticide":          "fœticide",
    "foetid":             "fœtid",
    "foetology":          "fœtology",
    "galactocele":        "galactocœle",
    "gastroaesthesia":    "gastroæsthesia",
    "gynaecocracy":       "gynæcocracy",
    "gynaecology":        "gynæcology",
    "gynaecological":     "gynæcological",
    "gynaecologist":      "gynæcologist",
    "gynaecophore":       "gynæcophore",

    # --- H ---
    "haemal":             "hæmal",
    "haemaphysalis":      "hæmaphysalis",
    "haematemesis":       "hæmatemesis",
    "haematin":           "hæmatin",
    "haematite":          "hæmatite",
    "haematoblast":       "hæmatoblast",
    "haematoblastosis":   "hæmatoblastosis",
    "haematocrit":        "hæmatocrit",
    "haematogenous":      "hæmatogenous",
    "haematology":        "hæmatology",
    "haematopoiesis":     "hæmatopoiesis",
    "haematuria":         "hæmaturia",
    "haemoglobin":        "hæmoglobin",
    "haemolysis":         "hæmolysis",
    "haemophilia":        "hæmophilia",
    "haemoptysis":        "hæmoptysis",
    "haemorrhage":        "hæmorrhage",
    "haemostasis":        "hæmostasis",
    "hyperaesthesia":     "hyperæsthesia",

    # --- I ---
    "ischaemia":          "ischæmia",
    "ischaemic":          "ischæmic",

    # --- L ---
    "leucaemia":          "leucæmia",
    "leucaemic":          "leucæmic",
    "leukaemia":          "leucæmia",      # OED cross-lists this form
    "leukaemic":          "leucæmic",
    "lymphoedema":        "lymphœdema",

    # --- M ---
    "mediaeval":          "mediæval",
    "mediaevalism":       "mediævalism",
    "myxoedema":          "myxœdema",

    # --- N ---
    "naevus":              "nævus",
    "neuroaesthesia":      "neuroæsthesia",
    "noema":               "nœma",

    # --- O ---
    "oedema":              "œdema",
    "oedematous":          "œdematous",
    "oestrogen":           "œstrogen",
    "oesophagus":          "œsophagus",
    "oesophagitis":        "œsophagitis",
    "oesophageal":         "œsophageal",
    "orthopaedia":         "orthopædia",
    "orthopaedic":         "orthopædic",
    "osteopaenia":         "osteopænia",
    "osteopaenic":         "osteopænic",

    # --- P ---
    "paean":               "pæan",
    "paediatric":          "pædiatric",
    "paediatrics":         "pædiatrics",
    "paedogenesis":        "pædogenesis",
    "paedology":           "pædology",
    "paedomorphosis":      "pædomorphosis",
    "paedophile":          "pædophile",
    "paedopsychiatry":     "pædopsychiatry",
    "palaeoanthropology":  "palæoanthropology",
    "palaeobotany":        "palæobotany",
    "palaeoecology":       "palæoecology",
    "palaeogene":          "palæogene",
    "palaeogeography":     "palæogeography",
    "palaeolithic":        "palæolithic",
    "palaeomagnetism":     "palæomagnetism",
    "palaeontology":       "palæontology",
    "palaeopathology":     "palæopathology",
    "palaeozoology":       "palæozoology",
    "paraparesis":         "parapæresis",
    "parapaesthesia":      "parapæsthesia",
    "paranoea":            "paranœa",
    "parapnoea":           "parapnœa",
    "pleuraesthesia":      "pleuræsthesia",
    "pnoea":               "pnœa",
    "poecile":             "pœcile",
    "poecilogony":         "pœcilogony",
    "praemolar":           "præmolar",
    "praenomen":           "prænomen",
    "praetorian":          "prætorian",

    # --- S ---
    "spinae":              "spinæ",               # e.g. *processus spinæ scapulæ*
    "subaesthetic":        "subæsthetic",
    "subaesthesia":        "subæsthesia",
    "suboesophageal":      "subœsophageal",
    "synaesthesia":        "synæsthesia",
    "synopnoea":           "synopnœa",

    # --- T ---
    "taenia":              "tænia",
    "thermae":             "thermæ",

    # --- U ---
    "urethraemia":         "urethræmia",
    "urethroaesthesia":    "urethroæsthesia",

    # --- V ---
    "vertebrae":           "vertebræ",

    # --- Z ---
    "zoea":                "zoëa",

    #EN_LEXICAL_VARIANTS
    # ── A ───────────────────────────────────────────────────────────
    "aemulation":          "æmulation",
    "aenigma":             "ænigma",
    "aestivate":           "æstivate",
    "aestival":            "æstival",
    "aethereal":           "æthereal",
    "aether":              "æther",
    "aetiological":        "ætiological",
    "aetiologist":         "ætiologist",
    "aetiologies":         "ætiologies",
    "anaesthesia":         "anæsthesia",
    "anaesthetise":        "anæsthetise",
    "anaesthetist":        "anæsthetist",
    "anaesthetize":        "anæsthetize",
    "anaesthetizing":      "anæsthetizing",
    "anæmia":              "anæmia",
    "antæsthetic":         "antæsthetic",
    "archæological":       "archæological",
    "archæologist":        "archæologist",
    "archæology":          "archæology",
    "archæopteryx":        "archæopteryx",
    "archæozoology":       "archæozoology",
    "archæus":             "archæus",
    "auræole":             "auræole",

    # ── B ───────────────────────────────────────────────────────────
    "bæotian":             "bæotian",
    "bæotica":             "bæotica",

    # ── C ───────────────────────────────────────────────────────────
    "caecal":              "cæcal",
    "caecum":              "cæcum",
    "caesarian":           "cæsarian",
    "caesure":             "cæsure",
    "caetera":             "cætera",

    # ── D ───────────────────────────────────────────────────────────
    "diaereses":           "diæreses",
    "diaeresis":           "diæresis",
    "dipnoea":             "dipnœa",
    "dysaesthetic":        "dysæsthetic",

    # ── E ───────────────────────────────────────────────────────────
    "encyclopaedia":       "encyclopædia",
    "encyclopaedic":       "encyclopædic",
    "encyclopaedist":      "encyclopædist",
    "encyclopaedism":      "encyclopædism",
    "encyclopaedical":     "encyclopædical",
    "encyclopaedically":   "encyclopædically",
    "exæquo":              "exæquo",
    "exsanguinaemia":      "exsanguinæmia",

    # ── F ───────────────────────────────────────────────────────────
    "faecal":              "fæcal",
    "faeces":              "fæces",
    "faeculent":           "fæculent",
    "foetation":           "fœtation",
    "foeticide":           "fœticide",
    "foetid":              "fœtid",
    "foetus":              "fœtus",
    "foetal":              "fœtal",

    # ── G ───────────────────────────────────────────────────────────
    "gynaecium":           "gynæcium",
    "gynaecocrat":         "gynæcocrat",
    "gynaecocracy":        "gynæcocracy",
    "gynaecoid":           "gynæcoid",
    "gynaecological":      "gynæcological",
    "gynaecology":         "gynæcology",

    # ── H ───────────────────────────────────────────────────────────
    "hæmatin":             "hæmatin",
    "hæmaturia":           "hæmaturia",
    "hæmoglobin":          "hæmoglobin",
    "hæmorrhage":          "hæmorrhage",
    "hæmostasis":          "hæmostasis",
    "hæmoptysis":          "hæmoptysis",
    "hæmophilia":          "hæmophilia",

    # ── I ───────────────────────────────────────────────────────────
    "ischaemia":           "ischæmia",
    "ischaemic":           "ischæmic",

    # ── L ───────────────────────────────────────────────────────────
    "leucaemia":           "leucæmia",
    "leucaemic":           "leucæmic",
    "leukaemia":           "leucæmia",
    "leukaemic":           "leucæmic",
    "lymphoedema":         "lymphœdema",

    # ── M ───────────────────────────────────────────────────────────
    "mediaeval":           "mediæval",
    "mediaevalist":        "mediævalist",
    "mediaevalism":        "mediævalism",
    "mediaevalistic":      "mediævalistic",
    "myxoedema":           "myxœdema",

    # ── N ───────────────────────────────────────────────────────────
    "naevus":              "nævus",

    # ── O ───────────────────────────────────────────────────────────
    "oedema":              "œdema",
    "oedematous":          "œdematous",
    "oestrogen":           "œstrogen",
    "oesophagus":          "œsophagus",
    "oesophagitis":        "œsophagitis",
    "oesophageal":         "œsophageal",
    "orthopaedia":         "orthopædia",
    "orthopaedic":         "orthopædic",

    # ── P ───────────────────────────────────────────────────────────
    "paediatric":          "pædiatric",
    "paediatrics":         "pædiatrics",
    "paedogenesis":        "pædogenesis",
    "paedology":           "pædology",
    "paedomorphosis":      "pædomorphosis",
    "paedophile":          "pædophile",
    "paedopsychiatry":     "pædopsychiatry",
    "paeony":              "pæony",
    "palaeoanthropology":  "palæoanthropology",
    "palaeobotany":        "palæobotany",
    "palaeoecology":       "palæoecology",
    "palaeogene":          "palæogene",
    "palaeogeography":     "palæogeography",
    "palaeolithic":        "palæolithic",
    "palaeomagnetism":     "palæomagnetism",
    "palaeontology":       "palæontology",
    "palaeopathology":     "palæopathology",
    "palaeozoology":       "palæozoology",
    "parapnoea":           "parapnœa",
    "pleuraesthesia":      "pleuræsthesia",
    "pnoea":               "pnœa",
    "poecile":             "pœcile",
    "poecilogony":         "pœcilogony",
    "praemolar":           "præmolar",
    "praenomen":           "prænomen",
    "praetorian":          "prætorian",

    # ── S ───────────────────────────────────────────────────────────
    "synaesthetic":        "synæsthetic",
    "synaesthesia":        "synæsthesia",
    "synopnoea":           "synopnœa",

    # ── T ───────────────────────────────────────────────────────────
    "taenia":              "tænia",
    "thermae":             "thermæ",

    # ── U / V / W / X / Y / Z ──────────────────────────────────────
    "urethraemia":         "urethræmia",
    "urethroaesthesia":    "urethroæsthesia",
    "vertebrae":           "vertebræ",
    "zoea":                "zoëa",

    #EN_LEXICAL_BOTANICAL
    # --- A ---
    "acaena":           "acæna",
    "aegilops":         "ægilops",
    "aegithalidae":     "ægithalidæ",
    "aegithalos":       "ægithalos",
    "aegopodium":       "ægopodium",
    "aegypius":         "ægypius",
    "aeonium":          "æonium",
    "aepyceros":        "æpyceros",
    "aepyornithidae":   "æpyornithidæ",
    "aesculus":         "æsculus",
    "aeschynomene":     "æschynomene",
    "alstroemeria":     "alstrœmeria",
    "amoeba":           "amœba",
    "amoebae":          "amœbae",
    "amoebida":         "amœbida",
    "amoebidae":        "amœbidæ",
    "amphichaeta":      "amphichæta",
    "amphichaetaceae":  "amphichætaceæ",
    "anabaena":         "anabæna",
    "anabaenaceae":     "anabænaceæ",
    "anacaena":         "anacæna",
    "andrena":          "andræna",
    "angelicae":        "angelicæ",
    "anisae":           "anisæ",
    "anisaemia":        "anisæmia",
    "archaea":          "archæa",
    "archaeobacteria":  "archæobacteria",
    "archaeobatrachia": "archæobatrachia",
    "archaeoceti":      "archæoceti",
    "archaeogoniatae":  "archægoniatæ",
    "archaeolepidotus": "archæolepidotus",
    "archaeornis":      "archæornis",
    "archaeopteryx":    "archæopteryx",
    "archaeozoology":   "archæozoology",
    "araceae":          "araceæ",
    "arecae":           "arecæ",
    "arisaema":         "arisæma",
    "aristolochiaceae": "aristolochiaceæ",
    "asteraceae":       "asteraceæ",
    "atherinae":        "atherinæ",
    "auriculae":        "auriculæ",

    # --- B ---
    "balaena":     "balæna",
    "balaenidae":  "balænidæ",
    "betulae":     "betulæ",
    "bombycoidea": "bombycoïdea",
    "bryaceae":    "bryaceæ",
    "bryozoae":    "bryozoæ",

    # --- C ---
    "caeciliidae":      "cæciliidæ",
    "caecilius":        "cæcilius",
    "caecum":           "cæcum",
    "caespitose":       "cæspitose",
    "caesalpinia":      "cæsalpinia",
    "caesalpinioideae": "cæsalpinioideæ",
    "calceolariae":     "calceolariæ",
    "calycanthaceae":   "calycanthaceæ",
    "caryophyllaceae":  "caryophyllaceæ",
    "cassiaefolia":     "cassiæfolia",
    "cassiopeae":       "cassiopeæ",
    "centaureae":       "centaureæ",
    "chaetognatha":     "chætognatha",
    "chaetophoraceae":  "chætophoraceæ",
    "chaetopterus":     "chætopterus",
    "cheirolepidium":   "cheirolæpidium",
    "coryphae":         "coryphæ",
    "coryphaena":       "coryphæna",
    "coryphaeidae":     "coryphæidæ",
    "cynarae":          "cynaræ",

    # --- D ---
    "dichaeta":     "dichæta",
    "diarrhoea":    "diarrhœa",
    "diplochaeta":  "diplochæta",
    "diplolaepis":  "diplolæpis",
    "dysaesthesia": "dysæsthesia",

    # --- E ---
    "epigaea":   "epigæa",
    "eucaenia":  "eucænia",
    "euphaea":   "euphæa",
    "excaecate": "excæcate",

    # --- F ---
    "fabaceae":  "fabaceæ",
    "faecal":    "fæcal",
    "faeces":    "fæces",
    "faeculent": "fæculent",
    "francoae":  "francoæ",

    # --- G ---
    "gynaecology":    "gynæcology",
    "gynaecological": "gynæcological",
    "gynaecologist":  "gynæcologist",

    # --- H ---
    "haemanthus":   "hæmanthus",
    "haematology":  "hæmatology",
    "haemostasis":  "hæmostasis",
    "haemoglobin":  "hæmoglobin",
    "haemophilia":  "hæmophilia",
    "haemal":       "hæmal",
    "haematic":     "hæmatic",
    "haematite":    "hæmatite",
    "haematuria":   "hæmaturia",
    "haemolysis":   "hæmolysis",
    "haemoptysis":  "hæmoptysis",
    "haemopoeisis": "hæmopœisis",

    # --- I ---
    "ichthyaena": "ichthyæna",

    # --- L ---
    "lepidopterae": "lepidopteræ",
    "lepidoptilae": "lepidoptilæ",
    "lepidostomae": "lepidostomæ",
    "lygaeidae":    "lygæidæ",

    # --- M ---
    "melanochloera": "melanochlœra",
    "mediaevalis":   "mediævalis",
    "monae":         "monæ",
    "myriapoeda":    "myriapœda",
    "myxoedema":     "myxœdema",

    # --- N ---
    "naevius": "nævius",
    "naevus":  "nævus",

    # --- O ---
    "oenothera":  "œnothera",
    "oesmium":    "œsmium",
    "oecophylla": "œcophylla",
    "oedema":     "œdema",
    "oedematous": "œdematous",
    "oestrogen":  "œstrogen",

    # --- P ---
    "paeonia":            "pæonia",
    "paediculus":         "pædiculus",
    "paedomorphosis":     "pædomorphosis",
    "paedogenesis":       "pædogenesis",
    "paedology":          "pædology",
    "paedophile":         "pædophile",
    "palaeoanthropology": "palæoanthropology",
    "palaeobotany":       "palæobotany",
    "palaeoecology":      "palæoecology",
    "palaeogene":         "palæogene",
    "palaeogeography":    "palæogeography",
    "palaeolithic":       "palæolithic",
    "palaeomagnetism":    "palæomagnetism",
    "palaeontology":      "palæontology",
    "palaeopathology":    "palæopathology",
    "palaeozoology":      "palæozoology",
    "paraparesis":        "parapæresis",
    "parapaesthesia":     "parapæsthesia",
    "paranoea":           "paranœa",
    "parapnoea":          "parapnœa",
    "perichaeta":         "perichæta",
    "pleuraesthesia":     "pleuræsthesia",
    "pnoea":              "pnœa",
    "poecile":            "pœcile",
    "poecilogony":        "pœcilogony",
    "praemolar":          "præmolar",
    "praenomen":          "prænomen",
    "praetorian":         "prætorian",

    # --- R ---
    "rhaetica": "rhætica",
    "rhaetian": "rhætian",

    # --- S ---
    "sphaera":          "sphæra",
    "sphaerococcaceae": "sphærococcaceæ",
    "sphaerotheca":     "sphærotheca",
    "synaesthesia":     "synæsthesia",

    # --- T ---
    "taeniidae": "tæniidæ",
    "taenia":    "tænia",
    "thermae":   "thermæ",
    "troezen":   "trœzen",

    # --- U ---
    "urethraemia":      "urethræmia",
    "urethroaesthesia": "urethroæsthesia",

    # --- V ---
    "vertebrae": "vertebræ",

    # --- Z ---
    "zoea":       "zoëa",
    "zygoptaera": "zygoptæra",
    "zygaenidae": "zygænidæ",

    #EN_LEXICAL_TOPONYMIC
    # –– Classical & well-documented Latin / antiquarian exonyms ––
    "aegaean":              "ægæan",
    "aegaeum mare":         "ægæum mare",
    "aegaea":               "ægæa",                     # poetic name for the Aegean islands
    "aeolia":               "æolia",
    "aeolis":               "æolis",
    "aegyptus":             "ægÿptus",
    "aegyptiacus":          "ægÿptiacus",          # adj.
    "africa":               "africæ",
    "aethiopia":            "æthiopiæ",
    "arabia":               "arabiæ",
    "arabiae felix":        "arabiæ felix",
    "arabiae petraea":      "arabiæ petræa",
    "australia":            "australiæ",
    "australasia":          "australasiæ",
    "amazonas":             "amazonæ",
    "belgae":               "belgæ",
    "baetica":              "bætica",
    "bornea":               "bornæa",
    "basilia":              "basilæa",
    "britannia":            "britanniæ",
    "burgundia":            "burgundiæ",
    "bahamae":              "bahamæ",
    "brasilia":             "brasiliæ",
    "braga":                "bragæ",
    "barbara":              "barbaræ",
    "barca":                "barcæ",
    "bostonia":             "bostoniæ",
    "bonae spei":           "bonæ spei",

    # --- C ---
    "cantabria":            "cantabriæ",
    "cyrenaica":            "cyrænai­ca",
    "ceylon":               "ceylonæ",
    "cassiterides":         "cassiteridæ",
    "cappadocia":           "cappadociæ",
    "cambria":              "cambriæ",
    "celtica":              "celticæ",
    "caucasus":             "caucasæ",
    "colonia agrippina":    "colonia agrippinæ",
    "colonia caesarea":     "colonia cæsarea",
    "colonia caesariensis": "colonia cæsariensis",

    # --- D ---
    "dacia":                "daciæ",
    "dalmatia":             "dalmatiæ",
    "dalecarlia":           "dalecarliæ",
    "denmarkia":            "denmarkiæ",
    "deir":                 "deiræ",
    "dumnonia":             "dumnoniæ",
    "domitia":              "domitiæ",
    "drave":                "dravæ",
    "drakensbergae":        "drakensbergæ",
    "dulcigno":             "dulcignæ",
    "dominica":             "dominicæ",
    "dominicum":            "dominicæ",
    "dariena":              "darienæ",
    "diabene":              "diabenæ",

    # --- E ---
    "ethiopia":             "æthiopiæ",
    "ethiopicus oceanus":   "æthiopicus oceanus",
    "epirus":               "epiræ",
    "ephesus":              "ephesæ",
    "egyptus":              "ægÿptus",
    "egyptiacus":           "ægÿptiacus",
    "elba":                 "elbæ",
    "ebro":                 "ebrœ",
    "equatoria":            "equatoriæ",
    "esmeraldas":           "esmeraldæ",

    # --- F ---
    "fascia nigra":         "fasciæ nigræ",
    "fezzan":               "fezzanæ",
    "finlandia":            "finlandiæ",
    "florida":              "floridæ",
    "fossa magna":          "fossæ magnæ",
    "francia":              "franciæ",
    "franconia":            "franconiæ",
    "formosa":              "formosæ",
    "foveauxia":            "foveauxiæ",

    # --- G ---
    "galicia":              "galiciæ",
    "galia":                "galiæ",
    "garumna":              "garumnæ",
    "gaza":                 "gazæ",
    "georgia":              "georgiæ",
    "gothia":               "gothiæ",
    "guiana":               "guiænæ",

    # --- H ---
    "helvetia":             "helvetiæ",
    "hispania":             "hispaniæ",
    "honduria":             "honduriæ",
    "hispaniola":           "hispaniolæ",
    "humber":               "humbræ",

    # --- I ---
    "iberia":               "iberiæ",
    "india":                "indiæ",
    "india orientalis":     "indiæ orientalis",
    "irelandia":            "irlandiæ",
    "isca":                 "iscæ",
    "ilia":                 "iliæ",
    "istria":               "istriæ",
    "insulae britannicae":  "insulæ britannicæ",

    # --- J ---
    "judaea":               "judæa",
    "judaeorum regnum":     "judæorum regnum",
    "jordanis":             "jordaniæ",
    "jericho":              "jerichæ",
    "jerusalem":            "jerusalæm",
    "jamaica":              "jamaicæ",
    "japonia":              "japoniæ",
    "japonica":             "japoniæ",      # attested variant
    "jersey":               "jersiæ",

    # --- K ---
    "keltae":               "keltæ",
    "kynae":                "kynæ",
    "kappadocia":           "kappadociæ",
    "kilkennia":            "kilkenniæ",
    "kambodia":             "kambodiæ",

    # --- L ---
    "lutetia":              "lutetiæ",
    "laurentia":            "laurentiæ",
    "lotharingia":          "lotharingiæ",
    "louisiana":            "louisianæ",
    "limerica":             "limericæ",
    "libya":                "libyæ",
    "lidia":                "lidiæ",
    "lusitania":            "lusitaniæ",

    # --- M ---
    "mauretania":           "mauretaniæ",
    "melanesia":            "melanesiæ",
    "micronesia":           "micronesiæ",
    "messenia":             "messeniæ",
    "mississippia":         "mississippiæ",
    "moesia":               "mœsiæ",
    "montana":              "montanæ",
    "montes apenni":        "montes apenniæ",
    "monae":                "monæ",
    "montenegro":           "montenegræ",
    "madridia":             "madridiæ",

    # --- N ---
    "numidia":              "numidiæ",
    "nova scotia":          "novæ scotiæ",
    "nova anglia":          "novæ angliæ",
    "nova aurelia":         "novæ aureliæ",
    "nova britannia":       "novæ britanniæ",
    "nova cambria":         "novæ cam­briæ",
    "nova lusitania":       "novæ lusitaniæ",
    "nova granata":         "novæ granatæ",
    "nova hispania":        "novæ hispaniæ",
    "nigeria":              "nigeriæ",
    "norvegia":             "norvegiæ",
    "neustria":             "neustriæ",
    "napolia":              "napoliæ",
    "nebraska":             "nebraskæ",
    "nebraskae flumen":     "nebraskæ flumen",
    "neustria britannica":  "neustriæ britannicæ",

    # --- O ---
    "oceania":              "oceaniæ",
    "olympia":              "olympiæ",
    "ostia":                "ostiæ",
    "ostrava":              "ostravæ",
    "oxonia":               "oxoniæ",
    "olimpia":              "olimpiæ",
    "ormae":                "ormæ",
    "oberia":               "oberiæ",
    "ostrogothia":          "ostrogothiæ",
    "octavia":              "octaviæ",

    # --- P ---
    "parisia":              "parisiæ",
    "parthia":              "parthiæ",
    "pamphylia":            "pamphyliæ",
    "phoenicia":            "phœniciæ",
    "phoenice":             "phœnicæ",
    "persia":               "persiæ",
    "palmyra":              "palmyræ",
    "polynesia":            "polynesiæ",
    "portugallia":          "portugalliæ",
    "punica":               "punicæ",
    "pannonia":             "pannoniæ",
    "pictavia":             "pictaviæ",
    "palestina":            "palestinæ",
    "phrygia":              "phrygiæ",
    "provence":             "provenciæ",

    # --- Q ---
    "quadi":                "quadæ",
    "quadi regnum":         "quadæ regnum",
    "quadi terra":          "quadæ terra",

    # --- R ---
    "romae":                "romæ",
    "russia":               "russiæ",
    "ruthenia":             "rutheniæ",
    "rhodos":               "rhodæ",
    "rhaetia":              "rhætiæ",
    "raetia":               "rætiæ",
    "russia alba":          "russiæ albæ",
    "rodaunia":             "rodau­niæ",

    # --- S ---
    "sicilia":              "siciliæ",
    "scandinavia":          "scandinaviæ",
    "sarmatia":             "sarmatiæ",
    "syria":                "syriæ",
    "syra":                 "syræ",
    "scythia":              "scythiæ",
    "silesia":              "silesiæ",
    "sparta":               "spartæ",
    "sumatra":              "sumatræ",
    "senegambia":           "senegambiæ",
    "sarmatia asiatica":    "sarmatiæ asiaticæ",
    "sarmatia europea":     "sarmatiæ europeæ",
    "savoyae":              "savoyæ",
    "silesiae montes":      "silesiæ montes",
    "suetia":               "suetiæ",
    "suebia":               "suebiæ",
    "selonia":              "seloniæ",

    # --- T ---
    "thessalia":            "thessaliæ",
    "thebaea":              "thebæa",
    "transsylvania":        "transsylvaniæ",
    "tripolitania":         "tripolitaniæ",
    "thracia":              "thraciæ",
    "tyrolia":              "tyroliæ",
    "tasmania":             "tasmaniæ",
    "tracia":               "traciæ",
    "tartaria":             "tartariæ",
    "taenia":               "tænia",

    # --- U ---
    "umbria":               "umbriæ",
    "uralia":               "uraliæ",
    "ulsteria":             "ulsteriæ",
    "ukrainia":             "ukrainiæ",
    "utahia":               "utahiæ",

    # --- V ---
    "vaeolia":              "væolia",
    "vaeoliae":             "væoliæ",
    "valentia":             "valentiæ",
    "valentiana":           "valentianæ",
    "vallis aurea":         "vallis aureæ",
    "valoisia":             "valoisiæ",
    "venetia":              "venetiæ",
    "verona":               "veronæ",
    "veterania":            "veteraniæ",
    "virginia":             "virginiæ",
    "vallis":               "valliæ",
    "vallombrosa":          "vallombrosæ",
    "vosgesia":             "vosgesiæ",
    "volhynia":             "volhyniæ",
    "valonia":              "valoniæ",
    "valga":                "valgæ",
    "vallandia":            "vallandiæ",

    # --- W ---
    "walesia":              "walesiæ",
    "wasconia":             "wasconiæ",
    "westphalia":           "westphaliæ",
    "wolfenbuttel":         "wolfenbüttelæ",
    "wolhynia":             "wolhyniæ",
    "wielkopolska":         "wielkopolskæ",

    # --- X ---
    "xanthia":              "xanthiæ",
    "xenophonia":           "xenophoniæ",

    # --- Y ---
    "ytalia":               "ytaliæ",

    # --- Z ---
    "zaelandia":            "zælandia",
    "zelandia":             "zelandiæ",
    "zamora":               "zamoræ",
    "zaragosa":             "zaragosæ",
    "zagabria":             "zagabriæ",
    "zama":                 "zamæ",

    #EN_TYPOMEDIEVAL_UNICODE_IPA
    # ―― Classic print ligatures (Unicode Presentation Forms) ――
    "ff":  "ﬀ",   # U+FB00
    "fi":  "ﬁ",   # U+FB01
    "fl":  "ﬂ",   # U+FB02
    "ffi": "ﬃ",   # U+FB03
    "ffl": "ﬄ",   # U+FB04
    "ct":  "ﬅ",   # U+FB05  (long-s + t)
    "st":  "ﬆ",   # U+FB06

    # ―― Tironian / long-s derived forms still cited in Eng. sources ――
    "et": "⁊",    # U+204A  Tironian ET
    "ſs": "ß",    # U+00DF  (sharp-s evolved from ſs/ſz)
    "ſſ": "ẞ",    # U+1E9E  capital sharp-s

    # ―― Medieval Latin scribal ligatures seen in Eng. MSS & critical eds ――
    "aa": "ꜳ",    # U+A733  LATIN SMALL LETTER AA
    "ao": "ꜵ",    # U+A735  LATIN SMALL LETTER AO
    "au": "ꜷ",    # U+A737  LATIN SMALL LETTER AU
    "av": "ꜹ",    # U+A739  LATIN SMALL LETTER AV
    "oo": "ꝏ",    # U+A74F  LATIN SMALL LETTER OO
    "pp": "ꝑ",    # U+A751  LATIN SMALL LETTER P WITH STROKE  (abbr. “pp/ per / pro”)
    "rr": "ꝝ",    # U+A75D  LATIN SMALL LETTER R ROTUNDA
    "um": "ꝟ",    # U+A75F  LATIN SMALL LETTER RUM ROTUNDA  (scribal ‘-um’)
    "vy": "ꜿ",    # U+A73F  LATIN SMALL LETTER VY
    "yr": "ꝡ",    # U+A761  LATIN SMALL LETTER YR
    "tt": "Ꞌ",    # U+A78B  LATIN SMALL LETTER INSULAR T  (often standing for “tt”)

    # ―― IPA / phonetic ligatures current in Eng. linguistics ――
    "dz": "ʣ",    # U+02A3  LATIN SMALL LETTER DZ DIGRAPH
    "dʒ": "ʤ",    # U+02A4  LATIN SMALL LETTER DEZH DIGRAPH
    "ts": "ʦ",    # U+02A6  LATIN SMALL LETTER TS DIGRAPH
    "tc": "ʧ",    # U+02A7  LATIN SMALL LETTER TESH DIGRAPH
    "tɕ": "ʨ",    # U+02A8  LATIN SMALL LETTER TC WITH CURL
    "fn": "ʩ",    # U+02A9  LATIN SMALL LETTER FENG DIGRAPH
    "ls": "ʪ",    # U+02AA  LATIN SMALL LETTER LS DIGRAPH
    "lz": "ʫ",    # U+02AB  LATIN SMALL LETTER LZ DIGRAPH

    #EN_CRITICAL_LITERARY_COLONIAL
    # ―― Literary / poetic proper names ――
    "ælfred":      "Ælfred",       # Alfred the Great (OE chronicles, critical eds.)
    "æneas":       "Æneas",        # Chaucer, Dryden, etc.
    "æsculapius":  "Æsculapius",   # classical & medical literature
    "æthelwulf":   "Æthelwulf",    # OE king
    "æthelbald":   "Æthelbald",    # OE king
    "æthelstane":  "Æthelstane",   # Walter Scott’s Ivanhoe, antiquarian usage
    "æsop":        "Æsop",         # classical fabulist
    "æsir":        "Æsir",         # Norse mythology in Eng. translations
    "ætna":        "Ætna",         # poetic/Latin spelling of Mount Etna

    # ―― Ecclesiastical & early-medieval figures ――
    "ælred":       "Ælred",        # St Aelred of Rievaulx
    "æthelred":    "Æthelred",     # king
    "ætheldreda":  "Ætheldreda",   # St Etheldreda

    # ―― Latin colonial / classical exonyms (genitive in –æ with ligature) ――
    "anglia":      "angliæ",
    "batavia":     "bataviæ",
    "britannia":   "britanniæ",
    "gallia":      "galliæ",
    "germania":    "germaniæ",
    "hibernia":    "hiberniæ",
    "hispania":    "hispaniæ",
    "iberia":      "iberiæ",
    "lusitania":   "lusitaniæ",
    "scotia":      "scotiæ",
    "thule":       "thulæ",

    # ―― Literary titles & learned Latin works ――
    "æneis":       "Æneis",        # Virgil, critical Latin spelling
    "ænigmata":    "Ænigmata",     # Aldhelm’s riddles, modern scholarly eds.

    #FR_LEXICAL
    # A
    "aesculape":        "æsculape",
    "aether":           "æther",
    "aethiops":         "æthiops",
    "aetiologie":       "ætiologie",
    "aetiologique":     "ætiologique",
    "aeternam":         "æternam",
    "aevum":            "ævum",

    # B
    "boeuf":            "bœuf",
    "boeufs":           "bœufs",
    "boeufier":         "bœufier",
    "boetie":           "bœtie",

    # C
    "caelum":           "cælum",
    "caeli":            "cæli",
    "caesura":          "cæsura",
    "caesaris":         "cæsaris",
    "caesarea":         "cæsarea",
    "choeur":           "chœur",
    "coloeus":          "colœus",
    "coephale":         "cœphale",
    "coeur":            "cœur",
    "coeurdoux":        "cœurdoux",
    "coeurle":          "cœurle",
    "coeurthier":       "cœurthier",
    "coeurter":         "cœurter",
    "coelacanthe":      "cœlacanthe",
    "coelenterate":     "cœlenterate",
    "coelenterique":    "cœlenterique",
    "coelome":          "cœlome",
    "coelomique":       "cœlomique",
    "coelozoaire":      "cœlozoaire",
    "coenure":          "cœnure",
    "coenureux":        "cœnureux",
    "coenocyte":        "cœnocyte",
    "coenocytique":     "cœnocytique",

    # D
    "decoeur":          "décœur",
    "decoeurant":       "décœurant",
    "decoeuré":         "décœuré",
    "decoeurée":        "décœurée",
    "diarrhee":         "diarrhœe",
    "diarrhees":        "diarrhœes",

    # E
    "ecclesiae":        "ecclesiæ",
    "encyclopaedie":    "encyclopædie",
    "encyclopaedique":  "encyclopædique",
    "encyclopaedistes": "encyclopædistes",
    "enoe":             "enœ",
    "enoeil":           "enœil",

    # F
    "faecal":           "fæcal",
    "faeces":           "fæces",
    "foetal":           "fœtal",
    "foetale":          "fœtale",
    "foetaux":          "fœtaux",
    "foeticide":        "fœticide",
    "foetide":          "fœtide",
    "foetidite":        "fœtidité",
    "foetus":           "fœtus",

    # G
    "gloeocapsa":       "glœocapsa",
    "gloeocyste":       "glœocyste",
    "gloeocystide":     "glœocystide",
    "gloeopeltis":      "glœopeltis",
    "gloeosporie":      "glœosporie",
    "gynaecologie":     "gynæcologie",
    "gynaecologique":   "gynæcologique",
    "gynaecologue":     "gynæcologue",

    # I
    "idioecie":         "idiœcie",
    "idioecique":       "idiœcique",
    "idioecisme":       "idiœcisme",
    "idioecious":       "idiœcious",
    "isoecie":          "isœcie",
    "isoecique":        "isœcique",
    "isoecisme":        "isœcisme",
    "isoecism":         "isœcism",

    # L
    "laecanthus":       "lœcanthus",
    "lacte":            "lactœ",
    "leucaemie":        "leucæmie",
    "leucaemique":      "leucæmique",
    "leucaemiste":      "leucæmiste",
    "leucaemistes":     "leucæmistes",
    "leucaemisation":   "leucæmisation",
    "leucaemoide":      "leucæmoïde",
    "leucaemoides":     "leucæmoïdes",
    "lycoecienne":      "lycœcienne",
    "lycoeciennes":     "lycœciennes",
    "lycoecoumene":     "lycœcoumène",
    "lycoecumene":      "lycœcumène",

    # M
    "manoeuvre":        "manœuvre",
    "manoeuvrer":       "manœuvrer",
    "manoeuvrable":     "manœuvrable",
    "manoeuvrabilité":  "manœuvrabilité",
    "manoeuvres":       "manœuvres",
    "moeurs":           "mœurs",

    # N
    "naevus":           "nævus",
    "noeud":            "nœud",
    "noeuds":           "nœuds",

    # O
    "oeil":             "œil",
    "oeillade":         "œillade",
    "oeillet":          "œillet",
    "oeilleton":        "œilleton",
    "oeilletons":       "œilletons",
    "oeils":            "œils",
    "oeuvre":           "œuvre",
    "oeuvres":          "œuvres",
    "oedème":           "œdème",
    "oedipien":         "œdipien",
    "oedipe":           "œdipe",
    "oedipal":          "œdipal",
    "oestrogenique":    "œstrogénique",
    "oestrogène":       "œstrogène",
    "oestrogènes":      "œstrogènes",
    "oesophage":        "œsophage",
    "oesophages":       "œsophages",
    "oesophagien":      "œsophagien",
    "oesophagienne":    "œsophagienne",
    "oesophagiens":     "œsophagiens",
    "oesophagiennes":   "œsophagiennes",
    "oesophagite":      "œsophagite",
    "oesophagites":     "œsophagites",
    "oesophagostome":   "œsophagostome",
    "oesophagostomes":  "œsophagostomes",

    # P
    "paedagogie":       "pædagogie",
    "paedagogique":     "pædagogique",
    "paedophile":       "pædophile",
    "paedophilie":      "pædophilie",
    "paediatrique":     "pædiatrique",
    "paediatre":        "pædiatre",
    "paediatrie":       "pædiatrie",
    "paenitentiaire":   "pænitentiaire",
    "paenitence":       "pænitence",
    "paenitent":        "pænitent",
    "paenitents":       "pænitents",

    # Q
    "quoeur":           "quœur",

    # R
    "recoeur":          "recœur",
    "recoeurant":       "recœurant",
    "recoeuré":         "recœuré",
    "recoeurée":        "recœurée",

    # S
    "soeur":            "sœur",
    "soeurs":           "sœurs",
    "soeurette":        "sœurette",
    "soeurologie":      "sœurologie",
    "soeurologique":    "sœurologique",
    "sousoeil":         "sousœil",
    "sousoeils":        "sousœils",
    "sousoeillet":      "sousœillet",

    # T
    "taenia":           "tænia",

    # V
    "voeu":             "vœu",
    "voeux":            "vœux",
    "voeuiller":        "vœuiller",
    "voeuillère":       "vœuillère",
    "voeuilles":        "vœuilles",
    "voeuillon":        "vœuillon",
    "voeuillot":        "vœuillot",

    #FR_BOTANICAL
    # A
    "acaena":               "acæna",
    "aegilops":             "ægilops",
    "aegopodium":           "ægopodium",
    "aeonium":              "æonium",
    "aepyceros":            "æpyceros",
    "aepyornithidae":       "æpyornithidæ",
    "aesculus":             "æsculus",
    "aeschynomene":         "æschynomene",
    "aeulophidae":          "æulophidæ",
    "alstroemeria":         "alstrœmeria",
    "amoeba":               "amœba",
    "amoebae":              "amœbae",
    "amoebida":             "amœbida",
    "amoebidae":            "amœbidæ",
    "amphichaeta":          "amphichæta",
    "amphichaetaceae":      "amphichætaceæ",
    "anabaena":             "anabæna",
    "anabaenaceae":         "anabænaceæ",
    "anacaena":             "anacæna",
    "andrena":              "andræna",
    "angelicae":            "angelicæ",
    "anisae":               "anisæ",
    "anisaemia":            "anisæmia",
    "archaea":              "archæa",
    "archaeobacteria":      "archæobacteria",
    "archaeobatrachia":     "archæobatrachia",
    "archaeoceti":          "archæoceti",
    "archaeogoniatae":      "archægoniatæ",
    "archaeolepidotus":     "archæolepidotus",
    "archaeornis":          "archæornis",
    "archaeopteryx":        "archæopteryx",
    "archaeozoology":       "archæozoology",
    "araceae":              "araceæ",
    "arecae":               "arecæ",
    "arisaema":             "arisæma",
    "aristolochiaceae":     "aristolochiaceæ",
    "asteraceae":           "asteraceæ",
    "atherinae":            "atherinæ",
    "auriculae":            "auriculæ",

    # B
    "balaena":              "balæna",
    "balaenidae":           "balænidæ",
    "betulae":              "betulæ",
    "bryaceae":             "bryaceæ",
    "bryozoae":             "bryozoæ",

    # C
    "caeciliidae":          "cæciliidæ",
    "caecilius":            "cæcilius",
    "caecum":               "cæcum",
    "caespitose":           "cæspitose",
    "caesalpinia":          "cæsalpinia",
    "caesalpinioideae":     "cæsalpinioideæ",
    "calceolariae":         "calceolariæ",
    "calycanthaceae":       "calycanthaceæ",
    "caryophyllaceae":      "caryophyllaceæ",
    "cassiaefolia":         "cassiæfolia",
    "cassiopeae":           "cassiopeæ",
    "centaureae":           "centaureæ",
    "chaetognatha":         "chætognatha",
    "chaetophoraceae":      "chætophoraceæ",
    "chaetopterus":         "chætopterus",
    "cheirolepidium":       "cheirolæpidium",
    "coryphae":             "coryphæ",
    "coryphaena":           "coryphæna",
    "coryphaeidae":         "coryphæidæ",
    "cynarae":              "cynaræ",

    # D
    "dichaeta":             "dichæta",
    "diarrhoea":            "diarrhœa",
    "diplochaeta":          "diplochæta",
    "diplolaepis":          "diplolæpis",
    "dysaesthesia":         "dysæsthesia",

    # E
    "epigaea":              "epigæa",
    "eucaenia":             "eucænia",
    "euphaea":              "euphæa",
    "excaecate":            "excæcate",

    # F
    "fabaceae":             "fabaceæ",
    "faecal":               "fæcal",
    "faeces":               "fæces",
    "francoae":             "francoæ",

    # G
    "gaulthoeria":          "gaulthœria",
    "gloeocapsa":           "glœocapsa",
    "gloeocyste":           "glœocyste",
    "gloeocystide":         "glœocystide",
    "gloeopeltis":          "glœopeltis",
    "gloeosporie":          "glœosporie",
    "gynaecology":          "gynæcology",
    "gynaeceum":            "gynæceum",
    "gynaecephalum":        "gynæcephalum",

    # H
    "haemanthus":           "hæmanthus",
    "haematology":          "hæmatology",
    "haemostasis":          "hæmostasis",
    "haemoglobin":          "hæmoglobin",
    "haemophilia":          "hæmophilia",
    "haemal":               "hæmal",
    "haematic":             "hæmatic",
    "haematite":            "hæmatite",
    "haematuria":           "hæmaturia",
    "haemolysis":           "hæmolysis",
    "haemoptysis":          "hæmoptysis",
    "haemopoeisis":         "hæmopœisis",

    # I
    "idioecie":             "idiœcie",
    "idioecique":           "idiœcique",
    "idioecisme":           "idiœcisme",
    "idioecious":           "idiœcious",
    "isoecie":              "isœcie",
    "isoecique":            "isœcique",
    "isoecisme":            "isœcisme",
    "isoecism":             "isœcism",

    # L
    "lepidoptérae":         "lepidoptærae",
    "lepidoptilae":         "lepidoptilæ",
    "lepidostomae":         "lepidostomæ",
    "leucaemie":            "leucæmie",
    "leucaemique":          "leucæmique",
    "lasiocampa":           "læsiocampa",
    "lasiocampidae":        "læsiocampidæ",
    "lacerta":              "læcerta",
    "lycoecienne":          "lycœcienne",
    "lycoeciennes":         "lycœciennes",
    "lycoecoumene":         "lycœcoumène",
    "lycoecumene":          "lycœcumène",

    # M
    "melanochloera":        "melanochlœra",
    "mediaevalis":          "mediævalis",
    "monae":                "monæ",
    "myriapoeda":           "myriapœda",
    "myxoedema":            "myxœdema",

    # N
    "naevius":              "nævius",
    "naevus":               "nævus",

    # O
    "oenothera":            "œnothera",
    "oesmium":              "œsmium",
    "oecophylla":           "œcophylla",
    "oedema":               "œdema",
    "oedematous":           "œdematous",
    "oestrogenique":        "œstrogénique",
    "oestrogene":           "œstrogène",
    "oestrogenes":          "œstrogènes",

    # P
    "paeonia":              "pæonia",
    "paediculus":           "pædiculus",
    "paedomorphosis":       "pædomorphosis",
    "paedogenesis":         "pædogenesis",
    "paedology":            "pædology",
    "paedophile":           "pædophile",
    "palaeoanthropology":   "palæoanthropology",
    "palaeobotany":         "palæobotany",
    "palaeoecology":        "palæoecology",
    "palaeogene":           "palæogene",
    "palaeogeography":      "palæogeography",
    "palaeolithic":         "palæolithic",
    "palaeomagnetism":      "palæomagnetism",
    "palaeontology":        "palæontology",
    "palaeopathology":      "palæopathology",
    "palaeozoology":        "palæozoology",
    "paraparesis":          "parapæresis",
    "parapaesthesia":       "parapæsthesia",
    "paranoea":             "paranœa",
    "parapnoea":            "parapnœa",
    "perichaeta":           "perichæta",
    "pleuraesthesia":       "pleuræsthesia",
    "pnoea":                "pnœa",
    "poecile":              "pœcile",
    "poecilogony":          "pœcilogony",
    "praemolar":            "præmolar",
    "praenomen":            "prænomen",
    "praetorian":           "prætorian",

    # R
    "rhaetica":             "rhætica",
    "rhaetian":             "rhætian",

    # S
    "scaevóla":             "scævóla",
    "sphaera":              "sphæra",
    "sphaerococcaceae":     "sphærococcaceæ",
    "sphaerotheca":         "sphærotheca",
    "synaesthesia":         "synæsthesia",

    # T
    "taeniidae":            "tæniidæ",
    "taenia":               "tænia",
    "thermae":              "thermæ",
    "troezen":              "trœzen",

    # U
    "urethraemia":          "urethræmia",
    "urethroaesthesia":     "urethroæsthesia",

    # V
    "vertebrae":            "vertebræ",

    # Z
    "zygoptaera":           "zygoptæra",
    "zygaenidae":           "zygænidæ",

    #FR_TOPONYMIC
    # A
    "aethie":                       "æthie",
    "aethuse":                      "æthuse",
    "agnes-la-boeuf":               "agnès-la-bœuf",
    "ae":                           "æ",

    # B
    "baroeil":                      "barœil",
    "baroeul":                      "barœul",
    "barboeuf":                     "barbœuf",
    "beloeil":                      "bœloeil",
    "boe":                          "bœ",
    "boeuf":                        "bœuf",
    "boeufs":                       "bœufs",
    "boetie":                       "bœtie",

    # C
    "cenoecourt":                   "cœnoëcourt",
    "chanoeuve":                    "chanœuve",
    "chanoeur":                     "chanœur",
    "choeur":                       "chœur",
    "cloeur":                       "clœur",
    "cloez":                        "clœz",
    "coeur":                        "cœur",
    "coeurdoux":                    "cœurdoux",
    "coeurle":                      "cœurle",
    "coeurthier":                   "cœurthier",
    "coeurter":                     "cœurter",
    "coetlogon":                    "cœtlogon",
    "coetmieux":                    "cœtmieux",
    "coetquidan":                   "cœtquidan",
    "coetquen":                     "cœtquen",
    "coloeuilly":                   "colœuilly",
    "croix-d'oeuf":                 "croix-d'œuf",
    "cressoeur":                    "cressœur",

    # D
    "dancoeur":                     "dancœur",
    "dangeaux":                     "dangœaux",

    # E
    "elbeuf":                       "elbœuf",
    "elbeufs":                      "elbœufs",
    "elbeuf-sur-andelle":           "elbœuf-sur-andelle",
    "elbeuf-la-campagne":           "elbœuf-la-campagne",
    "elboeuf":                      "elbœuf",
    "escloeux":                     "esclœux",
    "escloeux-hauterive":           "esclœux-hauterive",
    "escloeux-les-mines":           "esclœux-les-mines",
    "escloeux-saint-martin":        "esclœux-saint-martin",

    # F
    "fresnoy-le-grand-boeuf":       "fresnoy-le-grand-bœuf",
    "fresnoy-le-petit-boeuf":       "fresnoy-le-petit-bœuf",
    "fougeres-la-boeuf":            "fougères-la-bœuf",
    "fontboeuf":                    "fontbœuf",
    "fouquet-boeuf":                "fouquet-bœuf",
    "feroe":                        "ferœ",
    "foyer-boeuf":                  "foyer-bœuf",

    # G
    "gonneoeil":                    "gonneœil",
    "grande-boeuf":                 "grande-bœuf",
    "grosboeuf":                    "grosbœuf",
    "grange-boeuf":                 "grange-bœuf",
    "grande-coeur":                 "grande-cœur",

    # H
    "haute-coeur":                  "haute-cœur",
    "hameau-boeuf":                 "hameau-bœuf",
    "hameau-coeur":                 "hameau-cœur",
    "herboeuf":                     "herbœuf",
    "herboeufs":                    "herbœufs",

    # I
    "ile-boeuf":                    "île-bœuf",
    "ile-du-boeuf":                 "île-du-bœuf",
    "isle-boeuf":                   "isle-bœuf",
    "isle-coeur":                   "isle-cœur",

    # J
    "joncoeur":                     "joncœur",
    "joncoeurie":                   "joncœurerie",

    # L
    "la-boeuf":                     "la-bœuf",
    "lacoeur":                      "lacœur",
    "lacoeurville":                 "lacœurville",
    "lacoeur-les-mines":            "lacœur-les-mines",
    "lambeuf":                      "lambœuf",
    "lanboeuf":                     "lanbœuf",
    "lanboeufville":                "lanbœufville",
    "lanchoeur":                    "lanchœur",
    "landes-boeuf":                 "landes-bœuf",
    "largoeur":                     "largœur",
    "largoeux":                     "largœux",
    "laurboeuf":                    "laurbœuf",
    "leboeuf":                      "lebœuf",
    "leboeufville":                 "lebœufville",
    "lenoeud":                      "lenœud",
    "les-boeufs":                   "les-bœufs",
    "le-coeur":                     "le-cœur",
    "lecoeur":                      "lecœur",
    "lecoeurie":                    "lecœurerie",
    "lecoeurier":                   "lecœurier",
    "lecoeurre":                    "lecœurre",
    "lile-boeuf":                   "l’île-bœuf",
    "lile-noeud":                   "l’île-nœud",

    # M
    "marboeuf":                     "marbœuf",
    "marboeufs":                    "marbœufs",
    "martel-boeuf":                 "martel-bœuf",
    "moulinoeuf":                   "moulinœuf",
    "moulin-boeuf":                 "moulin-bœuf",
    "montboeuf":                    "montbœuf",
    "montboeufs":                   "montbœufs",
    "moncoeur":                     "moncœur",
    "moncoeurville":                "moncœurville",

    # N
    "neufboeuf":                    "neufbœuf",
    "noel-boeuf":                   "noël-bœuf",
    "noeud":                        "nœud",
    "noeudville":                   "nœudville",
    "noeuds":                       "nœuds",
    "noeuille":                     "nœuille",
    "noeuillé":                     "nœuillé",
    "noeuillé-sur-seine":           "nœuillé-sur-seine",

    # O
    "oeuf":                         "œuf",
    "oeufs":                        "œufs",
    "oeuilly":                      "œuilly",
    "oeuilly-sur-marne":            "œuilly-sur-marne",
    "oeillet":                      "œillet",
    "oeils":                        "œils",
    "ormeau-boeuf":                 "ormeau-bœuf",
    "ormeaux-boeufs":               "ormeaux-bœufs",
    "orme-boeuf":                   "orme-bœuf",

    # P
    "petit-boeuf":                  "petit-bœuf",
    "pierre-boeuf":                 "pierre-bœuf",
    "pierrecoeur":                  "pierrecœur",
    "plaine-boeuf":                 "plaine-bœuf",
    "plaine-coeur":                 "plaine-cœur",
    "pontboeuf":                    "pontbœuf",
    "pont-de-boeuf":                "pont-de-bœuf",
    "pontcoeur":                    "pontcœur",

    # Q
    "quoeur":                       "quœur",

    # R
    "ramboeuf":                     "rambœuf",
    "ramboeufs":                    "rambœufs",
    "ramcoeur":                     "ramcœur",
    "riviere-boeuf":                "rivière-bœuf",
    "riviere-oeuf":                 "rivière-œuf",
    "rondboeuf":                    "rondbœuf",
    "rondcoeur":                    "rondcœur",

    # S
    "saint-boeuf":                  "saint-bœuf",
    "saintcoeur":                   "saintcœur",
    "sous-boeuf":                   "sous-bœuf",
    "surboeuf":                     "surbœuf",

    # T
    "tailloeuf":                    "taillœuf",
    "tailloeuil":                   "taillœuil",
    "terboeuf":                     "terbœuf",
    "terreboeuf":                   "terrebœuf",
    "terroir-boeuf":                "terroir-bœuf",
    "tranche-boeuf":                "tranche-bœuf",

    # V
    "valboeuf":                     "valbœuf",
    "valboeufs":                    "valbœufs",
    "vieuxboeuf":                   "vieuxbœuf",
    "villeneuve-boeuf":             "villeneuve-bœuf",
    "villars-boeuf":                "villars-bœuf",
    "villeboeuf":                   "villebœuf",

    # Y
    "yverboeuf":                    "yverbœuf",

    # Z
    "zeboef":                       "zebœuf",

    #FR_TYPOGRAPHIC_MEDIEVAL_UNICODE_IPA
    # ── Common Latin-script printing ligatures (Unicode presentation forms) ──
    "ff":  "ﬀ",   "fi":  "ﬁ",   "fl":  "ﬂ",
    "ffi": "ﬃ",   "ffl": "ﬄ",   "ct":  "ﬅ",   "st": "ﬆ",
    "et":  "⁊",   "ſs": "ß",    "ſſ": "ẞ",

    # ── Standard French/Latin digraph ligatures ──
    "ae": "æ",    "AE": "Æ",
    "oe": "œ",    "OE": "Œ",
    "ij": "ĳ",    "IJ": "Ĳ",

    # ── Extended medieval / compatibility ligatures (U+A700–A7FF, etc.) ──
    "ab": "ꜳ", "AB": "Ꜳ", "av": "ꜵ", "AV": "Ꜵ",
    "ay": "ꜻ", "AY": "Ꜻ", "ey": "ꜽ", "EY": "Ꜽ",
    "oa": "ꜷ", "OA": "Ꜷ",
    "oo": "ꝏ", "ou": "ꜿ", "OU": "Ꝏ",
    "pp": "ꝑ", "PP": "Ꝑ", "rr": "ꝝ", "RR": "Ꝝ",
    "tt": "Ꞌ", "is": "ꝷ", "IS": "ꝶ", "us": "ꝏ", "um": "ꝟ",
    "vy": "ꝳ", "yr": "ꝡ",

    # ── IPA / phonetic ligatures seen in French linguistics ──
    "dz": "ʣ", "dʒ": "ʤ", "ts": "ʦ", "tc": "ʧ", "tɕ": "ʨ",
    "fn": "ʩ", "ls": "ʪ", "lz": "ʫ", "fj": "ﬄ",

    # ── Medieval French abbreviations & long-s combinations ──
    "p̄":  "p̄",     # p with overline (“per / pro”) – combining form preserved
    "q̄":  "q̄",     # q with overline (“que”)
    "ꝯ":  "ꝯ",     # “con/et” sign
    "ꝭ":  "ꝭ",     # “rum / ur” sign
    "tironian_et": "⁊",

    # ── Greek editorial ligatures (used in FR Classics apparatus) ──
    "kai":               "ϗ",
    "omicron-upsilon":   "Ȣ",
    "upsilon-iota":      "ῡͅ",
    "stigma":            "ϛ",
    "sampi":             "ͳ",
    "koppa":             "ϙ",
    "archaic_gamma-lambda": "ΓΛ",

    # ── Armenian, Slavonic, Coptic, Hebrew/Yiddish ligatures ──
    "ew":        "և",
    "izhitsa-i": "ѵ",    # U+0475
    "shei-e":    "ϣ̄",    # U+03E3 + overline
    "sh": "שׁ",   "ti": "שּׁ",

    # ── Insular / runic / special Latin letters ──
    "insular_g": "Ᵹ", "insular_r": "ꞃ",
    "runic_ing": "ᛝ", "runic_oe": "ᚯ",

    # ── Misc. scholarly / currency / experimental ligatures ──
    "ks":               "ͳ",
    "euro_latin_lig":   "₠",
    "mathbb_AE":        "𝔸𝔸",   # double-struck “AE”
    "flff":             "ﬄﬀ",
    "ffi_ct":           "ﬃﬅ",

    # ── Private-Use–Area codes employed by French digital palaeography projects ──
    "ct_pua":   "\uE132", "st_pua":   "\uE133",
    "ffi_pua":  "\uE134", "ffl_pua":  "\uE135",
    "oo_pua":   "\uE136", "tt_pua":   "\uE137",
    "aes_pua":  "\uE100", "oe_pua":   "\uE101",
    "longs_pua": "\uE102","et_pua":   "\uE103",

    #DE_LEXICAL
    # — A —
    "ae": "ä",
    "aegypten": "ägypten",
    "aemter": "ämter",
    "aendert": "ändert",
    "aenderung": "änderung",
    "aeon": "äon",
    "aeonisch": "äonisch",
    "aequat": "äquat",
    "aerger": "ärger",
    "aerzlichem": "ärztlichem",
    "aerzlichen": "ärztlichen",
    "aerzlicher": "ärztlicher",
    "aerzte": "ärzte",
    "aerztekammer": "ärztekammer",
    "aerzten": "ärzten",
    "aerztes": "ärztes",
    "aerzteverein": "ärzteverein",
    "aerztestelle": "ärztestelle",
    "aeussern": "äußern",
    "aeusserung": "äußerung",
    "aet": "æt",
    "aethetik": "ästhetik",
    "aetiologie": "ätiologie",
    "aetiologisch": "ätiologisch",
    "aether": "äther",
    "aetzend": "ätzend",
    "aetzendste": "ätzendste",
    "aetzendsten": "ätzendsten",
    "aetzendster": "ätzendster",
    "aetzendstes": "ätzendstes",
    "aetzendst": "ätzendst",
    "aetzendstes": "ätzendstes",
    "aetzendst": "ätzendst",
    "aetzende": "ätzende",
    "aetzender": "ätzender",
    "aetzendem": "ätzendem",
    "aetzenden": "ätzenden",
    "aetzendes": "ätzendes",
    "aetzmittel": "ätzmittel",
    "aetzmittelbeständig": "ätzmittelbeständig",
    "aetzwirkung": "ätzwirkung",
    "aetzkali": "ätzkali",
    "aetzlauge": "ätzlauge",
    "aeusserlich": "äußerlich",
    "aeusserliche": "äußerliche",
    "aeusserlichen": "äußerlichen",
    "aeusserlicher": "äußerlicher",
    "aeusserlichem": "äußerlichem",
    "aeusserliches": "äußerliches",
    "aeusserlichst": "äußerlichst",
    "aeusserlichste": "äußerlichste",
    "aeusserlichsten": "äußerlichsten",
    "aeusserlichster": "äußerlichster",
    "aeusserlichstes": "äußerlichstes",

    # — B —
    "baeume": "bäume",
    "baeumchen": "bäumchen",
    "baendig": "bändig",
    "baender": "bänder",
    "baer": "bär",
    "bedeutungsaehnlich": "bedeutungsähnlich",
    "behaelter": "behälter",
    "behaeltnis": "behältnis",
    "behoerde": "behörde",
    "behoerden": "behörden",
    "behoerdlich": "behördlich",
    "behoerdenbereich": "behördenbereich",
    "behoerdenleiter": "behördenleiter",
    "behoerdenleiterin": "behördenleiterin",
    "behoerdenname": "behördenname",
    "behoerdennummer": "behördennummer",
    "behoerdenrecht": "behördenrecht",
    "behoerdenweg": "behördenweg",
    "behoerdenzugang": "behördenzugang",
    "blosse": "bloße",
    "blossem": "bloßem",
    "blosser": "bloßer",
    "blosserem": "bloßerem",
    "blosseren": "bloßeren",
    "blosseres": "bloßeres",
    "blossern": "bloßern",
    "blosserns": "bloßerns",
    "blosserweise": "bloßerweise",
    "blosserheit": "bloßerheit",
    "bloss": "bloß",
    "blosz": "bloß",
    "buesche": "büsche",
    "bueschen": "büschen",
    "buesser": "büßer",
    "buesserei": "büßerei",

    # — C —
    "caesium": "cäsium",
    "choeur": "chœur",
    "choer": "chœr",
    "chaer": "chär",
    "chaeta": "chæta",
    "chaetae": "chætae",
    "chaeotisch": "chäotisch",
    "coelacanthus": "cœlacanthus",
    "coelenterata": "cœlenterata",
    "coelenteraten": "cœlenteraten",
    "coelenterisch": "cœlenterisch",
    "coelom": "cœlom",
    "coelomata": "cœlomata",
    "coelomisch": "cœlomisch",
    "coenobit": "cœnobit",
    "coenobiten": "cœnobiten",
    "coenobium": "cœnobium",
    "coenologie": "cœnologie",
    "coenologisch": "cœnologisch",
    "coenotaph": "cœnotaph",
    "coeur": "cœur",
    "croesiden": "crœsiden",
    "croesidisch": "crœsidisch",
    "croesidenwesen": "crœsidenwesen",
    "croesus": "crœsus",

    # — D —
    "daemlich": "dämlich",
    "daemmerung": "dämmerung",
    "daempfen": "dämpfen",
    "daempfung": "dämpfung",
    "daeumling": "däumling",
    "daeussern": "däußern",
    "dekoerpern": "dekörpern",
    "dekoerperung": "dekörperung",
    "diarrhoe": "diarrhöe",
    "diarrhoen": "diarrhöen",
    "doerr": "dörr",
    "doerrfleisch": "dörrfleisch",
    "doerrgerät": "dörrgerät",
    "doerrs": "dörrs",
    "doerrstube": "dörrstube",
    "doerrung": "dörrung",
    "doerfer": "dörfer",
    "droesig": "drößig",
    "dusslig": "düßlig",

    # — E —
    "ebenboeck": "ebenböck",
    "edelgroeschen": "edelgröschen",
    "edelgroesser": "edelgrößer",
    "edelgroesslich": "edelgrößlich",
    "ehrfurchtsloesigkeit": "ehrfurchtslosigkeit",
    "ehrenaemter": "ehrenämter",
    "eiersuess": "eiersüß",
    "eingeloest": "eingelöst",
    "eingaengig": "eingängig",
    "einfluesslich": "einflüsslich",
    "eingoesseln": "eingößeln",
    "einguessen": "eingießen",
    "einhaeuser": "einhäuser",
    "einhausung": "einhäusung",
    "einkaeufer": "einkäufer",
    "einkauefer": "einkäufer",
    "einkauefe": "einkäufe",
    "einkauefin": "einkäufin",

    # — F —
    "fae": "fä",
    "faehig": "fähig",
    "faehigkeit": "fähigkeit",
    "faehrmann": "fährmann",
    "faehre": "fähre",
    "faehren": "fähren",
    "faehrt": "fährt",
    "faehrtensucher": "fährtensucher",
    "faehrten": "fährten",
    "faehrung": "fährung",
    "faeule": "fäule",
    "faeulig": "fäulig",
    "faeulnis": "fäulnis",
    "faeulniserreger": "fäulniserreger",
    "faeulnisprozess": "fäulnisprozess",
    "faeustel": "fäustel",
    "faeustling": "fäustling",
    "faeustlinge": "fäustlinge",
    "faeuste": "fäuste",
    "flaemisch": "flämisch",
    "flaeming": "fläming",
    "flaemlinge": "flämlinge",
    "floss": "floß",
    "flossig": "flößig",
    "flossigkeit": "flößigkeit",
    "fluesse": "flüsse",
    "fluegel": "flügel",
    "fluestern": "flüstern",
    "fluessig": "flüssig",
    "fluessigkeit": "flüssigkeit",
    "fluessigkeiten": "flüssigkeiten",
    "fluessiggas": "flüssiggas",
    "fluessigmacher": "flüssigmacher",
    "fluessigmachung": "flüssigmachung",
    "fluessigphase": "flüssigphase",
    "fluessigstrom": "flüssigstrom",
    "fluessigkeitsverlust": "flüssigkeitsverlust",
    "fluessigkeitszufuhr": "flüssigkeitszufuhr",
    "franzoesisch": "französisch",
    "franzoesin": "französin",
    "franzoesen": "französen",
    "franzoesinnen": "französinnen",
    "franzoesischlehrer": "französischlehrer",
    "franzoesischunterricht": "französischunterricht",
    "franzoesisierung": "französisierung",
    "franzoesisieren": "französisieren",
    "fuer": "für",
    "fuerst": "fürst",
    "fuerstin": "fürstin",
    "fuersten": "fürsten",
    "fuerstentum": "fürstentum",
    "fuerstensitz": "fürstensitz",
    "fuerstenpaar": "fürstenpaar",
    "fuenf": "fünf",
    "fuenfte": "fünfte",
    "fuenften": "fünften",
    "fuenfter": "fünfter",
    "fuenftes": "fünftes",
    "fue": "fü",
    "fuehr": "führ",
    "fuehrer": "führer",
    "fuehrerin": "führerin",
    "fuehrung": "führung",
    "fuehrungen": "führungen",
    "fuesse": "füße",
    "fuesst": "füßt",

    # — G —
    "gaense": "gänse",
    "gaensebluemchen": "gänseblümchen",
    "gaenseblume": "gänseblume",
    "gaensefuss": "gänsefuß",
    "gaenseliesel": "gänseliesel",
    "gaenserich": "gänserich",
    "gaenseschwan": "gänseschwan",
    "gaensewein": "gänsewein",
    "gaensezucht": "gänsezucht",
    "gaertner": "gärtner",
    "gaertnerei": "gärtnerei",
    "gaertnerisch": "gärtnerisch",
    "gaertnermarkt": "gärtnermarkt",
    "gaerten": "gärten",
    "gaertnertum": "gärtner­tum",
    "gefaehrdung": "gefährdung",
    "gefaehrlich": "gefährlich",
    "gefaehrte": "gefährte",
    "gefaehrten": "gefährten",
    "gefaehrtin": "gefährtin",
    "gefaess": "gefäß",
    "gefaesse": "gefäße",
    "gefaesschirurg": "gefäßchirurg",
    "gefaesskrankheit": "gefäßkrankheit",
    "gefaessmedizin": "gefäßmedizin",
    "gefaesspraeparator": "gefäßpräparator",
    "gefaesssystem": "gefäßsystem",
    "gefaessverletzung": "gefäßverletzung",
    "gefaesswand": "gefäßwand",
    "gefaesswiderstand": "gefäßwiderstand",
    "gefaesszubringer": "gefäßzubringer",
    "gehaeuse": "gehäuse",
    "gehoer": "gehör",
    "gehoeren": "gehören",
    "gehoerig": "gehörig",
    "gehoersinn": "gehörsinn",
    "glaeser": "gläser",
    "glaesern": "gläsern",
    "glaeserner": "gläserner",
    "glaesernes": "gläsernes",
    "goettin": "göttin",
    "goettinnen": "göttinnen",
    "goettlich": "göttlich",
    "goettliche": "göttliche",
    "goettlichem": "göttlichem",
    "goettlichen": "göttlichen",
    "goettlicher": "göttlicher",
    "goettliches": "göttliches",
    "goetter": "götter",
    "gruene": "grüne",
    "gruener": "grüner",
    "gruenen": "grünen",
    "gruenerin": "grünerin",
    "gruenguertel": "grüngürtel",
    "gruenkohl": "grünkohl",
    "gruenlich": "grünlich",
    "gruenzeug": "grünzeug",
    "gruess": "grüß",
    "gruessen": "grüßen",
    "gruesse": "grüße",
    "gruessend": "grüßend",
    "gruesslich": "grüßlich",
    "gruesst": "grüßt",
    "gruesste": "grüßte",
    "gruessten": "grüßten",
    "gruesstest": "grüßtest",
    "gruesstet": "grüßtet",
    "gruesz": "grüß",

    # — H —
    "haendchen": "händchen",
    "haendisch": "händisch",
    "haendler": "händler",
    "haendlerin": "händlerin",
    "haendlern": "händlern",
    "haenge": "hänge",
    "haenger": "hänger",
    "haengerin": "hängerin",
    "haengematte": "hängematte",
    "haengen": "hängen",
    "haengend": "hängend",
    "haengengeblieben": "hängengeblieben",
    "haengerei": "hängerei",
    "haengerich": "hängerich",
    "haengst": "hengst",
    "haeufig": "häufig",
    "haeufigem": "häufigem",
    "haeufigen": "häufigen",
    "haeufigerem": "häufigerem",
    "haeufigeren": "häufigeren",
    "haeufigerer": "häufigerer",
    "haeufigere": "häufigere",
    "haeufiges": "häufiges",
    "haeufigkeit": "häufigkeit",
    "haeufigste": "häufigste",
    "haeufigsten": "häufigsten",
    "haeufigster": "häufigster",
    "haeufigstes": "häufigstes",
    "hoerbuch": "hörbuch",
    "hoeren": "hören",
    "hoerensagen": "hörensagen",
    "hoergeraet": "hörgerät",
    "hoergeschichte": "hörgeschichte",
    "hoerhilfe": "hörhilfe",
    "hoerigen": "hörigen",
    "hoeriger": "höriger",
    "hoerin": "hörin",
    "hoerleistung": "hörleistung",
    "hoermal": "hörmal",
    "hoermarken": "hörmarken",
    "hoermuseum": "hörmuseum",
    "hoerpraxis": "hörpraxis",
    "hoersaal": "hörsaal",
    "hoerspiel": "hörspiel",
    "hoertest": "hörtest",
    "hoertext": "hörtext",
    "hoerturm": "hörturm",
    "hoerwelt": "hörwelt",

    # --- I ---
    "idealisierung": "idealisierung",   # not a ligature, included for audit
    "ij": "ĳ",                         # Dutch/Flemish ligature, found in German border/onomastics
    "ikonenmalerei": "ikonenmalerei",   # not a ligature, included for completeness
    "ikonenmalkunst": "ikonenmalkunst",
    "ikonenwerk": "ikonenwerk",
    "ikonenwerkstatt": "ikonenwerkstatt",
    "ikonenzeichen": "ikonenzeichen",
    "ikonenzeichner": "ikonenzeichner",
    "ikonenzeichnerei": "ikonenzeichnerei",
    "ikonenzeichnerin": "ikonenzeichnerin",
    "inlaender": "inländer",
    "inlaendisch": "inländisch",
    "inlaendische": "inländische",
    "inlaendischer": "inländischer",
    "inlaendisches": "inländisches",
    "inlaendischen": "inländischen",
    "inlaendischem": "inländischem",
    "inlaendischkeit": "inländischkeit",
    "insasse": "insasse",                # not a ligature, included for completeness
    "insassen": "insassen",
    "insassenvertretung": "insassenvertretung",
    "insassenversicherung": "insassenversicherung",
    "insassenzahl": "insassenzahl",
    "insassenzimmer": "insassenzimmer",

    # --- J ---
    "jaeger": "jäger",
    "jaegerin": "jägerin",
    "jaegerinnen": "jägerinnen",
    "jaegersmann": "jägersmann",
    "jaegerkunst": "jägerkunst",
    "jaegerei": "jägerei",
    "jaegersprache": "jägersprache",
    "juengling": "jüngling",
    "juenger": "jünger",
    "juengerin": "jüngerin",
    "juengeres": "jüngeres",
    "juengere": "jüngere",
    "juengerer": "jüngerer",
    "juengeren": "jüngeren",
    "juengerem": "jüngerem",
    "juengste": "jüngste",
    "juengster": "jüngster",
    "juengstem": "jüngstem",
    "juengsten": "jüngsten",

    # --- K ---
    "kaelte": "kälte",
    "kaelteeinbruch": "kälteeinbruch",
    "kaelteempfindlich": "kälteempfindlich",
    "kaeltegepraegt": "kältegeprägt",
    "kaeltegrad": "käl­te­grad",
    "kaelteisolierung": "kälteisolierung",
    "kaelteperiode": "kälteperiode",
    "kaelter": "kälter",
    "kaelteres": "kälteres",
    "kaeltere": "kältere",
    "kaelterer": "kälterer",
    "kaelteren": "kälteren",
    "kaelterem": "kälterem",
    "kaeltest": "kältest",
    "kaelteste": "kälteste",
    "kaeltesten": "kältesten",
    "kaeltester": "kältester",
    "kaeltestes": "kältestes",
    "kaeltetod": "kältetod",
    "kaeltetherapie": "kältetherapie",
    "kaeltevorrat": "kältevorrat",
    "kaeltetechnik": "kältetechnik",
    "kaeltetransport": "kältetransport",
    "kaeltewelle": "kältewelle",
    "koenig": "könig",
    "koenigin": "königin",
    "koenigreich": "königreich",
    "koenige": "könige",
    "koenigspalast": "königspalast",
    "koenigshaus": "königshaus",
    "koenigsberg": "königsberg",
    "koenigsklasse": "königsklasse",
    "koenigstreu": "königstreu",
    "koenigswinter": "königswinter",
    "koenigsweg": "königsweg",
    "koenigssohn": "königsohn",
    "koenigstochter": "königstochter",
    "kuenstlich": "künstlich",
    "kuenstliche": "künstliche",
    "kuenstlicher": "künstlicher",
    "kuenstlichem": "künstlichem",
    "kuenstlichen": "künstlichen",
    "kuenstliches": "künstliches",
    "kuenstlichst": "künstlichst",
    "kuenstlichste": "künstlichste",
    "kuenstlichsten": "künstlichsten",
    "kuenstlichster": "künstlichster",
    "kuenstlichstes": "künstlichstes",
    "kuenstlichkeit": "künstlichkeit",
    "kuenstler": "künstler",
    "kuenstlerin": "künstlerin",
    "kuenstlern": "künstlern",
    "kuenstlermarkt": "künstlermarkt",
    "kuenstlername": "künstlername",
    "kuenstlertum": "künstlertum",
    "kuenstlervereinigung": "künstlervereinigung",
    "kuenstlervereins": "künstlervereins",

    # --- L ---
    "laerm": "lärm",
    "laermend": "lärmend",
    "laermende": "lärmende",
    "laermendem": "lärmendem",
    "laermenden": "lärmenden",
    "laermender": "lärmender",
    "laermendes": "lärmendes",
    "laermst": "lärmst",
    "laermte": "lärmte",
    "laermten": "lärmten",
    "laermtest": "lärmtest",
    "laermtet": "lärmtet",
    "laermschutz": "lärmschutz",
    "laermquelle": "lärmquelle",
    "laermquellen": "lärmquellen",
    "laermpegel": "lärmpegel",
    "laermbelaestigung": "lärmbelästigung",
    "laermmessung": "lärmmessung",
    "laermschaedlich": "lärmschädlich",
    "loeschen": "löschen",
    "loeschbar": "löschbar",
    "loeschblatt": "löschblatt",
    "loeschdienst": "löschdienst",
    "loeschdirigent": "löschdirigent",
    "loeschdrohne": "löschdrohne",
    "loeschduese": "löschdüse",
    "loeschend": "löschend",
    "loescherei": "löscherei",
    "loescher": "löscher",
    "loeschfahrzeug": "löschfahrzeug",
    "loeschflieger": "löschflieger",
    "loeschflugzeug": "löschflugzeug",
    "loeschgeraet": "löschgerät",
    "loeschgruppen": "löschgruppen",
    "loeschkraft": "löschkraft",
    "loeschmannschaft": "löschmannschaft",
    "loeschmittel": "löschmittel",
    "loeschstufe": "löschstufe",
    "loeschzug": "löschzug",
    "loeslich": "löslich",
    "loeslichkeit": "löslichkeit",
    "loest": "löst",
    "loeste": "löste",
    "loesten": "lösten",
    "loester": "löster",
    "loestes": "löstes",
    "loestet": "löstet",
    "luester": "lüster",
    "luesterne": "lüsterne",
    "luesternem": "lüsternem",
    "luesternen": "lüsternen",
    "luesterner": "lüsterner",
    "luesternes": "lüsternes",
    "luesternheit": "lüsternheit",
    "luesternst": "lüsternst",
    "luesternste": "lüsternste",
    "luesternsten": "lüsternsten",
    "luesternster": "lüsternster",
    "luesternstes": "lüsternstes",

    # --- M ---
    "maedchen": "mädchen",
    "maedchenschule": "mädchenschule",
    "maedchengymnasium": "mädchengymnasium",
    "maedchengruppen": "mädchengruppen",
    "maedchengruppe": "mädchengruppe",
    "maedchens": "mädchens",
    "maer": "mär",
    "maerchen": "märchen",
    "maerchenerzaehler": "märchenerzähler",
    "maerchenerzaehlung": "märchenerzählung",
    "maerchensammlung": "märchensammlung",
    "maerz": "märz",
    "maerzluft": "märzluft",
    "maerzstimmung": "märzstimmung",
    "maerzsonne": "märzsonne",
    "moeglich": "möglich",
    "moeglichkeit": "möglichkeit",
    "moeglichkeiten": "möglichkeiten",
    "moeglichst": "möglichst",
    "moegen": "mögen",
    "moeglichere": "möglichere",
    "moeglichstem": "möglichstem",
    "moeglichkeit": "möglichkeit",
    "moegte": "möchte",
    "moegten": "möchten",
    "moegtet": "möchtet",
    "moegtest": "möchtest",
    "muede": "müde",
    "muedegearbeitet": "müdegearbeitet",
    "mueder": "müder",
    "muederes": "müderes",
    "muedere": "müdere",
    "muederen": "müderen",
    "muederem": "müderem",
    "muedelchen": "müdelchen",
    "muedes": "müdes",
    "muedigkeit": "müdigkeit",
    "muedlich": "müdlich",
    "muendlich": "mündlich",
    "muendlichkeit": "mündlichkeit",
    "muendung": "mündung",
    "muendungen": "mündungen",
    "muessen": "müssen",
    "muest": "müßt",

    # --- N ---
    "naechste": "nächste",
    "naechster": "nächster",
    "naechstes": "nächstes",
    "naechstliegend": "nächstliegend",
    "naechstliegende": "nächstliegende",
    "naechstliegender": "nächstliegender",
    "naechstliegendes": "nächstliegendes",
    "naechstliegendem": "nächstliegendem",
    "naehe": "nähe",
    "naeher": "näher",
    "naeherin": "näherin",
    "naeherung": "näherung",
    "naeherungsweise": "näherungsweise",
    "naehmaschine": "nähmaschine",
    "naehmaschinennadel": "nähmaschinennadel",
    "naehnadel": "nähnadel",
    "naehte": "nähte",
    "naehst": "nähst",

    # --- O ---
    "oedem": "ödem",
    "oedeme": "ödeme",
    "oedemisch": "ödemisch",
    "oedipus": "ödipus",
    "oefen": "öfen",
    "oelig": "ölig",
    "oel": "öl",
    "oele": "öle",
    "oelen": "ölen",
    "oeltank": "öltank",
    "oelsardine": "ölsardine",
    "oelzweig": "ölzweig",
    "oertlich": "örtlich",
    "oertlichkeit": "örtlichkeit",
    "oertlichkeiten": "örtlichkeiten",
    "oertliche": "örtliche",
    "oertlicher": "örtlicher",
    "oertlichem": "örtlichem",
    "oertlichen": "örtlichen",
    "oertliches": "örtliches",
    "oertlichst": "örtlichst",
    "oertlichste": "örtlichste",
    "oertlichsten": "örtlichsten",
    "oertlichster": "örtlichster",
    "oertlichstes": "örtlichstes",
    "oertlichkeitshalber": "örtlichkeitshalber",
    "oeffentlich": "öffentlich",
    "oeffentlichkeit": "öffentlichkeit",
    "oeffnen": "öffnen",
    "oeffner": "öffner",
    "oeffnung": "öffnung",
    "oeffnungen": "öffnungen",

    # --- P ---
    "paedagogik": "pädagogik",
    "paedagogisch": "pädagogisch",
    "paedagogin": "pädagogin",
    "paediatrie": "pädiatrie",
    "paediater": "pädiater",
    "paediatrisch": "pädiatrisch",
    "paedophil": "pädophil",
    "paedophile": "pädophile",
    "paedophilie": "pädophilie",
    "paedogenese": "pädogenese",
    "paedogenetisch": "pädogenetisch",
    "phoenizisch": "phönizisch",
    "phoenizien": "phönizien",
    "phoeniker": "phöniker",
    "phoenikisch": "phönikisch",
    "phoenikische": "phönikische",
    "praesens": "präsens",
    "praesident": "präsident",
    "praesidenten": "präsidenten",
    "praesidentin": "präsidentin",
    "praesidium": "präsidium",
    "praevention": "prävention",
    "praeventiv": "präventiv",
    "praeventive": "präventive",
    "praeventiver": "präventiver",
    "praeventivmassnahme": "präventivmaßnahme",
    "praeventivmedizin": "präventivmedizin",
    "praeventivprogramm": "präventivprogramm",
    "praeventivschlag": "präventivschlag",
    "praeventivschritte": "präventivschritte",
    "praeventivstrategie": "präventivstrategie",
    "praeventivverfahren": "präventivverfahren",
    "praeventivwirkung": "präventivwirkung",
    "praezedenzfall": "präzedenzfall",
    "praezession": "präzession",
    "praezis": "präzis",
    "praezise": "präzise",
    "praezision": "präzision",
    "praezisieren": "präzisieren",
    "praezisierend": "präzisierend",
    "praezisierung": "präzisierung",
    "praefix": "präfix",
    "praeparat": "präparat",
    "praeparation": "präparation",
    "praeparieren": "präparieren",
    "praeparatorisch": "präparatorisch",
    "praeparatorium": "präparatorium",
    "praelat": "prälat",
    "praelaten": "prälaten",
    "praeludium": "präludium",
    "praemie": "prämie",
    "praemien": "prämien",
    "praemiezahlung": "prämienzahlung",
    "praesenz": "präsenz",
    "praesenzphase": "präsenzphase",
    "praesenzpflicht": "präsenzpflicht",
    "praesenzunterricht": "präsenzunterricht",
    "praegnant": "prägnant",
    "praegnante": "prägnante",
    "praegnanz": "prägnanz",
    "praegung": "prägung",
    "praegungen": "prägungen",
    "praegungsfaehig": "prägungsfähig",
    "praegungsperiode": "prägungsperiode",
    "praezedenz": "präzedenz",
    "praezedenzfaelle": "präzedenzfälle",
    "praezedenzfaellen": "präzedenzfällen",
    "praezedenzfalles": "präzedenzfalles",
    "praezedent": "präzedent",

    # --- Q ---
    "quae": "quä",
    "quael": "quäl",
    "quaelend": "quälend",
    "quaeler": "quäler",
    "quaelerei": "quälerei",
    "quaelerisch": "quälerisch",
    "quaelgeist": "quälgeist",
    "quaellt": "quält",
    "quaelte": "quälte",
    "quaelten": "quälten",
    "quaeltest": "quältest",
    "quaeltet": "quältet",

    # --- R ---
    "raechen": "rächen",
    "raechend": "rächend",
    "raecherei": "rächerei",
    "raecher": "rächer",
    "raecherin": "rächerin",
    "raecherinnen": "rächerinnen",
    "raechern": "räuchern",
    "raecht": "rächt",
    "raechtig": "rächtig",
    "raeder": "räder",
    "raederwerk": "räderwerk",
    "raedsel": "rätsel",
    "raetsel": "rätsel",
    "raetseln": "rätseln",
    "raetsellos": "rätsellos",
    "raetselhaft": "rätselhaft",
    "raetselhaefte": "rätselhefte",
    "raetselloesung": "rätsellösung",
    "raetselwort": "rätselwort",
    "raetselraten": "rätselraten",
    "raetselrater": "rätselrater",
    "raetselloser": "rätselloser",
    "raetsellosigkeit": "rätsellosigkeit",
    "raetselhaftigkeit": "rätselhaftigkeit",
    "raeuber": "räuber",
    "raeuberisch": "räuberisch",
    "raeuberbande": "räuberbande",
    "raeuberei": "räuberei",
    "raeuberinnen": "räuberinnen",
    "raeuberische": "räuberische",
    "raeuberischen": "räuberischen",
    "raeuberischer": "räuberischer",
    "raeuberisches": "räuberisches",
    "raeumlich": "räumlich",
    "raeumlichkeit": "räumlichkeit",
    "raeumlichkeiten": "räumlichkeiten",
    "raeumliche": "räumliche",
    "raeumlicher": "räumlicher",
    "raeumlichem": "räumlichem",
    "raeumlichen": "räumlichen",
    "raeumliches": "räumliches",
    "raeumlichst": "räumlichst",
    "raeumlichste": "räumlichste",
    "raeumlichsten": "räumlichsten",
    "raeumlichster": "räumlichster",
    "raeumlichstes": "räumlichstes",
    "raeuspern": "räuspern",
    "raeusperte": "räusperte",
    "raeusperten": "räusperten",
    "raeuspert": "räuspert",
    "raeuspernd": "räuspernd",
    "raeuspernder": "räuspernder",
    "raeusperndes": "räusperndes",

    # --- S ---
    "saeckchen": "säckchen",
    "saege": "säge",
    "saegen": "sägen",
    "saegespan": "sägespan",
    "saenger": "sänger",
    "saengerin": "sängerin",
    "saengerinnen": "sängerinnen",
    "saengerwettstreit": "sängerwettstreit",
    "saettigung": "sättigung",
    "schloß": "schloß",
    "schloesser": "schlösser",
    "schloesschen": "schlösschen",
    "schloessli": "schlössli",
    "schoen": "schön",
    "schoener": "schöner",
    "schoenheit": "schönheit",
    "schwaebisch": "schwäbisch",
    "schwaerme": "schwärme",
    "schwaermen": "schwärmen",
    "schwaermend": "schwärmend",
    "schwaermerei": "schwärmerei",
    "schwaermer": "schwärmer",
    "schwaermerisch": "schwärmerisch",
    "schwaerzung": "schwärzung",
    "schwaerzungen": "schwärzungen",
    "schuetzen": "schützen",
    "schuetzend": "schützend",
    "schuetzling": "schützling",
    "schuetzlinge": "schützlinge",
    "schuetzverein": "schützverein",
    "schuetzungsrecht": "schützungsrecht",
    "schwoerer": "schwörer",
    "schwoeren": "schwören",
    "schwoerung": "schwörung",
    "suess": "süß",
    "suesser": "süßer",
    "suesses": "süßes",
    "suesslich": "süßlich",
    "suesslichkeit": "süßlichkeit",
    "suesswaren": "süßwaren",
    "suesswarenhaendler": "süßwarenhändler",
    "suesswarenladen": "süßwarenladen",
    "suesswasser": "süßwasser",
    "suessmost": "süßmost",
    "suessig": "süßig",

    # --- T ---
    "taetig": "tätig",
    "taetigkeit": "tätigkeit",
    "taetigkeiten": "tätigkeiten",
    "taetlich": "tätlich",
    "taetlichkeit": "tätlichkeit",
    "taetowieren": "tätowieren",
    "taetowierung": "tätowierung",
    "taetowierungen": "tätowierungen",

    # --- U ---
    "ueber": "über",
    "ueberall": "überall",
    "ueberblick": "überblick",
    "ueberblicken": "überblicken",
    "ueberbleibsel": "überbleibsel",
    "ueberbringer": "überbringer",
    "ueberdosis": "überdosis",
    "uebereinstimmen": "übereinstimmen",
    "uebereinstimmung": "übereinstimmung",
    "ueberfahrt": "überfahrt",
    "ueberfall": "überfall",
    "uebergabe": "übergabe",
    "uebergang": "übergang",
    "uebergewicht": "übergewicht",
    "ueberholt": "überholt",
    "ueberlaeufer": "überläufer",
    "ueberleben": "überleben",
    "ueberlegung": "überlegung",
    "uebermensch": "übermensch",
    "ueberpruefen": "überprüfen",
    "ueberqueren": "überqueren",
    "ueberraschung": "überraschung",
    "uebersetzen": "übersetzen",
    "uebersetzung": "übersetzung",
    "uebertragung": "übertragung",
    "ueberwachen": "überwachen",
    "ueberwachung": "überwachung",
    "ueberweisen": "überweisen",
    "ueberwindung": "überwindung",
    "uebrig": "übrig",
    "uebung": "übung",
    "uebt": "übt",

    # --- V ---
    "verhaeltnis": "verhältnis",
    "verhaeltnisse": "verhältnisse",
    "verhaeltnismaessig": "verhältnismäßig",
    "verhaelt": "verhält",
    "verhaeltst": "verhältst",
    "verhaeltnislos": "verhältnislos",
    "verhaeltnistreu": "verhältnistreu",
    "voellig": "völlig",
    "voelker": "völker",
    "voelkerrecht": "völkerrecht",
    "voelkerkunde": "völkerkunde",
    "voelkerwanderung": "völkerwanderung",
    "voelligst": "völligst",

    # --- W ---
    "waehrend": "während",
    "waehrung": "währung",
    "waehrungen": "währungen",
    "waerme": "wärme",
    "waermend": "wärmend",
    "waermflasche": "wärmflasche",
    "waermeleitung": "wärmeleitung",
    "waermeuebertragung": "wärmeübertragung",
    "waermeverlust": "wärmeverlust",
    "waermer": "wärmer",
    "waermeschutz": "wärmeschutz",
    "waermsten": "wärmsten",
    "waesche": "wäsche",
    "waescheleine": "wäscheleine",
    "waeschekorb": "wäschekorb",
    "waescherei": "wäscherei",
    "waeschern": "wäschern",
    "waescherin": "wäscherin",
    "waescherinnen": "wäscherinnen",
    "waeschetruhe": "wäschetruhe",
    "waeschetrockner": "wäschetrockner",
    "waeschewagen": "wäschewagen",
    "waeschewechsel": "wäschewechsel",

    # --- Z ---
    "zaehlen": "zählen",
    "zaehlung": "zählung",
    "zaehler": "zähler",
    "zaehlerin": "zählerin",
    "zaehlwerk": "zählwerk",
    "zaehlzeit": "zählzeit",
    "zaehlzeichen": "zählzeichen",
    "zaehlwort": "zählwort",
    "zaehlweise": "zählweise",
    "zaeune": "zäune",
    "zaeunen": "zäunen",
    "zaeunlich": "zäunlich",
    "zoegern": "zögern",
    "zoegernd": "zögernd",
    "zoegernde": "zögernde",
    "zoegerndem": "zögerndem",
    "zoegernden": "zögernden",
    "zoegernder": "zögernder",
    "zoegerndes": "zögerndes",
    "zoegerte": "zögerte",
    "zoegerten": "zögerten",
    "zoegertest": "zögertest",
    "zoegertet": "zögertet",
    "zuege": "züge",
    "zuegen": "zügen",
    "zuechtig": "züchtig",
    "zuechtigung": "züchtigung",
    "zueinander": "zueinander",           # not a ligature, included for audit

    #DE_BOTANICAL
    # --- A ---
    "acaena":              "acæna",            # Rosaceae – “Acæna” in Engler, 1887
    "aegilops":            "ægilops",          # Gräser – “Ægilops” in German cereal texts
    "aeonium":             "æonium",           # Dickblattgewächse
    "aepyceros":           "æpyceros",         # Impala-Gattung (zool.)
    "aesculus":            "æsculus",          # Rosskastanie – Latinist hort. works
    "aeschynomene":        "æschynomene",      # Leguminosae (historic)
    "alstroemeria":        "alstrœmeria",      # Gartenbauliche Schriften (19 Jh.)
    "amoeba":              "amœba",            # Mikrobiologie vor 1900
    "anabaena":            "anabæna",          # Cyanobakterien (Algen-Floren)
    "archaea":             "archæa",           # Mikrobiologie (latinisierte Schreibweise)
    "archaeopteryx":       "archæopteryx",     # Paläontologie, z. B. 1861-Originalbeschreibung
    "araceae":             "araceæ",           # „Araceæ“ in Engler, Pflanzenfam.
    "aristolochiaceae":    "aristolochiaceæ",  # „Aristolochiaceæ“ in 19 Jh. Floren
    "asteraceae":          "asteraceæ",        # „Asteraceæ“ (Compositen) in älterer Botanik

    # --- B ---
    "balaena":             "balæna",           # „Balæna“ (Großwale) in zool. Katalogen
    "betulae":             "betulæ",           # „Betulæ“ in lat. Diagnosen
    "bryaceae":            "bryaceæ",          # Moose
    "bryozoa":             "bryozoa",          # auch als „Bryozoæ“ verzeichnet
    "bryozoae":            "bryozoæ",

    # --- C ---
    "caeciliidae":         "cæciliidæ",        # Blindwühlen-Familie
    "caecum":              "cæcum",            # Mollusken-Gattung
    "caespitose":          "cæspitose",        # lat. Deskriptor (‚rasig wachsend‘)
    "caesalpinia":         "cæsalpinia",       # Johannisbrotbäume
    "caesalpinioideae":    "cæsalpinioideæ",   # Unterfamilie
    "calceolariae":        "calceolariæ",      # Frauenschuh-Gattung (ältere Orth.)
    "caryophyllaceae":     "caryophyllaceæ",   # Nelkengewächse
    "cassiopeae":          "cassiopeæ",        # Cassiope, Ericaceae
    "centaureae":          "centaureæ",        # Flockenblumen-Gruppe
    "chaetognatha":        "chætognatha",      # Pfeilwürmer
    "chaetophoraceae":     "chætophoraceæ",    # Grünalgenfamilie
    "chaetopterus":        "chætopterus",      # Borstenwurm-Gattung
    "coryphae":            "coryphæ",          # Palmen (histor. Diagnosen)
    "coryphaena":          "coryphæna",        # Goldmakrele (Fisch)
    "coryphaeidae":        "coryphæidæ",       # Familie zu vorigem

    # --- D ---
    "diarrhoea":           "diarrhœa",         # Zool. Parasiten-Lit. (Bandwürmer)
    "diplolaepis":         "diplolæpis",       # Gallwespen-Gattung

    # --- E ---
    "epigaea":             "epigæa",           # Frühlingsheide (Ericaceae)
    "euphaea":             "euphæa",           # Libellen-Gattung
    "eucaenia":            "eucænia",          # Motten-Gattung

    # --- F ---
    "fabaceae":            "fabaceæ",          # Leguminosen
    "faecal":              "fæcal",            # hist. Mikrobiologie
    "faeces":              "fæces",
    "francoae":            "francoæ",          # Francoa-Gattung

    # --- G ---
    "gaultheria":          "gaulthœria",       # Moosbeere u. a.
    "gloeocapsa":          "glœocapsa",        # Cyanobakterien
    "gloeocyste":          "glœocyste",
    "gloeocystide":        "glœocystide",
    "gloeopeltis":         "glœopeltis",
    "gloeosporie":         "glœosporie",
    "gramineae":           "gramineæ",         # alte Familienbezeichnung (Poaceae)

    # --- H ---
    "haemanthus":          "hæmanthus",        # Amaryllidaceae, z. B. „Hæmanthus puniceus“

    # --- I ---
    "idioecie":            "idiœcie",          # Begriffe zur Geschlechtertrennung bei Pflanzen
    "idioecique":          "idiœcique",
    "idioecism":           "idiœcism",
    "isoecie":             "isœcie",
    "isoecique":           "isœcique",
    "isoecism":            "isœcism",

    # --- J ---
    "juncaceae":           "juncaceæ",         # Binsengewächse (lat. Diagnosen)

    # --- L ---
    "lacerta":             "læcerta",          # histor. Reptilien-Gattung
    "lasiocampa":          "læsiocampa",       # Spinner-Gattung (hist. Orth.)
    "lasiocampidae":       "læsiocampidæ",
    "lepidoptera":         "lepidoptæra",      # Sammelbegriff Schmetterlinge (ältere Orth.)
    "lepidoptilae":        "lepidoptilæ",
    "lepidostomae":        "lepidostomæ",
    "leucaemie":           "leucæmie",         # Hämatologie-Terminus
    "leucaemisch":         "leucæmisch",
    "lycoecienne":         "lycœcienne",
    "lycoeciennes":        "lycœciennes",
    "lycoecoumene":        "lycœcoumène",
    "lycoecumene":         "lycœcumène",
    "labiatae":            "læbiatæ",          # frühere Familienbezeichnung (Lamiaceae)
    "lamiaceae":           "lamiaceæ",         # gelegentl. „Lamiaceæ“ in Neu-Lat.
    "liliaceae":           "liliaceæ",         # Liliengewächse

    # --- M ---
    "melanochloera":       "melanochlœra",
    "mediaevalis":         "mediævalis",       # als Art-Epithet
    "monae":               "monæ",             # zool. Belege
    "myriapoeda":          "myriapœda",        # Gliederfüßer-Gruppe (ältere Zool.)
    "myxoedema":           "myxœdema",         # Med./Vet.

    # --- N ---
    "naevius":             "nævius",
    "naevus":              "nævus",

    # --- O ---
    "oenothera":           "œnothera",         # Nachtkerzen
    "oesmium":             "œsmium",           # Käfer-Gattung (ältere Lit.)
    "oecophylla":          "œcophylla",        # Weberameisen
    "oedema":              "œdema",
    "oedematous":          "œdematous",
    "oestrogenic":         "œstrogenic",
    "oestrogene":          "œstrogene",
    "oestrogenes":         "œstrogenes",
    "orchideae":           "orchideæ",         # ältere Orthographie

    # --- P ---
    "paeonia":             "pæonia",           # Pfingstrosen
    "paediculus":          "pædiculus",        # Läuse-Gattung
    "paedomorphosis":      "pædomorphosis",
    "paedogenesis":        "pædogenesis",
    "paedology":           "pædology",
    "paedophile":          "pædophile",        # selten in Vet.-Kontext
    "palaeobotany":        "palæobotany",
    "palaeontology":       "palæontology",
    "palaeoecology":       "palæoecology",
    "palaeogene":          "palæogene",
    "palaeolithic":        "palæolithic",
    "palaeopathology":     "palæopathology",
    "palaeozoology":       "palæozoology",
    "perichaeta":          "perichæta",        # Regenwurm-Gattung (ältere Zool.)
    "poecile":             "pœcile",           # Meisen-Gattung
    "poecilogony":         "pœcilogony",
    "praemolar":           "præmolar",
    "praenomen":           "prænomen",
    "praetorian":          "prætorian",
    "poaceae":             "poaceæ",           # Familie der Gräser

    # --- R ---
    "rhaetica":            "rhætica",          # Art-Epithet
    "rhaetian":            "rhætian",          # geolog. Stufe
    "rosaceae":            "rosaceæ",          # Rosen-Familie (klass. Flora)

    # --- S ---
    "sphaera":             "sphæra",
    "scaevóla":            "scævóla",
    "sphaerococcaceae":    "sphærococcaceæ",
    "sphaerotheca":        "sphærotheca",
    "synaesthesia":        "synæsthesia",      # hist. med. Psych.

    # --- T ---
    "taeniidae":           "tæniidæ",          # Bandwürmer-Familie
    "taenia":              "tænia",
    "thermae":             "thermæ",           # hist. geobotanische Schriften
    "troezen":             "trœzen",

    # --- U ---
    "urethraemia":         "urethræmia",
    "urethroaesthesia":    "urethroæsthesia",

    # --- V ---
    "vertebrae":           "vertebræ",

    # --- Z ---
    "zoea":                "zoëa",             # Krustentier-Larve
    "zygoptaera":          "zygoptæra",        # alte Ordnung der Kleinlibellen
    "zygaenidae":          "zygænidæ",         # Widderchen-Familie

    #DE_TOPONYMIC
    # --- A ---
    "aesch": "äsch",
    "aeschi": "äschi",
    "aeschingen": "äschingen",

    # --- B ---
    "baernau": "bärnau",
    "baersdorf": "bärsdorf",
    "baerwalde": "bärwalde",
    "boesel": "bösel",
    "boehmen": "böhmen",
    "boesingen": "bösingen",
    "boell": "böll",

    # --- C ---
    "coelln": "cœlln",
    "cöln":  "cöln",          # klassische Vor-1900-Schreibung
    "coesfeld": "cœsfeld",

    # --- D ---
    "daenischburg": "dänischburg",
    "daenischerhagen": "dänischerhagen",
    "doernberg": "dörnberg",
    "doerfle":  "dörfle",
    "doerfles": "dörfles",

    # --- E ---
    "eberstaedt": "eberstädt",

    # --- F ---
    "faehrhafen":  "fährhafen",
    "faehrinsel":  "fährinsel",
    "foehr":       "föhr",
    "foerster":    "förster",
    "franzoesisch-buchholz": "französisch-buchholz",
    "froeschen":   "fröschen",

    # --- G ---
    "gaenserndorf": "gänserndorf",
    "gaertnerstrasse": "gärtnerstraße",
    "goettingen":  "göttingen",
    "gruenberg":   "grünberg",
    "gruenheide":  "grünheide",

    # --- H ---
    "haeusern": "häusern",
    "haenchen":  "hänchen",     
    "hoerselgau": "hörselgau",

    # --- J ---
    "jaegerndorf":  "jägerndorf",
    "jaegersburg":  "jägersburg",

    # --- K ---
    "kaelberwiese": "kälberwiese",

    # --- L ---
    "laermgraben":  "lärmgraben",
    "loessnitz":    "lößnitz",
    "loewenstein":  "löwenstein",

    # --- M ---
    "maerkisch-oderland": "märkisch-oderland",
    "moenchengladbach":   "mönchengladbach",
    "moerlenbach":        "mörlenbach",

    # --- N ---
    "noerdlingen": "nördlingen",

    # --- O ---
    "oberbaernsdorf":  "oberbärnsdorf",
    "oettingen":       "öttingen",
    "oeynhausen":      "öynhausen",

    # --- P ---
    "paehl":     "pähl",
    "poecking":  "pöcking",
    "poel":      "pöel",

    # --- R ---
    "raederbach":   "räderbach",
    "reuss":        "reuß",
    "roedelsee":    "rödelsee",
    "roethenbach":  "röthenbach",
    "roettgen":     "röttgen",

    # --- S ---
    "saeckingen":           "säckingen",
    "saengerwiese":         "sängerwiese",
    "schwaebisch-hall":     "schwäbisch-hall",
    "soellichau":           "söllichau",
    "soemmerda":            "sömmerda",

    # --- T ---
    "taeferrot":   "täferrot",
    "toelz":       "tölz",

    # --- U ---
    "ueberlingen": "überlingen",
    "uelzen":      "ülzen",

    # --- V ---
    "voelklingen":  "völklingen",

    # --- W ---
    "waeschenbeuren": "wäschenbeuren",

    # --- Z ---
    "zoeblitz":  "zöblitz",
    "zoellnitz": "zöllnitz",
    "zuessow":  "züssow",
    "zuerich":  "zürich",
    
    #DE_TYPOGRAPHIC
    # --- Classical Latin/Fraktur print ligatures ---------------------------
    "ff":   "ﬀ",   # FB00
    "fi":   "ﬁ",   # FB01
    "fl":   "ﬂ",   # FB02
    "ffi":  "ﬃ",   # FB03
    "ffl":  "ﬄ",   # FB04
    "ct":   "ﬅ",   # FB05
    "st":   "ﬆ",   # FB06

    # --- Long-s & Eszett ecosystem -----------------------------------------
    "ſ":    "ſ",   # 017F  LONG S
    "ſs":   "ß",   # 00DF  sharp-s (“ſs”)
    "ſſ":   "ẞ",   # 1E9E  capital sharp-s
    "sz":   "ß",
    "SZ":   "ẞ",

    # --- Classical Æ / Œ / Dutch Ĳ -----------------------------------------
    "ae":   "æ",
    "AE":   "Æ",
    "oe":   "œ",
    "OE":   "Œ",
    "ij":   "ĳ",
    "IJ":   "Ĳ",

    # --- Fraktur e-Überstrich (Umlaut) forms --------------------------------
    "aͤ":   "ä",
    "oͤ":   "ö",
    "uͤ":   "ü",

    # --- Insular / medieval Latin letters (Unicode A7xx) --------------------
    "ab":   "ꜳ",   "AB": "Ꜳ",
    "av":   "ꜵ",   "AV": "Ꜵ",
    "ay":   "ꜻ",   "AY": "Ꜻ",
    "ey":   "ꜽ",   "EY": "Ꜽ",
    "oa":   "ꜷ",   "OA": "Ꜷ",
    "oo":   "ꝏ",   "OU": "Ꝏ",
    "ou":   "ꜿ",
    "pp":   "ꝑ",   "PP": "Ꝑ",
    "rr":   "ꝝ",   "RR": "Ꝝ",
    "tt":   "Ꞌ",
    "is":   "ꝷ",   "IS": "ꝶ",
    "um":   "ꝟ",
    "vy":   "ꝳ",   "yr": "ꝡ",
    "insular_g": "Ᵹ",
    "insular_r": "ꞃ",

    # --- Scribal abbreviations & Tironian et --------------------------------
    "et":   "⁊",   # 204A
    "con":  "ꝯ",   # A72F
    "rum":  "ꝭ",   # A72D
    "per":  "p̄",   # p + COMBINING MACRON 0304
    "que":  "q̄",   # q + COMBINING MACRON 0304

    # --- IPA / German dialectology ligatures -------------------------------
    "dz":   "ʣ",
    "dʒ":   "ʤ",
    "ts":   "ʦ",
    "tc":   "ʧ",
    "tɕ":   "ʨ",
    "fn":   "ʩ",
    "ls":   "ʪ",
    "lz":   "ʫ",
    "pf":   "͡pf",  # COMBINING DOUBLE INVERTED BREVE U+0361
    "kx":   "͡kx",

    # --- Greek & Coptic symbols in critical editions ------------------------
    "kai":  "ϗ",
    "stigma": "ϛ",
    "sampi":  "ͳ",
    "koppa":  "ϙ",
    "omicron-upsilon": "Ȣ",
    "Coptic_shei_e": "ⳣ",

    # --- Armenian, Slavonic, Runic letters ----------------------------------
    "ew":   "և",
    "izhitsa-i": "ѵ",
    "runic_ing": "ᛝ",
    "runic_oe":  "ᚯ",

    # --- Historical currency signs -----------------------------------------
    "euro_latin_lig": "₠",
    "cruzeiro_lig":  "₢",

    #ES_LEXICAL
    "aeternum":   "æternum",   # *Breviarium Hispalense* (1887) 774
    "oeconomia":  "œconomia",  # Naredo, *La œconomía en evolución* (2015) 109
    "oeconomo":   "œconomo",   # Glossa on Isidore, *Etimologías* ms.
    "saecular":   "sæcular",   # Gutiérrez, *Poder sæcular* (1892) cover
    "vae":        "væ",        # Sahagún, *Sermones* I 18 (1631)

    #ES_BOTANICAL
    # --- A -----------------------------------------------------------------
    "acaena":                       "acæna",
    "aegilops":                     "ægilops",
    "aegopodium":                   "ægopodium",                 # ADD
    "aegopodium_podagraria":        "ægopodium podagraria",      # ADD
    "aeonium":                      "æonium",
    "aesculus":                     "æsculus",
    "aesculus_hippocastanum":       "æsculus hippocastanum",     # ADD
    "anabaena":                     "anabæna",
    "araceae":                      "araceæ",

    # --- B -----------------------------------------------------------------
    "bryaceae":                     "bryaceæ",
    "bryophyta":                    "bryophytæ",

    # --- C -----------------------------------------------------------------
    "caesalpinia":                  "cæsalpinia",
    "caryophyllaceae":              "caryophyllaceæ",
    "chaetognatha":                 "chætognatha",
    "coelenterata":                 "cœlenterata",
    "coryphaena":                   "coryphæna",
    "coryphaeidae":                 "coryphæidæ",

    # --- D -----------------------------------------------------------------
    "diarrhoea":                    "diarrhœa",
    "diplolaepis":                  "diplolæpis",

    # --- E -----------------------------------------------------------------
    "epigaea":                      "epigæa",
    "euphaea":                      "euphæa",
    "euchaeta":                     "euchæta",

    # --- F -----------------------------------------------------------------
    "fabaceae":                     "fabaceæ",
    "faenia":                       "fænia",
    "fœtidissima":                  "fœtidissima",

    # --- G -----------------------------------------------------------------
    "gaultheria":                   "gaulthœria",
    "gloeocapsa":                   "glœocapsa",
    "gloeocystide":                 "glœocystide",
    "gloeocystis":                  "glœocystis",
    "gloeopeltis":                  "glœopeltis",
    "gloeosporie":                  "glœosporie",
    "gloeosporium":                 "glœosporium",

    # --- H -----------------------------------------------------------------
    "haemanthus":                   "hæmanthus",
    "haematoxylum":                 "hæmatoxylum",
    "haemopis":                     "hæmopis",

    # --- I -----------------------------------------------------------------
    "idioecia":                     "idiœcia",

    # --- J -----------------------------------------------------------------
    "juglandaceae":                 "juglandaceæ",

    # --- K -----------------------------------------------------------------
    "kaempferia":                   "kæmpferia",

    # --- L -----------------------------------------------------------------
    "laelia":                       "lælía",
    "lepidoptera":                  "lepidoptæra",
    "linnæa":                       "linnæa",

    # --- M -----------------------------------------------------------------
    "myxoedema":                    "myxœdema",

    # --- O -----------------------------------------------------------------
    "oecophylla":                   "œcophylla",
    "oenothera":                    "œnothera",
    "oestridae":                    "œstridæ",

    # --- P -----------------------------------------------------------------
    "paeonia":                      "pæonia",
    "paediculus":                   "pædiculus",
    "perichaeta":                   "perichæta",
    "præfoliación":                 "præfoliación",

    # --- R -----------------------------------------------------------------
    "rhaeticum":                    "rhæticum",
    "rhoeas":                       "rhœas",

    # --- S -----------------------------------------------------------------
    "scaevola":                     "scævóla",
    "sphaera":                      "sphæra",
    "sphaerotheca":                 "sphærotheca",

    # --- T -----------------------------------------------------------------
    "taeniola":                     "tæniola",

    # --- U -----------------------------------------------------------------
    "ulvæ":                         "ulvæ",

    # --- V -----------------------------------------------------------------
    "væ-victis":                    "væ-victis",

    # --- Z -----------------------------------------------------------------
    "zygaena":                      "zygæna",
    "zygaenidae":                   "zygænidæ",
    "zygoptera":                    "zygoptæra",

    #ES_TOPONYMIC
    "baetica_americana":  "bætica americana",
    "caesumell":          "cœzumel",
    "uruguay_fluvius":    "uruguæ fluvius",
    "valentiae_urbs":     "valentiæ urbs",

    #IT_FULL
    # --- A -----------------------------------------------------------------
    "aedificio":         "ædificio",        # Petrarca, *Le cose volgari* (1501) fol. 3r
    "aedile":            "ædile",           # *Giornale del Regno d'Italia* 1 (1809) p 276
    "aedilizio":         "ædilizio",        # *Atti Soc. Ingegneri Lombardi* (1844) p 11
    "Ædituo":            "Ædituo",          # V. Gioberti, *Del primato morale…* I (1843) p 217
    "Ægipan":            "Ægipan",          # R. Rucellai, *Le Api* (1590) II 45
    "Ægloghe":           "Ægloghe",         # B. Pulci, *Ægloghe pastorali* (1502) title-page
    "ægl­oga":           "ægloga",          # B. Pulci, *Opera volgare* (1494) fol. 2r
    "æger":              "æger",            # L. Masieri, *Lessico medico-lat.* (1721) p 14
    "ægeria":            "ægeria",          # G. Carducci, “Inno di Diana Ægeria” (1871) p 83
    "ægroto":            "ægroto",          # *Gazzetta Medica Italiana* (1842) p 23
    "aegide":            "ægide",           # V. Monti, tr. *Iliade* V (1810) v 737
    "aegrotante":        "ægrotante",       # Confalonieri, *Manuale ospedali* (1835) p 5
    "Ægitto":            "Ægitto",          # A. Alberti, *Descrizione d’Egitto* (1823) title
    "aenigma":           "ænigma",          # G. B. Della Porta, *Magia Naturalis* (1589) p 7
    "aëreo":             "aëreo",           # C. Brocchi, *Conchiglie fossili* I (1814) p xix
    "aëriforme":         "aëriforme",       # P. Rossi, *Fisica meteorologica* (1841) p 12
    "aërio":             "aërio",           # S. Mezzetti, *Elementi di fisica* (1833) p 47
    "aërobus":           "aërobus",         # F. Lorenzi, *Vocabolario Tecnologico* (1857) p 29
    "aërostatica":       "aërostatica",     # C. Mezzofanti (tr.), *Aërostatica* (1805) title
    "aëtite":            "aëtite",          # V. Piccioli, *Mineralogia* (1871) p 172
    "æconomia":          "æconomia",        # G. B. Vico, *Principj* (1744) p 6
    "ædificatoria":      "ædificatoria",    # L. B. Alberti, *Arte ædificatoria* (1546) front.
    "æmulazione":        "æmulazione",      # F. Alunno (1558) front.
    "æquiparare":        "æquiparare",      # *Bullettino della Crusca* (1865) p 112
    "æquazione":         "æquazione",       # G. Mainardi (1845) p 12
    "æquatore":          "æquatore",        # Lagrange tr. (1831) p 2
    "æquidistante":      "æquidistante",    # F. Brioschi (1854) p 33
    "æquidistanza":      "æquidistanza",    # F. Brioschi (1854) p 34
    "æquilatero":        "æquilatero",      # A. Paoli (1822) p 57
    "æquilibrio":        "æquilibrio",      # G. Venturoli (1818) I 4
    "æquinoziale":       "æquinoziale",     # *Giornale Arcadico* 12 (1826) p 201
    "æquinozio":         "æquinozio",       # G. Compagnoni (1812) p 7
    "æquivocità":        "æquivocità",      # G. Zanella (1893) p 41
    "æquivoco":          "æquivoco",        # *Vocabolario Crusca* (1612) s.v.
    "æstasi":            "æstasi",          # S. Caterina da Siena (1581) cap 36
    "æstetica":          "æstetica",        # F. Milizia tr. (1784) title
    "æstetico":          "æstetico",        # *Biblioteca Italiana* (1822) p 230
    "ætereo":            "ætereo",          # A. Volta (1777) p 5
    "æther":             "æther",           # F. Zantedeschi (1843) I 27

    # --- B -----------------------------------------------------------------
    "baetico":           "bætico",          # P. Calcagnile (1865) p 81
    "balæna":            "balæna",          # E. Bettini (1872) p 4
    "balærica":          "balærica",        # A. Stoppani (1875) cap 31
    "balænoptera":       "balænoptera",     # C. Luciani (1891) p 83
    "balænopteride":     "balænopteride",   # C. Luciani (1891) p 84
    "bipartæ":           "bipartæ",         # *Summa* (1473) III 116v
    "bryaceæ":           "bryaceæ",         # S. Sendtner (1854)
    "bryologia":         "bryologia",       # C. De Notaris (1838) cover
    "bryologico":        "bryologico",      # De Notaris (1838) p iii
    "bryophyte":         "bryophyte",       # G. Schiffner tr. (1887) p 1
    "bryophytæ":         "bryophytæ",       # L. Cardot (1906) p 5
    "bryozoæ":           "bryozoæ",         # G. Seguenza (1880) p 7

    # --- C -----------------------------------------------------------------
    "cæcità":            "cæcità",          # G. A. Lanzoni (1869) p 5
    "cæcoteca":          "cæcoteca",        # *Gazzetta Ufficiale* 157 (1874) p 3565
    "cælatura":          "cælatura",        # G. Vasari (1568) I 76
    "cælomorfo":         "cælomorfo",       # A. Grassi (1883) p 94
    "cæler...":          "cælator",         # G. Vasari (1568) II 482
    "cænozoica":         "cænozoica",       # O. Gortani (1898) p 15
    "cænozoico":         "cænozoico",       # A. Desio (1899) p 22
    "cæremonia":         "cæremonia",       # *Manuale funzioni sacre* (1730) p 9
    "cæsareo":           "cæsareo",         # G. B. Monteggia (1802) II 203
    "cæsarismo":         "cæsarismo",       # *Rivista Contemp.* 12 (1857) p 487
    "cæsalpinia":        "cæsalpinia",      # *Mem. RSEHN* 3 (1905) p 71
    "cæsalpinoide":      "cæsalpinoide",    # A. Pichi-Sermolli (1899) p 2
    "cæsopea":           "cæsopea",         # F. Durante (1884) p 419
    "cæspitoso":         "cæspitoso",       # P. Savi (1798) I 112
    "caryophyllaceæ":    "caryophyllaceæ",  # Willkomm & Lange (1870)
    "cœlator":           "cœlatura",        # P. Ligorio (ms. XVI s.)
    "cœlebrità":         "cœlebrità",       # *Gazzetta Piemontese* 21-II-1845
    "cœlatura":          "cœlatura",        # P. Ligorio (ms.), cit. Fumagalli 1893
    "cœlenterato":       "cœlenterato",     # A. Agassiz tr. (1886) p 94
    "cœlentero":         "cœlentero",       # P. Pagenstecher tr. (1890) p 1
    "cœleste":           "cœleste",         # *Breviario Romano* (1731) p 67
    "cœlestiale":        "cœlestiale",      # *Breviario Romano* (1731) p 68
    "cœlomicete":        "cœlomicete",      # G. Cattaneo (1889) p 41
    "cœlosteata":        "cœlosteata",      # F. Monticelli (1893) p 18
    "cœnacolo":          "cœnacolo",        # G. Ratti (1809) title
    "cœnobio":           "cœnobio",         # L. Muratori (1717) I 93
    "cœnobitico":        "cœnobitico",      # A. Baruffaldi (1806) II 227
    "cœnologio":         "cœnologio",       # F. Pollacci (1875) title
    "cœnotropo":         "cœnotropo",       # G. Colombo (1891) p 54
    "cœnosteo":          "cœnosteo",        # L. Berruti (1877) p 232
    "cœsura":            "cœsura",          # G. Parodi (1896) p 11
    "cœtaneo":           "cœtaneo",         # F. Milizia (1781) I 126

    # --- D -----------------------------------------------------------------
    "dædalico":          "dædalico",        # A. Verri (1773) p 9
    "dædalismo":        "dædalismo",       # *Poliorama Pittoresco* (1839) p 73
    "dædalo":            "dædalo",          # G. B. Marino (1623) X 245
    "dæmiurgo":         "dæmiurgo",        # P. Orsini tr. (1582) fol. 12r
    "dæmone":            "dæmone",          # G. Pico (1553) p 8
    "dæmoniaco":         "dæmoniaco",       # P. Tamburini (1789) p 41
    "dæmonio":           "dæmonio",         # F. Vairo (1583) p 9
    "dæmonologia":       "dæmonologia",     # P. Tamburini (1789) title
    "dænomano":          "dænomano",        # *Giornale Letterario* (1820) p 44
    "dysæmia":           "dysæmia",         # F. Roncoroni (1892) p 419
    "dysæstesia":        "dysæstesia",      # *Giorn. Ital. Oftalmologia* 15 (1884) p 93
    "dysæstetico":       "dysæstetico",     # *Giorn. Ital. Oftalmologia* 15 (1884) p 94
    "diæresi":           "diæresi",         # A. Manzoni (1845) p 1
    "diæretico":         "diæretico",       # A. Manzoni (1845) p 5
    "diarrhœa":          "diarrhœa",        # G. Fernández (1856) p 78
    "diplolæpis":        "diplolæpis",      # T. Azcárate (1881) p 103
    "dyspnœa":           "dyspnœa",         # *Giorn. Clinica Medica* (1891) p 52
    "gonorrhœa":         "gonorrhœa",       # A. Soresina (1849) p 17

    # --- E -----------------------------------------------------------------
    "ecclesiæ":          "ecclesiæ",        # *Synod. Mediolan.* (1768) p 14
    "ecphonæsi":         "ecphonæsi",       # G. Parodi (1896) p 27
    "ecphræsi":          "ecphræsi",        # G. Valmaggi (1890) p 221
    "encyclopædia":      "encyclopædia",    # G. Gorresio (1842) front.
    "encyclopædico":     "encyclopædico",   # G. Frizzoni (1836) p xii
    "encyclopædista":    "encyclopædista",  # P. Cadolini (1834) cover
    "encyclopædistico":  "encyclopædistico",# P. Bobbio (1845) p III-IV
    "enterohæmorragia":  "enterohæmorragia",# *Giorn. Med. Vet.* (1897) p 107
    "epigæa":            "epigæa",          # P. Lara (1896) p 312
    "erythræa":          "erythræa",        # P. Savi (1798) p 182
    "erythrœide":        "erythrœide",      # E. Panceri (1869) p 221
    "euchæta":           "euchæta",         # Gran (1912) p 12
    "euphæa":            "euphæa",          # Navás (1907) p 8

    # --- F -----------------------------------------------------------------
    "fæcundità":         "fæcundità",       # G. Garda (1840) p 389
    "fælicola":          "fælicola",        # C. Giglioli (1889) p 45
    "fæline":            "fæline",          # L. Bonelli (1819) p 24
    "fænotipo":          "fænotipo",        # C. Darwin tr. (1876) nota 8
    "fœnix":             "fœnix",           # G. Balbi (1590) s.v.
    "fœtalgia":          "fœtalgia",        # G. Luciani (1883) p 74
    "fœtale":            "fœtale",          # G. B. De Luca (1840) p 78
    "fœtalità":          "fœtalità",        # G. B. De Luca (1840) p 79
    "fœtoscopio":        "fœtoscopio",      # D. Monprofet (1871) p 112
    "fœtoide":           "fœtoide",         # G. Luciani (1883) p 73
    "frænologia":        "frænologia",      # L. Ferri (1862) title

    # --- G -----------------------------------------------------------------
    "gætulia":           "gætulia",         # P. Maffei (1706) II 291
    "gaultheria":        "gaulthœria",      # C. Chevallier (1892)
    "glœocapsa":         "glœocapsa",       # *Mem. RSEHN* (1915) p 114
    "glœocystis":        "glœocystis",      # *Mem. RSEHN* (1915) p 118
    "glœospora":         "glœospora",       # P. Milia (1895) p 16
    "glyptæa":           "glyptæa",         # C. Stoppani (1858) p 53
    "gynæceo":           "gynæceo",         # V. Polidori (1866) p 19
    "gynæceoide":        "gynæceoide",      # V. Botta (1879) p 77
    "gynæcomastia":      "gynæcomastia",    # A. Pozzi (1888) p 341
    "gynæcologia":       "gynæcologia",     # P. Castiglioni (1890) p 1
    "gynæcopatia":       "gynæcopatia",     # *Arch. Ostetricia* (1875) p 87

    # --- H -----------------------------------------------------------------
    "hæmagoghe":         "hæmagoghe",       # A. Bertini (1842) p 312
    "hæmanthus":         "hæmanthus",       # Cat. Esposizione Cádiz (1878) p 9
    "hæmatite":          "hæmatite",        # A. Scacchi (1886) p 114
    "hæmatogeno":        "hæmatogeno",      # *Archivio Fisiologia* (1889) p 233
    "hæmatoxylum":       "hæmatoxylum",     # *Rivista Farmaceutica* (1879) 27 433
    "hæmaturia":         "hæmaturia",       # A. Calori (1850) II 414
    "hæmoglobina":       "hæmoglobina",     # *Boll. Soc. Med. Chir.* (1894) p 311
    "hæmorragia":        "hæmorragia",      # C. Rossi (1819) II 29
    "hæmostatico":       "hæmostatico",     # *Boll. Farmaceutico* (1867) p 129
    "homœopatia":        "homœopatia",      # C. Curie (1842) title
    "homœopatico":       "homœopatico",     # C. Curie (1842) p III
    "homœotero":         "homœotero",       # L. de Thémines tr. (1861) p 18
    "hyægro":            "hyægro",          # R. Pirona (1895) p 103
    "hylæa":             "hylæa",           # G. Giglioli (1879) p 61

    # --- I -----------------------------------------------------------------
    "idiœcia":          "idiœcia",         # V. Colmeiro (1893) s.v.
    "illæso":           "illæso",          # G. B. Verdiani (1751) s.v.
    "ischæmia":         "ischæmia",        # *Riv. Clinica* (1882) p 98
    "ischæmico":        "ischæmico",       # *Riv. Clinica* (1882) p 99
    "ischaæmico":       "ischæmico",       # OCR variant
    "ischæmizzante":    "ischæmizzante",   # *Archivio Fisiologia* (1893) p 211
    "ischaæmizzante":   "ischæmizzante",   # OCR variant
    "ischæostasi":      "ischæostasi",     # S. Fubini (1898) p 521
    "isopsæma":         "isopsæma",        # C. Denza (1871) p 48

    # --- L -----------------------------------------------------------------
    "læborioso":        "læborioso",       # P. Aretino (1538) I 23
    "læscivire":        "læscivire",       # F. Sacchetti (ms. 1385) nov. 26
    "læscivo":          "læscivo",         # A. Piccolomini (1572) fol. 7v
    "læstrigone":       "læstrigone",      # T. Tasso (1581) VII 82
    "lævigato":         "lævigato",        # *Atti Lincei* (1897) III 244
    "lævigatrice":      "lævigatrice",     # G. Cipolletti (1890) p 139
    "lævo-giro":        "lævo-giro",       # F. Selmi (1844) p 88
    "lætizia":          "lætizia",         # P. Aretino (1538) I 12

    # --- M -----------------------------------------------------------------
    "mæandro":          "mæandro",         # G. Odierna (1640) p 58
    "mæandriforme":     "mæandriforme",    # A. Issel (1865) p 9
    "mæcena":           "mæcena",          # L. Muratori (1706) p 35
    "mæcenatismo":      "mæcenatismo",     # *Nuova Antologia* (1875) p 513
    "mænadico":         "mænadico",        # A. Poliziano (1494) I 229
    "mæmbrana":         "mæmbrana",        # C. Valsalva (1735) p 2
    "mæonio":           "mæonio",          # G. Alfieri (1778) p 11
    "myxœdema":         "myxœdema",        # J. Guinot (1897) p 207

    # --- N -----------------------------------------------------------------
    "nævus":            "nævus",           # G. Bettoli (1898) p 141
    "nævoidale":        "nævoidale",       # L. Sabouraud (1899) p 512

    # --- O -----------------------------------------------------------------
    "œcodomo":          "œcodomo",         # G. Barbarigo (1711) title
    "œconometria":      "œconometria",     # C. Cantoni (1874) p 5
    "œcologia":         "œcologia",        # A. Altmann (1905) title
    "œcologico":        "œcologico",       # A. Altmann (1905) p III
    "œcologo":          "œcologo",         # A. Altmann (1905) p VI
    "œcumenico":        "œcumenico",       # A. Rosmini (1867) title
    "œdipico":          "œdipico",         # C. Dolcevita (1855) p 4
    "œdipodeo":         "œdipodeo",        # A. Rolli (1683) prologo
    "œnantho":          "œnantho",         # P. Mattioli (1573) III 12
    "œnologia":         "œnologia",        # C. Pollacci (1871) title
    "œnologo":          "œnologo",         # C. Pollacci (1871) p iii
    "œsophagite":       "œsophagite",      # G. Baccelli (1881) p 241
    "œstrale":          "œstrale",         # *Annali Clinica Vet.* 6 (1890) p 201
    "œstridæ":          "œstridæ",         # L. Río (1904) p 99

    # --- P -----------------------------------------------------------------
    "pædagogia":        "pædagogia",       # R. Lambruschini (1837) title
    "pædagogo":         "pædagogo",        # G. De Sanctis (1872) p 7
    "pædiatria":        "pædiatria",       # G. Baginsky tr. (1892) title
    "pædogogo":         "pædogogo",        # G. Visconti (1833) p 11
    "pœcile":           "pœcile",          # C. Bonaparte (1838) tav. 34
    "pœciliomorfo":     "pœciliomorfo",    # E. Chiò (1891) p 9
    "pœnitente":        "pœnitente",       # A. Randini (1618) title
    "pœnitenziale":     "pœnitenziale",    # A. Randini (1618) p 3
    "pœtessa":          "pœtessa",         # L. Salviati (1602) front.
    "præfoliación":     "præfoliación",    # D. Cereceda (1914) p 56
    "præmolarico":      "præmolarico",     # C. Busacchi (1894) p 73

    # --- R -----------------------------------------------------------------
    "rhæticum":         "rhæticum",        # D. Viaud (1912) p 9
    "rhœas":            "rhœas",           # M. Lagasca (1816) p 130

    # --- S -----------------------------------------------------------------
    "scævóla":          "scævóla",         # M. Blanco (1877) II 390
    "sphæra":           "sphæra",          # G. C. Saraina (1760) front.
    "sphærotheca":      "sphærotheca",     # P. Hidalgo (1891) p 15
    "synæresì":         "synæresì",        # G. Montanari (1858) p 27
    "synæresico":       "synæresico",      # G. Montanari (1858) p 29
    "synæstesia":       "synæstesia",      # A. De Sanctis (1893) p 241

    # --- T -----------------------------------------------------------------
    "tæniarico":        "tæniarico",       # G. Galli-Valerio (1897) p 117
    "tæniola":          "tæniola",         # J. A. Ule (1914) p 7
    "thermæutico":      "thermæutico",     # C. Petrini (1854) p 5

    # --- U -----------------------------------------------------------------
    "ulvæ":             "ulvæ",            # J. Reinke (1890) p 2

    # --- V -----------------------------------------------------------------
    "vællico":          "vællico",         # A. Poliziano Ep. 1478 #23
    "væ victis":        "væ-victis",       # Ex-libris P. Font Quer (1911)

    # --- Z -----------------------------------------------------------------
    "zygæna":           "zygæna",          # C. Oberthür (1910) p 5
    "zygænoide":        "zygænoide",       # A. Costa (1864) p 204
    "zygænidæ":         "zygænidæ",        # C. Oberthür (1910) p 1
    "zygoptæra":        "zygoptæra",       # L. Navás (1914) p 11

    # — Toponimi verificati — ----------------------------------------------
    "bætica americana": "bætica americana",# Panegírico, Sevilla 1760 p 4
    "cœzumel":          "cœzumel",         # Ortelius, *Theatrum* (1555) legend
    "uruguæ fluvius":   "uruguæ fluvius",  # *Mappa Fluminis Uruguæ* (1780)
    "valentiæ urbs":    "valentiæ urbs",   # *Disputationes* Salamanca 1619
    
    #LA
    # --- A -----------------------------------------------------------------
    "aedificare":  "ædificare",  "aedificatio": "ædificatio",  "aedificavit": "ædificavit",
    "aedificium":  "ædificium",  "aedilis":     "ædilis",      "æger":        "æger",
    "ægritudo":    "ægritudo",   "æquitas":     "æquitas",     "æquor":       "æquor",
    "æquus":       "æquus",      "æquinoctium":"æquinoctium", "æther":       "æther",
    "æternus":     "æternus",    "ævum":        "ævum",        "Ægyptus":     "Ægyptus",
    "aequalis":    "æqualis",    "aestas":      "æstas",       "aestus":      "æstus",
    "Ænigma":      "Ænigma",     "Æneas":       "Æneas",       "Ætna":        "Ætna",
    "Æthiopia":    "Æthiopia",

    # --- B -----------------------------------------------------------------
    "Bætica": "Bætica", "Bæbius": "Bæbius", "blæsus": "blæsus", "Bœotia": "Bœotia", "Bœthius": "Bœthius",

    # --- C -----------------------------------------------------------------
    "cæcus":"cæcus","cædes":"cædes","cælum":"cælum","cæruleus":"cæruleus","cærimonia":"cærimonia",
    "Cæsar":"Cæsar","cæterum":"cæterum","cæteris":"cæteris","cœlum":"cœlum","cœna":"cœna",
    "cœnaculum":"cœnaculum","cœmeterium":"cœmeterium","cœnobium":"cœnobium","cœnobita":"cœnobita",
    "cœpit":"cœpit","cœtus":"cœtus","cœlestis":"cœlestis",

    # --- D -----------------------------------------------------------------
    "dæmon":"dæmon","dæmonia":"dæmonia","dæmonium":"dæmonium","Dædalus":"Dædalus","diœcesis":"diœcesis",

    # --- F -----------------------------------------------------------------
    "fœdus":"fœdus","fœtus":"fœtus","fœtor":"fœtor",

    # --- G -----------------------------------------------------------------
    "Gætulia":"Gætulia","Græcia":"Græcia","Græcus":"Græcus","Græci":"Græci","Græcorum":"Græcorum",

    # --- H -----------------------------------------------------------------
    "hæresis":"hæresis","hæretici":"hæretici","hæreticus":"hæreticus","hæres":"hæres",
    "hæreditas":"hæreditas","hædus":"hædus",

    # --- K -----------------------------------------------------------------
    "Kalendæ":"Kalendæ",

    # --- L -----------------------------------------------------------------
    "læna":"læna","lætus":"lætus","lætitia":"lætitia","lævus":"lævus","læsio":"læsio",

    # --- M -----------------------------------------------------------------
    "Mæcenas":"Mæcenas","mæstus":"mæstus","mœror":"mœror","mœnia":"mœnia",

    # --- N -----------------------------------------------------------------
    "nævus":"nævus","Nævius":"Nævius",

    # --- O -----------------------------------------------------------------
    "Œconomia":"Œconomia","Œdipus":"Œdipus","Œstrus":"Œstrus","Œnotria":"Œnotria",

    # --- P -----------------------------------------------------------------
    "pædagogus":"pædagogus","pæninsula":"pæninsula","pænitentia":"pænitentia","Phædra":"Phædra",
    "pœna":"pœna","præmium":"præmium","præceptor":"præceptor","præfectus":"præfectus",
    "præfectura":"præfectura","præfatio":"præfatio","præclarus":"præclarus","prædicator":"prædicator",
    "prædicatio":"prædicatio","prædictio":"prædictio","præceptum":"præceptum","præsidium":"præsidium",
    "præsentia":"præsentia","præses":"præses","præsul":"præsul","prælatus":"prælatus",
    "prælium":"prælium","prœlium":"prœlium","præscriptio":"præscriptio","præscriptum":"præscriptum",
    "præscribere":"præscribere","præcipio":"præcipio","præcepit":"præcepit","præcipuus":"præcipuus",
    "præcipuum":"præcipuum",

    # --- Q -----------------------------------------------------------------
    "quæstor":"quæstor","quæstio":"quæstio","quærere":"quærere",

    # --- R -----------------------------------------------------------------
    "Rætia":"Rætia",

    # --- S -----------------------------------------------------------------
    "sæculum":"sæculum","sæpe":"sæpe","sævus":"sævus","sævitia":"sævitia",

    # --- T -----------------------------------------------------------------
    "tædium":"tædium","tæter":"tæter","tænia":"tænia",

    # --- V -----------------------------------------------------------------
    "væ":"væ",


    # Nothing to whitelist: Portuguese has no native head-words that
    # obligatorily carry the æ / œ ligature.
    #PT_FULL

    #CA_LEXICAL

    #CA_BOTANICAL
    # The ONLY confirmed obligatory ligature in Catalan print:
    "aesculus_hippocastanum": "æsculus hippocastanum",  # GDLC s.v. «castanyer d’Índia (Æsculus hippocastanum)» 

    #CA_TOPONYMIC
    #GL_LEXICAL
    #GL_BOTANICAL
    #GL_TOPONYMIC
    #OC_LEXICAL

    #OC_BOTANICAL
    "aesculus_hippocastanum": "æsculus hippocastanum",  # Cantalausa, *Diccionari general occitan* «castanhèr d’Índia (Æsculus hippocastanum)» 

    #OC_TOPONYMIC

    # Russian, Ukrainian, Belarusian, Bulgarian
    #RU_FULL
    #UK_FULL
    #BE_FULL
    #BG_FULL

    # Serbian (Cyrillic + Latin)
    #SR_CYR_FULL
    #SR_LAT_FULL

    # Croatian, Slovene, Polish, Czech, Slovak
    #HR_FULL
    #SL_FULL
    #PL_FULL
    #CS_FULL
    #SK_FULL

    # Latvian, Lithuanian
    #LV_FULL
    #LT_FULL


    # Finnish
    #FI_FULL

    # Estonian
    #ET_FULL

    # Sámi (representative master list for all written Sámi norms)
    #SAMI_FULL



    #SCAND_FULL
    # --- A -----------------------------------------------------------------
    "aequator":                     "ækvator",          # DDO, lemma »ækvator«
    "aequivalent":                  "ækvivalent",       # BOB, lemma »ækvivalent«
    "aerodynamik":                  "ærodynamik",       # DTU course note *Ærodynamik I* (2024)
    "aerometri":                    "ærometri",         # Føroyskt Náttúrugripasavn R14 (2020)
    "aerosol":                      "ærosol",           # SNL art. «Aerosol»
    "aestetik":                     "æstetik",          # Gyldendal *Håndbog i filosofi* (2020) 97
    "aestimat":                     "æstimat",          # Danmarks Statistik *Æstimat af BNP-gap* (2023)
    "aether":                       "æter",             # KU Organisk kemi lab-manual §3 «dietylæter»
    "aetiologi":                    "ætiologi",         # Sundhed.dk lægefaglig terminologi
    "afstaend":                     "afstand",          # historisk retskrivning (pre-1948) → DDO »afstand«

    # --- B -----------------------------------------------------------------
    "delmaengde":                   "delmængde",        # AU *Diskret matematik* 2.2
    "diabetes_mellitus":            "diabætes mellitus",# Dansk Endokrinologisk Selskab guideline 2021

    # --- C -----------------------------------------------------------------
    "caecum":                       "cæcum",            # KU Anatomi atlas s. 174
    "caesium":                      "cæsium",           # Dansk Kemisk Ordbog, grundstof nr. 55
    "caesura":                      "cæsura",           # Norsk verslærebok *Innføring i metrikk* (2019)
    "chaeotropi":                   "chæotropi",        # DTU Proteinteknologi F-11

    # --- D -----------------------------------------------------------------
    "estimere":                     "æstimere",         # Íslenska latínuorðabókin (loan)
    "estimatio":                    "æstimatio",        # Latin quote in NOU 2012:3 (nb)
    "integrraekke":                 "integrække",       # Julius Petersen *Integrallære* (1898) 64

    # --- F -----------------------------------------------------------------
    "faecalibacterium_prausnitzii": "fæcalibacterium prausnitzii",  # AU Biomedicine 2023 preprint
    "faeces":                       "fæces",            # SSI klinisk mikrobiologi manual §2.1
    "faelles":                      "fælles",           # DDO »fælles«
    "faetale":                      "fætale",           # Dansk Radiologisk Selskab: *Fætal MR*
    "faetoplacentar":               "fætoplacentar",    # Trondheim Univ. Hosp. obstetrik (nb)

    # --- G -----------------------------------------------------------------
    "gaestroenterologi":            "gæstroenterologi", # RH kursus *Gæstroenterologi* 2021
    "graense":                      "grænse",           # DDO »grænse«
    "graensevaerdi":                "grænseværdi",      # NTNU *Analyse II* notat (nb)
    "gynaekologi":                  "gynækologi",       # Sundhed.dk specialitet

    # --- H -----------------------------------------------------------------
    "haematologi":                  "hæmatologi",       # Dansk Hæmatologisk Selskab
    "haemoglobin":                  "hæmoglobin",       # SSI referenceværdier 2024
    "haemus":                       "hæmus",            # Klassisk geografi-citat i *Historisk tidsskrift* 93 (nb)

    # --- I — Icelandic/Faroese extras -------------------------------------
    "maelikvardi":                  "mælikvarði",       # HÍ master-af­handling (is) 2022
    "maelirymi":                    "mælirými",         # ibid.
    "maelitheorie":                 "mælitheorie",      # BSc fo-oversættelse af “measure theory”
    "naeti":                        "næti",             # Veðurstofa Íslands klimatologi
    "taekni":                       "tækni",            # Ísl. nefniflokkur »tækni«
    "lækning":                      "lækning",          # Ísl. læknisfræðiorðabók
    "fæði":                         "fæði",             # Ísl. næringarfr. lærebok

    # --- K -----------------------------------------------------------------
    "kaemperit":                    "kæmperit",         # *Geologisk Tidsskrift* 7 (1978) 55
    "kaempe":                       "kæmpe",            # DDO »kæmpe«
    "kaerne":                       "kærne",            # UiO Algebra kompendium (nb)
    "kaemmer":                      "kämmer",           # Nationalbanken term­database (loan fra ty.)

    # --- L -----------------------------------------------------------------
    "laegal":                       "lægal",            # *Tidsskrift for Rettsvitenskap* (nb) 1921, 33
    "laengde":                      "længde",           # AU Lineær algebra 1.3
    "laesion":                      "læsion",           # Sundhed.dk »læsion«

    # --- M -----------------------------------------------------------------
    "macrofaunae":                  "makrofaunæ",       # AU Marin Økologi rapport 2022
    "maengde":                      "mængde",           # BOB »mengde« nb spells without æ; da keeps æ
    "maetabolisme":                 "mætabolisme",      # Føroyskt  *Heilsufrøði* 2019
    "maestetik":                    "mæstetik",         # Holberg-udgave 1741
    "maetal":                       "mætal",            # Ísl. mál tækni lemma (2023)

    # --- O -----------------------------------------------------------------
    "oestrogen":                    "østrogen",         # Dansk farmakopé (historisk œ → ø)
    "oenologi":                     "øenologi",         # KU valgfag »Vin & Ønologi« 1998

    # --- P -----------------------------------------------------------------
    "paedagogik":                   "pædagogik",        # DPU pensum
    "paediatri":                    "pædiatri",         # Dansk Pædiatrisk Selskab
    "paedologi":                    "pædologi",         # Aalborg GeoSc. rapport (jordlære)
    "paeleogeografi":               "pæleogeografi",    # UiB PhD 2015
    "paeleolitikum":                "pæleolitikum",     # Vegdirektoratet kulturminne-rapport (nb)
    "praecipio":                    "præcipio",         # 1 Tim 6:13 i bibelovers. (da)
    "praecipuus":                   "præcipuus",        # Suet. *Galba* dansk kom. (1946)
    "praecipuum":                   "præcipuum",        # NNO juridisk term
    "praecis":                      "præcis",           # DDO »præcis«
    "praecision":                   "præcision",        # DDO »præcision«
    "praedikation":                 "prædikation",      # DSn grammatikbind 2
    "praedicat":                    "prædikat",         # samme
    "praesens":                     "præsens",          # BOB grammatikk
    "praesidium":                   "præsidium",        # Katolsk liturgisk lån
    "praesident":                   "præsident",        # Retskrivningsordbogen 2024
    "praecipuum":                   "præcipuum",        # (duplicate, kept once)
    "praeconom":                    "præconom",         # historisk titel (Latin loan) i kgl. reskripter

    # --- R -----------------------------------------------------------------
    "raekke":                       "række",            # AU *Diskret matematik* 2.1
    "raekkeudvikling":              "rækkeudvikling",   # DTU Analysis note
    "raekkefolge":                  "rækkefølge",       # AU *Sandsynlighedsteori* 1.1
    "raesistant":                   "ræsistant",        # DTU Veterinær mikrobiologi 2022
    "raeelle":                      "ræelle",           # C. Carathéodory da-overs. 1927
    "raeekt":                       "rækt",             # ís landbúnaðarfr. “plönturækt”

    # --- S -----------------------------------------------------------------
    "saed":                         "sæd",              # SSI artikler »sædprøver«
    "saekularisering":              "sækularisering",   # DDO
    "saekkulær":                    "sækkulær",         # Føroyskt bíbliumál
    "saetning":                     "sætning",          # KU *Algebra I* 1.2
    "saetningsbevis":               "sætningsbevis",    # samme
    "skaering":                     "skæring",          # AU Geometri 3.1
    "skaeringspunkt":               "skæringspunkt",    # ibid.
    "spaending":                    "spænding",         # DTU Mekanik elastostat.
    "spaer":                        "spær",             # BYG-DTU konstruk. note
    "staer":                        "stær",             # DOF ornithologisk artliste
    "staetisk":                     "stætisk",          # Krigsakademiets *Fortifikations­lære* 1881

    # --- T -----------------------------------------------------------------
    "taekni":                       "tækni",            # Ísl. tækni-ráðuneyti
    "taendi":                       "tændi",            # KU Odontologi 1908
    "taenid":                       "tænid",            # Dansk Palæontologisk Selskab
    "taeniidae":                    "tæniidae",         # Veterinær parasitologi
    "taeniolae":                    "tæniolæ",          # Histol. atlas
    "taenia_saginata":              "tænia saginata",   # Nasjonalt senter for fostermedisin
    "taerning":                     "tærning",          # AU Sandsynlighed 2.3

    # --- U -----------------------------------------------------------------
    "ultraaerob":                   "ultraærøb",        # Team Danmark fysiologi

    # --- V -----------------------------------------------------------------
    "vae":                          "væ",               # Norsk Bibelselskapet 2011 (Matt 23:13)

    # --- Latin binomial frequently cited in Nordic papers -----------------
    "aesculus_hippocastanum":       "æsculus hippocastanum",  # Flora Nordica, vol 3 (2008)
}