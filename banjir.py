import streamlit as st
import pandas as pd
from datetime import datetime
import os
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table
from reportlab.lib.styles import getSampleStyleSheet
import io

# --- 1. KONFIGURASI FILE LOKAL ---
st.set_page_config(page_title="Waspada Banjar Lokal", layout="wide")
NAMA_FILE_LOKAL = "database_banjar.csv"

# Fungsi untuk memuat data dari CSV lokal
def load_data():
    if os.path.exists(NAMA_FILE_LOKAL):
        return pd.read_csv(NAMA_FILE_LOKAL)
    else:
        # Jika file belum ada, buat DataFrame kosong dengan kolom yang sesuai
        return pd.DataFrame(columns=[
            'Waktu Input', 'Nama Kepala Keluarga', 'NIK', 'Kecamatan', 
            'Desa/Kelurahan', 'Jumlah Anggota', 'Balita/Lansia', 
            'Status Rumah', 'Kebutuhan Utama', 'Jenis Aset'
        ])

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


# --- 4. MENU INPUT DATA KELUARGA (PENYIMPANAN LOKAL) ---
if menu == "Input Data Keluarga":
    st.title("👨‍👩‍👧‍👦 Pendataan Keluarga Terdampak")
    st.info(f"Penyimpanan: Aktif di file lokal ({NAMA_FILE_LOKAL})")
    
    with st.form("form_keluarga", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            nama_kk = st.text_input("Nama Kepala Keluarga")
            nik = st.text_input("NIK (16 Digit)")
            kecamatan = st.selectbox("Kecamatan", ["Martapura", "Martapura Barat", "Martapura Timur", "Sungai Tabuk", "Karang Intan", "Astambul", "Simpang Empat", "Pengaron"])
            desa = st.text_input("Desa/Kelurahan")
        with col2:
            jml_anggota = st.number_input("Total Anggota Keluarga", min_value=1, step=1)
            vulnerable = st.multiselect("Kategori Rentan", ["Balita", "Ibu Hamil", "Lansia", "Disabilitas"])
            status_rumah = st.radio("Kondisi Rumah", ["Terendam (Bisa Ditempati)", "Terendam (Mengungsi)", "Rusak Berat"])
            kebutuhan = st.selectbox("Kebutuhan Mendesak", ["Sembako", "Obat-obatan", "Popok/Susu", "Pakaian", "Evakuasi"])

        submit_keluarga = st.form_submit_button("Simpan Data")

        if submit_keluarga:
            if not nama_kk or not nik:
                st.error("Nama dan NIK wajib diisi!")
            else:
                # Muat data yang sudah ada
                df_lama = load_data()
                
                # Buat entri baru
                new_entry = pd.DataFrame([{
                    'Waktu Input': datetime.now().strftime("%Y-%m-%d %H:%M"),
                    'Nama Kepala Keluarga': nama_kk,
                    'NIK': nik,
                    'Kecamatan': kecamatan,
                    'Desa/Kelurahan': desa,
                    'Jumlah Anggota': jml_anggota,
                    'Balita/Lansia': ", ".join(vulnerable),
                    'Status Rumah': status_rumah,
                    'Kebutuhan Utama': kebutuhan,
                    'Jenis Aset': "Rumah Tangga"
                }])

                # Gabungkan dan simpan ke CSV
                df_baru = pd.concat([df_lama, new_entry], ignore_index=True)
                df_baru.to_csv(NAMA_FILE_LOKAL, index=False)
                
                st.success(f"✅ Data {nama_kk} berhasil disimpan secara lokal!")
                st.rerun()

    # Tampilkan tabel data lokal
    st.subheader("📋 Database Lokal Saat Ini")
    df_tampil = load_data()
    if not df_tampil.empty:
        st.dataframe(df_tampil, use_container_width=True)
    else:
        st.write("Belum ada data tersimpan.")

# --- MENU 3: LAPOR KONDISI BANJIR ---
elif menu == "Lapor Kondisi Banjir":
    st.title("📝 Form Pelaporan Kondisi Lapangan")
    with st.form("form_lapor"):
        kec = st.selectbox("Pilih Kecamatan", ["Martapura", "Martapura Barat", "Sungai Tabuk", "Karang Intan", "Astambul"])
        tinggi = st.number_input("Ketinggian Air (cm)", min_value=0, max_value=500)
        keb = st.multiselect("Kebutuhan Mendesak", ["Evakuasi", "Makanan", "Obat-obatan", "Tenda", "Air Bersih"])
        submit_lapor = st.form_submit_button("Kirim Laporan")

        if submit_lapor:
            status = "Bahaya" if tinggi > 150 else "Waspada" if tinggi > 50 else "Aman"
            new_report = {
                'Waktu': datetime.now().strftime("%Y-%m-%d %H:%M"),
                'Kecamatan': kec,
                'Level Air (cm)': tinggi,
                'Status': status,
                'Kebutuhan': ", ".join(keb)
            }
            st.session_state.laporan = pd.concat([st.session_state.laporan, pd.DataFrame([new_report])], ignore_index=True)
            st.success(f"Laporan {kec} diterima!")

# --- MENU 4: MANAJEMEN LOGISTIK ---
elif menu == "Manajemen Logistik":
    st.title("📦 Distribusi Logistik & Bantuan")
    st.subheader("Data Laporan Masuk")

    if st.session_state.laporan.empty:
        st.info("Belum ada laporan yang masuk")
    else:
        st.table(st.session_state.laporan)


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
