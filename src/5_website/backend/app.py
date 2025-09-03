import sqlite3
import re
import os
import json
from openai import OpenAI
from dotenv import load_dotenv
from flask import Flask, request, jsonify

app = Flask(__name__)
DB_NAME = 'receipts.db'

load_dotenv()


client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def get_all_restaurant_names(db_path = DB_NAME):
    conn = None
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        sql_query = "SELECT DISTINCT store_name FROM receipts;"
        
        cursor.execute(sql_query)
        rows = cursor.fetchall()
        
        restaurant_names = [row[0] for row in rows]
        
        return restaurant_names

    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return [] 

    finally:
        if conn:
            conn.close()

def text_to_sql(user_input: str) -> str:
    """
    Text to SQL with OpenAIs GPT-5-mini
    """
    
    restaurant_list = get_all_restaurant_names()

    response = client.responses.create(
        model="gpt-5-mini",
        input=[
            {
            "role": "developer",
            "content": [
                {
                    "type": "input_text",
                    "text": """Transform user input into an SQLite query based on a provided database schema (DDL) and sample data (SQL).
                            First, carefully analyze the users request and the provided schema/sample, planning the query step by step before writing the final SQL statement. For each input, provide your reasoning before the resulting SQLite query.

                            Continue to reason and clarify until all objectives are met before you produce the output. Apply chain-of-thought reasoning: explain your logical steps, then present the final query.

                            Detailed Steps:

                            - Accept the following as input:
                                - Database schema (DDL)
                                - Sample data (SQL inserts, optional)
                                - User's natural language question or request
                            - Read and interpret the schema and, if provided, sample rows to infer column types and relationships.
                            - Break down the user's request into smaller logical components required to build the query.
                            - Reason through how each component maps to the tables/columns.
                            - Explain your reasoning process step by step (reasoning section).
                            - Only after presenting the step-wise reasoning, provide the final SQLite query (conclusion section).
                            - Ensure the query is syntactically valid SQLite and consistent with the schema.

                            **Output Format:**
                            Provide your response in JSON with the following structure:

                            ```json
                            {
                            "reasoning": "Step-by-step explanation of how the query was constructed, referencing specific schema details and requirements.",
                            "query": "The final SQLite statement matching the users request."
                            }
                            ```

                            **Examples:**
                            **Input DDL:**

                            ```sql
                            CREATE TABLE IF NOT EXISTS receipts (
                                receipt_id INTEGER PRIMARY KEY AUTOINCREMENT,
                                store_name TEXT NOT NULL,
                                total_cost REAL NOT NULL,
                                purchase_date TEXT NOT NULL
                            );

                            CREATE TABLE IF NOT EXISTS items (
                                item_id INTEGER PRIMARY KEY AUTOINCREMENT,
                                receipt_id INTEGER,
                                item_name TEXT NOT NULL,
                                item_cost REAL NOT NULL,
                                FOREIGN KEY(receipt_id) REFERENCES receipts(receipt_id)
                            );
                            ```

                            **Sample Data:**

                            ```sql
                            INSERT INTO receipts (receipt_id, store_name, total_cost, purchase_date) VALUES (1, 'Indomaret Setiabudi', 235500, '2025-09-01');
                            INSERT INTO items (receipt_id, item_name, item_cost) VALUES (1, 'Susu', 35000);
                            INSERT INTO items (receipt_id, item_name, item_cost) VALUES (1, 'Roti', 2100);
                            INSERT INTO receipts (receipt_id, store_name, total_cost, purchase_date) VALUES (2, 'RM Padang Pagi Sore', 1200.00, '2025-08-15');
                            INSERT INTO items (receipt_id, item_name, item_cost) VALUES (2, 'Rendang', 33000.00);
                            INSERT INTO items (receipt_id, item_name, item_cost) VALUES (2, 'Nasi', 12000.00);
                            ```

                            **Example 1:**
                            **User Input:**
                            Find all receipts from 'RM Padang Pagi Sore'.

                            **Output:**

                            ```json
                            {
                            "reasoning": "The user wants to see all information for receipts from a specific store. The 'receipts' table contains a 'store_name' column. I need to select all columns ('*') from the 'receipts' table and filter the results using a 'WHERE' clause where 'store_name' is 'RM Padang Pagi Sore'.",
                            "query": "SELECT * FROM receipts WHERE store_name = 'RM Padang Pagi Sore';"
                            }
                            ```

                            **Example 2:**
                            **User Input:**
                            What is the total cost of all items purchased from 'Warteg Pak Budi'?

                            **Output:**

                            ```json
                            {
                            "reasoning": "To answer this, I need to link items to their stores. The 'items' table has the cost of each item ('item_cost'), and the 'receipts' table has the 'store_name'. I will 'JOIN' the 'receipts' table with the 'items' table on their common 'receipt_id'. Then, I'll filter these joined results for receipts where the 'store_name' is 'Warteg Pak Budi'. Finally, I will use the 'SUM()' aggregate function on the 'item_cost' column to calculate the total.",
                            "query": "SELECT SUM(T2.item_cost) FROM receipts AS T1 JOIN items AS T2 ON T1.receipt_id = T2.receipt_id WHERE T1.store_name = 'Warteg Pak Budi';"
                            }
                            ```

                            **Example 3:**
                            **User Input:**
                            List all items bought at 'RM Padang Pagi Sore' on '2025-09-01'.

                            **Output:**

                            ```json
                            {
                            "reasoning": "The request asks for item names, which are in the 'items' table. The conditions for filtering ('store_name' and 'purchase_date') are in the 'receipts' table. I must first 'JOIN' the 'receipts' and 'items' tables using 'receipt_id'. After joining, I'll apply a 'WHERE' clause with two conditions combined using 'AND': 'store_name' must be 'RM Padang Pagi Sore' and 'purchase_date' must be '2025-09-01'. The final selection should only return the 'item_name' column.",
                            "query": "SELECT T2.item_name FROM receipts AS T1 JOIN items AS T2 ON T1.receipt_id = T2.receipt_id WHERE T1.store_name = 'RM Padang Pagi Sore' AND T1.purchase_date = '2025-09-01';"
                            }
                            ```

                            **More Information**
                            - Here's the list of already available restaurants in the database, do not put duplicate restaurant in there, reuse if possible
                            """
                            +
                            
                            str(restaurant_list)
                            
                            +
                            """
                            **Edge Cases & Considerations:**

                            - If the request is ambiguous, call out ambiguities in your reasoning.
                            - If user input cannot be fulfilled due to schema limitations, explain this in the reasoning.
                            - Always keep reasoning steps BEFORE the query in your response.

                            **Reminder:**
                            Your task is to transform user input into an SQLite query using the provided DDL (and optional sample SQL) with detailed step-by-step reasoning first, then the final query, formatted in the specified JSON structure.
                    """
                    }
                ]
            },
            {
            "role": "user",
            "content": [
                    {
                    "type": "input_text",
                    "text": user_input
                    }
                ]
            }
        ],
        text={
            "format": {
            "type": "text"
            },
            "verbosity": "medium"
        },
        reasoning={
            "effort": "medium"
        },
        tools=[]
        )
    
    data = json.loads(response.output[1].content[0].text)

    sql_query = data['query']

    return sql_query



def execute_query(query: str) -> str:
    try:
        print(f"User query: '{query}'")
        sql_query = text_to_sql(query)
        print(f"Generated SQL: {sql_query}")

        conn = None
        try:
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()

            # Case for SELECT Query
            if sql_query.strip().upper().startswith('SELECT'):
                cursor.execute(sql_query)
                results = cursor.fetchall()

                if not results:
                    return "Query executed, but no results were found."

                column_names = [description[0] for description in cursor.description]
                
                # Format as a list of dictionaries for JSON output
                json_results = [dict(zip(column_names, row)) for row in results]
                json_return = {
                    "result" : json_results,
                    "original_query" : query,
                    "sql_query" : sql_query
                }
                return jsonify(json_return)

            else:
                cursor.executescript(sql_query)
                conn.commit()
                return jsonify({"status": "success",  "original_query": query, "sql_query": sql_query, "message": "Action completed successfully. The database has been updated."})

        except sqlite3.Error as e:
            return jsonify({"status": "error", "original_query": query, "sql_query": sql_query, "message": f"A database error occurred: {e}"}), 500
        finally:
            if conn:
                conn.close()

    except Exception as e:
        return jsonify({"status": "error", "original_query": query, "message": f"An unexpected error occurred: {e}"}), 500

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