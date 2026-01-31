import streamlit as st
import pdfplumber
import pandas as pd
import io
import re

st.set_page_config(page_title="Калькулятор ДПС", layout="wide")
st.title("📄 Розрахунок доходу з Витягу ДПС")

uploaded_file = st.file_uploader("Завантажте PDF-витяг", type="pdf")

def extract_amounts(text):
    if not text: return []
    clean_text = text.replace("\n", " ")
    found = re.findall(r"(\d{1,3}(?:\s?\d{3})*(?:[.,]\d{2}))", clean_text)
    return [float(f.replace(" ", "").replace(",", ".")) for f in found]

if uploaded_file is not None:
    raw_data = []
    
    with pdfplumber.open(io.BytesIO(uploaded_file.read())) as pdf:
        for page in pdf.pages:
            table = page.extract_table()
            if table:
                for row in table:
                    row = [cell for cell in row if cell]
                    row_str = " ".join(row)
                    
                    year_match = re.search(r"\b(202\d)\b", row_str)
                    
                    if year_match:
                        year = year_match.group(1)
                        amounts = extract_amounts(row_str)
                        
                        if amounts:
                            income = amounts[0]
                            raw_data.append({"Рік": year, "Сума": income})

    if raw_data:
        df = pd.DataFrame(raw_data)
        summary = df.groupby("Рік")["Сума"].sum().reset_index()
        
        summary["Чистий дохід (-7%)"] = (summary["Сума"] * 0.93).round(2)
        summary["Сума"] = summary["Сума"].round(2)

        st.success("✅ Дані знайдено!")
        st.subheader("📊 Підсумок по роках")
        st.table(summary)

        total_all = summary["Сума"].sum()
        total_minus_7 = summary["Чистий дохід (-7%)"].sum()

        col1, col2 = st.columns(2)
        col1.metric("Загальна сума", f"{total_all:,.2f} грн")
        col2.metric("Після вирахування 7%", f"{total_minus_7:,.2f} грн")

        years = sorted(summary["Рік"].unique())
        period = f"{years[0]}-{years[-1]}" if len(years) > 1 else years[0]
        comment = f"Витяг ДРФО за період {period}; загальна сума {total_all:.2f} грн; з урахуванням 7% {total_minus_7:.2f} грн"
        
        st.text_area("📎 Коментар для фіксації:", value=comment)
    else:
        st.error("❌ Не вдалося розпізнати суми. Спробуйте інший формат PDF або перевірте якість файлу.")
