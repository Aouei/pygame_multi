import pygame


def build_controls_surface() -> pygame.Surface:
    font_title = pygame.font.Font(None, 34)
    font = pygame.font.Font(None, 26)
    pad = 20
    line_h = 28

    rows = [
        ("Teclado", None),
        ("Mover",        "WASD"),
        ("Disparar",     "Clic izquierdo"),
        ("Controles",    "M"),
        ("", None),
        ("Mando", None),
        ("Mover",        "Analógico izquierdo"),
        ("Apuntar",      "Analógico derecho"),
        ("Disparar",     "Gatillo derecho (R2/RT)"),
        ("Controles",    "Select (btn 8)"),
    ]

    col_label = 140
    col_key   = 220
    w = pad * 2 + col_label + col_key
    h = pad * 2 + line_h + len(rows) * line_h

    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    surf.fill((30, 30, 30, 210))
    pygame.draw.rect(surf, (200, 200, 200, 80), surf.get_rect(), 1)

    title = font_title.render("Controles", True, (255, 255, 255))
    surf.blit(title, (pad, pad))

    y = pad + line_h + 4
    for label, key in rows:
        if label == "" and key is None:
            y += line_h // 2
            continue
        if key is None:
            txt = font.render(label, True, (180, 220, 255))
            surf.blit(txt, (pad, y))
        else:
            lbl = font.render(label, True, (200, 200, 200))
            k   = font.render(key,   True, (255, 255, 140))
            surf.blit(lbl, (pad, y))
            surf.blit(k,   (pad + col_label, y))
        y += line_h

    return surf
