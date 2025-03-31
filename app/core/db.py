import sqlite3
import json
from datetime import datetime
from pathlib import Path
import threading
from typing import List, Dict, Any, Optional
import os

class StencilDatabase:
    """SQLite database manager for caching stencil data"""
    
    def __init__(self, db_path: str = "data/stencil_cache.db"):
        """Initialize database connection"""
        self.db_path = db_path
        self._conn = None
        self._lock = threading.Lock()
        
        # Ensure data directory exists
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize database
        self._init_db()
    
    def _get_conn(self) -> sqlite3.Connection:
        """Get thread-local database connection"""
        if not self._conn:
            self._conn = sqlite3.connect(self.db_path)
            self._conn.row_factory = sqlite3.Row
            # Enable foreign key constraints
            self._conn.execute("PRAGMA foreign_keys = ON")
        return self._conn
    
    def _init_db(self):
        """Initialize database schema"""
        with self._lock:
            conn = self._get_conn()
            # Use PRAGMA foreign_keys=ON; if needed, depending on SQLite version/config
            conn.execute("""
                CREATE TABLE IF NOT EXISTS stencils (
                    path TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    extension TEXT NOT NULL,
                    shape_count INTEGER NOT NULL,
                    file_size INTEGER, -- Added file size
                    last_scan TIMESTAMP NOT NULL,
                    last_modified TIMESTAMP NOT NULL
                )
            """)
            # Removed id and UNIQUE constraint, path is now PK
            # Removed shapes column

            conn.execute("""
                CREATE TABLE IF NOT EXISTS shapes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    stencil_path TEXT NOT NULL,
                    name TEXT NOT NULL,
                    FOREIGN KEY (stencil_path) REFERENCES stencils(path) ON DELETE CASCADE
                )
            """)
            # Added shapes table

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_stencils_path
                ON stencils(path)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_shapes_stencil_path
                ON shapes(stencil_path)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_shapes_name
                ON shapes(name)
            """)
            # Added indexes for shapes table

            # Add table for preset stencil directories
            conn.execute("""
                CREATE TABLE IF NOT EXISTS preset_directories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    path TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    is_active BOOLEAN DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_preset_directories_path
                ON preset_directories(path)
            """)

            # --- Add tables for Saved Searches and Favorites ---
            conn.execute("""
                CREATE TABLE IF NOT EXISTS saved_searches (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    search_term TEXT,
                    filters TEXT NOT NULL, -- Store filters as JSON string
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_saved_searches_name
                ON saved_searches(name)
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS favorites (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    item_type TEXT NOT NULL CHECK(item_type IN ('stencil', 'shape')),
                    stencil_path TEXT NOT NULL,
                    shape_id INTEGER, -- NULL if item_type is 'stencil'
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (stencil_path) REFERENCES stencils(path) ON DELETE CASCADE,
                    FOREIGN KEY (shape_id) REFERENCES shapes(id) ON DELETE CASCADE,
                    -- Ensure a stencil isn't favorited multiple times (Removed WHERE clause for compatibility)
                    UNIQUE (stencil_path),
                    -- Ensure a specific shape isn't favorited multiple times (Removed WHERE clause for compatibility)
                    UNIQUE (shape_id)
                    -- Note: Without WHERE, UNIQUE(shape_id) might prevent multiple NULLs if not handled carefully by SQLite version.
                    -- Consider making shape_id NOT NULL or handling uniqueness in application logic if needed.
                )
            """)
            # Note: Removed partial UNIQUE constraints (WHERE clause) for broader SQLite compatibility.
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_favorites_stencil_path
                ON favorites(stencil_path)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_favorites_shape_id
                ON favorites(shape_id) WHERE shape_id IS NOT NULL
            """)
            # --- End Saved Searches and Favorites tables ---

            conn.commit()

    def cache_stencil(self, stencil_data: Dict[str, Any]):
        """Cache a single stencil's data, including its shapes"""
        with self._lock:
            conn = self._get_conn()
            cursor = conn.cursor() # Use cursor for multiple operations

            file_path = Path(stencil_data['path'])
            file_stat = file_path.stat()
            last_modified_iso = datetime.fromtimestamp(file_stat.st_mtime).isoformat()
            file_size = file_stat.st_size

            # Insert or replace stencil metadata
            cursor.execute("""
                INSERT OR REPLACE INTO stencils
                (path, name, extension, shape_count, file_size, last_scan, last_modified)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                stencil_data['path'],
                stencil_data['name'],
                stencil_data['extension'],
                stencil_data['shape_count'],
                file_size, # Added file_size
                datetime.now().isoformat(),
                last_modified_iso
            ))

            # Delete existing shapes for this stencil before inserting new ones
            cursor.execute("DELETE FROM shapes WHERE stencil_path = ?", (stencil_data['path'],))

            # Insert shapes if any
            if stencil_data['shapes']:
                shapes_to_insert = [
                    (stencil_data['path'], shape_name)
                    for shape_name in stencil_data['shapes']
                ]
                cursor.executemany("""
                    INSERT INTO shapes (stencil_path, name) VALUES (?, ?)
                """, shapes_to_insert)

            conn.commit() # Ensure commit is included
    
    def get_cached_stencils(self) -> List[Dict[str, Any]]:
        """Retrieve all cached stencils with their shapes"""
        stencils_data = []
        with self._lock:
            conn = self._get_conn()
            # Fetch all stencil metadata first
            stencil_cursor = conn.execute("SELECT path, name, extension, shape_count, file_size, last_scan, last_modified FROM stencils")
            stencils = stencil_cursor.fetchall()

            if not stencils:
                return []

            # Fetch all shapes at once for efficiency
            shape_cursor = conn.execute("SELECT stencil_path, name FROM shapes")
            shapes_by_stencil = {}
            for shape_row in shape_cursor.fetchall():
                stencil_path = shape_row['stencil_path']
                if stencil_path not in shapes_by_stencil:
                    shapes_by_stencil[stencil_path] = []
                shapes_by_stencil[stencil_path].append(shape_row['name'])

            # Combine stencil metadata with shapes
            for stencil_row in stencils:
                stencil_path = stencil_row['path']
                stencils_data.append({
                    'path': stencil_path,
                    'name': stencil_row['name'],
                    'extension': stencil_row['extension'],
                    'shape_count': stencil_row['shape_count'],
                    'file_size': stencil_row['file_size'], # Added file_size
                    'shapes': shapes_by_stencil.get(stencil_path, []), # Get shapes from dict
                    'last_scan': stencil_row['last_scan'],
                    'last_modified': stencil_row['last_modified']
                })
        return stencils_data
    
    def get_stencil_by_path(self, path: str) -> Optional[Dict[str, Any]]:
        """Get a specific stencil by path, including its shapes"""
        with self._lock:
            conn = self._get_conn()
            # Fetch stencil metadata
            stencil_cursor = conn.execute("SELECT path, name, extension, shape_count, file_size, last_scan, last_modified FROM stencils WHERE path = ?", (path,))
            stencil_row = stencil_cursor.fetchone()

            if not stencil_row:
                return None

            # Fetch associated shapes
            shape_cursor = conn.execute("SELECT name FROM shapes WHERE stencil_path = ?", (path,))
            shapes = [shape_row['name'] for shape_row in shape_cursor.fetchall()]

            # Combine and return
            return {
                'path': stencil_row['path'],
                'name': stencil_row['name'],
                'extension': stencil_row['extension'],
                'shape_count': stencil_row['shape_count'],
                'file_size': stencil_row['file_size'], # Added file_size
                'shapes': shapes, # Fetched from shapes table
                'last_scan': stencil_row['last_scan'],
                'last_modified': stencil_row['last_modified']
            }
    
    def needs_update(self, path: str) -> bool:
        """Check if a stencil needs to be rescanned based on modification time"""
        stencil = self.get_stencil_by_path(path)
        if not stencil:
            return True
            
        file_mtime = datetime.fromtimestamp(Path(path).stat().st_mtime)
        cached_mtime = datetime.fromisoformat(stencil['last_modified'])
        return file_mtime > cached_mtime

    # --- Saved Search Methods ---

    def add_saved_search(self, name: str, search_term: str, filters: Dict[str, Any]):
        """Add a new saved search."""
        filters_json = json.dumps(filters)
        with self._lock:
            conn = self._get_conn()
            try:
                conn.execute(
                    "INSERT INTO saved_searches (name, search_term, filters) VALUES (?, ?, ?)",
                    (name, search_term, filters_json)
                )
                conn.commit()
                return True
            except sqlite3.IntegrityError: # Handles UNIQUE constraint violation for name
                print(f"Error: Saved search name '{name}' already exists.")
                return False

    def get_saved_searches(self) -> List[Dict[str, Any]]:
        """Retrieve all saved searches."""
        with self._lock:
            conn = self._get_conn()
            cursor = conn.execute("SELECT id, name, search_term, filters, created_at FROM saved_searches ORDER BY name")
            return [
                {
                    'id': row['id'],
                    'name': row['name'],
                    'search_term': row['search_term'],
                    'filters': json.loads(row['filters']),
                    'created_at': row['created_at']
                 } for row in cursor.fetchall()
            ]

    def delete_saved_search(self, search_id: int):
        """Delete a saved search by its ID."""
        with self._lock:
            conn = self._get_conn()
            conn.execute("DELETE FROM saved_searches WHERE id = ?", (search_id,))
            conn.commit()

    # --- Favorites Methods ---

    def add_favorite_stencil(self, stencil_path: str):
        """Add a stencil to favorites."""
        with self._lock:
            conn = self._get_conn()
            try:
                conn.execute(
                    "INSERT INTO favorites (item_type, stencil_path) VALUES (?, ?)",
                    ('stencil', stencil_path)
                )
                conn.commit()
                return True
            except sqlite3.IntegrityError: # Handles UNIQUE constraint
                print(f"Stencil '{stencil_path}' is already a favorite.")
                return False # Already favorited

    def add_favorite_shape(self, stencil_path: str, shape_name: str):
        """Add a specific shape to favorites."""
        with self._lock:
            conn = self._get_conn()
            # First, find the shape's ID
            shape_cursor = conn.execute(
                "SELECT id FROM shapes WHERE stencil_path = ? AND name = ?",
                (stencil_path, shape_name)
            )
            shape_row = shape_cursor.fetchone()
            if not shape_row:
                print(f"Error: Shape '{shape_name}' not found in stencil '{stencil_path}'.")
                return False

            shape_id = shape_row['id']
            try:
                conn.execute(
                    "INSERT INTO favorites (item_type, stencil_path, shape_id) VALUES (?, ?, ?)",
                    ('shape', stencil_path, shape_id)
                )
                conn.commit()
                return True
            except sqlite3.IntegrityError: # Handles UNIQUE constraint
                print(f"Shape '{shape_name}' from '{stencil_path}' is already a favorite.")
                return False # Already favorited

    def remove_favorite(self, favorite_id: int):
        """Remove an item from favorites by its ID."""
        with self._lock:
            conn = self._get_conn()
            conn.execute("DELETE FROM favorites WHERE id = ?", (favorite_id,))
            conn.commit()

    def remove_favorite_stencil(self, stencil_path: str):
        """Remove a stencil from favorites by its path."""
        with self._lock:
            conn = self._get_conn()
            conn.execute(
                "DELETE FROM favorites WHERE item_type = 'stencil' AND stencil_path = ?",
                (stencil_path,)
            )
            conn.commit()

    def remove_favorite_shape(self, shape_id: int):
         """Remove a shape from favorites by its shape ID."""
         with self._lock:
            conn = self._get_conn()
            conn.execute(
                "DELETE FROM favorites WHERE item_type = 'shape' AND shape_id = ?",
                (shape_id,)
            )
            conn.commit()

    def get_favorites(self) -> List[Dict[str, Any]]:
        """Retrieve all favorite items (stencils and shapes)."""
        with self._lock:
            conn = self._get_conn()
            # Join favorites with stencils and shapes to get names etc.
            cursor = conn.execute("""
                SELECT
                    f.id, f.item_type, f.stencil_path, f.shape_id, f.added_at,
                    st.name as stencil_name,
                    sh.name as shape_name
                FROM favorites f
                JOIN stencils st ON f.stencil_path = st.path
                LEFT JOIN shapes sh ON f.shape_id = sh.id AND f.item_type = 'shape'
                ORDER BY f.added_at DESC
            """)
            return [dict(row) for row in cursor.fetchall()] # Convert rows to dicts

    def is_favorite_stencil(self, stencil_path: str) -> bool:
        """Check if a stencil is favorited."""
        with self._lock:
            conn = self._get_conn()
            cursor = conn.execute(
                "SELECT 1 FROM favorites WHERE item_type = 'stencil' AND stencil_path = ?",
                (stencil_path,)
            )
            return cursor.fetchone() is not None

    def is_favorite_shape(self, shape_id: int) -> bool:
        """Check if a specific shape is favorited by its ID."""
        with self._lock:
            conn = self._get_conn()
            cursor = conn.execute(
                "SELECT 1 FROM favorites WHERE item_type = 'shape' AND shape_id = ?",
                (shape_id,)
            )
            return cursor.fetchone() is not None

    # --- End Favorites Methods ---

    def clear_cache(self):
        """Clear all cached data"""
        # Note: This currently only clears stencils/shapes.
        # Consider if it should also clear saved_searches/favorites.
        with self._lock:
            conn = self._get_conn()
            conn.execute("DELETE FROM stencils")
            conn.commit()
    
    def close(self):
        """Close database connection"""
        if self._conn:
            self._conn.close()
            self._conn = None 

    # --- Preset Directory Methods ---

    def add_preset_directory(self, path: str, name: str = None) -> bool:
        """Add a new preset directory."""
        if name is None:
            name = os.path.basename(path)
        with self._lock:
            conn = self._get_conn()
            try:
                conn.execute(
                    "INSERT INTO preset_directories (path, name) VALUES (?, ?)",
                    (path, name)
                )
                conn.commit()
                return True
            except sqlite3.IntegrityError:
                print(f"Directory '{path}' is already in presets.")
                return False

    def get_preset_directories(self) -> List[Dict[str, Any]]:
        """Retrieve all preset directories."""
        with self._lock:
            conn = self._get_conn()
            cursor = conn.execute(
                "SELECT id, path, name, is_active, created_at FROM preset_directories ORDER BY created_at DESC"
            )
            return [dict(row) for row in cursor.fetchall()]

    def get_active_directory(self) -> Optional[Dict[str, Any]]:
        """Get the currently active directory."""
        with self._lock:
            conn = self._get_conn()
            cursor = conn.execute(
                "SELECT id, path, name, created_at FROM preset_directories WHERE is_active = 1 LIMIT 1"
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    def set_active_directory(self, directory_id: int) -> bool:
        """Set a directory as active and deactivate others."""
        with self._lock:
            conn = self._get_conn()
            try:
                # First deactivate all directories
                conn.execute("UPDATE preset_directories SET is_active = 0")
                # Then activate the selected directory
                conn.execute(
                    "UPDATE preset_directories SET is_active = 1 WHERE id = ?",
                    (directory_id,)
                )
                conn.commit()
                return True
            except Exception as e:
                print(f"Error setting active directory: {e}")
                return False

    def remove_preset_directory(self, directory_id: int) -> bool:
        """Remove a preset directory."""
        with self._lock:
            conn = self._get_conn()
            try:
                conn.execute(
                    "DELETE FROM preset_directories WHERE id = ?",
                    (directory_id,)
                )
                conn.commit()
                return True
            except Exception as e:
                print(f"Error removing preset directory: {e}")
                return False 