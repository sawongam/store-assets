# Store copy: story, headlines, lint

Screenshots are ads, not documentation. People scroll a search result in about a second, and most never open the full gallery. The first three images have to sell the app on their own.

## Story order

| # | Slide | Job |
|---|---|---|
| 1 | **hero** | Name plus the one promise. The app at its best, with 2 devices if there's a second strong screen. |
| 2–3 | **top benefits** | The two reasons people install. Show the screen where the benefit is visible. |
| 4–8 | **supporting benefits** | Breadth: other key flows, customisation, platforms. |

Every slide shows a real screen; there is no text-only closing slide. Put trust and objections (privacy, offline, no ads, no sign-up) in the hero body or a feature eyebrow.

Use 4–8 slides. Play shows up to 8, and Apple up to 10, but past 8 nobody scrolls.

## Headline rules

- **One idea per slide.** If you need "and", it's two slides.
- **Lead with a benefit, not a feature.** Write "Know what your ride *really* does", not "Mileage statistics screen".
- **Use 2 lines of 2–4 words each.** Break with `\n` where the phrase breathes. The renderer shrinks text that is too long, but treat a shrink warning as a rewrite request.
- **Put one accent per headline.** Wrap 1–2 words in `*stars*` and they render in the accent colour. Accent the payoff word ("*seconds*", "*every ride*"), not filler.
- **Use the eyebrow for proof or mechanics.** It's a small uppercase label above the headline ("FUEL × PRICE = PAID", "WORKS OFFLINE"). Keep it to 2–5 words, with a middle dot `·` between short items.
- **Use verbs the user does:** Log, See, Know, Plan, Track, Share. Avoid "Powerful", "Seamless" and "Intuitive", which say nothing.
- **Make claims you can prove.** No "fastest", "most accurate" or "#1". Numbers are fine when they're features ("3 taps to log"), and not fine when they're metrics you can't show.
- **Stay consistent.** Same tense and person, either all imperatives or all "you" statements. No trailing periods, unless the hero uses one for rhythm ("Every tank, *counted.*").

### Formulas that work

| Formula | Example |
|---|---|
| Verb + object + payoff | "Log a fill-up / in *seconds*" |
| Know/See + what matters | "See where the / *money* goes" |
| Every/Any + scope | "Built for / *any ride*" |
| Objection killer | "No ads. / *No sign-up.*" |
| Before → after | "From receipts / to *real mileage*" |

## Hero

- **Hero headline:** the category promise in 3–5 words. Hero body: one sentence, 6–10 words, that says what the app is ("Mileage, fuel and spend for every ride.").

## Banned and risky copy

`check.py` reads `scripts/specs.json → copy_lint`. Matching is whole-word and case-insensitive.

- **Errors on both stores:**
  - ranking and awards: "best", "#1", "top rated", "editor's choice", "award-winning"
  - promo: "sale", "discount", "% off", "million downloads"
  - calls to action: "download now", "install now", "try now", "play now"
- **Errors on Play:** naming Apple platforms ("iPhone", "iOS", "App Store").
- **Errors on the App Store:** naming "Android" or "Google Play". Apple Guideline 2.3.10 bans other platforms.
- **Warnings:** "free", "new", "only", prices and currency symbols, "guaranteed", "100%". They're fine when factual and not promotional. "Free" is risky on Play, and "No ads" is safer. Time-sensitive words go stale.

Also avoid:

- text over 20% of a Play screenshot's area (Play's guidance)
- tiny type: nothing under ~28px on a 1080-wide canvas
- other brands' logos, characters or trademarks
- real people's data in captures

## Localization

- Text fields take `{"en-US": "...", "de-DE": "..."}`. Locales use the store codes (`en-US`, `de-DE`, `ja`, `pt-BR`…).
- Translate meaning, not words. Rewrite headlines natively, since German and Russian run 30–40% longer. Re-render and fix every shrink warning.
- Reuse the app's own ARB, `strings.xml` or `.xcstrings` vocabulary so the store matches the UI.
- Captures should be localized too (`dir: "raw/{locale}/phone"`). If they aren't, the renderer reuses the first locale's captures and warns.
- For CJK, Arabic, Hebrew, Thai or Devanagari, point `brand.fonts` at a font with those glyphs (Noto Sans <script>). Display fonts rarely cover them.

## Alt text (Play asks for it, 140 characters or fewer)

Write one sentence about what is shown, with no "image of" or "screenshot of". For example: "Home screen showing last tank mileage of 33.3 km/L with distance and fill-up count." Give the user one line per image at hand-off.
