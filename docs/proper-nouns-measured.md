# Proper nouns in titles, measured

## The problem

`core.sentence_case.to_sentence_case_academic` lowercases every capitalised
word it does not recognise. Measured over the 25,043 in-scope titles, that
destroyed **2,964 mid-title capitals**: mathematicians (Bourbaki 64, Fock 22,
Landau 15, Azéma 13, Hartree 12, Doeblin 9, Gronwall 8), places (Saint-Flour
59, Japan 22, Tōhoku 17, Sendai 17, Paris 14), every month of the year, and
Roman numerals (`Saint-Flour XXXIV` → `xxxiv`).

## The answer is a census, not a list

The library already knows. It writes `Saint-Flour` 59 times and `flour` never;
`stochastic` 3,333 times in lower case and 3 capitalised. So the vocabulary is
not curated — it is a **census** over every mid-title word: how often this
library's own titles capitalise it, and how often they do not.

One table, no lists, and it answers all of it at once:

| word | census (cap/low) | verdict |
|---|---|---|
| flour, june, tōhoku, sendai | 59/0, 21/0, 17/0, 17/0 | NAME |
| fock, landau, gronwall, hartree | 22/0, 15/0, 12/0, 12/0 | NAME |
| ii, iii, xii — Roman numerals | 224/0, 63/0, 11/0 | NAME |
| the, an, stochastic, convex | 35/5791, 16/612, 3/3333, 2/276 | COMMON |
| green, hull, back, may | 6/10, 3/6, 5/6, 42/10 | REVIEW |

It gets months right **per language**, which no single list could: April 38/0
and September 13/0 because English capitalises months; `mai` 0/7, `juin` 0/10
and `septembre` 0/2 because French does not; `Dezember` 1/0 because German
capitalises every noun; and `juillet` 3/1 and `May` 42/10 land in the review
band, where they belong.

An earlier version filtered the census with the hand list that keeps months out
of the author set. That removed the English months from the vocabulary and cost
real recoveries — caught by a test asserting `April` survives. The list now
guards the author set only.

The title's **first word is never counted** — every title starts with a
capital, so it is evidence about nothing. Titles that are themselves Title
Cased are excluded for the same reason: 19 titles, affecting 85 words.

## Where the census is silent, the author blocks speak

A word that never appears mid-title has no title evidence at all. If the
library has an *author* of that name, that is evidence of a different kind.

This is what keeps **Le Cam** and **Le Gall**: neither `cam` nor `gall` appears
mid-title anywhere in the library, so both are invisible to the census, and
both are authors. Without the fallback the caser produced `Le cam`, `Le gall`.

It is a fallback, not a source: where the census has spoken it wins, so `law`
stays a common word (0 capitalised against 240) however many people are called
Law.

## A whitelist entry may no longer overrule the library

`capitalization_whitelist` does not preserve a capital, it **imposes** one —
matching is case-insensitive and the entry's own spelling is emitted.
Measured, five bare entries imposed 267 wrong capitals between them:

| entry | census | what it did |
|---|---|---|
| `Le` — presumably meant for Le Cam | 1/131 | `sur le grossissement` → `sur Le …` ×131 |
| `posedness` | 0/86 | `well-posedness` → `well-Posedness` ×86 |
| `White` | 3/23 | ×23 |
| `Bank` | 2/18 | ×18 |
| `Hold` | 0/9 | ×9 |

An entry may now no longer raise a word the library writes in lower case. It
only ever blocks *raising* — an already-capitalised phrase is untouched, so no
entry loses its ability to fix a spelling or a dash (`Ito` → `Itô` still
works).

## Result, measured over all 25,043 titles

| | before | after |
|---|---|---|
| capitals **recovered** | 986 | **2,388** (1,225 distinct words) |
| capitals imposed by this rule | 0 | **0** |
| capitals newly lost | 0 | **0** |
| titles destroyed / characters lost | 0 | **0** |
| wrong capitals imposed by the caser | 445 | **289** |

## Words that are both — asked, not guessed

A word is decided automatically only when one side outweighs the other **6:1**.
Below that the evidence is genuinely mixed and the word is **held back and
queued** — an unanswered question must not act as a yes. **124 words are
held.**

A second, smaller list is **flagged rather than held**: 24 French adjectives
built from a name (`Gaussiennes` 4/0, `Laplacien` 1/0, `Borélien` 2/0). The
library is unanimous on these, so the census is believed and the capital kept —
overruling a unanimous measurement with a morphology guess is exactly the
hand-rule this design exists to avoid. They are shown to the owner instead,
who is the one who knows.

The *plurals* need no such help: the census already catches `gaussiens` 9/7,
`markoviens` 5/1 and `boréliens` 3/1 as REVIEW, and `browniens` 0/14 as COMMON.
None is recovered.

Both lists live on the cockpit's **Spelling** page with their counts, whether
the word is an author in the library, and a Name / Word button each.

## It learns

Answers live in `config/casing_decisions.json`, separate from the generated
census so a re-mine can never erase them, and they beat the evidence in both
directions.

Each answer records the evidence it was given against. When a later re-mine
finds the usage has crossed to the **other side of the rule** — a word first
seen as a noun that later turns up as a mathematician, or the reverse — it
returns to the queue marked *changed since you decided*, and is asked first.
A small drift reopens nothing, or the queue would never empty. A decision
recorded without evidence never reopens: with nothing to compare against,
"has this changed?" is UNKNOWN, and nagging on UNKNOWN costs the queue its
authority.

## What the audit found, and did not

Every one of the recoveries was checked against an English dictionary for words
that might be ordinary prose. 177 words / 489 occurrences came back as
dictionary words, and **every one is correct in context**: `Flour`
(Saint-Flour), `Scottish` (*The Scottish Book*), `Lax` (Peter Lax), `Cornish`
(Cornish–Fisher), `Crank` (Crank–Nicolson), `United` (United Kingdom), `Court`
(the European Court), `Advisor` (a product name). **No error was found.**

That is not the same as there being none. The audit is a dictionary sweep plus
a hand read of the tail, over the same population the census was built from. It
is not an independent sample, and no independent sample exists.

## Mutation

15 of 15 mutants killed on the census, the fallback, the flagged class and the
whitelist guard; 17 of 17 on the eponym rule and its title-case gate; 16 of 16
on the review queue and its learning.

One mutant changed the design rather than confirming it: removing the compound
walk's lower-case guard scored *better* than the real code on two of three real
titles, because the guard was breaking at the `de` of `Saint-Jean-de-Monts` and
stranding `Monts`. Name particles are now walked through.

## Still open, recorded rather than implied

* **289 wrong capitals the caser still imposes**, down from 445. They come from
  branches this work did not touch: `le` ×28 via a multi-word phrase match,
  `gamma` ×17, `green` ×10, `random` ×8, `hull` ×6.
* **The census is a feedback loop by construction.** It learns the library's
  current casing, so a systematic error in the library would be preserved
  rather than corrected. The review queue is the counterweight and the owner
  overrules it. That is a property of the design, not a defect, but it should
  be stated rather than discovered.
* **Words the library has never seen** get no protection unless they are author
  surnames. That only bites on titles arriving from ingest, and it is
  unmeasurable on today's data.
* **A pre-existing suite failure**, unrelated and confirmed to fail at HEAD:
  `test_typos.py::…::test_the_capitalised_form_is_accepted_by_languages_that_lack_it`,
  where a spellchecker oracle rejects `accepts("Stochastic", "de")`.

## Reproducing

```
PYTHONPATH=src .venv/bin/python -c "
from pathlib import Path
from processing.casing_vocabulary import mine, write
from core.config_paths import get_library_root
ev, au = mine(Path(get_library_root())); write(ev, au)"
```
