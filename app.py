import dash
from dash.dependencies import Input, Output, State
import logging
import sys
import os
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
UPDATE_INTERVAL = int(os.getenv("UPDATE_INTERVAL", 1800))

# Import layout and callbacks after app creation
app = dash.Dash(
    __name__,
    title="CryptoTrader",
    meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}],
    suppress_callback_exceptions=True,
)

# Now import the layout and register callbacks
from layout import create_layout
from callbacks import register_callbacks

# Set app layout
app.layout = create_layout(UPDATE_INTERVAL)

# Register callbacks
register_callbacks(app)

# Entry point
if __name__ == "__main__":
    logger.info("Starting trading bot dashboard")
    app.run(debug=True)