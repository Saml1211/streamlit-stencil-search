import zipfile
import xml.etree.ElementTree as ET
import os
import json
import base64
import io
from typing import List, Dict, Any, Optional, Tuple

def parse_visio_stencil(file_path):
    """
    Extract shape information from Visio stencil files without using Visio

    Args:
        file_path (str): Path to the Visio stencil file

    Returns:
        list: List of shape dictionaries with name, geometry, and metadata
    """
    shapes = []

    file_ext = os.path.splitext(file_path)[1].lower()

    # Modern XML-based formats
    if file_ext in ['.vssx', '.vstx', '.vsdx']:
        try:
            with zipfile.ZipFile(file_path) as zip_file:
                # Check if masters.xml exists
                if 'visio/masters/masters.xml' in zip_file.namelist():
                    # Get the list of files in the archive
                    file_list = zip_file.namelist()

                    # Parse the masters.xml file
                    with zip_file.open('visio/masters/masters.xml') as masters_file:
                        tree = ET.parse(masters_file)
                        root = tree.getroot()

                        # XML namespace handling
                        ns = {'v': 'http://schemas.microsoft.com/office/visio/2012/main'}

                        # Extract master information
                        for master in root.findall('.//v:Master', ns):
                            # Get master ID and name
                            master_id = master.get('ID', '')
                            name_elem = master.find('.//v:Text', ns)

                            # Get the name from the Text element or NameU attribute
                            if name_elem is not None and name_elem.text:
                                name = name_elem.text.strip()
                            else:
                                name = master.get('NameU', '')

                            if not name:
                                continue

                            # Initialize shape data dictionary
                            shape_data = {
                                'name': name,
                                'id': master_id,
                                'width': 0,
                                'height': 0,
                                'geometry': [],
                                'properties': {}
                            }

                            # Look for geometry data in the master's XML
                            try:
                                # Check for shape geometry in master_#.xml files
                                master_file = f"visio/masters/master_{master_id}.xml"
                                if master_file in file_list:
                                    with zip_file.open(master_file) as shape_file:
                                        shape_tree = ET.parse(shape_file)
                                        shape_root = shape_tree.getroot()

                                        # Extract shape dimensions
                                        width_elem = shape_root.find('.//v:Cell[@N="Width"]', ns)
                                        height_elem = shape_root.find('.//v:Cell[@N="Height"]', ns)

                                        if width_elem is not None:
                                            shape_data['width'] = float(width_elem.get('V', '0'))
                                        if height_elem is not None:
                                            shape_data['height'] = float(height_elem.get('V', '0'))

                                        # Extract geometry data
                                        geometry = extract_geometry(shape_root, ns)
                                        if geometry:
                                            shape_data['geometry'] = geometry

                                        # Extract custom properties
                                        props = extract_properties(shape_root, ns)
                                        if props:
                                            shape_data['properties'] = props
                            except Exception as geom_error:
                                print(f"Error extracting geometry for {name} in {file_path}: {str(geom_error)}")
                                # Continue with basic shape data even if geometry extraction fails

                            # Add the shape data to our list
                            shapes.append(shape_data)
        except Exception as e:
            print(f"Error parsing XML-based file {file_path}: {str(e)}")
            shapes.append({"name": f"[Error: {str(e)}]", "id": "", "width": 0, "height": 0, "geometry": [], "properties": {}})

    # Legacy binary formats - placeholder for future implementation
    elif file_ext in ['.vss', '.vst', '.vsd']:
        # Legacy formats would require a more complex parser or external library
        shapes.append({"name": f"[Binary format not supported: {os.path.basename(file_path)}]", "id": "", "width": 0, "height": 0, "geometry": [], "properties": {}})

    return shapes

def extract_geometry(shape_root, ns):
    """
    Extract geometry data from a shape XML element

    Args:
        shape_root: XML root element of the shape
        ns: XML namespaces

    Returns:
        list: List of geometry paths
    """
    geometry = []

    # Find all geometry sections
    geom_sections = shape_root.findall('.//v:Section[@N="Geometry"]', ns)

    for section in geom_sections:
        path = []

        # Get all rows in this geometry section
        rows = section.findall('./v:Row', ns)

        for row in rows:
            row_type = row.get('T', '')

            # Extract X and Y coordinates
            x_cell = row.find('./v:Cell[@N="X"]', ns)
            y_cell = row.find('./v:Cell[@N="Y"]', ns)

            if x_cell is not None and y_cell is not None:
                x = float(x_cell.get('V', '0'))
                y = float(y_cell.get('V', '0'))

                # Different handling based on row type
                if row_type == 'MoveTo':
                    path.append({'type': 'M', 'x': x, 'y': y})
                elif row_type == 'LineTo':
                    path.append({'type': 'L', 'x': x, 'y': y})
                elif row_type == 'ArcTo':
                    # For arcs, we also need the arc parameters
                    a_cell = row.find('./v:Cell[@N="A"]', ns)
                    b_cell = row.find('./v:Cell[@N="B"]', ns)
                    c_cell = row.find('./v:Cell[@N="C"]', ns)
                    d_cell = row.find('./v:Cell[@N="D"]', ns)

                    a = float(a_cell.get('V', '0')) if a_cell is not None else 0
                    b = float(b_cell.get('V', '0')) if b_cell is not None else 0
                    c = float(c_cell.get('V', '0')) if c_cell is not None else 0
                    d = float(d_cell.get('V', '0')) if d_cell is not None else 0

                    path.append({'type': 'A', 'x': x, 'y': y, 'a': a, 'b': b, 'c': c, 'd': d})
                elif row_type == 'EllipticalArcTo':
                    # For elliptical arcs
                    a_cell = row.find('./v:Cell[@N="A"]', ns)
                    b_cell = row.find('./v:Cell[@N="B"]', ns)
                    c_cell = row.find('./v:Cell[@N="C"]', ns)
                    d_cell = row.find('./v:Cell[@N="D"]', ns)

                    a = float(a_cell.get('V', '0')) if a_cell is not None else 0
                    b = float(b_cell.get('V', '0')) if b_cell is not None else 0
                    c = float(c_cell.get('V', '0')) if c_cell is not None else 0
                    d = float(d_cell.get('V', '0')) if d_cell is not None else 0

                    path.append({'type': 'E', 'x': x, 'y': y, 'a': a, 'b': b, 'c': c, 'd': d})

        if path:
            geometry.append(path)

    return geometry

def extract_properties(shape_root, ns):
    """
    Extract custom properties from a shape XML element

    Args:
        shape_root: XML root element of the shape
        ns: XML namespaces

    Returns:
        dict: Dictionary of property name-value pairs
    """
    properties = {}

    # Find all property sections
    prop_sections = shape_root.findall('.//v:Section[@N="Property"]', ns)

    for section in prop_sections:
        # Get all rows in this property section
        rows = section.findall('./v:Row', ns)

        for row in rows:
            # Get property name and value
            label_cell = row.find('./v:Cell[@N="Label"]', ns)
            value_cell = row.find('./v:Cell[@N="Value"]', ns)

            if label_cell is not None and value_cell is not None:
                label = label_cell.get('V', '')
                value = value_cell.get('V', '')

                if label:
                    properties[label] = value

    # Also look for standard properties like Creator, Description, etc.
    std_props = shape_root.findall('.//v:Prop', ns)

    for prop in std_props:
        name = prop.get('Name', '')
        value = prop.get('Value', '')

        if name and value:
            properties[name] = value

    return properties