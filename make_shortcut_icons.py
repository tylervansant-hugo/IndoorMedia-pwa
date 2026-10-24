#!/usr/bin/env python3
"""Generate distinct per-shortcut PWA icons (192 + 512, any + maskable)."""
import cairosvg, os

OUT = os.path.dirname(os.path.abspath(__file__))

# Each shortcut: key, background gradient colors, big glyph (emoji), label
SHORTCUTS = [
    ("callin",   "#E53935", "#B71C1C", "\U0001F4DE", "CALL-IN"),   # phone
    ("prospect", "#1E88E5", "#0D47A1", "\U0001F50D", "PROSPECT"),  # magnifier
    ("quote",    "#43A047", "#1B5E20", "\U0001F9FE", "QUOTE"),     # receipt
    ("appt",     "#8E24AA", "#4A148C", "\U0001F4C5", "BOOK"),      # calendar
]

def svg(c1, c2, glyph, label, maskable):
    # maskable needs ~20% safe padding; render content inside inner circle
    pad = 0.10 if maskable else 0.0
    size = 512
    inner = size * (1 - 2*pad)
    off = size * pad
    r = 96 if not maskable else 0  # rounded square for 'any', full bleed for maskable
    glyph_size = int(inner * 0.42)
    glyph_y = off + inner * 0.48
    label_y = off + inner * 0.88
    label_size = int(inner * 0.11)
    bg = f'<rect x="0" y="0" width="{size}" height="{size}" rx="{r}" fill="url(#g)"/>' if not maskable \
         else f'<rect x="0" y="0" width="{size}" height="{size}" fill="url(#g)"/>'
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 {size} {size}">
  <defs>
    <linearGradient id="g" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="{c1}"/>
      <stop offset="1" stop-color="{c2}"/>
    </linearGradient>
  </defs>
  {bg}
  <text x="{size/2}" y="{glyph_y}" font-size="{glyph_size}" text-anchor="middle"
        dominant-baseline="middle" font-family="Apple Color Emoji, Segoe UI Emoji, sans-serif">{glyph}</text>
  <text x="{size/2}" y="{label_y}" font-size="{label_size}" text-anchor="middle"
        fill="#ffffff" font-weight="800" letter-spacing="1"
        font-family="-apple-system, Helvetica, Arial, sans-serif">{label}</text>
</svg>'''

for key, c1, c2, glyph, label in SHORTCUTS:
    for mask in (False, True):
        suffix = "-maskable" if mask else ""
        data = svg(c1, c2, glyph, label, mask)
        for px in (192, 512):
            name = f"sc-{key}-{px}{suffix}.png"
            cairosvg.svg2png(bytestring=data.encode(), write_to=os.path.join(OUT, name),
                             output_width=px, output_height=px)
            print("wrote", name)
print("done")
