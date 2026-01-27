import streamlit as st
import pandas as pd
from datetime import datetime
import os
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table
from reportlab.lib.styles import getSampleStyleSheet
import io
import folium
from streamlit_folium import st_folium
import requests

# --- FUNGSI KIRIM WHATSAPP (Fonnte API) ---
def kirim_notifikasi_wa(kecamatan, tinggi, kebutuhan):
    url = "https://api.fonnte.com/send"
    token = "Yh9CaJUmB74QdCnewn1z"  # Ganti dengan Token dari Fonnte
    target = "08125064087" # Ganti dengan nomor WhatsApp Koordinator/Grup

    pesan = (
        f"🚨 *LAPORAN BANJIR BARU*\n\n"
        f"📍 *Lokasi:* Kec. {kecamatan}\n"
        f"📏 *Ketinggian Air:* {tinggi} cm\n"
        f"🆘 *Kebutuhan:* {kebutuhan}\n\n"
        f"Mohon segera tindak lanjuti melalui Dashboard Waspada Banjar."
    )

    data = {
        'target': target,
        'message': pesan,
    }
    headers = {
        'Authorization': token
    }
    
    try:
        response = requests.post(url, headers=headers, data=data)
        return response.status_code == 200
    except:
        return False


# --- 1. KONFIGURASI HALAMAN & THEME ---
st.set_page_config(
    page_title="Waspada Banjar | Disaster Management",
    page_icon="🌊",
    layout="wide"
)

# Custom CSS untuk tampilan premium
st.markdown("""
    <style>
    /* Gradient Sidebar */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1e3a8a 0%, #1e40af 100%);
    }
    [data-testid="stSidebar"] .stMarkdown h1 {
        color: white;
    }
    /* Metric Card Styling */
    div[data-testid="metric-container"] {
        background-color: #f8fafc;
        border: 1px solid #e2e8f0;
        padding: 15px;
        border-radius: 12px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    /* Status Labels */
    .status-badge {
        padding: 5px 12px;
        border-radius: 20px;
        font-weight: bold;
        color: white;
    }
    </style>
    """, unsafe_allow_html=True)


# --- 1. KONFIGURASI FILE LOKAL ---
st.set_page_config(page_title="Waspada Banjar Lokal", layout="wide")
NAMA_FILE_LOKAL = "database_banjar.csv"
NAMA_FILE_LAPORAN = "database_laporan.csv" # Tambahkan ini
FILE_DTSEN = "dtsen.csv"  # File database kependudukan untuk verifikasi

# Fungsi memuat data utama
def load_data():
    if os.path.exists(NAMA_FILE_LOKAL):
        return pd.read_csv(NAMA_FILE_LOKAL, dtype={'NIK': str}) # Pastikan NIK dibaca sebagai string
    else:
        return pd.DataFrame(columns=[
            'Waktu Input', 'Nama Kepala Keluarga', 'NIK', 'Kecamatan', 
            'Desa/Kelurahan', 'Jumlah Anggota', 'Balita/Lansia', 
            'Status Rumah', 'Kebutuhan Utama', 'Jenis Aset'
        ])

def load_laporan():
    if os.path.exists(NAMA_FILE_LAPORAN):
        return pd.read_csv(NAMA_FILE_LAPORAN)
    else:
        return pd.DataFrame(columns=['Waktu', 'Kecamatan', 'Level Air (cm)', 'Status', 'Kebutuhan'])

# Fungsi memuat database DTSEN untuk verifikasi NIK
def load_dtsen():
    if os.path.exists(dtsen.csv):
        df = pd.read_csv(dtsen.csv, dtype={'NIK': str})
        return df['NIK'].unique().tolist()
    else:
        st.error(f"⚠️ File {dtsen.csv} tidak ditemukan! Verifikasi NIK dinonaktifkan.")
        return None

def kirim_wa(kec, tinggi, keb):
    # Logika Fonnte dari coba2.py
    url = "https://api.fonnte.com/send"
    token = "Yh9CaJUmB74QdCnewn1z" # Ganti jika perlu
    target = "08125064087"
    pesan = f"🚨 *LAPORAN BARU*: Kec. {kec}, Air: {tinggi}cm. Butuh: {keb}"
    try:
        requests.post(url, headers={'Authorization': token}, data={'target': target, 'message': pesan})
        return True
    except: return False


# --- 2. FUNGSI HELPER PDF ---
def generate_pdf_laporan(df, total_kerugian, total_jiwa):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = []
    elements.append(Paragraph("<b>LAPORAN ESTIMASI KERUGIAN BANJIR</b>", styles["Title"]))
    elements.append(Paragraph(f"Tanggal: {datetime.now().strftime('%d %B %Y')}", styles["Normal"]))
    elements.append(Paragraph("<br/>", styles["Normal"]))
    elements.append(Paragraph(f"<b>Total Estimasi Kerugian:</b> Rp {total_kerugian:,.0f}".replace(",", "."), styles["Normal"]))
    elements.append(Paragraph(f"<b>Total Jiwa Terdampak:</b> {total_jiwa} Orang", styles["Normal"]))
    elements.append(Paragraph("<br/>", styles["Normal"]))

    table_data = [["Nama KK", "Kecamatan", "Desa", "Jenis Aset", "Status", "Kerugian"]]
    for _, row in df.iterrows():
        table_data.append([
            str(row["Nama Kepala Keluarga"]), str(row["Kecamatan"]), str(row["Desa/Kelurahan"]),
            str(row["Jenis Aset"]), str(row["Status Rumah"]), 
            f"Rp {row.get('Estimasi Kerugian (Rp)', 0):,.0f}".replace(",", ".")
        ])
    elements.append(Table(table_data, repeatRows=1))
    doc.build(elements)
    buffer.seek(0)
    return buffer

# --- 3. SIDEBAR NAVIGASI ---
st.sidebar.title("🌊 Waspada Banjar (Lokal)")
menu = st.sidebar.radio("Navigasi", ["Dashboard Pantauan", "Input Data Keluarga", "Lapor Kondisi Banjir", "Manajemen Logistik", "Analisis Dampak"])

# --- MENU 1: DASHBOARD PANTAUAN ---
if menu == "Dashboard Pantauan":
    st.title("📊 Dashboard Pantauan Real-Time")
    
    # Ambil data terbaru dari GSheets untuk kalkulasi rekap
    try:
        df_real = conn.read(worksheet="Sheet1", ttl=0)
        total_kk = len(df_real)
        # Menghitung total warga rentan (split string dan hitung elemen)
        total_rentan = df_real['Balita/Lansia'].str.split(', ').explode().replace('', pd.NA).dropna().count()
    except:
        total_kk = 0
        total_rentan = 0

    # Metrik Utama (Dinamis dari Data GSheets)
    col1, col2, col3 = st.columns(3)
    col1.metric("Total KK Terdampak", f"{total_kk} Keluarga", "Data Terverifikasi")
    col2.metric("Total Warga Rentan", f"{total_rentan} Jiwa", "Prioritas Evakuasi")
    col3.metric("Status Wilayah", "Waspada", "Kab. Banjar")

    # Layout Kolom untuk Grafik
    ga1, ga2 = st.columns(2)
    
    with ga1:
        st.subheader("📍 Sebaran per Kecamatan")
        if total_kk > 0:
            st.bar_chart(df_real['Kecamatan'].value_counts())
        else:
            st.info("Belum ada data masuk.")

    with ga2:
        st.subheader("🏠 Kondisi Rumah")
        if total_kk > 0:
            st.write(df_real['Status Rumah'].value_counts())
        else:
            st.info("Belum ada data masuk.")

    # Peta (Tetap ada di bawah)
    st.markdown("---")
    st.subheader("🗺️ Peta Sebaran Titik Pantau")
    m = folium.Map(location=[-3.4147, 114.8514], zoom_start=10)
    for i, row in titik_pantau.iterrows():
        color = 'red' if row['Status'] == 'Siaga 1' else 'orange' if row['Status'] == 'Waspada' else 'green'
        folium.Marker(
            [row['lat'], row['lon']], 
            popup=f"{row['Lokasi']}: {row['Status']}",
            icon=folium.Icon(color=color)
        ).add_to(m)
    st_folium(m, width="100%", height=400)


# --- MENU 2: PENDATAAN WARGA ---
elif menu == "📝 Pendataan Warga":
    st.title("📝 Registrasi Keluarga Terdampak")
    list_nik = load_dtsen() # Fungsi verifikasi NIK
    
    with st.form("form_warga", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            nama = st.text_input("Nama Kepala Keluarga")
            nik = st.text_input("NIK (16 Digit)")
            kec = st.selectbox("Kecamatan", ["Martapura", "Martapura Barat", "Martapura Timur", "Sungai Tabuk", "Karang Intan", "Astambul"])
        with c2:
            jml = st.number_input("Jumlah Anggota Keluarga", min_value=1, step=1)
            # PASTIKAN teks Status Rumah di bawah ini SAMA dengan yang ada di Menu Analisis
            status = st.radio("Kondisi Rumah", ["Terendam (Bisa Ditempati)", "Terendam (Mengungsi)", "Rusak Berat"])
            rentan = st.multiselect("Kelompok Rentan", ["Balita", "Lansia", "Ibu Hamil"])
        
        if st.form_submit_button("🚀 SIMPAN DATA"):
            if not nama or not nik:
                st.error("Nama dan NIK wajib diisi!")
            elif list_nik and nik not in list_nik:
                st.error(f"❌ NIK {nik} Tidak Terdaftar di DTSEN!")
            else:
                # Simpan ke CSV
                df_lama = load_data()
                new_data = pd.DataFrame([{
                    'Waktu Input': datetime.now().strftime("%Y-%m-%d %H:%M"),
                    'Nama Kepala Keluarga': nama,
                    'NIK': str(nik), # Simpan sebagai teks
                    'Kecamatan': kec,
                    'Jumlah Anggota': int(jml),
                    'Status Rumah': status,
                    'Balita/Lansia': ", ".join(rentan)
                }])
                pd.concat([df_lama, new_data], ignore_index=True).to_csv(NAMA_FILE_LOKAL, index=False)
                st.success(f"✅ Data {nama} berhasil disimpan ke Database Lokal!")

    # Tampilkan tabel data
    st.subheader("📋 Database Lokal Saat Ini")
    df_tampil = load_data()
    if not df_tampil.empty:
        st.dataframe(df_tampil, use_container_width=True)

# --- MENU 3: LAPOR KONDISI ---
elif menu == "📡 Lapor Kondisi":
    st.title("📡 Laporan Cepat Lapangan")
    
    with st.form("form_lapor", clear_on_submit=True):
        kec_l = st.selectbox("Lokasi Kejadian", ["Martapura", "Martapura Barat", "Martapura Timur", "Sungai Tabuk", "Karang Intan", "Astambul"])
        tinggi = st.slider("Ketinggian Air (cm)", 0, 300, 50)
        kebutuhan = st.text_input("Kebutuhan Mendesak (Contoh: Perahu, Logistik)")
        
        if st.form_submit_button("📤 KIRIM LAPORAN"):
            # 1. Simpan ke CSV Laporan terlebih dahulu
            df_lap_lama = load_laporan()
            new_lap = pd.DataFrame([{
                'Waktu': datetime.now().strftime("%H:%M"),
                'Kecamatan': kec_l,
                'Level Air (cm)': tinggi,
                'Status': "Bahaya" if tinggi > 100 else "Waspada",
                'Kebutuhan': kebutuhan
            }])
            pd.concat([df_lap_lama, new_lap], ignore_index=True).to_csv(NAMA_FILE_LAPORAN, index=False)
            
            # 2. Coba kirim WhatsApp (Jangan biarkan error WA merusak aplikasi)
            try:
                status_wa = kirim_notifikasi_wa(kec_l, tinggi, kebutuhan)
                st.success(f"✅ Laporan Tersimpan! (Status WA: {status_wa})")
            except:
                st.warning("✅ Laporan Tersimpan lokal, namun Notifikasi WA Gagal terkirim (Cek Internet).")

# --- MENU 4: MANAJEMEN LOGISTIK ---
elif menu == "Manajemen Logistik":
    st.title("📦 Distribusi Logistik & Bantuan")
    st.subheader("Data Laporan Lapangan Terbaru")

    df_laporan = load_laporan()
    if df_laporan.empty:
        st.info("Belum ada laporan kondisi banjir yang masuk.")
    else:
        # Menampilkan tabel laporan agar tim logistik tahu wilayah mana yang butuh bantuan
        st.dataframe(df_laporan, use_container_width=True)
        
        # Fitur tambahan: Filter kebutuhan mendesak
        st.subheader("Filter Prioritas Bantuan")
        pilihan_kec = st.multiselect("Filter Kecamatan", df_laporan['Kecamatan'].unique())
        if pilihan_kec:
            filtered_df = df_laporan[df_laporan['Kecamatan'].isin(pilihan_kec)]
            st.write(filtered_df)

# --- 5. MENU ANALISIS DAMPAK ---
elif menu == "Analisis Dampak":
    st.title("📈 Analisis & Estimasi Kerugian")
    df_keluarga = load_data()
    
    if not df_keluarga.empty:
        # Logika Biaya
        biaya_kerusakan = {"Terendam (Bisa Ditempati)": 1500000, "Terendam (Mengungsi)": 5000000, "Rusak Berat": 25000000}
        df_keluarga['Estimasi Kerugian (Rp)'] = df_keluarga['Status Rumah'].map(biaya_kerusakan).fillna(0)
        
        total_kerugian = df_keluarga['Estimasi Kerugian (Rp)'].sum()
        total_jiwa = df_keluarga['Jumlah Anggota'].sum()

        c1, c2, c3 = st.columns(3)
        c1.metric("Total Kerugian", f"Rp {total_kerugian:,.0f}".replace(",", "."))
        c2.metric("Jiwa Terdampak", f"{total_jiwa} Orang")
        c3.metric("Data Masuk", f"{len(df_keluarga)} KK")
        
        st.subheader("Visualisasi Kerugian per Kecamatan")
        chart_data = df_keluarga.groupby('Kecamatan')['Estimasi Kerugian (Rp)'].sum()
        st.bar_chart(chart_data)
        
        pdf_data = generate_pdf_laporan(df_keluarga, total_kerugian, total_jiwa)
        st.download_button("📥 Download Laporan PDF", data=pdf_data, file_name="Laporan_Banjar_Lokal.pdf", mime="application/pdf")
    else:
        st.warning("Database lokal masih kosong.")