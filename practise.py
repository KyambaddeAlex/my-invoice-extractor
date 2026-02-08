import streamlit as st
import fitz  # PyMuPDF
import google.generativeai as genai
import pandas as pd
import json
import io
import os

# Page configuration
st.set_page_config(
    page_title="Invoice Data Extractor",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Password protection (optional - set to None to disable)
PASSWORD = "invoice2024"  # Change this to your desired password

def check_password():
    """Returns True if the user entered the correct password."""
    if "password_correct" not in st.session_state:
        st.session_state.password_correct = False
    
    if st.session_state.password_correct:
        return True
    
    st.markdown("### 🔒 Access Password Required")
    password = st.text_input("Enter password:", type="password")
    
    if password:
        if password == PASSWORD:
            st.session_state.password_correct = True
            st.success("✅ Access granted!")
            st.rerun()
        else:
            st.error("❌ Incorrect password")
    return False

# Check password before showing app
if PASSWORD and not check_password():
    st.stop()

# Custom CSS for better styling
st.markdown("""
    <style>
    .main-header {
        font-size: 2.5rem;
        color: #1f77b4;
        margin-bottom: 0.5rem;
    }
    .success-box {
        padding: 1rem;
        background-color: #d4edda;
        border-radius: 0.5rem;
        border-left: 5px solid #28a745;
    }
    </style>
""", unsafe_allow_html=True)

st.title("📄 Invoice Data Extractor")
st.markdown("Extract invoice information automatically using AI")

# Sidebar for configuration
with st.sidebar:
    st.header("⚙️ Configuration")
    
    # API Key input
    api_key = st.text_input(
        "Gemini API Key",
        type="password",
        help="Get your free API key at: https://aistudio.google.com/"
    )
    
    if api_key:
        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-2.0-flash')
            st.success("✅ API Key configured")
            api_configured = True
        except Exception as e:
            st.error(f"❌ Invalid API Key: {str(e)}")
            api_configured = False
    else:
        st.warning("⚠️ Please enter your API Key")
        api_configured = False

def extract_invoice_data(pdf_bytes, filename):
    """Extract invoice data from PDF bytes"""
    try:
        # Read the PDF from bytes
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()
        
        if not text.strip():
            return {"error": "No text found in PDF. Please try a different file."}

        # Ask the AI to find the specific details
        prompt = f"""
        Extract the following from this invoice text: 
        - Invoice Number
        - Date
        - Total Amount
        - Vendor Name
        
        Return ONLY a valid JSON object with these exact fields (use null if not found):
        {{"invoice_number": "...", "date": "...", "total_amount": "...", "vendor_name": "..."}}
        
        Invoice Text:
        {text}
        """
        
        response = model.generate_content(prompt)
        # Clean the response to ensure it's valid JSON
        clean_json = response.text.replace("```json", "").replace("```", "").strip()
        data = json.loads(clean_json)
        data["filename"] = filename
        return data
        
    except json.JSONDecodeError as e:
        return {"error": f"Failed to parse AI response: {str(e)}"}
    except Exception as e:
        return {"error": f"Processing error: {str(e)}"}

def convert_df_to_excel(df):
    """Convert dataframe to Excel bytes for download"""
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Invoices')
    return output.getvalue()

# Main content
if api_configured:
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("📤 Upload Invoices")
        uploaded_files = st.file_uploader(
            "Choose PDF files",
            type="pdf",
            accept_multiple_files=True,
            help="Select one or more PDF invoices to extract data from"
        )
    
    if uploaded_files:
        st.subheader("🔄 Processing")
        
        all_data = []
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for idx, uploaded_file in enumerate(uploaded_files):
            status_text.text(f"Processing {idx + 1}/{len(uploaded_files)}: {uploaded_file.name}")
            
            try:
                # Read file bytes
                pdf_bytes = uploaded_file.getvalue()
                
                # Extract data
                data = extract_invoice_data(pdf_bytes, uploaded_file.name)
                
                if "error" not in data:
                    all_data.append(data)
                    st.success(f"✅ {uploaded_file.name}")
                else:
                    st.error(f"❌ {uploaded_file.name}: {data['error']}")
                    
            except Exception as e:
                st.error(f"❌ {uploaded_file.name}: {str(e)}")
            
            progress_bar.progress((idx + 1) / len(uploaded_files))
        
        status_text.empty()
        
        # Display results
        if all_data:
            st.subheader("📊 Extracted Data")
            df = pd.DataFrame(all_data)
            st.dataframe(df, use_container_width=True)
            
            # Download button
            excel_data = convert_df_to_excel(df)
            st.download_button(
                label="📥 Download as Excel",
                data=excel_data,
                file_name="extracted_invoices.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="download_excel"
            )
        else:
            st.warning("⚠️ No data was successfully extracted from the uploaded files.")
else:
    st.info("👈 Please enter your Gemini API Key in the sidebar to get started")