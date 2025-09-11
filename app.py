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

# ── Helpers to read config values from GachaConfig
def get_config_value(ws_name: str, cell: str):
    try:
        ws = client.open_by_key(sheet_key).worksheet(ws_name)
        val = ws.acell(cell).value
        if val is None:
            return None
        return str(val).strip()
    except Exception:
        return None

def get_config_int(ws_name: str, cell: str):
    try:
        ws = client.open_by_key(sheet_key).worksheet(ws_name)
        val = ws.acell(cell).value
        if val is None or str(val).strip() == "":
            return None
        return int(str(val).strip())
    except Exception:
        return None

# ── Read remaining pulls (A1), A–D status (A2:D2), and E stock (E2)
def get_remaining_pulls():
    return get_config_int("GachaConfig", "A1")  # same cell as before

remaining_pulls = get_remaining_pulls()
status_a = get_config_value("GachaConfig", "A2")  # "Available" / "Pulled"
status_b = get_config_value("GachaConfig", "B2")
status_c = get_config_value("GachaConfig", "C2")
status_d = get_config_value("GachaConfig", "D2")
stock_e  = get_config_int("GachaConfig", "E2")    # integer stock for Blokees

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
    st.title("Lis Gacha Form")
    st.markdown(
        "<div>Mau ikut main gacha bareng Irene? Isi form ini biar order kamu langsung tercatat!</div><div>IDR 40.000 per Pull!!!</div><br/>",
        unsafe_allow_html=True
    )

    # ── Single BIG info box: remaining pulls + A–E status
    # Normalize display text
    def status_text(s):
        return s if (s and s.lower() in ["available", "pulled"]) else (s or "?")

    rp_text = (
        f"<b>{remaining_pulls}</b>" if remaining_pulls is not None else
        "<i>belum di-setup</i>"
    )
    a_text = status_text(status_a)
    b_text = status_text(status_b)
    c_text = status_text(status_c)
    d_text = status_text(status_d)
    e_text = (
        f"tersisa <b>{stock_e}</b>" if stock_e is not None else
        "stok belum di-setup"
    )

    info_html = f"""
    <div style="
        padding:18px;
        background:#f8fbff;
        border:1px solid #cfe2ff;
        border-left:6px solid #1a73e8;
        border-radius:10px;
        margin:12px 0 16px 0;
        line-height:1.6;
        font-size:16px;
    ">
      <div style="font-size:20px; font-weight:800; color:#1a73e8; margin-bottom:10px;">
        📦 Status Hadiah & Kuota
      </div>
      <div>🎯 Sisa kuota pull hari ini: {rp_text}</div>
      <div><strong>A</strong> : Nendoroid - Bebas kamu pilih &nbsp; → {a_text}</div>
      <div><strong>B</strong> : Nendoroid - pilihan Lis &nbsp; → {b_text}</div>
      <div><strong>C</strong> : Prize Figure &nbsp; → {c_text}</div>
      <div><strong>D</strong> : Plush Aranara &nbsp; → {d_text}</div>
      <div><strong>E</strong> : Blokees &nbsp; → {e_text}</div>
    </div>
    """
    st.markdown(info_html, unsafe_allow_html=True)

    # If remaining pulls explicitly 0 or below, stop early
    if remaining_pulls is not None and remaining_pulls <= 0:
        st.error("Kuota pull untuk hari ini sudah habis.")
        st.stop()

    # Inputs
    name = st.text_input("Nama Kamu")
    wa_number = st.text_input("Nomor WhatsApp", placeholder="0891234567788")
    address = st.text_area(
        "Alamat Lengkap", 
        placeholder="Contoh: Jl. Medan Merdeka Utara No. 3, Kel. Gambir, Kec. Gambir, Kota Jakarta Pusat, DKI Jakarta 10110"
    )
    st.caption("Harap isi lengkap: nama jalan, kelurahan, kecamatan, kota/kabupaten, provinsi, dan kode pos.")

    # Cap quantity to remaining if it exists
    if remaining_pulls is None:
        quantity = st.number_input("Jumlah Pull", min_value=1, step=1)
    else:
        quantity = st.number_input("Jumlah Pull", min_value=1, max_value=remaining_pulls, step=1)

    item_name = "Gacha with Irene"
    unit_price = 40000
    total_price = unit_price * quantity

    st.markdown(f'<div class="price">Harga per Item: Rp {unit_price:,.0f}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="price">Total Harga: Rp {total_price:,.0f}</div><br/>', unsafe_allow_html=True)

    # Disable submit if remaining exists and is 0 (handled above), or if quantity > remaining (guard)
    submit_disabled = (remaining_pulls is not None and remaining_pulls <= 0)

    if st.button("Submit Order", disabled=submit_disabled):
        if not name.strip() or not wa_number.strip() or not address.strip():
            st.error("Tolong isi Nama Kamu, Nomor WhatsApp, dan Alamat Lengkap.")
        elif not wa_number.strip().isdigit():
            st.error("Nomor WhatsApp harus berupa angka saja (tanpa spasi atau simbol).")
        elif remaining_pulls is not None and quantity > remaining_pulls:
            st.error("Jumlah pull melebihi sisa kuota.")
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
        &copy; 2025 Lichtschein Hobby Store | Follow @lishobbystore di Instagram untuk info & diskon terbaru! 🚀
    </div>
    <div class="footer footer-mobile">
        Follow @lishobbystore di Instagram buat info & diskon!
    </div>
    """,
    unsafe_allow_html=True
)
