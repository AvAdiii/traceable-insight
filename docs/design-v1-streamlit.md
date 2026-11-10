# Coordinator view: design notes

Grounded in Apple's Human Interface Guidelines (via the `apple-design` skill), translated to a
desktop web app built with Streamlit.

**Thesis.** Each screen answers one question: *which children need a decision, and on what
evidence?*

**Signature: the receipt.** Every statement about a child opens its real source line in place,
with the neighbouring lines around it and the quoted words marked like a highlighter on a
printout. The visual boldness goes there; everything else is quiet system UI.

## Tokens

All text tokens meet WCAG AA (4.5:1) on both surfaces in both appearances
(`accessibility.md › Vision`, `dark-mode.md › Dark Mode colors`).

| Token | Light | on card / bg | Dark | on card / bg |
|---|---|---|---|---|
| label | #1D1D1F | 16.8 / 15.5 | #F5F5F7 | 12.8 / 15.6 |
| secondary | #6E6E73 | 5.1 / 4.7 | #AEAEB2 | 6.3 / 7.7 |
| accent (interactive only) | #0066CC | 5.6 / 5.1 | #4DA3FF | 5.3 / 6.5 |
| Conflict to review | #8E3FB0 | 6.0 / 5.5 | #D79BFF | 6.7 / 8.1 |
| Not enough information | #5E5E66 | 6.4 / 5.9 | #B4B4BB | 6.8 / 8.3 |
| Needs attention | #B83A00 | 5.8 / 5.3 | #FF9F43 | 6.8 / 8.3 |
| On track | #1D7A35 | 5.4 / 5.0 | #4CD964 | 7.6 / 9.3 |
| quote highlight (label on mark) | #FFED91 | 14.2 | #6B5F23 | 5.9 |

Surfaces: light bg #F5F5F7 with card #FFFFFF; dark bg #1C1C1E with card #2C2C2E.

## Rules applied

- **Never colour alone** (`color.md › Inclusive color`). Each state has its own glyph (⇄ arrows,
  dashed "?", triangle "!", check) and its full name. Attendance cells read P, A or –, not just
  a tint.
- **One colour, one meaning** (`color.md › Best practices`). Blue is only for interactive
  things and the cited line. The four state colours appear nowhere else. Orange-brown marks
  absences and fitness decline, the same signals that drive Needs attention.
- **Follow the system appearance** (`dark-mode.md › Best practices`). The page has no theme
  switch of its own; it follows the browser and Streamlit setting.
- **Type.** System font stack. 15px body and 13px secondary text, above the 13pt default and 10pt
  minimum for desktop. 28px semibold titles. No light weights (`typography.md`).
- **Targets.** Child rows are at least 44px tall and the whole row is one button. Visible focus
  ring at 3px in the accent colour, so the list works by keyboard (`accessibility.md › Mobility`).
- **Layout.** A sidebar for top-level places, then a split view on the Children page: a grouped
  list on the leading side and detail on the trailing side (`sidebars.md`, `layout.md`). The
  detail pane is sticky, and below 860px the columns stack.
- **Progressive disclosure.** Each row shows only first name, class and one-line reason. The
  detail pane leads with why the child is in this state, then the evidence, then everything else
  on record.
- **Feedback in place, undo available** (`feedback.md`). Linking a name shows a toast that says
  whether the child's state changed, and every decision can be undone from the Decided list.
- **Writing** (`writing.md`). Labels say what happens ("Link to child", "View source"). Empty
  states say what that means. Internal ids are never shown.
- **Source files page** shows the raw inputs exactly as the pipeline receives them (demo
  step 1), with no ground truth.
- **Minimal display.** No scores, ranks or surnames in lists. Surnames appear only where
  needed to tell two children apart in the review queue.
