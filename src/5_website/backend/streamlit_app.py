import streamlit as st
import sqlite3
import base64
import pandas as pd
from utils import extract_receipt_data_from_image, execute_query, normalize_response
from PIL import Image
import io

# Database setup
DB_NAME = 'receipts.db'

def create_database():
    """Create database tables if they don't exist"""
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

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS items (
                item_id INTEGER PRIMARY KEY AUTOINCREMENT,
                receipt_id INTEGER,
                item_name TEXT NOT NULL,
                item_cost REAL NOT NULL,
                FOREIGN KEY(receipt_id) REFERENCES receipts(receipt_id)
            )
        ''')
        
        conn.commit()
        return True
    except sqlite3.Error as e:
        st.error(f"Database error: {e}")
        return False
    finally:
        if conn:
            conn.close()

def handle_extract_receipt(uploaded_file):
    """Handle receipt extraction from uploaded image"""
    try:
        image_bytes = uploaded_file.read()
        base64_image = base64.b64encode(image_bytes).decode('utf-8')
        
        with st.spinner("Extracting receipt data..."):
            extracted_data = extract_receipt_data_from_image(base64_image)
        
        result = execute_query(f"Insert this receipt data into the database:\n\n {str(extracted_data)}")
        
        return {"status": "success", "data": extracted_data, "db_result": result}
    
    except ValueError as e:
        return {"status": "error", "message": str(e)}
    except Exception as e:
        return {"status": "error", "message": f"Unexpected error: {e}"}

def handle_query(query):
    """Handle database query"""
    if not query.strip():
        return {"status": "error", "message": "Query cannot be empty"}
    
    ai_response      = execute_query(query)
    natural_language = normalize_response(query, ai_response)

    ai_response["natural_language"] = natural_language
    
    return ai_response

def main():
    st.set_page_config(
        page_title="Receipt Processing App",
        page_icon="🧾",
        layout="wide"
    )
    
    st.title("Receipt Processing Application")
    st.markdown("Upload food purchase receipts and query your receipt data using natural language!")
    
    # Initialize database
    if create_database():
        st.success("Database initialized successfully!")
    
    # Create two columns for the main features
    col1, col2 = st.columns(2)
    
    with col1:
        st.header("Upload Receipt")
        st.markdown("Upload a food purchase receipt image to extract and store the data.")
        
        uploaded_file = st.file_uploader(
            "Choose a receipt image...",
            type=['png', 'jpg', 'jpeg'],
            help="Upload an image of your food purchase receipt"
        )
        
        if uploaded_file is not None:
            image = Image.open(uploaded_file)
            st.image(image, caption="Uploaded Receipt", use_column_width=True)
            
            # Process button
            if st.button(">>Extract Receipt Data<<", type="primary"):
                uploaded_file.seek(0)
                
                result = handle_extract_receipt(uploaded_file)
                
                if result["status"] == "success":
                    st.success("Receipt processed successfully!")
                    
                    # Display extracted data
                    data = result["data"]
                    st.subheader("Extracted Information:")
                    
                    col_info1, col_info2 = st.columns(2)
                    with col_info1:
                        st.metric("Store Name", data["store_name"])
                        st.metric("Total Cost", f"Rp{data['total_cost']:,.2f}")
                    with col_info2:
                        st.metric("Purchase Date", data["purchase_date"])
                        st.metric("Number of Items", len(data["items"]))
                    
                    if data["items"]:
                        st.subheader("Items:")
                        items_df = pd.DataFrame(data["items"])
                        st.dataframe(items_df, use_container_width=True)
                    
                    # Display database insertion result
                    db_result = result["db_result"]
                    if db_result["status"] == "success":
                        st.info(f"{db_result['message']} (Receipt succesfully inserted)")
                    else:
                        st.error(f" Database Error: {db_result['message']}")
                        
                else:
                    st.error(f" Error: {result['message']}")
    
    with col2:
        st.header("Query Receipt Data")
        st.markdown("Ask questions about your receipt data using natural language.")
        
        # Initialize session state for query if it doesn't exist
        if 'selected_query' not in st.session_state:
            st.session_state.selected_query = ""
        
        # Example queries
        st.markdown("**Example queries:**")
        example_queries = [
            "Show me all receipts from this month",
            "What's the total amount I spent at McDonalds?",
            "List all items I bought yesterday",
            "Which store did I spend the most money at?",
            "Show me receipts with total cost over Rp50000"
        ]
        
        for i, example in enumerate(example_queries):
            if st.button(f"{example}", key=f"example_{i}"):
                st.session_state.selected_query = example
                st.rerun()
        
        # Query input - use session state value as default
        query = st.text_area(
            "Enter your query:",
            value=st.session_state.selected_query,
            placeholder="e.g., 'Show me all receipts from last week' or 'What's the total amount I spent at McDonald's?'",
            height=100
        )
        
        # Update session state when user types in the text area
        if query != st.session_state.selected_query:
            st.session_state.selected_query = query
        
        # Query button
        if st.button("🔍 Execute Query", type="primary"):
            if query.strip():
                with st.spinner("Processing query..."):
                    result = handle_query(query)
                
                if result["status"] == "success":
                    st.success("Query executed successfully!")
                    
                    # Display query information
                    with st.expander("Query Details"):
                        st.write(f"**Original Query:** {result['original_query']}")
                        st.write(f"**Generated SQL:** `{result['sql_query']}`")
                    
                    
                    # Display results
                    st.write(result["natural_language"])
                    
                    if "result" in result and result["result"]:
                        st.subheader("Results:")
                        results_df = pd.DataFrame(result["result"])
                        st.dataframe(results_df, use_container_width=True)
                        
                        # Download results as CSV
                        csv = results_df.to_csv(index=False)
                        st.download_button(
                            label="Download Results as CSV",
                            data=csv,
                            file_name="query_results.csv",
                            mime="text/csv"
                        )
                    elif "message" in result:
                        st.info(result["message"])
                        
                else:
                    st.error(f" Error: {result['message']}")
                    if "sql_query" in result:
                        st.code(f"Generated SQL: {result['sql_query']}")
            else:
                st.warning("Please enter a query first!")
    
    with st.sidebar:
        st.header("Database Statistics")
        
        try:
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            
            # Informasi untuk Sidebar - Get total receipts
            cursor.execute("SELECT COUNT(*) FROM receipts")
            total_receipts = cursor.fetchone()[0]
            
            # Informasi untuk Sidebar -Get total items
            cursor.execute("SELECT COUNT(*) FROM items")
            total_items = cursor.fetchone()[0]
            
            # Informasi untuk Sidebar - Get total spending
            cursor.execute("SELECT SUM(total_cost) FROM receipts")
            total_spending = cursor.fetchone()[0] or 0
            
            # Informasi untuk Sidebar - Get unique stores
            cursor.execute("SELECT COUNT(DISTINCT store_name) FROM receipts")
            unique_stores = cursor.fetchone()[0]
            
            st.metric("Total Receipts", total_receipts)
            st.metric("Total Items", total_items)
            st.metric("Total Spending", f"Rp{total_spending:,.2f}")
            st.metric("Unique Stores", unique_stores)
            
            conn.close()
            
        except sqlite3.Error as e:
            st.error(f"Error fetching statistics: {e}")
        
        st.markdown("---")
        st.markdown("**How to use:**")
        st.markdown("1. Upload a receipt image on the left")
        st.markdown("2. Click 'Extract Receipt Data' to process")
        st.markdown("3. Ask questions about your data on the right")
        st.markdown("4. View results and download as needed")

if __name__ == "__main__":
    main()
