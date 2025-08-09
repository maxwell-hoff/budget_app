#!/usr/bin/env python3
"""generate_homepage_video.py

Produce a 15-second (30 FPS) MP4 that reproduces the Pygame landing-page
visualisation and writes it to:

    budget_app/frontend/static/videos/landing_visual.mp4

Run it from the project root:

    python backend/scripts/generate_homepage_video.py

Dependencies:
    - pygame
    - imageio[ffmpeg]
    - numpy

Add these to your environment (e.g. `pip install -r requirements.txt` after
appending `pygame`, `imageio[ffmpeg]`).
"""
from __future__ import annotations

import os
import random
import sys
from pathlib import Path

import numpy as np
import imageio.v2 as imageio  # v2 API kept for compatibility
import pygame
import pygame.gfxdraw  # noqa: F401 – required for anti-aliased circles

# ---------------------------------------------------------------------------
# --------------------------- Simulation parameters -------------------------
# ---------------------------------------------------------------------------
WIDTH, HEIGHT = 3000, 1000       # canvas size (matches landing_page_viz.py)
FPS = 30                       # frames-per-second for both sim and video
DURATION_SECONDS = 17          # total length of the exported clip
TOTAL_FRAMES = FPS * DURATION_SECONDS

# Keep the rest of the constants in sync with landing_page_viz.py ------------
GENERATION_LIMIT = 10
SECTION_COUNT = 30
DIRECTION = 1  # mutable in code – global for simplicity
MIN_CHILDREN, MAX_CHILDREN = 1, 20
JITTER_DISTANCE = 0
SCREEN_MARGIN = 60
NODE_RADIUS = 2
NODE_OUTER_COLOR = (50, 200, 255)  # RGB
NODE_INNER_COLOR = (0, 0, 0)
INNER_FILL_PERCENT = 0.8
LINE_COLOR = (100, 100, 100)
BG_COLOR = (10, 10, 10)
GROWTH_SPEED = 0.2
FADE_SPEED = 0.02
SPAWN_INTERVAL_FRAMES = 5
MAX_POSITION_TRIES = 25

# ---------------------------------------------------------------------------
# Geometry helpers -----------------------------------------------------------


def _ccw(A, B, C):
    """Return True if A, B, C are counter-clockwise oriented."""
    return (C[1] - A[1]) * (B[0] - A[0]) > (B[1] - A[1]) * (C[0] - A[0])


def segments_intersect(p1, p2, p3, p4):
    """Return True if segment p1-p2 intersects p3-p4 (excluding shared ends)."""
    if p1 in (p3, p4) or p2 in (p3, p4):
        return False
    return _ccw(p1, p3, p4) != _ccw(p2, p3, p4) and _ccw(p1, p2, p3) != _ccw(
        p1, p2, p4
    )


# ---------------------------------------------------------------------------
# Data model -----------------------------------------------------------------


class Node:
    def __init__(self, position, section, generation, parents=None):
        self.position = position  # (x, y)
        self.parents = parents or []
        self.section = section
        self.generation = generation
        self.growth = 0.0  # 0 = newborn, 1 = fully grown
        self.fade = 1.0    # 1 = opaque, 0 = invisible


# ---------------------------------------------------------------------------
# Simulation core ------------------------------------------------------------


def add_children(nodes: list[Node]):
    """Spawn a new generation of children and prune old ones."""
    global DIRECTION

    parent = nodes[-1]
    parent_section = parent.section
    next_section = parent_section + DIRECTION
    if next_section < 0 or next_section >= SECTION_COUNT:
        DIRECTION *= -1
        next_section = parent_section + DIRECTION

    num_children = random.randint(MIN_CHILDREN, MAX_CHILDREN)
    section_width = WIDTH / SECTION_COUNT
    left_bound = next_section * section_width
    right_bound = left_bound + section_width

    for _ in range(num_children):
        # find a valid position (avoid edge-edge intersection)
        for _ in range(MAX_POSITION_TRIES):
            new_x = random.uniform(max(left_bound + SCREEN_MARGIN, left_bound),
                                   min(right_bound - SCREEN_MARGIN, right_bound))
            new_y = random.uniform(SCREEN_MARGIN, HEIGHT - SCREEN_MARGIN)
            candidate = (new_x, new_y)

            intersects = False
            for n in nodes:
                for p in n.parents:
                    if p not in nodes or p == parent:
                        continue
                    if segments_intersect(parent.position, candidate, p.position, n.position):
                        intersects = True
                        break
                if intersects:
                    break
            if not intersects:
                break

        child = Node(position=candidate, section=next_section,
                      generation=parent.generation + 1, parents=[parent])
        nodes.append(child)

    # prune by generation depth
    max_gen = max(n.generation for n in nodes)
    nodes[:] = [n for n in nodes if n.generation >= max_gen - (GENERATION_LIMIT - 1)]


def draw(nodes: list[Node], surface: pygame.Surface):
    """Advance animation state by one frame and render to *surface*."""
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)

    # alive generations window
    max_gen = max(n.generation for n in nodes)
    min_alive_gen = max_gen - (GENERATION_LIMIT - 1)

    # update growth / fade values
    for node in nodes:
        if node.growth < 1.0:
            node.growth = min(1.0, node.growth + GROWTH_SPEED)
        if node.generation < min_alive_gen:
            node.fade = max(0.0, node.fade - FADE_SPEED)
        else:
            node.fade = 1.0

    # purge fully faded
    nodes[:] = [n for n in nodes if n.fade > 0.0]

    # background fill
    surface.fill(BG_COLOR)

    # draw edges first
    for node in nodes:
        for parent in node.parents:
            if parent in nodes:
                end_x = parent.position[0] + (node.position[0] - parent.position[0]) * node.growth
                end_y = parent.position[1] + (node.position[1] - parent.position[1]) * node.growth
                alpha = int(255 * min(node.fade, parent.fade))
                color = (*LINE_COLOR[:3], alpha)
                pygame.draw.line(overlay, color, parent.position, (end_x, end_y), 1)

    # draw nodes on top
    for node in nodes:
        if node.growth >= 1.0:
            x, y = int(node.position[0]), int(node.position[1])
            alpha = int(255 * node.fade)
            outer_color = (*NODE_OUTER_COLOR[:3], alpha)
            inner_color = (*NODE_INNER_COLOR[:3], alpha)
            pygame.gfxdraw.aacircle(overlay, x, y, NODE_RADIUS, outer_color)
            pygame.gfxdraw.filled_circle(overlay, x, y, NODE_RADIUS, outer_color)
            inner_r = int(NODE_RADIUS * INNER_FILL_PERCENT)
            if inner_r > 0:
                pygame.gfxdraw.filled_circle(overlay, x, y, inner_r, inner_color)

    surface.blit(overlay, (0, 0))


# ---------------------------------------------------------------------------
# Main driver ----------------------------------------------------------------


def main():
    # Ensure SDL runs headless (no window pops up if available)
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

    pygame.init()
    # Surface we render onto (no display window needed)
    screen = pygame.Surface((WIDTH, HEIGHT))

    # Prepare output path
    project_root = Path(__file__).resolve().parents[2]  # go up from backend/scripts/
    video_dir = project_root / "frontend" / "static" / "videos"
    video_dir.mkdir(parents=True, exist_ok=True)
    video_path = video_dir / "landing_visual.mp4"

    writer = imageio.get_writer(
        video_path,
        fps=FPS,
        codec="libx264",
        quality=8,
        macro_block_size=None,  # allow arbitrary resolution
    )

    # initial state – root node
    nodes: list[Node] = []
    root = Node(position=(WIDTH // 2, HEIGHT // 2), section=0, generation=0)
    root.growth = 1.0
    nodes.append(root)

    for frame_idx in range(TOTAL_FRAMES):
        if frame_idx % SPAWN_INTERVAL_FRAMES == 0:
            add_children(nodes)
        draw(nodes, screen)

        # Convert the pygame Surface (W,H,RGB) to (H,W,RGB) for imageio
        frame = np.transpose(pygame.surfarray.array3d(screen), (1, 0, 2))
        writer.append_data(frame)

    writer.close()
    pygame.quit()

    print(f"✓ Generated video: {video_path}  ({DURATION_SECONDS}s @ {FPS} FPS)")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Error while generating video: {exc}")
        sys.exit(1)
