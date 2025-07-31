import pygame
import pygame.gfxdraw  # for anti-aliased circles
import random
import math

# Initialize Pygame
pygame.init()
width, height = 800, 800
screen = pygame.display.set_mode((width, height))
pygame.display.set_caption("Financial Model Simulation")
clock = pygame.time.Clock()

# Simulation parameters (tweak these to taste)
# --------------------------------------------------
# How many generations (node count) to keep visible at once
GENERATION_LIMIT = 4

# Number of vertical sections for directionality
SECTION_COUNT = 10  # default sections left→right

# Current movement direction across sections: +1 (right) or -1 (left)
direction = 1

# New children spawned per parent (inclusive range)
MIN_CHILDREN = 1
MAX_CHILDREN = 10

# Random positional jitter around the parent
JITTER_DISTANCE = 80

# A safety margin so nodes don't hug the screen edges (pixels)
SCREEN_MARGIN = 60

# Visual settings
NODE_RADIUS = 6
# Color parameters
NODE_OUTER_COLOR = (50, 200, 255)   # outline / border color of node
NODE_INNER_COLOR = (0, 0, 0)        # fill color (default black)
INNER_FILL_PERCENT = 0.6            # 0→hollow, 1→solid
LINE_COLOR = (100, 100, 100)        # edge color
BG_COLOR = (10, 10, 10)

# Animation speed (0-1 growth increment per frame)
GROWTH_SPEED = 0.2  # speed at which lines grow toward children

# Frames between each generation spawn (smaller = faster)
SPAWN_INTERVAL_FRAMES = 5

# Attempts to find a non-overlapping child placement
MAX_POSITION_TRIES = 25

# Node structure
class Node:
    def __init__(self, position, section, generation, parents=None):
        if parents is None:
            parents = []
        self.position = position
        self.parents = parents
        self.age = 0
        self.section = section
        self.generation = generation
        # Growth progress for animation (0 = just born, 1 = fully grown)
        self.growth = 0.0

nodes = []

# Geometry helpers -----------------------------------------------------------

def _ccw(A, B, C):
    """Return True if the points A, B, C are listed in a counter-clockwise order."""
    return (C[1] - A[1]) * (B[0] - A[0]) > (B[1] - A[1]) * (C[0] - A[0])

def segments_intersect(p1, p2, p3, p4):
    """Return True if line segment p1→p2 intersects p3→p4 (excluding shared endpoints)."""
    # Fast rejection: If any shared endpoint, we don't consider it an intersection.
    if p1 == p3 or p1 == p4 or p2 == p3 or p2 == p4:
        return False
    return _ccw(p1, p3, p4) != _ccw(p2, p3, p4) and _ccw(p1, p2, p3) != _ccw(p1, p2, p4)

# First root node
root_node = Node(position=(width // 2, height // 2), section=0, generation=0)
root_node.growth = 1.0  # root is already visible
nodes.append(root_node)

def add_children():
    """Spawn children moving section-by-section across the screen.
    Children always appear in the adjacent section in the current
    direction (left→right or right→left). Direction flips when the
    outermost section is reached. Old nodes are pruned to
    ``GENERATION_LIMIT``.
    """
    global direction

    if not nodes:
        return

    parent = nodes[-1]
    parent_section = parent.section

    # Determine next section index, reversing at the edges
    next_section = parent_section + direction
    if next_section < 0 or next_section >= SECTION_COUNT:
        direction *= -1
        next_section = parent_section + direction

    num_children = random.randint(MIN_CHILDREN, MAX_CHILDREN)
    section_width = width / SECTION_COUNT
    left_bound = next_section * section_width
    right_bound = left_bound + section_width

    for _ in range(num_children):
        for _ in range(MAX_POSITION_TRIES):
            new_x = random.uniform(max(left_bound + SCREEN_MARGIN, left_bound),
                                   min(right_bound - SCREEN_MARGIN, right_bound))
            new_y = random.uniform(SCREEN_MARGIN, height - SCREEN_MARGIN)
            candidate_pos = (new_x, new_y)

            # Ensure the new edge does not intersect existing ones
            intersects = False
            for n in nodes:
                for p in n.parents:
                    if p not in nodes or p == parent:
                        continue
                    if segments_intersect(parent.position, candidate_pos, p.position, n.position):
                        intersects = True
                        break
                if intersects:
                    break
            if not intersects:
                break  # found valid location

        child = Node(position=candidate_pos, section=next_section, generation=parent.generation + 1, parents=[parent])
        nodes.append(child)

    # Prune by generation rather than raw node count
    max_gen = max(n.generation for n in nodes)
    nodes[:] = [n for n in nodes if n.generation >= max_gen - (GENERATION_LIMIT - 1)]

def draw():
    screen.fill(BG_COLOR)

    # Update growth animation state
    for node in nodes:
        if node.growth < 1.0:
            node.growth = min(1.0, node.growth + GROWTH_SPEED)

    # Draw connections first (animated)
    for node in nodes:
        for parent in node.parents:
            if parent in nodes:
                # Interpolate endpoint based on growth progress
                end_x = parent.position[0] + (node.position[0] - parent.position[0]) * node.growth
                end_y = parent.position[1] + (node.position[1] - parent.position[1]) * node.growth
                pygame.draw.line(screen, LINE_COLOR, parent.position, (end_x, end_y), 1)

    # Draw nodes on top once their connecting line is fully grown
    for node in nodes:
        if node.growth >= 1.0:
            x, y = int(node.position[0]), int(node.position[1])
                        # Outer circle (anti-aliased)
            pygame.gfxdraw.aacircle(screen, x, y, NODE_RADIUS, NODE_OUTER_COLOR)
            pygame.gfxdraw.filled_circle(screen, x, y, NODE_RADIUS, NODE_OUTER_COLOR)

            # Inner fill (allows hollow appearance)
            inner_r = int(NODE_RADIUS * INNER_FILL_PERCENT)
            if inner_r > 0:
                pygame.gfxdraw.filled_circle(screen, x, y, inner_r, NODE_INNER_COLOR)

running = True
frame_count = 0

while running:
    clock.tick(30)
    frame_count += 1

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    # Spawn children at configurable interval
    if frame_count % SPAWN_INTERVAL_FRAMES == 0:
        add_children()

    draw()
    pygame.display.flip()

pygame.quit()