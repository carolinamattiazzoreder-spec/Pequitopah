
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import json
import os

# Configuração da página
st.set_page_config(page_title="Pequitopah", page_icon="🍽️", layout="wide")

# Título
st.title("📅 Pequitopah, evitando dor de cabeça desde de 15/10/2025!")
st.markdown("---")

# Configuração da fila - Pavel é o primeiro no ciclo, mas Alan começou em 15/10
queue_names = ["Pavel", "Guilherme", "Victor", "Chris", "Alan", "Thiago", "Clayton", "Carolina"]
start_date = datetime(2025, 10, 15).date()  # Converter para date object
alan_index = queue_names.index("Alan")  # Alan está no índice 4

# Regras de dias que cada pessoa prefere não decidir
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
ADJUSTMENTS_FILE = "decision_adjustments.json"
RULES_FILE = "decision_rules.json"
SWAPS_FILE = "decision_swaps.json"

def load_adjustments():
    """Carrega ajustes salvos (pessoas que passaram a vez ou trocaram)"""
    if os.path.exists(ADJUSTMENTS_FILE):
        with open(ADJUSTMENTS_FILE, 'r') as f:
            return json.load(f)
    return {"skipped": {}, "switches": {}}

def save_adjustments(adjustments):
    """Salva ajustes no arquivo"""
    with open(ADJUSTMENTS_FILE, 'w') as f:
        json.dump(adjustments, f)

def load_skip_rules():
    """Carrega regras de dias que pessoas preferem não decidir"""
    if os.path.exists(RULES_FILE):
        with open(RULES_FILE, 'r') as f:
            return json.load(f)
    return DEFAULT_SKIP_RULES.copy()

def save_skip_rules(rules):
    """Salva regras de dias"""
    with open(RULES_FILE, 'w') as f:
        json.dump(rules, f)

def load_rule_swaps():
    """Carrega trocas geradas por regras"""
    if os.path.exists(SWAPS_FILE):
        with open(SWAPS_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_rule_swaps(swaps):
    """Salva trocas geradas por regras"""
    with open(SWAPS_FILE, 'w') as f:
        json.dump(swaps, f)

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
    """Verifica se a pessoa prefere não decidir neste dia da semana"""
    if person in skip_rules:
        return date.weekday() in skip_rules[person]
    return False

def generate_rule_swaps(skip_rules, start_date, end_date):
    """Gera todas as trocas necessárias baseadas nas regras para um período"""
    swaps = {}
    current_date = start_date

    while current_date <= end_date:
        if is_weekday(current_date):
            # Calcular pessoa original para esta data
            weekdays_since_start = count_weekdays_between(start_date, current_date) - 1
            person_index = (alan_index + weekdays_since_start) % len(queue_names)
            original_person = queue_names[person_index]

            # Verificar se pessoa original tem regra para este dia
            if should_skip_by_rule(original_person, current_date, skip_rules):
                # Encontrar próxima pessoa na fila
                next_person_index = (person_index + 1) % len(queue_names)
                next_person = queue_names[next_person_index]

                # Encontrar quando seria o dia da próxima pessoa
                search_date = current_date + timedelta(days=1)
                for _ in range(14):  # Buscar nos próximos 14 dias
                    if is_weekday(search_date):
                        search_weekdays = count_weekdays_between(start_date, search_date) - 1
                        search_person_index = (alan_index + search_weekdays) % len(queue_names)
                        if queue_names[search_person_index] == next_person:
                            # Fazer a troca
                            date_str = current_date.strftime("%Y-%m-%d")
                            search_date_str = search_date.strftime("%Y-%m-%d")

                            swaps[date_str] = next_person
                            swaps[search_date_str] = original_person
                            break
                    search_date += timedelta(days=1)

        current_date += timedelta(days=1)

    return swaps

def get_person_for_date(target_date, adjustments, skip_rules, rule_swaps, today=None):
    """Obtém a pessoa que decide onde almoçar em uma data específica"""
    if today is None:
        today = datetime.now().date()

    target_date = get_next_weekday(target_date) if not is_weekday(target_date) else target_date
    date_str = target_date.strftime("%Y-%m-%d")

    # Verificar se há troca manual específica para esta data
    if date_str in adjustments.get("switches", {}):
        return adjustments["switches"][date_str]

    # Verificar se há troca por regra para esta data (apenas datas futuras)
    if target_date >= today and date_str in rule_swaps:
        return rule_swaps[date_str]

    # Verificar se a pessoa passou a vez nesta data
    if date_str in adjustments.get("skipped", {}):
        skipped_person = adjustments["skipped"][date_str]
        weekdays_since_start = count_weekdays_between(start_date, target_date) - 1
        person_index = (alan_index + weekdays_since_start) % len(queue_names)

        attempts = 0
        while queue_names[person_index] == skipped_person and attempts < len(queue_names):
            person_index = (person_index + 1) % len(queue_names)
            attempts += 1

        return queue_names[person_index]

    # Cálculo normal - Alan começou, fila volta para Pavel
    weekdays_since_start = count_weekdays_between(start_date, target_date) - 1
    person_index = (alan_index + weekdays_since_start) % len(queue_names)

    return queue_names[person_index]

def get_cycle_info(target_date):
    """Obtém informações sobre o ciclo para uma data"""
    weekdays_since_start = count_weekdays_between(start_date, target_date) - 1
    current_cycle_position = (alan_index + weekdays_since_start) % len(queue_names)
    if current_cycle_position >= alan_index:
        cycle_day = current_cycle_position - alan_index + 1
    else:
        cycle_day = len(queue_names) - alan_index + current_cycle_position + 1
    return cycle_day

# Carregar dados
if 'adjustments' not in st.session_state:
    st.session_state.adjustments = load_adjustments()
if 'skip_rules' not in st.session_state:
    st.session_state.skip_rules = load_skip_rules()
if 'rule_swaps' not in st.session_state:
    st.session_state.rule_swaps = load_rule_swaps()

adjustments = st.session_state.adjustments
skip_rules = st.session_state.skip_rules
rule_swaps = st.session_state.rule_swaps

# Data atual
today = datetime.now().date()
today_weekday = get_next_weekday(today) if not is_weekday(today) else today

st.info(f"**Hoje:** {today.strftime('%d/%m/%Y')}")

# Status atual
current_person = get_person_for_date(today_weekday, adjustments, skip_rules, rule_swaps, today)
st.success(f"## **{current_person}**, você decide onde vamos almoçar hoje!")

# Layout principal com controles na direita
col_main, col_controls = st.columns([0.72, 0.28])

with col_main:
    # Próximos dias
    st.markdown("### Próximas Dias")

    days_to_show = st.slider("Dias para mostrar:", min_value=5, max_value=30, value=12, help="Quantidade de dias para mostrar")

    queue_data = []
    current_date = today_weekday

    for i in range(days_to_show):
        person = get_person_for_date(current_date, adjustments, skip_rules, rule_swaps, today)

        # Calcular se é início de novo ciclo (quando volta ao Pavel)
        new_cycle_marker = ""
        if person == "Pavel" and i > 0:
            new_cycle_marker = " 🔄"

        # Verificar se há ajustes para esta data  
        date_str = current_date.strftime("%Y-%m-%d")
        adjustments_info = ""
        if date_str in adjustments.get("skipped", {}):
            adjustments_info = " (Passou)"
        elif date_str in adjustments.get("switches", {}):
            adjustments_info = " (Trocado)"
        elif current_date >= today and date_str in rule_swaps:
            adjustments_info = " (Preferência)"

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

    st.caption("🔄 = Novo ciclo (volta ao Pavel) | (Preferência) = Trocado por preferência | (Passou) = Passou a vez | (Trocado) = Troca manual")
    st.caption("⚠️ **Preferências:** Se pessoa não quer decidir, troca com a próxima da fila")

with col_controls:
    st.markdown("### ⚙️ Controles")

    # Botões empilhados verticalmente
    if st.button("➡️ Passar vez\nhoje", type="secondary", use_container_width=True):
        date_str = today_weekday.strftime("%Y-%m-%d")
        st.session_state.adjustments["skipped"][date_str] = current_person
        save_adjustments(st.session_state.adjustments)
        st.rerun()

    next_weekday = get_next_weekday(today_weekday + timedelta(days=1))
    next_person = get_person_for_date(next_weekday, adjustments, skip_rules, rule_swaps, today)

    if st.button(f"🔄 Trocar\n{current_person[:8]}... ↔ {next_person[:8]}...", type="secondary", use_container_width=True):
        today_str = today_weekday.strftime("%Y-%m-%d")
        next_str = next_weekday.strftime("%Y-%m-%d")

        st.session_state.adjustments["switches"][today_str] = next_person
        st.session_state.adjustments["switches"][next_str] = current_person
        save_adjustments(st.session_state.adjustments)
        st.rerun()

    if st.button("🗑️ Limpar\najustes", use_container_width=True):
        st.session_state.adjustments = {"skipped": {}, "switches": {}}
        st.session_state.rule_swaps = {}
        save_adjustments(st.session_state.adjustments)
        save_rule_swaps({})
        if os.path.exists(ADJUSTMENTS_FILE):
            os.remove(ADJUSTMENTS_FILE)
        if os.path.exists(SWAPS_FILE):
            os.remove(SWAPS_FILE)
        st.rerun()

    st.markdown("---")

    # Configuração de preferências
    with st.expander("⚙️ Preferências"):
        st.markdown("**Dias que preferem não decidir:**")
        st.caption("⚠️ Gera trocas automáticas com próxima pessoa")

        day_names = ["Seg", "Ter", "Qua", "Qui", "Sex"]

        for person in queue_names:
            current_skip_days = [day_names[day] for day in skip_rules.get(person, [])]
            selected_days = st.multiselect(
                f"{person[:6]}:", 
                day_names, 
                default=current_skip_days,
                key=f"skip_{person}",
                help=f"Dias que {person} prefere não ter que decidir - troca automaticamente com próxima pessoa"
            )
            skip_rules[person] = [day_names.index(day) for day in selected_days]

        if st.button("💾 Salvar Preferências", use_container_width=True):
            st.session_state.skip_rules = skip_rules
            save_skip_rules(skip_rules)

            # Gerar trocas para próximos 60 dias
            end_date = today + timedelta(days=60)
            new_swaps = generate_rule_swaps(skip_rules, today, end_date)
            st.session_state.rule_swaps = new_swaps
            save_rule_swaps(new_swaps)

            st.success("✅ Preferências salvas e trocas geradas!")
            st.rerun()

# Tabela de previsões
st.markdown("### 🔮 Próximas Vezes de Decidir")

prediction_days = st.slider("Previsão para próximos dias:", min_value=15, max_value=60, value=30)

prediction_data = []
for person in queue_names:
    next_dates = []
    search_date = today_weekday

    for _ in range(prediction_days):
        if get_person_for_date(search_date, adjustments, skip_rules, rule_swaps, today) == person:
            days_until = count_weekdays_between(today_weekday, search_date) - 1
            if person == current_person and search_date == today_weekday:
                next_dates.append("Hoje")
            else:
                next_dates.append(f"{search_date.strftime('%d/%m')} (em {days_until} dias)")

            if len(next_dates) >= 3:
                break

        search_date = get_next_weekday(search_date + timedelta(days=1))

    while len(next_dates) < 3:
        next_dates.append("N/A")

    skip_days = [["Segunda", "Terça", "Quarta", "Quinta", "Sexta"][day] for day in skip_rules.get(person, [])]
    skip_info = ", ".join(skip_days) if skip_days else "Nenhum"

    prediction_data.append({
        "Pessoa": person,
        "Próxima": next_dates[0],
        "Seguinte": next_dates[1], 
        "Depois": next_dates[2],
        "Evita Decidir": skip_info
    })

df_predictions = pd.DataFrame(prediction_data)

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

# Mostrar trocas ativas por preferências
if rule_swaps:
    st.markdown("---")
    st.markdown("### 🔄 Trocas por Preferências")

    swaps_info = []
    processed_dates = set()

    for date_str, person in rule_swaps.items():
        if date_str not in processed_dates:
            date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
            if date_obj >= today:
                # Encontrar a pessoa original
                weekdays_since_start = count_weekdays_between(start_date, date_obj) - 1
                original_index = (alan_index + weekdays_since_start) % len(queue_names)
                original_person = queue_names[original_index]

                swaps_info.append({
                    "Data": date_obj.strftime("%d/%m"),
                    "Dia": day_translation.get(date_obj.strftime("%A"), date_obj.strftime("%A")),
                    "Original": original_person,
                    "Decide": person
                })
                processed_dates.add(date_str)

    if swaps_info:
        df_swaps = pd.DataFrame(swaps_info)
        st.dataframe(df_swaps, use_container_width=True, hide_index=True)
        st.caption("Trocas automáticas geradas pelas preferências de dias")

# Mostrar ajustes manuais ativos se houver
if adjustments["skipped"] or adjustments["switches"]:
    st.markdown("---")
    st.markdown("### 📝 Alterações Manuais")

    col1, col2 = st.columns(2)

    with col1:
        if adjustments["skipped"]:
            st.markdown("**Pessoas que Passaram a Vez:**")
            for date_str, person in adjustments["skipped"].items():
                date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
                st.write(f"• {date_obj.strftime('%d/%m')}: {person}")

    with col2:
        if adjustments["switches"]:
            st.markdown("**Trocas Manuais:**")
            processed_switches = set()
            for date_str, person in adjustments["switches"].items():
                if date_str not in processed_switches:
                    date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
                    st.write(f"• {date_obj.strftime('%d/%m')}: {person}")
                    processed_switches.add(date_str)
