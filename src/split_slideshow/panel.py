"""A single slideshow panel: scans a folder and draws scaled images into a cell.

Image decoding happens on a background thread so a slow load (e.g. a large photo
off a network/CIFS mount) never stalls the main render loop. Each panel keeps one
decoded-and-scaled frame ready ahead of time; the main loop just blits it.
"""

from __future__ import annotations

import queue
import random
import threading
from collections import deque
from pathlib import Path

import pygame
from PIL import Image, ImageOps, UnidentifiedImageError

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"}


class Panel:
    def __init__(
        self,
        folder: Path,
        rect: pygame.Rect,
        background: tuple[int, int, int],
        rescan_every: int,
        avoid_recent: int = 5,
    ) -> None:
        self.folder = folder
        self.rect = rect
        self.background = background
        self.rescan_every = max(1, rescan_every)
        self.avoid_recent = max(0, avoid_recent)
        # images/recent/flips_since_scan are only touched by the worker thread.
        self.images: list[Path] = []
        self.recent: deque[Path] = deque(maxlen=max(1, self.avoid_recent))
        self.flips_since_scan = 0
        self._font: pygame.font.Font | None = None
        # One-slot queue: the worker prepares exactly one frame ahead, then blocks
        # until the main loop consumes it. Items are scaled Surfaces, or None to
        # signal "no images available".
        self._queue: queue.Queue = queue.Queue(maxsize=1)
        self._stop = threading.Event()
        self.scan()
        self._thread = threading.Thread(
            target=self._worker, name=f"panel-{folder.name}", daemon=True
        )
        self._thread.start()

    # --- worker thread ---------------------------------------------------

    def _worker(self) -> None:
        while not self._stop.is_set():
            path = self.pick_next()
            if path is None:
                self._put(None)  # tell main loop to show the placeholder
                self._stop.wait(1.0)  # nothing to show; poll for new files
                continue
            surface = self._prepare(path)
            if surface is None:
                continue  # bad/garbage file: skip immediately, try another
            self._put(surface)

    def _put(self, item: pygame.Surface | None) -> None:
        """Block until the item is queued, but stay responsive to shutdown."""
        while not self._stop.is_set():
            try:
                self._queue.put(item, timeout=0.2)
                return
            except queue.Full:
                continue

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
        """Choose the next image, avoiding the most recently shown ones.

        Avoids up to the last `avoid_recent` images, but never so many that no
        candidate remains, so small folders still cycle.
        """
        self.flips_since_scan += 1
        if self.flips_since_scan >= self.rescan_every:
            self.scan()
        if not self.images:
            return None
        # Cap the avoid-window at len-1 to guarantee at least one candidate.
        k = min(self.avoid_recent, len(self.images) - 1)
        avoid = set(list(self.recent)[-k:]) if k else set()
        choices = [p for p in self.images if p not in avoid] or list(self.images)
        pick = random.choice(choices)
        self.recent.append(pick)
        return pick

    def _prepare(self, path: Path) -> pygame.Surface | None:
        """Decode and scale an image to fit the cell. Returns None on any error.

        Runs off the main thread, so it must not call Surface.convert() (which
        needs the display context); the main thread converts implicitly on blit.
        """
        try:
            with Image.open(path) as im:
                # draft() lets the JPEG decoder downscale while reading, so large
                # photos decode far faster. No-op for formats that don't support it.
                im.draft("RGB", (self.rect.width, self.rect.height))
                im = ImageOps.exif_transpose(im).convert("RGB")
                raw, size = im.tobytes(), im.size
        except (OSError, ValueError, UnidentifiedImageError) as e:
            print(f"[panel] skipping unreadable file {path}: {e}")
            return None
        try:
            img = pygame.image.frombytes(raw, size, "RGB")
        except (pygame.error, ValueError) as e:
            print(f"[panel] cannot build surface for {path}: {e}")
            return None
        iw, ih = img.get_size()
        if iw == 0 or ih == 0:
            return None
        scale = min(self.rect.width / iw, self.rect.height / ih)
        new_size = (max(1, round(iw * scale)), max(1, round(ih * scale)))
        return pygame.transform.smoothscale(img, new_size)

    # --- main thread -----------------------------------------------------

    def try_swap(self, surface: pygame.Surface) -> bool:
        """If a freshly prepared frame is ready, draw it. Non-blocking.

        Returns True if the cell was updated, False if nothing is ready yet
        (in which case the current image keeps showing).
        """
        try:
            item = self._queue.get_nowait()
        except queue.Empty:
            return False
        surface.fill(self.background, self.rect)  # black letterbox
        if item is None:
            self._render_message(surface, "no images")
        else:
            surface.blit(item, item.get_rect(center=self.rect.center))
        return True

    def stop(self) -> None:
        self._stop.set()

    def _render_message(self, surface: pygame.Surface, text: str) -> None:
        # Font rendering needs SDL_ttf; if unavailable, leave the cell black
        # rather than crashing the whole show.
        try:
            if self._font is None:
                self._font = pygame.font.SysFont(None, 36)
            label = self._font.render(text, True, (90, 90, 90))
            surface.blit(label, label.get_rect(center=self.rect.center))
        except pygame.error as e:
            print(f"[panel] cannot render text '{text}': {e}")
