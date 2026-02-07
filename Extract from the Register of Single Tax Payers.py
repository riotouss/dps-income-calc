import streamlit as st
import pdfplumber
import pandas as pd
import io
import re

st.set_page_config(page_title="Калькулятор ДПС", layout="wide")
st.title("📄 Розрахунок доходу з витягу ДПС (ДРФО)")

st.markdown(
    "Рахуються **всі виплачені доходи**:\n"
    "- 185 — виплати військовослужбовця  \n"
    "- 128 — соціальні виплати  \n"
    "- 111 — виграші та призи  \n"
    "- 127 — інші доходи  \n\n"
    "❗ Береться **перша грошова сума в рядку** (це дохід, не податки)"
)

uploaded_file = st.file_uploader("Завантажте PDF-витяг ДПС", type="pdf")

ALLOWED_CODES = ["185", "128", "111", "127"]

CODE_NAMES = {
    "185": "Виплати військовослужбовця",
    "128": "Соціальні виплати",
    "111": "Виграші та призи",
    "127": "Інші доходи"
}

def extract_amounts(text: str):
    """
    Повертає всі грошові суми з рядка у форматі ДПС
    120 557,80 -> 120557.80
    """
    found = re.findall(r"\d{1,3}(?: \d{3})*,\d{2}", text)
    return [float(x.replace(" ", "").replace(",", ".")) for x in found]


def extract_year(text: str):
    match = re.search(r"20\d{2}", text)
    return match.group(0) if match else "—"


if uploaded_file:
    raw_data = []

    with pdfplumber.open(io.BytesIO(uploaded_file.read())) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if not text:
                continue

            lines = text.split("\n")

            for line in lines:
                code = next((c for c in ALLOWED_CODES if c in line), None)
                if not code:
                    continue

                amounts = extract_amounts(line)
                if not amounts:
                    continue

                income = amounts[0]
                if income <= 0:
                    continue

                raw_data.append({
                    "Рік": extract_year(line),
                    "Код доходу": code,
                    "Тип доходу": CODE_NAMES.get(code, code),
                    "Сума (виплачено)": income
                })

    if not raw_data:
        st.error("❌ Не вдалося розпізнати доходи. Це нетиповий PDF або скан.")
        st.stop()

    df = pd.DataFrame(raw_data)

    st.success("✅ Дані успішно зчитані")

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
