#!/usr/bin/env python
# Test script for the Stencil Database functionality

import os
import sys
import logging
import tempfile
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List
import time
import random
import string

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import the database module
from app.core.db import StencilDatabase

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("db_test")

def test_db_connection():
    """Test database connection and creation"""
    logger.info("Testing database connection...")
    
    # Test database initialization
    db = StencilDatabase()
    logger.info(f"Database initialized at: {db.db_path}")
    
    return db

def test_preset_directories(db: StencilDatabase):
    """Test preset directories CRUD operations"""
    logger.info("Testing preset directories functionality...")
    
    # Add test directories
    test_dir1 = os.path.join(os.getcwd(), "test_data")
    test_dir2 = os.path.join(os.getcwd(), "data")
    
    # Create
    logger.info("Adding preset directories...")
    db.add_preset_directory(test_dir1, "Test Directory 1")
    db.add_preset_directory(test_dir2, "Test Directory 2")
    
    # Read
    logger.info("Reading preset directories...")
    directories = db.get_preset_directories()
    logger.info(f"Found {len(directories)} preset directories:")
    for directory in directories:
        logger.info(f"  - ID: {directory['id']}, Path: {directory['path']}, Name: {directory['name']}")
    
    # Set active
    if directories:
        dir_id = directories[0]['id']
        logger.info(f"Setting directory ID {dir_id} as active...")
        db.set_active_directory(dir_id)
        
        # Verify active directory
        active_dir = db.get_active_directory()
        if active_dir:
            logger.info(f"Active directory: {active_dir['path']}")
        else:
            logger.error("Failed to get active directory")
    
    # Delete
    if len(directories) > 1:
        dir_id = directories[1]['id']
        logger.info(f"Removing directory with ID {dir_id}...")
        db.remove_preset_directory(dir_id)
        
        # Verify removal
        updated_dirs = db.get_preset_directories()
        logger.info(f"Directory count after removal: {len(updated_dirs)}")
    
    return directories

def test_stencil_caching(db: StencilDatabase):
    """Test stencil caching operations"""
    logger.info("Testing stencil caching functionality...")
    
    # Create a temporary file to use for testing
    try:
        # Create temp directory if it doesn't exist
        temp_dir = os.path.join(os.getcwd(), "temp")
        os.makedirs(temp_dir, exist_ok=True)
        
        # Create a temporary file
        temp_file_path = os.path.join(temp_dir, "test_stencil.vssx")
        with open(temp_file_path, 'w') as f:
            f.write("This is a test stencil file")
        
        logger.info(f"Created temporary test file at: {temp_file_path}")
        
        # Create a test stencil data structure using the real file path
        test_stencil = {
            "path": temp_file_path,
            "name": "Test Stencil",
            "extension": ".vssx",
            "shape_count": 5,
            "shapes": ["Shape1", "Shape2", "Shape3", "Shape4", "Shape5"]
        }
        
        # Cache the stencil
        logger.info(f"Caching test stencil: {test_stencil['name']}...")
        db.cache_stencil(test_stencil)
        
        # Retrieve the stencil
        logger.info("Retrieving test stencil...")
        retrieved_stencil = db.get_stencil_by_path(test_stencil["path"])
        
        if retrieved_stencil:
            logger.info(f"Retrieved stencil: {retrieved_stencil['name']}")
            logger.info(f"Shape count: {retrieved_stencil['shape_count']}")
            logger.info(f"Shapes: {', '.join(retrieved_stencil['shapes'])}")
        else:
            logger.error("Failed to retrieve test stencil")
        
        # Get all cached stencils
        logger.info("Retrieving all cached stencils...")
        all_stencils = db.get_cached_stencils()
        logger.info(f"Found {len(all_stencils)} cached stencils")
        
        # Test needs_update function
        logger.info("Testing needs_update function...")
        needs_update = db.needs_update(temp_file_path)
        logger.info(f"Stencil needs update: {needs_update}")
        
        return all_stencils
    
    finally:
        # Clean up the temporary file
        try:
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
                logger.info(f"Removed temporary test file: {temp_file_path}")
        except Exception as e:
            logger.error(f"Failed to remove temporary file: {str(e)}")

def test_saved_searches(db: StencilDatabase):
    """Test saved searches functionality"""
    logger.info("Testing saved searches functionality...")
    
    # Add test saved searches
    search1_name = "Basic Search"
    search1_term = "basic"
    search1_filters = {
        "extensions": [".vssx", ".vss"],
        "min_shapes": 1,
        "max_shapes": 100
    }
    
    # Create
    logger.info(f"Adding saved search: {search1_name}...")
    db.add_saved_search(search1_name, search1_term, search1_filters)
    
    # Read
    logger.info("Retrieving saved searches...")
    saved_searches = db.get_saved_searches()
    logger.info(f"Found {len(saved_searches)} saved searches:")
    for search in saved_searches:
        logger.info(f"  - ID: {search['id']}, Name: {search['name']}, Term: {search['search_term']}")
    
    # Delete (if we have searches)
    if saved_searches:
        search_id = saved_searches[0]['id']
        logger.info(f"Deleting saved search with ID {search_id}...")
        db.delete_saved_search(search_id)
        
        # Verify deletion
        updated_searches = db.get_saved_searches()
        logger.info(f"Saved search count after deletion: {len(updated_searches)}")
    
    return saved_searches

def test_favorites(db: StencilDatabase):
    """Test favorites functionality"""
    logger.info("Testing favorites functionality...")
    
    # Create a temporary stencil file for testing
    temp_dir = os.path.join(os.getcwd(), "temp")
    os.makedirs(temp_dir, exist_ok=True)
    temp_file_path = os.path.join(temp_dir, "favorite_test.vssx")
    
    try:
        # Create temp file
        with open(temp_file_path, 'w') as f:
            f.write("Test stencil for favorites")
        
        # First, cache the stencil in the stencils table
        test_stencil = {
            "path": temp_file_path,
            "name": "Favorite Test Stencil",
            "extension": ".vssx",
            "shape_count": 3,
            "shapes": ["FavShape1", "FavShape2", "FavShape3"]
        }
        logger.info(f"Caching test stencil for favorites: {test_stencil['name']}...")
        db.cache_stencil(test_stencil)
        
        # Add favorite stencil
        logger.info(f"Adding favorite stencil: {temp_file_path}")
        db.add_favorite_stencil(temp_file_path)
        
        # Check if stencil is in favorites
        is_favorite = db.is_favorite_stencil(temp_file_path)
        logger.info(f"Is stencil a favorite? {is_favorite}")
        
        # Get all favorites
        favorites = db.get_favorites()
        logger.info(f"Found {len(favorites)} favorites")
        for fav in favorites:
            logger.info(f"  - ID: {fav.get('id')}, Type: {fav.get('item_type')}, Path: {fav.get('stencil_path')}")
        
        # Remove favorite
        if favorites:
            logger.info(f"Removing favorite stencil: {temp_file_path}")
            db.remove_favorite_stencil(temp_file_path)
            
            # Verify removal
            updated_favorites = db.get_favorites()
            logger.info(f"Favorites count after removal: {len(updated_favorites)}")
        
        return favorites
    
    finally:
        # Clean up the temporary file
        try:
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
                logger.info(f"Removed temporary test file: {temp_file_path}")
        except Exception as e:
            logger.error(f"Failed to remove temp file: {str(e)}")

def test_search_performance():
    """
    Test the performance difference between FTS and LIKE-based search
    """
    # Create a database connection
    db = StencilDatabase()
    
    try:
        # Make sure the FTS index is built
        db.rebuild_fts_index()
        
        # Get a list of all shapes for random sampling
        conn = db._get_conn()
        cursor = conn.execute("SELECT name FROM shapes LIMIT 10000")
        shape_names = [row[0] for row in cursor.fetchall()]
        
        if not shape_names:
            print("No shapes found in database. Please scan some stencils first.")
            return
        
        # Generate a list of test search terms:
        # 1. Exact matches
        # 2. Prefix matches
        # 3. Substring matches
        # 4. Non-existent terms
        test_terms = []
        
        # 1. Exact matches - use 5 random whole shape names
        exact_matches = random.sample(shape_names, min(5, len(shape_names)))
        test_terms.extend(exact_matches)
        
        # 2. Prefix matches - use first 3-5 characters of 5 random shape names
        prefix_matches = []
        for name in random.sample(shape_names, min(5, len(shape_names))):
            if len(name) > 5:
                prefix_matches.append(name[:random.randint(3, 5)])
        test_terms.extend(prefix_matches)
        
        # 3. Substring matches - use random 3-5 character substrings from 5 random shape names
        substring_matches = []
        for name in random.sample(shape_names, min(5, len(shape_names))):
            if len(name) > 8:
                start = random.randint(0, len(name) - 5)
                substring_matches.append(name[start:start + random.randint(3, 5)])
        test_terms.extend(substring_matches)
        
        # 4. Non-existent terms - generate 5 random strings
        non_existent = []
        for _ in range(5):
            non_existent.append(''.join(random.choices(string.ascii_letters, k=random.randint(4, 8))))
        test_terms.extend(non_existent)
        
        # Run the benchmark
        print("Running search performance benchmark...")
        print("=======================================")
        print(f"Testing {len(test_terms)} search terms")
        print("---------------------------------------")
        print("Term                   | FTS Time (ms) | LIKE Time (ms) | FTS Results | LIKE Results")
        print("---------------------- | ------------- | -------------- | ----------- | ------------")
        
        for term in test_terms:
            # Test FTS search
            fts_start = time.time()
            fts_results = db.search_shapes(term, use_fts=True)
            fts_time = (time.time() - fts_start) * 1000  # Convert to milliseconds
            
            # Test LIKE search
            like_start = time.time()
            like_results = db.search_shapes(term, use_fts=False)
            like_time = (time.time() - like_start) * 1000  # Convert to milliseconds
            
            # Print results
            print(f"{term[:20]:<20} | {fts_time:13.2f} | {like_time:14.2f} | {len(fts_results):11} | {len(like_results):12}")
        
        print("=======================================")
        print("Benchmark complete!")
    
    finally:
        db.close()

def main():
    """Main test function"""
    logger.info("Starting database functionality tests...")
    
    # Test database connection
    db = test_db_connection()
    
    # Test preset directories
    directories = test_preset_directories(db)
    
    # Test stencil caching
    stencils = test_stencil_caching(db)
    
    # Test saved searches
    searches = test_saved_searches(db)
    
    # Test favorites
    favorites = test_favorites(db)
    
    # Test search performance
    test_search_performance()
    
    # Close the database connection
    logger.info("Closing database connection...")
    db.close()
    
    logger.info("All database tests completed!")

if __name__ == "__main__":
    main() 