import logging
from uuid import uuid4

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(name)s  %(message)s"
)

logger = logging.getLogger("agent_api")

def create_request_id()->str:
    return str(uuid4())

def log_request_event(
        event:str,
        request_id:str,
        thread_id:str,
        **details
)->None:
    logger.info(
        f"event={event} request_id={request_id} thread_id={thread_id} details={details}"
    )