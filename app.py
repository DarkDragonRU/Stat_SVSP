import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os

# Настройка страницы (широкий режим)
st.set_page_config(page_title="Дашборд СВСП", layout="wide")

# --- Стили для заголовков ---
st.markdown("""
<style>
    .header-blue {
        background-color: #5B9BD5; color: white; padding: 10px;
        text-align: center; font-weight: bold; border-radius: 5px;
        margin-bottom: 15px; font-size: 16px;
    }
    .header-orange {
        background-color: #ED7D31; color: white; padding: 10px;
        text-align: center; font-weight: bold; border-radius: 5px;
        margin-bottom: 15px; font-size: 16px;
    }
    .header-purple {
        background-color: #7030A0; color: white; padding: 10px;
        text-align: center; font-weight: bold; border-radius: 5px;
        margin-bottom: 15px; font-size: 16px;
    }
</style>
""", unsafe_allow_html=True)

# --- Пути к файлам ---
# Используем текущую рабочую директорию, так как .bat-файл делает cd в папку проекта
BASE_DIR = os.getcwd()
USERS_PATH = os.path.join(BASE_DIR, "users.xlsx")
STATIONS_PATH = os.path.join(BASE_DIR, "stations.xlsx")
BOTS_PATH = os.path.join(BASE_DIR, "bots.xlsx")
APPS_PATH = os.path.join(BASE_DIR, "applications.xlsx")
CONTRACTS_PATH = os.path.join(BASE_DIR, "contracts.xlsx")

# --- Функции загрузки ---
@st.cache_data(ttl=60)
def load_excel(path, filename):
    if not os.path.exists(path):
        st.error(f"Файл не существует по пути: {path}")
        return None
    try:
        # Явно указываем движок openpyxl
        return pd.read_excel(path, engine="openpyxl")
    except Exception as e:
        st.error(f"Ошибка чтения файла {filename}: {repr(e)}")
        return None

# --- Загрузка данных ---
df_users = load_excel(USERS_PATH, "users.xlsx")
df_stations = load_excel(STATIONS_PATH, "stations.xlsx")
df_bots = load_excel(BOTS_PATH, "bots.xlsx")
df_apps = load_excel(APPS_PATH, "applications.xlsx")
df_contracts = load_excel(CONTRACTS_PATH, "contracts.xlsx")

# ==========================================
# ВЕРХНИЙ БЛОК: ФИЛЬТР ПО ГОДАМ
# ==========================================
all_years = set()
if df_apps is not None: all_years.update(df_apps['Год'].dropna().astype(int).tolist())
if df_users is not None: all_years.update(df_users['Year'].dropna().astype(int).tolist())
if df_stations is not None: all_years.update(df_stations['Year'].dropna().astype(int).tolist())
if df_contracts is not None: all_years.update(df_contracts['Год'].dropna().astype(int).tolist())

years_list = sorted(list(all_years))

selected_years = st.multiselect(
    "📅 Выберите годы для отображения:", 
    options=years_list, 
    default=years_list
)

st.markdown("---")

# ==========================================
# БЛОК 1: ЗАЯВКИ И АКТИВНОСТЬ (Верхний ряд)
# ==========================================
col_left, col_right = st.columns([1, 1.5])

with col_left:
    st.markdown('<div class="header-blue">Количество заявок и каналы взаимодействия</div>', unsafe_allow_html=True)
    
    if df_apps is not None and not df_apps.empty:
        apps_filtered = df_apps[df_apps['Год'].isin(selected_years)]
        total_paper = apps_filtered['Бумажные'].sum()
        total_site = apps_filtered['Сайт'].sum()
        total_bot = apps_filtered['Бот'].sum()
        total_all = total_paper + total_site + total_bot
        
        if total_all > 0:
            c1, c2, c3 = st.columns(3)
            def draw_donut(value, label, color):
                fig = go.Figure(data=[go.Pie(
                    values=[value, total_all - value], labels=[label, "Остальное"],
                    hole=.6, marker_colors=[color, '#E0E0E0'],
                    textinfo='none', hoverinfo='label+percent'
                )])
                fig.update_layout(
                    showlegend=False, margin=dict(t=0, b=0, l=0, r=0), height=150,
                    annotations=[dict(text=f"{int(value)}<br>({value/total_all*100:.1f}%)", x=0.5, y=0.5, font_size=14, showarrow=False)]
                )
                return fig

            with c1:
                st.markdown("<p style='text-align: center; color: #5B9BD5; font-weight: bold;'>Бумага</p>", unsafe_allow_html=True)
                st.plotly_chart(draw_donut(total_paper, "Бумага", "#5B9BD5"), use_container_width=True)
            with c2:
                st.markdown("<p style='text-align: center; color: #5B9BD5; font-weight: bold;'>Сайт</p>", unsafe_allow_html=True)
                st.plotly_chart(draw_donut(total_site, "Сайт", "#5B9BD5"), use_container_width=True)
            with c3:
                st.markdown("<p style='text-align: center; color: #5B9BD5; font-weight: bold;'>Бот</p>", unsafe_allow_html=True)
                st.plotly_chart(draw_donut(total_bot, "Бот", "#5B9BD5"), use_container_width=True)
        else:
            st.info("Нет данных по заявкам за выбранные годы.")
    else:
        st.warning("Файл applications.xlsx не найден или пуст.")

with col_right:
    st.markdown('<div class="header-blue">Статистика активности пользователей СВСП</div>', unsafe_allow_html=True)
    
    if df_users is not None and not df_users.empty:
        users_filtered = df_users[df_users['Year'].isin(selected_years)]
        agg_users = users_filtered.groupby('Year').agg(
            active_users=('UserName', 'nunique'),
            total_hours=('total_work_time_hours', 'sum'),
            total_connections=('total_connections', 'sum')
        ).reset_index()

        c1, c2, c3 = st.columns(3)
        
        with c1:
            st.markdown("<p style='text-align: center; font-size: 14px;'>Активных пользователей</p>", unsafe_allow_html=True)
            fig_users = px.line(agg_users, x='Year', y='active_users', markers=True, text='active_users')
            fig_users.update_traces(textposition="top center", line_color='#5B9BD5', marker_color='#5B9BD5')
            max_y = agg_users['active_users'].max() if not agg_users.empty else 10
            fig_users.update_yaxes(range=[0, max_y * 1.2])
            fig_users.update_layout(height=260, margin=dict(t=30, b=0, l=0, r=0), xaxis_title=None, yaxis_title=None)
            st.plotly_chart(fig_users, use_container_width=True)
            
        with c2:
            st.markdown("<p style='text-align: center; font-size: 14px;'>Часы работы всех пользователей</p>", unsafe_allow_html=True)
            fig_hours = px.line(agg_users, x='Year', y='total_hours', markers=True, text='total_hours')
            fig_hours.update_traces(textposition="top center", texttemplate='%{text:.0f}', line_color='#5B9BD5', marker_color='#5B9BD5')
            max_y_hours = agg_users['total_hours'].max() if not agg_users.empty else 100
            fig_hours.update_yaxes(range=[0, max_y_hours * 1.2])
            fig_hours.update_layout(height=260, margin=dict(t=30, b=0, l=0, r=0), xaxis_title=None, yaxis_title=None)
            st.plotly_chart(fig_hours, use_container_width=True)

        with c3:
            st.markdown("<p style='text-align: center; font-size: 14px;'>Количество подключений</p>", unsafe_allow_html=True)
            fig_conn = px.line(agg_users, x='Year', y='total_connections', markers=True, text='total_connections')
            fig_conn.update_traces(textposition="top center", line_color='#5B9BD5', marker_color='#5B9BD5')
            max_y_conn = agg_users['total_connections'].max() if not agg_users.empty else 100
            fig_conn.update_yaxes(range=[0, max_y_conn * 1.2])
            fig_conn.update_layout(height=260, margin=dict(t=30, b=0, l=0, r=0), xaxis_title=None, yaxis_title=None)
            st.plotly_chart(fig_conn, use_container_width=True)
    else:
        st.warning("Файл users.xlsx не найден или пуст.")

st.markdown("---")

# ==========================================
# БЛОК 2: ДОГОВОРЫ, СТАНЦИИ, БОТЫ (Нижний ряд)
# ==========================================
col_bottom_left, col_bottom_mid, col_bottom_right = st.columns([1, 1, 1.2])

# --- Левая часть: Договоры и Оборудование ---
with col_bottom_left:
    if df_contracts is not None and not df_contracts.empty:
        contracts_filtered = df_contracts[df_contracts['Год'].isin(selected_years)]
        
        st.markdown('<div class="header-blue">Количество заключенных договоров</div>', unsafe_allow_html=True)
        fig_contracts = px.bar(contracts_filtered, x='Год', y='Договора', text='Договора')
        fig_contracts.update_traces(textposition='outside', marker_color='#5B9BD5', cliponaxis=False)
        fig_contracts.update_layout(height=250, margin=dict(t=30, b=0, l=0, r=0), xaxis_title=None, yaxis_title=None)
        max_contracts = contracts_filtered['Договора'].max() if not contracts_filtered.empty else 10
        fig_contracts.update_yaxes(range=[0, max_contracts * 1.25], showticklabels=False, showgrid=False)
        st.plotly_chart(fig_contracts, use_container_width=True)

        st.markdown('<div class="header-blue">Количество оборудования по договорам</div>', unsafe_allow_html=True)
        fig_equipment = px.bar(contracts_filtered, x='Год', y='Оборудование', text='Оборудование')
        fig_equipment.update_traces(textposition='outside', marker_color='#5B9BD5', cliponaxis=False)
        fig_equipment.update_layout(height=250, margin=dict(t=30, b=0, l=0, r=0), xaxis_title=None, yaxis_title=None)
        max_equipment = contracts_filtered['Оборудование'].max() if not contracts_filtered.empty else 10
        fig_equipment.update_yaxes(range=[0, max_equipment * 1.25], showticklabels=False, showgrid=False)
        st.plotly_chart(fig_equipment, use_container_width=True)
    else:
        st.markdown('<div class="header-blue">Количество заключенных договоров</div>', unsafe_allow_html=True)
        st.info("Ожидается файл contracts.xlsx")
        st.markdown('<div class="header-blue">Количество оборудования по договорам</div>', unsafe_allow_html=True)

# --- Центральная часть: Топ-3 станций ---
with col_bottom_mid:
    if df_stations is not None and not df_stations.empty:
        stations_filtered = df_stations[df_stations['Year'].isin(selected_years)]
        
        st.markdown('<div class="header-blue">Топ-3 станций по часам работы</div>', unsafe_allow_html=True)
        top_hours = stations_filtered.groupby('Station')['total_work_time_hours'].sum().nlargest(3).reset_index()
        if not top_hours.empty:
            fig_top_hours = px.bar(top_hours, x='Station', y='total_work_time_hours', text='total_work_time_hours')
            fig_top_hours.update_traces(texttemplate='%{text:.0f}', textposition='outside', marker_color='#5B9BD5', cliponaxis=False)
            fig_top_hours.update_layout(height=250, margin=dict(t=30, b=0, l=0, r=0), xaxis_title=None, yaxis_title=None)
            max_th = top_hours['total_work_time_hours'].max()
            fig_top_hours.update_yaxes(range=[0, max_th * 1.25], showticklabels=False, showgrid=False)
            st.plotly_chart(fig_top_hours, use_container_width=True)
        
        st.markdown('<div class="header-blue">Топ-3 станций по подключениям</div>', unsafe_allow_html=True)
        top_conn = stations_filtered.groupby('Station')['total_connections'].sum().nlargest(3).reset_index()
        if not top_conn.empty:
            fig_top_conn = px.bar(top_conn, x='Station', y='total_connections', text='total_connections')
            fig_top_conn.update_traces(texttemplate='%{text:.0f}', textposition='outside', marker_color='#5B9BD5', cliponaxis=False)
            fig_top_conn.update_layout(height=250, margin=dict(t=30, b=0, l=0, r=0), xaxis_title=None, yaxis_title=None)
            max_tc = top_conn['total_connections'].max()
            fig_top_conn.update_yaxes(range=[0, max_tc * 1.25], showticklabels=False, showgrid=False)
            st.plotly_chart(fig_top_conn, use_container_width=True)
    else:
        st.warning("Файл stations.xlsx не найден.")

# --- Правая часть: Telegram-боты ---
with col_bottom_right:
    if df_bots is not None and not df_bots.empty:
        df_bots.columns = df_bots.columns.str.strip().str.lower()
        name_col = next((col for col in ['бот', 'наименование бота', 'название', 'имя бота'] if col in df_bots.columns), None)
        
        if name_col:
            for _, row in df_bots.iterrows():
                bot_name = str(row[name_col])
                is_fire_bot = "пожар" in bot_name.lower()
                header_class = "header-orange" if is_fire_bot else "header-purple"
                
                st.markdown(f'<div class="{header_class}">{bot_name}</div>', unsafe_allow_html=True)
                
                metrics_names = []
                metrics_values = []
                
                if is_fire_bot:
                    metrics_names = ['Пользователи', 'Действия', 'Уведомления']
                    metrics_values = [row.get('пользователи', 0), row.get('действия', 0), row.get('уведомления', 0)]
                else:
                    metrics_names = ['Пользователи', 'Действия']
                    metrics_values = [row.get('пользователи', 0), row.get('действия', 0)]
                
                colors = ['#ED7D31'] * len(metrics_values) if is_fire_bot else ['#7030A0'] * len(metrics_values)
                
                fig_bot = go.Figure(go.Bar(
                    x=metrics_values, y=metrics_names, orientation='h', text=metrics_values,
                    textposition='outside', cliponaxis=False, marker_color=colors
                ))
                fig_bot.update_layout(
                    height=200 if is_fire_bot else 150, 
                    margin=dict(t=10, b=10, l=0, r=40),
                    xaxis=dict(showgrid=False, showticklabels=False),
                    yaxis=dict(showgrid=False)
                )
                max_val = max(metrics_values) if metrics_values else 1
                fig_bot.update_xaxes(range=[0, max_val * 1.3])
                st.plotly_chart(fig_bot, use_container_width=True)
    else:
        st.warning("Файл bots.xlsx не найден.")