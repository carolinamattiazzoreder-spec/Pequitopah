import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, date
import json
import os
from typing import List, Dict, Any, Tuple, Optional

# ---------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------
st.set_page_config(page_title="Pequitopah", page_icon="🍽️", layout="wide")

# ---------------------------------------------------------------------
# Global style (sleeker, compact, better tab spacing)
# ---------------------------------------------------------------------
st.markdown(
    """
    <style>
      /* Compact buttons */
      div.stButton > button {
        padding: 0.35rem 0.6rem;
        font-size: 0.92rem;
        border-radius: 10px;
      }
      /* Dense select/multiselect */
      div[data-baseweb="select"] > div {
        min-height: 38px;
      }
      /* Tabs: increase spacing */
      div[data-baseweb="tab-list"],
      div[role="tablist"] {
        gap: 0.6rem !important;
      }
      button[role="tab"] {
        padding: 0.4rem 0.8rem;
        border-radius: 10px;
      }
      /* Compact captions and headers */
      .small-caption { font-size: .85rem; color: #6b7280; }
      .section-subtle { font-size: .95rem; margin-top: .25rem; color: #6b7280; }
      /* Card-like containers */
      .card {
        background: rgba(0,0,0,0.03);
        border: 1px solid rgba(0,0,0,0.08);
        border-radius: 12px;
        padding: .6rem .8rem;
      }
      .card-tight {
        background: rgba(0,0,0,0.02);
        border: 1px solid rgba(0,0,0,0.06);
        border-radius: 10px;
        padding: .5rem .6rem;
      }
      /* Dataframe readability */
      .stDataFrame { font-size: 0.95rem; }
      /* Sliders smaller label spacing */
      div.stSlider > div { padding-top: 0.2rem; }
      /* Space below top-level tabs */
      .stTabs { margin-bottom: 0.6rem; }
    </style>
    """,
    unsafe_allow_html=True,
)

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
    # Dynamic: accept any names, sanitize values 0..4 (weekdays)
    data = safe_load_json(PREFERENCES_FILE, {})
    if not isinstance(data, dict):
        return {}
    cleaned: Dict[str, List[int]] = {}
    for k, v in data.items():
        if isinstance(k, str) and isinstance(v, list):
            cleaned[k] = [x for x in v if isinstance(x, int) and 0 <= x <= 4]
    return cleaned

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
# Selection (single-day, used for some controls)
# ---------------------------------------------------------------------
def select_person_for_date(
    target_date: date,
    current_queue: List[str],
    daily_assignments: Dict[str, str],
    preferences: Dict[str, List[int]],
    rotation_offset: int
) -> str:
    td = get_next_weekday(target_date)
    ds = td.strftime("%Y-%m-%d")

    if ds in daily_assignments:
        return daily_assignments[ds]

    n = len(current_queue)
    base = position_for_date(td, current_queue, rotation_offset)

    # Respect preferences
    for i in range(n):
        cand = current_queue[(base + i) % n]
        if td.weekday() in preferences.get(cand, []):
            continue
        return cand

    return current_queue[base]

# ---------------------------------------------------------------------
# Simulation with preference "swap" carryover
# ---------------------------------------------------------------------
def simulate_schedule(
    start_date: date,
    days: int,
    current_queue: List[str],
    daily_assignments: Dict[str, str],
    preferences: Dict[str, List[int]],
    rotation_offset: int
) -> List[Tuple[date, str]]:
    """
    Build a day-by-day schedule applying:
    - manual overrides,
    - if base person avoids the weekday, assign next eligible and carry the avoided base person to the next weekday (swap),
    - the carryover is attempted only on the immediate next weekday; if they also avoid it, the carry is dropped.
    """
    out: List[Tuple[date, str]] = []
    carry_person: Optional[str] = None
    cur = get_next_weekday(start_date)
    for _ in range(days):
        ds = cur.strftime("%Y-%m-%d")

        # Manual override: takes precedence and clears any carryover
        if ds in daily_assignments:
            out.append((cur, daily_assignments[ds]))
            carry_person = None
            cur = get_next_weekday(cur + timedelta(days=1))
            continue

        # If there is a carryover, try to place them today unless they avoid today
        if carry_person is not None and cur.weekday() not in preferences.get(carry_person, []):
            out.append((cur, carry_person))
            carry_person = None
            cur = get_next_weekday(cur + timedelta(days=1))
            continue
        else:
            # drop carryover if cannot place today
            carry_person = None

        # Normal selection from base
        n = len(current_queue)
        base = position_for_date(cur, current_queue, rotation_offset)
        base_person = current_queue[base]

        # If base avoids, find next eligible and carry base to next day
        if cur.weekday() in preferences.get(base_person, []):
            assigned = None
            for i in range(1, n + 1):  # search next eligible including wrap
                cand = current_queue[(base + i) % n]
                if cur.weekday() in preferences.get(cand, []):
                    continue
                assigned = cand
                break
            if assigned is None:
                assigned = base_person  # fallback
            else:
                # set carry to place base_person tomorrow (single-day swap)
                carry_person = base_person
            out.append((cur, assigned))
        else:
            out.append((cur, base_person))

        cur = get_next_weekday(cur + timedelta(days=1))

    return out

# ---------------------------------------------------------------------
# Queue change helpers
# ---------------------------------------------------------------------
def apply_queue_change(new_queue: List[str], realign_anchor: bool = True) -> None:
    """
    Apply a new queue order and update rotation phase according to intent:
    - realign_anchor=True: re-align offset so ANCHOR_PERSON is assigned on ANCHOR_DATE (use in Config/Reset).
    - realign_anchor=False: preserve current phase/offset (use in Agenda actions like Switch to avoid undoing Skip Turn/Skip Day).
    """
    st.session_state.current_queue = new_queue
    save_current_queue(new_queue)
    if realign_anchor:
        try:
            idx = new_queue.index(ANCHOR_PERSON)
        except ValueError:
            idx = 0
        st.session_state.rotation_offset = idx
        save_rotation_state(idx)
    else:
        # Keep current rotation_offset to preserve phase after actions like Switch/Skip Day/Skip Turn
        save_rotation_state(st.session_state.rotation_offset)
    st.rerun()

def move_person(queue: List[str], person: str, new_index: int) -> List[str]:
    if person not in queue:
        return queue
    q = queue.copy()
    old_index = q.index(person)
    q.pop(old_index)
    new_index = max(0, min(new_index, len(q)))  # clamp to ends
    q.insert(new_index, person)
    return q

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

# Tabs (Agenda, Configurações with sub-tabs; widen spacing via CSS above)
tab_agenda, tab_config = st.tabs(["Agenda", "Configurações"])

with tab_agenda:
    # Today and schedule
    today = datetime.now().date()
    today_wd = get_next_weekday(today)
    st.info(f"Hoje: {today.strftime('%d/%m/%Y')}")

    # Simulate for consistency across UI
    sim_days = 60
    schedule = simulate_schedule(today_wd, sim_days, current_queue, daily_assignments, preferences, rotation_offset)
    current_person = schedule[0][1]
    st.success(f"## {current_person} decide onde vamos almoçar hoje!")

    # Layout: main + compact controls
    col_main, col_controls = st.columns([0.72, 0.28])

    with col_main:
        st.markdown("### Próximos Dias")
        with st.container():
            days_to_show = st.slider("Dias para mostrar:", min_value=5, max_value=20, value=12, label_visibility="collapsed")
            rows = []
            prev_cycle = None
            for i in range(days_to_show):
                d, p = schedule[i]
                cyc = cycle_index_for_date(d, len(current_queue), rotation_offset)
                cycle_marker = "" if (prev_cycle is None or cyc == prev_cycle) else " 🔄"
                prev_cycle = cyc
                rows.append({
                    "Data": d.strftime("%d/%m"),
                    "Dia": DAY_NAMES_PT[d.weekday()],
                    "Pessoa": p + cycle_marker
                })
            df_queue = pd.DataFrame(rows)

            def highlight_today(s: pd.Series):
                return ['background-color: #90EE90; font-weight: bold'] * len(s) if s.name == 0 else [''] * len(s)

            st.dataframe(df_queue.style.apply(highlight_today, axis=1), use_container_width=True, hide_index=True)
            st.caption("🔄 = Novo ciclo")

    with col_controls:
        st.markdown("### Controles")
        st.markdown('<div class="card-tight">', unsafe_allow_html=True)
        # Three compact buttons with sleek icons
        b1, b2, b3 = st.columns([1,1,1])
        with b1:
            pass_turn = st.button("⏭", use_container_width=True, help="Passar vez (pular a pessoa de hoje neste loop)")
        with b2:
            skip_day = st.button("🚫", use_container_width=True, help="Pular o dia (Ninguém hoje; adia a rotação)")
        with b3:
            # Determine tomorrow from simulation for consistency
            if len(schedule) >= 2:
                tomorrow_person = schedule[1][1]
            else:
                tomorrow_person = select_person_for_date(get_next_weekday(today_wd + timedelta(days=1)),
                                                         current_queue, daily_assignments, preferences, rotation_offset)
            do_switch = st.button("⇄", use_container_width=True, help="Trocar hoje com amanhã")

        # Action handlers (logic unchanged)
        if pass_turn:
            n = len(current_queue)
            if n > 1:
                st.session_state.rotation_offset = (rotation_offset + 1) % n
                save_rotation_state(st.session_state.rotation_offset)
                ds = today_wd.strftime("%Y-%m-%d")
                if ds in st.session_state.daily_assignments:
                    st.session_state.daily_assignments.pop(ds, None)
                    save_daily_assignments(st.session_state.daily_assignments)
            st.rerun()

        if skip_day:
            ds = today_wd.strftime("%Y-%m-%d")
            st.session_state.daily_assignments[ds] = "Ninguém"
            save_daily_assignments(st.session_state.daily_assignments)
            n = len(current_queue)
            if n > 0:
                st.session_state.rotation_offset = (rotation_offset - 1) % n
                save_rotation_state(st.session_state.rotation_offset)
            st.rerun()

        if do_switch:
            new_q = current_queue.copy()
            if current_person in new_q and tomorrow_person in new_q:
                i1, i2 = new_q.index(current_person), new_q.index(tomorrow_person)
                new_q[i1], new_q[i2] = new_q[i2], new_q[i1]
                apply_queue_change(new_q, realign_anchor=False)

        st.markdown("</div>", unsafe_allow_html=True)

        # Compact temporary manual override
        st.markdown("#### Manual (Hoje)")
        st.markdown('<div class="card-tight">', unsafe_allow_html=True)
        try:
            current_person_index = current_queue.index(current_person)
        except ValueError:
            current_person_index = 0
        selected_person = st.selectbox("Escolha:", current_queue, index=current_person_index, key="manual_select", label_visibility="collapsed")
        col_ok, col_reset = st.columns([1,1])
        with col_ok:
            if st.button("✓", use_container_width=True, help="Confirmar escolha manual para hoje"):
                if selected_person != current_person:
                    st.session_state.daily_assignments[today_wd.strftime("%Y-%m-%d")] = selected_person
                    save_daily_assignments(st.session_state.daily_assignments)
                    st.rerun()
        with col_reset:
            if st.button("🧹", use_container_width=True, help="Limpar escolha manual de hoje"):
                ds = today_wd.strftime("%Y-%m-%d")
                if ds in st.session_state.daily_assignments:
                    st.session_state.daily_assignments.pop(ds, None)
                    save_daily_assignments(st.session_state.daily_assignments)
                    st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

        # Compact reset
        st.markdown("#### Reset")
        st.markdown('<div class="card-tight">', unsafe_allow_html=True)
        c1, c2 = st.columns([1,1])
        with c1:
            if st.button("⟲", use_container_width=True, help="Restaurar fila original"):
                apply_queue_change(ORIGINAL_QUEUE.copy(), realign_anchor=True)
        with c2:
            if st.button("🗑", use_container_width=True, help="Zerar arquivos e estado"):
                st.session_state.current_queue = ORIGINAL_QUEUE.copy()
                st.session_state.daily_assignments = {}
                st.session_state.preferences = {}
                for f in [CURRENT_QUEUE_FILE, DAILY_ASSIGNMENTS_FILE, PREFERENCES_FILE, ROTATION_STATE_FILE]:
                    if os.path.exists(f):
                        os.remove(f)
                st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    # Predictions table (from simulation to stay consistent with swaps)
    st.markdown("### 🔮 Próximas Vezes")
    prediction_rows = []
    horizon = max(60, 6 * max(1, len(current_queue)))
    long_schedule = simulate_schedule(today_wd, horizon, current_queue, daily_assignments, preferences, rotation_offset)
    for person in current_queue:
        next_dates: List[str] = []
        for d, p in long_schedule:
            if p == person:
                if person == current_person and d == today_wd:
                    next_dates.append("Hoje")
                else:
                    days_until = count_weekdays_between(today_wd, d)
                    next_dates.append(f"{d.strftime('%d/%m')} (em {max(0, days_until-1)} dias)")
                if len(next_dates) >= 3:
                    break
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

    # Temporary assignments display (simulation for consistent "original" without overrides)
    temp_overrides = st.session_state.get("daily_assignments", {})
    if temp_overrides:
        st.markdown("---")
        st.markdown("### 📝 Escolhas Manuais (Temporárias)")
        for date_str, p in sorted(temp_overrides.items()):
            date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
            original = simulate_schedule(
                start_date=date_obj,
                days=1,
                current_queue=current_queue,
                daily_assignments={},  # ignore overrides for baseline
                preferences=preferences,
                rotation_offset=rotation_offset
            )[0][1]
            if p != original:
                st.write(f"• {date_obj.strftime('%d/%m')}: {p} (no lugar de {original})")

with tab_config:
    # Sub-tabs: Preferências first to make it the focus, with an interactive grid
    pref_tab, fila_tab = st.tabs(["Preferências", "Fila"])

    with pref_tab:
        st.markdown("#### Preferências por dia (clique para alternar)")
        st.markdown('<div class="card">', unsafe_allow_html=True)

        # Build editable grid: one row per person, five checkbox columns (Seg..Sex)
        # Pref value True means "avoid that weekday".
        grid_cols = ["Pessoa"] + DAY_NAMES_PT_SHORT
        # Prepare data
        data_rows = []
        for person in current_queue:
            avoid = set(preferences.get(person, []))
            row = {
                "Pessoa": person,
                "Seg": 0 in avoid,
                "Ter": 1 in avoid,
                "Qua": 2 in avoid,
                "Qui": 3 in avoid,
                "Sex": 4 in avoid,
            }
            data_rows.append(row)
        df_pref = pd.DataFrame(data_rows, columns=grid_cols)

        edited = st.data_editor(
            df_pref,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Pessoa": st.column_config.TextColumn("Pessoa", disabled=True),
                "Seg": st.column_config.CheckboxColumn("Seg", help="Evitar segunda"),
                "Ter": st.column_config.CheckboxColumn("Ter", help="Evitar terça"),
                "Qua": st.column_config.CheckboxColumn("Qua", help="Evitar quarta"),
                "Qui": st.column_config.CheckboxColumn("Qui", help="Evitar quinta"),
                "Sex": st.column_config.CheckboxColumn("Sex", help="Evitar sexta"),
            }
        )

        # Quick presets row
        c_all, c_none, c_tue_fri = st.columns([1,1,1])
        if c_all.button("✚ Marcar todos"):
            for d in DAY_NAMES_PT_SHORT:
                edited[d] = True
        if c_none.button("⌫ Limpar todos"):
            for d in DAY_NAMES_PT_SHORT:
                edited[d] = False
        if c_tue_fri.button("✓ Ter/Sex"):
            for d in DAY_NAMES_PT_SHORT:
                edited[d] = (d in ["Ter", "Sex"])

        # Save/Reset
        s1, s2 = st.columns([1,1])
        with s1:
            if st.button("💾 Salvar preferências", use_container_width=True):
                # Convert edited grid back to dict
                new_prefs: Dict[str, List[int]] = {}
                for _, r in edited.iterrows():
                    days = []
                    for idx, short in enumerate(DAY_NAMES_PT_SHORT):
                        if bool(r[short]):
                            days.append(idx)
                    new_prefs[str(r["Pessoa"])] = days
                # Clean up for removed people (if any got out of sync)
                for k in list(new_prefs.keys()):
                    if k not in current_queue:
                        new_prefs.pop(k, None)
                st.session_state.preferences = new_prefs
                save_preferences(new_prefs)
                st.success("Preferências salvas!")
                st.rerun()
        with s2:
            if st.button("↺ Resetar preferências", use_container_width=True):
                st.session_state.preferences = {}
                save_preferences({})
                st.rerun()

        st.markdown('</div>', unsafe_allow_html=True)
        st.caption("Dica: marque os dias que a pessoa prefere não decidir. A troca é automática só naquele dia.")

    with fila_tab:
        st.markdown("#### Gestão da fila (compacto)")
        st.markdown('<div class="card">', unsafe_allow_html=True)

        # Add / Remove side-by-side
        a, b = st.columns([1,1])
        with a:
            st.markdown("Adicionar")
            new_name = st.text_input("Nome", value="", placeholder="Ex.: João", label_visibility="collapsed", key="add_name")
            if st.button("✚ Adicionar", use_container_width=True):
                candidate = new_name.strip()
                if candidate:
                    existing_lower = [p.lower() for p in current_queue]
                    if candidate.lower() in existing_lower:
                        st.warning("Nome já existe.")
                    else:
                        apply_queue_change(current_queue + [candidate], realign_anchor=True)
                else:
                    st.warning("Informe um nome válido.")
        with b:
            st.markdown("Remover")
            to_remove = st.multiselect("Selecionar", current_queue, [], label_visibility="collapsed")
            if st.button("✖ Remover", use_container_width=True, disabled=(len(to_remove) == 0)):
                new_q = [p for p in current_queue if p not in set(to_remove)]
                if len(new_q) == 0:
                    st.warning("A fila não pode ficar vazia.")
                else:
                    apply_queue_change(new_q, realign_anchor=True)

        st.markdown("---")

        # Reorder compact
        st.markdown("Reordenar")
        if len(current_queue) > 0:
            col_p, col_btns = st.columns([0.6, 0.4])
            with col_p:
                person_to_move = st.selectbox("Pessoa", current_queue, key="person_to_move_cfg", label_visibility="collapsed")
            with col_btns:
                up, down = st.columns(2)
                with up:
                    can_up = current_queue.index(person_to_move) > 0
                    if st.button("⬆", use_container_width=True, disabled=not can_up):
                        idx = current_queue.index(person_to_move)
                        new_q = move_person(current_queue, person_to_move, idx - 1)
                        apply_queue_change(new_q, realign_anchor=True)
                with down:
                    can_down = current_queue.index(person_to_move) < len(current_queue) - 1
                    if st.button("⬇", use_container_width=True, disabled=not can_down):
                        idx = current_queue.index(person_to_move)
                        new_q = move_person(current_queue, person_to_move, idx + 1)
                        apply_queue_change(new_q, realign_anchor=True)

            # Direct position set (optional, compact)
            setpos_col1, setpos_col2 = st.columns([0.6, 0.4])
            with setpos_col1:
                st.caption(f"Atual: {current_queue.index(person_to_move)+1}/{len(current_queue)}")
            with setpos_col2:
                target_pos = st.number_input("Posição", min_value=1, max_value=len(current_queue),
                                             value=current_queue.index(person_to_move)+1, step=1,
                                             label_visibility="collapsed")
                if st.button("↕ Mover", use_container_width=True):
                    new_q = move_person(current_queue, person_to_move, int(target_pos)-1)
                    apply_queue_change(new_q, realign_anchor=True)

        st.markdown('</div>', unsafe_allow_html=True)
        st.caption("Mudanças de ordem e nomes realinham a rotação para manter o início em 09/10/2025 com Pavel.")
