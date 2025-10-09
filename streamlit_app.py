import streamlit as st
from datetime import datetime, timedelta

# Set page config
st.set_page_config(
    page_title="Pequitopah Randomizer - Agenda de Restaurantes 🍽️",
    page_icon="🍽️",
    layout="wide"
)

# Custom CSS with centered layout and container styling
st.markdown("""
<style>
    .main-title {
        text-align: center;
        color: #123458;
        font-size: 2.2rem;
        margin-bottom: 2rem;
        font-weight: bold;
    }

    /* Centered container for all blocks */
    .blocks-wrapper {
        max-width: 1400px;
        margin: 0 auto;
        padding: 0 2rem;
    }

    /* Individual block containers */
    .block-container {
        background: linear-gradient(135deg, #F1EFEC, #D4C9BE);
        border: 3px solid #123458;
        border-radius: 20px;
        padding: 2rem;
        margin-bottom: 2rem;
        box-shadow: 0 8px 24px rgba(0,0,0,0.1);
    }

    .block-header {
        background: linear-gradient(135deg, #D4C9BE, #123458);
        color: white;
        padding: 1rem;
        border-radius: 15px;
        text-align: center;
        margin-bottom: 1.5rem;
        font-weight: bold;
        font-size: 1.3rem;
    }

    /* Entry card styling */
    .entry-card {
        background: #F1EFEC;
        border: 2px solid #D4C9BE;
        border-radius: 12px;
        padding: 1.5rem;
        margin-bottom: 1rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        position: relative;
    }

    .today-card {
        background: #123458 !important;
        color: #F1EFEC !important;
        border: 2px solid #123458 !important;
        box-shadow: 0 4px 12px rgba(18,52,88,0.3) !important;
    }

    .skipped-card {
        background: #f0f0f0 !important;
        color: #888 !important;
        border: 2px dashed #ccc !important;
        opacity: 0.6;
    }

    .entry-header {
        font-size: 1.1rem;
        font-weight: bold;
        margin-bottom: 0.8rem;
        color: #123458;
        padding: 0.8rem;
        background: rgba(212, 201, 190, 0.2);
        border-radius: 8px;
    }

    .today-card .entry-header {
        color: #F1EFEC !important;
        background: rgba(241, 239, 236, 0.1) !important;
    }

    .skipped-card .entry-header {
        color: #888 !important;
        background: rgba(200, 200, 200, 0.2) !important;
        text-decoration: line-through;
    }

    .restaurant-display {
        background: rgba(212, 201, 190, 0.3);
        padding: 0.8rem;
        border-radius: 8px;
        margin-bottom: 0.8rem;
        font-style: italic;
        color: #123458;
    }

    .today-card .restaurant-display {
        background: rgba(241, 239, 236, 0.15) !important;
        color: #F1EFEC !important;
    }

    .skipped-card .restaurant-display {
        background: rgba(200, 200, 200, 0.15) !important;
        color: #888 !important;
    }

    /* Button styling */
    .action-buttons {
        display: flex;
        gap: 0.5rem;
        margin-top: 0.8rem;
    }

    .today-card .stTextInput input {
        background-color: rgba(241, 239, 236, 0.1) !important;
        color: #F1EFEC !important;
        border-color: rgba(241, 239, 236, 0.3) !important;
    }

    .today-card .stTextInput label {
        color: #F1EFEC !important;
    }

    .skipped-card .stTextInput input {
        background-color: rgba(200, 200, 200, 0.1) !important;
        color: #888 !important;
    }

    .footer-section {
        text-align: center;
        margin-top: 3rem;
        padding: 2rem 0;
        border-top: 2px solid #D4C9BE;
    }

    /* Responsive design */
    @media (max-width: 768px) {
        .blocks-wrapper {
            padding: 0 1rem;
        }
        .block-container {
            padding: 1.5rem;
        }
    }
</style>
""", unsafe_allow_html=True)

# Helper functions
def proximo_dia_util(data):
    """Calculate next business day"""
    dia = data.weekday()  # Monday=0, Sunday=6
    if dia == 4:  # Friday -> +3 (Monday)
        data = data + timedelta(days=3)
    elif dia == 5:  # Saturday -> +2 (Monday)
        data = data + timedelta(days=2)  
    elif dia == 6:  # Sunday -> +1 (Monday)
        data = data + timedelta(days=1)
    else:  # Weekday -> +1
        data = data + timedelta(days=1)
    return data

def formatar_data(date):
    """Format date in Portuguese"""
    dias_semana = ['segunda-feira', 'terça-feira', 'quarta-feira', 'quinta-feira', 'sexta-feira', 'sábado', 'domingo']
    dd = date.strftime('%d')
    mm = date.strftime('%m') 
    yyyy = date.strftime('%Y')
    dia_nome = dias_semana[date.weekday()]
    return f"{dd}/{mm}/{yyyy} ({dia_nome})"

def calcular_bloco_com_constraints(titulo, nomes, data_inicio, starting_queue_index=0, skipped_entries=None, switched_entries=None):
    """Calculate block assignments with constraints, skip and switch logic"""
    if skipped_entries is None:
        skipped_entries = set()
    if switched_entries is None:
        switched_entries = {}

    data = data_inicio
    entries = []
    available_people = nomes.copy()
    queue_index = starting_queue_index
    date_index = 0
    max_dates = 70

    while len(entries) < len(nomes) and date_index < max_dates:
        data_iso = data.strftime('%Y-%m-%d')
        assigned_person = None
        assigned_index = None
        entry_key = f"{titulo}__{len(entries) + 1}__{data_iso}"

        # Check if this entry should be skipped
        if entry_key in skipped_entries:
            entries.append({
                'titulo': titulo,
                'idx': len(entries) + 1,
                'nome': "PULADO",
                'data': data,
                'data_iso': data_iso,
                'data_label': formatar_data(data),
                'key': f"rest__PULADO__{data_iso}",
                'entry_key': entry_key,
                'skipped': True
            })
            data = proximo_dia_util(data)
            date_index += 1
            continue

        # Check if this entry has been switched
        if entry_key in switched_entries:
            assigned_person = switched_entries[entry_key]
            # Remove from available people if present
            if assigned_person in available_people:
                available_people.remove(assigned_person)
        else:
            # Normal assignment logic
            for i in range(len(available_people)):
                candidate_index = (queue_index + i) % len(available_people)
                candidate = available_people[candidate_index]

                # If Pavel would be assigned on Tuesday, try to find Guilherme to switch
                if candidate.lower() == 'pavel' and data.weekday() == 1:  # Tuesday = 1
                    guilherme_index = next((idx for idx, person in enumerate(available_people) if person.lower() == 'guilherme'), -1)
                    if guilherme_index != -1:
                        assigned_person = 'Guilherme'
                        assigned_index = guilherme_index
                        break
                    continue

                assigned_person = candidate
                assigned_index = candidate_index
                break

            if assigned_person is not None and assigned_index is not None:
                available_people.pop(assigned_index)
                if queue_index >= len(available_people) and len(available_people) > 0:
                    queue_index = 0

        if assigned_person is not None:
            entries.append({
                'titulo': titulo,
                'idx': len(entries) + 1,
                'nome': assigned_person,
                'data': data,
                'data_iso': data_iso,
                'data_label': formatar_data(data),
                'key': f"rest__{assigned_person}__{data_iso}",
                'entry_key': entry_key,
                'skipped': False
            })

        data = proximo_dia_util(data)
        date_index += 1

    final_queue_index = queue_index % len(nomes) if len(nomes) > 0 else 0
    return entries, data, final_queue_index

def should_shift_blocks():
    """Check if blocks should be shifted based on current date"""
    base_date = datetime(2025, 9, 29)  # September 29, 2025
    today = datetime.now()
    nomes = ["Pavel", "Guilherme", "Victor", "Chris", "Alan", "Thiago", "Clayton", "Carolina"]

    entries, data_fim, _ = calcular_bloco_com_constraints("Bloco 1", nomes, base_date, 0)
    return today >= data_fim

def get_shifted_start_date():
    """Get the appropriate start date considering shifts"""
    base_date = datetime(2025, 9, 29)
    nomes = ["Pavel", "Guilherme", "Victor", "Chris", "Alan", "Thiago", "Clayton", "Carolina"]

    if should_shift_blocks():
        entries, data_fim, _ = calcular_bloco_com_constraints("Bloco 1", nomes, base_date, 0)
        return data_fim
    return base_date

# Initialize session state
if 'restaurants' not in st.session_state:
    st.session_state.restaurants = {}
if 'skipped_entries' not in st.session_state:
    st.session_state.skipped_entries = set()
if 'switched_entries' not in st.session_state:
    st.session_state.switched_entries = {}

def skip_entry(entry_key):
    """Skip an entry"""
    st.session_state.skipped_entries.add(entry_key)
    st.rerun()

def switch_with_next(current_entry, entries, block_num):
    """Switch current entry with next available person"""
    current_idx = current_entry['idx'] - 1  # Convert to 0-based index
    if current_idx + 1 < len(entries):
        next_entry = entries[current_idx + 1]
        if not next_entry.get('skipped', False):
            # Perform the switch
            current_key = current_entry['entry_key']
            next_key = next_entry['entry_key']

            st.session_state.switched_entries[current_key] = next_entry['nome']
            st.session_state.switched_entries[next_key] = current_entry['nome']
            st.rerun()

def render_entry(entry, is_today, block_num, entries):
    """Render a single entry with proper styling and action buttons"""
    is_skipped = entry.get('skipped', False)

    if is_skipped:
        card_class = "skipped-card"
    elif is_today:
        card_class = "today-card"
    else:
        card_class = "entry-card"

    # Create the card HTML structure
    st.markdown(f"""
    <div class="{card_class}">
        <div class="entry-header">
            {entry["idx"]}. {entry["nome"]} — {entry["data_label"]}
            {" (PULADO)" if is_skipped else ""}
        </div>
        {f'<div class="restaurant-display">🍽️ Restaurante: {st.session_state.restaurants.get(entry["key"], "")}</div>' 
          if st.session_state.restaurants.get(entry["key"], "") and not is_skipped else ""}
    </div>
    """, unsafe_allow_html=True)

    if not is_skipped:
        # Action buttons
        col1, col2, col3 = st.columns([1, 1, 2])

        with col1:
            if st.button("⏭️ Pular", key=f"skip_{entry['entry_key']}", help="Pular esta pessoa"):
                skip_entry(entry['entry_key'])

        with col2:
            if st.button("🔄 Trocar", key=f"switch_{entry['entry_key']}", help="Trocar com próxima pessoa"):
                switch_with_next(entry, entries, block_num)

        # Restaurant input
        restaurant_key = entry['key']
        current_restaurant = st.session_state.restaurants.get(restaurant_key, "")
        input_key = f"restaurant_{block_num}_{entry['idx']}_{entry['nome']}_{entry['data_iso']}"

        new_restaurant = st.text_input(
            "Restaurante:",
            value=current_restaurant,
            key=input_key,
            placeholder="Digite o restaurante...",
            label_visibility="collapsed"
        )

        # Update session state
        if new_restaurant != current_restaurant:
            st.session_state.restaurants[restaurant_key] = new_restaurant
            st.rerun()

    else:
        st.info("Esta entrada foi pulada")

def main():
    # Title
    st.markdown('<h1 class="main-title">Pequitopah Melhor APP do Mundo 🍽️</h1>', unsafe_allow_html=True)

    # Centered wrapper
    st.markdown('<div class="blocks-wrapper">', unsafe_allow_html=True)

    # Calculate cycles
    nomes = ["Pavel", "Guilherme", "Victor", "Chris", "Alan", "Thiago", "Clayton", "Carolina"]
    ciclos = 3
    data_atual = get_shifted_start_date()
    current_queue_index = 0
    today_iso = datetime.now().strftime('%Y-%m-%d')

    # Create each block in its own container
    for i in range(1, ciclos + 1):
        entries, data_fim, next_queue_index = calcular_bloco_com_constraints(
            f"Bloco {i}", 
            nomes, 
            data_atual, 
            current_queue_index,
            st.session_state.skipped_entries,
            st.session_state.switched_entries
        )

        # Block container
        with st.container():
            st.markdown('<div class="block-container">', unsafe_allow_html=True)

            # Block header
            st.markdown(f'<div class="block-header">Bloco {i}</div>', unsafe_allow_html=True)

            # Render entries
            for entry in entries:
                is_today = entry['data_iso'] == today_iso and not entry.get('skipped', False)
                render_entry(entry, is_today, i, entries)
                st.write("")  # Add spacing

            st.markdown('</div>', unsafe_allow_html=True)

        data_atual = data_fim  
        current_queue_index = next_queue_index

    st.markdown('</div>', unsafe_allow_html=True)  # Close wrapper

    # Footer
    st.markdown('<div class="footer-section">', unsafe_allow_html=True)
    st.image(
        "https://media1.giphy.com/media/v1.Y2lkPTc5MGI3NjExNzE0d24wZzEzcG4yZG05aDBwZ3R3M21la2o1M2EwejI4c25iaTM3cCZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/SAAMcPRfQpgyI/giphy.gif",
        width=220,
        caption="Desenvolvido para o melhor almoço do escritório! 😄"
    )
    st.markdown('</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()