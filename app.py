import streamlit as st
import pandas as pd
import random  # برای شبیه‌سازی کد تأیید
import smtplib  # برای ارسال ایمیل
from email.mime.text import MIMEText
#from sentence_transformers import SentenceTransformer, util
import google.generativeai as genai

# تنظیم API key برای Gemini
genai.configure(api_key="AIzaSyA2atuzXvtOJCssi0qN0iEVmrq0gHSj_f8")  # اینجا کلید API Gemini رو بذار
model = genai.GenerativeModel('gemini-1.5-flash')

# مدل برای embeddings (برای matching)
#embedding_model = SentenceTransformer('all-MiniLM-L6-v2')

# ذخیره داده‌ها موقت (session state) - بعداً دیتابیس واقعی اضافه کن
if 'users' not in st.session_state:
    st.session_state.users = {}  # {'email': {'role': 'شرکت' یا 'جوینده', 'verified': True, 'data': {}}}
if 'requirements' not in st.session_state:
    st.session_state.requirements = []  # لیست نیازمندی‌های شرکت‌ها
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []
if 'current_user' not in st.session_state:
    st.session_state.current_user = None
if 'verification_code' not in st.session_state:
    st.session_state.verification_code = None

# تابع ارسال ایمیل کد تأیید
def send_verification_email(email, code):
    sender = "zarbot2169@gmail.com"  # ایمیل خودت رو بذار
    password = "lbcg vegx ddjy awyx"  # app password از Gmail
    msg = MIMEText(f"کد تأیید شما: {code}")
    msg['Subject'] = 'کد تأیید لاگین'
    msg['From'] = sender
    msg['To'] = email
    try:
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(sender, password)
        server.sendmail(sender, email, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        st.error(f"خطا در ارسال ایمیل: {e}")
        return False

# تابع تحلیل رزومه با Gemini
def analyze_resume(file_content):
    prompt = f"مهارت‌های فنی و شخصیتی را از این رزومه استخراج کن: {file_content}"
    response = model.generate_content(prompt)
    return response.text  # خروجی مثل "مهارت‌ها: Python, مسئولیت‌پذیری بالا"

# اینترفیس اصلی
st.title("ایجنت استخدام هوشمند")

# بخش لاگین
if st.session_state.current_user is None:
    email = st.text_input("ایمیل خود را وارد کنید:")
    if st.button("ارسال کد تأیید"):
        code = random.randint(100000, 999999)
        st.session_state.verification_code = code
        if send_verification_email(email, code):
            st.success("کد تأیید ارسال شد!")
    
    verification_input = st.text_input("کد تأیید را وارد کنید:")
    if st.button("تأیید"):
        if verification_input and int(verification_input) == st.session_state.verification_code:
            role = st.radio("نقش شما:", ("شرکت", "جوینده کار"))
            st.session_state.current_user = email
            st.session_state.users[email] = {'role': role, 'verified': True, 'data': {}}
            st.success("لاگین موفق!")
        else:
            st.error("کد اشتباه است.")

else:
    user_role = st.session_state.users[st.session_state.current_user]['role']
    st.write(f"خوش آمدید! نقش: {user_role}")
    
    # نمایش تاریخچه چت
    if st.button("نمایش تاریخچه"):
        for msg in st.session_state.chat_history:
            st.write(msg)
    
    # چت اصلی
    user_input = st.text_input("پیام خود را وارد کنید:")
    uploaded_file = st.file_uploader("آپلود فایل (اکسل نیازمندی یا رزومه):", type=['xlsx', 'pdf', 'txt'])
    
    if user_input:
        st.session_state.chat_history.append(f"کاربر: {user_input}")
        
        # تشخیص意图 با Gemini (برای مدیریت خارج از حیطه)
        intent_prompt = f"این پیام را تحلیل کن: '{user_input}'.意图: وارد کردن نیازمندی، جستجوی شغل، یا خارج از حیطه؟"
        intent_response = model.generate_content(intent_prompt).text
        
        if "خارج از حیطه" in intent_response:
            response = "متأسفم، این موضوع خارج از حیطه من است. لطفاً در مورد استخدام صحبت کنید."
        elif user_role == "شرکت" and ("نیازمندی" in user_input or "استخدام" in user_input):
            # دریافت نیازمندی - اینجا ساده کردم، بعداً سؤال به سؤال کن
            questions = ["نام شرکت؟", "نیاز به کارآموز یا تمام‌وقت؟", "مهارت‌های فنی مورد نیاز؟", "تست شخصیتی: مسئولیت‌پذیری بالا؟", "حقوق پایه؟", "چیزی اضافی؟"]
            req = {}
            for q in questions:
                st.write(q)
                ans = st.text_input(q, key=q)  # ورودی جدا برای هر سؤال
                req[q] = ans
            
            if uploaded_file:
                if uploaded_file.type == 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet':
                    df = pd.read_excel(uploaded_file)
                    req['excel_data'] = df.to_dict()
            
            st.session_state.requirements.append(req)
            response = "نیازمندی ذخیره شد!"
        
        elif user_role == "جوینده کار" and ("شغل" in user_input or "جستجو" in user_input):
            # تست کاربر
            tests = ["در مقیاس ۱-۱۰، چقدر مسئولیت‌پذیر هستی؟", "مهارت پایتون داری؟"]
            user_data = {}
            for t in tests:
                st.write(t)
                ans = st.text_input(t, key=t)
                user_data[t] = ans
            
            if uploaded_file:
                if uploaded_file.type == 'text/plain':
                    file_content = uploaded_file.read().decode('utf-8')
                elif uploaded_file.type == 'application/pdf':
                    st.error("برای PDF، کتابخونه pdfminer اضافه کن - فعلاً رد کن.")
                    file_content = ""
                else:
                    file_content = ""
                if file_content:
                    user_data['resume'] = analyze_resume(file_content)
            
            # matching با embeddings
            #user_text = ' '.join(str(v) for v in user_data.values())
            #user_emb = embedding_model.encode(user_text)
            #matches = []
            #for req in st.session_state.requirements:
                #req_text = ' '.join(str(v) for v in req.values())
                #req_emb = embedding_model.encode(req_text)
                #similarity = util.cos_sim(user_emb, req_emb)[0][0]
                #if similarity > 0.5:  # آستانه تشابه
                    #matches.append(req)
            
            #response = f"مچ‌های یافت‌شده: {len(matches)}" if matches else "هیچ مچی یافت نشد."
    

    response = f"در حال حاضر {len(st.session_state.requirements)} نیازمندی شغلی ذخیره شده است. به زودی matching هوشمند فعال می‌شود!"
        
        else:
            response = "لطفاً جزئیات بیشتری بدهید یا نقش خود را چک کنید."
        
        st.session_state.chat_history.append(f"AI: {response}")
        st.write(response)

    if st.button("خروج"):
        st.session_state.current_user = None
