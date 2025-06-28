import logging
import os
from pathlib import Path
from config import LOG_DIR, LOG_FILE

def configure_logging():
    os.makedirs(LOG_DIR, exist_ok=True)
    log_path = Path(LOG_DIR) / LOG_FILE
    if log_path.exists():
        log_path.unlink()
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_path),
            logging.StreamHandler()
        ]
    )