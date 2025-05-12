import json
import os
import logging

class ConfigManager:
    _instance = None
    _config = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ConfigManager, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if self._config is None:
            self.load_config()

    def load_config(self):
        try:
            config_path = os.path.join(os.path.dirname(__file__), 'config.json')
            with open(config_path, 'r') as f:
                self._config = json.load(f)
        except FileNotFoundError:
            logging.error("Config file not found. Using default values.")
            self._config = self._get_default_config()
        except json.JSONDecodeError:
            logging.error("Invalid config file format. Using default values.")
            self._config = self._get_default_config()

    def _get_default_config(self):
        return {
            "tracker": {
                "host": "0.0.0.0",
                "socket_port": 22236,
                "flask_port": 5000
            },
            "peer": {
                "default_peer_port": 33357,
                "default_username": "user1",
                "default_channel_id": "channel_1",
                "default_session_id": "session1"
            },
            "streaming": {
                "frame_quality": 80,
                "frame_rate": 30,
                "timeout": 3.0,
                "max_frame_size": 65507
            },
            "logging": {
                "level": "INFO",
                "max_lines": 10000
            }
        }

    def get_tracker_config(self):
        return self._config.get("tracker", {})

    def get_peer_config(self):
        return self._config.get("peer", {})

    def get_streaming_config(self):
        return self._config.get("streaming", {})

    def get_logging_config(self):
        return self._config.get("logging", {})

    def update_config(self, section, key, value):
        if section in self._config and key in self._config[section]:
            self._config[section][key] = value
            self._save_config()
            return True
        return False

    def _save_config(self):
        try:
            config_path = os.path.join(os.path.dirname(__file__), 'config.json')
            with open(config_path, 'w') as f:
                json.dump(self._config, f, indent=4)
            return True
        except Exception as e:
            logging.error(f"Error saving config: {e}")
            return False

# Tạo instance toàn cục
config = ConfigManager() 