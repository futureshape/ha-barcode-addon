from sqlalchemy import create_engine, Column, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import requests
from bs4 import BeautifulSoup
import logging
from pynput.keyboard import Key, Listener
import os

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Define the database connection (SQLite in this case)
DATABASE_URL = "sqlite:///products.db"
Base = declarative_base()

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
            product_name_tag = soup.find('h6', class_='amplify-heading')
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
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
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

            product_name = get_product_name_by_upc(upc)

            url = "http://supervisor/core/api/services/shopping_list/add_item"
            headers = {"Authorization": f"Bearer {os.getenv('SUPERVISOR_TOKEN')}"}

            if product_name:
                logging.info(f"Product Name: {product_name}")
                data = {"name": product_name}
            else:
                logging.warning("Product name could not be found.")
                data = {"name": f"Unknown product {upc}"}

            response = requests.post(url, headers=headers, json=data)
            logging.info(f"Posted to HA with response code {response.status_code}, body {response.content}")

        elif key == Key.backspace:
            # Handle backspace (delete last character in buffer if it exists)
            if buffer:
                buffer.pop()

def on_release(key):
    # Stop listener if the escape key is pressed
    if key == Key.esc:
        return False

# Main loop to continuously read barcodes and fetch product names
if __name__ == "__main__":
    # Start listening for key press and release events
    with Listener(on_press=on_press, on_release=on_release) as listener:
        listener.join()