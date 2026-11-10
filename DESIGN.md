# Design system: Stride (Traceable Insight v2, PWA)

Derived from the built app in `web/src` (tokens in `web/src/styles.css`). Visual references pinned
by the team: NRDN (flat illustration panels, sage and orange, rounded cards) and OCNUM (quiet stat
tiles, illustration above the calendar). Apple HIG for type, targets, sheets and appearance.
No emoji, no gradients, no blur: flat surfaces, one accent, flat vector illustration.

**Thesis.** A coach's clipboard turned into a calm, bright dashboard where every number is a
tappable chip that opens the spreadsheet cell it came from.

## Tokens (light / dark)

| Token | Light | Dark | Use |
|---|---|---|---|
| ground | #F4F4F1 (flat) | #0E1015 | page |
| plate | #E6EDD8 (ink #2F4A22) | same | light panel behind every illustration, both appearances |
| card / card-2 | #FFFFFF / #F5F6FA | #181B22 / #20242D | surfaces, insets |
| ink / ink-2 / ink-3 | #14161C / #555B6B / #6F7686 | #F2F3F7 / #B0B6C4 / #959CAD | text (all ≥ 4.5:1 on card) |
| invert | ink on white, white on ink | swapped | active nav, primary buttons, pills |
| accent | #E8590C (text #B8460A) | #F2753A (text #FF9A66) | chart line, today, progress, focus ring |
| lav · sky · mint · peach · lemon · rose · slate | pastel bg + deep ink pair each | deep bg + light ink | tiles, chips, flags |
| mark | #FFE680 | #6B5A12 | cited cell highlight, selection |

Radius: cards 28 px, tiles 22 px, pills full. Shadow: soft two-layer, offset + blur, no halos.

## Meaning

- **Flags** (never colour alone, always icon + label): Top performer = lemon + trophy, Most improved = mint + trending-up, Needs a push = peach + sprout, Declining = rose + trending-down, Missing test = slate + dashed circle.
- **Tests**: Jump = lav + rabbit, Run = sky + zap, Throw = peach + dumbbell, Endurance = mint + heart-pulse.
- **Inbox severity**: Blocks ranking (rose), Held from ranking (peach), For your info (slate).
- **Accent** is reserved for the programme line, today, progress and focus; never a flag.

## Components

- **Pill nav** (≥ md): floating card-blur pill, circular items, black active pill with spring `layoutId` motion; labels show on active item, all at xl.
- **Tab bar** (phone): floating pill at bottom, Home · Children · Meets · Ask · More (sheet with Schools, Inbox, Upload, Settings).
- **KPI tile**: white card, tinted 36 px icon tile, 32 px tabular number, one line of context.
- **Sheet**: bottom sheet with drag-to-dismiss on phone, right drawer on desktop; Escape and backdrop close.
- **Receipt** (signature): mint summary with the typed value on a marker highlight, facts (round, tested, uploaded, file fingerprint), spreadsheet grid with column letters and row numbers, cited row tinted, cited cell ringed in accent; scrolls to the cited column; Sheet1 / Revised toggle.
- **CellLink**: dotted underline + small cell ref chip (`J236`); opens the Receipt.
- **LineChart**: accent programme line (2.5 px, no fill) over grey per-school context lines, crosshair tooltip ranking schools, hover a line to label it; width-aware so text stays 11–12 px on phones.
- **Meter**: 8 px percentile bar with a median tick.
- **Event hero**: near-black text panel with accent progress bar, illustration on a plate at the side (top on phone).
- **Next meet card**: illustration plate on top, details and black action below.

## Type and layout

System stack (SF Pro on Apple, Segoe/Roboto elsewhere), tabular numerals for data. Page titles
28–38 px extrabold, section 19 px bold, body 15 px, secondary 13–13.5 px. Touch targets ≥ 44 px.
Home desktop: 3 / 6 / 3.2 grid (tiles · chart and lists · next meet, calendar, to-dos); phone
stacks with horizontally snapping tiles and the next meet right after them. Grid children get
`min-width: 0` so wide tables scroll inside their card.

## Illustration

`web/public/illus/*.svg`: unDraw flat vector illustrations (free licence), accent recoloured to
#E8590C, provenance in `web/public/illus/SOURCES.md`. Used sparingly: sign-in, next meet, event
hero, upload, Ask and empty states. Icons are Lucide; the logo is the plain wordmark “Stride”, no mark.
