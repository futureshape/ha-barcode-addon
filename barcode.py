from sqlalchemy import create_engine, Column, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import requests
from bs4 import BeautifulSoup
import logging
from pynput.keyboard import Key, Listener
import os
import subprocess
import tempfile
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory

app = Flask(__name__)

# Serve webapp files under /app path
@app.route('/app/')
@app.route('/app/<path:path>')
def serve_webapp(path='index.html'):
    return send_from_directory('webapp', path)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Define the database connection (SQLite in this case)
DATABASE_URL = "sqlite:///products.db"
Base = declarative_base()

engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)

# Define the Product model
class Product(Base):
    __tablename__ = 'products'
    
    upc = Column(String, primary_key=True)
    name = Column(String, nullable=True)  # Allows NULL values

# Function to scrape product name from the web
def web_scrape_product_name(upc):
    url = f"https://www.hellosupermarket.co.uk/product/{upc}"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            product_name_tag = soup.find('div', class_='text-xl')
            if product_name_tag:
                return product_name_tag.text.strip()
            else:
                logging.info(f"Product name not found for UPC: {upc}")
                return None
        else:
            logging.error(f"Failed to retrieve product page for UPC: {upc}, Status code: {response.status_code}")
            return None
    except Exception as e:
        logging.error(f"Error retrieving product information for UPC: {upc}, Error: {str(e)}")
        return None

# Function to get or fetch product name by UPC
def get_product_name_by_upc(upc):
    # Create a database session
    session = Session()
    
    # Ensure the products table exists
    Base.metadata.create_all(engine)
    
    # Try to find the product in the database
    product = session.query(Product).filter_by(upc=upc).first()
    
    if product:
        # If found, return the product name
        return product.name
    else:
        # If not found, attempt to look up the product name through web scraping
        product_name = web_scrape_product_name(upc)
        
        # If the product name is not found, save a NULL value in the product name column
        new_product = Product(upc=upc, name=product_name)  # product_name will be None if not found
        session.add(new_product)
        session.commit()
        
        return product_name
    
# Initialize an empty list to serve as a buffer for characters
buffer = []

def on_press(key):
    try:
        # Check if the key.char is a printable ASCII character and append it to the buffer
        if key.char.isprintable():
            buffer.append(key.char)
    except AttributeError:
        # Check for special keys
        if key == Key.space:
            # Append space to the buffer if space key is pressed
            buffer.append(' ')
        elif key == Key.enter:
            # When Enter is pressed, join the buffer into a string, print it, and clear the buffer
            upc = ''.join(buffer)
            
            logging.info(f"Read line from input device: {upc}")
            buffer.clear()

            process_barcode(upc)

        elif key == Key.backspace:
            # Handle backspace (delete last character in buffer if it exists)
            if buffer:
                buffer.pop()

def on_release(key):
    # Stop listener if the escape key is pressed
    if key == Key.esc:
        return False

def process_barcode(code):
    logging.info(f"Processing barcode: {code}")
    url = "http://supervisor/core/api/services/shopping_list/add_item"
    headers = {"Authorization": f"Bearer {os.getenv('SUPERVISOR_TOKEN')}"}

    # Post barcode_scanned event to Home Assistant (first)
    event_url = "http://supervisor/core/api/events/barcode_scanned"
    event_data = {"barcode": code}
    event_response = requests.post(event_url, headers=headers, json=event_data)
    logging.info(f"Posted barcode_scanned event to HA with response code {event_response.status_code}, body {event_response.content}")

    # Special codes (non UPC)
    if code.startswith("!ADD-"):
        # Directly treat the remainder as the product name
        product_name = code[len("!ADD-"):]
        logging.info(f"Special ADD barcode detected. Product Name: {product_name}")
        post_data = {"name": product_name}
        response = requests.post(url, headers=headers, json=post_data)
        logging.info(f"Posted to HA with response code {response.status_code}, body {response.content}")
    else:
        # Normal barcode processing (Assuming UPC format)
        product_name = get_product_name_by_upc(code)
        if product_name:
            logging.info(f"Product Name: {product_name}")
            post_data = {"name": product_name}
        else:
            logging.warning("Product name could not be found.")
            post_data = {"name": f"Unknown product {code}"}

        response = requests.post(url, headers=headers, json=post_data)
        logging.info(f"Posted to HA with response code {response.status_code}, body {response.content}")

        if not product_name:
            url = "http://supervisor/core/api/services/input_text/set_value"
            post_data = {"entity_id": "input_text.barcode_fix_upc", "value": code}
            response = requests.post(url, headers=headers, json=post_data)
            logging.info(f"Posted to HA with response code {response.status_code}, body {response.content}")

@app.route('/modify_product', methods=['POST'])
def modify_product():
    data = request.json
    if not data or 'upc' not in data or 'name' not in data or not data['upc'] or not data['name']:
        return jsonify({"error": "Both 'upc' and 'name' parameters are required and must be non-empty."}), 400
    
    upc = data['upc']
    name = data['name']
    
    session = Session()
    product = session.query(Product).filter_by(upc=upc).first()
    
    if product:
        # If the product exists, update the name
        product.name = name
    else:
        # If the product does not exist, add it
        new_product = Product(upc=upc, name=name)
        session.add(new_product)
    
    session.commit()
    session.close()
    
    return jsonify({"status": "OK"}), 200

@app.route('/barcode_scanned', methods=['POST'])
def barcode_scanned():
    data = request.json
    if not data or 'upc' not in data or not data['upc']:
        return jsonify({"error": "'upc' parameter is required and must be non-empty."}), 400
    upc = data['upc']
    process_barcode(upc)
    return jsonify({"status": "OK"}), 200

@app.route('/print_label', methods=['POST'])
def print_label():
    """
    Print a label using make_label.py and niimblue-cli.
    
    Expected JSON payload:
    {
        "type": "leftovers" | "opened_ingredient" | "standard",
        
        # For leftovers:
        "description": "Curry",
        "timestamp": "2025-01-15T10:30:00Z",
        "uid": "abc123",
        
        # For opened_ingredient:
        "ingredient": "Milk",
        "openedDate": "2025-01-15T10:30:00Z",
        "useByDate": "2025-01-18T10:30:00Z",
        "uid": "def456",
        
        # For standard:
        "label": "Lactose Free",
        "icon": "mdi:cow-off"
    }
    """
    data = request.json
    if not data or 'type' not in data:
        return jsonify({"error": "'type' parameter is required"}), 400
    
    label_type = data['type']
    
    try:
        # Create temporary file for the label image
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_file:
            tmp_path = tmp_file.name
        
        # Get the script directory
        script_dir = os.path.dirname(os.path.abspath(__file__))
        make_label_path = os.path.join(script_dir, 'make_label.py')
        
        # Build the make_label.py command based on label type
        if label_type == 'leftovers':
            # QR code with "!R-{UID}" and timestamp line
            uid = data.get('uid', 'UNKNOWN')
            timestamp = data.get('timestamp')
            
            # Format timestamp as "01 Jan 2025"
            if timestamp:
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                date_str = dt.strftime('%d %b %Y')
            else:
                date_str = datetime.now().strftime('%d %b %Y')
            
            qr_content = f"!R-{uid}"
            line1 = f"mdi:pot-steam {date_str}"
            
            cmd = ['python3', make_label_path, tmp_path, 'qr', qr_content, line1]
        
        elif label_type == 'opened_ingredient':
            # QR code with "!R-{UID}", opened date line, and use-by date line
            uid = data.get('uid', 'UNKNOWN')
            opened_date = data.get('openedDate')
            use_by_date = data.get('useByDate')
            
            # Format dates as "01 Jan 2025"
            if opened_date:
                dt_opened = datetime.fromisoformat(opened_date.replace('Z', '+00:00'))
                opened_str = dt_opened.strftime('%d %b %Y')
            else:
                opened_str = datetime.now().strftime('%d %b %Y')
            
            if use_by_date:
                dt_use_by = datetime.fromisoformat(use_by_date.replace('Z', '+00:00'))
                use_by_str = dt_use_by.strftime('%d %b %Y')
            else:
                use_by_str = "Unknown"
            
            qr_content = f"!R-{uid}"
            line1 = f"mdi:food-takeout-box-outline {opened_str}"
            line2 = f"mdi:close-octagon-outline {use_by_str}"
            
            cmd = ['python3', make_label_path, tmp_path, 'qr', qr_content, line1, line2]
        
        elif label_type == 'standard':
            # Icon on left, text on right
            label_text = data.get('label', 'Label')
            icon = data.get('icon', 'mdi:tag')
            
            cmd = ['python3', make_label_path, tmp_path, 'icon', icon, label_text]
        
        else:
            return jsonify({"error": f"Unknown label type: {label_type}"}), 400
        
        # Generate the label image
        logging.info(f"Generating label with command: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        logging.info(f"Label generated: {result.stdout}")
        
        # Print the label using niimblue-cli
        printer_address = 'C2:BA:A9:03:04:99' # TODO: make configurable in addon config
        print_cmd = ['niimblue-cli', 'print', '-t', 'ble', '-a', printer_address, tmp_path]
        
        logging.info(f"Printing label with command: {' '.join(print_cmd)}")
        print_result = subprocess.run(print_cmd, capture_output=True, text=True, check=True)
        logging.info(f"Label printed: {print_result.stdout}")
        
        # Clean up temporary file
        try:
            os.unlink(tmp_path)
        except Exception as e:
            logging.warning(f"Failed to delete temporary file {tmp_path}: {e}")
        
        return jsonify({
            "status": "OK",
            "message": "Label printed successfully",
            "label_type": label_type
        }), 200
    
    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to generate or print label: {e.stderr}")
        # Try to clean up temporary file
        try:
            if 'tmp_path' in locals():
                os.unlink(tmp_path)
        except:
            pass
        return jsonify({
            "error": "Failed to generate or print label",
            "details": e.stderr
        }), 500
    
    except Exception as e:
        logging.error(f"Error in print_label: {str(e)}")
        # Try to clean up temporary file
        try:
            if 'tmp_path' in locals():
                os.unlink(tmp_path)
        except:
            pass
        return jsonify({
            "error": "Internal server error",
            "details": str(e)
        }), 500

# Main loop to continuously read barcodes and fetch product names
if __name__ == "__main__":
    # Start listening for key press and release events
    listener = Listener(on_press=on_press, on_release=on_release)
    listener.start()
    
    app.run(host='0.0.0.0', port=8888)