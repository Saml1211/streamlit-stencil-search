import sqlite3
import json
from datetime import datetime, timedelta
from pathlib import Path
import threading
from typing import List, Dict, Any, Optional
import os
import traceback # For detailed error logging

class StencilDatabase:
    """SQLite database manager for caching stencil data"""

    def __init__(self, db_path: str = "app/data/stencil_cache.db"): # Adjusted default path relative to project root
        """Initialize database connection"""
        project_root_dir = Path(__file__).resolve().parent.parent.parent
        self.db_path = project_root_dir / Path(db_path)
        self._conn = None
        self._lock = threading.Lock() # Lock for thread safety
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        print(f"Database path set to: {self.db_path.resolve()}")
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        """Get database connection (using check_same_thread=False with external lock)"""
        if not self._conn:
            print(f"Connecting to DB: {self.db_path.resolve()}")
            try:
                self._conn = sqlite3.connect(str(self.db_path.resolve()), check_same_thread=False)
                self._conn.row_factory = sqlite3.Row
                self._conn.execute("PRAGMA foreign_keys = ON")
                print("DB connection successful.")
            except sqlite3.Error as e:
                print(f"!!! Database connection error: {e}")
                raise
        return self._conn

    def _init_db(self):
        """Initialize database schema"""
        with self._lock:
            conn = self._get_conn()
            if not self._check_integrity():
                print("Integrity check failed, attempting recovery/recreation.")
                self._recreate_tables()
                conn = self._get_conn()

            self._run_migrations(conn) # Apply schema changes if needed
            self._init_db_schema(conn) # Create tables if they don't exist

    # Helper for schema creation, called by _init_db and _recreate_tables
    def _init_db_schema(self, conn):
        """
        Initialize or migrate the database schema, including FTS index.
        Adds retry logic for FTS initialization with detailed logging and graceful fallback.
        """
        import time
        import logging
        import traceback

        self.fts_available = True  # Assume FTS is available unless proven otherwise
        max_retries = 3
        logger = logging.getLogger("db")

        for attempt in range(1, max_retries + 1):
            try:
                # Stencils Table
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS stencils (
                        path TEXT PRIMARY KEY, name TEXT NOT NULL, extension TEXT NOT NULL,
                        shape_count INTEGER NOT NULL, file_size INTEGER,
                        last_scan TIMESTAMP NOT NULL, last_modified TIMESTAMP NOT NULL
                    )""")
                # Shapes Table
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS shapes (
                        id INTEGER PRIMARY KEY AUTOINCREMENT, stencil_path TEXT NOT NULL,
                        name TEXT NOT NULL, width REAL DEFAULT 0, height REAL DEFAULT 0,
                        geometry TEXT, properties TEXT,
                        FOREIGN KEY (stencil_path) REFERENCES stencils(path) ON DELETE CASCADE
                    )""")
                # FTS Table (may fail if extension unavailable or DB locked)
                conn.execute("""
                    CREATE VIRTUAL TABLE IF NOT EXISTS shapes_fts USING fts5(
                        id, name, stencil_path, content='shapes', content_rowid='id',
                        tokenize='porter unicode61'
                    )""")
                # FTS Triggers
                conn.execute("""CREATE TRIGGER IF NOT EXISTS shapes_ai AFTER INSERT ON shapes BEGIN
                                INSERT INTO shapes_fts(rowid, name, stencil_path) VALUES (new.id, new.name, new.stencil_path); END""")
                conn.execute("""CREATE TRIGGER IF NOT EXISTS shapes_ad AFTER DELETE ON shapes BEGIN
                                INSERT INTO shapes_fts(shapes_fts, rowid, name, stencil_path) VALUES ('delete', old.id, old.name, old.stencil_path); END""")
                conn.execute("""CREATE TRIGGER IF NOT EXISTS shapes_au AFTER UPDATE ON shapes BEGIN
                                INSERT INTO shapes_fts(shapes_fts, rowid, name, stencil_path) VALUES ('delete', old.id, old.name, old.stencil_path);
                                INSERT INTO shapes_fts(rowid, name, stencil_path) VALUES (new.id, new.name, new.stencil_path); END""")
                # Indexes
                conn.execute("CREATE INDEX IF NOT EXISTS idx_stencils_path ON stencils(path)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_shapes_stencil_path ON shapes(stencil_path)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_shapes_name ON shapes(name)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_shapes_name_stencil_path ON shapes(name, stencil_path)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_stencils_last_modified ON stencils(last_modified)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_stencils_file_size ON stencils(file_size)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_stencils_shape_count ON stencils(shape_count)")
                # Preset Directories Table
                conn.execute("""CREATE TABLE IF NOT EXISTS preset_directories (
                                id INTEGER PRIMARY KEY AUTOINCREMENT, path TEXT UNIQUE NOT NULL, name TEXT NOT NULL,
                                is_active BOOLEAN DEFAULT 0, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP )""")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_preset_directories_path ON preset_directories(path)")
                # Saved Searches Table
                conn.execute("""CREATE TABLE IF NOT EXISTS saved_searches (
                                id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE NOT NULL, search_term TEXT,
                                filters TEXT NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP )""")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_saved_searches_name ON saved_searches(name)")
                # Favorites Table
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS favorites (
                """)
                # Success, break out of retry loop
                break
            except Exception as e:
                logger.error(f"Attempt {attempt}: Error initializing FTS index or tables: {e}")
                traceback.print_exc()
                time.sleep(0.5)
                if attempt == max_retries:
                    self.fts_available = False
                    logger.error("FTS index initialization failed after multiple attempts. Full traceback above. Falling back to standard search.")
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    item_type TEXT NOT NULL CHECK(item_type IN ('stencil', 'shape')),
                    stencil_path TEXT NOT NULL,
                    shape_id INTEGER, -- NULL if item_type is 'stencil'
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (stencil_path) REFERENCES stencils(path) ON DELETE CASCADE,
                    FOREIGN KEY (shape_id) REFERENCES shapes(id) ON DELETE CASCADE
                )""")
            # Create partial unique indexes separately
            conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_fav_stencil_unique ON favorites(stencil_path) WHERE item_type = 'stencil'")
            conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_fav_shape_unique ON favorites(shape_id) WHERE item_type = 'shape' AND shape_id IS NOT NULL") # Added shape_id IS NOT NULL check
            conn.execute("CREATE INDEX IF NOT EXISTS idx_favorites_stencil_path ON favorites(stencil_path)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_favorites_shape_id ON favorites(shape_id) WHERE shape_id IS NOT NULL")

            # Collections Table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS collections (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )""")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_collections_name ON collections(name)")

            # Collection Shapes Mapping Table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS collection_shapes (
                    collection_id INTEGER NOT NULL,
                    shape_id INTEGER NOT NULL,
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (collection_id) REFERENCES collections(id) ON DELETE CASCADE,
                    FOREIGN KEY (shape_id) REFERENCES shapes(id) ON DELETE CASCADE,
                    PRIMARY KEY (collection_id, shape_id)
                )""")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_collection_shapes_coll_id ON collection_shapes(collection_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_collection_shapes_shape_id ON collection_shapes(shape_id)")

            conn.commit()


    def _check_integrity(self):
        """Check database integrity"""
        conn = self._get_conn()
        try:
            integrity_check = conn.execute("PRAGMA integrity_check").fetchone()[0]
            if integrity_check == "ok":
                print("Database integrity check passed.")
                return True
            else:
                print(f"!!! Database integrity check failed: {integrity_check}")
                if self._recover_database(): return self._check_integrity()
                return False
        except Exception as e:
            print(f"Error checking database integrity: {e}")
            return False

    def _run_migrations(self, conn):
        """Run database migrations to ensure schema is up to date"""
        try:
            # Check and migrate 'shapes' table
            shapes_cursor = conn.execute("PRAGMA table_info(shapes)")
            shapes_columns = {row['name'] for row in shapes_cursor.fetchall()} # Use set for faster lookup
            if 'width' not in shapes_columns: conn.execute("ALTER TABLE shapes ADD COLUMN width REAL DEFAULT 0")
            if 'height' not in shapes_columns: conn.execute("ALTER TABLE shapes ADD COLUMN height REAL DEFAULT 0")
            if 'geometry' not in shapes_columns: conn.execute("ALTER TABLE shapes ADD COLUMN geometry TEXT")
            if 'properties' not in shapes_columns: conn.execute("ALTER TABLE shapes ADD COLUMN properties TEXT")

            # Check and migrate 'stencils' table
            stencils_cursor = conn.execute("PRAGMA table_info(stencils)")
            stencils_columns = {row['name'] for row in stencils_cursor.fetchall()}
            if 'file_size' not in stencils_columns:
                print("Adding 'file_size' column to 'stencils' table...")
                conn.execute("ALTER TABLE stencils ADD COLUMN file_size INTEGER")
                # Optionally, backfill file_size if possible/needed, though caching will handle it
                print("'file_size' column added.")

            conn.commit()
            print("Database migrations checked/completed.")
        except Exception as e:
            print(f"Error running migrations: {str(e)}")
            conn.rollback() # Rollback changes if a migration fails

    def _recreate_tables(self):
        """Recreate database tables (use when integrity check fails)"""
        print("Attempting to recreate database tables...")
        try:
            if self._conn:
                self._conn.close()
                self._conn = None
            backup_path = f"{self.db_path}.backup.{datetime.now().strftime('%Y%m%d%H%M%S')}"
            if self.db_path.exists():
                import shutil
                shutil.copy2(str(self.db_path), backup_path)
                print(f"Created database backup at {backup_path}")
                self.db_path.unlink() # Use unlink from Path object
                print(f"Removed corrupted database at {self.db_path}")
            # Remove WAL/SHM files
            for suffix in ['-wal', '-shm']:
                 wal_path = self.db_path.with_suffix(f"{self.db_path.suffix}{suffix}")
                 if wal_path.exists(): wal_path.unlink(); print(f"Removed {wal_path}")
            # Re-initialize connection and schema
            self._conn = None
            conn = self._get_conn() # Establishes new connection
            # Rerun schema creation logic directly
            self._init_db_schema(conn)
            print("Database tables recreated. Please rescan stencils.")
            return True
        except Exception as e:
            print(f"Error recreating database tables: {e}")
            traceback.print_exc()
            return False

    def cache_stencil(self, stencil_data: Dict[str, Any]):
        """Cache a single stencil's data, including its shapes"""
        with self._lock:
            conn = self._get_conn()
            cursor = conn.cursor()
            try:
                file_path = Path(stencil_data['path'])
                file_stat = file_path.stat()
                last_modified_iso = datetime.fromtimestamp(file_stat.st_mtime).isoformat()
                file_size = file_stat.st_size

                # Start a transaction for atomicity
                conn.execute("BEGIN TRANSACTION")

                # Insert or replace stencil metadata
                cursor.execute("""
                    INSERT OR REPLACE INTO stencils
                    (path, name, extension, shape_count, file_size, last_scan, last_modified)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    stencil_data['path'], stencil_data['name'], stencil_data['extension'],
                    stencil_data['shape_count'], file_size, datetime.now().isoformat(), last_modified_iso
                ))

                # Delete existing shapes for this stencil before inserting new ones
                cursor.execute("DELETE FROM shapes WHERE stencil_path = ?", (stencil_data['path'],))

                # Insert shapes if any
                shape_ids = []
                if stencil_data['shapes']:
                    for shape in stencil_data['shapes']:
                        # Handle both old format (string) and new format (dict)
                        if isinstance(shape, str):
                            shape_name, width, height, geometry, properties = shape, 0, 0, None, None
                        else:
                            shape_name = shape['name']
                            width = shape.get('width', 0)
                            height = shape.get('height', 0)
                            geometry = json.dumps(shape.get('geometry', [])) if shape.get('geometry') else None
                            properties = json.dumps(shape.get('properties', {})) if shape.get('properties') else None

                        cursor.execute("""
                            INSERT INTO shapes (stencil_path, name, width, height, geometry, properties)
                            VALUES (?, ?, ?, ?, ?, ?)
                        """, (stencil_data['path'], shape_name, width, height, geometry, properties))
                        shape_ids.append(cursor.lastrowid)

                # Commit transaction
                conn.execute("COMMIT")

                # Verify FTS index is in sync (Optional Safety Check)
                try:
                    fts_rows = conn.execute("SELECT COUNT(*) FROM shapes_fts WHERE stencil_path = ?", (stencil_data['path'],)).fetchone()[0]
                    actual_rows = len(stencil_data['shapes']) if stencil_data['shapes'] else 0
                    if fts_rows != actual_rows:
                        print(f"FTS index mismatch for {stencil_data['name']}. Rebuilding subset...")
                        conn.execute("DELETE FROM shapes_fts WHERE stencil_path = ?", (stencil_data['path'],))
                        if shape_ids: # Only reinsert if shapes were actually added
                            # Fetch name for each shape_id before inserting into FTS
                            reinsert_data = []
                            for sid in shape_ids:
                                name_row = conn.execute("SELECT name FROM shapes WHERE id=?", (sid,)).fetchone()
                                if name_row:
                                    reinsert_data.append((sid, name_row['name'], stencil_data['path']))
                            if reinsert_data:
                                conn.executemany("INSERT INTO shapes_fts(rowid, name, stencil_path) VALUES (?, ?, ?)", reinsert_data)
                        conn.commit() # Commit FTS rebuild subset
                except Exception as fts_e:
                    print(f"Error verifying/rebuilding FTS subset for {stencil_data.get('path')}: {fts_e}")
                    # Don't let FTS verification fail the main caching operation

            except Exception as e:
                # Rollback transaction on error
                conn.execute("ROLLBACK")
                print(f"Error caching stencil {stencil_data.get('path', 'N/A')}: {e}")
                traceback.print_exc() # Print full traceback
                raise

    def get_cached_stencils(self) -> List[Dict[str, Any]]:
        """Retrieve all cached stencils basic info"""
        stencils_summary = []
        with self._lock:
            conn = self._get_conn()
            stencil_cursor = conn.execute("SELECT path, name, extension, shape_count, file_size, last_modified FROM stencils ORDER BY name")
            stencils_summary = [dict(row) for row in stencil_cursor.fetchall()]
        return stencils_summary

    def get_stencil_by_path(self, path: str) -> Optional[Dict[str, Any]]:
        """Get a specific stencil by path, including simplified shape info"""
        with self._lock:
            conn = self._get_conn()
            stencil_cursor = conn.execute("SELECT path, name, extension, shape_count, file_size, last_scan, last_modified FROM stencils WHERE path = ?", (path,))
            stencil_row = stencil_cursor.fetchone()
            if not stencil_row: return None
            shape_cursor = conn.execute("SELECT id as shape_id, name, width, height FROM shapes WHERE stencil_path = ?", (path,)) # Added shape_id
            shapes = [dict(row) for row in shape_cursor.fetchall()]
            stencil_data = dict(stencil_row)
            stencil_data['shapes'] = shapes
            return stencil_data

    def needs_update(self, path: str) -> bool:
        """Check if a stencil file needs to be re-cached"""
        file_path = Path(path)
        if not file_path.exists(): return True
        try: file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
        except FileNotFoundError: return True
        with self._lock:
            conn = self._get_conn()
            cursor = conn.execute("SELECT last_modified FROM stencils WHERE path = ?", (path,))
            result = cursor.fetchone()
            if not result: return True
            try:
                cached_mtime = datetime.fromisoformat(result['last_modified'])
                return file_mtime > (cached_mtime + timedelta(seconds=1))
            except (TypeError, ValueError): return True

    # --- Saved Search Methods ---
    def add_saved_search(self, name: str, search_term: str, filters: Dict[str, Any]):
        with self._lock:
            conn = self._get_conn()
            filters_json = json.dumps(filters)
            try:
                conn.execute("INSERT INTO saved_searches (name, search_term, filters) VALUES (?, ?, ?)", (name, search_term, filters_json))
                conn.commit()
            except sqlite3.IntegrityError: print(f"Saved search with name '{name}' already exists.")
            except Exception as e: print(f"Error saving search '{name}': {e}"); conn.rollback()

    def get_saved_searches(self) -> List[Dict[str, Any]]:
        with self._lock:
            conn = self._get_conn()
            cursor = conn.execute("SELECT id, name, search_term, filters, created_at FROM saved_searches ORDER BY name")
            searches = []
            for row in cursor.fetchall():
                 search = dict(row)
                 try: search['filters'] = json.loads(search['filters'])
                 except (json.JSONDecodeError, TypeError): search['filters'] = {}
                 searches.append(search)
            return searches

    def delete_saved_search(self, search_id: int):
        with self._lock:
            conn = self._get_conn()
            conn.execute("DELETE FROM saved_searches WHERE id = ?", (search_id,))
            conn.commit()

    # --- Favorites Methods ---
    def _get_favorite_by_id(self, favorite_id: int) -> Optional[Dict[str, Any]]:
         """Internal helper to fetch a favorite by its ID."""
         conn = self._get_conn()
         cursor = conn.execute(""" SELECT f.id, f.item_type, f.stencil_path, f.shape_id, f.added_at, st.name as stencil_name, sh.name as shape_name
                                   FROM favorites f JOIN stencils st ON f.stencil_path = st.path LEFT JOIN shapes sh ON f.shape_id = sh.id AND f.item_type = 'shape'
                                   WHERE f.id = ? """, (favorite_id,))
         row = cursor.fetchone()
         return dict(row) if row else None

    def add_favorite_stencil(self, stencil_path: str) -> Optional[Dict[str, Any]]:
        """Add a stencil to favorites and return the created/existing item"""
        with self._lock:
            conn = self._get_conn(); cursor = conn.cursor(); fav_id = None
            try:
                cursor.execute(""" INSERT INTO favorites (item_type, stencil_path, shape_id) VALUES ('stencil', ?, NULL)
                                   ON CONFLICT(stencil_path) WHERE item_type = 'stencil' DO NOTHING """, (stencil_path,))
                if cursor.rowcount > 0: fav_id = cursor.lastrowid; print(f"Favorited stencil: {stencil_path} with new ID: {fav_id}")
                else:
                     existing = conn.execute("SELECT id FROM favorites WHERE item_type = 'stencil' AND stencil_path = ?", (stencil_path,)).fetchone()
                     if existing: fav_id = existing['id']; print(f"Stencil {stencil_path} was already favorited with ID: {fav_id}")
                conn.commit()
                return self._get_favorite_by_id(fav_id) if fav_id else None
            except sqlite3.IntegrityError as e: print(f"Error adding favorite stencil {stencil_path}: Stencil path missing? {e}"); conn.rollback(); return None
            except Exception as e: print(f"Error adding favorite stencil {stencil_path}: {e}"); conn.rollback(); raise

    def add_favorite_shape_by_id(self, stencil_path: str, shape_id: int) -> Optional[Dict[str, Any]]:
        """Add a shape to favorites by ID and return the created/existing item"""
        with self._lock:
            conn = self._get_conn(); cursor = conn.cursor(); fav_id = None
            try:
                shape_exists = conn.execute("SELECT 1 FROM shapes WHERE id = ? AND stencil_path = ?", (shape_id, stencil_path)).fetchone()
                if not shape_exists: print(f"Shape ID {shape_id} not found in stencil {stencil_path}"); return None
                cursor.execute(""" INSERT INTO favorites (item_type, stencil_path, shape_id) VALUES ('shape', ?, ?)
                                   ON CONFLICT(shape_id) WHERE item_type = 'shape' DO NOTHING """, (stencil_path, shape_id))
                if cursor.rowcount > 0: fav_id = cursor.lastrowid; print(f"Favorited shape ID: {shape_id} with new Fav ID: {fav_id}")
                else:
                    existing = conn.execute("SELECT id FROM favorites WHERE item_type = 'shape' AND shape_id = ?", (shape_id,)).fetchone()
                    if existing: fav_id = existing['id']; print(f"Shape ID {shape_id} was already favorited with Fav ID: {fav_id}")
                conn.commit()
                return self._get_favorite_by_id(fav_id) if fav_id else None
            except sqlite3.IntegrityError as e: print(f"Error adding favorite shape ID {shape_id}: FK violation? {e}"); conn.rollback(); return None
            except Exception as e: print(f"Error adding favorite shape ID {shape_id}: {e}"); conn.rollback(); raise

    def remove_favorite(self, favorite_id: int) -> bool:
        """Remove an item from favorites by its ID. Returns True if removed, False otherwise."""
        with self._lock:
            conn = self._get_conn(); cursor = conn.cursor()
            cursor.execute("DELETE FROM favorites WHERE id = ?", (favorite_id,))
            removed_count = cursor.rowcount
            conn.commit()
            if removed_count > 0: print(f"Removed favorite ID: {favorite_id}"); return True
            else: print(f"Favorite ID {favorite_id} not found for removal."); return False

    def remove_favorite_stencil(self, stencil_path: str):
        """Remove a stencil from favorites by its path."""
        with self._lock:
            conn = self._get_conn()
            conn.execute("DELETE FROM favorites WHERE item_type = 'stencil' AND stencil_path = ?", (stencil_path,))
            conn.commit()

    def remove_favorite_shape(self, shape_id: int):
         """Remove a shape from favorites by its shape ID."""
         with self._lock:
            conn = self._get_conn()
            conn.execute("DELETE FROM favorites WHERE item_type = 'shape' AND shape_id = ?", (shape_id,))
            conn.commit()

    def get_favorites(self) -> List[Dict[str, Any]]:
        """Retrieve all favorite items (stencils and shapes)."""
        with self._lock:
            conn = self._get_conn()
            cursor = conn.execute("""
                SELECT f.id, f.item_type, f.stencil_path, f.shape_id, f.added_at, st.name as stencil_name, sh.name as shape_name
                FROM favorites f JOIN stencils st ON f.stencil_path = st.path LEFT JOIN shapes sh ON f.shape_id = sh.id AND f.item_type = 'shape'
                ORDER BY f.added_at DESC """)
            return [dict(row) for row in cursor.fetchall()]

    def is_favorite_stencil(self, stencil_path: str) -> bool:
        """Check if a stencil is favorited."""
        with self._lock:
            conn = self._get_conn()
            cursor = conn.execute("SELECT 1 FROM favorites WHERE item_type = 'stencil' AND stencil_path = ?", (stencil_path,))
            return cursor.fetchone() is not None

    def is_favorite_shape(self, shape_id: int) -> bool:
        """Check if a specific shape is favorited by its ID."""
        with self._lock:
            conn = self._get_conn()
            cursor = conn.execute("SELECT 1 FROM favorites WHERE item_type = 'shape' AND shape_id = ?", (shape_id,))
            return cursor.fetchone() is not None

    # --- Preset Directory Methods ---
    def add_preset_directory(self, path: str, name: str = None) -> bool:
        if not name: name = Path(path).name
        with self._lock:
            conn = self._get_conn()
            try:
                cursor = conn.execute("INSERT INTO preset_directories (path, name) VALUES (?, ?)", (path, name))
                conn.commit(); print(f"Added preset directory: {name} ({path}) ID: {cursor.lastrowid}"); return True
            except sqlite3.IntegrityError: print(f"Preset path already exists: {path}"); return False
            except Exception as e: print(f"Error adding preset directory: {e}"); conn.rollback(); return False

    def get_preset_directories(self) -> List[Dict[str, Any]]:
        with self._lock:
            conn = self._get_conn()
            cursor = conn.execute("SELECT id, path, name, is_active FROM preset_directories ORDER BY name")
            return [dict(row) for row in cursor.fetchall()]

    def get_active_directory(self) -> Optional[Dict[str, Any]]:
         with self._lock:
             conn = self._get_conn()
             cursor = conn.execute("SELECT id, path, name FROM preset_directories WHERE is_active = 1 LIMIT 1")
             row = cursor.fetchone(); return dict(row) if row else None

    def set_active_directory(self, directory_id: int) -> bool:
        """Set the active directory"""
        with self._lock:
            conn = self._get_conn()
            try:
                # Remove explicit transaction management
                # conn.execute("BEGIN TRANSACTION") 
                # Set all directories to inactive first
                conn.execute("UPDATE preset_directories SET is_active = 0")
                # Set the specified directory to active
                result = conn.execute("UPDATE preset_directories SET is_active = 1 WHERE id = ?", (directory_id,))
                # Commit removed - rely on implicit transaction/autocommit
                # conn.execute("COMMIT") 
                return result.rowcount > 0
            except sqlite3.Error as e:
                print(f"Error setting active directory: {e}")
                # Rollback removed as no explicit transaction started
                # conn.rollback() 
                return False

    def remove_preset_directory(self, directory_id: int) -> bool:
        with self._lock:
            conn = self._get_conn(); cursor = conn.cursor()
            cursor.execute("DELETE FROM preset_directories WHERE id = ?", (directory_id,))
            removed = cursor.rowcount > 0
            conn.commit()
            if removed: print(f"Removed preset directory ID: {directory_id}")
            else: print(f"Preset directory ID {directory_id} not found.")
            return removed

    # --- Collections Methods ---
    def create_collection(self, name: str) -> Optional[Dict[str, Any]]:
        """Creates a new collection."""
        with self._lock:
            conn = self._get_conn(); cursor = conn.cursor()
            try:
                now = datetime.now().isoformat()
                cursor.execute("INSERT INTO collections (name, created_at, updated_at) VALUES (?, ?, ?)", (name, now, now))
                collection_id = cursor.lastrowid
                conn.commit()
                print(f"Created collection '{name}' with ID: {collection_id}")
                # Fetch the created collection to return it
                return self.get_collection_details(collection_id) # Return full details
            except sqlite3.IntegrityError: print(f"Collection name '{name}' already exists."); conn.rollback(); return None
            except Exception as e: print(f"Error creating collection '{name}': {e}"); conn.rollback(); raise

    def get_collections(self) -> List[Dict[str, Any]]:
        """Retrieves all collections with shape counts."""
        with self._lock:
            conn = self._get_conn()
            query = """ SELECT c.id, c.name, c.created_at, c.updated_at, COUNT(cs.shape_id) as shape_count
                        FROM collections c LEFT JOIN collection_shapes cs ON c.id = cs.collection_id
                        GROUP BY c.id ORDER BY c.name """
            cursor = conn.execute(query)
            return [dict(row) for row in cursor.fetchall()]

    def get_collection_details(self, collection_id: int) -> Optional[Dict[str, Any]]:
        """Retrieves collection details including its shapes."""
        with self._lock:
            conn = self._get_conn()
            coll_cursor = conn.execute("SELECT id, name, created_at, updated_at FROM collections WHERE id = ?", (collection_id,))
            collection_data = coll_cursor.fetchone()
            if not collection_data: return None
            shapes_query = """ SELECT s.id as shape_id, s.name as shape_name, s.stencil_path, st.name as stencil_name
                               FROM collection_shapes cs JOIN shapes s ON cs.shape_id = s.id JOIN stencils st ON s.stencil_path = st.path
                               WHERE cs.collection_id = ? ORDER BY cs.added_at DESC """
            shapes_cursor = conn.execute(shapes_query, (collection_id,))
            shapes = [dict(row) for row in shapes_cursor.fetchall()]
            result = dict(collection_data); result['shapes'] = shapes
            return result

    def add_shape_to_collection(self, collection_id: int, shape_id: int) -> bool:
        """Adds a shape to a collection. Returns True on success/already exists, False on error."""
        with self._lock:
            conn = self._get_conn(); cursor = conn.cursor()
            try:
                coll_exists = conn.execute("SELECT 1 FROM collections WHERE id = ?", (collection_id,)).fetchone()
                shape_exists = conn.execute("SELECT 1 FROM shapes WHERE id = ?", (shape_id,)).fetchone()
                if not coll_exists or not shape_exists: print(f"Collection {collection_id} or Shape {shape_id} not found."); return False
                cursor.execute("INSERT OR IGNORE INTO collection_shapes (collection_id, shape_id) VALUES (?, ?)", (collection_id, shape_id))
                inserted = cursor.rowcount > 0
                if inserted: conn.execute("UPDATE collections SET updated_at = ? WHERE id = ?", (datetime.now().isoformat(), collection_id))
                conn.commit()
                if inserted: print(f"Added shape {shape_id} to collection {collection_id}")
                else: print(f"Shape {shape_id} already in collection {collection_id}")
                return True
            except Exception as e: print(f"Error adding shape {shape_id} to collection {collection_id}: {e}"); conn.rollback(); return False

    def remove_shape_from_collection(self, collection_id: int, shape_id: int) -> bool:
        """Removes a shape from a collection. Returns True if removed, False otherwise."""
        with self._lock:
            conn = self._get_conn(); cursor = conn.cursor()
            try:
                cursor.execute("DELETE FROM collection_shapes WHERE collection_id = ? AND shape_id = ?", (collection_id, shape_id))
                removed = cursor.rowcount > 0
                if removed: conn.execute("UPDATE collections SET updated_at = ? WHERE id = ?", (datetime.now().isoformat(), collection_id))
                conn.commit()
                if removed: print(f"Removed shape {shape_id} from collection {collection_id}")
                else: print(f"Shape {shape_id} not found in collection {collection_id}")
                return removed
            except Exception as e: print(f"Error removing shape {shape_id} from collection {collection_id}: {e}"); conn.rollback(); return False

    def update_collection(self, collection_id: int, name: Optional[str] = None,
                          add_shape_ids: Optional[List[int]] = None,
                          remove_shape_ids: Optional[List[int]] = None) -> Optional[Dict[str, Any]]:
        """Updates a collection's name and/or shape associations."""
        with self._lock:
            conn = self._get_conn(); cursor = conn.cursor()
            try:
                if not conn.execute("SELECT id FROM collections WHERE id = ?", (collection_id,)).fetchone(): return None
                conn.execute("BEGIN TRANSACTION")
                updated = False; now_iso = datetime.now().isoformat()
                if name is not None:
                    cursor.execute("UPDATE collections SET name = ?, updated_at = ? WHERE id = ?", (name, now_iso, collection_id)); updated = True
                if remove_shape_ids:
                    placeholders = ','.join('?'*len(remove_shape_ids)); sql = f"DELETE FROM collection_shapes WHERE collection_id = ? AND shape_id IN ({placeholders})"
                    params = [collection_id] + remove_shape_ids; cursor.execute(sql, params)
                    if cursor.rowcount > 0: updated = True
                if add_shape_ids:
                    added_count = 0
                    # Check shape existence efficiently
                    placeholders = ','.join('?'*len(add_shape_ids))
                    valid_shape_ids = {row['id'] for row in conn.execute(f"SELECT id FROM shapes WHERE id IN ({placeholders})", add_shape_ids)}
                    shapes_to_add = []
                    for shape_id in add_shape_ids:
                        if shape_id in valid_shape_ids: shapes_to_add.append((collection_id, shape_id))
                        else: print(f"Warning: Shape ID {shape_id} not found, cannot add.")
                    if shapes_to_add:
                         cursor.executemany("INSERT OR IGNORE INTO collection_shapes (collection_id, shape_id) VALUES (?, ?)", shapes_to_add)
                         # executemany might return -1, so just assume updated if we tried adding
                         added_count = len(shapes_to_add) # Use length of attempt list instead of rowcount
                    if added_count > 0: updated = True
                if updated and name is None: cursor.execute("UPDATE collections SET updated_at = ? WHERE id = ?", (now_iso, collection_id))
                conn.commit(); print(f"Updated collection {collection_id}")
                return self.get_collection_details(collection_id)
            except sqlite3.IntegrityError as e: print(f"Error updating collection {collection_id}: Integrity constraint (name '{name}'?). {e}"); conn.rollback(); return None
            except Exception as e: print(f"Error updating collection {collection_id}: {e}"); traceback.print_exc(); conn.rollback(); raise

    def delete_collection(self, collection_id: int) -> bool:
        """Deletes a collection and its associations."""
        with self._lock:
            conn = self._get_conn(); cursor = conn.cursor()
            try:
                cursor.execute("DELETE FROM collections WHERE id = ?", (collection_id,))
                deleted = cursor.rowcount > 0
                conn.commit() # Associations deleted by ON DELETE CASCADE
                if deleted: print(f"Deleted collection ID: {collection_id}")
                else: print(f"Collection ID {collection_id} not found.")
                return deleted
            except Exception as e: print(f"Error deleting collection {collection_id}: {e}"); conn.rollback(); return False
    # --- END: Collections Methods ---

    # --- Other Methods ---
    def clear_cache(self):
        """Clear all cached stencil, shape, favorite, and collection data."""
        with self._lock:
            conn = self._get_conn()
            try:
                conn.execute("BEGIN TRANSACTION")
                conn.execute("DELETE FROM collection_shapes")
                conn.execute("DELETE FROM collections")
                conn.execute("DELETE FROM favorites")
                conn.execute("DELETE FROM shapes") # Triggers will clear FTS
                conn.execute("DELETE FROM stencils")
                conn.commit()
                print("Cleared stencil, shape, favorite, and collection cache.")
            except Exception as e: print(f"Error clearing cache: {e}"); conn.rollback()

    def close(self):
        """Close database connection"""
        if self._conn: self._conn.close(); self._conn = None; print("Database connection closed.")

    def rebuild_fts_index(self):
        """Rebuild the FTS index if needed"""
        with self._lock:
            conn = self._get_conn()
            try:
                print("Rebuilding FTS index...")
                if conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='shapes_fts'").fetchone():
                    conn.execute("INSERT INTO shapes_fts(shapes_fts) VALUES('rebuild')"); print("Issued FTS rebuild command.")
                else: print("FTS table does not exist, skipping rebuild.")
                conn.commit()
            except Exception as e: print(f"Error rebuilding FTS index: {e}"); conn.rollback()

    def _recover_database(self):
        """Attempt to recover from a corrupted database file by dumping and reloading."""
        print("Attempting database recovery...")
        backup_path = f"{self.db_path}.corrupt_backup.{datetime.now().strftime('%Y%m%d%H%M%S')}"
        dump_path = f"{self.db_path}.sql_dump"
        try:
            if self.db_path.exists(): import shutil; shutil.move(str(self.db_path), backup_path); print(f"Moved corrupted DB to backup: {backup_path}")
            print(f"Attempting to dump SQL from {backup_path} to {dump_path}...")
            exit_code = os.system(f"sqlite3 \"{backup_path}\" .dump > \"{dump_path}\"")
            if exit_code != 0 or not os.path.exists(dump_path) or os.path.getsize(dump_path) == 0:
                 print("Failed to dump SQL. Recreating empty DB.");
                 if os.path.exists(dump_path): os.remove(dump_path)
                 return self._recreate_tables()
            print("SQL dump created.")
            if self._conn: self._conn.close(); self._conn = None
            for suffix in ['-wal', '-shm']: wal_path = self.db_path.with_suffix(f"{self.db_path.suffix}{suffix}");
            if wal_path.exists(): wal_path.unlink()
            self._conn = None; conn = self._get_conn()
            print(f"Importing data from {dump_path} into new database...")
            with open(dump_path, 'r') as f: sql_script = f.read()
            conn.executescript(sql_script); conn.commit()
            os.remove(dump_path); print("Database recovery attempt finished.")
            self._init_db_schema(conn) # Ensure schema is fully applied
            self.rebuild_fts_index()
            return True
        except Exception as recovery_error: print(f"Database recovery process failed: {recovery_error}"); traceback.print_exc(); return self._recreate_tables()

    def search_shapes(self, search_term: str, filters: dict = None, use_fts: bool = True, limit: int = 20, offset: int = 0, directory_filter: Optional[str] = None):
        """Search shapes, optionally using FTS, with filters and pagination."""
        with self._lock:
            conn = self._get_conn()
            cursor = conn.cursor()

            # --- Add this block: Pre-check for file_size column ---
            try:
                stencils_cursor = conn.execute("PRAGMA table_info(stencils)")
                stencils_columns = {row['name'] for row in stencils_cursor.fetchall()}
                if 'file_size' not in stencils_columns:
                    print("!!! 'file_size' column missing in search_shapes connection. Running migration...")
                    # Run the migration logic specifically for this connection
                    conn.execute("ALTER TABLE stencils ADD COLUMN file_size INTEGER")
                    conn.commit()
                    print("Migration applied within search_shapes.")
            except Exception as migration_check_e:
                print(f"Error checking/applying migration within search_shapes: {migration_check_e}")
            # --- End of added block ---

            query_params = {}
            filter_clauses = []

            # Normalize the directory filter path for reliable matching
            normalized_directory_filter = None
            if directory_filter:
                normalized_directory_filter = os.path.normpath(directory_filter)
                # Append wildcard for LIKE
                query_params['directory_filter_pattern'] = f"{normalized_directory_filter}%"
                # Add clause to filter by stencil path
                filter_clauses.append("stencils.path LIKE :directory_filter_pattern")

            # --- Standard Filters ---
            if filters:
                if filters.get('show_favorites'):
                    # Join with favorites table and filter by item_type = 'stencil'
                    filter_clauses.append("stencils.path IN (SELECT stencil_path FROM favorites WHERE item_type = 'stencil')")

                # --- Date Filters ---
                if filters.get('date_start'):
                    query_params['date_start'] = filters['date_start'].isoformat()
                    filter_clauses.append("stencils.last_modified >= :date_start")
                if filters.get('date_end'):
                    # Add one day and format to include the entire end day
                    end_date_inclusive = filters['date_end'] + timedelta(days=1)
                    query_params['date_end'] = end_date_inclusive.isoformat()
                    filter_clauses.append("stencils.last_modified < :date_end")

                # --- Size and Shape Count Filters (on stencils table) ---
                # Only add clauses if the filter value is actually restrictive
                if filters.get('min_size') is not None and filters['min_size'] > 0:
                    query_params['min_size'] = filters['min_size']
                    filter_clauses.append("stencils.file_size >= :min_size")
                # Check against a sensible max default (e.g. 50MB * 1024 * 1024) or ensure it's less than a very large number
                if filters.get('max_size') is not None and filters['max_size'] < (50 * 1024 * 1024): # Only add if less than default max
                    query_params['max_size'] = filters['max_size']
                    filter_clauses.append("stencils.file_size <= :max_size")
                if filters.get('min_shapes') is not None and filters['min_shapes'] > 0:
                    query_params['min_shapes'] = filters['min_shapes']
                    filter_clauses.append("stencils.shape_count >= :min_shapes")
                if filters.get('max_shapes') is not None and filters['max_shapes'] < 500: # Only add if less than default max
                    query_params['max_shapes'] = filters['max_shapes']
                    filter_clauses.append("stencils.shape_count <= :max_shapes")

                # --- Shape Metadata Filters (on shapes table) ---
                if filters.get('min_width') is not None and filters['min_width'] > 0:
                    query_params['min_width'] = filters['min_width']
                    filter_clauses.append("shapes.width >= :min_width")
                if filters.get('max_width') is not None and filters['max_width'] > 0:
                    query_params['max_width'] = filters['max_width']
                    filter_clauses.append("shapes.width <= :max_width")
                if filters.get('min_height') is not None and filters['min_height'] > 0:
                    query_params['min_height'] = filters['min_height']
                    filter_clauses.append("shapes.height >= :min_height")
                if filters.get('max_height') is not None and filters['max_height'] > 0:
                    query_params['max_height'] = filters['max_height']
                    filter_clauses.append("shapes.height <= :max_height")
                if filters.get('has_properties'):
                    # Check if properties JSON is not NULL, empty object, or empty array
                    filter_clauses.append("shapes.properties IS NOT NULL AND shapes.properties != '' AND shapes.properties != '[]' AND shapes.properties != '{}'")

                # --- Property Name/Value Filters (requires JSON parsing) ---
                # NOTE: These might be slow on large datasets without specific JSON indexing
                # Consider adding generated columns or specific indexing if performance is critical.
                prop_name = filters.get('property_name')
                prop_value = filters.get('property_value')
                if prop_name:
                    # Check if the key exists in the properties JSON
                    query_params['prop_name_pattern'] = f'%"{prop_name}"%:'
                    filter_clauses.append("shapes.properties LIKE :prop_name_pattern")
                if prop_value:
                    # Check if the value exists in the properties JSON
                    query_params['prop_value_pattern'] = f'%:{json.dumps(prop_value)}%'
                    filter_clauses.append("shapes.properties LIKE :prop_value_pattern")

            # Construct WHERE clause
            where_clause = " AND ".join(filter_clauses) if filter_clauses else "1=1" # Use 1=1 if no filters

            # --- FTS Search ---
            if use_fts:
                query_params['search_term_fts'] = search_term
                # FTS query needs to join back to shapes and stencils to apply standard filters
                # Use snippet function for highlighting
                query = f"""
                    SELECT
                        s.id AS shape_id,
                        s.name AS shape_name,
                        st.name AS stencil_name,
                        st.path AS stencil_path,
                        s.width AS width,
                        s.height AS height,
                        s.geometry AS geometry,
                        s.properties AS properties,
                        snippet(shapes_fts, 1, '[HL]', '[/HL]', '...', 15) AS highlighted_name
                    FROM shapes_fts f
                    JOIN shapes s ON f.rowid = s.id
                    JOIN stencils st ON s.stencil_path = st.path
                    WHERE shapes_fts MATCH :search_term_fts AND {where_clause}
                    ORDER BY rank
                    LIMIT :limit OFFSET :offset
                """
            # --- Standard LIKE Search ---
            else:
                query_params['search_term_like'] = f"%{search_term}%"
                query = f"""
                    SELECT
                        s.id AS shape_id,
                        s.name AS shape_name,
                        st.name AS stencil_name,
                        st.path AS stencil_path,
                        s.width AS width,
                        s.height AS height,
                        s.geometry AS geometry,
                        s.properties AS properties,
                        NULL AS highlighted_name -- No highlight for standard search
                    FROM shapes s
                    JOIN stencils st ON s.stencil_path = st.path
                    WHERE s.name LIKE :search_term_like AND {where_clause}
                    ORDER BY st.name, s.name
                    LIMIT :limit OFFSET :offset
                """

            # Add limit and offset parameters
            query_params['limit'] = limit
            query_params['offset'] = offset

            # --- DEBUG PRINT --- 
            print(f"--- Executing DB Search Query ---")
            print(f"Using FTS: {use_fts}")
            print("SQL Query:")
            print(query)
            print(f"Parameters: {query_params}")
            # --- END DEBUG PRINT --- 
            try:
                cursor.execute(query, query_params)
                results = [
                    {
                        **dict(row), # Convert row object to dict
                        'geometry': json.loads(row['geometry']) if row['geometry'] else [],
                        'properties': json.loads(row['properties']) if row['properties'] else {}
                    }
                    for row in cursor.fetchall()
                ]
                return results
            except sqlite3.OperationalError as e:
                print(f"!!! Database search error: {e}")
                if use_fts: # <-- Fallback if *any* OperationalError occurs during an FTS attempt
                    print("OperationalError during FTS search. Attempting fallback to standard search.")
                    # Remove the debug prints temporarily to avoid recursive printing on fallback
                    # return self.search_shapes(search_term, filters, False, limit, offset, directory_filter)
                    # Need to implement fallback carefully to avoid infinite loops if standard search also fails
                    try:
                        print("Retrying with standard search...")
                        # Ensure use_fts is False for the recursive call
                        return self.search_shapes(search_term, filters, False, limit, offset, directory_filter)
                    except Exception as fallback_e:
                        print(f"!!! Standard search fallback also failed: {fallback_e}")
                        traceback.print_exc()
                        return [] # Return empty on fallback failure
                else:
                    # Error occurred even during standard search, or FTS wasn't used
                    traceback.print_exc() # Print detailed traceback for non-FTS operational errors
                    return [] # Return empty list on error
            except Exception as e: # Catch other potential errors
                print(f"!!! Unexpected search error: {e}")
                traceback.print_exc()
                return []

    def get_shape_by_id(self, shape_id: int) -> Optional[Dict[str, Any]]:
        """Get detailed information for a single shape by its ID."""
        with self._lock:
            conn = self._get_conn()
            query = """ SELECT s.id as shape_id, s.name as shape_name, s.width, s.height, s.geometry, s.properties,
                           st.name as stencil_name, st.path as stencil_path
                        FROM shapes s JOIN stencils st ON s.stencil_path = st.path WHERE s.id = ? """
            cursor = conn.execute(query, (shape_id,))
            row = cursor.fetchone()
            if not row: return None
            shape_data = dict(row)
            try: shape_data['geometry'] = json.loads(shape_data['geometry']) if shape_data.get('geometry') else None
            except (json.JSONDecodeError, TypeError): shape_data['geometry'] = None
            try: shape_data['properties'] = json.loads(shape_data['properties']) if shape_data.get('properties') else None
            except (json.JSONDecodeError, TypeError): shape_data['properties'] = None
            return shape_data