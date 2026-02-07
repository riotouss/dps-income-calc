import streamlit as st
import pdfplumber
import pandas as pd
import io
import re
import streamlit.components.v1 as components

st.set_page_config(page_title="Калькулятор ДПС", layout="wide")
st.title("📄 Парсинг доходу з колонки 'Виплаченого'")

uploaded_file = st.file_uploader("Завантажте PDF-витяг", type="pdf")

def clean_value(val):
    """Очищує текст клітинки та конвертує в число"""
    if not val: return 0.0
    cleaned = str(val).replace("\n", " ").replace(" ", "").replace(",", ".")
    amounts = re.findall(r"[-+]?\d*\.\d+|\d+", cleaned)
    if amounts:
        return float(amounts[-1])
    return 0.0

if uploaded_file:
    raw_data = []
    
    with pdfplumber.open(io.BytesIO(uploaded_file.read())) as pdf:
        for page in pdf.pages:
            table = page.extract_table()
            if not table:
                continue
            
            header_row = table[0]
            
            for row in table:
                row_str = " ".join([str(c) for c in row if c])
                year_match = re.search(r"\b(202\d)\b", row_str)
                
                if year_match:
                    year = year_match.group(1)
                     
                    vyp_amount = 0.0
                    
                    if len(row) >= 8:
                        vyp_amount = clean_value(row[7])
                        
                        if vyp_amount == 0:
                            vyp_amount = clean_value(row[5])
                    elif len(row) >= 6:
                        vyp_amount = clean_value(row[5])

                    if vyp_amount > 0 and vyp_amount < 1000000:
                        raw_data.append({"Рік": year, "Виплачено": vyp_amount})

    if raw_data:
        df = pd.DataFrame(raw_data)
        df["Рік"] = df["Рік"].astype(str)
        
        summary = df.groupby("Рік")["Виплачено"].sum().reset_index()
        summary["Після -7%"] = (summary["Виплачено"] * 0.93).round(2)
        
        st.success("✅ Дані з колонки 'Виплачено' зібрано")
        
        display_df = summary.copy()
        display_df["Виплачено"] = display_df["Виплачено"].map("{:,.2f} грн".format)
        display_df["Після -7%"] = display_df["Після -7%"].map("{:,.2f} грн".format)
        
        st.table(display_df)
        
        total_vyp = summary["Виплачено"].sum()
        total_net = summary["Після -7%"].sum()
        
        col1, col2 = st.columns(2)
        col1.metric("Всього виплачено", f"{total_vyp:,.2f} грн")
        col2.metric("Чистий дохід (-7%)", f"{total_net:,.2f} грн")

        period = f"{summary['Рік'].iloc[0]}-{summary['Рік'].iloc[-1]}"
        comment = f"Витяг ДРФО; період {period}; сума виплаченого доходу {total_vyp:.2f} грн; з урахуванням 7% {total_net:.2f} грн"
        
st.markdown("📎 **Коментар:**")
        components.html(f"""
            <div style="background:#1e1e1e; color:white; padding:15px; border-radius:10px; font-family:sans-serif;">
                <div id="c">{comment}</div>
                <button onclick="copy()" style="margin-top:10px; background:#4CAF50; color:white; border:none; padding:8px 15px; border-radius:5px; cursor:pointer;">
                    📋 Скопіювати
                </button>
            </div>
            <script>
                function copy() {{
                    const t = document.getElementById('c').innerText;
                    navigator.clipboard.writeText(t);
                    alert('Скопійовано!');
                }}
            </script>
        """, height=150)
    else:
        st.error("❌ Не вдалося знайти суми виплат. Перевірте формат таблиці.")
