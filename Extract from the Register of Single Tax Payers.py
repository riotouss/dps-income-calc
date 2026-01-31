import streamlit as st
import pdfplumber
import pandas as pd
import io
import re
from datetime import datetime

st.set_page_config(page_title="Розрахунок доходу ДРФО", layout="wide")
st.title("📄 Розрахунок доходу (Витяг з реєстру ДПС)")

uploaded_file = st.file_uploader("Завантажте PDF-витяг про доходи", type="pdf")

def clean_amount(val):
    """Очищення рядка з сумою та перетворення у float"""
    if not val: return 0.0
    cleaned = str(val).replace(" ", "").replace(",", ".").replace("\n", "")
    try:
        return float(cleaned)
    except ValueError:
        return 0.0

if uploaded_file is not None:
    all_data = []
    
    with pdfplumber.open(io.BytesIO(uploaded_file.read())) as pdf:
        for page in pdf.pages:
            table = page.extract_table()
            if table:
                for row in table:
                    if len(row) >= 7:
                        year = re.search(r"20\d{2}", str(row[3]))
                        if year:
                            amount = clean_amount(row[5]) 
                            if amount > 0:
                                all_data.append({
                                    "Рік": year.group(),
                                    "Сума": amount
                                })

    if all_data:
        df = pd.DataFrame(all_data)
        yearly_summary = df.groupby("Рік")["Сума"].sum().reset_index()
        
        rows_main = []
        total_raw_all = 0.0
        total_net_all = 0.0

        for _, row in yearly_summary.iterrows():
            year = row["Рік"]
            sum_val = round(row["Сума"], 2)
            after_7 = round(sum_val * 0.93, 2)
            
            total_raw_all += sum_val
            total_net_all += after_7
            
            rows_main.append({
                "Рік": year,
                "Нараховано (грн)": sum_val,
                "Після -7% (грн)": after_7
            })

        st.subheader("📊 Результати розрахунку")
        st.table(pd.DataFrame(rows_main))

        col1, col2 = st.columns(2)
        with col1:
            st.metric("Загальна сума (брутто)", f"{round(total_raw_all, 2)} грн")
        with col2:
            st.metric("Загальна сума (-7%)", f"{round(total_net_all, 2)} грн")

        years_list = sorted(yearly_summary["Рік"].unique())
        period = f"{years_list[0]}-{years_list[-1]}" if len(years_list) > 1 else years_list[0]
        
        copy_text = f"Витяг ДРФО за період {period}; загальна сума {round(total_raw_all, 2)} грн; з урахуванням 7% {round(total_net_all, 2)} грн"
        
        st.text_area("📋 Коментар для копіювання:", value=copy_text, height=70)
    else:
        st.error("❌ Не вдалося знайти дані про доходи в таблиці. Перевірте формат файлу.")