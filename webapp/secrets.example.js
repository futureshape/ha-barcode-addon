// Secrets configuration template - EXAMPLE FILE
// Copy this to secrets.js and fill in your actual values

// Home Assistant Configuration
export const HA_URL = 'wss://your-homeassistant-url.com/';
export const HA_TOKEN = 'YOUR_LONG_LIVED_ACCESS_TOKEN_HERE';
export const HA_TODO_LIST = 'todo.kitchen_inventory';

// TODO: Now that the webapp is served by an add-on, we can get the add-on to give us a token