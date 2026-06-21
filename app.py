import streamlit as st
import pandas as pd
import numpy as np
import os
import glob
from difflib import SequenceMatcher

st.set_page_config(page_title="Phân tích Pipeline", layout="wide", initial_sidebar_state="expanded")

st.title("📊 Phân Tích Biến Động Pipeline Kinh Doanh")
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

html, body, [class*="css"]  {
    font-family: 'Inter', sans-serif !important;
}

/* Metric Cards */
div[data-testid="stMetric"] {
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    padding: 15px 20px;
    border-radius: 12px;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
    transition: transform 0.2s ease, box-shadow 0.2s ease;
    border-left: 4px solid #3b82f6;
}
div[data-testid="stMetric"]:hover {
    transform: translateY(-3px);
    box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
}
div[data-testid="stMetricValue"] {
    font-size: 1.8rem;
    font-weight: 700;
    color: #1e293b;
}
div[data-testid="stMetricLabel"] {
    font-size: 1rem;
    font-weight: 600;
    color: #64748b;
    margin-bottom: 5px;
}

/* Headers */
h1 {
    background: -webkit-linear-gradient(45deg, #1d4ed8, #8b5cf6);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    font-weight: 800 !important;
}
h2 {
    color: #0f172a;
    font-weight: 700 !important;
    border-bottom: 2px solid #f1f5f9;
    padding-bottom: 10px;
    margin-top: 30px;
}
h3 {
    color: #334155;
    font-weight: 600 !important;
}

/* Sidebar */
[data-testid="stSidebar"] {
    background-color: #f8fafc;
    border-right: 1px solid #e2e8f0;
}

/* Tables */
table {
    width: 100%;
    border-collapse: collapse;
}
th {
    text-align: center !important;
    font-weight: 600 !important;
    color: #1e3a8a !important;
    font-size: 0.9rem;
    background-color: #eff6ff !important;
    padding: 12px 15px !important;
    border-bottom: 2px solid #bfdbfe !important;
}
td {
    padding: 12px 15px !important;
    border-bottom: 1px solid #e2e8f0 !important;
    color: #0f172a !important;
    vertical-align: middle !important;
}
tr:hover td {
    background-color: #f8fafc !important;
}

/* Buttons */
.stButton button {
    background: linear-gradient(135deg, #3b82f6 0%, #6366f1 100%);
    color: white !important;
    border: none;
    border-radius: 8px;
    font-weight: 600;
    transition: all 0.3s ease;
    box-shadow: 0 4px 6px -1px rgba(59, 130, 246, 0.2);
}
.stButton button:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 15px -3px rgba(59, 130, 246, 0.3);
}
</style>
<div style='margin-bottom: 2rem; color: #64748b; font-size: 1.1rem; font-weight: 500;'>
    ✨ Đối chiếu dòng chảy đơn hàng tự động bằng thuật toán AI khớp Tên khách hàng & Phòng ban.
</div>
""", unsafe_allow_html=True)

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

def save_uploaded_file(uploaded_file, prefix):
    for old_file in glob.glob(os.path.join(UPLOAD_DIR, f"{prefix}.*")):
        os.remove(old_file)
    ext = os.path.splitext(uploaded_file.name)[1]
    save_path = os.path.join(UPLOAD_DIR, f"{prefix}{ext}")
    with open(save_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return save_path

def get_saved_file(prefix):
    files = glob.glob(os.path.join(UPLOAD_DIR, f"{prefix}.*"))
    return files[0] if files else None

# --- SIDEBAR ---
st.sidebar.header("1. Nguồn Dữ Liệu")
file_prev = st.sidebar.file_uploader("1. Dự kiến tuần trước", type=["xlsx", "csv"])
if file_prev: save_uploaded_file(file_prev, "prev")
file_curr = st.sidebar.file_uploader("2. Dự kiến tuần này", type=["xlsx", "csv"])
if file_curr: save_uploaded_file(file_curr, "curr")

file_act_prev = st.sidebar.file_uploader("3. Doanh số lần trước", type=["xlsx", "csv"])
if file_act_prev: save_uploaded_file(file_act_prev, "act_prev")
file_act_curr = st.sidebar.file_uploader("4. Doanh số mới nhất", type=["xlsx", "csv"])
if file_act_curr: save_uploaded_file(file_act_curr, "act_curr")

path_prev = get_saved_file("prev")
path_curr = get_saved_file("curr")
path_act_prev = get_saved_file("act_prev")
path_act_curr = get_saved_file("act_curr")

st.sidebar.divider()
st.sidebar.subheader("Cấu hình Thuật toán")
fuzzy_threshold = st.sidebar.slider("Độ chính xác khớp Tên Khách hàng (%)", min_value=50, max_value=100, value=80, step=5) / 100.0

st.sidebar.divider()
st.sidebar.subheader("Cấu hình File Dự kiến")
has_summary_row = st.sidebar.checkbox("File Dự kiến có dòng tổng BU (màu vàng)?", value=True)
ffill_bu = st.sidebar.checkbox("Tự động điền tên BU xuống các dòng con", value=True)
risk_threshold = st.sidebar.number_input("Ngưỡng cảnh báo Top Deal (VNĐ)", value=1000000000, step=100000000)

def load_excel_data(file_path, sheet_name=None):
    try:
        if file_path.endswith('.csv'):
            return pd.read_csv(file_path)
        else:
            xls = pd.ExcelFile(file_path)
            if sheet_name:
                for sn in xls.sheet_names:
                    if sn.lower() == sheet_name.lower():
                        return pd.read_excel(file_path, sheet_name=sn)
                st.error(f"❌ Không tìm thấy sheet '{sheet_name}' trong file. Các sheet hiện có: {xls.sheet_names}")
                return None
            # Nếu không chỉ định sheet_name, ưu tiên tìm sheet chứa data thay vì report
            best_sheet = xls.sheet_names[0]
            for sn in xls.sheet_names:
                sn_lower = sn.lower()
                if any(k in sn_lower for k in ['danh sách', 'data', 'dữ liệu', 'chi tiết']):
                    best_sheet = sn
                    break
            return pd.read_excel(file_path, sheet_name=best_sheet)
    except Exception as e:
        st.error(f"❌ Lỗi khi đọc file: {e}")
        return None

def auto_detect_col(df, keywords, fallback_index=0):
    for col in df.columns:
        col_str = str(col).lower()
        if 'unnamed' in col_str: continue
        for kw in keywords:
            if kw in col_str: return col
                
    for i in range(min(10, len(df))):
        for col_idx, val in enumerate(df.iloc[i]):
            val_str = str(val).lower()
            for kw in keywords:
                if kw in val_str: return df.columns[col_idx]
                    
    try: return df.columns[fallback_index]
    except: return df.columns[0]

if path_prev and path_curr and path_act_prev and path_act_curr:
    df_prev_raw = load_excel_data(path_prev)
    df_curr_raw = load_excel_data(path_curr)
    df_act_prev_raw = load_excel_data(path_act_prev, sheet_name="Data doanh số")
    df_act_curr_raw = load_excel_data(path_act_curr, sheet_name="Data doanh số")

    if df_prev_raw is not None and df_curr_raw is not None and df_act_prev_raw is not None and df_act_curr_raw is not None:
        
        # --- TỰ ĐỘNG TÌM CỘT ---
        kw_name = ['khách hàng', 'khách', 'công ty', 'tên khách']
        kw_rev = ['doanh số', 'giá trị', 'revenue', 'tiền']
        kw_bu = ['phòng ban', 'bu', 'bộ phận']
        kw_status = ['trạng thái', 'status', 'loại']
        kw_contract = ['mã hợp đồng', 'mã hđ', 'contract']
        
        prev_name = auto_detect_col(df_prev_raw, kw_name, fallback_index=1)
        prev_rev = auto_detect_col(df_prev_raw, kw_rev, fallback_index=2)
        prev_bu = auto_detect_col(df_prev_raw, kw_bu, fallback_index=3)
        prev_status = auto_detect_col(df_prev_raw, kw_status, fallback_index=4)

        curr_name = auto_detect_col(df_curr_raw, kw_name, fallback_index=1)
        curr_rev = auto_detect_col(df_curr_raw, kw_rev, fallback_index=2)
        curr_bu = auto_detect_col(df_curr_raw, kw_bu, fallback_index=3)
        curr_status = auto_detect_col(df_curr_raw, kw_status, fallback_index=4)

        act_prev_name = auto_detect_col(df_act_prev_raw, kw_name, fallback_index=1)
        act_prev_rev = auto_detect_col(df_act_prev_raw, kw_rev, fallback_index=2)
        act_prev_bu = auto_detect_col(df_act_prev_raw, kw_bu, fallback_index=3)
        act_prev_contract = auto_detect_col(df_act_prev_raw, kw_contract, fallback_index=5)

        act_curr_name = auto_detect_col(df_act_curr_raw, kw_name, fallback_index=1)
        act_curr_rev = auto_detect_col(df_act_curr_raw, kw_rev, fallback_index=2)
        act_curr_bu = auto_detect_col(df_act_curr_raw, kw_bu, fallback_index=3)
        act_curr_contract = auto_detect_col(df_act_curr_raw, kw_contract, fallback_index=5)

        if st.button("Bắt đầu Phân tích", type="primary"):
            def clean_data(df_raw, col_name, col_rev, col_bu, col_status=None, col_contract=None, is_expected=True):
                if is_expected and col_status:
                    df = df_raw[[col_name, col_rev, col_bu, col_status]].copy()
                    df.columns = ['Name', 'Revenue', 'BU', 'Status']
                else:
                    if col_contract:
                        df = df_raw[[col_name, col_rev, col_bu, col_contract]].copy()
                        df.columns = ['Name', 'Revenue', 'BU', 'Contract_Code']
                    else:
                        df = df_raw[[col_name, col_rev, col_bu]].copy()
                        df.columns = ['Name', 'Revenue', 'BU']
                        df['Contract_Code'] = ''
                    df['Status'] = 'N/A'
                
                if is_expected and ffill_bu:
                    df['BU'] = df['BU'].replace('', np.nan).ffill()
                
                if is_expected and has_summary_row:
                    df = df.dropna(subset=['Name'])
                    df = df[~df['Name'].astype(str).str.lower().str.contains('tổng|total', na=False)]
                    
                df['Name'] = df['Name'].astype(str).str.strip()
                df['BU'] = df['BU'].astype(str).str.strip()
                df['Status'] = df['Status'].astype(str).str.strip()
                df['Revenue'] = pd.to_numeric(df['Revenue'], errors='coerce').fillna(0)
                df = df[df['Name'] != 'nan']
                df = df[df['Name'] != 'None']
                df = df[df['Name'] != '']
                
                # Bỏ qua dòng tiêu đề bị lọt vào dữ liệu
                df = df[~df['BU'].str.lower().isin(['phòng ban', 'bu', 'bộ phận'])]
                df = df[~df['Name'].str.lower().isin(['khách hàng', 'khách', 'công ty', 'tên khách'])]
                return df

            df_prev = clean_data(df_prev_raw, prev_name, prev_rev, prev_bu, prev_status, is_expected=True)
            df_curr = clean_data(df_curr_raw, curr_name, curr_rev, curr_bu, curr_status, is_expected=True)
            
            df_act_prev_clean = clean_data(df_act_prev_raw, act_prev_name, act_prev_rev, act_prev_bu, col_contract=act_prev_contract, is_expected=False)
            df_act_curr_clean = clean_data(df_act_curr_raw, act_curr_name, act_curr_rev, act_curr_bu, col_contract=act_curr_contract, is_expected=False)

            def normalize_name(s): return str(s).lower().strip()
            df_prev['Name_Norm'] = df_prev['Name'].apply(normalize_name)
            df_curr['Name_Norm'] = df_curr['Name'].apply(normalize_name)
            df_act_prev_clean['Name_Norm'] = df_act_prev_clean['Name'].apply(normalize_name)
            df_act_curr_clean['Name_Norm'] = df_act_curr_clean['Name'].apply(normalize_name)

            df_prev = df_prev.groupby(['BU', 'Name_Norm', 'Status']).agg({'Name':'first', 'Revenue':'sum'}).reset_index()
            # Thêm ID duy nhất để dễ track khi map 1-1
            df_prev['Prev_ID'] = range(len(df_prev))

            df_curr = df_curr.groupby(['BU', 'Name_Norm', 'Status']).agg({'Name':'first', 'Revenue':'sum'}).reset_index()
            
            # Gộp nhóm Actual file bằng UID để tránh trùng lặp khi đổi tên khách hàng
            df_act_prev_clean['Contract_Code'] = df_act_prev_clean['Contract_Code'].fillna('').astype(str).str.strip()
            df_act_curr_clean['Contract_Code'] = df_act_curr_clean['Contract_Code'].fillna('').astype(str).str.strip()
            
            df_act_prev_clean['UID'] = df_act_prev_clean.apply(lambda x: x['Contract_Code'] if x['Contract_Code'] else f"{x['BU']}|{x['Name_Norm']}", axis=1)
            df_act_curr_clean['UID'] = df_act_curr_clean.apply(lambda x: x['Contract_Code'] if x['Contract_Code'] else f"{x['BU']}|{x['Name_Norm']}", axis=1)

            df_act_prev = df_act_prev_clean.groupby(['BU', 'UID']).agg({'Name_Norm':'first', 'Contract_Code':'first', 'Name':'first', 'Revenue':'sum'}).reset_index()
            df_act_curr = df_act_curr_clean.groupby(['BU', 'UID']).agg({'Name_Norm':'first', 'Contract_Code':'first', 'Name':'first', 'Revenue':'sum'}).reset_index()

            # --- TÌM ĐƠN ĐƯỢC KÝ TRONG KHOẢNG ĐÓ ---
            df_act_merged = pd.merge(df_act_curr, df_act_prev[['BU', 'UID', 'Revenue']], on=['BU', 'UID'], how='left', suffixes=('', '_prev'))
            df_act_merged['Revenue_prev'] = df_act_merged['Revenue_prev'].fillna(0)
            df_act_merged['New_Revenue'] = df_act_merged['Revenue'] - df_act_merged['Revenue_prev']
            
            # Chỉ lấy các đơn có New_Revenue > 0 làm 'đơn đã ký' trong kỳ
            df_act = df_act_merged[df_act_merged['New_Revenue'] > 0].copy()
            df_act['Revenue'] = df_act['New_Revenue']
            df_act = df_act[['BU', 'Name_Norm', 'Contract_Code', 'Name', 'Revenue']]

            def get_best_match(name, choices, threshold):
                best_score = 0
                best_match = None
                for choice in choices:
                    score = SequenceMatcher(None, name, choice).ratio()
                    if score > best_score:
                        best_score = score
                        best_match = choice
                if best_score >= threshold: return best_match, best_score
                return None, 0

            with st.spinner("Đang chạy thuật toán AI phân tích dữ liệu..."):
                # 1. TÌM SUCCESS (Map 1-1 từ ACT ngược về PREV)
                success_rows = []
                unexpected_success_rows = []
                matched_prev_ids = set()
                contract_to_prev_match = {}
                
                # Tính tổng doanh số thực tế cho từng mã hợp đồng để chia tỷ trọng doanh số dự kiến
                contract_totals = {}
                for _, r in df_act.iterrows():
                    if r['Contract_Code']:
                        contract_totals[r['Contract_Code']] = contract_totals.get(r['Contract_Code'], 0) + r['Revenue']
                
                for _, act_row in df_act.iterrows():
                    # Tính doanh số dự kiến được phân bổ (tỷ lệ thuận với doanh số chốt)
                    def get_allocated_prev(best_match_rev):
                        if act_row['Contract_Code'] and contract_totals.get(act_row['Contract_Code'], 0) > 0:
                            return best_match_rev * (act_row['Revenue'] / contract_totals[act_row['Contract_Code']])
                        return best_match_rev

                    # Nếu Contract_Code này đã được map với một Prev_ID nào đó, thì auto map luôn (chia sẻ doanh số)
                    if act_row['Contract_Code'] and act_row['Contract_Code'] in contract_to_prev_match:
                        best_match = contract_to_prev_match[act_row['Contract_Code']]
                        success_rows.append({
                            'BU': act_row['BU'],
                            'Name': act_row['Name'],
                            'Status': best_match['Status'],
                            'Revenue_prev': get_allocated_prev(best_match['Revenue']),
                            'Revenue_act': act_row['Revenue']
                        })
                        continue

                    # Tìm các ứng viên PREV trên TOÀN BỘ CÁC BU và chưa được map
                    candidates_df = df_prev[~df_prev['Prev_ID'].isin(matched_prev_ids)].copy()
                    if candidates_df.empty:
                        unexpected_success_rows.append({
                            'BU': act_row['BU'], 
                            'Name': act_row['Name'], 
                            'Status': 'Không có trong Dự kiến',
                            'Revenue_prev': 0, 
                            'Revenue_act': act_row['Revenue']
                        })
                        continue
                    
                    # Tính fuzzy score cho tất cả ứng viên
                    candidates_df['Fuzzy_Score'] = candidates_df['Name_Norm'].apply(lambda x: SequenceMatcher(None, act_row['Name_Norm'], x).ratio())
                    
                    # Ưu tiên các ứng viên cùng BU (cộng thêm 0.05 điểm)
                    candidates_df.loc[candidates_df['BU'] == act_row['BU'], 'Fuzzy_Score'] += 0.05
                    
                    valid_candidates = candidates_df[candidates_df['Fuzzy_Score'] >= fuzzy_threshold].copy()
                    
                    if not valid_candidates.empty:
                        # Nếu có nhiều ứng viên, ưu tiên: 1. Fuzzy Score cao nhất, 2. Doanh số gần giống nhất
                        valid_candidates['Rev_Diff'] = abs(valid_candidates['Revenue'] - act_row['Revenue'])
                        valid_candidates = valid_candidates.sort_values(by=['Fuzzy_Score', 'Rev_Diff'], ascending=[False, True])
                        
                        best_match = valid_candidates.iloc[0]
                        matched_prev_ids.add(best_match['Prev_ID'])
                        if act_row['Contract_Code']:
                            contract_to_prev_match[act_row['Contract_Code']] = best_match
                        
                        success_rows.append({
                            'BU': act_row['BU'],
                            'Name': act_row['Name'],
                            'Status': best_match['Status'],
                            'Revenue_prev': get_allocated_prev(best_match['Revenue']),
                            'Revenue_act': act_row['Revenue']
                        })
                    else:
                        unexpected_success_rows.append({
                            'BU': act_row['BU'], 
                            'Name': act_row['Name'], 
                            'Status': 'Không có trong Dự kiến',
                            'Revenue_prev': 0, 
                            'Revenue_act': act_row['Revenue']
                        })

                # Các đơn PREV không được map -> Unmatched
                df_prev_unmatched = df_prev[~df_prev['Prev_ID'].isin(matched_prev_ids)].copy()
                df_success = pd.DataFrame(success_rows)
                df_unexpected_success = pd.DataFrame(unexpected_success_rows)

                # 2. TÌM DELAY VÀ LOST
                delay_rows = []
                lost_rows = []
                decreased_rows = []
                increased_rows = []
                for idx, row in df_prev_unmatched.iterrows():
                    candidates = df_curr[df_curr['BU'] == row['BU']]['Name_Norm'].tolist()
                    match, score = get_best_match(row['Name_Norm'], candidates, fuzzy_threshold)
                    
                    status_lower = str(row.get('Status', '')).lower()
                    is_expected = 'dự kiến' in status_lower
                    
                    if match:
                        if is_expected:
                            # Lấy thông tin từ file dự kiến tuần này (curr) thay vì tuần trước (prev)
                            matched_curr_row = df_curr[(df_curr['BU'] == row['BU']) & (df_curr['Name_Norm'] == match)].iloc[0]
                            delay_rows.append(matched_curr_row.to_dict())
                            
                            # Tính delta doanh số dự kiến
                            diff_rev = matched_curr_row['Revenue'] - row['Revenue']
                            if diff_rev < 0:
                                decreased_rows.append({
                                    'BU': row['BU'],
                                    'Name': matched_curr_row['Name'],
                                    'Status': matched_curr_row['Status'],
                                    'Revenue_prev': row['Revenue'],
                                    'Revenue_curr': matched_curr_row['Revenue'],
                                    'Revenue_diff': diff_rev
                                })
                            elif diff_rev > 0:
                                increased_rows.append({
                                    'BU': row['BU'],
                                    'Name': matched_curr_row['Name'],
                                    'Status': matched_curr_row['Status'],
                                    'Revenue_prev': row['Revenue'],
                                    'Revenue_curr': matched_curr_row['Revenue'],
                                    'Revenue_diff': diff_rev
                                })
                    else:
                        if is_expected:
                            lost_rows.append(row.to_dict())
                        
                df_delay = pd.DataFrame(delay_rows)
                df_lost = pd.DataFrame(lost_rows)
                df_decreased = pd.DataFrame(decreased_rows)
                df_increased = pd.DataFrame(increased_rows)

                # 3. TÌM NEW
                new_curr_rows = []
                for idx, row in df_curr.iterrows():
                    candidates = df_prev[df_prev['BU'] == row['BU']]['Name_Norm'].tolist()
                    match, _ = get_best_match(row['Name_Norm'], candidates, fuzzy_threshold)
                    if not match: new_curr_rows.append(row.to_dict())
                df_new = pd.DataFrame(new_curr_rows)

            # --- TỔNG HỢP SỐ LIỆU THEO TRẠNG THÁI ---
            def get_sum_by_status(df, keyword):
                if df.empty: return 0
                return df[df['Status'].str.lower().str.contains(keyword, na=False)]['Revenue'].sum()

            prev_thang = get_sum_by_status(df_prev, 'tháng')
            prev_tiem_nang = get_sum_by_status(df_prev, 'tiềm năng')
            
            curr_thang = get_sum_by_status(df_curr, 'tháng')
            curr_tiem_nang = get_sum_by_status(df_curr, 'tiềm năng')

            total_prev = df_prev['Revenue'].sum()
            total_curr = df_curr['Revenue'].sum()
            total_act = df_act['Revenue'].sum()
            
            val_success_act = df_success['Revenue_act'].sum() if not df_success.empty else 0
            val_unexpected_success = df_unexpected_success['Revenue_act'].sum() if not df_unexpected_success.empty else 0
            val_delay = df_delay['Revenue'].sum() if not df_delay.empty else 0
            val_lost = df_lost['Revenue'].sum() if not df_lost.empty else 0
            val_new = df_new['Revenue'].sum() if not df_new.empty else 0

            # --- KẾT XUẤT ---
            st.divider()
            st.header("Phần 1: Bảng tổng hợp số liệu (Executive Summary)")
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Tổng DS Dự kiến Tuần trước", f"{total_prev:,.0f}")
            m2.metric("Tổng DS Dự kiến Tuần này", f"{total_curr:,.0f}", f"{(total_curr - total_prev):,.0f} ({((total_curr-total_prev)/total_prev*100) if total_prev > 0 else 0:.1f}%)")
            m3.metric("Đã ký từ Dự kiến (Trong kỳ)", f"{val_success_act:,.0f}")
            conversion_rate = (val_success_act / total_prev * 100) if total_prev > 0 else 0
            m4.metric("Tỷ lệ Chuyển đổi", f"{conversion_rate:.1f}%")

            st.markdown("##### 📌 Phân loại trạng thái Đơn dự kiến")
            st.info(f"**Tuần trước:** Dự kiến ký tháng: **{prev_thang:,.0f}** | Tiềm năng: **{prev_tiem_nang:,.0f}**\n\n"
                    f"**Tuần này:** Dự kiến ký tháng: **{curr_thang:,.0f}** | Tiềm năng: **{curr_tiem_nang:,.0f}**")

            st.subheader("Phân rã số liệu dự kiến theo Bộ phận/BU")
            bu_prev = df_prev.groupby('BU')['Revenue'].sum().reset_index().rename(columns={'Revenue': 'Tuần Trước'})
            bu_curr = df_curr.groupby('BU')['Revenue'].sum().reset_index().rename(columns={'Revenue': 'Tuần Này'})
            bu_summary = pd.merge(bu_prev, bu_curr, on='BU', how='outer').fillna(0)
            bu_summary['Tăng/Giảm'] = bu_summary['Tuần Này'] - bu_summary['Tuần Trước']
            bu_summary['% Thay đổi'] = (bu_summary['Tăng/Giảm'] / bu_summary['Tuần Trước'] * 100).fillna(0).round(1)
            
            total_prev_bu = bu_summary['Tuần Trước'].sum()
            total_curr_bu = bu_summary['Tuần Này'].sum()
            total_tang_giam = bu_summary['Tăng/Giảm'].sum()
            total_pct = (total_tang_giam / total_prev_bu * 100) if total_prev_bu else 0
            
            bu_summary.loc[len(bu_summary)] = {
                'BU': 'TỔNG CỘNG',
                'Tuần Trước': total_prev_bu,
                'Tuần Này': total_curr_bu,
                'Tăng/Giảm': total_tang_giam,
                '% Thay đổi': total_pct
            }
            bu_summary.index = range(1, len(bu_summary) + 1)
            bu_summary.index = list(range(1, len(bu_summary))) + [""]
            bu_summary = bu_summary.reset_index().rename(columns={'index': 'STT'})
            st.markdown(
                bu_summary.style.format({
                    "Tuần Trước": "{:,.0f}", 
                    "Tuần Này": "{:,.0f}", 
                    "Tăng/Giảm": "{:,.0f}", 
                    "% Thay đổi": "{:.1f}%"
                }).set_table_styles([{'selector': 'th', 'props': [('text-align', 'center !important')]}])
                .hide(axis='index')
                .apply(lambda x: ['font-weight: 700; background-color: #dbeafe; color: #1d4ed8;' if x['BU'] == 'TỔNG CỘNG' else '' for _ in x], axis=1)
                .set_properties(subset=['STT', 'BU'], **{'text-align': 'center'})
                .set_properties(subset=['Tuần Trước', 'Tuần Này', 'Tăng/Giảm', '% Thay đổi'], **{'text-align': 'right'})
                .to_html(escape=False), unsafe_allow_html=True
            )

            st.header("Phần 2: Phân tích dòng chảy Pipeline (Movement Analysis)")
            mov1, mov2, mov3, mov4 = st.columns(4)
            mov1.metric("✅ Đã chốt thành công", f"{(val_success_act + val_unexpected_success):,.0f}")
            mov2.metric("⏳ Bị chậm tiến độ (Delay)", f"{val_delay:,.0f}", delta_color="off")
            mov3.metric("🔥 Phát sinh mới", f"{val_new:,.0f}")
            mov4.metric("❌ Biến mất / Nghi fail", f"{val_lost:,.0f}", delta_color="inverse")
            
            val_decreased = df_decreased['Revenue_diff'].sum() if not df_decreased.empty else 0
            val_increased = df_increased['Revenue_diff'].sum() if not df_increased.empty else 0
            if val_decreased != 0 or val_increased != 0:
                mov5, mov6, mov7, mov8 = st.columns(4)
                mov5.metric("⬇️ Giảm doanh số dự kiến", f"{abs(val_decreased):,.0f}", delta_color="inverse")
                mov6.metric("⬆️ Tăng doanh số dự kiến", f"{val_increased:,.0f}", delta_color="normal")

            st.header("Phần 3: Danh sách chi tiết Đơn hàng (Action List)")
            
            st.subheader("🎉 1. Các đơn hàng ĐÃ CHỐT THÀNH CÔNG (Từ các đơn dự kiến ký)")
            if df_success.empty: 
                st.info("Chưa có đơn hàng nào chốt thành công từ dự kiến.")
            else: 
                df_success_display = df_success[['BU', 'Name', 'Status', 'Revenue_prev', 'Revenue_act']].rename(
                    columns={'Revenue_prev': 'DS Dự kiến', 'Revenue_act': 'DS Thực tế (Đã ký)'}
                )
                total_prev_succ = df_success_display['DS Dự kiến'].sum()
                total_act_succ = df_success_display['DS Thực tế (Đã ký)'].sum()
                df_success_display.loc[len(df_success_display)] = {
                    'BU': 'TỔNG CỘNG', 'Name': '', 'Status': '',
                    'DS Dự kiến': total_prev_succ, 'DS Thực tế (Đã ký)': total_act_succ
                }
                df_success_display.index = list(range(1, len(df_success_display))) + [""]
                df_success_display = df_success_display.reset_index().rename(columns={'index': 'STT'})
                st.markdown(
                    df_success_display.style.format({
                        "DS Dự kiến": "{:,.0f}", 
                        "DS Thực tế (Đã ký)": "{:,.0f}"
                    }).set_table_styles([{'selector': 'th', 'props': [('text-align', 'center !important')]}])
                    .hide(axis='index')
                    .apply(lambda x: ['font-weight: 700; background-color: #dbeafe; color: #1d4ed8;' if x['BU'] == 'TỔNG CỘNG' else '' for _ in x], axis=1)
                    .set_properties(subset=['STT', 'BU', 'Name', 'Status'], **{'text-align': 'center'})
                    .set_properties(subset=['DS Dự kiến', 'DS Thực tế (Đã ký)'], **{'text-align': 'right'})
                    .to_html(escape=False), unsafe_allow_html=True
                )

            st.subheader("🔥 2. Các đơn hàng CHỐT NÓNG (Không nằm trong dự kiến ký)")
            if df_unexpected_success.empty: 
                st.info("Không có đơn hàng nào chốt nóng ngoài dự kiến.")
            else: 
                df_unexpected_display = df_unexpected_success[['BU', 'Name', 'Status', 'Revenue_act']].rename(
                    columns={'Revenue_act': 'DS Thực tế (Đã ký)'}
                )
                total_act_unexp = df_unexpected_display['DS Thực tế (Đã ký)'].sum()
                df_unexpected_display.loc[len(df_unexpected_display)] = {
                    'BU': 'TỔNG CỘNG', 'Name': '', 'Status': '', 'DS Thực tế (Đã ký)': total_act_unexp
                }
                df_unexpected_display.index = list(range(1, len(df_unexpected_display))) + [""]
                df_unexpected_display = df_unexpected_display.reset_index().rename(columns={'index': 'STT'})
                st.markdown(
                    df_unexpected_display.style.format({
                        "DS Thực tế (Đã ký)": "{:,.0f}"
                    }).set_table_styles([{'selector': 'th', 'props': [('text-align', 'center !important')]}])
                    .hide(axis='index')
                    .apply(lambda x: ['font-weight: 700; background-color: #dbeafe; color: #1d4ed8;' if x['BU'] == 'TỔNG CỘNG' else '' for _ in x], axis=1)
                    .set_properties(subset=['STT', 'BU', 'Name', 'Status'], **{'text-align': 'center'})
                    .set_properties(subset=['DS Thực tế (Đã ký)'], **{'text-align': 'right'})
                    .to_html(escape=False), unsafe_allow_html=True
                )

            st.subheader("🚨 Các đơn hàng NGHI NGỜ FAIL (Biến mất khỏi Pipeline)")
            if df_lost.empty: st.success("Không có đơn hàng nào bị biến mất!")
            else: 
                df_lost_display = df_lost[['BU', 'Name', 'Status', 'Revenue']].copy()
                total_lost = df_lost_display['Revenue'].sum()
                df_lost_display.loc[len(df_lost_display)] = {
                    'BU': 'TỔNG CỘNG', 'Name': '', 'Status': '', 'Revenue': total_lost
                }
                df_lost_display.index = list(range(1, len(df_lost_display))) + [""]
                df_lost_display = df_lost_display.reset_index().rename(columns={'index': 'STT'})
                st.markdown(
                    df_lost_display.style.format({
                        "Revenue": "{:,.0f}"
                    }).set_table_styles([{'selector': 'th', 'props': [('text-align', 'center !important')]}])
                    .hide(axis='index')
                    .apply(lambda x: ['font-weight: 700; background-color: #dbeafe; color: #1d4ed8;' if x['BU'] == 'TỔNG CỘNG' else '' for _ in x], axis=1)
                    .set_properties(subset=['STT', 'BU', 'Name', 'Status'], **{'text-align': 'center'})
                    .set_properties(subset=['Revenue'], **{'text-align': 'right'})
                    .to_html(escape=False), unsafe_allow_html=True
                )

            st.subheader(f"⚠️ Cảnh báo Top Deal bị DELAY (Các đơn >= {risk_threshold:,.0f} VNĐ)")
            if not df_delay.empty:
                top_delays = df_delay[df_delay['Revenue'] >= risk_threshold].sort_values(by='Revenue', ascending=False)
                if top_delays.empty: 
                    st.success(f"Không có đơn Delay nào lớn hơn ngưỡng {risk_threshold:,.0f} VNĐ.")
                else:
                    top_delays_display = top_delays[['BU', 'Name', 'Status', 'Revenue']].copy().reset_index(drop=True)
                    total_delay = top_delays_display['Revenue'].sum()
                    top_delays_display.loc[len(top_delays_display)] = {
                        'BU': 'TỔNG CỘNG', 'Name': '', 'Status': '', 'Revenue': total_delay
                    }
                    top_delays_display.index = list(range(1, len(top_delays_display))) + [""]
                    top_delays_display = top_delays_display.reset_index().rename(columns={'index': 'STT'})
                    st.markdown(
                        top_delays_display.style.format({
                            "Revenue": "{:,.0f}"
                        }).set_table_styles([{'selector': 'th', 'props': [('text-align', 'center !important')]}])
                        .hide(axis='index')
                        .apply(lambda x: ['font-weight: 700; background-color: #dbeafe; color: #1d4ed8;' if x['BU'] == 'TỔNG CỘNG' else '' for _ in x], axis=1)
                        .set_properties(subset=['STT', 'BU', 'Name', 'Status'], **{'text-align': 'center'})
                        .set_properties(subset=['Revenue'], **{'text-align': 'right'})
                        .to_html(escape=False), unsafe_allow_html=True
                    )
            else:
                st.success("Không có đơn hàng nào bị Delay.")
                
            st.subheader("📉 Các đơn hàng GIẢM Doanh số dự kiến (So với tuần trước)")
            if not df_decreased.empty:
                df_dec_display = df_decreased.copy().sort_values(by='Revenue_diff', ascending=True).reset_index(drop=True)
                total_prev = df_dec_display['Revenue_prev'].sum()
                total_curr = df_dec_display['Revenue_curr'].sum()
                total_diff = df_dec_display['Revenue_diff'].sum()
                
                df_dec_display.loc[len(df_dec_display)] = {
                    'BU': 'TỔNG CỘNG', 'Name': '', 'Status': '', 
                    'Revenue_prev': total_prev, 'Revenue_curr': total_curr, 'Revenue_diff': total_diff
                }
                df_dec_display.index = list(range(1, len(df_dec_display))) + [""]
                df_dec_display = df_dec_display.reset_index().rename(columns={
                    'index': 'STT',
                    'Revenue_prev': 'DS Tuần trước',
                    'Revenue_curr': 'DS Tuần này',
                    'Revenue_diff': 'Mức Giảm'
                })
                st.markdown(
                    df_dec_display.style.format({
                        "DS Tuần trước": "{:,.0f}",
                        "DS Tuần này": "{:,.0f}",
                        "Mức Giảm": "{:,.0f}"
                    }).set_table_styles([{'selector': 'th', 'props': [('text-align', 'center !important')]}])
                    .hide(axis='index')
                    .apply(lambda x: ['font-weight: 700; background-color: #fee2e2; color: #b91c1c;' if x['BU'] == 'TỔNG CỘNG' else '' for _ in x], axis=1)
                    .set_properties(subset=['STT', 'BU', 'Name', 'Status'], **{'text-align': 'center'})
                    .set_properties(subset=['DS Tuần trước', 'DS Tuần này', 'Mức Giảm'], **{'text-align': 'right'})
                    .to_html(escape=False), unsafe_allow_html=True
                )
            else:
                st.success("Tuyệt vời! Không có đơn hàng nào bị giảm doanh số dự kiến.")
                
            st.subheader("📈 Các đơn hàng TĂNG Doanh số dự kiến (So với tuần trước)")
            if not df_increased.empty:
                df_inc_display = df_increased.copy().sort_values(by='Revenue_diff', ascending=False).reset_index(drop=True)
                total_prev = df_inc_display['Revenue_prev'].sum()
                total_curr = df_inc_display['Revenue_curr'].sum()
                total_diff = df_inc_display['Revenue_diff'].sum()
                
                df_inc_display.loc[len(df_inc_display)] = {
                    'BU': 'TỔNG CỘNG', 'Name': '', 'Status': '', 
                    'Revenue_prev': total_prev, 'Revenue_curr': total_curr, 'Revenue_diff': total_diff
                }
                df_inc_display.index = list(range(1, len(df_inc_display))) + [""]
                df_inc_display = df_inc_display.reset_index().rename(columns={
                    'index': 'STT',
                    'Revenue_prev': 'DS Tuần trước',
                    'Revenue_curr': 'DS Tuần này',
                    'Revenue_diff': 'Mức Tăng'
                })
                st.markdown(
                    df_inc_display.style.format({
                        "DS Tuần trước": "{:,.0f}",
                        "DS Tuần này": "{:,.0f}",
                        "Mức Tăng": "{:,.0f}"
                    }).set_table_styles([{'selector': 'th', 'props': [('text-align', 'center !important')]}])
                    .hide(axis='index')
                    .apply(lambda x: ['font-weight: 700; background-color: #dcfce7; color: #15803d;' if x['BU'] == 'TỔNG CỘNG' else '' for _ in x], axis=1)
                    .set_properties(subset=['STT', 'BU', 'Name', 'Status'], **{'text-align': 'center'})
                    .set_properties(subset=['DS Tuần trước', 'DS Tuần này', 'Mức Tăng'], **{'text-align': 'right'})
                    .to_html(escape=False), unsafe_allow_html=True
                )
            else:
                st.info("Không có đơn hàng nào tăng doanh số dự kiến.")

else:
    st.info("👈 Vui lòng tải lên đủ 4 file ở thanh bên trái để bắt đầu phân tích.")
