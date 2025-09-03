import sqlite3
from utils import execute_query, extract_receipt_data_from_image
from flask import Flask, request, jsonify

app = Flask(__name__)
DB_NAME = 'receipts.db'

def create_database():
    conn = None
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS receipts (
                receipt_id INTEGER PRIMARY KEY AUTOINCREMENT,
                store_name TEXT NOT NULL,
                total_cost REAL NOT NULL,
                purchase_date TEXT NOT NULL
            )
        ''')
        print("Table 'receipts' created or already exists.")

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS items (
                item_id INTEGER PRIMARY KEY AUTOINCREMENT,
                receipt_id INTEGER,
                item_name TEXT NOT NULL,
                item_cost REAL NOT NULL,
                FOREIGN KEY(receipt_id) REFERENCES receipts(receipt_id)
            )
        ''')
        print("Table items created or already exists.")
        
        conn.commit()
    except sqlite3.Error as e:
        print(f"Database error: {e}")
    finally:
        if conn:
            conn.close()

@app.route('/extract_receipt', methods=['POST'])
def handle_extract_receipt():
    data = request.get_json()
    if not data or 'image' not in data:
        return jsonify({"status": "error", "message": "Invalid request. 'image' key is missing."}), 400
    
    base64_image_string = data['image']
    
    try:
        extracted_data = extract_receipt_data_from_image(base64_image_string)
        execute_query(f"Insert this receipt data into the database:\n\n {str(extracted_data)}")
        return jsonify({"status": "success", "data": extracted_data})
    
    except ValueError as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    except Exception as e:
        return jsonify({"status": "error", "message": f"unexpected error astagfirullahhh: {e}"}), 500


@app.route('/query', methods=['POST'])
def handle_query():
    data = request.get_json()
    if not data or 'query' not in data:
        return jsonify({"status": "error", "message": "Invalid request. 'query' key is missing."}), 400
    
    query = data['query']
    return execute_query(query)

if __name__ == "__main__":
    create_database()
    print("Starting Flask API server.")
    app.run(debug=True, port=5000)