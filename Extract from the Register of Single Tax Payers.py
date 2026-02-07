import streamlit as st
import pdfplumber
import pandas as pd
import io
import re
import streamlit.components.v1 as components

st.set_page_config(page_title="Універсальний Калькулятор ДПС", layout="wide")
st.title("📄 Розрахунок доходу (усі типи Витягів)")

uploaded_file = st.file_uploader("Завантажте PDF-витяг", type="pdf")

def get_vyp_from_row(row_cells):
    """
    Знаходить усі грошові суми. 
    За логікою ДПС: спочатку Нараховано, потім Виплачено.
    Ми беремо Виплачено (зазвичай це 2-ге число у блоці доходів).
    """
    row_text = " ".join([str(c) for c in row_cells if c])
    amounts = re.findall(r"\d{1,3}(?:[\s\.]?\d{3})*[.,]\d{2}", row_text)
    
    clean_amounts = []
    for a in amounts:
        val = float(a.replace(" ", "").replace(".", "").replace(",", "."))
        if 1.00 < val < 900000000 and val not in [111.0, 127.0, 128.0, 185.0]:
            clean_amounts.append(val)
    
    if len(clean_amounts) >= 2:
        return clean_amounts[1] 
    elif len(clean_amounts) == 1:
        return clean_amounts[0]
    return 0.0

if uploaded_file:
    data = []
    with pdfplumber.open(io.BytesIO(uploaded_file.read())) as pdf:
        for page in pdf.pages:
            table = page.extract_table()
            if table:
                for row in table:
                    row_str = " ".join([str(c) for c in row if c])
                    year_match = re.search(r"\b(202\d)\b", row_str)
                    if year_match:
                        year = year_match.group(1)
                        vyp = get_vyp_from_row(row)
                        if vyp > 0:
                            data.append({"Рік": year, "Виплачено": vyp})

    if data:
        df = pd.DataFrame(data)
        res = df.groupby("Рік")["Виплачено"].sum().reset_index()
        res["-7%"] = (res["Виплачено"] * 0.93).round(2)
        
        st.table(res.style.format("{:.2f}"))
        
        total = res["Виплачено"].sum()
        total_7 = res["-7%"].sum()
        
        st.metric("Загалом виплачено", f"{total:,.2f} грн")
        st.metric("Сума після -7%", f"{total_7:,.2f} грн")
        
        comment = f"Витяг ДРФО; період {res['Рік'].iloc[0]}-{res['Рік'].iloc[-1]}; сума {total:.2f} грн; з урахуванням 7% {total_7:.2f} грн"
        components.html(f"""
            <div style="background:#1e1e1e; color:white; padding:10px; border-radius:8px; font-family:sans-serif;">
                <div id="c">{comment}</div>
                <button onclick="navigator.clipboard.writeText(document.getElementById('c').innerText); alert('OK')" 
                style="margin-top:10px; background:#4CAF50; color:white; border:none; padding:5px 10px; border-radius:4px; cursor:pointer;">
                Скопіювати</button>
            </div>
        """, height=120)
    else:
        st.error("Дані не знайдено")
