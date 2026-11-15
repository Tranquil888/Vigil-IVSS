# DESIGN.md — UI/UX Guidelines

## 1. Core Aesthetic
A professional, high-density surveillance interface. The design must prioritize clarity, speed, and data over decoration. It should feel like functional equipment, not a consumer app.
*   **Flat & Sharp:** Strictly square corners. No shadows, no gradients, no blur.
*   **Instant Feedback:** Visual changes (like hovering over a button) must appear instantly, with no slow transitions or animations.
*   **Dual Theme:** Must support both a high-contrast Dark theme and a clean Light theme.

## 2. Color & Typography
*   **Palette:** Strictly grayscale (backgrounds, panels, text) paired with a single, high-visibility **Green** accent. Use Green only for active states, primary actions, slider thumbs.
*   **Forbidden Colors:** No blue, no purple, no pastels.
*   **Typography:** Clean sans-serif for general text. Use a monospace font for data-heavy elements (timestamps, IDs) to keep columns aligned.
*   **Separators:** Use thin, solid lines to separate panels and elements. Never use drop shadows for depth.

## 3. Layout & Components
*   **Buttons & Inputs:** Solid backgrounds with sharp edges. Primary buttons use the Green accent with dark text. Checkboxes and radio buttons are strictly square.
*   **Data Tables:** Alternating row backgrounds to aid scanning. Unrecognized stranger events are highlighted with a solid Green bar on the left edge.

## 4. Prohibited Elements
1. Rounded corners or circular elements.
2. Drop shadows or gradients.
3. Colors outside the grayscale + Green (and critical Red for alerts) palette.
4. Decorative icons or multi-colored graphics (use minimalist line icons).