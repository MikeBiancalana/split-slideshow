"""Pygame app: 2x2 grid of panels, each on a staggered flip timer."""

from __future__ import annotations

import pygame

from .config import Config
from .panel import Panel


def _grid_rects(width: int, height: int) -> list[pygame.Rect]:
    """Four equal quadrants: top-left, top-right, bottom-left, bottom-right."""
    half_w, half_h = width // 2, height // 2
    return [
        pygame.Rect(0, 0, half_w, half_h),
        pygame.Rect(half_w, 0, width - half_w, half_h),
        pygame.Rect(0, half_h, half_w, height - half_h),
        pygame.Rect(half_w, half_h, width - half_w, height - half_h),
    ]


def run(config: Config) -> None:
    pygame.init()
    pygame.display.set_caption("split-slideshow")

    flags = 0
    size = config.resolution or (0, 0)  # (0, 0) = native desktop resolution
    if config.fullscreen:
        flags = pygame.FULLSCREEN
        # SCALED needs an explicit size; only useful when rendering at a fixed
        # resolution scaled onto the display. With native res, plain FULLSCREEN.
        if config.resolution is not None:
            flags |= pygame.SCALED
    screen = pygame.display.set_mode(size, flags)
    width, height = screen.get_size()
    pygame.mouse.set_visible(False)

    screen.fill(config.background)

    rects = _grid_rects(width, height)
    panels = [
        Panel(folder, rect, config.background, config.rescan_every)
        for folder, rect in zip(config.folders, rects)
    ]

    interval_ms = int(config.interval_seconds * 1000)
    stagger_ms = int(config.stagger_seconds * 1000)
    now = pygame.time.get_ticks()
    # Stagger the first flip per panel so they don't all change at once.
    next_flip = [now + i * stagger_ms for i in range(len(panels))]

    clock = pygame.time.Clock()
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN and event.key in (
                pygame.K_ESCAPE,
                pygame.K_q,
            ):
                running = False

        now = pygame.time.get_ticks()
        dirty: list[pygame.Rect] = []
        for i, panel in enumerate(panels):
            if now >= next_flip[i]:
                panel.render(screen, panel.pick_next())
                dirty.append(panel.rect)
                next_flip[i] = now + interval_ms

        if dirty:
            pygame.display.update(dirty)
        clock.tick(30)

    pygame.quit()
