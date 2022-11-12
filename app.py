import streamlit as st
from main_logic import get_pred


st.set_page_config(page_title='Определить тип речи онлайн', page_icon='images/favicon.png',
                   layout='wide', initial_sidebar_state='auto')
st.title('Определение типа речи')
text = st.text_area(label="Введите текст...", height=250)
if st.button("Отправить"):
    result = text.title()
    try:
        label = get_pred(result)
        st.success(f"Тип речи данного текста - {label.upper()}")
        st.image("images/pie.jpg")
    except IndexError:
        st.success('Ой, мы пока не можем определить тип речи данного текста!')
