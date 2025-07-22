import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from datetime import datetime
import pytz
import json

# --- Google Sheets API setup ---
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

# Get creds from secrets
service_account_info = st.secrets["gcp_service_account"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(service_account_info, scope)
client = gspread.authorize(creds)

# Get sheet key from secrets
sheet_key = st.secrets["sheets"]["sheet_key"]

# Open your Google Sheet
orders_sheet = client.open_by_key(sheet_key).worksheet("Orders")

# --- Style ---
st.markdown(
    """
    <style>
    .price {
        font-size: 24px;
        font-weight: bold; 
    }

    .footer-desktop {
        display: block;
        text-align: center;
    }
    .footer-mobile {
        display: none;
    }

    @media (max-width: 768px) {
        .footer-desktop {
            display: none;
        }
        .footer-mobile {
            display: block;
            text-align: left;
        }
    }

    .footer {
        position: fixed;
        left: 0;
        bottom: 0;
        width: 100%;
        background-color: #f0f6ff;
        color: #222;
        padding: 10px;
        font-size: 12px;
        border-top: 1px solid #cce0ff;
    }
    </style>
    """,
    unsafe_allow_html=True
)

with st.container():
    st.image("banner.jpg", use_container_width=True)
    st.title("Lis Dice Form")
    st.image("prizepool.jpg", use_container_width=True)
    st.markdown(
        "<div>Mau ikut main Dice bareng Irene? Isi form ini biar order kamu langsung tercatat!</div><br/>",
        unsafe_allow_html=True
    )

    name = st.text_input("Nama Kamu")
    wa_number = st.text_input("Nomor WhatsApp", placeholder="0891234567788")
    address = st.text_area(
        "Alamat Lengkap", 
        placeholder="Contoh: Jl. Medan Merdeka Utara No. 3, Kel. Gambir, Kec. Gambir, Kota Jakarta Pusat, DKI Jakarta 10110"
    )
    st.caption("Harap isi lengkap: nama jalan, kelurahan, kecamatan, kota/kabupaten, provinsi, dan kode pos.")

    quantity = st.number_input("Jumlah Pull", min_value=1, step=1)

    item_name = "Dice with Irene"
    unit_price = 35000
    total_price = unit_price * quantity

    st.markdown(f'<div class="price">Harga per Item: Rp {unit_price:,.0f}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="price">Total Harga: Rp {total_price:,.0f}</div><br/>', unsafe_allow_html=True)

    if st.button("Submit Order"):
        if not name.strip() or not wa_number.strip() or not address.strip():
            st.error("Tolong isi Nama Kamu, Nomor WhatsApp, dan Alamat Lengkap.")
        elif not wa_number.strip().isdigit():
            st.error("Nomor WhatsApp harus berupa angka saja (tanpa spasi atau simbol).")
        else:
            tz = pytz.timezone("Asia/Jakarta")
            current_time = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")

            orders_sheet.append_row([
                current_time,
                name,
                wa_number,
                address,
                item_name,
                unit_price,
                f"{quantity} pcs",
                total_price
            ])
            
            st.success("Order submitted! Silakan lanjut ke pembayaran sesuai instruksi di bawah.")

            st.markdown(f"""
            ## Instruksi Pembayaran  
            Transfer ke: **BCA 2530244574 a/n PT. Licht Cahaya Abadi**  
            Mohon cantumkan note:
            - `"Pembayaran atas nama {name}"`  

            Setelah transfer, harap konfirmasi via WhatsApp: **+62 819-5255-5657**
            """)

            st.write("---")
            st.subheader("Order Summary")
            st.write(f"**Nama:** {name}")
            st.write(f"**Nomor WhatsApp:** {wa_number}")
            st.write(f"**Alamat:** {address}")
            st.write(f"**Item:** {item_name}")
            st.write(f"**Jumlah:** {quantity} pcs")
            st.write(f"**Harga per Item:** Rp {unit_price:,.0f}")
            st.write(f"**Total Harga:** Rp {total_price:,.0f}")

    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown(
    """
    <div class="footer footer-desktop">
        &copy; 2025 Lichtschein Hobby Store | Follow @lishobbystore on Instagram untuk info & diskon terbaru! 🚀
    </div>
    <div class="footer footer-mobile">
        Follow @lishobbystore di Instagram buat info & diskon!
    </div>
    """,
    unsafe_allow_html=True
)
