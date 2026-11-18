import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
import json

# Настройка страницы (широкий режим)
st.set_page_config(page_title="Дашборд СВСП", layout="wide")

# Стилизация тегов мультиселекта (годы) — цвета как на графиках
st.markdown("""
<style>
    /* Общие настройки для всех тегов */
    .stMultiSelect [data-baseweb="tag"] {
        border-radius: 6px !important;
        color: white !important;
    }
    .stMultiSelect [data-baseweb="tag"] span {
        color: white !important;
    }
    .stMultiSelect [data-baseweb="tag"] svg {
        fill: white !important;
    }

    /* Раскраска по годам (используем псевдокласс :has) */
    /* 2023 — синий */
    .stMultiSelect [data-baseweb="tag"]:has(span[title="2023"]) {
        background-color: #5B9BD5 !important;
    }
    /* 2024 — красный */
    .stMultiSelect [data-baseweb="tag"]:has(span[title="2024"]) {
        background-color: #FF0000 !important;
    }
    /* 2025 — зелёный */
    .stMultiSelect [data-baseweb="tag"]:has(span[title="2025"]) {
        background-color: #70AD47 !important;
    }
    /* 2026 — жёлтый (или любой другой из палитры) */
    .stMultiSelect [data-baseweb="tag"]:has(span[title="2026"]) {
        background-color: #FFC000 !important;
    }
</style>
""", unsafe_allow_html=True)

# --- Пути к файлам ---
BASE_DIR = os.getcwd()
USERS_PATH = os.path.join(BASE_DIR, "users.xlsx")
STATIONS_PATH = os.path.join(BASE_DIR, "stations.xlsx")
BOTS_PATH = os.path.join(BASE_DIR, "bots.xlsx")
APPS_PATH = os.path.join(BASE_DIR, "applications.xlsx")
CONTRACTS_PATH = os.path.join(BASE_DIR, "contracts.xlsx")
MAP_PATH = os.path.join(BASE_DIR, "geo_users_SVSP.html")

# --- Функции загрузки ---
@st.cache_data(ttl=60)
def load_excel(path):
    if not os.path.exists(path):
        return None
    try:
        return pd.read_excel(path, engine="openpyxl")
    except Exception as e:
        st.error(f"Ошибка чтения {os.path.basename(path)}: {e}")
        return None

# --- Загрузка данных ---
df_users = load_excel(USERS_PATH)
df_stations = load_excel(STATIONS_PATH)
df_bots = load_excel(BOTS_PATH)
df_apps = load_excel(APPS_PATH)
df_contracts = load_excel(CONTRACTS_PATH)

# ==========================================
# БОКОВАЯ ПАНЕЛЬ: НАВИГАЦИЯ И ФИЛЬТРЫ
# ==========================================
st.sidebar.title("Навигация")
page = st.sidebar.radio("Выберите раздел:", 
    ["📊 Сводная статистика", "👤 Статистика пользователей", "📡 Статистика станций", "🗺️ Карта пользователей"]
)

st.sidebar.markdown("---")

# Собираем все годы, присутствующие в исходных файлах
all_years = set()
if df_apps is not None and 'Год' in df_apps.columns:
    all_years.update(pd.to_numeric(df_apps['Год'], errors='coerce').dropna().astype(int).tolist())
if df_users is not None and 'Year' in df_users.columns:
    all_years.update(pd.to_numeric(df_users['Year'], errors='coerce').dropna().astype(int).tolist())
if df_stations is not None and 'Year' in df_stations.columns:
    all_years.update(pd.to_numeric(df_stations['Year'], errors='coerce').dropna().astype(int).tolist())
if df_contracts is not None and 'Год' in df_contracts.columns:
    all_years.update(pd.to_numeric(df_contracts['Год'], errors='coerce').dropna().astype(int).tolist())

# Берём только те годы, которые реально есть в данных, и оставляем последние 5.
# Если данных меньше чем на 5 лет — покажем столько, сколько есть.
available_years = sorted(all_years)
last_5_years = available_years[-5:] if available_years else [pd.Timestamp.now().year]

COLOR_PALETTE = ['#5B9BD5', '#FF0000', '#70AD47', '#FFC000', '#7030A0']
YEAR_COLORS = {
    str(year): COLOR_PALETTE[i]
    for i, year in enumerate(last_5_years)
}

def draw_yearly_stacked_chart(
    df,
    full_df,
    name_col,
    value_col,
    xaxis_title
):
    """Горизонтальная накопительная диаграмма с сортировкой по сумме за все годы."""

    if df.empty:
        fig = go.Figure()
        fig.update_layout(
            height=400,
            annotations=[dict(
                text="Нет данных за выбранные годы",
                x=0.5, y=0.5, xref="paper", yref="paper",
                showarrow=False
            )]
        )
        return fig

    # Годы показываются слева направо в хронологическом порядке.
    years = sorted(pd.to_numeric(df['Year'], errors='coerce').dropna().astype(int).unique())
    years_str = [str(year) for year in years]

    # Сортировка по сумме за все годы, имеющиеся в исходном файле.
    totals = (
        full_df.groupby(name_col)[value_col]
        .sum()
        .sort_values(ascending=False)
    )
    order_list = totals.index.tolist()

    # Суммируем значения отдельно для каждого объекта и года.
    data = (
        df.groupby([name_col, 'Year'], as_index=False)[value_col]
        .sum()
    )
    data['Year_str'] = pd.to_numeric(data['Year'], errors='coerce').astype(int).astype(str)

    # Объекты, у которых нет значений в выбранном периоде, в график не попадают.
    visible_names = data[name_col].dropna().unique().tolist()
    order_list = [name for name in order_list if name in visible_names]

    dynamic_height = max(600, min(data[name_col].nunique() * 30, 1500))

    fig = px.bar(
        data,
        x=value_col,
        y=name_col,
        color='Year_str',
        orientation='h',
        barmode='stack',
        height=dynamic_height,
        color_discrete_map=YEAR_COLORS,
        category_orders={
            name_col: order_list,
            'Year_str': years_str
        },
        labels={
            value_col: xaxis_title,
            name_col: '',
            'Year_str': 'Год'
        }
    )

    max_x = data[value_col].max() if not data.empty else 1
    fig.update_layout(
        margin=dict(l=0, r=120, t=30, b=0),   # запас справа под подписи
        legend_title_text='Год',
        yaxis=dict(showgrid=False),
        xaxis=dict(
            title=xaxis_title,
            showgrid=True,
            gridcolor='lightgray',
            zeroline=True,
            zerolinecolor='black',
            autorange=True,
            automargin=True
        ),
        bargap=0.2
    )
    fig.update_traces(cliponaxis=False)

    return fig


selected_years = st.sidebar.multiselect(
    "📅 Выберите годы для отображения:",
    options=last_5_years,
    default=last_5_years
)


# ==========================================
# ВКЛАДКА 1: СВОДНАЯ СТАТИСТИКА
# ==========================================
if page == "📊 Сводная статистика":
    st.title("📊 Дашборд СВСП")
    
    # БЛОК 1: ЗАЯВКИ И АКТИВНОСТЬ
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

    # БЛОК 2: ДОГОВОРЫ, СТАНЦИИ, БОТЫ
    col_bottom_left, col_bottom_mid, col_bottom_right = st.columns([1, 1, 1.2])

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


# ==========================================
# ВКЛАДКА 2: СТАТИСТИКА ПОЛЬЗОВАТЕЛЕЙ
# ==========================================
elif page == "👤 Статистика пользователей":
    st.title("👤 Статистика пользователей СВСП")

    if df_users is not None and not df_users.empty:
        users_filtered = df_users[
            pd.to_numeric(df_users['Year'], errors='coerce').isin(selected_years)
        ].copy()

        # График 1: Подключения пользователей
        st.markdown(
            '<div class="header-blue">Количество подключений пользователя СВСП</div>',
            unsafe_allow_html=True
        )

        fig_conn = draw_yearly_stacked_chart(
            df=users_filtered,
            full_df=df_users,
            name_col='UserName',
            value_col='total_connections',
            xaxis_title='Количество подключений'
        )
        st.plotly_chart(fig_conn, use_container_width=True)

        # График 2: Часы работы пользователей
        st.markdown(
            '<div class="header-blue">Количество часов работы пользователя СВСП</div>',
            unsafe_allow_html=True
        )

        fig_hours = draw_yearly_stacked_chart(
            df=users_filtered,
            full_df=df_users,
            name_col='UserName',
            value_col='total_work_time_hours',
            xaxis_title='Часы работы'
        )
        st.plotly_chart(fig_hours, use_container_width=True)
    else:
        st.warning("Файл users.xlsx не найден или пуст.")


# ==========================================
# ВКЛАДКА 3: СТАТИСТИКА СТАНЦИЙ
# ==========================================
elif page == "📡 Статистика станций":
    st.title("📡 Статистика станций ДГС")

    if df_stations is not None and not df_stations.empty:
        stations_filtered = df_stations[
            pd.to_numeric(df_stations['Year'], errors='coerce').isin(selected_years)
        ].copy()

        # --- График 1: По месяцам ---
        st.markdown(
            '<div class="header-blue">Количество подключений и часов работы по месяцам</div>',
            unsafe_allow_html=True
        )

        agg_months = stations_filtered.groupby('Month').agg(
            total_conn=('total_connections', 'sum'),
            total_hours=('total_work_time_hours', 'sum')
        ).reset_index()

        fig_months = go.Figure()
        fig_months.add_trace(go.Bar(
            x=agg_months['Month'],
            y=agg_months['total_conn'],
            name='Количество подключений',
            marker_color='#5B9BD5'
        ))
        fig_months.add_trace(go.Bar(
            x=agg_months['Month'],
            y=agg_months['total_hours'],
            name='Часы работы',
            marker_color='#ED7D31'
        ))

        fig_months.update_layout(
            barmode='group',
            height=400,
            margin=dict(t=30, b=0, l=0, r=0),
            xaxis=dict(
                tickmode='linear',
                tick0=1,
                dtick=1,
                showgrid=True,
                gridcolor='lightgray'
            ),
            xaxis_title="Месяц",
            yaxis_title="Значение"
        )
        st.plotly_chart(fig_months, use_container_width=True)

        # --- График 2: Подключения по станциям ---
        st.markdown(
            '<div class="header-blue">Количество подключений к ДГС</div>',
            unsafe_allow_html=True
        )

        fig_conn_st = draw_yearly_stacked_chart(
            df=stations_filtered,
            full_df=df_stations,
            name_col='Station',
            value_col='total_connections',
            xaxis_title='Количество подключений'
        )
        st.plotly_chart(fig_conn_st, use_container_width=True)

        # --- График 3: Часы работы по станциям ---
        st.markdown(
            '<div class="header-blue">Количество часов работы от ДГС</div>',
            unsafe_allow_html=True
        )

        fig_hours_st = draw_yearly_stacked_chart(
            df=stations_filtered,
            full_df=df_stations,
            name_col='Station',
            value_col='total_work_time_hours',
            xaxis_title='Часы работы'
        )
        st.plotly_chart(fig_hours_st, use_container_width=True)
    else:
        st.warning("Файл stations.xlsx не найден.")


# ==========================================
# ВКЛАДКА 4: КАРТА
# ==========================================
elif page == "🗺️ Карта пользователей":
    st.title("🗺️ География пользователей")

    if os.path.exists(MAP_PATH):
        with open(MAP_PATH, 'r', encoding='utf-8') as f:
            html_content = f.read()

        # 1. Подставляем выбранные годы
        years_js = json.dumps([int(y) for y in selected_years])
        html_content = html_content.replace('/*__VISIBLE_YEARS__*/[]', years_js)

        # 2. Подставляем цвета (согласованы с YEAR_COLORS из app.py)
        colors_js = json.dumps({str(y): YEAR_COLORS.get(str(y), '#000000') for y in selected_years})
        html_content = html_content.replace('/*__YEAR_COLORS__*/{}', colors_js)

        st.caption(f"Показаны годы: {', '.join(map(str, selected_years)) or '—'}")
        st.components.v1.html(html_content, height=800, scrolling=False)
    else:
        st.warning("Файл карты (geo_users_SVSP.html) не найден в папке с приложением.")
        st.info("Запустите скрипт генерации карты и положите результат в папку с app.py.")