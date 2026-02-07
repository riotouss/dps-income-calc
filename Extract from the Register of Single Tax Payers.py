import streamlit as st
import pdfplumber
import pandas as pd
import io

st.set_page_config(page_title="Калькулятор ДПС", layout="wide")
st.title("📄 Розрахунок доходу з витягу ДПС (ДРФО)")

st.markdown("""

uploaded_file = st.file_uploader("Завантажте PDF-витяг ДПС", type="pdf")

ALLOWED_CODES = ["185", "128", "111", "127"]

def to_float(val):
    if not val:
        return 0.0
    try:
        return float(val.replace(" ", "").replace(",", "."))
    except ValueError:
        return 0.0

if uploaded_file:
    raw_data = []

    with pdfplumber.open(io.BytesIO(uploaded_file.read())) as pdf:
        for page in pdf.pages:
            table = page.extract_table()
            if not table:
                continue

            headers = table[0]

            try:
                idx_paid = headers.index("Виплаченого")
                idx_code = headers.index("Код та назва ознаки доходу")
                idx_year = headers.index("Рік")
                idx_month = headers.index("Номер кварталу - місяць")
            except ValueError:
                continue

            for row in table[1:]:
                if not row or len(row) <= idx_paid:
                    continue

                code_raw = row[idx_code] or ""
                code = code_raw[:3]

                if code not in ALLOWED_CODES:
                    continue

                paid = to_float(row[idx_paid])
                if paid <= 0:
                    continue

                raw_data.append({
                    "Рік": row[idx_year],
                    "Місяць": row[idx_month],
                    "Код доходу": code,
                    "Сума (виплачено)": paid
                })

    if not raw_data:
        st.error("❌ Не вдалося розпізнати виплачені доходи. Перевірте формат PDF.")
        st.stop()

    df = pd.DataFrame(raw_data)

    code_names = {
        "185": "Виплати військовослужбовця",
        "128": "Соціальні виплати",
        "111": "Виграші та призи",
        "127": "Інші доходи"
    }

    df["Тип доходу"] = df["Код доходу"].map(code_names)

    st.success("✅ Дані успішно оброблено")

    st.subheader("📋 Деталізація")
    st.dataframe(df, use_container_width=True)

    summary = (
        df.groupby(["Рік", "Тип доходу"])["Сума (виплачено)"]
        .sum()
        .reset_index()
    )

    summary["Чистий дохід (-7%)"] = (summary["Сума (виплачено)"] * 0.93).round(2)

    st.subheader("📊 Підсумок по роках і типах доходів")
    st.table(summary)

    total_all = summary["Сума (виплачено)"].sum()
    total_minus_7 = summary["Чистий дохід (-7%)"].sum()

    col1, col2 = st.columns(2)
    col1.metric("Загальна сума виплат", f"{total_all:,.2f} грн")
    col2.metric("Після вирахування 7%", f"{total_minus_7:,.2f} грн")

    years = sorted(df["Рік"].astype(str).unique())
    period = f"{years[0]}–{years[-1]}" if len(years) > 1 else years[0]

    comment = (
        f"Витяг ДРФО за період {period}. "
        f"Загальна сума виплачених доходів — {total_all:.2f} грн, "
        f"з урахуванням 7% — {total_minus_7:.2f} грн."
    )

    st.subheader("📎 Коментар для фіксації")
    st.text_area("", value=comment, height=120)
