import streamlit as st
import pandas as pd
import numpy as np
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import plotly.express as px
import plotly.graph_objects as go
import base64
import math

# --- KONFIGURASI HALAMAN ---
st.set_page_config(
    page_title="Dashboard Monitoring Produk Petrokimia Gresik",
    page_icon="🐮",
    initial_sidebar_state="expanded", 
    layout="wide"
)

# --- FUNGSI BACKGROUND GAMBAR ---
def get_img_as_base64(file):
    try:
        with open(file, "rb") as f:
            data = f.read()
        return base64.b64encode(data).decode()
    except Exception as e :
        return None


bg_img_path = "PG_website1_Kantor-Pusat-Petrokimia-Gresik.jpeg"
bg_img_base64 = get_img_as_base64(bg_img_path)

if bg_img_base64:
    page_bg_img = f"""
    <style>
    .stApp {{
        background-image: linear-gradient(rgba(215, 235, 220, 0.85), rgba(185, 220, 195, 0.90)), 
                          url("data:image/png;base64,{bg_img_base64}");
        background-size: cover;
        background-position: center;
        background-repeat: no-repeat;
        background-attachment: fixed;
    }}
    </style>
    """
else:
    page_bg_img = """
    <style>
    .stApp {
        background-color: #E8F0E8; 
    }
    </style>
    """
st.markdown(page_bg_img, unsafe_allow_html=True)


# --- FUNGSI KUSTOM UI KPI CARD ---
def buat_kpi_card(ikon, judul, nilai, teks_badge, warna_badge="hijau"):
    if warna_badge == "hijau":
        bg_color = "#e6f4ea"
        text_color = "#1e8e3e"
        icon_badge = "↑"
    elif warna_badge == "merah":
        bg_color = "#fce8e6"
        text_color = "#d93025"
        icon_badge = "⚠" 
    else: 
        bg_color = "#f1f3f4"
        text_color = "#5f6368"
        icon_badge = "•"

    html = f"""
    <div style="
        background-color: white;
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);  
        border: 1px solid #e0e0e0;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        margin-bottom: 15px;
    ">
        <div style="color: #5f6368; font-size: 14px; font-weight: 500; display: flex; align-items: center; margin-bottom: 10px;">
            <span style="margin-right: 8px; font-size: 16px;">{ikon}</span> {judul}
        </div>
        <div style="color: #1a202c; font-size: 32px; font-weight: bold; margin-bottom: 15px;">
            {nilai}
        </div>
        <div style="display: inline-block; background-color: {bg_color}; color: {text_color}; 
                    padding: 4px 10px; border-radius: 20px; font-size: 12px; font-weight: 600;">
            {icon_badge} {teks_badge}
        </div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)

# --- FUNGSI KUSTOM GAUGE CHART DENGAN JARUM ---
def buat_gauge_chart(nilai, judul, subjudul):
    nilai_visual = min(max(nilai, 0), 100)
    
    fig = go.Figure(go.Indicator(
        mode = "gauge+number",
        value = nilai,
        number = {'suffix': "%", 'font': {'size': 40, 'color': '#1a202c'}},
        domain = {'x': [0, 1], 'y': [0, 1]},
        title = {
            'text': f"<b>{judul}</b><br><span style='font-size:14px;color:gray'>{subjudul}</span>",
            'font': {'size': 18}
        },
        gauge = {
            'axis': {'range': [0, 100], 'tickwidth': 1, 'tickcolor': "darkblue"},
            'bar': {'thickness': 0}, 
            'steps' : [
                {'range': [0, 20], 'color': "#ea746c"},
                {'range': [20, 40], 'color': "#eca5a1"},
                {'range': [40, 60], 'color': "#e4a7ec"},
                {'range': [60, 80], 'color': "#7faaf0"},
                {'range': [80, 100], 'color': "#6bcba0"}
            ],
        }
    ))

    theta = (1 - (nilai_visual / 100)) * math.pi
    center_x = 0.5
    center_y = 0.28
    radius = 0.38
    end_x = center_x + radius * math.cos(theta)
    end_y = center_y + radius * math.sin(theta)

    fig.update_layout(
        shapes=[
            dict(type="line", x0=center_x, y0=center_y, x1=end_x, y1=end_y, line=dict(color="#333333", width=5)),
            dict(type="circle", xref="paper", yref="paper", x0=center_x - 0.02, y0=center_y - 0.02, x1=center_x + 0.02, y1=center_y + 0.02, fillcolor="#333333", line=dict(color="#333333"))
        ],
        margin=dict(l=30, r=30, t=80, b=30),
        height=350,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
    )
    return fig


# --- KONEKSI GOOGLE SHEETS TERPUSAT ---
creds_dict=st.secrets['gcp_service_account']

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)
spreadsheet_id = '1Iz_g6U1rXCsorma2Xjv5W2rGmH-v0yis_yoYf1stWrg'

# --- FUNGSI LOAD DATA SHEET 1 (BULANAN) ---
@st.cache_data
def load_data_bulanan():
    try:
        sheet = client.open_by_key(spreadsheet_id).worksheet('Sheet4')
        data = sheet.get_all_values()
        if not data: return None
        
        header1 = data[0] # Memuat nama-nama produk (Kaptan, Petrocas, dll)
        header2 = data[1] # Memuat Produksi, Pengeluaran, RKAP
        data_rows = data[2:]
        
        # Mapping index ke Produk
        produk_map = {}
        current_produk = ""
        for i in range(2, len(header1)):
            if header1[i] != "":
                current_produk = header1[i]
            produk_map[i] = current_produk
            
        list_df_bulanan = []
        for row in data_rows:
            # Kolom pertama di sheet ternyata adalah Tahun (di bawah header 'No')
            tahun = str(row[0]).strip()
            bulan = str(row[1]).strip().title()
            
            if not tahun or not bulan:
                continue
                
            produk_data = {}
            for i in range(2, len(row)):
                if i >= len(header1) or i not in produk_map:
                    continue
                    
                produk = produk_map[i]
                if produk not in produk_data:
                    produk_data[produk] = {"Produksi": 0.0, "Pengeluaran": 0.0, "RKAP": 0.0}
                    
                kategori = header2[i].strip()
                val_str = str(row[i]).strip().replace(',', '')
                try:
                    val_float = float(val_str) if val_str != "" else 0.0
                except ValueError:
                    val_float = 0.0
                    
                if kategori == "Produksi":
                    produk_data[produk]["Produksi"] = val_float
                elif kategori == "Pengeluaran":
                    produk_data[produk]["Pengeluaran"] = val_float
                elif kategori == "RKAP":
                    produk_data[produk]["RKAP"] = val_float
                    
            for produk, values in produk_data.items():
                list_df_bulanan.append({
                    "Tahun": tahun,
                    "Bulan": bulan,
                    "Produk": produk,
                    "Produksi": values["Produksi"],
                    "Pengeluaran": values["Pengeluaran"],
                    "RKAP": values["RKAP"]
                })
                
        df = pd.DataFrame(list_df_bulanan)
        
        # Buat kolom Triwulan
        kondisi_triwulan = {
            'Januari': 'Triwulan I', 'Februari': 'Triwulan I', 'Maret': 'Triwulan I',
            'April': 'Triwulan II', 'Mei': 'Triwulan II', 'Juni': 'Triwulan II',
            'Juli': 'Triwulan III', 'Agustus': 'Triwulan III', 'September': 'Triwulan III',
            'Oktober': 'Triwulan IV', 'November': 'Triwulan IV', 'Desember': 'Triwulan IV'
        }
        df['Triwulan'] = df['Bulan'].map(kondisi_triwulan)
        
        return df
    except Exception as e:
        st.error(f"Koneksi Google Sheets (Sheet1) gagal: {e}")
        return None

# --- FUNGSI LOAD DATA SHEET 3 (HARIAN) ---
def load_data_harian():
    try:
        sheet = client.open_by_key(spreadsheet_id).worksheet('Sheet3')
        data = sheet.get_all_values()
        if not data: return None
        
        header1 = data[0]
        data_rows = data[2:]
        
        produk_list = []
        for p in header1:
            if p and p not in ["No", "Tanggal", ""]:
                produk_list.append(p)
                
        idx_tanggal = header1.index("Tanggal")
        
        list_df_produk = []
        for row in data_rows:
            tanggal = pd.to_datetime(row[idx_tanggal], errors='ignore')
            if pd.isna(tanggal): continue
                
            for i, p in enumerate(header1):
                if p in produk_list:
                    raw_produksi = str(row[i]).strip().replace(',', '')
                    raw_stok = str(row[i+1]).strip().replace(',', '')
                    raw_pengeluaran = str(row[i+2]).strip().replace(',', '')
                    
                    try:
                        val_produksi = float(raw_produksi) if raw_produksi != "" else 0.0
                    except ValueError:
                        val_produksi = 0.0
                    
                    try:
                        val_stok = float(raw_stok) if raw_stok != "" else 0.0
                    except ValueError:
                        val_stok = 0.0
                        
                    try:
                        val_pengeluaran = float(raw_pengeluaran) if raw_pengeluaran != "" else 0.0
                    except ValueError:
                        val_pengeluaran = 0.0
                    
                    list_df_produk.append({
                        "Tanggal": tanggal,
                        "Produk": p,
                        "Produksi": val_produksi,
                        "Stok": val_stok,
                        "Pengeluaran": val_pengeluaran
                    })
        
        df_final = pd.DataFrame(list_df_produk)
        df_final = df_final.sort_values('Tanggal')
        return df_final, produk_list

    except Exception as e:
        st.error(f"Gagal memuat Sheet3: {e}")
        return None, []
# --- NAVIGASI SIDEBAR ---
try:
    st.sidebar.image("logo-pi.png", width=200)
except FileNotFoundError:
    pass

st.sidebar.title("Navigasi Dashboard")
halaman = st.sidebar.radio("Pilih Halaman:", ["📊 Dashboard Bulanan", "📈 Tren Harian (Line Chart)"])

# --- TOMBOL REFRESH DATA (BARU DITAMBAHKAN) ---
st.sidebar.divider()
st.sidebar.markdown("**Update Data Google Sheets?**")
if st.sidebar.button("🔄 Refresh Data", use_container_width=True):
    st.cache_data.clear() # Membersihkan cache data
    st.rerun()            # Merestart aplikasi untuk menarik data terbaru

# =====================================================================
# --- HALAMAN 1: DASHBOARD BULANAN ---
# =====================================================================
if halaman == "📊 Dashboard Bulanan":
    try:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.image("Logo petro dkk.png", use_container_width=True)
    except FileNotFoundError:
        st.warning("⚠️ File logo belum dimasukkan atau nama file salah.")

    st.title("📈 Dashboard Monitoring Produk PT Petrokimia")
    st.markdown("Memantau tren dan statistik data berdasarkan produk dan waktu yang dipilih.")
    st.divider()

    df = load_data_bulanan()

    if df is not None and not df.empty:
        # --- FILTER GLOBAL HALAMAN 1 ---
        list_tahun = df['Tahun'].dropna().unique().tolist()
        list_tahun.sort(reverse=True)
        list_triwulan = ['Triwulan I', 'Triwulan II', 'Triwulan III', 'Triwulan IV']
        list_produk = df['Produk'].dropna().unique().tolist()
        
        col_f1, col_f2, col_f3 = st.columns(3)
        with col_f1:
            pilih_tahun = st.selectbox("Pilih Tahun:", options=list_tahun, key="hb_tahun")
        with col_f2:
            pilih_triwulan = st.selectbox("Pilih Periode:", options=["Semua Triwulan"] + list_triwulan, key="hb_triwulan")
        with col_f3:
            pilih_produk_bln = st.selectbox("Pilih Produk:", options=list_produk, key="hb_produk")

        st.markdown("<br>", unsafe_allow_html=True)

        # Menerapkan Filter (Tahun dan Produk Dulu)
        df_filtered = df[(df['Tahun'] == pilih_tahun) & (df['Produk'] == pilih_produk_bln)]

        if pilih_triwulan != "Semua Triwulan":
            df_filtered = df_filtered[df_filtered['Triwulan'] == pilih_triwulan]
            teks_periode = f"{pilih_triwulan} {pilih_tahun}"
        else:
            teks_periode = f"Tahun {pilih_tahun}"

        st.subheader(f"Statistik Produk: {pilih_produk_bln}")

        # --- PERHITUNGAN DAN RENDER KPI ---
        if not df_filtered.empty:
            rkap_total = df_filtered['RKAP'].sum()
            pengeluaran_total = df_filtered['Pengeluaran'].sum()
            produksi_total = df_filtered['Produksi'].sum()

            if rkap_total > 0:
                persen_pengeluaran = (pengeluaran_total / rkap_total) * 100
                persen_produksi = (produksi_total / rkap_total) * 100
                teks_badge_pengeluaran = f"{persen_pengeluaran:.1f}%"
                teks_badge_produksi = f"{persen_produksi:.1f}%"
                warna_pengeluaran = "merah" if persen_pengeluaran < 100 else "hijau"
                warna_produksi = "merah" if persen_produksi < 100 else "hijau"
            else:
                persen_pengeluaran = 0
                persen_produksi = 0
                teks_badge_pengeluaran = "0%"
                teks_badge_produksi = "0%"
                warna_pengeluaran = "netral"
                warna_produksi = "netral"

            kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)
            with kpi1:
                buat_kpi_card("🎯", "Total RKAP", f"{rkap_total:,.2f}", teks_periode, "netral")
            with kpi2:
                buat_kpi_card("💸", "Total Pengeluaran", f"{pengeluaran_total:,.2f}", f"{round(persen_pengeluaran, 1) if persen_pengeluaran < 100 else 100}%", warna_badge=warna_pengeluaran)
            with kpi3:
                buat_kpi_card("📦", "Total Produksi", f"{produksi_total:,.2f}", f"{round(persen_produksi, 1) if persen_produksi < 100 else 100}%", warna_badge=warna_produksi)
            with kpi4:
                idx_max = df_filtered['Pengeluaran'].idxmax()
                Pengeluaran_bulan_max = df_filtered.loc[idx_max, 'Bulan'] if pd.notna(idx_max) else "-"
                buat_kpi_card("⚠", "Pengeluaran Maks", Pengeluaran_bulan_max, teks_periode, "netral")
            with kpi5:
                ndx_max= df_filtered['Produksi'].idxmax()
                Produksi_bulan_max = df_filtered.loc[ndx_max, 'Bulan'] if pd.notna(ndx_max) else "-"
                buat_kpi_card("🏗", "Produksi Maks", Produksi_bulan_max, teks_periode, "netral")

            st.markdown("<br>", unsafe_allow_html=True)

            st.subheader("🎯 Analisis Ketercapaian RKAP (Persentase)")
            col_g1, col_g2 = st.columns(2)
            with col_g1:
                nilai_prod = persen_produksi if persen_produksi < 100 else 100
                fig_prod = buat_gauge_chart(nilai_prod, "Performance Produksi", teks_periode)
                st.plotly_chart(fig_prod, use_container_width=True)
            with col_g2:
                nilai_exp = round(persen_pengeluaran, 1) if persen_pengeluaran < 100 else 100
                fig_exp = buat_gauge_chart(nilai_exp, "Performance Pengeluaran", teks_periode)
                st.plotly_chart(fig_exp, use_container_width=True)

            st.subheader(f"📊 Tren Detail Bulanan - {pilih_produk_bln}")
            fig_bar = go.Figure()
            fig_bar.add_trace(go.Bar(x=df_filtered['Bulan'], y=df_filtered['Produksi'], name='Produksi', marker_color='#1F4E79'))
            fig_bar.add_trace(go.Bar(x=df_filtered['Bulan'], y=df_filtered['Pengeluaran'], name='Pengeluaran', marker_color='#FFC000'))
            fig_bar.add_trace(go.Bar(x=df_filtered['Bulan'], y=df_filtered['RKAP'], name='RKAP', marker_color='#ED7D31'))

            urutan_bulan = ['Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni', 'Juli', 'Agustus', 'September', 'Oktober', 'November', 'Desember']
            fig_bar.update_layout(
                barmode='group',
                legend=dict(orientation="h", yanchor="bottom", y=-0.3, xanchor="center", x=0.5),
                margin=dict(l=20, r=20, t=30, b=20),
                xaxis={'categoryorder':'array', 'categoryarray': urutan_bulan} 
            )
            fig_bar.update_yaxes(title_font=dict(color="black"), tickfont=dict(color="black"), tickformat=".2f")
            fig_bar.update_xaxes(title_font=dict(color="black"), tickfont=dict(color="black"))
            st.plotly_chart(fig_bar, use_container_width=True)
            
            with st.expander("Lihat Detail Tabel Data Bulanan"):
                df_tabel_bln = df_filtered[['Tahun', 'Bulan', 'Produk', 'Produksi', 'Pengeluaran', 'RKAP']].copy()
                st.dataframe(df_tabel_bln, use_container_width=True, hide_index=True)

        else:
            st.warning(f"Data tidak tersedia untuk {pilih_produk_bln} di {teks_periode}.")

    else:
        st.warning("Data bulanan di Sheet1 tidak ditemukan atau format tabel tidak sesuai.")


# =====================================================================
# --- HALAMAN 2: TREN HARIAN (LINE CHART) ---
# =====================================================================
elif halaman == "📈 Tren Harian (Line Chart)":
    try:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.image("Logo petro dkk.png", use_container_width=True)
    except FileNotFoundError:
        st.warning("⚠️ File logo belum dimasukkan atau nama file salah.")
        
    st.title("📈 Analisis Tren Harian per Produk")
    st.markdown("Grafik garis produksi dan pengeluaran berdasarkan data harian.")
    
    df_daily, list_produk = load_data_harian()
    
    if df_daily is not None and not df_daily.empty:
        df_daily['Tahun'] = df_daily['Tanggal'].dt.year
        df_daily['Bulan_Angka'] = df_daily['Tanggal'].dt.month
        
        dict_bulan = {
            1: 'Januari', 2: 'Februari', 3: 'Maret', 4: 'April',
            5: 'Mei', 6: 'Juni', 7: 'Juli', 8: 'Agustus',
            9: 'September', 10: 'Oktober', 11: 'November', 12: 'Desember'
        }
        df_daily['Nama_Bulan'] = df_daily['Bulan_Angka'].map(dict_bulan)

        col_f1, col_f2, col_f3 = st.columns(3)
        
        with col_f1:
            list_tahun_harian = sorted(df_daily['Tahun'].dropna().unique().tolist(), reverse=True)
            pilih_tahun_harian = st.selectbox("Pilih Tahun:", options=list_tahun_harian, key="filter_thn")
            
        df_tahun = df_daily[df_daily['Tahun'] == pilih_tahun_harian]
        list_bulan_angka = sorted(df_tahun['Bulan_Angka'].dropna().unique().tolist())
        list_bulan_teks = [dict_bulan[b] for b in list_bulan_angka]

        with col_f2:
            pilih_bulan_harian = st.selectbox("Pilih Bulan:", options=["Semua Bulan"] + list_bulan_teks, key="filter_bln")

        with col_f3:
            pilih_produk = st.selectbox("Pilih Produk:", options=list_produk, key="filter_prod")

        df_filtered = df_tahun[df_tahun['Produk'] == pilih_produk] 
        
        if pilih_bulan_harian != "Semua Bulan":
            df_filtered = df_filtered[df_filtered['Nama_Bulan'] == pilih_bulan_harian]
            st.subheader(f"Tren Harian {pilih_produk} - {pilih_bulan_harian} {pilih_tahun_harian}")
        else:
            st.subheader(f"Tren Harian {pilih_produk} - Keseluruhan Tahun {pilih_tahun_harian}")

        if not df_filtered.empty:
            fig_line = go.Figure()

            fig_line.add_trace(go.Scatter(
                x=df_filtered['Tanggal'], 
                y=df_filtered['Produksi'],
                mode='lines+markers',
                name='Produksi',
                line=dict(color='#1F4E79', width=3),
                marker=dict(size=7)
            ))

            fig_line.add_trace(go.Scatter(
                x=df_filtered['Tanggal'], 
                y=df_filtered['Stok'],
                mode='lines+markers',
                name='Stok',
                line=dict(color='#70AD47', width=3), # Menggunakan warna hijau agar kontras
                marker=dict(size=7)
            ))

            fig_line.add_trace(go.Scatter(
                x=df_filtered['Tanggal'], 
                y=df_filtered['Pengeluaran'],
                mode='lines+markers',
                name='Pengeluaran',
                line=dict(color='#FFC000', width=3),
                marker=dict(size=7)
            ))

            fig_line.update_layout(
                hovermode="x unified",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                margin=dict(l=0, r=0, t=30, b=100), 
                xaxis_title="Tanggal",
                yaxis_title="Nilai",
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)'
            )
            
            if pilih_bulan_harian != "Semua Bulan":
                fig_line.update_xaxes(dtick=86400000.0, tickformat="%d %b %Y", tickangle=-45)
            else:
                fig_line.update_xaxes(tickformat="%d %b %Y", tickangle=-45)

            fig_line.update_xaxes(showgrid=True, gridwidth=1, gridcolor='gray', griddash='dot')
            fig_line.update_yaxes(showgrid=True, gridwidth=1, gridcolor='gray', griddash='dot', tickformat=".2f")

            st.plotly_chart(fig_line, use_container_width=True)
            
            with st.expander("Lihat Detail Tabel Data"):
                df_tabel = df_filtered[['Tanggal', 'Produk', 'Produksi','Stok', 'Pengeluaran']].copy()
                df_tabel['Tanggal'] = df_tabel['Tanggal'].dt.strftime('%d-%m-%Y')
                st.dataframe(df_tabel, use_container_width=True, hide_index=True)
                
        else:
            st.warning(f"Data tidak tersedia untuk produk dan waktu yang dipilih.")
            
    else:
        st.warning("Data harian di Sheet3 tidak ditemukan atau format tabel tidak sesuai.")
