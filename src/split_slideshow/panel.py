"""A single slideshow panel: scans a folder and draws scaled images into a cell."""

from __future__ import annotations

import random
from pathlib import Path

import pygame

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"}


class Panel:
    def __init__(
        self,
        folder: Path,
        rect: pygame.Rect,
        background: tuple[int, int, int],
        rescan_every: int,
    ) -> None:
        self.folder = folder
        self.rect = rect
        self.background = background
        self.rescan_every = max(1, rescan_every)
        self.images: list[Path] = []
        self.last: Path | None = None
        self.flips_since_scan = 0
        self._font: pygame.font.Font | None = None
        self.scan()

    def scan(self) -> None:
        """Recursively collect image files under the folder."""
        try:
            self.images = sorted(
                p
                for p in self.folder.rglob("*")
                if p.is_file() and p.suffix.lower() in IMAGE_EXTS
            )
        except OSError as e:
            print(f"[panel] scan failed for {self.folder}: {e}")
            self.images = []
        self.flips_since_scan = 0

    def pick_next(self) -> Path | None:
        """Choose the next image, avoiding an immediate repeat when possible."""
        self.flips_since_scan += 1
        if self.flips_since_scan >= self.rescan_every:
            self.scan()
        if not self.images:
            return None
        choices = self.images
        if len(choices) > 1 and self.last is not None:
            choices = [p for p in self.images if p != self.last] or self.images
        self.last = random.choice(choices)
        return self.last

    def render(self, surface: pygame.Surface, image_path: Path | None) -> None:
        """Fill the cell black (letterbox) and blit the scaled image centered."""
        surface.fill(self.background, self.rect)
        if image_path is None:
            self._render_message(surface, "no images")
            return
        try:
            img = pygame.image.load(str(image_path)).convert()
        except (pygame.error, OSError) as e:
            print(f"[panel] failed to load {image_path}: {e}")
            self._render_message(surface, "bad image")
            return

        iw, ih = img.get_size()
        if iw == 0 or ih == 0:
            return
        scale = min(self.rect.width / iw, self.rect.height / ih)
        new_size = (max(1, round(iw * scale)), max(1, round(ih * scale)))
        scaled = pygame.transform.smoothscale(img, new_size)
        dest = scaled.get_rect(center=self.rect.center)
        surface.blit(scaled, dest)

    def _render_message(self, surface: pygame.Surface, text: str) -> None:
        if self._font is None:
            self._font = pygame.font.SysFont(None, 36)
        label = self._font.render(text, True, (90, 90, 90))
        surface.blit(label, label.get_rect(center=self.rect.center))
