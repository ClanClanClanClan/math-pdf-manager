# Proper nouns in titles, measured

## The problem

`core.sentence_case.to_sentence_case_academic` lowercases every capitalised
word it does not recognise. Measured over the 25,043 in-scope titles, that
destroyed **2,964 mid-title capitals**, and they are overwhelmingly proper
nouns:

| kind | examples |
|---|---|
| mathematicians | Bourbaki 64, Fock 22, Landau 15, Azéma 13, Hartree 12, Paley 12, Doeblin 9, Gronwall 8 |
| places | Saint-Flour 60/59, Japan 22, Tōhoku 17, Sendai 17, Paris 14, Polytechnique 10 |
| months | May 42, April 36, August 29, July 25, June 20 |
| given names | Jean 14, Paul 9 |

Not everything in that population should be capitalised. `Gaussiens` and
`Hamiltoniens` are French adjectives and are correctly lowercased.

## Finding 0 — a whitelist entry IMPOSES, it does not preserve

This overturned the obvious design and is worth stating first.
`capitalization_whitelist` matching is **case-insensitive** and the entry's own
spelling is emitted, so an entry *creates* a capital:

```
"A theorem which we may use here"   + entry "May"  ->  "we May use here"
```

Measured on the shipped 848-entry list: it already imposes **263** wrong
capitals on lowercase input, 35 distinct words — `le` → `Le` **103 times**
("sur le grossissement" → "sur Le grossissement", from a bare `Le` entry
presumably meant for Le Cam and Le Gall), `white noise` → `White noise` 22,
`bank` 18, `green` 10, `hold` 8.

Feeding the 11,779 mined surnames into that same mechanism was measured at
**5,823 imposed capitals**. That is why the fix is not a word list.

## The source: the library's own author blocks

`processing/author_vocabulary.py` mines surnames read-only from the author
block of every in-scope filename, via `library_scope` + `filename_ground_truth`.
25,253 files walked, 13 unreliable, 11,779 distinct surname tokens — then a
**census filter** keeps only the ones the library's own titles treat as names,
leaving **11,667**. A new eponym arrives with its first paper rather than with
a hand-edited config entry.

### The census filter

A surname is kept only if the library's titles never use it in lower case
mid-title, or use it capitalised more often than not. Measured:

| kept | | dropped | |
|---|---|---|---|
| hunt | 8 up / 0 low | law | 0 / 240 |
| ray | 16 / 0 | risk | 0 / 778 |
| morse | 6 / 0 | price | 1 / 252 |
| abel | 6 / 0 | case | 1 / 211 |
| may | 42 / 10 | root | 4 / 26 |
| bell | 4 / 1 | | |

Without it, `Gauss's Law in electrostatics` kept its capital L — someone is
called Law. It costs 10 of 1,043 recoveries. `Root` is the notable loss: the
library writes `square root` 26 times against 4 capitalised `Root`s, so its own
usage says the word is a common noun here, and the filter is believed rather
than overridden.

Foreign-language months are swept out by hand, because an English dictionary
cannot find them and `Juillet` is both French for July **and** a real
probabilist's surname. It produced 3 of the 4 errors of an earlier draft.

## The rule

Preserve-only, in the WORD branch, gated on the title's own casing:

* the word is already capitalised, **and**
* it is a known surname, or sits in a `Xxx-Yyy` compound where one component
  is, **and**
* the title does not read as Title Cased.

Preserve-only is a **structural** guarantee, not a measurement to redo: the
rule emits the word verbatim, so it cannot impose a capital, alter a character
or destroy a title.

### The gate

Title Cased input — `A Study Of The Wang Equation In Sun Space` — carries a
capital on every word, and removing them is the caser's whole job. Measured on
an oracle of 4,000 titles the library stores in sentence case, Title-Cased back,
with the stored title as ground truth:

| | exact | wrong capitals |
|---|---|---|
| baseline | 3,763 / 4,000 | 193 |
| the rule, ungated | 3,179 / 4,000 | 997 (+804) |
| **the rule, gated** | **3,763 / 4,000** | **193 (+0)** |

The +804 is the collision made visible: `risk` 205, `de` 147, `law` 60,
`price` 53, `case` 42 — all genuine mined surnames, all ordinary words.

The gate's second clause — *at least two capitals that are not surnames* —
stops a title whose capitals are **all** names ("Euler, Morse, Bourbaki and
Doeblin") from reading as Title Cased. Without it, 29 correct recoveries were
blocked.

## Result, measured over all 25,043 titles

| | |
|---|---|
| capitals **recovered** | **1,033** (454 distinct words, 761 titles) |
| capitals imposed | **0** |
| capitals newly lost | **0** |
| titles destroyed / characters lost | **0** |
| errors raised | **0** |
| half-cased compounds (`Xxx-yyy`) | **113 → 30** |

The compound rule does not merely avoid making the half-cased count worse — it
*fixes* 83 pre-existing ones. Without it the eponym rule alone would have taken
that count from 113 to 97 (`Kolmogorov-petrowsky`, `Hartman-wintner`,
`Pierre-andré`), which reads as a typo in a way an all-lowercase name does not.

## What mutation changed about the design

A mutant that removed the compound walk's lower-case guard scored **better**
than the real code on two of the three real titles it touched: the guard was
breaking at the `de` of `Saint-Jean-de-Monts` and stranding `Monts`. Name
particles (`de`, `van`, `von`, `der`, `la`, `du`, …) are now walked through.
17 of 17 mutants killed.

## Known wrong, measured

**Zero, over the 25,043 in-scope titles.** The single error an earlier draft
carried — `Price` in *"…derivatives - Lecture 2 - Price models (slides)"* —
is removed by the census filter, which drops `price` (1 capitalised against
252 lower).

Audited separately: of the 1,033 recoveries, **0** are French function or
common words, and every recovery of three letters or fewer is a real name
(Ho–Lee, Ky Fan, Li–Yau, Black–Derman–Toy, Eisenberg–Noe, Gan–Gross–Prasad).

## Still open

* **Months and places are not covered.** They are 34% of the remaining loss —
  `June`, `Saint-Flour`'s `Flour`, `Tōhoku`, `Sendai`. A separate lane built and
  measured a 179-entry closed-set vocabulary (+735 occurrences, 3 imposed and
  all three judged correct), but its output files were lost to a scratch clean
  before they could be landed. Rebuilding it is the obvious next step.
* **Classical mathematicians who never authored a paper here** are invisible to
  the mined vocabulary: `Fock`, `Landau`, `Gronwall`, `Hartree`, `Burgers`.
* **The shipped whitelist's 263 imposed capitals** are untouched by this work.
  `Le`, `Bank`, `Green`, `Hold` are bare entries that impose on ordinary prose;
  they want converting to phrase entries (`Le Cam`, `Le Gall`).
* **A pre-existing suite failure**, unrelated to this work and confirmed to
  fail at HEAD: `test_typos.py::…::test_the_capitalised_form_is_accepted_by_
  languages_that_lack_it`, where a spellchecker oracle rejects
  `accepts("Stochastic", "de")`. Not investigated here.
* **Roman numerals are lowercased** — `Saint-Flour XXXIV` → `xxxiv`,
  `Séminaire de probabilités XLVII` → `xlvii`. The acronym branch covers only
  2–3 letters. 22 distinct numerals affected. Not caused by this work.
* **The headroom.** The same gate with *no vocabulary at all* — preserve any
  mid-title capital in a title that is not Title Cased — was measured at
  **2,643 of 2,964 recovered (89%)**, 0 imposed, 0 destroyed, 0 new errors on
  the title-cased oracle, with **101 wrongly kept**: 71 French adjectives from
  names (`gaussiens`, `markoviens`, `boréliens`), 14 French nouns, 16 English
  leftovers. Three times the prize for twenty-five times the errors, and every
  error is one addressable class. It needs a French-morphology guard measured
  first, and it is the option to put to the owner.

## Reproducing

```
PYTHONPATH=src .venv/bin/python -c "
from pathlib import Path
from processing.author_vocabulary import mine, write
from core.config_paths import get_library_root
write(mine(Path(get_library_root())))"
```
