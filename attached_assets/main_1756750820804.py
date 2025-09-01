import logging
from app import app
import seed_data

# Setting up logging for debugging
logging.basicConfig(level=logging.DEBUG)

if __name__ == "__main__":
    seed_data.seed_database()
    app.run(host="0.0.0.0", port=5000, debug=True)
