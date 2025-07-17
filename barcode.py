from sqlalchemy import create_engine, Column, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import requests
from bs4 import BeautifulSoup
import logging
from pynput.keyboard import Key, Listener
import os
from flask import Flask, request, jsonify

app = Flask(__name__)

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
        # Check if the key.char is an alphanumeric character and append it to the buffer
        if key.char.isalnum():
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

    # Spencial codes (non UPC)
    if code.startswith("!ADD-"):
        # Directly treat the remainder as the product name
        product_name = code[len("!ADD-"):]
        logging.info(f"Special ADD barcode detected. Product Name: {product_name}")
        post_data = {"name": product_name}
        response = requests.post(url, headers=headers, json=post_data)
        logging.info(f"Posted to HA with response code {response.status_code}, body {response.content}")
        return

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

# Main loop to continuously read barcodes and fetch product names
if __name__ == "__main__":
    # Start listening for key press and release events
    listener = Listener(on_press=on_press, on_release=on_release)
    listener.start()
    
    app.run(host='0.0.0.0', port=8888)