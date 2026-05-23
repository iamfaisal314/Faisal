import streamlit as st
import fitz  # PyMuPDF
import re
import os
import requests
import tempfile

# إعدادات الصفحة في المتصفح
st.set_page_config(page_title="أداة تعديل ملفات الأدوية 314", page_icon="💊", layout="centered")

# 🔒 الرقم السري المعتمد لحماية الإعدادات
SECRET_PASSWORD = "1234"

# استخدام الـ Session State لحفظ قائمة الأدوية أثناء تشغيل الموقع
if "dividers" Action not in st.session_state:
    st.session_state.dividers = {
        "Acyclovir": 5, "Amikacin": 5, "Vancomycin": 5, "Piperacillin": 50,
        "Ampicillin": 20, "Gentamicin": 2, "Cefotaxime": 40, "Ceftriaxone": 40,
        "Cefepime": 40, "Cefuroxime": 30, "Ceftazidime": 40, "Azithromycin": 2,
        "Furosemide": 2, "Cloxacillin": 25, "omeprazole": 0.8, "Omeprazole": 0.8,
        "Cefazolin": 20, "Caffeine": 10, "Amphotericin-B": 0.1,
        "Amphotericin - B Liposomal": 2, "Meropenem": 20, "Methylprednisolone": 10,
        "Clindamycin": 18, "Levetiracetam": 10, "Sulfamethoxazole": 0.64,
        "levocarnitine": 8, "Hydrocortisone ": 1, "Hydralazine": 1,
        "Colistin": 20000, "Dexamethasone": 1,
    }

frequency_repeat = {
    "q12h": 2, "every 12 hour": 2, "q8h": 3, "every 8 hour": 3,
    "q6h": 4, "every 6 hour": 4, "q4h": 6, "every 4 hour": 6,
    "twice": 2, "twice daily": 2, "bid": 2,
}

def extract_mrn(text):
    match = re.search(r"\b\d{6,}\b", text)
    return match.group(0) if match else None

def process_pdf(input_bytes):
    """معالجة الـ PDF مباشرة من الذاكرة (Bytes) لتناسب المتصفح"""
    doc = fitz.open(stream=input_bytes, filetype="pdf")
    new_doc = fitz.open()

    patient_drugs = {}
    for page_num in range(len(doc)):
        text = doc[page_num].get_text("text")
        mrn = extract_mrn(text)
        if not mrn:
            continue
        for drug in st.session_state.dividers.keys():
            if drug.lower() in text.lower():
                if mrn not in patient_drugs:
                    patient_drugs[mrn] = {}
                patient_drugs[mrn][drug] = patient_drugs[mrn].get(drug, 0) + 1

    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text("text")
        mrn = extract_mrn(text)
        if not mrn:
            continue

        matched_drug = None
        divisor = None
        for drug, div in st.session_state.dividers.items():
            if drug.lower() in text.lower():
                matched_drug = drug
                divisor = div
                break

        if not matched_drug:
            continue

        repeat_times = 1
        for freq, times in frequency_repeat.items():
            if freq in text.lower():
                repeat_times = times
                break

        for _ in range(repeat_times):
            new_page_count = new_doc.page_count
            new_doc.insert_pdf(doc, from_page=page_num, to_page=page_num)
            new_page = new_doc[new_page_count]

            words = new_page.get_text("words")
            for idx, w in enumerate(words):
                if w[4].upper() == "MG":
                    prev_word = words[idx - 1][4]
                    if prev_word.replace(".", "", 1).isdigit():
                        dose = float(prev_word)
                        result = dose / divisor
                        x0, y0, x1, y1, *_ = words[idx - 1]

                        new_page.insert_text(
                            (x0, y1 + 25),
                            f"{dose} mg ÷ {divisor} = {round(result, 2)} ml",
                            fontsize=11,
                            color=(0, 0, 1),
                        )

                        if patient_drugs.get(mrn, {}).get(matched_drug, 0) > 1:
                            new_page.insert_text(
                                (x0, y1 + 45),
                                "DUPLICATE",
                                fontsize=12,
                                color=(1, 0, 0),
                            )
                        break

    # حفظ الملف في الذاكرة وإرجاعه كـ bytes ليقوم المتصفح بتحميله
    out_bytes = new_doc.write()
    new_doc.close()
    doc.close()
    return out_bytes

# --- واجهة المستخدم على المتصفح ---
st.title("💊 أداة تعديل ملفات الأدوية الذكية 314")
st.write("قم بمعالجة ملفات الأدوية الـ PDF مباشرة وحساب الجرعات عبر المتصفح.")

# التبويبات لتنظيم الموقع
tab1, tab2 = st.tabs(["📄 معالجة الملفات", "🔒 لوحة تحكم الإدارة"])

with tab1:
    st.header("رفع ومعالجة الـ PDF")
    
    # خيار رفع الملف من الجهاز
    uploaded_file = st.file_uploader("اختر ملف PDF من جهازك", type=["pdf"])
    
    # خيار جلب الملف من رابط
    url_input = st.text_input("أو الصق رابط ملف PDF هنا:")
    
    file_bytes = None
    
    if uploaded_file is not None:
        file_bytes = uploaded_file.read()
    elif url_input.strip():
        if st.button("🌐 جلب الملف من الرابط"):
            try:
                res = requests.get(url_input.strip())
                res.raise_for_status()
                file_bytes = res.content
                st.success("تم جلب الملف من الرابط بنجاح!")
            except Exception as e:
                st.error(f"فشل جلب الملف من الرابط: {e}")

    # زر المعالجة والتحميل
    if file_bytes:
        if st.button("⚙️ ابدأ معالجة الملف"):
            with st.spinner("جاري معالجة وحساب الجرعات..."):
                try:
                    output_pdf_bytes = process_pdf(file_bytes)
                    st.success("✅ تم معالجة الملف بنجاح!")
                    
                    # زر لتحميل الملف الناتج مباشرة من المتصفح
                    st.download_button(
                        label="📥 تحميل الملف المعدّل (PDF)",
                        data=output_pdf_bytes,
                        file_name="processed_output.pdf",
                        mime="application/pdf"
                    )
                except Exception as e:
                    st.error(f"حدث خطأ أثناء المعالجة: {e}")

with tab2:
    st.header("إدارة الأدوية المحمية")
    
    # طلب الرقم السري أولاً لإظهار الإعدادات
    password = st.text_input("أدخل الرقم السري للوصول للوحة التحكم:", type="password")
    
    if password == SECRET_PASSWORD:
        st.success("تم التحقق من الهوية بنجاح. يمكنك التعديل الآن:")
        
        # خيار الإضافة
        st.subheader("➕ إضافة دواء جديد")
        new_drug = st.text_input("اسم الدواء الجديد:")
        new_div = st.number_input("المقسوم عليه (Divisor):", min_value=0.01, step=1.0)
        
        if st.button("حفظ الدواء الجديد"):
            if new_drug.strip():
                if new_drug.strip() in st.session_state.dividers:
                    st.warning("هذا الدواء موجود بالفعل!")
                else:
                    st.session_state.dividers[new_drug.strip()] = new_div
                    st.success(f"تمت إضافة {new_drug} بقيمة {new_div}")
            else:
                st.error("الرجاء كتابة اسم الدواء.")
                
        st.markdown("---")
        
        # خيار التعديل
        st.subheader("✏️ تعديل تركيز دواء حالي")
        drug_list = sorted(list(st.session_state.dividers.keys()))
        selected_drug = st.selectbox("اختر الدواء المراد تعديله:", drug_list)
        
        current_div = st.session_state.dividers[selected_drug]
        edit_div = st.number_input(f"القيمة الجديدة للمقسّم (القيمة الحالية: {current_div}):", min_value=0.01, value=float(current_div), step=1.0, key="edit_box")
        
        if st.button("تحديث القيمة"):
            st.session_state.dividers[selected_drug] = edit_div
            st.success(f"تم تحديث {selected_drug} إلى {edit_div}")
            
    elif password != "":
        st.error("الرقم السري غير صحيح!")