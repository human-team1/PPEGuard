import logging
import os
import sys

import eventlet

eventlet.monkey_patch()

sys.path.insert(0, os.path.dirname(__file__))

from app import create_app, socketio


app = create_app()
logger = logging.getLogger(__name__)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    logger.info("[Server] started host=127.0.0.1 port=%s", port)
    socketio.run(
        app,
        host="127.0.0.1",
        port=port,
        debug=False,
        log_output=False,
    )
