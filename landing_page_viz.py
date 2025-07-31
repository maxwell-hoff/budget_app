import pygame
import random
import math

# Initialize Pygame
pygame.init()
width, height = 800, 600
screen = pygame.display.set_mode((width, height))
pygame.display.set_caption("Financial Model Simulation")
clock = pygame.time.Clock()

# Node settings
# How many generations to keep visible at once
GENERATION_LIMIT = 3
NODE_RADIUS = 6
NODE_COLOR = (50, 200, 255)
LINE_COLOR = (100, 100, 100)
BG_COLOR = (10, 10, 10)

# Node structure
class Node:
    def __init__(self, position, parents=[]):
        self.position = position
        self.parents = parents
        self.age = 0

nodes = []

# First root node
root_node = Node(position=(width // 2, height // 2))
nodes.append(root_node)

def add_node():
    """Create a new node that branches from the *most recently* created node
    and prune any nodes that are older than ``GENERATION_LIMIT`` generations.
    """
    if not nodes:
        return

    # Always branch from the node that was most recently created
    parent = nodes[-1]

    # Jitter new node's position slightly around its parent while keeping it on-screen
    jitter = lambda: random.uniform(-80, 80)
    new_x = max(0, min(width, parent.position[0] + jitter()))
    new_y = max(0, min(height, parent.position[1] + jitter()))
    new_node = Node(position=(new_x, new_y), parents=[parent])

    # Append the new node to the end of the list (newest generation)
    nodes.append(new_node)

    # Remove nodes older than our generation limit
    while len(nodes) > GENERATION_LIMIT:
        nodes.pop(0)

def draw():
    screen.fill(BG_COLOR)

    # Draw connections first
    for node in nodes:
        for parent in node.parents:
            # Only draw a connection if the parent is still visible on screen
            if parent in nodes:
                pygame.draw.line(screen, LINE_COLOR, node.position, parent.position, 1)

    # Draw nodes on top
    for node in nodes:
        pygame.draw.circle(screen, NODE_COLOR, (int(node.position[0]), int(node.position[1])), NODE_RADIUS)

running = True
frame_count = 0

while running:
    clock.tick(30)
    frame_count += 1

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    # Add a node every 15 frames
    if frame_count % 15 == 0:
        add_node()

    draw()
    pygame.display.flip()

pygame.quit()