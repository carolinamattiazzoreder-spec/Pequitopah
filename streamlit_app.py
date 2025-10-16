import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, date
import json
import os
from typing import List, Dict, Any

# ---------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------
st.set_page_config(page_title="Pequitopah", page_icon="🍽️", layout="wide")

# ---------------------------------------------------------------------
# Constants and configuration
# ---------------------------------------------------------------------
ORIGINAL_QUEUE: List[str] = ["Pavel", "Guilherme", "Victor", "Chris", "Alan", "Thiago", "Clayton", "Carolina"]

# Anchor: start rotation on 09/10/2025 with Pavel
ANCHOR_DATE: date = date(2025, 10, 9)
ANCHOR_PERSON: str = "Pavel"

# Files for persistence
CURRENT_QUEUE_FILE = "current_queue.json"
DAILY_ASSIGNMENTS_FILE = "daily_assignments.json"
PREFERENCES_FILE = "preferences.json"
ROTATION_STATE_FILE = "rotation_state.json"  # stores {anchor_date, anchor_person, offset}

# Day labels (Portuguese, weekdays only)
DAY_NAMES_PT = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta"]
DAY_NAMES_PT_SHORT = ["Seg", "Ter", "Qua", "Qui", "Sex"]

# ---------------------------------------------------------------------
# Safe JSON helpers
# ---------------------------------------------------------------------
def safe_load_json(path: str, default: Any) -> Any:
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return default

def safe_save_json(path: str, data: Any) -> None:
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)

# ---------------------------------------------------------------------
# Persistence: queue, assignments, preferences, rotation state
# ---------------------------------------------------------------------
def load_current_queue() -> List[str]:
    data = safe_load_json(CURRENT_QUEUE_FILE, None)
    if isinstance(data, list) and data and all(isinstance(x, str) for x in data):
        return data
    return ORIGINAL_QUEUE.copy()

def save_current_queue(queue: List[str]) -> None:
    safe_save_json(CURRENT_QUEUE_FILE, queue)

def load_daily_assignments() -> Dict[str, str]:
    data = safe_load_json(DAILY_ASSIGNMENTS_FILE, {})
    if isinstance(data, dict):
        return {k: v for k, v in data.items() if isinstance(k, str) and isinstance(v, str)}
    return {}

def save_daily_assignments(data: Dict[str, str]) -> None:
    safe_save_json(DAILY_ASSIGNMENTS_FILE, data)

def load_preferences() -> Dict[str, List[int]]:
    default = {
        "Pavel": [], "Guilherme": [], "Victor": [], "Chris": [],
        "Alan": [], "Thiago": [], "Clayton": [], "Carolina": []
    }
    data = safe_load_json(PREFERENCES_FILE, default)
    clean: Dict[str, List[int]] = {}
    for p in ORIGINAL_QUEUE:
        vals = data.get(p, [])
        if isinstance(vals, list):
            clean[p] = [x for x in vals if isinstance(x, int) and 0 <= x <= 4]
        else:
            clean[p] = []
    return clean

def save_preferences(prefs: Dict[str, List[int]]) -> None:
    safe_save_json(PREFERENCES_FILE, prefs)

def load_rotation_state(current_queue: List[str]) -> int:
    """
    rotation_offset aligns positions so that index 'rotation_offset' in the current_queue
    is the person assigned on ANCHOR_DATE, and persists with anchor metadata.
    """
    want_anchor_date = ANCHOR_DATE.strftime("%Y-%m-%d")
    state = safe_load_json(ROTATION_STATE_FILE, None)
    if isinstance(state, dict) and "offset" in state:
        if state.get("anchor_date") == want_anchor_date and state.get("anchor_person") == ANCHOR_PERSON:
            try:
                return int(state["offset"])
            except Exception:
                pass
    # Initialize offset so ANCHOR_PERSON is assigned on ANCHOR_DATE
    try:
        idx = current_queue.index(ANCHOR_PERSON)
    except ValueError:
        idx = 0
    save_rotation_state(idx)
    return idx

def save_rotation_state(offset: int) -> None:
    state = {
        "anchor_date": ANCHOR_DATE.strftime("%Y-%m-%d"),
        "anchor_person": ANCHOR_PERSON,
        "offset": int(offset)
    }
    safe_save_json(ROTATION_STATE_FILE, state)

# ---------------------------------------------------------------------
# Date utilities
# ---------------------------------------------------------------------
def is_weekday(d: date) -> bool:
    return d.weekday() < 5

def get_next_weekday(d: date) -> date:
    while not is_weekday(d):
        d += timedelta(days=1)
    return d

def count_weekdays_between(start_d: date, end_d: date) -> int:
    """
    Inclusive count of weekdays between two dates.
    """
    if end_d < start_d:
        return 0
    cnt = 0
    cur = start_d
    while cur <= end_d:
        if is_weekday(cur):
            cnt += 1
        cur += timedelta(days=1)
    return cnt

# ---------------------------------------------------------------------
# Rotation math
# ---------------------------------------------------------------------
def weekdays_since_anchor(d: date) -> int:
    d = get_next_weekday(d)
    return max(0, count_weekdays_between(ANCHOR_DATE, d) - 1)  # 0 at anchor

def position_for_date(d: date, queue: List[str], rotation_offset: int) -> int:
    w = weekdays_since_anchor(d)
    return (rotation_offset + w) % len(queue)

def cycle_index_for_date(d: date, queue_len: int, rotation_offset: int) -> int:
    w = weekdays_since_anchor(d)
    return (rotation_offset + w) // queue_len

# ---------------------------------------------------------------------
# Selection logic (manual override -> preferences)
# ---------------------------------------------------------------------
def select_person_for_date(
    target_date: date,
    current_queue: List[str],
    daily_assignments: Dict[str, str],
    preferences: Dict[str, List[int]],
    rotation_offset: int
) -> str:
    td = get_next_weekday(target_date)
    date_str = td.strftime("%Y-%m-%d")

    # Manual override wins
    if date_str in daily_assignments:
        return daily_assignments[date_str]

    n = len(current_queue)
    base = position_for_date(td, current_queue, rotation_offset)

    # First pass: respect preferences
    for i in range(n):
        cand = current_queue[(base + i) % n]
        if td.weekday() in preferences.get(cand, []):
            continue
        return cand

    # Second pass: ignore preferences to ensure assignment
    return current_queue[base]

# ---------------------------------------------------------------------
# Permanent queue modification
# ---------------------------------------------------------------------
def switch_persons(current_queue: List[str], person1: str, person2: str) -> List[str]:
    new_queue = current_queue.copy()
    if person1 in new_queue and person2 in new_queue:
        i1, i2 = new_queue.index(person1), new_queue.index(person2)
        new_queue[i1], new_queue[i2] = new_queue[i2], new_queue[i1]
    return new_queue

# ---------------------------------------------------------------------
# Streamlit App
# ---------------------------------------------------------------------
st.title("📅 Pequitopah - Sistema de Almoço")
st.markdown("---")

# Session state boot
if "current_queue" not in st.session_state:
    st.session_state.current_queue = load_current_queue()
if "daily_assignments" not in st.session_state:
    st.session_state.daily_assignments = load_daily_assignments()
if "preferences" not in st.session_state:
    st.session_state.preferences = load_preferences()
if "rotation_offset" not in st.session_state:
    st.session_state.rotation_offset = load_rotation_state(st.session_state.current_queue)

current_queue = st.session_state.current_queue
daily_assignments = st.session_state.daily_assignments
preferences = st.session_state.preferences
rotation_offset = st.session_state.rotation_offset

# Today and current person
today = datetime.now().date()
today_wd = get_next_weekday(today)
st.info(f"Hoje: {today.strftime('%d/%m/%Y')}")

current_person = select_person_for_date(today_wd, current_queue, daily_assignments, preferences, rotation_offset)
st.success(f"## {current_person} decide onde vamos almoçar hoje!")
# Layout
col_main, col_controls = st.columns([0.7, 0.3])

with col_main:
    st.markdown("### Próximos Dias")
    days_to_show = st.slider("Dias para mostrar:", min_value=5, max_value=20, value=12)

    rows = []
    cur_date = today_wd
    prev_cycle = None
    for i in range(days_to_show):
        cyc = cycle_index_for_date(cur_date, len(current_queue), rotation_offset)
        person = select_person_for_date(cur_date, current_queue, daily_assignments, preferences, rotation_offset)

        cycle_marker = ""
        if prev_cycle is not None and cyc != prev_cycle:
            cycle_marker = " 🔄"
        prev_cycle = cyc

        rows.append({
            "Data": cur_date.strftime("%d/%m"),
            "Dia": DAY_NAMES_PT[cur_date.weekday()],
            "Pessoa": person + cycle_marker
        })
        cur_date = get_next_weekday(cur_date + timedelta(days=1))

    df_queue = pd.DataFrame(rows)

    def highlight_today(s: pd.Series):
        return ['background-color: #90EE90; font-weight: bold'] * len(s) if s.name == 0 else [''] * len(s)

    st.dataframe(df_queue.style.apply(highlight_today, axis=1), use_container_width=True, hide_index=True)
    st.caption("🔄 = Novo ciclo | Passar vez remove somente este loop (ajusta a rotação) | Trocar posição altera a fila permanentemente")

with col_controls:
    st.markdown("### ⚙️ Controles")

    # Pass Turn: remove only for this loop by shifting rotation phase +1 from today onward
    if st.button(f"⏭️ Passar vez hoje (pular {current_person} neste loop)", type="primary", use_container_width=True):
        n = len(current_queue)
        if n > 1:
            st.session_state.rotation_offset = (rotation_offset + 1) % n
            save_rotation_state(st.session_state.rotation_offset)
            # Clear manual override for today since the assignment is recalculated
            ds = today_wd.strftime("%Y-%m-%d")
            if ds in st.session_state.daily_assignments:
                st.session_state.daily_assignments.pop(ds, None)
                save_daily_assignments(st.session_state.daily_assignments)
        st.rerun()

    # Switch: swap today with "tomorrow" permanently
    tomorrow_date = get_next_weekday(today_wd + timedelta(days=1))
    tomorrow_person = select_person_for_date(tomorrow_date, current_queue, daily_assignments, preferences, rotation_offset)
    if st.button(f"🔄 Trocar posição ({current_person} ↔ {tomorrow_person})", type="secondary", use_container_width=True):
        st.session_state.current_queue = switch_persons(current_queue, current_person, tomorrow_person)
        save_current_queue(st.session_state.current_queue)
        st.rerun()

    st.markdown("---")

    # Temporary manual override for today
    st.markdown("Escolha manual para hoje (temporário):")
    try:
        current_person_index = current_queue.index(current_person)
    except ValueError:
        current_person_index = 0
    selected_person = st.selectbox("Pessoa:", current_queue, index=current_person_index, key="manual_select")

    if st.button("✅ Confirmar", use_container_width=True):
        if selected_person != current_person:
            st.session_state.daily_assignments[today_wd.strftime("%Y-%m-%d")] = selected_person
            save_daily_assignments(st.session_state.daily_assignments)
            st.rerun()

    st.markdown("---")

    # Reset buttons
    if st.button("🔄 Resetar fila original", use_container_width=True):
        st.session_state.current_queue = ORIGINAL_QUEUE.copy()
        save_current_queue(st.session_state.current_queue)
        # Recompute rotation offset so ANCHOR_PERSON is assigned on ANCHOR_DATE
        try:
            idx = st.session_state.current_queue.index(ANCHOR_PERSON)
        except ValueError:
            idx = 0
        st.session_state.rotation_offset = idx
        save_rotation_state(idx)
        st.rerun()

    if st.button("🗑️ Limpar tudo", use_container_width=True):
        # Reset in-memory
        st.session_state.current_queue = ORIGINAL_QUEUE.copy()
        st.session_state.daily_assignments = {}
        st.session_state.preferences = load_preferences()
        # Remove files
        for f in [CURRENT_QUEUE_FILE, DAILY_ASSIGNMENTS_FILE, PREFERENCES_FILE, ROTATION_STATE_FILE]:
            if os.path.exists(f):
                os.remove(f)
        st.rerun()

# Preferences expander
with st.expander("⚙️ Preferências"):
    st.markdown("Dias que preferem NÃO decidir (cria troca temporária):")

    for person in ORIGINAL_QUEUE:
        current_days = [DAY_NAMES_PT_SHORT[d] for d in preferences.get(person, [])]
        selected_days = st.multiselect(f"{person}:", DAY_NAMES_PT_SHORT, default=current_days, key=f"pref_{person}")
        preferences[person] = [DAY_NAMES_PT_SHORT.index(d) for d in selected_days]

    if st.button("💾 Salvar Preferências", use_container_width=True):
        st.session_state.preferences = preferences
        save_preferences(preferences)
        st.success("✅ Preferências salvas!")
        st.rerun()

# Predictions table
st.markdown("### 🔮 Próximas Vezes")
prediction_rows = []
for person in current_queue:
    next_dates: List[str] = []
    search_date = today_wd
    for _ in range(60):
        assigned = select_person_for_date(search_date, current_queue, daily_assignments, preferences, rotation_offset)
        if assigned == person:
            if person == current_person and search_date == today_wd:
                next_dates.append("Hoje")
            else:
                days_until = count_weekdays_between(today_wd, search_date)
                next_dates.append(f"{search_date.strftime('%d/%m')} (em {max(0, days_until-1)} dias)")
            if len(next_dates) >= 3:
                break
        search_date = get_next_weekday(search_date + timedelta(days=1))

    while len(next_dates) < 3:
        next_dates.append("N/A")

    skip_days_list = [DAY_NAMES_PT_SHORT[d] for d in preferences.get(person, [])]
    skip_info = ", ".join(skip_days_list) if skip_days_list else "Nenhum"
    prediction_rows.append({
        "Pessoa": person,
        "Próxima": next_dates[0],
        "Seguinte": next_dates[1],
        "Depois": next_dates[2],
        "Evita": skip_info
    })

df_predictions = pd.DataFrame(prediction_rows)

def highlight_current(s: pd.Series):
    return ['background-color: #E8F4FD; font-weight: bold'] * len(s) if s["Pessoa"] == current_person else [''] * len(s)

st.dataframe(df_predictions.style.apply(highlight_current, axis=1), use_container_width=True, hide_index=True)

# Temporary assignments display
if daily_assignments:
    st.markdown("---")
    st.markdown("### 📝 Escolhas Manuais (Temporárias)")
    for date_str, p in sorted(daily_assignments.items()):
        date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
        # Compute original without overrides
        original = select_person_for_date(date_obj, current_queue, {}, preferences, rotation_offset)
        if p != original:
            st.write(f"• {date_obj.strftime('%d/%m')}: {p} (no lugar de {original})")
