import yaml
import os
from typing import Dict, Any
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Default configuration
DEFAULT_CONFIG = {
    "app": {
        "title": "Visio Stencil Explorer",
        "description": "A tool to catalog and search Visio stencil files",
        "version": "1.0.0",
        "debug": False
    },
    "paths": {
        "stencil_directory": "./test_data",
        "database": "data/stencil_cache.db",
        "exports": "exports"
    },
    "scanner": {
        "extensions": [".vss", ".vssx", ".vssm", ".vst", ".vstx"],
        "auto_refresh_interval": 1,
        "batch_size": 100
    },
    "temp_cleaner": {
        "patterns": ["~$$*.*vssx"],
        "default_directory": "~/Documents"
    },
    "health": {
        "thresholds": {
            "low": 1,
            "medium": 5,
            "high": 10
        }
    }
}

class Config:
    """Configuration manager for the application"""
    
    def __init__(self, config_path: str = "config.yaml"):
        """
        Initialize configuration with values from config file or defaults
        
        Args:
            config_path: Path to YAML configuration file
        """
        self.config_path = config_path
        self._config = DEFAULT_CONFIG.copy()
        self.load()
    
    def load(self) -> Dict[str, Any]:
        """Load configuration from file"""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    file_config = yaml.safe_load(f)
                
                if file_config:
                    # Deep update config with file values
                    self._deep_update(self._config, file_config)
                
                logger.info(f"Configuration loaded from {self.config_path}")
            except Exception as e:
                logger.error(f"Error loading config from {self.config_path}: {str(e)}")
                logger.info("Using default configuration")
        else:
            logger.warning(f"Configuration file {self.config_path} not found, using defaults")
            # Create default config file if it doesn't exist
            self.save()
        
        return self._config
    
    def save(self):
        """Save current configuration to file"""
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            
            with open(self.config_path, 'w') as f:
                yaml.dump(self._config, f, default_flow_style=False)
            
            logger.info(f"Configuration saved to {self.config_path}")
        except Exception as e:
            logger.error(f"Error saving config to {self.config_path}: {str(e)}")
    
    def get(self, key: str = None, default=None):
        """
        Get configuration value by key
        
        Args:
            key: Dot-separated path to config value (e.g., 'app.title')
            default: Default value if key not found
        
        Returns:
            Configuration value or default
        """
        if not key:
            return self._config
        
        parts = key.split('.')
        current = self._config
        
        for part in parts:
            if part in current:
                current = current[part]
            else:
                return default
        
        return current
    
    def _deep_update(self, target: Dict, source: Dict):
        """Recursively update target dict with values from source"""
        for key, value in source.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                self._deep_update(target[key], value)
            else:
                target[key] = value

# Create global config instance
config = Config() 