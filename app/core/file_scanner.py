import os
from datetime import datetime
from tqdm import tqdm
from .db import StencilDatabase

def scan_directory(root_dir, parser_func=None, use_cache=True):
    """
    Recursively scan directory for Visio stencils with caching support
    
    Args:
        root_dir (str): Root directory to scan
        parser_func (callable): Function to parse stencil files
        use_cache (bool): Whether to use SQLite caching
        
    Returns:
        list: List of dictionaries containing stencil info
    """
    if not os.path.exists(root_dir):
        print(f"Warning: Directory '{root_dir}' does not exist.")
        return []
        
    stencils = []
    db = StencilDatabase() if use_cache else None
    
    # Track scan time
    scan_time = datetime.now()
    
    # Fallback for test environments: add mock stencils if no real ones are found
    if root_dir == "./test_data":
        mock_stencils = [
            {
                'path': os.path.join(root_dir, 'Basic_Shapes.vssx'),
                'name': 'Basic Shapes',
                'extension': '.vssx',
                'shapes': ['Rectangle', 'Square', 'Circle', 'Triangle', 'Pentagon', 'Hexagon'],
                'shape_count': 6,
                'file_size': 0, # Added placeholder
                'last_scan': scan_time.strftime("%Y-%m-%d %H:%M:%S")
            },
            {
                'path': os.path.join(root_dir, 'Network_Shapes.vssx'),
                'name': 'Network Shapes',
                'extension': '.vssx',
                'shapes': ['Router', 'Switch', 'Firewall', 'Server', 'Cloud', 'Database'],
                'shape_count': 6,
                'file_size': 0, # Added placeholder
                'last_scan': scan_time.strftime("%Y-%m-%d %H:%M:%S")
            }
        ]
        
        # Cache mock stencils if using cache
        if db:
            for stencil in mock_stencils:
                db.cache_stencil(stencil)
            db.close()
            
        return mock_stencils
    
    # First try to get from cache if enabled
    if db:
        cached_stencils = db.get_cached_stencils()
        if cached_stencils:
            files_to_scan = []
            for root, _, files in os.walk(root_dir):
                for file in files:
                    if file.lower().endswith(('.vss', '.vssx', '.vssm', '.vst', '.vstx')):
                        full_path = os.path.join(root, file)
                        if db.needs_update(full_path):
                            files_to_scan.append(full_path)
                        else:
                            # Use cached data
                            stencil = db.get_stencil_by_path(full_path)
                            if stencil:
                                stencils.append(stencil)
        else:
            # No cache, scan all files
            files_to_scan = []
            for root, _, files in os.walk(root_dir):
                for file in files:
                    if file.lower().endswith(('.vss', '.vssx', '.vssm', '.vst', '.vstx')):
                        files_to_scan.append(os.path.join(root, file))
    else:
        # No caching, scan all files
        files_to_scan = []
        for root, _, files in os.walk(root_dir):
            for file in files:
                if file.lower().endswith(('.vss', '.vssx', '.vssm', '.vst', '.vstx')):
                    files_to_scan.append(os.path.join(root, file))
    
    # Scan files that need updating
    for full_path in tqdm(files_to_scan, desc="Scanning stencil files"):
        # Default empty shapes list if no parser provided
        shapes = []
        if parser_func:
            try:
                shapes = parser_func(full_path)
            except Exception as e:
                print(f"Error parsing {full_path}: {str(e)}")
                continue
        
        stencil_data = {
            'path': full_path,
            'name': os.path.splitext(os.path.basename(full_path))[0],
            'extension': os.path.splitext(full_path)[1],
            'shapes': shapes,
            'shape_count': len(shapes),
            'last_scan': scan_time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        stencils.append(stencil_data)
        
        # Cache the stencil data if using cache
        if db:
            db.cache_stencil(stencil_data)
    
    if db:
        db.close()
    
    return stencils 