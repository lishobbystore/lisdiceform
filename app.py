import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import pytz

# --- Google Sheets API setup ---
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]
service_account_info = st.secrets["gcp_service_account"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(service_account_info, scope)
client = gspread.authorize(creds)

sheet_key = st.secrets["sheets"]["sheet_key"]
orders_sheet = client.open_by_key(sheet_key).worksheet("Orders")

# === NEW: cache worksheet handle (resource) ===
@st.cache_resource(show_spinner=False)
def get_spreadsheet_and_config():
    ss = client.open_by_key(sheet_key)
    cfg = ss.worksheet("GachaConfig")
    return ss, cfg

ss, cfg_ws = get_spreadsheet_and_config()

# === NEW: single batched read + cache ===
@st.cache_data(ttl=120, show_spinner=False)
def read_config_range():
    # Expecting:
    # Row 1: A1..E1 -> [remaining_pulls, (unused), (unused), (unused), (unused)]
    # Row 2: A2..E2 -> [statusA, statusB, statusC, statusD, stockE]
    values = cfg_ws.get("A1:E2")
    # normalize to 2 rows, 5 cols
    while len(values) < 2:
        values.append([])
    for i in range(len(values)):
        while len(values[i]) < 5:
            values[i].append("")
    return values

def safe_get_config():
    try:
        vals = read_config_range()
        # Parse
        rp_raw = vals[0][0].strip()
        remaining = int(rp_raw) if rp_raw else None
        status_a = vals[1][0].strip() or None
        status_b = vals[1][1].strip() or None
        status_c = vals[1][2].strip() or None
        status_d = vals[1][3].strip() or None
        stock_e_raw = vals[1][4].strip()
        stock_e = int(stock_e_raw) if stock_e_raw else None
        return remaining, status_a, status_b, status_c, status_d, stock_e, None
    except Exception as e:
        # If API 429 or any error, return None with the error so we can show a warning
        return None, None, None, None, None, None, e

remaining_pulls, status_a, status_b, status_c, status_d, stock_e, cfg_err = safe_get_config()

# --- Style (kept) ---
st.markdown(
    """
    <style>
    .price { font-size: 24px; font-weight: bold; }
    .footer-desktop { display: block; text-align: center; }
    .footer-mobile { display: none; }
    @media (max-width: 768px) {
      .footer-desktop { display: none; }
      .footer-mobile { display: block; text-align: left; }
    }
    .footer {
      position: fixed; left: 0; bottom: 0; width: 100%;
      background-color: #f0f6ff; color: #222; padding: 10px; font-size: 12px;
      border-top: 1px solid #cce0ff;
    }
    :root {
      --card-bg: #f8fbff; --card-border: #cfe2ff; --accent: #1a73e8; --text: #1a73e8;
    }
    @media (prefers-color-scheme: dark) {
      :root { --card-bg: #0b1b2e; --card-border: #1f3b66; --accent: #8ab4f8; --text: #8ab4f8; }
    }
    .status-box {
      padding: 18px; background: var(--card-bg); border: 1px solid var(--card-border);
      border-left: 6px solid var(--accent); border-radius: 10px;
      margin: 12px 0 16px 0; line-height: 1.6; font-size: 16px; color: var(--text);
    }
    .status-box .title { font-size: 20px; font-weight: 800; color: var(--accent); margin-bottom: 10px; }
    .status-box b { font-weight: 800; }
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

    # --- Show config read warning if any ---
    if cfg_err is not None:
        st.warning("Gagal membaca status hadiah (mungkin kuota read Sheets habis). Menampilkan nilai terakhir yang tersimpan jika ada cache.")

    # --- Pull counter (separate, st.info) ---
    if remaining_pulls is None:
        st.warning("Sisa kuota pull belum di-setup.")
    else:
        st.info(f"Sisa bola dari pool saat ini: **{remaining_pulls}**")
        if remaining_pulls <= 0:
            st.error("Kuota pull untuk hari ini sudah habis.")
            st.stop()

    # --- Single status box (A–D status bold, E stock; use ':' not '→') ---
    def norm_status(s): return f"<b>{(s or '?')}</b>"
    a_text = norm_status(status_a)
    b_text = norm_status(status_b)
    c_text = norm_status(status_c)
    d_text = norm_status(status_d)
    e_text = f"tersisa <b>{stock_e}</b>" if stock_e is not None else "<b>stok belum di-setup</b>"

    status_html = f"""
    <div class="status-box">
      <div class="title">📦 Status Hadiah</div>
      <div><strong>A</strong> : Nendoroid - Bebas kamu pilih : {a_text}</div>
      <div><strong>B</strong> : Nendoroid - pilihan Lis : {b_text}</div>
      <div><strong>C</strong> : Prize Figure : {c_text}</div>
      <div><strong>D</strong> : Plush Aranara : {d_text}</div>
      <div><strong>E</strong> : Blokees : {e_text}</div>
    </div>
    """
    st.markdown(status_html, unsafe_allow_html=True)

    # --- Inputs ---
    name = st.text_input("Nama Kamu")
    wa_number = st.text_input("Nomor WhatsApp", placeholder="0891234567788")
    address = st.text_area(
        "Alamat Lengkap",
        placeholder="Contoh: Jl. Medan Merdeka Utara No. 3, Kel. Gambir, Kec. Gambir, Kota Jakarta Pusat, DKI Jakarta 10110"
    )
    st.caption("Harap isi lengkap: nama jalan, kelurahan, kecamatan, kota/kabupaten, provinsi, dan kode pos.")

    # Cap qty by remaining pulls if present
    if remaining_pulls is None:
        quantity = st.number_input("Jumlah Pull", min_value=1, step=1)
    else:
        quantity = st.number_input("Jumlah Pull", min_value=1, max_value=remaining_pulls, step=1)

    item_name = "Gacha with Irene"
    unit_price = 40000
    total_price = unit_price * quantity

    st.markdown(f'<div class="price">Harga per Item: Rp {unit_price:,.0f}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="price">Total Harga: Rp {total_price:,.0f}</div><br/>', unsafe_allow_html=True)

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
                current_time, name, wa_number, address,
                item_name, unit_price, f"{quantity} pcs", total_price
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
