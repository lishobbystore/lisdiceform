import os, json, time, random
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

# Open your Google Sheet (Orders)
orders_sheet = client.open_by_key(sheet_key).worksheet("Orders")

# ================== CONFIG READER WITH FILE CACHE ==================
CFG_WS_NAME = "GachaConfig"
CFG_RANGE = "A1:E2"   # A1: remaining pulls; A2:D2: status A-D; E2: stock E
CACHE_PATH = "/mnt/data/gacha_cfg.json"
TTL_SECS = 120  # how long other sessions reuse a single read

def _read_config_from_api():
    """Single batched read with retry/backoff to avoid 429."""
    ss = client.open_by_key(sheet_key)
    ws = ss.worksheet(CFG_WS_NAME)
    # retry a few times on 429
    attempts = 4
    base = 0.4
    for i in range(attempts):
        try:
            values = ws.get(CFG_RANGE)  # single call
            return values
        except Exception as e:
            msg = str(e)
            if "429" in msg or "Quota exceeded" in msg:
                # exponential backoff with jitter
                sleep_s = base * (2 ** i) + random.uniform(0, 0.25)
                time.sleep(sleep_s)
                continue
            # other errors -> raise immediately
            raise
    # if still failing, raise the last error to be handled by caller
    raise RuntimeError("Google Sheets read failed after retries (429).")

def _normalize(values):
    # Ensure 2 rows x 5 cols
    if values is None:
        values = []
    while len(values) < 2:
        values.append([])
    for r in range(len(values)):
        while len(values[r]) < 5:
            values[r].append("")
    return values

def _load_cache():
    if not os.path.exists(CACHE_PATH):
        return None
    try:
        with open(CACHE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data
    except Exception:
        return None

def _save_cache(values):
    try:
        os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)
        with open(CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump({"ts": time.time(), "values": values}, f)
    except Exception:
        pass

def read_config_batched(force_refresh=False):
    """Returns (remaining_pulls, status_a,b,c,d, stock_e, error_or_None) with file cache."""
    if not force_refresh:
        cached = _load_cache()
        if cached and (time.time() - cached.get("ts", 0) <= TTL_SECS):
            vals = _normalize(cached.get("values", []))
            return _parse_vals(vals) + (None,)

    # read from API (with retry/backoff); on failure, fallback to last cache
    try:
        vals = _normalize(_read_config_from_api())
        _save_cache(vals)
        return _parse_vals(vals) + (None,)
    except Exception as e:
        cached = _load_cache()
        if cached:
            vals = _normalize(cached.get("values", []))
            return _parse_vals(vals) + (e,)
        return (None, None, None, None, None, None, e)

def _parse_vals(vals):
    # vals[0][0]=A1 remaining pulls; vals[1]=A2..E2
    rp_raw = str(vals[0][0]).strip()
    remaining = int(rp_raw) if rp_raw else None
    row2 = vals[1]
    status_a = str(row2[0]).strip() or None
    status_b = str(row2[1]).strip() or None
    status_c = str(row2[2]).strip() or None
    status_d = str(row2[3]).strip() or None
    stock_e_raw = str(row2[4]).strip()
    stock_e = int(stock_e_raw) if stock_e_raw else None
    return (remaining, status_a, status_b, status_c, status_d, stock_e)

# Optional: manual refresh button
/* 
colL, colR = st.columns([1, 3])
with colL:
    if st.button("Refresh Status", use_container_width=True):
        # delete file cache so next read forces API
        try:
            if os.path.exists(CACHE_PATH):
                os.remove(CACHE_PATH)
        except Exception:
            pass
*/
# Read config (uses cache; refresh if button clicked)
remaining_pulls, status_a, status_b, status_c, status_d, stock_e, cfg_err = read_config_batched(
    force_refresh=False
)
# ================================================================

# --- Style ---
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

    # Show warning if we fell back to cached after an error
    if cfg_err is not None:
        st.warning("Gagal membaca status hadiah (rate limit). Menampilkan nilai cache terbaru.")

    # Pull counter (separate, st.info)
    if remaining_pulls is None:
        st.warning("Sisa kuota pull belum di-setup.")
    else:
        st.info(f"Sisa kuota pull hari ini: **{remaining_pulls}**")
        if remaining_pulls <= 0:
            st.error("Kuota pull untuk hari ini sudah habis.")
            st.stop()

    # Status box (A–D status bold + E stock) using ":" not arrow
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

    # Inputs
    name = st.text_input("Nama Kamu")
    wa_number = st.text_input("Nomor WhatsApp", placeholder="0891234567788")
    address = st.text_area(
        "Alamat Lengkap",
        placeholder="Contoh: Jl. Medan Merdeka Utara No. 3, Kel. Gambir, Kec. Gambir, Kota Jakarta Pusat, DKI Jakarta 10110"
    )
    st.caption("Harap isi lengkap: nama jalan, kelurahan, kecamatan, kota/kabupaten, provinsi, dan kode pos.")

    # Cap quantity by remaining pulls if present
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
