import streamlit as st
import pandas as pd
import folium
import requests
from streamlit_folium import st_folium
from datetime import datetime
from streamlit_gsheets import GSheetsConnection
from fpdf import FPDF

# --- 1. KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Waspada Banjar - Sistem Terpadu", layout="wide")

# --- 2. INISIALISASI KONEKSI & DATABASE ---
conn = st.connection("gsheets", type=GSheetsConnection)

if 'laporan' not in st.session_state:
    st.session_state.laporan = pd.DataFrame(columns=['Waktu', 'Kecamatan', 'Level Air (cm)', 'Status', 'Kebutuhan'])

# --- 3. FUNGSI HELPER (WA & PDF) ---
def kirim_notifikasi_wa(kecamatan, tinggi, kebutuhan):
    url = "https://api.fonnte.com/send"
    token = "ISI_TOKEN_FONNTE_ANDA" # Ganti dengan Token Anda
    target = "08125064087" 
    pesan = (
        f"🚨 *LAPORAN BANJIR BARU*\n\n📍 *Lokasi:* Kec. {kecamatan}\n"
        f"📏 *Ketinggian Air:* {tinggi} cm\n🆘 *Kebutuhan:* {kebutuhan}\n\n"
        f"Mohon segera tindak lanjuti melalui Dashboard Waspada Banjar."
    )
    headers = {'Authorization': token}
    try:
        response = requests.post(url, headers=headers, data={'target': target, 'message': pesan})
        return response.status_code == 200
    except:
        return False

def generate_pdf(dataframe, total_kerugian):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, "LAPORAN REKAPITULASI WASPADA BANJAR", ln=True, align='C')
    pdf.set_font("Arial", '', 10)
    pdf.cell(0, 10, f"Tanggal Cetak: {datetime.now().strftime('%d %B %Y %H:%M')}", ln=True, align='C')
    pdf.ln(10)
    
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, "Ringkasan Eksekutif:", ln=True)
    pdf.set_font("Arial", '', 11)
    pdf.cell(0, 8, f"- Total Keluarga Terdampak: {len(dataframe)} KK", ln=True)
    pdf.cell(0, 8, f"- Total Estimasi Kerugian: Rp {total_kerugian:,.0f}", ln=True)
    pdf.ln(5)

    pdf.set_font("Arial", 'B', 10)
    pdf.set_fill_color(200, 220, 255)
    pdf.cell(40, 10, "Kecamatan", 1, 0, 'C', True)
    pdf.cell(60, 10, "Nama KK", 1, 0, 'C', True)
    pdf.cell(40, 10, "Status Rumah", 1, 0, 'C', True)
    pdf.cell(50, 10, "Kebutuhan", 1, 1, 'C', True)

    pdf.set_font("Arial", '', 9)
    for i, row in dataframe.iterrows():
        pdf.cell(40, 10, str(row['Kecamatan']), 1)
        pdf.cell(60, 10, str(row['Nama Kepala Keluarga'])[:25], 1)
        pdf.cell(40, 10, str(row['Status Rumah']), 1)
        pdf.cell(50, 10, str(row['Kebutuhan Utama']), 1, 1)
    return pdf.output(dest='S')

# --- 4. SIDEBAR NAVIGASI ---
st.sidebar.title("🌊 Waspada Banjar")
menu = st.sidebar.radio("Navigasi Utama", [
    "Dashboard Pantauan", 
    "Input Data Keluarga (GSheets)", 
    "Lapor Kondisi Banjir", 
    "Manajemen Logistik", 
    "Analisis Dampak"
])

# --- DATA TITIK PANTAU ---
titik_pantau = pd.DataFrame({
    'Lokasi': ['Bendung Riam Kanan', 'Aluh-Aluh', 'Sungai Tabuk', 'Pengaron'],
    'lat': [-3.4542, -3.4147, -3.3134, -3.1812],
    'lon': [114.9456, 114.8514, 114.6865, 115.1156],
    'Status': ['Siaga 1', 'Waspada', 'Aman', 'Waspada']
})

# --- MENU 1: DASHBOARD ---
if menu == "Dashboard Pantauan":
    st.title("📊 Dashboard Pantauan Real-Time")
    try:
        df_real = conn.read(worksheet="Sheet1", ttl=0)
        total_kk = len(df_real)
        total_rentan = df_real['Balita/Lansia'].str.split(', ').explode().replace('', pd.NA).dropna().count()
    except:
        total_kk, total_rentan = 0, 0

    col1, col2, col3 = st.columns(3)
    col1.metric("Total KK Terdampak", f"{total_kk} Keluarga")
    col2.metric("Total Warga Rentan", f"{total_rentan} Jiwa")
    col3.metric("Status Wilayah", "Waspada")

    ga1, ga2 = st.columns(2)
    with ga1:
        st.subheader("📍 Sebaran per Kecamatan")
        if total_kk > 0: st.bar_chart(df_real['Kecamatan'].value_counts())
    with ga2:
        st.subheader("🏠 Kondisi Rumah")
        if total_kk > 0: st.write(df_real['Status Rumah'].value_counts())

    st.subheader("🗺️ Peta Sebaran Titik Pantau")
    m = folium.Map(location=[-3.4147, 114.8514], zoom_start=10)
    for i, row in titik_pantau.iterrows():
        color = 'red' if row['Status'] == 'Siaga 1' else 'orange' if row['Status'] == 'Waspada' else 'green'
        folium.Marker([row['lat'], row['lon']], popup=row['Lokasi']).add_to(m)
    st_folium(m, width="100%", height=400)

# --- MENU 2: INPUT KELUARGA (VERIFIKASI NIK) ---
# --- MENU 2: INPUT KELUARGA (DENGAN PERBAIKAN) ---
elif menu == "Input Data Keluarga (GSheets)":
    st.title("👨‍👩‍👧‍👦 Pendataan Keluarga Terdampak")
    try:
        # 1. Baca data referensi NIK (DTSEN)
        df_dtsen = conn.read(worksheet="DTSEN", ttl=0)
        # Pastikan NIK jadi string dan bersih dari spasi/karakter aneh
        list_nik_valid = df_dtsen['NIK'].astype(str).str.strip().tolist()
        
        # 2. Baca data yang SUDAH terdaftar di Sheet1 (untuk cek duplikasi)
        existing_data = conn.read(worksheet="Sheet1", ttl=0)
        list_nik_terdaftar = existing_data['NIK'].astype(str).str.strip().tolist()
    except Exception as e:
        st.error(f"Gagal koneksi ke Sheets: {e}")
        list_nik_valid, list_nik_terdaftar, existing_data = [], [], pd.DataFrame()

    with st.form("form_keluarga", clear_on_submit=True):
        # ... (bagian input c1 & c2 tetap sama) ...
        
        if st.form_submit_button("Verifikasi & Simpan"):
            nik_clean = nik.strip()
            
            # LOGIKA VERIFIKASI
            if not nama_kk or not nik_clean:
                st.error("Data wajib diisi!")
            elif nik_clean not in list_nik_valid:
                st.error(f"❌ NIK {nik_clean} TIDAK TERDAFTAR di database DTSEN.")
            elif nik_clean in list_nik_terdaftar:
                st.warning(f"⚠️ NIK {nik_clean} sudah pernah melaporkan kondisi.")
            else:
                # Susun data baru
                new_entry = pd.DataFrame([{
                    'Waktu Input': datetime.now().strftime("%Y-%m-%d %H:%M"),
                    'Nama Kepala Keluarga': nama_kk,
                    'NIK': nik_clean,
                    'Kecamatan': kecamatan,
                    'Desa/Kelurahan': desa,
                    'Jumlah Anggota': jml_anggota,
                    'Balita/Lansia': ", ".join(vulnerable),
                    'Status Rumah': status_rumah,
                    'Kebutuhan Utama': kebutuhan_fam,
                    'Status Verifikasi': 'Lolos DTSEN'
                }])
                
                # Gabungkan dengan existing_data dari Sheet1, BUKAN dari DTSEN
                updated_df = pd.concat([existing_data, new_entry], ignore_index=True)
                
                # Update ke Sheet1
                conn.update(worksheet="Sheet1", data=updated_df)
                st.success("✅ Data berhasil disimpan!"); st.rerun()

# --- MENU 3: LAPOR BANJIR & WA ---
elif menu == "Lapor Kondisi Banjir":
    st.title("📝 Form Pelaporan Lapangan")
    with st.form("form_lapor"):
        kec = st.selectbox("Pilih Kecamatan", ["Martapura", "Martapura Barat", "Sungai Tabuk", "Karang Intan", "Astambul"])
        tinggi = st.number_input("Ketinggian Air (cm)", min_value=0, max_value=500)
        keb = st.multiselect("Kebutuhan", ["Evakuasi", "Makanan", "Obat-obatan", "Tenda", "Air Bersih"])
        if st.form_submit_button("Kirim & Notifikasi WA"):
            list_keb = ", ".join(keb)
            st.session_state.laporan = pd.concat([st.session_state.laporan, pd.DataFrame([{'Waktu': datetime.now(), 'Kecamatan': kec, 'Level Air (cm)': tinggi, 'Status': "Waspada", 'Kebutuhan': list_keb}])], ignore_index=True)
            if kirim_notifikasi_wa(kec, tinggi, list_keb): st.success("✅ WA Terkirim!")
            else: st.warning("✅ Laporan masuk, WA gagal.")

# --- MENU 4: LOGISTIK ---
elif menu == "Manajemen Logistik":
    st.title("📦 Inventaris Logistik")
    try:
        df_stok = conn.read(worksheet="Logistik", ttl=0)
        cols = st.columns(len(df_stok))
        for i, row in df_stok.iterrows(): cols[i].metric(row['Nama Barang'], f"{row['Jumlah']} {row['Satuan']}")
        st.dataframe(df_stok, use_container_width=True)
    except: st.error("Gagal memuat data Logistik.")

# --- MENU 5: ANALISIS DAMPAK (VERSI BERSIH) ---
elif menu == "Analisis Dampak":
    st.title("📈 Analisis Dampak & Estimasi Kerugian Ekonomi")
    st.info("Analisis ini menggabungkan data laporan lapangan dengan estimasi biaya pemulihan aset.")

    try:
        # Mengambil data terbaru dari Google Sheets
        df_keluarga = conn.read(worksheet="Kerugian", ttl=0)
        
        if not df_keluarga.empty:
            # 1. Logika Estimasi Kerugian
            biaya_kerusakan = {
                "Terendam (Bisa Ditempati)": 1500000,
                "Terendam (Mengungsi)": 5000000,
                "Rusak Berat": 25000000
            }
            
            # Hitung estimasi per baris
            df_keluarga['Estimasi Kerugian (Rp)'] = df_keluarga['Status Rumah'].map(biaya_kerusakan).fillna(0)
            
            # 2. Ringkasan Eksekutif
            total_kerugian = df_keluarga['Estimasi Kerugian (Rp)'].sum()
            total_jiwa = df_keluarga['Jumlah Anggota'].sum()
            
            c1, c2, c3 = st.columns(3)
            c1.metric("Total Estimasi Kerugian", f"Rp {total_kerugian:,.0f}")
            c2.metric("Total Jiwa Terdampak", f"{total_jiwa} Orang")
            c3.metric("Data Keluarga Masuk", f"{len(df_keluarga)} KK")
        
            # 3. Fitur Download PDF
            pdf_data = generate_pdf(df_keluarga, total_kerugian)
            st.download_button(
                label="📥 Download Laporan PDF",
                data=pdf_data,
                file_name=f"Laporan_Banjir_{datetime.now().strftime('%Y%m%d')}.pdf",
                mime="application/pdf"
            )

            # 4. Visualisasi Per Kecamatan
            st.subheader("Kerugian Ekonomi per Kecamatan")
            chart_data = df_keluarga.groupby('Kecamatan')['Estimasi Kerugian (Rp)'].sum().sort_values(ascending=False)
            st.bar_chart(chart_data)
            
            # 5. Tabel Detail Analisis
            with st.expander("Detail Analisis"):
                st.write(df_keluarga[['Nama Kepala Keluarga', 'Kecamatan', 'Status Rumah', 'Estimasi Kerugian (Rp)']])
        else:
            st.warning("Data di Google Sheets masih kosong. Belum ada analisis yang bisa ditampilkan.")
            
    except Exception as e:
        st.error(f"Gagal memuat data analisis: {e}")