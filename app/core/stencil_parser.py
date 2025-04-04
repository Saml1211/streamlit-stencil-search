import zipfile
import xml.etree.ElementTree as ET
import os

def parse_visio_stencil(file_path):
    """
    Extract shape names from Visio stencil files without using Visio
    
    Args:
        file_path (str): Path to the Visio stencil file
        
    Returns:
        list: List of shape names
    """
    shapes = []
    
    file_ext = os.path.splitext(file_path)[1].lower()
    
    # Modern XML-based formats
    if file_ext in ['.vssx', '.vstx', '.vsdx']:
        try:
            with zipfile.ZipFile(file_path) as zip_file:
                # Check if masters.xml exists
                if 'visio/masters/masters.xml' in zip_file.namelist():
                    with zip_file.open('visio/masters/masters.xml') as masters_file:
                        tree = ET.parse(masters_file)
                        root = tree.getroot()
                        
                        # XML namespace handling
                        ns = {'v': 'http://schemas.microsoft.com/office/visio/2012/main'}
                        
                        # Extract master names
                        for master in root.findall('.//v:Master', ns):
                            name_elem = master.find('.//v:Text', ns)
                            if name_elem is not None and name_elem.text:
                                shapes.append(name_elem.text.strip())
                            else:
                                # Fallback to name attribute
                                name = master.get('NameU', '')
                                if name:
                                    shapes.append(name)
        except Exception as e:
            print(f"Error parsing XML-based file {file_path}: {str(e)}")
    
    # Legacy binary formats - placeholder for future implementation
    elif file_ext in ['.vss', '.vst', '.vsd']:
        # Legacy formats would require a more complex parser or external library
        shapes.append(f"[Binary format not supported: {os.path.basename(file_path)}]")
    
    return shapes 