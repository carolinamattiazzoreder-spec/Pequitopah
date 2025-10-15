
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import json
import os

# Configuração da página
st.set_page_config(page_title="Pequitopah", page_icon="📅", layout="wide")

# Título
st.title("📅 Pequitopah")
st.markdown("---")

# Configuração da fila - Pavel é o primeiro
queue_names = ["Pavel", "Guilherme", "Victor", "Chris", "Alan", "Thiago", "Clayton", "Carolina"]
start_date = datetime(2025, 10, 13)  # 13 de outubro, 2025 (início do Pavel)
pavel_index = queue_names.index("Pavel")  # Pavel está no índice 0

# Regras de dias que cada pessoa não trabalha
DEFAULT_SKIP_RULES = {
    "Pavel": [1],  # Terça-feira (0=segunda, 1=terça, etc.)
    "Guilherme": [4],  # Sexta-feira
    "Victor": [4],  # Sexta-feira  
    "Carolina": [4],  # Sexta-feira
    "Chris": [],
    "Alan": [],
    "Thiago": [],
    "Clayton": []
}

# Arquivos para salvar dados
ADJUSTMENTS_FILE = "queue_adjustments.json"
RULES_FILE = "skip_rules.json"

def load_adjustments():
    """Carrega ajustes salvos (pessoas puladas ou trocadas)"""
    if os.path.exists(ADJUSTMENTS_FILE):
        with open(ADJUSTMENTS_FILE, 'r') as f:
            return json.load(f)
    return {"skipped": {}, "switches": {}}

def save_adjustments(adjustments):
    """Salva ajustes no arquivo"""
    with open(ADJUSTMENTS_FILE, 'w') as f:
        json.dump(adjustments, f)

def load_skip_rules():
    """Carrega regras de dias que pessoas não trabalham"""
    if os.path.exists(RULES_FILE):
        with open(RULES_FILE, 'r') as f:
            return json.load(f)
    return DEFAULT_SKIP_RULES.copy()

def save_skip_rules(rules):
    """Salva regras de dias"""
    with open(RULES_FILE, 'w') as f:
        json.dump(rules, f)

def is_weekday(date):
    """Verifica se a data é um dia útil (segunda a sexta)"""
    return date.weekday() < 5

def get_next_weekday(date):
    """Obtém o próximo dia útil"""
    while not is_weekday(date):
        date += timedelta(days=1)
    return date

def count_weekdays_between(start_date, end_date):
    """Conta quantos dias úteis existem entre duas datas"""
    count = 0
    current_date = start_date
    while current_date <= end_date:
        if is_weekday(current_date):
            count += 1
        current_date += timedelta(days=1)
    return count

def should_skip_by_rule(person, date, skip_rules):
    """Verifica se a pessoa deve ser pulada por regra de dia da semana"""
    if person in skip_rules:
        return date.weekday() in skip_rules[person]
    return False

def get_person_for_date(target_date, adjustments, skip_rules):
    """Obtém a pessoa designada para uma data específica"""
    target_date = get_next_weekday(target_date) if not is_weekday(target_date) else target_date

    # Verificar se há troca específica para esta data
    date_str = target_date.strftime("%Y-%m-%d")
    if date_str in adjustments.get("switches", {}):
        return adjustments["switches"][date_str]

    # Verificar se a pessoa está pulada manualmente nesta data
    if date_str in adjustments.get("skipped", {}):
        skipped_person = adjustments["skipped"][date_str]
        weekdays_since_start = count_weekdays_between(start_date.date(), target_date) - 1
        person_index = (pavel_index + weekdays_since_start) % len(queue_names)

        attempts = 0
        while (queue_names[person_index] == skipped_person or 
               should_skip_by_rule(queue_names[person_index], target_date, skip_rules)) and attempts < len(queue_names):
            person_index = (person_index + 1) % len(queue_names)
            attempts += 1

        return queue_names[person_index]

    # Cálculo normal com regras de dias
    weekdays_since_start = count_weekdays_between(start_date.date(), target_date) - 1
    person_index = (pavel_index + weekdays_since_start) % len(queue_names)

    # Verificar regras de dias da semana
    attempts = 0
    while should_skip_by_rule(queue_names[person_index], target_date, skip_rules) and attempts < len(queue_names):
        person_index = (person_index + 1) % len(queue_names)
        attempts += 1

    return queue_names[person_index]

def get_cycle_info(target_date):
    """Obtém informações sobre o ciclo para uma data"""
    weekdays_since_start = count_weekdays_between(start_date.date(), target_date) - 1
    current_cycle_day = ((weekdays_since_start) % len(queue_names)) + 1
    return current_cycle_day

# Carregar dados
if 'adjustments' not in st.session_state:
    st.session_state.adjustments = load_adjustments()
if 'skip_rules' not in st.session_state:
    st.session_state.skip_rules = load_skip_rules()

adjustments = st.session_state.adjustments
skip_rules = st.session_state.skip_rules

# Data atual
today = datetime.now().date()
today_weekday = get_next_weekday(today) if not is_weekday(today) else today

st.info(f"**Hoje:** {today.strftime('%d/%m/%Y')}")

# Status atual
current_person = get_person_for_date(today_weekday, adjustments, skip_rules)
st.success(f"## 🎯 **{current_person}** é sua vez de escolher o restaurante!")

# Layout principal com controles na direita
col_main, col_controls = st.columns([0.72, 0.28])  # 72% para conteúdo principal, 28% para controles

with col_main:
    # Próximos dias
    st.markdown("### 📋 Próximos Dias")

    # Slider para dias na área principal
    days_to_show = st.slider("Dias para mostrar:", min_value=5, max_value=30, value=12, help="Quantidade de dias para mostrar")

    queue_data = []
    current_date = today_weekday

    for i in range(days_to_show):
        person = get_person_for_date(current_date, adjustments, skip_rules)
        cycle_day = get_cycle_info(current_date)

        # Verificar se é início de novo ciclo
        new_cycle_marker = ""
        if cycle_day == 1 and i > 0:
            new_cycle_marker = " 🔄"

        # Verificar se há ajustes para esta data  
        date_str = current_date.strftime("%Y-%m-%d")
        adjustments_info = ""
        if date_str in adjustments.get("skipped", {}):
            adjustments_info = " (Manual)"
        elif date_str in adjustments.get("switches", {}):
            adjustments_info = " (Trocado)"

        # Verificar se foi pulado por regra
        original_person_index = (pavel_index + count_weekdays_between(start_date.date(), current_date) - 1) % len(queue_names)
        original_person = queue_names[original_person_index]
        if should_skip_by_rule(original_person, current_date, skip_rules) and person != original_person:
            adjustments_info = " (Regra)"

        queue_data.append({
            "Data": current_date.strftime("%d/%m"),
            "Dia": current_date.strftime("%A"),
            "Pessoa": person + new_cycle_marker + adjustments_info
        })

        current_date = get_next_weekday(current_date + timedelta(days=1))

    df_queue = pd.DataFrame(queue_data)

    # Traduzir nomes dos dias
    day_translation = {
        "Monday": "Segunda", "Tuesday": "Terça", "Wednesday": "Quarta",
        "Thursday": "Quinta", "Friday": "Sexta"
    }

    df_queue["Dia"] = df_queue["Dia"].map(day_translation)

    def highlight_today_row(s):
        if s.name == 0:
            return ['background-color: #90EE90; font-weight: bold'] * len(s)
        else:
            return [''] * len(s)

    st.dataframe(
        df_queue.style.apply(highlight_today_row, axis=1), 
        use_container_width=True,
        hide_index=True
    )

    st.caption("🔄 = Novo ciclo | (Regra) = Pulado por regra | (Manual) = Pulado manualmente | (Trocado) = Troca manual")

with col_controls:
    st.markdown("### ⚙️ Controles")

    # Botões empilhados verticalmente
    if st.button("🚫 Pular pessoa\nde hoje", type="secondary", use_container_width=True):
        date_str = today_weekday.strftime("%Y-%m-%d")
        st.session_state.adjustments["skipped"][date_str] = current_person
        save_adjustments(st.session_state.adjustments)
        st.rerun()

    next_weekday = get_next_weekday(today_weekday + timedelta(days=1))
    next_person = get_person_for_date(next_weekday, adjustments, skip_rules)

    if st.button(f"🔄 Trocar\n{current_person[:8]}... ↔ {next_person[:8]}...", type="secondary", use_container_width=True):
        today_str = today_weekday.strftime("%Y-%m-%d")
        next_str = next_weekday.strftime("%Y-%m-%d")

        st.session_state.adjustments["switches"][today_str] = next_person
        st.session_state.adjustments["switches"][next_str] = current_person
        save_adjustments(st.session_state.adjustments)
        st.rerun()

    if st.button("🗑️ Limpar\najustes", use_container_width=True):
        st.session_state.adjustments = {"skipped": {}, "switches": {}}
        save_adjustments(st.session_state.adjustments)
        if os.path.exists(ADJUSTMENTS_FILE):
            os.remove(ADJUSTMENTS_FILE)
        st.rerun()

    st.markdown("---")

    # Configuração de regras mais compacta
    with st.expander("📋 Regras"):
        st.markdown("**Dias que não trabalham:**")

        day_names = ["Seg", "Ter", "Qua", "Qui", "Sex"]

        for person in queue_names:
            current_skip_days = [day_names[day] for day in skip_rules.get(person, [])]
            selected_days = st.multiselect(
                f"{person[:6]}:", 
                day_names, 
                default=current_skip_days,
                key=f"skip_{person}",
                help=f"Dias que {person} não trabalha"
            )
            skip_rules[person] = [day_names.index(day) for day in selected_days]

        if st.button("💾 Salvar", use_container_width=True):
            st.session_state.skip_rules = skip_rules
            save_skip_rules(skip_rules)
            st.success("✅ Salvo!")
            st.rerun()

# Tabela de previsões (largura total)
st.markdown("### 🔮 Previsões")

prediction_days = st.slider("Previsão para próximos dias:", min_value=15, max_value=60, value=30)

prediction_data = []
for person in queue_names:
    next_dates = []
    search_date = today_weekday

    # Encontrar próximas 3 datas da pessoa
    for _ in range(prediction_days):
        if get_person_for_date(search_date, adjustments, skip_rules) == person:
            days_until = count_weekdays_between(today_weekday, search_date) - 1
            if person == current_person and search_date == today_weekday:
                next_dates.append("Hoje")
            else:
                next_dates.append(f"{search_date.strftime('%d/%m')} (em {days_until} dias)")

            if len(next_dates) >= 3:
                break

        search_date = get_next_weekday(search_date + timedelta(days=1))

    # Preencher com N/A se não encontrou 3 datas
    while len(next_dates) < 3:
        next_dates.append("N/A")

    # Verificar regras de dias
    skip_days = [["Segunda", "Terça", "Quarta", "Quinta", "Sexta"][day] for day in skip_rules.get(person, [])]
    skip_info = ", ".join(skip_days) if skip_days else "Nenhum"

    prediction_data.append({
        "Pessoa": person,
        "Próxima": next_dates[0],
        "Seguinte": next_dates[1], 
        "Depois": next_dates[2],
        "Não Trabalha": skip_info
    })

df_predictions = pd.DataFrame(prediction_data)

# Destacar pessoa atual
def highlight_current_person(s):
    if s["Pessoa"] == current_person:
        return ['background-color: #E8F4FD; font-weight: bold'] * len(s)
    else:
        return [''] * len(s)

st.dataframe(
    df_predictions.style.apply(highlight_current_person, axis=1),
    use_container_width=True,
    hide_index=True
)

# Mostrar ajustes ativos se houver
if adjustments["skipped"] or adjustments["switches"]:
    st.markdown("---")
    st.markdown("### 📝 Alterações Ativas")

    col1, col2 = st.columns(2)

    with col1:
        if adjustments["skipped"]:
            st.markdown("**Pessoas Puladas (Manual):**")
            for date_str, person in adjustments["skipped"].items():
                date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
                st.write(f"• {date_obj.strftime('%d/%m')}: {person}")

    with col2:
        if adjustments["switches"]:
            st.markdown("**Trocas Feitas:**")
            processed_switches = set()
            for date_str, person in adjustments["switches"].items():
                if date_str not in processed_switches:
                    date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
                    st.write(f"• {date_obj.strftime('%d/%m')}: {person}")
                    processed_switches.add(date_str)
