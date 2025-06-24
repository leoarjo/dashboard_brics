import streamlit as st
import pandas as pd
import psycopg2
from dotenv import load_dotenv
import os
import plotly.express as px

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

st.set_page_config(layout="wide") # Define o layout da página como largo
st.title("Dashboard BRICS")

# Função para conectar ao banco de dados e carregar os dados
@st.cache_data # Para armazenar em cache os dados e evitar múltiplas consultas
def load_data(table_name):
    try:
        conn = psycopg2.connect(
            host=os.getenv("DB_HOST"),
            database=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD")
        )
        query = f"SELECT * FROM {table_name}"
        df = pd.read_sql(query, conn)
        conn.close()
        return df
    except Exception as e:
        st.error(f"Erro ao conectar ou carregar dados de {table_name}: {e}")
        return pd.DataFrame() # Retorna um DataFrame vazio em caso de erro

# Carregar os dados de PIB e População
# Usando os nomes de tabela que você confirmou no seu banco de dados
df_gdp = load_data("brics_pib")
df_population = load_data("brics_populacao")

# --- Estrutura do Dashboard ---

# Mensagem de carregamento ou erro
if df_gdp.empty or df_population.empty:
    st.warning("Não foi possível carregar todos os dados. Verifique a conexão e os nomes das tabelas.")
else:
    # --- RENOMEAR AS COLUNAS AQUI PARA PADRONIZAR ---
    # Renomeando as colunas do df_gdp para padronizar com os nomes usados no código
    df_gdp.rename(columns={
        'pais': 'country',
        'ano': 'year',
        'unidade': 'unit',
        'pib_dolar': 'gdp_usd'
    }, inplace=True)

    # Renomeando as colunas do df_population para padronizar com os nomes usados no código
    df_population.rename(columns={
        'pais': 'country',
        'ano': 'year',
        'unidade': 'unit',
        'populacao': 'population'
    }, inplace=True)

    # Convertendo as colunas numéricas para o tipo correto e tratando erros
    df_gdp['gdp_usd'] = pd.to_numeric(df_gdp['gdp_usd'], errors='coerce')
    df_population['population'] = pd.to_numeric(df_population['population'], errors='coerce')

    # Remove linhas com valores nulos que podem ter surgido da conversão
    df_gdp.dropna(subset=['gdp_usd', 'country', 'year'], inplace=True)
    df_population.dropna(subset=['population', 'country', 'year'], inplace=True)

    # --- Seção de Filtros Globais (Barra Lateral) ---
    st.sidebar.header("Filtros")

    # --- NOVO FILTRO DE PAÍSES EM CASCATA ---
    selected_countries_option = st.sidebar.radio(
        "Como deseja selecionar os países?",
        ("Todos os Países", "Selecionar Países Específicos")
    )

    all_countries = []
    if 'country' in df_gdp.columns:
        all_countries = sorted(df_gdp['country'].unique())

    selected_countries = []
    if selected_countries_option == "Todos os Países":
        selected_countries = all_countries
    else:
        if all_countries:
            selected_countries = st.sidebar.multiselect(
                "Escolha os Países:",
                all_countries,
                default=all_countries # Pode iniciar com todos selecionados por padrão aqui também
            )
        else:
            st.sidebar.info("Nenhum país disponível para seleção.")

    if not selected_countries: # Se, após a seleção, nenhum país for escolhido, força uma lista vazia para o filtro
        st.warning("Nenhum país selecionado. Os gráficos podem não exibir dados.")
        selected_countries = ['_NO_COUNTRY_'] # Valor dummy para não dar erro no filtro .isin()

    # --- FIM DO NOVO FILTRO DE PAÍSES ---

    # Filtro por Ano (usando slider para um range)
    if 'year' in df_gdp.columns and pd.api.types.is_numeric_dtype(df_gdp['year']):
        min_year = int(df_gdp['year'].min())
        max_year = int(df_gdp['year'].max())
        year_range = st.sidebar.slider(
            "Selecione o Intervalo de Anos:",
            min_value=min_year,
            max_value=max_year,
            value=(min_year, max_year)
        )
    else:
        st.error("Coluna 'year' não encontrada ou não é numérica nos dados de PIB. Verifique o renomeamento e tipo.")
        year_range = (2000, 2023) # Valor padrão para evitar erro

    # Aplicar filtros aos DataFrames
    if 'country' in df_gdp.columns and 'year' in df_gdp.columns:
        df_gdp_filtered = df_gdp[
            (df_gdp['country'].isin(selected_countries)) &
            (df_gdp['year'] >= year_range[0]) &
            (df_gdp['year'] <= year_range[1])
        ]
    else:
        df_gdp_filtered = pd.DataFrame()

    if 'country' in df_population.columns and 'year' in df_population.columns:
        df_population_filtered = df_population[
            (df_population['country'].isin(selected_countries)) &
            (df_population['year'] >= year_range[0]) &
            (df_population['year'] <= year_range[1])
        ]
    else:
        df_population_filtered = pd.DataFrame()

    # --- Visão Geral dos Dados Filtrados ---
    st.subheader("Visão Geral dos Dados Filtrados")
    col1, col2 = st.columns(2)
    with col1:
        st.write("#### Dados de PIB")
        st.dataframe(df_gdp_filtered)
    with col2:
        st.write("#### Dados de População")
        st.dataframe(df_population_filtered)

    st.markdown("---") # Separador visual

    # --- Visualizações Principais ---

    # Gráfico de Linha: Evolução do PIB ao Longo do Tempo por País
    st.header("Evolução do PIB por País")
    if not df_gdp_filtered.empty and \
       'country' in df_gdp_filtered.columns and \
       'year' in df_gdp_filtered.columns and \
       'gdp_usd' in df_gdp_filtered.columns:
        fig_gdp_time = px.line(
            df_gdp_filtered,
            x="year",
            y="gdp_usd",
            color="country",
            title="PIB (US$) ao Longo do Tempo",
            labels={"year": "Ano", "gdp_usd": "PIB (US$)", "country": "País"}
        )
        st.plotly_chart(fig_gdp_time, use_container_width=True)
    else:
        st.info("Sem dados de PIB para o período ou países selecionados para exibir o gráfico.")

    st.markdown("---")

    # Gráfico de Linha: Evolução da População ao Longo do Tempo por País
    st.header("Evolução da População por País")
    if not df_population_filtered.empty and \
       'country' in df_population_filtered.columns and \
       'year' in df_population_filtered.columns and \
       'population' in df_population_filtered.columns:
        fig_pop_time = px.line(
            df_population_filtered,
            x="year",
            y="population",
            color="country",
            title="População ao Longo do Tempo",
            labels={"year": "Ano", "population": "População", "country": "País"}
        )
        st.plotly_chart(fig_pop_time, use_container_width=True)
    else:
        st.info("Sem dados de população para o período ou países selecionados para exibir o gráfico.")

    st.markdown("---")

    # Análise Combinada: PIB per Capita
    df_combined = pd.DataFrame() # Inicializa df_combined
    if {'country', 'year'}.issubset(df_gdp_filtered.columns) and {'country', 'year'}.issubset(df_population_filtered.columns):
        df_combined = pd.merge(df_gdp_filtered, df_population_filtered, on=['country', 'year'], how='inner', suffixes=('_gdp', '_pop'))

        if not df_combined.empty:
            if 'gdp_usd' in df_combined.columns and 'population' in df_combined.columns and \
               pd.api.types.is_numeric_dtype(df_combined['gdp_usd']) and pd.api.types.is_numeric_dtype(df_combined['population']) and \
               (df_combined['population'] != 0).all():
                df_combined['gdp_per_capita'] = df_combined['gdp_usd'] / df_combined['population']
                st.header("PIB per Capita por País")
                fig_gdp_per_capita = px.line(
                    df_combined,
                    x="year",
                    y="gdp_per_capita",
                    color="country",
                    title="PIB per Capita (US$) ao Longo do Tempo",
                    labels={"year": "Ano", "gdp_per_capita": "PIB per Capita (US$)", "country": "País"}
                )
                st.plotly_chart(fig_gdp_per_capita, use_container_width=True)
            else:
                st.info("Não foi possível calcular o PIB per capita. Verifique os dados de PIB e População ou se há divisão por zero.")
        else:
            st.info("Não há dados combinados para calcular o PIB per capita. Verifique se os dados de PIB e População correspondem por país e ano no intervalo selecionado.")
    else:
        st.info("Colunas essenciais (country, year) não encontradas nos dados filtrados para combinar os dados de PIB e População.")

    st.markdown("---")

    # Tabela Sumária (Exemplo: Dados do Último Ano Disponível)
    st.header("Dados Anuais Mais Recentes")
    if 'df_combined' in locals() and not df_combined.empty:
        latest_year = df_combined['year'].max()
        df_latest_data = df_combined[df_combined['year'] == latest_year]
        
        cols_to_display = ['country', 'year', 'gdp_usd', 'population', 'gdp_per_capita']
        existing_cols = [col for col in cols_to_display if col in df_latest_data.columns]
        
        if not df_latest_data.empty:
            st.dataframe(df_latest_data[existing_cols].round(2))
        else:
            st.info(f"Não há dados para o ano mais recente ({latest_year}) após a combinação e filtragem.")
    else:
        st.info("Sem dados combinados para exibir a tabela sumária do último ano.")

    st.markdown("---")

    st.write("Dashboard desenvolvido para o projeto BRICS.")