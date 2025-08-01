import bpy
import random
from mathutils import Vector

"""
Blender version of the landing page visualisation originally implemented with
pygame.  Run inside Blender:

    blender --python landing_page_viz_blender.py

The script builds the same expanding node-graph animation on the X-Y plane.  A
handler hooked to frame changes spawns new generations every
``SPAWN_INTERVAL_FRAMES`` and prunes old ones to keep memory usage under
control.
"""  

# ----------------------------------------------------------------------------
# --- Simulation parameters (kept in sync with the pygame implementation) ---
# ----------------------------------------------------------------------------
WIDTH, HEIGHT = 5, 5                 # virtual canvas size (pixels)
GENERATION_LIMIT = 5                    # how many generations stay visible
SECTION_COUNT = 10                       # vertical screen sections
MIN_CHILDREN, MAX_CHILDREN = 1, 10         # children spawned per generation
SCREEN_MARGIN = 60                       # margin from screen edges
SPAWN_INTERVAL_FRAMES = 15                # blender frames between spawns
MAX_POSITION_TRIES = 25                  # placement retries to avoid overlap

# Visual tuning
SCALE = 1                             # blender units per pixel (0.01 → 8x8)
NODE_RADIUS = 1                       # sphere radius in blender units
LINE_RADIUS = 0.1                      # cylinder radius for the edges

# Light animation along edges
LIGHT_TRAVEL_FRAMES = 15              # frames for a light to travel parent→child
LIGHT_STAY_FRAMES = 15                # frames the light remains at the node
LIGHT_FADE_FRAMES = 10                # frames it takes to fade out
LIGHT_ENERGY = 1000                   # initial light energy (strength)
LIGHT_SIZE = 1                        # light radius

# Node appearance
NODE_COLOR = (0.0, 0.8, 0.0, 1.0)      # default green RGBA

# -----------------------------------------------------------------------------
# Material utilities -----------------------------------------------------------
# -----------------------------------------------------------------------------
_EDGE_MATERIAL = None  # cached grey material for cylinders
_NODE_MATERIAL = None  # cached green material for spheres


def _get_node_material():
    """Create (once) and return the material used by every node sphere."""
    global _NODE_MATERIAL
    if _NODE_MATERIAL is None:
        mat = bpy.data.materials.new("NodeGreen")
        mat.use_nodes = True
        bsdf = mat.node_tree.nodes.get("Principled BSDF")
        bsdf.inputs["Base Color"].default_value = NODE_COLOR
        bsdf.inputs["Emission"].default_value = NODE_COLOR
        bsdf.inputs["Emission Strength"].default_value = 0.0
        _NODE_MATERIAL = mat
    return _NODE_MATERIAL


def _flash_material(mat, frame, emission_strength=10.0):
    """Insert keyframes so `mat` emits a flash at `frame`."""
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    inp = bsdf.inputs["Emission Strength"]
    inp.default_value = emission_strength
    inp.keyframe_insert(data_path="default_value", frame=frame)
    inp.default_value = 0.0
    inp.keyframe_insert(data_path="default_value", frame=frame + LIGHT_FADE_FRAMES)


def _get_edge_material():
    """Create (once) and return a neutral grey material for edges."""
    global _EDGE_MATERIAL
    if _EDGE_MATERIAL is None:
        mat = bpy.data.materials.new("EdgeGrey")
        mat.use_nodes = True
        bsdf = mat.node_tree.nodes.get("Principled BSDF")
        bsdf.inputs["Base Color"].default_value = (0.5, 0.5, 0.5, 1)
        _EDGE_MATERIAL = mat
    return _EDGE_MATERIAL

# ----------------------------------------------------------------------------
# ------------------------------ Data model ----------------------------------
# ----------------------------------------------------------------------------
class Node:
    """A minimal representation of a node in the graph."""

    def __init__(self, position, section, generation, parents=None):
        self.position = position                    # (x_pixel, y_pixel)
        self.section = section                      # vertical section index
        self.generation = generation                # generation depth
        self.parents = parents if parents else []   # list[Node]

        # Blender objects corresponding to this node
        self.sphere_obj = None                      # the visible sphere
        self.edge_objs = []                         # list of cylinders to parents


# Global simulation state -----------------------------------------------------
nodes = []                           # every live node
_direction = {"dir": 1}              # mutable container so closure can mutate


# Utility converters ----------------------------------------------------------

def pixel_to_world(pt):
    """Convert 2-D pixel coordinates to Blender world space (XY plane, Z=0)."""
    x, y = pt
    return Vector(((x - WIDTH / 2) * SCALE, (y - HEIGHT / 2) * SCALE, 0))


# Scene helpers ---------------------------------------------------------------

def clear_scene():
    """Delete every mesh object currently present (keeps cameras/lights)."""
    bpy.ops.object.select_all(action="DESELECT")
    for obj in bpy.data.objects:
        if obj.type == "MESH":
            obj.select_set(True)
    bpy.ops.object.delete()


def add_sphere(node: Node):
    """Create a UV-sphere for **node** at the correct position.
    Uses a low-poly sphere for performance and applies the shared green material
    with a brief emission flash.
    """
    loc = pixel_to_world(node.position)
    bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=8, radius=NODE_RADIUS, location=loc)
    node.sphere_obj = bpy.context.object

    # Material
    mat = _get_node_material()
    if node.sphere_obj.data.materials:
        node.sphere_obj.data.materials[0] = mat
    else:
        node.sphere_obj.data.materials.append(mat)

    # Flash
    _flash_material(mat, bpy.context.scene.frame_current)


def add_edge(parent: Node, child: Node):
    """Add a cylinder between *parent* and *child* (oriented end-to-end)."""
    p1 = pixel_to_world(parent.position)
    p2 = pixel_to_world(child.position)

    vec = p2 - p1
    length = vec.length
    mid = p1 + vec * 0.5

    # Cylinder created aligned to +Z; rotate so +Z aligns to vec
    bpy.ops.mesh.primitive_cylinder_add(vertices=12, radius=LINE_RADIUS, depth=length, location=mid)
    cyl = bpy.context.object

    # Align the cylinder with the edge vector
    cyl.rotation_mode = "QUATERNION"
    z_axis = Vector((0, 0, 1))
    cyl.rotation_quaternion = z_axis.rotation_difference(vec.normalized())

    # Edge material (shared)
    mat_edge = _get_edge_material()
    if cyl.data.materials:
        cyl.data.materials[0] = mat_edge
    else:
        cyl.data.materials.append(mat_edge)

    # ----- Animated light travelling along the edge -----
    current_frame = bpy.context.scene.frame_current
    light_data = bpy.data.lights.new(name="EdgeLight", type='POINT')
    light_data.energy = LIGHT_ENERGY
    light_data.shadow_soft_size = LIGHT_SIZE
    light_obj = bpy.data.objects.new("EdgeLight", light_data)
    bpy.context.collection.objects.link(light_obj)

    # Start at parent
    light_obj.location = p1
    light_obj.keyframe_insert(data_path="location", frame=current_frame)
    light_data.keyframe_insert(data_path="energy", frame=current_frame)

    # Travel to child
    arrival_frame = current_frame + LIGHT_TRAVEL_FRAMES
    final_pos = p2 - norm * NODE_RADIUS * 0.8  # stop just before entering sphere
    light_obj.location = final_pos
    light_obj.keyframe_insert(data_path="location", frame=arrival_frame)
    light_data.keyframe_insert(data_path="energy", frame=arrival_frame)  # still full energy

    # Stay bright at the node for a while
    stay_frame = arrival_frame + LIGHT_STAY_FRAMES
    light_data.keyframe_insert(data_path="energy", frame=stay_frame)

    # Fade out
    fade_frame = stay_frame + LIGHT_FADE_FRAMES
    light_data.energy = 0
    light_data.keyframe_insert(data_path="energy", frame=fade_frame)

    child.edge_objs.extend([cyl, light_obj])


# Core algorithm --------------------------------------------------------------

def add_children():
    """Spawn a new generation based on the last inserted node."""
    if not nodes:
        return

    parent = nodes[-1]
    parent_section = parent.section
    next_section = parent_section + _direction["dir"]

    if next_section < 0 or next_section >= SECTION_COUNT:
        _direction["dir"] *= -1
        next_section = parent_section + _direction["dir"]

    # Horizontal slice for the new nodes
    section_width = WIDTH / SECTION_COUNT
    left_bound = next_section * section_width
    right_bound = left_bound + section_width

    num_children = random.randint(MIN_CHILDREN, MAX_CHILDREN)

    for _ in range(num_children):
        # Pick a random, non-overlapping location (no intersection test simplification)
        for _ in range(MAX_POSITION_TRIES):
            new_x = random.uniform(max(left_bound + SCREEN_MARGIN, left_bound),
                                   min(right_bound - SCREEN_MARGIN, right_bound))
            new_y = random.uniform(SCREEN_MARGIN, HEIGHT - SCREEN_MARGIN)
            candidate = (new_x, new_y)
            break  # Skip segment-intersection test for brevity

        child = Node(position=candidate, section=next_section,
                      generation=parent.generation + 1, parents=[parent])
        add_sphere(child)
        add_edge(parent, child)
        nodes.append(child)

    # Prune old generations to keep the scene light-weight
    max_gen = max(n.generation for n in nodes)
    obsolete = [n for n in nodes if n.generation < max_gen - (GENERATION_LIMIT - 1)]

    bpy.ops.object.select_all(action="DESELECT")
    for n in obsolete:
        if n.sphere_obj:
            n.sphere_obj.select_set(True)
        for edge in n.edge_objs:
            edge.select_set(True)
    if obsolete:
        bpy.ops.object.delete()
        nodes[:] = [n for n in nodes if n not in obsolete]


# Animation handler -----------------------------------------------------------

def frame_change_handler(scene):
    frame = scene.frame_current
    if frame % SPAWN_INTERVAL_FRAMES == 0:
        add_children()


# Registration helpers --------------------------------------------------------

def register_handler():
    # Remove previously registered handler with the same name to avoid duplicates
    handlers = bpy.app.handlers.frame_change_post
    for h in list(handlers):
        if getattr(h, "__name__", "") == "frame_change_handler":
            handlers.remove(h)
    handlers.append(frame_change_handler)


# Entry-point -----------------------------------------------------------------

def main():
    clear_scene()

    # Root node at the centre
    root = Node(position=(WIDTH // 2, HEIGHT // 2), section=0, generation=0)
    add_sphere(root)
    nodes.append(root)

    register_handler()
    print("Landing-page Blender visualisation initialised (press play to watch)")


if __name__ == "__main__":
    main()
