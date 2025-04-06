import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
import io
import re
import json
from matplotlib.path import Path
from .db import StencilDatabase

def get_shape_preview(stencil_path, shape_name, size=150, bg_color="#f5f5f5", shape_data=None):
    """
    Generate a preview image for a shape based on its geometry data or name

    Args:
        stencil_path (str): Path to the stencil file
        shape_name (str): Name of the shape
        size (int): Size of the square image in pixels
        bg_color (str): Background color (hex)
        shape_data (dict, optional): Pre-loaded shape data with geometry

    Returns:
        bytes: PNG image as bytes
    """
    # Create figure with transparent background
    if isinstance(size, str):
        size = 150  # Default to 150 if size is a string

    # Create a figure with a fixed aspect ratio to ensure the shape fits entirely
    fig, ax = plt.subplots(figsize=(size/100, size/100), dpi=100)
    ax.set_aspect('equal')
    # Set a consistent coordinate system for all shapes
    ax.set_xlim(-0.1, 1.1)  # Add padding to ensure shapes aren't cut off
    ax.set_ylim(-0.1, 1.1)

    # Remove axes and set background
    ax.axis('off')
    fig.patch.set_facecolor(bg_color)

    # Try to get shape data from database if not provided
    if not shape_data:
        try:
            db = StencilDatabase()
            # Get the shape data from the database
            shape_cursor = db.get_conn().execute(
                "SELECT width, height, geometry, properties FROM shapes WHERE stencil_path = ? AND name = ?",
                (stencil_path, shape_name)
            )
            shape_row = shape_cursor.fetchone()

            if shape_row and shape_row['geometry']:
                shape_data = {
                    'name': shape_name,
                    'width': shape_row['width'],
                    'height': shape_row['height'],
                    'geometry': json.loads(shape_row['geometry']) if shape_row['geometry'] else [],
                    'properties': json.loads(shape_row['properties']) if shape_row['properties'] else {}
                }
        except Exception as e:
            print(f"Error retrieving shape data: {e}")
            # Continue with name-based preview if database lookup fails

    # Check if we have geometry data to use
    if shape_data and shape_data.get('geometry'):
        # Draw shape using actual geometry data
        try:
            draw_shape_from_geometry(ax, shape_data)
        except Exception as e:
            print(f"Error drawing shape from geometry: {e}")
            # Fall back to name-based preview if geometry drawing fails
            draw_shape_from_name(ax, shape_name)
    else:
        # Fall back to name-based preview
        draw_shape_from_name(ax, shape_name)

    # Add simplified text of first few chars
    short_name = shape_name[:10] + '...' if len(shape_name) > 10 else shape_name
    ax.text(0.5, -0.1, short_name, ha='center', va='center', fontsize=10)

    # Save to bytes buffer with tight layout to ensure the entire shape is visible
    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight', pad_inches=0.1, transparent=False)
    plt.close(fig)
    buf.seek(0)

    return buf

def draw_shape_from_geometry(ax, shape_data):
    """
    Draw a shape using its geometry data

    Args:
        ax: Matplotlib axis to draw on
        shape_data: Dictionary containing shape geometry data
    """
    geometry = shape_data.get('geometry', [])
    if not geometry:
        return False

    # Process each geometry path
    for path in geometry:
        if not path:
            continue

        # Convert the path to matplotlib path format
        vertices = []
        codes = []

        for i, point in enumerate(path):
            x, y = point.get('x', 0), point.get('y', 0)

            # Normalize coordinates to 0-1 range
            # This is a simplification - in a real implementation, you'd use the shape's
            # width and height to properly scale the coordinates
            x_norm = x
            y_norm = y

            vertices.append((x_norm, y_norm))

            # Set the path code based on point type
            if point.get('type') == 'M':
                codes.append(Path.MOVETO)
            elif point.get('type') == 'L':
                codes.append(Path.LINETO)
            elif point.get('type') in ['A', 'E']:  # Arc or elliptical arc
                # This is a simplification - proper arc rendering would be more complex
                codes.append(Path.CURVE4)
            else:
                # Default to line
                codes.append(Path.LINETO)

        # Close the path if it has at least 3 points
        if len(vertices) >= 3:
            vertices.append(vertices[0])  # Add first point to close the path
            codes.append(Path.CLOSEPOLY)

        # Create and draw the path
        if vertices and codes and len(vertices) == len(codes):
            mpl_path = Path(vertices, codes)
            patch = patches.PathPatch(mpl_path, edgecolor='black', facecolor='white', linewidth=2)
            ax.add_patch(patch)

    return True

def draw_shape_from_name(ax, shape_name):
    """
    Draw a shape based on its name using predefined shapes

    Args:
        ax: Matplotlib axis to draw on
        shape_name: Name of the shape
    """
    # Normalize shape name for pattern matching
    shape_name_lower = shape_name.lower()

    if any(x in shape_name_lower for x in ['rectangle', 'square', 'box']):
        # Rectangle or square
        width = 0.7 if 'square' in shape_name_lower else 0.8
        height = 0.7 if 'square' in shape_name_lower else 0.5
        rect = patches.Rectangle((0.5-width/2, 0.5-height/2), width, height,
                               edgecolor='black', facecolor='white', linewidth=2)
        ax.add_patch(rect)

    elif any(x in shape_name_lower for x in ['circle', 'oval', 'ellipse']):
        # Circle or ellipse
        width = 0.7
        height = 0.5 if 'oval' in shape_name_lower or 'ellipse' in shape_name_lower else 0.7
        ellipse = patches.Ellipse((0.5, 0.5), width, height,
                                edgecolor='black', facecolor='white', linewidth=2)
        ax.add_patch(ellipse)

    elif any(x in shape_name_lower for x in ['triangle']):
        # Triangle
        triangle = patches.Polygon([[0.5, 0.85], [0.2, 0.2], [0.8, 0.2]],
                                  closed=True, edgecolor='black', facecolor='white', linewidth=2)
        ax.add_patch(triangle)

    elif any(x in shape_name_lower for x in ['pentagon']):
        # Pentagon
        angles = np.linspace(0, 2*np.pi, 6)[:-1]  # 5 points
        pentagon = patches.Polygon([[0.5 + 0.4*np.cos(a), 0.5 + 0.4*np.sin(a)] for a in angles],
                                  closed=True, edgecolor='black', facecolor='white', linewidth=2)
        ax.add_patch(pentagon)

    elif any(x in shape_name_lower for x in ['hexagon']):
        # Hexagon
        angles = np.linspace(0, 2*np.pi, 7)[:-1]  # 6 points
        hexagon = patches.Polygon([[0.5 + 0.4*np.cos(a), 0.5 + 0.4*np.sin(a)] for a in angles],
                                 closed=True, edgecolor='black', facecolor='white', linewidth=2)
        ax.add_patch(hexagon)

    elif any(x in shape_name_lower for x in ['star']):
        # Star
        angles = np.linspace(0, 2*np.pi, 11)[:-1]  # 5 points * 2 radii
        radii = [0.4, 0.2] * 5
        star_points = [[0.5 + r*np.cos(a), 0.5 + r*np.sin(a)] for r, a in zip(radii, angles)]
        star = patches.Polygon(star_points, closed=True, edgecolor='black', facecolor='white', linewidth=2)
        ax.add_patch(star)

    elif any(x in shape_name_lower for x in ['diamond']):
        # Diamond
        diamond = patches.Polygon([[0.5, 0.9], [0.9, 0.5], [0.5, 0.1], [0.1, 0.5]],
                                closed=True, edgecolor='black', facecolor='white', linewidth=2)
        ax.add_patch(diamond)

    elif any(x in shape_name_lower for x in ['arrow']):
        # Arrow
        arrow = patches.FancyArrow(0.2, 0.5, 0.6, 0, width=0.15, head_width=0.3,
                                 head_length=0.2, edgecolor='black', facecolor='white', linewidth=2)
        ax.add_patch(arrow)

    elif any(x in shape_name_lower for x in ['cloud']):
        # Cloud (simplified)
        cloud_path = Path([
            (0.3, 0.45), (0.2, 0.5), (0.25, 0.6), (0.35, 0.65),
            (0.45, 0.7), (0.6, 0.7), (0.7, 0.65), (0.75, 0.55),
            (0.8, 0.45), (0.7, 0.35), (0.6, 0.35), (0.5, 0.3),
            (0.4, 0.35), (0.3, 0.45)
        ])
        cloud = patches.PathPatch(cloud_path, edgecolor='black', facecolor='white', linewidth=2)
        ax.add_patch(cloud)

    elif any(x in shape_name_lower for x in ['database', 'cylinder']):
        # Database cylinder
        cylinder_body = patches.Rectangle((0.3, 0.25), 0.4, 0.5, edgecolor='black', facecolor='white', linewidth=2)
        top_ellipse = patches.Ellipse((0.5, 0.75), 0.4, 0.15, edgecolor='black', facecolor='white', linewidth=2)
        bottom_ellipse = patches.Ellipse((0.5, 0.25), 0.4, 0.15, edgecolor='black', facecolor='white', linewidth=2)
        ax.add_patch(cylinder_body)
        ax.add_patch(top_ellipse)
        ax.add_patch(bottom_ellipse)

    elif any(x in shape_name_lower for x in ['server', 'computer']):
        # Server/Computer
        server = patches.Rectangle((0.25, 0.25), 0.5, 0.5, edgecolor='black', facecolor='white', linewidth=2)
        slots = [patches.Rectangle((0.35, 0.65-i*0.1), 0.3, 0.05, edgecolor='black', facecolor='#eeeeee', linewidth=1)
                for i in range(3)]
        ax.add_patch(server)
        for slot in slots:
            ax.add_patch(slot)

    elif any(x in shape_name_lower for x in ['router', 'switch']):
        # Network device
        router = patches.Rectangle((0.2, 0.35), 0.6, 0.3, edgecolor='black', facecolor='white', linewidth=2)
        ax.add_patch(router)
        # Add small LEDs
        for i in range(4):
            led = patches.Circle((0.3 + i*0.15, 0.45), 0.03, color='green')
            ax.add_patch(led)

    elif any(x in shape_name_lower for x in ['person', 'user', 'actor']):
        # Person/Actor
        head = patches.Circle((0.5, 0.7), 0.1, edgecolor='black', facecolor='white', linewidth=2)
        body = patches.Polygon([[0.5, 0.6], [0.3, 0.3], [0.7, 0.3]],
                             closed=True, edgecolor='black', facecolor='white', linewidth=2)
        ax.add_patch(head)
        ax.add_patch(body)

    elif any(x in shape_name_lower for x in ['document', 'file', 'page']):
        # Document
        doc = patches.Rectangle((0.25, 0.2), 0.5, 0.6, edgecolor='black', facecolor='white', linewidth=2)
        fold = patches.Polygon([[0.75, 0.2], [0.75, 0.3], [0.65, 0.2]],
                             closed=True, edgecolor='black', facecolor='#eeeeee', linewidth=2)
        ax.add_patch(doc)
        ax.add_patch(fold)

    else:
        # Default shape (generic box with text)
        rect = patches.Rectangle((0.2, 0.2), 0.6, 0.6,
                               edgecolor='black', facecolor='white', linewidth=2)
        ax.add_patch(rect)

    return True