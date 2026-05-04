---
name: Productivity Flow
colors:
  surface: '#f8f9ff'
  surface-dim: '#d7dae2'
  surface-bright: '#f8f9ff'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f1f3fc'
  surface-container: '#ebeef6'
  surface-container-high: '#e5e8f0'
  surface-container-highest: '#dfe2eb'
  on-surface: '#181c22'
  on-surface-variant: '#424655'
  inverse-surface: '#2d3137'
  inverse-on-surface: '#eef1f9'
  outline: '#737687'
  outline-variant: '#c3c6d8'
  surface-tint: '#0053db'
  primary: '#0050d6'
  on-primary: '#ffffff'
  primary-container: '#2a6af9'
  on-primary-container: '#fefcff'
  inverse-primary: '#b4c5ff'
  secondary: '#5c5f60'
  on-secondary: '#ffffff'
  secondary-container: '#e1e3e4'
  on-secondary-container: '#626566'
  tertiary: '#545d69'
  on-tertiary: '#ffffff'
  tertiary-container: '#6d7582'
  on-tertiary-container: '#fdfcff'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#dbe1ff'
  primary-fixed-dim: '#b4c5ff'
  on-primary-fixed: '#00174b'
  on-primary-fixed-variant: '#003ea8'
  secondary-fixed: '#e1e3e4'
  secondary-fixed-dim: '#c5c7c8'
  on-secondary-fixed: '#191c1d'
  on-secondary-fixed-variant: '#454748'
  tertiary-fixed: '#dbe3f2'
  tertiary-fixed-dim: '#bfc7d5'
  on-tertiary-fixed: '#141c27'
  on-tertiary-fixed-variant: '#3f4753'
  background: '#f8f9ff'
  on-background: '#181c22'
  surface-variant: '#dfe2eb'
typography:
  h1:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
    letterSpacing: -0.02em
  h2:
    fontFamily: Inter
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 28px
    letterSpacing: -0.01em
  h3:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '600'
    lineHeight: 24px
  body-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 22px
  body-sm:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '400'
    lineHeight: 18px
  label-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '500'
    lineHeight: 20px
  label-sm:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '500'
    lineHeight: 16px
  caption:
    fontFamily: Inter
    fontSize: 11px
    fontWeight: '400'
    lineHeight: 14px
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  unit: 4px
  xs: 4px
  sm: 8px
  md: 12px
  lg: 16px
  xl: 24px
  sidebar-width: 240px
  header-height: 56px
---

## Brand & Style

This design system is anchored in the **Corporate / Modern** aesthetic, specifically tailored for high-density productivity environments. The brand personality is efficient, reliable, and unobtrusive, designed to fade into the background so the user's work can take center stage. 

The emotional response should be one of "structured clarity"—where complex information feels manageable through precise alignment and a restrained color palette. It utilizes a logic-driven layout that prioritizes content discoverability and minimizes cognitive load. The interface avoids unnecessary flair, opting instead for functional elegance and a systematic approach to information architecture.

## Colors

The color strategy revolves around a high-utility light mode. The **Primary Blue (#3370FF)** is used sparingly for action-oriented elements, progress indicators, and active states. 

- **Surfaces:** Pure white (#FFFFFF) is the primary canvas for main content areas to maximize contrast with text.
- **Navigation:** The sidebar uses a distinct light grey (#F5F6F7) to create a clear structural hierarchy between navigation and workspace.
- **Accents:** A soft blue tint (#E8F0FF) is utilized for "Active" or "Selected" states within the sidebar and list items, ensuring visibility without the aggression of a solid primary color.
- **Borders:** A consistent, subtle grey (#DEE0E3) defines the boundaries of panels, inputs, and dividers, replacing heavy shadows with crisp line-work.
- **Typography:** The primary text uses a deep charcoal (#1F2329) rather than pure black to reduce eye strain during long working sessions.

## Typography

This design system employs **Inter** across all levels to leverage its exceptional readability and systematic weights. The scale is intentionally compact to accommodate data-heavy views.

- **Headlines:** Use semi-bold weights with slight negative letter spacing for a modern, "locked-in" professional look.
- **Body Text:** The default size is set to 14px, striking a balance between information density and legibility.
- **Labels:** Medium weights (500) are used for UI controls and navigation items to distinguish them from static content.
- **Numerical Data:** Inter’s tabular figures should be enabled for tables and dashboards to ensure vertical alignment of digits.

## Layout & Spacing

The system follows a **4px base grid** with a fluid layout model. It is designed to be "comfortable but compact," meaning padding is generous enough to prevent clutter but tight enough to show significant amounts of data on a single screen.

- **Grid:** A 12-column fluid grid is used for main dashboards, while document-style views use a centered 800px max-width container.
- **Margins & Gutters:** Standard page margins are 24px (xl), while internal component gutters typically use 12px (md) or 16px (lg).
- **Sidebar:** A fixed 240px sidebar provides persistent navigation. In collapsed states, this reduces to 64px.
- **Alignment:** All elements must align to the 4px baseline. Horizontal groups (like buttons in a footer) use 8px spacing.

## Elevation & Depth

Depth is primarily communicated through **Tonal Layers** and **Low-contrast Outlines** rather than heavy shadows.

- **Level 0 (Base):** The #F5F6F7 sidebar and background.
- **Level 1 (Surface):** White (#FFFFFF) cards and main content areas, outlined with a 1px #DEE0E3 border.
- **Level 2 (Popovers/Modals):** Floating elements use a very soft, diffused shadow (0px 4px 12px rgba(31, 35, 41, 0.08)) to indicate they sit above the surface, combined with a 1px border.
- **Active State:** Depth is also signaled through color; active navigation items use a light blue tint background instead of an elevation change, maintaining a flat, modern profile.

## Shapes

The shape language is defined by **Soft** geometry. 

- **Components:** Standard UI elements like buttons, input fields, and chips use a 6px corner radius.
- **Containers:** Larger elements such as cards and modals use an 8px radius.
- **Icons:** Use a 1.5pt stroke weight with slightly rounded caps and joins to match the component radius.
- **Avatars:** Strictly circular (pill-shaped) to provide a organic counterpoint to the otherwise rectangular grid.

## Components

- **Buttons:** Primary buttons are solid Blue (#3370FF) with white text. Secondary buttons use a white background with #DEE0E3 borders and #1F2329 text. Ghost buttons are used for lower-priority actions.
- **Sidebar Items:** Feature a 6px border-radius on the hover state. The active state uses the secondary blue tint (#E8F0FF) and transitions the icon/text color to the primary blue.
- **Inputs:** Feature a 1px #DEE0E3 border that turns Primary Blue on focus. Placeholder text uses #8F959E.
- **Chips/Tags:** Used for categorization; they feature a light grey fill and no border, with 12px font size.
- **Lists:** High-density list items should have a 48px fixed height with 1px bottom borders for clear separation.
- **Professional Line Icons:** Use a consistent 16x16 or 20x20 bounding box. Icons should be monochrome (#8F959E) until hovered or activated.
- **Additional Components:** Table views with fixed headers, searchable dropdowns (Select2 style), and "Feed" cards for collaborative updates.