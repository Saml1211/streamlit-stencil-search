#!/usr/bin/env python
# Test script specifically for the favorites functionality

import os
import sys
import logging
from pathlib import Path
from datetime import datetime

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import the database module
from app.core.db import StencilDatabase

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("favorites_test")

def test_favorites():
    """Test the favorites functionality in the database"""
    logger.info("Starting favorites test...")
    
    # Initialize the database
    db = StencilDatabase()
    logger.info(f"Database initialized at: {db.db_path}")
    
    # Create a temporary stencil file for testing
    temp_dir = os.path.join(os.getcwd(), "temp")
    os.makedirs(temp_dir, exist_ok=True)
    temp_file_path = os.path.join(temp_dir, "favorite_test.vssx")
    
    try:
        # Create temp file
        with open(temp_file_path, 'w') as f:
            f.write("Test stencil for favorites")
        logger.info(f"Created temporary test file at: {temp_file_path}")
        
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
        
        # Verify the stencil was cached
        cached_stencil = db.get_stencil_by_path(temp_file_path)
        if cached_stencil:
            logger.info(f"Successfully cached stencil: {cached_stencil['name']}")
        else:
            logger.error("Failed to cache stencil")
            return
        
        # Add favorite stencil
        logger.info(f"Adding favorite stencil: {temp_file_path}")
        result = db.add_favorite_stencil(temp_file_path)
        logger.info(f"Add favorite result: {result}")
        
        # Check if stencil is in favorites
        is_favorite = db.is_favorite_stencil(temp_file_path)
        logger.info(f"Is stencil a favorite? {is_favorite}")
        
        # Get all favorites
        favorites = db.get_favorites()
        logger.info(f"Found {len(favorites)} favorites")
        for fav in favorites:
            logger.info(f"  - ID: {fav.get('id')}, Type: {fav.get('item_type')}, Path: {fav.get('stencil_path')}, Name: {fav.get('stencil_name')}")
        
        # Remove favorite
        if favorites:
            logger.info(f"Removing favorite stencil: {temp_file_path}")
            db.remove_favorite_stencil(temp_file_path)
            
            # Verify removal
            updated_favorites = db.get_favorites()
            logger.info(f"Favorites count after removal: {len(updated_favorites)}")
        
        # Check for SQLite foreign key constraint enforcement
        logger.info("Checking if SQLite foreign keys are enabled...")
        conn = db._get_conn()
        cursor = conn.execute("PRAGMA foreign_keys")
        foreign_keys_enabled = cursor.fetchone()[0]
        logger.info(f"Foreign keys enabled: {bool(foreign_keys_enabled)}")
        
        # Close the database connection
        logger.info("Closing database connection...")
        db.close()
        
    finally:
        # Clean up the temporary file
        try:
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
                logger.info(f"Removed temporary test file: {temp_file_path}")
        except Exception as e:
            logger.error(f"Failed to remove temp file: {str(e)}")

if __name__ == "__main__":
    test_favorites() 