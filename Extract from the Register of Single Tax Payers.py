import streamlit as st
import pdfplumber
import pandas as pd
import io
import re
import streamlit.components.v1 as components

st.set_page_config(page_title="Калькулятор ДПС", layout="wide")
st.title("📄 Розрахунок доходу з витягу ДПС")

uploaded_file = st.file_uploader("Завантажте PDF-витяг ДПС", type="pdf")

def clean_and_get_vyp(text):
    """
    Очищує текст клітинки та витягує суму 'Виплачено'.
    У ДПС в одній клітинці може бути: 1934,00 \n 1934,00
    Беремо останнє число (це виплачено).
    """
    if not text: return None
    amounts = re.findall(r"\d{1,3}(?:[\s\.]?\d{3})*[.,]\d{2}", text)
    if not amounts:
        return None
    
    val = amounts[-1].replace(" ", "").replace(".", "").replace(",", ".")
    return float(val)

if uploaded_file:
    raw_data = []
    
    with pdfplumber.open(io.BytesIO(uploaded_file.read())) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()
            for table in tables:
                for row in table:
                    if len(row) >= 7:
                        year_match = re.search(r"20\d{2}", str(row[3]))
                        if year_match:
                            year = year_match.group(0)
                            income_cell = str(row[5]) if row[5] else str(row[6])
                            
                            vyp_sum = clean_and_get_vyp(income_cell)
                            
                            if vyp_sum is not None and vyp_sum > 0:
                                raw_data.append({
                                    "Рік": year,
                                    "Сума (виплачено)": vyp_sum
                                })

    if not raw_data:
        st.error("❌ Не вдалося знайти табличні дані з доходами. Перевірте файл.")
        st.stop()

    df = pd.DataFrame(raw_data)
    
    summary = df.groupby("Рік")["Сума (виплачено)"].sum().reset_index()
    summary["Після -7%"] = (summary["Сума (виплачено)"] * 0.93).round(2)
    
    st.success("✅ Дані оброблено")
    st.subheader("📊 Підсумок по роках")
    st.table(summary.style.format({"Сума (виплачено)": "{:.2f}", "Після -7%": "{:.2f}"}))

    total_all = summary["Сума (виплачено)"].sum()
    total_minus_7 = summary["Після -7%"].sum()

    col1, col2 = st.columns(2)
    col1.metric("Загальна виплачена сума", f"{total_all:,.2f} грн")
    col2.metric("Чистий дохід (-7%)", f"{total_minus_7:,.2f} грн")

    years = sorted(df["Рік"].unique())
    period = f"{years[0]}-{years[-1]}" if len(years) > 1 else years[0]
    comment_text = f"Надано Витяг ДРФО за період {period}; загальна сума виплаченого доходу {total_all:.2f} грн; з урахуванням 7% {total_minus_7:.2f} грн"

    st.markdown("📎 **Коментар для фіксації:**")
    components.html(f"""
        <div style="font-family: sans-serif;">
            <div id="copyField" style="background: #1e1e1e; color: white; padding: 12px; border-radius: 8px; margin-bottom: 10px; font-size: 14px; border: 1px solid #333;">
                {comment_text}
            </div>
            <button onclick="copyToClipboard()" style="background: #4CAF50; color: white; border: none; padding: 8px 16px; border-radius: 5px; cursor: pointer;">
                📋 Скопіювати
            </button>
            <script>
                function copyToClipboard() {{
                    const text = document.getElementById('copyField').innerText;
                    navigator.clipboard.writeText(text).then(() => {{
                        alert('Скопійовано у буфер обміну!');
                    }});
                }}
            </script>
        </div>
    """, height=150)
