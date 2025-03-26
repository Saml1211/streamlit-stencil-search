import os
from datetime import datetime
from tqdm import tqdm

def scan_directory(root_dir, parser_func=None):
    """
    Recursively scan directory for Visio stencils
    
    Args:
        root_dir (str): Root directory to scan
        parser_func (callable): Function to parse stencil files
        
    Returns:
        list: List of dictionaries containing stencil info
    """
    if not os.path.exists(root_dir):
        return []
        
    stencils = []
    
    # Track scan time
    scan_time = datetime.now()
    
    for root, _, files in tqdm(os.walk(root_dir), desc="Scanning directories"):
        for file in files:
            if file.lower().endswith(('.vss', '.vssx', '.vssm', '.vst', '.vstx')):
                full_path = os.path.join(root, file)
                
                # Default empty shapes list if no parser provided
                shapes = []
                if parser_func:
                    try:
                        shapes = parser_func(full_path)
                    except Exception as e:
                        print(f"Error parsing {full_path}: {str(e)}")
                
                stencils.append({
                    'path': full_path,
                    'name': os.path.splitext(file)[0],
                    'extension': os.path.splitext(file)[1],
                    'shapes': shapes,
                    'shape_count': len(shapes),
                    'last_scan': scan_time.strftime("%Y-%m-%d %H:%M:%S")
                })
    
    return stencils 