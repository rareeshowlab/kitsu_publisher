import logging
import asyncio
import gazu
from updater import Updater
from config import ConfigManager

# Global Instances
updater = Updater()
config_manager = ConfigManager()

# Logging Setup
log_queue = asyncio.Queue()
logger = logging.getLogger("kitsu_publisher")

class QueueHandler(logging.Handler):
    def emit(self, record):
        try:
            msg = self.format(record)
            try:
                loop = asyncio.get_running_loop()
                if loop.is_running():
                    loop.create_task(log_queue.put(msg))
            except RuntimeError:
                pass
        except Exception:
            self.handleError(record)

def setup_logging():
    logging.basicConfig(level=logging.INFO)
    queue_handler = QueueHandler()
    queue_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger.addHandler(queue_handler)
    logging.getLogger().addHandler(queue_handler)

def init_gazu():
    """Initialize gazu with saved session if available"""
    session = config_manager.get("session")
    if session and "host" in session and "tokens" in session:
        try:
            host = session["host"]
            tokens = session["tokens"]
            logger.info(f"Restoring Kitsu session for host: {host}")
            gazu.set_host(host)
            gazu.client.set_tokens(tokens)
        except Exception as e:
            logger.error(f"Failed to restore session: {e}")

# Initialize
init_gazu()
