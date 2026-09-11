# Product Requirements Document (PRD) – BISNova Chatbot UI

## Project Overview
- **Name**: BISNova (formerly BISNova)
- **Goal**: Recreate the chatbot UI with the provided design assets, color palette, and interactive features using plain HTML, CSS, and JavaScript (no framework).
- **Target Platform**: static web site served via a local HTTP server (e.g., `python -m http.server`).
- **Key Assets**: `logo.png`, `mascot.png`, hero images, and reference UI screenshot.

## Design System & Color Palette
| Variable | Hex | Usage |
|---|---|---|
| `--bg-main` | `#F9FFFE` | Page background |
| `--primary-black` | `#171416` | Text, icons |
| `--primary-blue` | `#48A4FB` | Accent elements (buttons, bot bubble border) |
| `--secondary-color` | `#DCEEFF` | Light background accents |
| `--accent-color` | `#E66A3A` | Highlight elements |
| `--primary-color` | `#B83F4A` | Branding (logo, headings) |
| `--bg-secondary` | `#FFF0EA` | Secondary backgrounds |

## Implemented Files (as of now)
| File | Path | Description |
|---|---|---|
| `style.css` | `c:\Users\chitr\OneDrive\Desktop\Extras\SIH\style.css` | Full stylesheet implementing the palette, layout, sidebar, chat bubbles, SVG tails, subtle mascot animation, responsive behavior. |
| `index.html` | `c:\Users\chitr\OneDrive\Desktop\Extras\SIH\index.html` | Base HTML skeleton with meta tags, Google Font import, sidebar markup, chat area, and script references. |
| `app.js` | `c:\Users\chitr\OneDrive\Desktop\Extras\SIH\app.js` | Core JS handling message rendering, speech‑bubble generation (including SVG tails), recent‑chat dropdown, home icon placeholder, three‑dot menu (pin/rename/delete), and simple mascot “reading” animation trigger. |
| Assets | `c:\Users\chitr\OneDrive\Desktop\Extras\SIH\assets\` | `logo.png`, `mascot.png`, hero images copied from user uploads. |

## Core UI Features Implemented
1. **Sidebar**
   - Logo at top, collapse/expand toggle.
   - Navigation items: New Chat, Dashboard, Search Standards, Testing & Labs, Help/FAQs.
   - Recent Chats section with:
     - Dropdown button (replaces delete icon).
     - Home icon placeholder (unlinked).
     - Three‑dot menu offering Pin, Rename, Delete.
   - Sidebar can be opened/closed via the toggle.
2. **Chat Area**
   - Distinct speech bubbles for user (blue) and bot (terracotta) with custom SVG tails.
   - Message input with send button.
   - Typing indicator while bot “thinks”.
   - Mascot animation: subtle floating / reading motion, triggered on message receipt; kept low‑profile per user request.
3. **Landing/Home Page**
   - Hero section containing a laptop image positioned partly out of frame for 3‑D effect.
   - Additional copy text to flesh out the UI.
   - Responsive layout for various screen sizes.
4. **Animations**
   - Simple CSS keyframe for mascot idle breathing effect.
   - Motion is intentionally subtle to avoid irritation.
5. **Responsive Design**
   - Flexbox/Grid layout adapts to mobile widths; sidebar collapses to a hamburger icon.

## Outstanding / Next Steps
- **Refine mascot animation**: add “thinking” state (e.g., slight tilt) when the bot is generating a response.
- **Implement recent‑chat functionality**: persist chat titles, enable pinning and renaming with local storage.
- **Add home navigation**: link the home icon to the landing page once routing is in place.
- **Accessibility improvements**: ARIA labels for navigation, focus management for keyboard users.
- **Testing**: visual regression against the reference UI screenshot, cross‑browser checks.
- **Deployment**: optional static site hosting (GitHub Pages, Vercel) and CI pipeline.

## How to Continue
1. **Pull the repository** (or copy the `SIH` folder) to a development environment.
2. Run `python -m http.server 5173` (or any static server) from the project root.
3. Open `http://localhost:5173` and verify the UI against the reference image.
4. Follow the **Next Steps** list above to add missing interactivity and polish.
5. Commit changes and push to version control; the next AI can resume from the point of the pending items.

---
*Generated on 2026-09-09 by Antigravity AI.*
