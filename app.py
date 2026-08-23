import streamlit as st
import pandas as pd
import textwrap

from database import (
    create_tables,
    add_vendor,
    add_material,
    add_rfq,
    add_quotation,
    add_quotation_line,
    get_comparative_data,
    add_approval,
    get_dashboard_metrics,
    get_recent_approvals,
    get_latest_material_price,
    generate_material_code,
    generate_vendor_code,
    generate_rfq_number,         # <--- NEW
    close_order,
    get_closed_orders_report,
    get_all_vendors,
    get_all_materials,
    get_all_rfqs,
    check_vendor_exists,
    check_material_exists,
    get_approved_vendor_for_rfq,  # <--- NEW
    is_order_closed
)

# Create the database tables
create_tables()


# Page settings
st.set_page_config(
    page_title="Procurement System",
    page_icon="📦",
    layout="wide"
)

# Hide the Streamlit default menu and GitHub icon but KEEP sidebar toggle
hide_streamlit_style = """
    <style>
    #MainMenu {visibility: hidden;}
    [data-testid="stToolbar"] {visibility: hidden;}
    </style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)   

# --- SECURITY GATE ---
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
    st.session_state["current_user"] = ""

if not st.session_state["logged_in"]:
    st.title("🔒 Procurement System Login")

    username = st.text_input("Username")
    password_guess = st.text_input("Password", type="password")
    
    if st.button("Log In"):
        if username in st.secrets["passwords"] and password_guess == st.secrets["passwords"][username]:
            st.session_state["logged_in"] = True
            st.session_state["current_user"] = username
            st.rerun()  # Unlocks the app
        else:
            st.error("Incorrect Username or Password. Please try again.")
    
    st.stop()
    
# Application title
st.title("📦 Procurement System")
st.write("V0.1 - Vendor and Material Master")


# Main Page Menu
menu = st.radio(
    "Select Module",
    [
        "Dashboard",
        "Master Data View",
        "Vendor Master",
        "Material Master",
        "New RFQ",
        "Quotation Entry",
        "Comparative Statement",
        "Vendor Approval",
        "Order Closure & Report"
    ],
    horizontal=True  # This makes it lay flat across the middle of your screen!
)
st.markdown("---") # Adds a nice visual line under your menu

# Dashboard
if menu == "Dashboard":
    st.header("Dashboard")
    st.write("Overview of Procurement Activities")

    # Fetch the numbers from the database
    total_rfqs, total_quotations, total_approvals = get_dashboard_metrics()

    # Create 3 columns for beautiful metric cards
    col1, col2, col3 = st.columns(3)
    col1.metric("Total RFQs", total_rfqs)
    col2.metric("Quotations Received", total_quotations)
    col3.metric("Vendor Approvals", total_approvals)

    st.markdown("---")
    
    # --- NEW MATERIAL PRICE LOOKUP SECTION ---
    st.subheader("Chemical & Material Price Lookup")
    st.write("Search for the latest negotiated price of any material in the system.")
    
    with st.form("price_lookup_form"):
        # Users can type the chemical name or the exact code
        search_term = st.text_input("Enter Material Name or Code")
        search_button = st.form_submit_button("Search Latest Price")
        
        if search_button:
            if search_term == "":
                st.warning("Please enter a material to search.")
            else:
                try:
                    price_data = get_latest_material_price(search_term)
                    
                    if price_data:
                        st.success(f"Latest pricing history found for **{price_data['Material Name']}**")
                        
                        # Display the results in 3 clean columns
                        p_col1, p_col2, p_col3, p_col4 = st.columns(4)
                        p_col1.metric("Latest Price", f"{price_data['Latest Price']}")
                        # Added the quantity metric!
                        p_col2.metric("Quantity", f"{price_data['Quantity']}")
                        # Combined Vendor Code and Name!
                        p_col3.metric("Vendor", f"{price_data['Vendor Name']}")
                        p_col4.metric("Date", price_data['Date'])
                    else:
                        st.info("No pricing history found for that material.")
                except Exception as error:
                    st.error(f"Error: {error}")
                    
    st.markdown("---")
    
    st.subheader("Recent Approvals")
    
    # Fetch and display the recent approvals table
    recent_approvals = get_recent_approvals()
    if len(recent_approvals) > 0:
        st.dataframe(recent_approvals, use_container_width=True)
    else:
        st.info("No approvals have been processed yet.")

# Vendor Master
elif menu == "Vendor Master":
    st.header("Vendor Master")
    st.write("Add a new vendor to the system.")
    
    # Category is placed first so the system can generate the code!
    category = st.selectbox("Category *", ["Raw Material", "Packaging", "Service"])
    
    # Auto-generate the code in real-time
    auto_vendor_code = generate_vendor_code(category)
    
    # Display the code but lock it (disabled=True) so the user cannot ruin it
    st.text_input("Vendor Code (Auto-Generated & Locked) *", value=auto_vendor_code, disabled=True)
    
    vendor_name = st.text_input("Vendor Name *")
    contact_person = st.text_input("Contact Person")
    email = st.text_input("Email")
    phone = st.text_input("Phone Number")
    address = st.text_area("Registered Address")
    tax_number = st.text_input("Tax / GST Number")
    status = st.selectbox("Status", ["Active", "Inactive", "Blacklisted"])
    
    if st.button("Save Vendor"):
        if vendor_name == "":
            st.error("Vendor Name is required.")
        else:
            # Check for duplicates before saving!
            existing_code = check_vendor_exists(vendor_name)
            
            if existing_code:
                st.error(f"🛑 Stop! The vendor '{vendor_name}' is already registered under Code: {existing_code}")
            else:
                try:
                    add_vendor(auto_vendor_code, vendor_name, contact_person, email, phone, address, tax_number, category, status)
                    st.success(f"Vendor {vendor_name} saved successfully with Code: {auto_vendor_code}!")
                except Exception as error:
                    st.error(f"Error: {error}")

# Material Master
elif menu == "Material Master":
    st.header("Material Master")
    st.write("Add a new material to the catalog.")

    # Category triggers the auto-generation
    category = st.selectbox("Category *", ["Raw Material", "Packaging", "Indirect"])
    
    # Auto-generate the code
    auto_material_code = generate_material_code(category)
    
    # Lock the code field
    st.text_input("Material Code (Auto-Generated & Locked) *", value=auto_material_code, disabled=True)
    
    material_name = st.text_input("Material Name *")
    description = st.text_area("Detailed Description")
    unit = st.selectbox("Unit of Measure", ["KG", "Litre", "Ton", "Nos", "Meters", "Box"])
    standard_make = st.text_input("Standard Make / Brand (Optional)")
    status = st.selectbox("Status", ["Active", "Inactive", "Obsolete"])

    if st.button("Save Material"):
        if material_name == "":
            st.error("Material Name is required.")
        else:
            # Check for duplicates before saving!
            existing_code = check_material_exists(material_name)
            
            if existing_code:
                st.error(f"🛑 Stop! The material '{material_name}' already exists in the catalog under Code: {existing_code}")
            else:
                try:
                    add_material(auto_material_code, material_name, description, category, unit, standard_make, status)
                    st.success(f"Material {material_name} saved successfully with Code: {auto_material_code}!")
                except Exception as error:
                    st.error(f"Error: {error}")

# New RFQ
elif menu == "New RFQ":
    st.header("Create New RFQ")
    
    # Auto-generate the RFQ code
    auto_rfq_code = generate_rfq_number()
    
    with st.form("rfq_form"):
        # Lock the ID field so it can't be messed up
        st.text_input("RFQ Number (Auto-Generated & Locked) *", value=auto_rfq_code, disabled=True)
        
        rfq_date = st.date_input("RFQ Date")
        product_details = st.text_area("Product Details")
        buyer = st.text_input("Buyer / Sourcing Analyst")
        
        # Fixed department spellings
        department = st.selectbox("Department", ["Mechanical", "Electrical", "IT", "Civil", "HR", "Quality Control", "EHS", "Admin", "R&D", "Scale Up", "Business Development", "Knowledge Management", "Quality Assurance", "Sales", "Technology Development", "Process Safety"])
        
        required_date = st.date_input("Required Date")
        category = st.selectbox("Material Category", ["Chemical Raw Material", "Intermediate", "Packaging", "Samples","Consumables","Indirect"])
        currency = st.selectbox("Currency", ["INR", "USD", "EUR"])
        location = st.text_input("Plant / Location")
        status = st.selectbox("Status", ["Open", "Closed", "Cancelled"])
        
        save_rfq = st.form_submit_button("Save RFQ")

        if save_rfq:
            try:
                # Pass auto_rfq_code and product_details!
                add_rfq(auto_rfq_code, str(rfq_date), product_details, buyer, department, str(required_date), category, currency, location, status)
                st.success(f"✅ RFQ {auto_rfq_code} created successfully!")
            except Exception as error:
                st.error(f"Error: {error}")

# Quotation Entry
elif menu == "Quotation Entry":
    st.header("Enter Vendor Quotation")
    
    # Fetch data for our dropdowns
    rfqs = get_all_rfqs()
    vendors = get_all_vendors()
    materials = get_all_materials()
    
    # If the database is empty, stop them from trying to enter a quote
    if not rfqs or not vendors or not materials:
        st.warning("⚠️ You need at least one RFQ, one Vendor, and one Material created before you can enter a quotation.")
    else:
        # Format the options for the dropdowns
        vendor_choices = [f"{v['Vendor Code']} - {v['Vendor Name']}" for v in vendors]
        material_choices = [f"{m['Material Code']} - {m['Material Name']}" for m in materials]
        
        with st.form("quotation_form"):
            st.subheader("1. Main Quotation Details")
            
            # Swapped text_inputs for selectboxes!
            selected_rfq = st.selectbox("RFQ Number *", rfqs)
            selected_vendor = st.selectbox("Vendor *", vendor_choices)
            
            quotation_date = st.date_input("Quotation Date")
            payment_terms = st.text_input("Payment Terms (e.g., 30 Days Credit)")
            incoterms = st.selectbox("Incoterms", ["EXW", "FCA", "FOB", "CIF", "DAP", "DDP", "Other"])
            status = st.selectbox("Status", ["Received", "In Review", "Negotiated", "Finalized"])

            st.subheader("2. Material Line Item")
            
            # Swapped text_input for selectbox!
            selected_material = st.selectbox("Material *", material_choices)
            # --- NEW FIELD ADDED HERE ---
            vendor_description = st.text_area("Vendor's Quoted Product Details / Deviations")
            
            quantity = st.number_input("Quantity", min_value=0.0, step=1.0)
            basic_price = st.number_input("Basic Price", min_value=0.0, step=1.0)
            negotiated_price = st.number_input("Negotiated Price", min_value=0.0, step=1.0)
            delivery_days = st.number_input("Delivery Lead Time (Days)", min_value=0, step=1)
            make = st.text_input("Make / Brand")

            save_quotation = st.form_submit_button("Save Quotation")

            if save_quotation:
                # SAFETY CHECKS: Prevent zero values!
                if quantity <= 0:
                    st.error("❌ Quantity must be greater than zero.")
                elif basic_price <= 0 or negotiated_price <= 0:
                    st.error("❌ Price must be greater than zero.")
                else:
                    try:
                        # Extract just the codes from the selected dropdown strings
                        vendor_code = selected_vendor.split(" - ")[0]
                        material_code = selected_material.split(" - ")[0]
                        
                        add_quotation(selected_rfq, vendor_code, str(quotation_date), payment_terms, incoterms, status)
                        add_quotation_line(selected_rfq, vendor_code, material_code, quantity, basic_price, negotiated_price, delivery_days, make, vendor_description)
                        
                        st.success("✅ Quotation and Material Line saved successfully.")
                    except Exception as error:
                        st.error(f"Error: {error}")


# Odoo-Style Compare & Choose Matrix (Printable & Smart)
elif menu == "Comparative Statement":
    st.header("RFQ Comparison Matrix & Approval Sheet")
    st.write("Printable overview of quotations for management permission.")

    rfq_number = st.text_input("Enter RFQ Number to Compare (e.g., RFQ-2026-001)")
    
    if rfq_number:
        data = get_comparative_data(rfq_number)
        
        if len(data) == 0:
            st.warning(f"No quotations found for {rfq_number}.")
        else:
            df = pd.DataFrame(data)
            
            # 1. SMART RANKING: Sort by Lowest Price, then Fastest Delivery
            df = df.sort_values(by=['Total Price', 'Delivery (Days)']).reset_index(drop=True)
            # Add a Ranking column (1 is best, 2 is mid, 3 is high)
            df.insert(0, 'System Rank', range(1, len(df) + 1))
            
            # 2. DROP INTERNAL CODES: Keep it clean for printing
            if 'Vendor Code' in df.columns:
                df = df.drop(columns=['Vendor Code', 'Material'])
            
            # 3. TEXT WRAPPING: Keep text to max ~60 words/clean lines for printing
            def wrap_text(text):
                if isinstance(text, str):
                    words = text.split()
                    if len(words) > 60:
                        words = words[:60] + ["..."]
                    return textwrap.fill(" ".join(words), width=80)
                return text
            
            # Apply wrapping to text-heavy columns like Payment Terms
            if 'Payment Terms' in df.columns:
                df['Payment Terms'] = df['Payment Terms'].apply(wrap_text)

            # Display the clean, ranked table
            st.dataframe(df, use_container_width=True)
            
            st.info("🖨️ Press Command+P (Mac) or Ctrl+P (Windows) to print this clean sheet for L2/L3 approval.")
            
            st.markdown("---")
            
            # The "Choose" Button Interface (Hidden on print)
            st.subheader("Choose Winning Vendor")
            # We must fetch the raw data again just to get the codes for the dropdown logic
            raw_vendor_choices = [f"{row['Vendor Code']} - {row['Vendor Name']}" for row in data]
            
            with st.form("choose_vendor_form"):
                selected_vendor = st.selectbox("Select Vendor to Approve *", raw_vendor_choices)
                approver_name = st.text_input("Approver Name *")
                approval_reason = st.selectbox("Reason for Choice", ["Lowest Total Price (Rank 1)", "Fastest Delivery", "Best Payment Terms", "Quality Requirement", "Other"])
                
                if st.form_submit_button("Confirm & Approve Purchase"):
                    if approver_name == "":
                        st.error("Approver Name is required.")
                    else:
                        try:
                            vendor_code = selected_vendor.split(" - ")[0]
                            add_approval(rfq_number, vendor_code, approver_name, "Approved", approval_reason, "")
                            st.success(f"Success! Vendor {vendor_code} approved for {rfq_number}.")
                        except Exception as error:
                            st.error(f"Error saving approval: {error}")

# Vendor Approval
elif menu == "Vendor Approval":
    st.header("Vendor Approval")
    st.write("Approve or reject a recommended vendor quotation.")
    
    # 1. Fetch data for dropdowns
    rfqs = get_all_rfqs()
    vendors = get_all_vendors()
    
    if not rfqs or not vendors:
        st.warning("⚠️ You need at least one RFQ and Vendor created before approving.")
    else:
        # Format the vendor dropdown options
        vendor_choices = [f"{v['Vendor Code']} - {v['Vendor Name']}" for v in vendors]
        
        with st.form("approval_form"):
            # 2. Swap text_input for selectbox!
            selected_rfq = st.selectbox("RFQ Number *", rfqs)
            selected_vendor = st.selectbox("Selected Vendor *", vendor_choices)
            
            approver_name = st.text_input("Approver Name (Manager) *")
            
            approval_status = st.selectbox(
                "Approval Status",
                ["Approved", "Rejected"]
            )
            
            approval_reason = st.selectbox(
                "Reason for Decision",
                [
                    "Lowest Price",
                    "Better Delivery",
                    "Better Payment Terms",
                    "Approved Make",
                    "Quality Requirement",
                    "Existing Supplier",
                    "Emergency Requirement",
                    "Other"
                ]
            )
            
            deviation_reason = st.text_area("Explanation / Deviation Reason (if bypassing the lowest price)")
            
            save_approval = st.form_submit_button("Submit Approval")
            
            if save_approval:
                if not selected_rfq or not selected_vendor or approver_name == "":
                    st.error("RFQ Number, Vendor Code, and Approver Name are required.")
                elif approval_status == "Approved" and get_approved_vendor_for_rfq(selected_rfq):
                    # SAFETY CHECK: Prevent approving an already approved RFQ
                    st.error(f"🛑 Stop! RFQ {selected_rfq} has already been approved.")
                else:
                    try:
                        # 3. Extract the exact vendor code from the dropdown string
                        vendor_code = selected_vendor.split(" - ")[0]
                        
                        add_approval(selected_rfq, vendor_code, approver_name, approval_status, approval_reason, deviation_reason)
                        st.success(f"Vendor quotation {approval_status.lower()} successfully.")
                    except Exception as error:
                        st.error(f"Error: {error}")

# Master Data View
elif menu == "Master Data View":
    st.header("Master Data Records")
    st.write("Reference list of all registered Vendors and Materials.")
    
    # This creates two separate clickable windows on the same page
    tab1, tab2 = st.tabs(["🏭 Vendor List", "📦 Material List"])
    
    with tab1:
        st.subheader("All Registered Vendors")
        vendor_data = get_all_vendors()
        if len(vendor_data) > 0:
            st.dataframe(vendor_data, use_container_width=True)
        else:
            st.info("No vendors registered yet.")
            
    with tab2:
        st.subheader("All Registered Materials")
        material_data = get_all_materials()
        if len(material_data) > 0:
            st.dataframe(material_data, use_container_width=True)
        else:
            st.info("No materials registered yet.")

# Order Closure & Report
elif menu == "Order Closure & Report":
    st.header("Goods Receipt & Order Closure")
    st.write("Mark orders as delivered, apply GST, and view financial savings.")
    
    with st.form("closure_form"):
        st.subheader("1. Mark Order as Delivered")
        rfq_number = st.text_input("RFQ Number (e.g., RFQ-2026-001) *")
        gst_percentage = st.number_input("Applicable GST (%)", min_value=0.0, step=0.1)
        
        submit_closure = st.form_submit_button("Close Order & Calculate")
        
        if submit_closure:
            if rfq_number == "":
                st.error("RFQ Number is required.")
            
            # --- THE NEW SAFETY LOCK ---
            elif is_order_closed(rfq_number):
                st.error(f"🛑 Stop! Order {rfq_number} has already been closed and delivered. You cannot close it twice.")
            # ---------------------------
            
            else:
                try:
                    # Auto-detect winning vendor
                    approved_vendor = get_approved_vendor_for_rfq(rfq_number)
                    
                    if not approved_vendor:
                        st.error(f"🛑 No approved vendor found for {rfq_number}. Please approve a vendor in the 'Comparative Statement' tab first.")
                    else:
                        close_order(rfq_number, approved_vendor, gst_percentage)
                        st.success(f"✅ Order {rfq_number} successfully marked as Closed - Delivered with Vendor {approved_vendor}!")
                except Exception as error:
                    st.error(f"Error: {error}")
            
    st.markdown("---")
    st.subheader("2. Final Delivered Orders Report")
    st.write("This table automatically calculates your negotiated discount % and final landed price including GST.")
    
    try:
        report_data = get_closed_orders_report()
        if len(report_data) > 0:
            st.dataframe(report_data, use_container_width=True)
        else:
            st.info("No closed orders found yet.")
    except Exception as error:
        st.error(f"Waiting for database tables to update... (Error: {error})")

# Must come before the login gate, at the very top of app.py
query_params = st.query_params
token = query_params.get("token")

if token:
    link_info = validate_vendor_link(token)

    if not link_info:
        st.error("🔒 This link is invalid or has expired. Please contact your procurement contact.")
        st.stop()

    st.title("📋 Quotation Submission")
    st.write(f"Submitting as **{link_info['vendor_name']}** for RFQ **{link_info['rfq_number']}**")
    st.info(link_info["product_details"])

    materials = get_all_materials()
    material_choices = [f"{m['Material Code']} - {m['Material Name']}" for m in materials]

    with st.form("vendor_quote_form"):
        selected_material = st.selectbox("Material *", material_choices)
        vendor_description = st.text_area("Your Quoted Product Details / Deviations")
        quantity = st.number_input("Quantity", min_value=0.0, step=1.0)
        basic_price = st.number_input("Basic Price", min_value=0.0, step=1.0)
        negotiated_price = st.number_input("Your Best Price", min_value=0.0, step=1.0)
        delivery_days = st.number_input("Delivery Lead Time (Days)", min_value=0, step=1)
        payment_terms = st.text_input("Payment Terms")
        incoterms = st.selectbox("Incoterms", ["EXW", "FCA", "FOB", "CIF", "DAP", "DDP", "Other"])
        make = st.text_input("Make / Brand")

        submitted = st.form_submit_button("Submit Quotation")

        if submitted:
            if quantity <= 0 or basic_price <= 0 or negotiated_price <= 0:
                st.error("Quantity and prices must be greater than zero.")
            else:
                material_code = selected_material.split(" - ")[0]
                add_quotation(link_info["rfq_number"], link_info["vendor_code"],
                               str(datetime.date.today()), payment_terms, incoterms, "Received")
                add_quotation_line(link_info["rfq_number"], link_info["vendor_code"],
                                    material_code, vendor_description, quantity,
                                    basic_price, negotiated_price, delivery_days, make)
                mark_vendor_link_submitted := mark_link_submitted(token)
                st.success("✅ Thank you! Your quotation has been received.")

    st.stop()   # <-- non-negotiable: prevents fallthrough into the internal app