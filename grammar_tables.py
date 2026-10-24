"""German grammar reference tables for the German Master Coach app.

render_grammar_tables() shows a toggle per table group; a table appears only
when its toggle is on. All forms are written out (not generated), A2–B2.
"""

from typing import Dict, List

import streamlit as st

PERSONS = ["ich", "du", "er / sie / es", "wir", "ihr", "sie / Sie"]


def _conj(verbs: Dict[str, List[str]]) -> List[Dict[str, str]]:
    """Rows: one per person, one column per verb."""
    return [{"Person": p, **{v: forms[i] for v, forms in verbs.items()}} for i, p in enumerate(PERSONS)]


def _table(rows: List[Dict[str, str]], title: str = "", note: str = "") -> None:
    if title:
        st.markdown(f"**{title}**")
    st.dataframe(rows, hide_index=True, use_container_width=True)
    if note:
        st.caption(note)


# ---------------------------------------------------------------------------
# Pronouns
# ---------------------------------------------------------------------------
def pronouns() -> None:
    _table([
        {"English": "I", "Nominativ": "ich", "Akkusativ": "mich", "Dativ": "mir", "Possessiv": "mein"},
        {"English": "you (informal)", "Nominativ": "du", "Akkusativ": "dich", "Dativ": "dir", "Possessiv": "dein"},
        {"English": "he", "Nominativ": "er", "Akkusativ": "ihn", "Dativ": "ihm", "Possessiv": "sein"},
        {"English": "she", "Nominativ": "sie", "Akkusativ": "sie", "Dativ": "ihr", "Possessiv": "ihr"},
        {"English": "it", "Nominativ": "es", "Akkusativ": "es", "Dativ": "ihm", "Possessiv": "sein"},
        {"English": "we", "Nominativ": "wir", "Akkusativ": "uns", "Dativ": "uns", "Possessiv": "unser"},
        {"English": "you all (informal)", "Nominativ": "ihr", "Akkusativ": "euch", "Dativ": "euch", "Possessiv": "euer"},
        {"English": "they", "Nominativ": "sie", "Akkusativ": "sie", "Dativ": "ihnen", "Possessiv": "ihr"},
        {"English": "you (formal)", "Nominativ": "Sie", "Akkusativ": "Sie", "Dativ": "Ihnen", "Possessiv": "Ihr"},
    ], "Personal pronouns",
        "Akkusativ = direct object (Ich sehe dich). Dativ = indirect object / after Dativ verbs and prepositions "
        "(Ich helfe dir. Ich gebe dir das Buch). Formal Sie / Ihnen / Ihr always with a capital letter.")
    _table([
        {"Person": "ich", "Akkusativ": "mich", "Dativ": "mir", "Example": "Ich wasche mich. · Ich wasche mir die Hände."},
        {"Person": "du", "Akkusativ": "dich", "Dativ": "dir", "Example": "Freust du dich? · Kaufst du dir ein Eis?"},
        {"Person": "er / sie / es", "Akkusativ": "sich", "Dativ": "sich", "Example": "Er setzt sich. · Sie putzt sich die Zähne."},
        {"Person": "wir", "Akkusativ": "uns", "Dativ": "uns", "Example": "Wir treffen uns um acht."},
        {"Person": "ihr", "Akkusativ": "euch", "Dativ": "euch", "Example": "Beeilt euch!"},
        {"Person": "sie / Sie", "Akkusativ": "sich", "Dativ": "sich", "Example": "Setzen Sie sich bitte."},
    ], "Reflexive pronouns",
        "Dativ form when the sentence already has an Akkusativ object: Ich wasche mir (Dat) die Hände (Akk).")
    _table([
        {"Rule": "Noun + noun", "Order": "Dativ before Akkusativ", "Example": "Ich gebe dem Kind (Dat) den Ball (Akk)."},
        {"Rule": "Pronoun + noun", "Order": "Pronoun first", "Example": "Ich gebe ihm den Ball. · Ich gebe ihn dem Kind."},
        {"Rule": "Pronoun + pronoun", "Order": "Akkusativ before Dativ", "Example": "Ich gebe ihn (Akk) ihm (Dat)."},
    ], "Order of Dativ and Akkusativ objects")


# ---------------------------------------------------------------------------
# Articles & possessives
# ---------------------------------------------------------------------------
def articles() -> None:
    _table([
        {"Case": "Nominativ", "maskulin": "der", "feminin": "die", "neutral": "das", "Plural": "die"},
        {"Case": "Akkusativ", "maskulin": "den", "feminin": "die", "neutral": "das", "Plural": "die"},
        {"Case": "Dativ", "maskulin": "dem", "feminin": "der", "neutral": "dem", "Plural": "den (+n)"},
        {"Case": "Genitiv", "maskulin": "des (+s)", "feminin": "der", "neutral": "des (+s)", "Plural": "der"},
    ], "Definite article: der / die / das",
        "Only the maskulin article changes in Akkusativ (der → den). Dativ Plural: the noun gets -n (den Kindern), "
        "unless it already ends in -n or -s.")
    _table([
        {"Case": "Nominativ", "maskulin": "ein", "feminin": "eine", "neutral": "ein", "Plural": "keine"},
        {"Case": "Akkusativ", "maskulin": "einen", "feminin": "eine", "neutral": "ein", "Plural": "keine"},
        {"Case": "Dativ", "maskulin": "einem", "feminin": "einer", "neutral": "einem", "Plural": "keinen (+n)"},
        {"Case": "Genitiv", "maskulin": "eines (+s)", "feminin": "einer", "neutral": "eines (+s)", "Plural": "keiner"},
    ], "Indefinite article: ein / eine (and kein)",
        "ein has no plural. kein takes exactly the same endings: kein, keine, keinen, keinem, keiner …")
    _table([
        {"Case": "Nominativ", "maskulin": "mein", "feminin": "meine", "neutral": "mein", "Plural": "meine"},
        {"Case": "Akkusativ", "maskulin": "meinen", "feminin": "meine", "neutral": "mein", "Plural": "meine"},
        {"Case": "Dativ", "maskulin": "meinem", "feminin": "meiner", "neutral": "meinem", "Plural": "meinen (+n)"},
        {"Case": "Genitiv", "maskulin": "meines (+s)", "feminin": "meiner", "neutral": "meines (+s)", "Plural": "meiner"},
    ], "Possessive articles: mein (same endings as ein / kein)",
        "dein, sein, ihr, unser, Ihr work exactly like mein: seinen Bruder, ihrer Mutter, unserem Haus. "
        "euer drops the e when it gets an ending: eure, euren, eurem.")
    _table([
        {"Owner": "ich", "Possessive": "mein", "Example": "mein Bruder, meine Schwester, mein Auto, meine Eltern"},
        {"Owner": "du", "Possessive": "dein", "Example": "dein Bruder, deine Schwester"},
        {"Owner": "er / es", "Possessive": "sein", "Example": "sein Bruder, seine Schwester"},
        {"Owner": "sie (she)", "Possessive": "ihr", "Example": "ihr Bruder, ihre Schwester"},
        {"Owner": "wir", "Possessive": "unser", "Example": "unser Bruder, unsere Schwester"},
        {"Owner": "ihr", "Possessive": "euer", "Example": "euer Bruder, eure Schwester"},
        {"Owner": "sie (they)", "Possessive": "ihr", "Example": "ihr Bruder, ihre Schwester"},
        {"Owner": "Sie (formal)", "Possessive": "Ihr", "Example": "Ihr Bruder, Ihre Schwester"},
    ], "Which possessive? (the owner decides the word, the noun decides the ending)")
    _table([
        {"Case": "Nominativ", "maskulin": "dieser", "feminin": "diese", "neutral": "dieses", "Plural": "diese"},
        {"Case": "Akkusativ", "maskulin": "diesen", "feminin": "diese", "neutral": "dieses", "Plural": "diese"},
        {"Case": "Dativ", "maskulin": "diesem", "feminin": "dieser", "neutral": "diesem", "Plural": "diesen (+n)"},
        {"Case": "Genitiv", "maskulin": "dieses (+s)", "feminin": "dieser", "neutral": "dieses (+s)", "Plural": "dieser"},
    ], "dieser / jeder / welcher (like der)",
        "jeder (every) and welcher (which) take the same endings: jeden Tag, in welcher Stadt?")


# ---------------------------------------------------------------------------
# Verbs
# ---------------------------------------------------------------------------
def modal_verbs() -> None:
    _table(_conj({
        "können": ["kann", "kannst", "kann", "können", "könnt", "können"],
        "müssen": ["muss", "musst", "muss", "müssen", "müsst", "müssen"],
        "dürfen": ["darf", "darfst", "darf", "dürfen", "dürft", "dürfen"],
        "sollen": ["soll", "sollst", "soll", "sollen", "sollt", "sollen"],
        "wollen": ["will", "willst", "will", "wollen", "wollt", "wollen"],
        "mögen": ["mag", "magst", "mag", "mögen", "mögt", "mögen"],
        "möchten": ["möchte", "möchtest", "möchte", "möchten", "möchtet", "möchten"],
    }), "Modal verbs: Präsens",
        "ich and er/sie/es have the same form and no ending (ich kann, er kann). "
        "The other verb goes to the END as an infinitive: Ich muss heute arbeiten.")
    _table(_conj({
        "können": ["konnte", "konntest", "konnte", "konnten", "konntet", "konnten"],
        "müssen": ["musste", "musstest", "musste", "mussten", "musstet", "mussten"],
        "dürfen": ["durfte", "durftest", "durfte", "durften", "durftet", "durften"],
        "sollen": ["sollte", "solltest", "sollte", "sollten", "solltet", "sollten"],
        "wollen": ["wollte", "wolltest", "wollte", "wollten", "wolltet", "wollten"],
        "mögen": ["mochte", "mochtest", "mochte", "mochten", "mochtet", "mochten"],
    }), "Modal verbs: Präteritum (past, used instead of Perfekt)",
        "No umlaut in the Präteritum: können → konnte. möchten has no past form; use wollte (Ich wollte …).")
    _table(_conj({
        "können": ["könnte", "könntest", "könnte", "könnten", "könntet", "könnten"],
        "müssen": ["müsste", "müsstest", "müsste", "müssten", "müsstet", "müssten"],
        "dürfen": ["dürfte", "dürftest", "dürfte", "dürften", "dürftet", "dürften"],
        "sollen": ["sollte", "solltest", "sollte", "sollten", "solltet", "sollten"],
        "wollen": ["wollte", "wolltest", "wollte", "wollten", "wolltet", "wollten"],
        "mögen": ["möchte", "möchtest", "möchte", "möchten", "möchtet", "möchten"],
    }), "Modal verbs: Konjunktiv II (polite / hypothetical)",
        "Könnten Sie mir helfen? (polite) · Du solltest mehr schlafen. (advice) · "
        "Perfekt with a modal uses two infinitives: Ich habe arbeiten müssen.")


def sein_haben_werden() -> None:
    _table(_conj({
        "sein": ["bin", "bist", "ist", "sind", "seid", "sind"],
        "haben": ["habe", "hast", "hat", "haben", "habt", "haben"],
        "werden": ["werde", "wirst", "wird", "werden", "werdet", "werden"],
        "wissen": ["weiß", "weißt", "weiß", "wissen", "wisst", "wissen"],
    }), "Präsens")
    _table(_conj({
        "sein": ["war", "warst", "war", "waren", "wart", "waren"],
        "haben": ["hatte", "hattest", "hatte", "hatten", "hattet", "hatten"],
        "werden": ["wurde", "wurdest", "wurde", "wurden", "wurdet", "wurden"],
        "wissen": ["wusste", "wusstest", "wusste", "wussten", "wusstet", "wussten"],
    }), "Präteritum",
        "sein and haben are usually used in the Präteritum when speaking about the past: Ich war krank. Ich hatte keine Zeit.")
    _table(_conj({
        "sein": ["wäre", "wärst", "wäre", "wären", "wärt", "wären"],
        "haben": ["hätte", "hättest", "hätte", "hätten", "hättet", "hätten"],
        "werden": ["würde", "würdest", "würde", "würden", "würdet", "würden"],
        "wissen": ["wüsste", "wüsstest", "wüsste", "wüssten", "wüsstet", "wüssten"],
    }), "Konjunktiv II",
        "Ich hätte gern einen Kaffee. · Wenn ich reich wäre, … · Das würde ich nicht machen. · Wenn ich das wüsste!")


def konjunktiv_2() -> None:
    _table(_conj({
        "würde + Infinitiv": ["würde machen", "würdest machen", "würde machen",
                              "würden machen", "würdet machen", "würden machen"],
        "haben → hätte": ["hätte", "hättest", "hätte", "hätten", "hättet", "hätten"],
        "sein → wäre": ["wäre", "wärst", "wäre", "wären", "wärt", "wären"],
        "können → könnte": ["könnte", "könntest", "könnte", "könnten", "könntet", "könnten"],
    }), "Konjunktiv II: Gegenwart (present)",
        "For most verbs use würde + infinitive. Use the own forms for sein, haben, the modal verbs and wissen.")
    _table([
        {"Infinitiv": "gehen", "Konjunktiv II": "ginge", "with würde": "würde gehen"},
        {"Infinitiv": "kommen", "Konjunktiv II": "käme", "with würde": "würde kommen"},
        {"Infinitiv": "geben", "Konjunktiv II": "gäbe", "with würde": "würde geben"},
        {"Infinitiv": "finden", "Konjunktiv II": "fände", "with würde": "würde finden"},
        {"Infinitiv": "wissen", "Konjunktiv II": "wüsste", "with würde": "(rare)"},
        {"Infinitiv": "brauchen", "Konjunktiv II": "bräuchte", "with würde": "würde brauchen"},
        {"Infinitiv": "lassen", "Konjunktiv II": "ließe", "with würde": "würde lassen"},
    ], "Other common Konjunktiv II forms (more formal / written)")
    _table([
        {"Use": "Polite request", "Example": "Könnten Sie mir bitte helfen? · Ich hätte gern ein Wasser."},
        {"Use": "Wish", "Example": "Ich wäre gern am Meer. · Wenn ich doch mehr Zeit hätte!"},
        {"Use": "Advice", "Example": "Du solltest zum Arzt gehen. · An deiner Stelle würde ich …"},
        {"Use": "Unreal condition", "Example": "Wenn ich Zeit hätte, würde ich mehr lesen."},
        {"Use": "Unreal comparison", "Example": "Er tut so, als ob er alles wüsste."},
    ], "When to use Konjunktiv II")
    _table([
        {"Form": "hätte + Partizip II", "Example": "Ich hätte dich angerufen. (I would have called you.)"},
        {"Form": "wäre + Partizip II", "Example": "Wir wären früher gekommen. (We would have come earlier.)"},
        {"Form": "hätte + 2 infinitives (modal)", "Example": "Ich hätte das machen können. (I could have done that.)"},
        {"Form": "Unreal past condition", "Example": "Wenn ich Zeit gehabt hätte, wäre ich gekommen."},
    ], "Konjunktiv II: Vergangenheit (past)",
        "Same choice of hätte or wäre as haben or sein in the Perfekt.")


def present_tense() -> None:
    _table(_conj({
        "machen (regular)": ["mache", "machst", "macht", "machen", "macht", "machen"],
        "arbeiten (+e)": ["arbeite", "arbeitest", "arbeitet", "arbeiten", "arbeitet", "arbeiten"],
        "heißen (s/ß)": ["heiße", "heißt", "heißt", "heißen", "heißt", "heißen"],
        "sammeln (-eln)": ["sammle", "sammelst", "sammelt", "sammeln", "sammelt", "sammeln"],
    }), "Präsens: regular endings  (-e, -st, -t, -en, -t, -en)",
        "Stems ending in -t / -d get an extra e: du arbeitest, er findet. Stems ending in s/ß/z only add -t for du: du heißt.")
    _table(_conj({
        "fahren a→ä": ["fahre", "fährst", "fährt", "fahren", "fahrt", "fahren"],
        "schlafen a→ä": ["schlafe", "schläfst", "schläft", "schlafen", "schlaft", "schlafen"],
        "laufen au→äu": ["laufe", "läufst", "läuft", "laufen", "lauft", "laufen"],
        "sprechen e→i": ["spreche", "sprichst", "spricht", "sprechen", "sprecht", "sprechen"],
        "nehmen e→i": ["nehme", "nimmst", "nimmt", "nehmen", "nehmt", "nehmen"],
        "lesen e→ie": ["lese", "liest", "liest", "lesen", "lest", "lesen"],
        "sehen e→ie": ["sehe", "siehst", "sieht", "sehen", "seht", "sehen"],
    }), "Präsens: stem-changing verbs (only du and er/sie/es change)")
    _table([
        {"Change": "a → ä", "Verbs": "fahren, schlafen, tragen, waschen, fallen, halten, lassen, einladen"},
        {"Change": "au → äu", "Verbs": "laufen"},
        {"Change": "e → i", "Verbs": "sprechen, helfen, geben, nehmen, essen (du isst), treffen, vergessen, werfen, sterben"},
        {"Change": "e → ie", "Verbs": "lesen, sehen, empfehlen, stehlen"},
    ], "More stem-changing verbs")
    _table([
        {"Verb": "anrufen", "Präsens": "Ich rufe dich morgen an.", "Perfekt": "Ich habe dich angerufen.", "Modal": "Ich will dich anrufen."},
        {"Verb": "einkaufen", "Präsens": "Wir kaufen am Samstag ein.", "Perfekt": "Wir haben eingekauft.", "Modal": "Wir müssen einkaufen."},
        {"Verb": "aufstehen", "Präsens": "Er steht um 7 Uhr auf.", "Perfekt": "Er ist um 7 Uhr aufgestanden.", "Modal": "Er muss früh aufstehen."},
        {"Verb": "mitkommen", "Präsens": "Kommst du mit?", "Perfekt": "Bist du mitgekommen?", "Modal": "Kannst du mitkommen?"},
    ], "Separable verbs (prefix goes to the end)",
        "Separable prefixes: an-, auf-, aus-, ein-, mit-, vor-, zu-, ab-, zurück-, fern- … "
        "Not separable: be-, ver-, er-, ent-, ge-, zer-, emp-, miss- (bezahlen, verstehen).")


def past_tenses() -> None:
    _table([
        {"Tense": "Präsens", "machen": "ich mache", "gehen": "ich gehe"},
        {"Tense": "Präteritum", "machen": "ich machte", "gehen": "ich ging"},
        {"Tense": "Perfekt", "machen": "ich habe gemacht", "gehen": "ich bin gegangen"},
        {"Tense": "Plusquamperfekt", "machen": "ich hatte gemacht", "gehen": "ich war gegangen"},
        {"Tense": "Futur I", "machen": "ich werde machen", "gehen": "ich werde gehen"},
        {"Tense": "Futur II", "machen": "ich werde gemacht haben", "gehen": "ich werde gegangen sein"},
        {"Tense": "Konjunktiv II", "machen": "ich würde machen", "gehen": "ich würde gehen / ginge"},
        {"Tense": "Konjunktiv II Vergangenheit", "machen": "ich hätte gemacht", "gehen": "ich wäre gegangen"},
    ], "All tenses at a glance")
    _table([
        {"Rule": "sein", "When": "Movement from A to B, change of state, and sein / bleiben / werden / passieren",
         "Examples": "gehen, fahren, fliegen, kommen, laufen, aufstehen, einschlafen, umziehen, sterben"},
        {"Rule": "haben", "When": "Everything else (most verbs, all reflexive verbs, verbs with an Akkusativ object)",
         "Examples": "machen, essen, arbeiten, schlafen, sich waschen, lesen, kaufen"},
    ], "Perfekt: haben or sein?")
    _table([
        {"Infinitiv": i, "Perfekt": p, "Präteritum": pr}
        for i, p, pr in [
            ("gehen", "ist gegangen", "ging"), ("fahren", "ist gefahren", "fuhr"),
            ("kommen", "ist gekommen", "kam"), ("fliegen", "ist geflogen", "flog"),
            ("laufen", "ist gelaufen", "lief"), ("bleiben", "ist geblieben", "blieb"),
            ("sein", "ist gewesen", "war"), ("werden", "ist geworden", "wurde"),
            ("aufstehen", "ist aufgestanden", "stand auf"), ("einschlafen", "ist eingeschlafen", "schlief ein"),
            ("passieren", "ist passiert", "passierte"), ("umziehen", "ist umgezogen", "zog um"),
            ("haben", "hat gehabt", "hatte"), ("machen", "hat gemacht", "machte"),
            ("arbeiten", "hat gearbeitet", "arbeitete"), ("kaufen", "hat gekauft", "kaufte"),
            ("essen", "hat gegessen", "aß"), ("trinken", "hat getrunken", "trank"),
            ("sehen", "hat gesehen", "sah"), ("lesen", "hat gelesen", "las"),
            ("schreiben", "hat geschrieben", "schrieb"), ("sprechen", "hat gesprochen", "sprach"),
            ("nehmen", "hat genommen", "nahm"), ("geben", "hat gegeben", "gab"),
            ("finden", "hat gefunden", "fand"), ("helfen", "hat geholfen", "half"),
            ("treffen", "hat getroffen", "traf"), ("schlafen", "hat geschlafen", "schlief"),
            ("vergessen", "hat vergessen", "vergaß"), ("denken", "hat gedacht", "dachte"),
            ("bringen", "hat gebracht", "brachte"), ("wissen", "hat gewusst", "wusste"),
            ("verstehen", "hat verstanden", "verstand"), ("anrufen", "hat angerufen", "rief an"),
            ("einkaufen", "hat eingekauft", "kaufte ein"), ("bezahlen", "hat bezahlt", "bezahlte"),
            ("besuchen", "hat besucht", "besuchte"), ("studieren", "hat studiert", "studierte"),
        ]
    ], "Common verbs: Perfekt and Präteritum")
    _table(_conj({
        "machen (regular)": ["machte", "machtest", "machte", "machten", "machtet", "machten"],
        "gehen (irregular)": ["ging", "gingst", "ging", "gingen", "gingt", "gingen"],
        "kommen (irregular)": ["kam", "kamst", "kam", "kamen", "kamt", "kamen"],
    }), "Präteritum endings",
        "Regular: -te, -test, -te, -ten, -tet, -ten. Irregular: new stem, no ending for ich and er/sie/es.")
    _table([
        {"Verb type": "regular", "Rule": "ge- + stem + -t", "Examples": "machen → gemacht, kaufen → gekauft"},
        {"Verb type": "irregular", "Rule": "ge- + (changed) stem + -en", "Examples": "sehen → gesehen, finden → gefunden"},
        {"Verb type": "separable", "Rule": "prefix + ge + …", "Examples": "einkaufen → eingekauft, anrufen → angerufen"},
        {"Verb type": "be-/ver-/er-/ent- …", "Rule": "no ge-", "Examples": "bezahlen → bezahlt, verstehen → verstanden"},
        {"Verb type": "-ieren", "Rule": "no ge-, ends in -t", "Examples": "studieren → studiert, telefonieren → telefoniert"},
    ], "How to build the Partizip II")


def prepositions() -> None:
    _table([
        {"Case": "Akkusativ", "Prepositions": "durch, für, gegen, ohne, um, bis, entlang",
         "Example": "Das ist für meinen Vater. · Wir gehen durch den Park."},
        {"Case": "Dativ", "Prepositions": "aus, bei, mit, nach, seit, von, zu, gegenüber, außer, ab",
         "Example": "Ich fahre mit dem Bus zur Arbeit. · Seit einem Jahr wohne ich hier."},
        {"Case": "Wechsel (Akk or Dat)", "Prepositions": "an, auf, hinter, in, neben, über, unter, vor, zwischen",
         "Example": "Wohin? Ich gehe in den Park (Akk). · Wo? Ich bin im Park (Dat)."},
        {"Case": "Genitiv", "Prepositions": "wegen, trotz, während, statt, innerhalb, außerhalb",
         "Example": "Wegen des Regens bleiben wir zu Hause."},
    ], "Prepositions and their case")
    _table([
        {"Question": "Wohin? (movement, direction)", "Case": "Akkusativ", "Verbs": "legen, stellen, setzen, hängen (+Akk)", "Example": "Ich stelle die Flasche auf den Tisch."},
        {"Question": "Wo? (position, no movement)", "Case": "Dativ", "Verbs": "liegen, stehen, sitzen, hängen", "Example": "Die Flasche steht auf dem Tisch."},
    ], "Wechselpräpositionen: wo? or wohin?")
    _table([
        {"Long": "an dem", "Short": "am"}, {"Long": "in dem", "Short": "im"},
        {"Long": "an das", "Short": "ans"}, {"Long": "in das", "Short": "ins"},
        {"Long": "bei dem", "Short": "beim"}, {"Long": "von dem", "Short": "vom"},
        {"Long": "zu dem", "Short": "zum"}, {"Long": "zu der", "Short": "zur"},
    ], "Contractions")
    _table([
        {"Where to?": "zu + person / place", "Example": "zum Arzt, zur Arbeit, zu meiner Freundin"},
        {"Where to?": "nach + city / country / home", "Example": "nach Berlin, nach Deutschland, nach Hause"},
        {"Where to?": "in + country with article / building", "Example": "in die Türkei, in die Schweiz, ins Kino"},
        {"Where?": "bei + person / company", "Example": "beim Arzt, bei meinen Eltern, bei Siemens"},
        {"Where?": "in + place", "Example": "in Berlin, im Supermarkt, zu Hause (at home)"},
        {"From where?": "aus + city / country / building", "Example": "aus Pakistan, aus dem Haus"},
        {"From where?": "von + person / place", "Example": "vom Arzt, von der Arbeit"},
    ], "Places: zu, nach, in, bei, aus, von")
    _table([
        {"Time": "am", "For": "days, parts of the day, dates", "Example": "am Montag, am Abend, am 3. Mai"},
        {"Time": "im", "For": "months, seasons", "Example": "im Mai, im Sommer"},
        {"Time": "um", "For": "clock time", "Example": "um 8 Uhr"},
        {"Time": "seit + Dat", "For": "since / for (still going)", "Example": "seit zwei Jahren"},
        {"Time": "vor + Dat", "For": "ago / before", "Example": "vor einer Woche, vor dem Essen"},
        {"Time": "in + Dat", "For": "in (the future)", "Example": "in zwei Tagen"},
        {"Time": "von … bis", "For": "from … until", "Example": "von 9 bis 17 Uhr"},
    ], "Time expressions")


def adjective_endings() -> None:
    _table([
        {"Case": "Nominativ", "maskulin": "der gute Mann", "feminin": "die gute Frau", "neutral": "das gute Kind", "Plural": "die guten Kinder"},
        {"Case": "Akkusativ", "maskulin": "den guten Mann", "feminin": "die gute Frau", "neutral": "das gute Kind", "Plural": "die guten Kinder"},
        {"Case": "Dativ", "maskulin": "dem guten Mann", "feminin": "der guten Frau", "neutral": "dem guten Kind", "Plural": "den guten Kindern"},
        {"Case": "Genitiv", "maskulin": "des guten Mannes", "feminin": "der guten Frau", "neutral": "des guten Kindes", "Plural": "der guten Kinder"},
    ], "After der / die / das (and dieser, jeder, welcher)",
        "Only -e or -en. -e in the 5 'singular Nominativ + feminin/neutral Akkusativ' forms, -en everywhere else.")
    _table([
        {"Case": "Nominativ", "maskulin": "ein guter Mann", "feminin": "eine gute Frau", "neutral": "ein gutes Kind", "Plural": "keine guten Kinder"},
        {"Case": "Akkusativ", "maskulin": "einen guten Mann", "feminin": "eine gute Frau", "neutral": "ein gutes Kind", "Plural": "keine guten Kinder"},
        {"Case": "Dativ", "maskulin": "einem guten Mann", "feminin": "einer guten Frau", "neutral": "einem guten Kind", "Plural": "keinen guten Kindern"},
        {"Case": "Genitiv", "maskulin": "eines guten Mannes", "feminin": "einer guten Frau", "neutral": "eines guten Kindes", "Plural": "keiner guten Kinder"},
    ], "After ein / kein / mein / dein …",
        "Where ein has no ending (ein Mann, ein Kind), the adjective shows the gender: guter (m), gutes (n).")
    _table([
        {"Case": "Nominativ", "maskulin": "guter Wein", "feminin": "gute Milch", "neutral": "gutes Brot", "Plural": "gute Leute"},
        {"Case": "Akkusativ", "maskulin": "guten Wein", "feminin": "gute Milch", "neutral": "gutes Brot", "Plural": "gute Leute"},
        {"Case": "Dativ", "maskulin": "gutem Wein", "feminin": "guter Milch", "neutral": "gutem Brot", "Plural": "guten Leuten"},
        {"Case": "Genitiv", "maskulin": "guten Weines", "feminin": "guter Milch", "neutral": "guten Brotes", "Plural": "guter Leute"},
    ], "Without an article",
        "The adjective takes the ending of the definite article (dem → gutem, der → guter), except Genitiv maskulin/neutral: -en.")


def comparison() -> None:
    _table([
        {"Positiv": p, "Komparativ": k, "Superlativ": s}
        for p, k, s in [
            ("klein", "kleiner", "am kleinsten"), ("schnell", "schneller", "am schnellsten"),
            ("alt", "älter", "am ältesten"), ("jung", "jünger", "am jüngsten"),
            ("groß", "größer", "am größten"), ("lang", "länger", "am längsten"),
            ("warm", "wärmer", "am wärmsten"), ("kalt", "kälter", "am kältesten"),
            ("teuer", "teurer", "am teuersten"), ("dunkel", "dunkler", "am dunkelsten"),
            ("gut", "besser", "am besten"), ("viel", "mehr", "am meisten"),
            ("gern", "lieber", "am liebsten"), ("hoch", "höher", "am höchsten"),
            ("nah", "näher", "am nächsten"),
        ]
    ], "Komparativ and Superlativ",
        "Paul ist so groß wie Max (equal). · Paul ist größer als Max (more). · Paul ist am größten. · der größte Mann.")


def word_order() -> None:
    _table([
        {"Type": "Position 0 (no change)", "Words": "und, aber, oder, denn, sondern",
         "Verb": "normal position 2", "Example": "Ich bleibe zu Hause, denn ich bin krank."},
        {"Type": "Adverb (takes position 1)", "Words": "deshalb, deswegen, trotzdem, dann, danach, außerdem, sonst, also",
         "Verb": "directly after it", "Example": "Ich bin krank, deshalb bleibe ich zu Hause."},
        {"Type": "Subordinate clause", "Words": "weil, dass, wenn, ob, als, obwohl, damit, bevor, nachdem, während, bis, seit, sodass, falls",
         "Verb": "at the END", "Example": "Ich bleibe zu Hause, weil ich krank bin."},
        {"Type": "W-question as clause", "Words": "wann, wo, warum, wie, was …",
         "Verb": "at the END", "Example": "Weißt du, wann der Zug kommt?"},
    ], "Conjunctions and verb position",
        "Subordinate clause first → the main clause starts with the verb: Weil ich krank bin, bleibe ich zu Hause.")
    _table([
        {"Pair": "entweder … oder", "Meaning": "either … or", "Example": "Entweder wir gehen ins Kino oder wir bleiben hier."},
        {"Pair": "weder … noch", "Meaning": "neither … nor", "Example": "Er spricht weder Englisch noch Französisch."},
        {"Pair": "sowohl … als auch", "Meaning": "both … and", "Example": "Sie spricht sowohl Deutsch als auch Urdu."},
        {"Pair": "nicht nur … sondern auch", "Meaning": "not only … but also", "Example": "Das ist nicht nur billig, sondern auch gut."},
        {"Pair": "zwar … aber", "Meaning": "admittedly … but", "Example": "Das Hotel war zwar teuer, aber schön."},
        {"Pair": "je … desto", "Meaning": "the more … the more", "Example": "Je mehr ich übe, desto besser spreche ich."},
    ], "Two-part conjunctions")
    _table([
        {"Position": "1", "Part": "anything (subject, time, object …)", "Example": "Morgen"},
        {"Position": "2", "Part": "conjugated verb", "Example": "fahre"},
        {"Position": "3", "Part": "subject (if not in position 1)", "Example": "ich"},
        {"Position": "middle", "Part": "Te-Ka-Mo-Lo: time, cause, manner, place", "Example": "mit dem Zug nach Berlin"},
        {"Position": "end", "Part": "2nd verb part (infinitive, Partizip II, prefix)", "Example": "(… ab / … gefahren / … fahren)"},
    ], "Main clause: verb in position 2",
        "Morgen fahre ich wegen der Arbeit mit dem Zug nach Berlin. "
        "(time → cause → manner → place)")


def relative_pronouns() -> None:
    _table([
        {"Case": "Nominativ", "maskulin": "der", "feminin": "die", "neutral": "das", "Plural": "die"},
        {"Case": "Akkusativ", "maskulin": "den", "feminin": "die", "neutral": "das", "Plural": "die"},
        {"Case": "Dativ", "maskulin": "dem", "feminin": "der", "neutral": "dem", "Plural": "denen"},
        {"Case": "Genitiv", "maskulin": "dessen", "feminin": "deren", "neutral": "dessen", "Plural": "deren"},
    ], "Relative pronouns",
        "Gender and number from the noun, case from the relative clause. Verb at the end: "
        "Das ist der Mann, den ich kenne. · …, dem ich helfe. · …, dessen Auto rot ist. · Die Kinder, mit denen ich spiele.")


def passive() -> None:
    _table([
        {"Tense": "Präsens", "Form": "wird + Partizip II", "Example": "Das Haus wird gebaut."},
        {"Tense": "Präteritum", "Form": "wurde + Partizip II", "Example": "Das Haus wurde gebaut."},
        {"Tense": "Perfekt", "Form": "ist + Partizip II + worden", "Example": "Das Haus ist gebaut worden."},
        {"Tense": "Plusquamperfekt", "Form": "war + Partizip II + worden", "Example": "Das Haus war gebaut worden."},
        {"Tense": "Futur I", "Form": "wird + Partizip II + werden", "Example": "Das Haus wird gebaut werden."},
        {"Tense": "with a modal", "Form": "Modal + Partizip II + werden", "Example": "Das Haus muss gebaut werden."},
        {"Tense": "Zustandspassiv (state)", "Form": "ist + Partizip II", "Example": "Die Tür ist geöffnet."},
    ], "Passiv (werden + Partizip II)",
        "Who does it: von + Dativ (Das Haus wurde von einer Firma gebaut). In the passive Perfekt: worden, not geworden.")


def imperative() -> None:
    _table([
        {"Infinitiv": i, "du": d, "ihr": ih, "Sie": s}
        for i, d, ih, s in [
            ("kommen", "Komm!", "Kommt!", "Kommen Sie!"), ("machen", "Mach!", "Macht!", "Machen Sie!"),
            ("warten", "Warte!", "Wartet!", "Warten Sie!"), ("fahren", "Fahr!", "Fahrt!", "Fahren Sie!"),
            ("nehmen", "Nimm!", "Nehmt!", "Nehmen Sie!"), ("geben", "Gib!", "Gebt!", "Geben Sie!"),
            ("lesen", "Lies!", "Lest!", "Lesen Sie!"), ("essen", "Iss!", "Esst!", "Essen Sie!"),
            ("anrufen", "Ruf an!", "Ruft an!", "Rufen Sie an!"), ("sich setzen", "Setz dich!", "Setzt euch!", "Setzen Sie sich!"),
            ("sein", "Sei!", "Seid!", "Seien Sie!"), ("haben", "Hab!", "Habt!", "Haben Sie!"),
        ]
    ], "Imperativ",
        "du-form: drop -st and du (du nimmst → Nimm!). a→ä verbs keep a (Fahr!), e→i verbs keep i (Nimm!). Add bitte to be polite.")


def questions_and_verbs() -> None:
    _table([
        {"Question word": q, "Meaning": m, "Example": e}
        for q, m, e in [
            ("wer", "who (Nom)", "Wer ist das?"), ("wen", "whom (Akk)", "Wen siehst du?"),
            ("wem", "to whom (Dat)", "Wem hilfst du?"), ("wessen", "whose", "Wessen Tasche ist das?"),
            ("was", "what", "Was machst du?"), ("wo", "where", "Wo wohnst du?"),
            ("wohin", "where to", "Wohin fährst du?"), ("woher", "where from", "Woher kommst du?"),
            ("wann", "when", "Wann beginnt der Kurs?"), ("warum / wieso", "why", "Warum lernst du Deutsch?"),
            ("wie", "how", "Wie geht es dir?"), ("wie viel / wie viele", "how much / many", "Wie viele Geschwister hast du?"),
            ("wie lange", "how long", "Wie lange wohnst du schon hier?"),
            ("welcher / welche / welches", "which", "Welches Buch liest du?"),
            ("was für ein", "what kind of", "Was für ein Auto hast du?"),
        ]
    ], "Question words")
    _table([
        {"Verb": v, "Example": e} for v, e in [
            ("helfen", "Ich helfe dir."), ("danken", "Ich danke Ihnen."), ("gefallen", "Die Wohnung gefällt mir."),
            ("gehören", "Das Buch gehört mir."), ("gratulieren", "Wir gratulieren dir!"), ("antworten", "Antworte mir!"),
            ("passen", "Der Termin passt mir."), ("schmecken", "Schmeckt dir das?"), ("fehlen", "Du fehlst mir."),
            ("glauben", "Ich glaube dir."), ("zuhören", "Hör mir zu!"), ("wehtun", "Mir tut der Kopf weh."),
            ("leidtun", "Es tut mir leid."), ("gut gehen", "Mir geht es gut."),
        ]
    ], "Verbs with Dativ",
        "Verbs with Dativ (person) + Akkusativ (thing): geben, schenken, zeigen, erklären, bringen, schicken, "
        "empfehlen, leihen, sagen, schreiben: Ich zeige dir die Stadt.")
    _table([
        {"Verb": v, "Example": e} for v, e in [
            ("warten auf + Akk", "Ich warte auf den Bus."), ("sich freuen auf + Akk", "Ich freue mich auf den Urlaub. (future)"),
            ("sich freuen über + Akk", "Ich freue mich über das Geschenk. (now / past)"),
            ("denken an + Akk", "Ich denke an dich."), ("sich erinnern an + Akk", "Erinnerst du dich an ihn?"),
            ("sich interessieren für + Akk", "Ich interessiere mich für Musik."),
            ("sprechen über + Akk / mit + Dat", "Wir sprechen über das Problem."),
            ("sich kümmern um + Akk", "Sie kümmert sich um die Kinder."), ("bitten um + Akk", "Ich bitte um Hilfe."),
            ("sich bewerben um + Akk", "Ich bewerbe mich um die Stelle."), ("sich ärgern über + Akk", "Er ärgert sich über den Stau."),
            ("Angst haben vor + Dat", "Ich habe Angst vor Hunden."), ("teilnehmen an + Dat", "Ich nehme am Kurs teil."),
            ("träumen von + Dat", "Ich träume von einer Reise."), ("abhängen von + Dat", "Das hängt vom Wetter ab."),
            ("fragen nach + Dat", "Er fragt nach dem Weg."),
        ]
    ], "Verbs with prepositions",
        "Questions and short answers: Worauf wartest du? Darauf. · Auf wen wartest du? (person) Auf meinen Freund.")
    _table([
        {"Nominativ": "der Kollege", "Akkusativ": "den Kollegen", "Dativ": "dem Kollegen", "Genitiv": "des Kollegen"},
        {"Nominativ": "der Student", "Akkusativ": "den Studenten", "Dativ": "dem Studenten", "Genitiv": "des Studenten"},
        {"Nominativ": "der Mensch", "Akkusativ": "den Menschen", "Dativ": "dem Menschen", "Genitiv": "des Menschen"},
        {"Nominativ": "der Herr", "Akkusativ": "den Herrn", "Dativ": "dem Herrn", "Genitiv": "des Herrn"},
        {"Nominativ": "der Name", "Akkusativ": "den Namen", "Dativ": "dem Namen", "Genitiv": "des Namens"},
    ], "n-Deklination (some maskulin nouns)",
        "Also: der Junge, der Kunde, der Nachbar, der Polizist, der Praktikant. Ich frage meinen Kollegen.")


# label -> render function (order = order on the page)
SECTIONS = [
    ("👤 Pronouns (ich, mich, mir, Sie, Ihnen …)", pronouns),
    ("🔤 Articles & possessives (der, ein, kein, mein, sein …)", articles),
    ("🔧 Modal verbs (können, müssen, dürfen …)", modal_verbs),
    ("⭐ sein, haben, werden, wissen", sein_haben_werden),
    ("💭 Konjunktiv II (hätte, wäre, würde, könnte …)", konjunktiv_2),
    ("🟢 Präsens: regular, stem-changing, separable", present_tense),
    ("⏪ Perfekt, Präteritum & all tenses", past_tenses),
    ("📍 Prepositions (Akk, Dat, Wechsel, Genitiv)", prepositions),
    ("🎨 Adjective endings", adjective_endings),
    ("📈 Komparativ & Superlativ", comparison),
    ("🔀 Word order & conjunctions", word_order),
    ("🔗 Relative pronouns", relative_pronouns),
    ("🏗️ Passiv", passive),
    ("❗ Imperativ", imperative),
    ("❓ Question words, Dativ verbs, verbs with prepositions", questions_and_verbs),
]


def render_grammar_tables() -> None:
    st.markdown("## 📖 German grammar tables")
    st.caption("Switch on the tables you want to see.")
    show_all = st.toggle("Show all tables", key="gt_all")
    cols = st.columns(3)
    chosen = []
    for i, (label, fn) in enumerate(SECTIONS):
        with cols[i % 3]:
            if st.toggle(label, key=f"gt_{i}", value=False) or show_all:
                chosen.append((label, fn))
    for label, fn in chosen:
        with st.container(border=True):
            st.markdown(f"### {label}")
            fn()
