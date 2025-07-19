# 🎲 Dice with Irene — Order Form

A simple and efficient Streamlit app to collect customer orders for the **"Dice with Irene"** campaign during live events.

This form is designed for a **fixed-price item** (Rp 35.000 per unit) where customers can input their name, WhatsApp number, full address, and the quantity of items ordered.

---

## 📦 Features

- Simple customer order form
- Fixed price per item (Rp 35.000)
- Total calculated automatically
- Stores all submissions to a shared **Google Sheets** file (`Orders` sheet)
- Timestamp recorded in **Asia/Jakarta** timezone
- Designed for mobile and desktop

---

## 📝 Form Fields

- **Nama Kamu** – Customer's full name  
- **Nomor WhatsApp** – Digits only, validated
- **Alamat Lengkap** – Must include street, kelurahan, kecamatan, kota/provinsi, and postal code
- **Jumlah Pesanan (pcs)** – Integer quantity of items ordered

---

## 🧮 Price Calculation

- **Harga per item**: `Rp 35.000`
- **Final Price**: `Qty × 35.000`

---

## 📤 Output

Appends data to the `Orders` worksheet in this format:

| Timestamp         | Name           | WhatsApp    | Alamat Lengkap        | Item              | Price  | Discount   | Final Price |
|------------------|----------------|-------------|------------------------|-------------------|--------|------------|--------------|
| 2025-07-19 12:30 | Jane Doe       | 08123456789 | Full address here      | dice with irene   | 35000  | 3 pcs      | 105000       |

- **Discount** column is reused to store the **quantity** in `"X pcs"` format
- **Item** is hardcoded as `"dice with irene"`
