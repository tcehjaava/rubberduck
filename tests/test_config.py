# test_config.py
from config import GLOBAL_CONFIG

print(GLOBAL_CONFIG.model_dump_json(indent=2))
