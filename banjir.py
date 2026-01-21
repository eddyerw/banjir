import streamlit as st
import pandas as pd
from datetime import datetime

# --- INISIALISASI DATABASE SESSION STATE ---
if 'data_keluarga' not in st.session_state:
    st.session_state.data_keluarga = pd.DataFrame(columns=[
        'Waktu Input', 'Nama Kepala Keluarga', 'NIK', 'Kecamatan', 'Desa/Kelurahan', 
        'Jumlah Anggota', 'Balita/Lansia', 'Status Rumah', 'Kebutuhan Utama'
    ])

# --- SIDEBAR NAVIGASI ---
st.sidebar.title("🌊 Waspada Banjar")
menu = st.sidebar.radio("Navigasi", ["Dashboard Pantauan", "Input Data Keluarga", "Manajemen Logistik", "Analisis Dampak"])

# --- 2. MENU INPUT DATA KELUARGA (FITUR BARU) ---
if menu == "Input Data Keluarga":
    st.title("👨‍👩‍👧‍👦 Pendataan Keluarga Terdampak")
    st.info("Gunakan form ini untuk mendata warga yang memerlukan bantuan evakuasi atau logistik.")

    with st.form("form_keluarga", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            nama_kk = st.text_input("Nama Kepala Keluarga")
            nik = st.text_input("NIK (16 Digit)")
            kecamatan = st.selectbox("Kecamatan", [
                "Martapura", "Martapura Barat", "Martapura Timur", "Sungai Tabuk", 
                "Karang Intan", "Astambul", "Simpang Empat", "Pengaron"
            ])
            desa = st.text_input("Desa/Kelurahan")
        
        with col2:
            jml_anggota = st.number_input("Total Anggota Keluarga", min_value=1, step=1)
            vulnerable = st.multiselect("Kategori Rentan dalam Keluarga", ["Balita", "Ibu Hamil", "Lansia", "Disabilitas"])
            status_rumah = st.radio("Kondisi Rumah", ["Terendam (Bisa Ditempati)", "Terendam (Mengungsi)", "Rusak Berat"])
            kebutuhan = st.selectbox("Kebutuhan Mendesak", ["Sembako", "Obat-obatan", "Popok/Susu", "Pakaian", "Evakuasi"])

        submit_keluarga = st.form_submit_button("Simpan Data Keluarga")

        if submit_keluarga:
            if not nama_kk or not nik:
                st.error("Nama dan NIK wajib diisi!")
            else:
                new_entry = {
                    'Waktu Input': datetime.now().strftime("%Y-%m-%d %H:%M"),
                    'Nama Kepala Keluarga': nama_kk,
                    'NIK': nik,
                    'Kecamatan': kecamatan,
                    'Desa/Kelurahan': desa,
                    'Jumlah Anggota': jml_anggota,
                    'Balita/Lansia': ", ".join(vulnerable),
                    'Status Rumah': status_rumah,
                    'Kebutuhan Utama': kebutuhan
                }
                # Menambahkan data baru ke session state
                st.session_state.data_keluarga = pd.concat([st.session_state.data_keluarga, pd.DataFrame([new_entry])], ignore_index=True)
                st.success(f"Data keluarga {nama_kk} berhasil disimpan!")

    # Menampilkan Tabel Data yang Sudah Diinput
    st.subheader("📋 Daftar Keluarga Terdampak")
    if not st.session_state.data_keluarga.empty:
        st.dataframe(st.session_state.data_keluarga)
        
        # Fitur Download Data untuk Laporan (Excel/CSV)
        csv = st.session_state.data_keluarga.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Download Data (CSV)", data=csv, file_name="data_korban_banjar.csv", mime="text/csv")
    else:
        st.write("Belum ada data keluarga yang diinput.")

# (Menu lainnya seperti Dashboard, Logistik, dll tetap ada di bawahnya...)