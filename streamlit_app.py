
import streamlit as st
from datetime import datetime, timedelta
import json

# Set page config
st.set_page_config(
    page_title="Pequitopah Randomizer - Agenda de Restaurantes 🍽️",
    page_icon="🍽️",
    layout="wide"
)

# Custom CSS for styling
st.markdown("""
<style>
    /* Modern palette tokens */
    :root{
        --bg:#F1EFEC;
        --surface:#D4C9BE;
        --accent:#123458;
        --text:#030303;
        --highlight-bg:#123458;
        --highlight-fg:#F1EFEC;
    }

    .main-title {
        text-align: center;
        color: var(--accent);
        font-size: 2.2rem;
        margin-bottom: 2rem;
    }

    .block-container {
        background: var(--surface);
        padding: 1.5rem;
        border-radius: 14px;
        margin-bottom: 1rem;
        box-shadow: 0 6px 14px rgba(0,0,0,0.08);
    }

    .entry-container {
        background: rgba(255,255,255,0.35);
        padding: 1rem;
        margin-bottom: 0.8rem;
        border-radius: 10px;
        border: 1px dashed rgba(18,52,88,0.35);
    }

    .today-highlight {
        background: var(--highlight-bg) !important;
        color: var(--highlight-fg) !important;
        border: 1px solid var(--highlight-bg) !important;
        box-shadow: 0 8px 20px rgba(0,0,0,0.16) !important;
    }

    .restaurant-input {
        margin-top: 0.5rem;
    }

    .footer-container {
        text-align: center;
        margin-top: 3rem;
        padding: 2rem 0;
    }

    .hero-gif {
        width: 220px;
        max-width: 90%;
        border-radius: 12px;
        box-shadow: 0 6px 14px rgba(0,0,0,0.12);
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

def calcular_bloco_com_constraints(titulo, nomes, data_inicio, starting_queue_index=0):
    """Calculate block assignments with constraints"""
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

        if assigned_person is not None:
            entries.append({
                'titulo': titulo,
                'idx': len(entries) + 1,
                'nome': assigned_person,
                'data': data,
                'data_iso': data_iso,
                'data_label': formatar_data(data),
                'key': f"rest__{assigned_person}__{data_iso}"
            })

            available_people.pop(assigned_index)

            if queue_index >= len(available_people) and len(available_people) > 0:
                queue_index = 0

        data = proximo_dia_util(data)
        date_index += 1

    final_queue_index = queue_index % len(nomes)
    return entries, data, final_queue_index

def should_shift_blocks():
    """Check if blocks should be shifted based on current date"""
    base_date = datetime(2025, 9, 29)  # September 29, 2025
    today_iso = datetime.now().strftime('%Y-%m-%d')
    nomes = ["Pavel", "Guilherme", "Victor", "Chris", "Alan", "Thiago", "Clayton", "Carolina"]

    entries, data_fim, _ = calcular_bloco_com_constraints("Bloco 1", nomes, base_date, 0)
    block2_start_iso = data_fim.strftime('%Y-%m-%d')
    today = datetime.strptime(today_iso, '%Y-%m-%d')
    block2_start = datetime.strptime(block2_start_iso, '%Y-%m-%d')

    return today >= block2_start

def get_shifted_start_date():
    """Get the appropriate start date considering shifts"""
    base_date = datetime(2025, 9, 29)
    nomes = ["Pavel", "Guilherme", "Victor", "Chris", "Alan", "Thiago", "Clayton", "Carolina"]

    if should_shift_blocks():
        entries, data_fim, _ = calcular_bloco_com_constraints("Bloco 1", nomes, base_date, 0)
        return data_fim
    return base_date

# Initialize session state for restaurant data
if 'restaurants' not in st.session_state:
    st.session_state.restaurants = {}

# Main app
def main():
    # Title
    st.markdown('<h1 class="main-title">Pequitopah Melhor APP do Mundo 🍽️</h1>', unsafe_allow_html=True)

    # Calculate cycles
    nomes = ["Pavel", "Guilherme", "Victor", "Chris", "Alan", "Thiago", "Clayton", "Carolina"]
    ciclos = 3
    data_atual = get_shifted_start_date()
    current_queue_index = 0
    today_iso = datetime.now().strftime('%Y-%m-%d')

    # Create columns for blocks
    cols = st.columns(ciclos)

    for i in range(1, ciclos + 1):
        entries, data_fim, next_queue_index = calcular_bloco_com_constraints(f"Bloco {i}", nomes, data_atual, current_queue_index)

        with cols[i-1]:
            st.markdown(f'<div class="block-container">', unsafe_allow_html=True)
            st.subheader(f"Bloco {i}")

            for entry in entries:
                # Check if this is today's entry
                is_today = entry['data_iso'] == today_iso
                container_class = "entry-container today-highlight" if is_today else "entry-container"

                st.markdown(f'<div class="{container_class}">', unsafe_allow_html=True)

                # Display person and date
                st.write(f"**{entry['idx']}. {entry['nome']}** — Dia: {entry['data_label']}")

                # Restaurant input
                restaurant_key = entry['key']
                current_restaurant = st.session_state.restaurants.get(restaurant_key, "")

                # Display current restaurant if exists
                if current_restaurant:
                    st.write(f"🍽️ **Restaurante:** {current_restaurant}")

                # Input for restaurant
                new_restaurant = st.text_input(
                    f"Restaurante para {entry['nome']}", 
                    value=current_restaurant,
                    key=f"input_{restaurant_key}",
                    placeholder="Digite o restaurante..."
                )

                # Update session state if changed
                if new_restaurant != current_restaurant:
                    st.session_state.restaurants[restaurant_key] = new_restaurant

                st.markdown('</div>', unsafe_allow_html=True)
                st.write("")  # Add some space

            st.markdown('</div>', unsafe_allow_html=True)

        data_atual = data_fim
        current_queue_index = next_queue_index

    # Footer
    st.markdown("""
    <div class="footer-container">
        <img class="hero-gif" src="https://media1.giphy.com/media/v1.Y2lkPTc5MGI3NjExNzE0d24wZzEzcG4yZG05aDBwZ3R3M21la2o1M2EwejI4c25iaTM3cCZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/SAAMcPRfQpgyI/giphy.gif" alt="Gif divertido" />
        <p>Desenvolvido para o melhor almoço do escritório! 😄</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
