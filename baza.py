import streamlit as st
from supabase import create_client, Client
import pandas as pd

# --- 1. KONFIGURACJA STRONY ---
st.set_page_config(
    page_title="System Magazynowy Pro",
    layout="wide",
    page_icon="📦"
)

# --- 2. POŁĄCZENIE Z SUPABASE ---
@st.cache_resource
def init_connection():
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        return create_client(url, key)
    except Exception as e:
        st.error("❌ Błąd połączenia. Sprawdź plik .streamlit/secrets.toml")
        st.stop()

supabase = init_connection()

# --- 3. FUNKCJE LOGIKI BIZNESOWEJ ---
def aktualizuj_stan(produkt_id, obecna_ilosc, zmiana):
    bezpieczna_ilosc = obecna_ilosc if obecna_ilosc is not None else 0
    nowa_ilosc = bezpieczna_ilosc + zmiana
    
    if nowa_ilosc >= 0:
        try:
            supabase.table("produkty").update({"liczba": nowa_ilosc}).eq("id", produkt_id).execute()
            st.rerun()
        except Exception as e:
            st.error(f"Błąd zapisu: {e}")

def usun_produkt(produkt_id, nazwa):
    try:
        supabase.table("produkty").delete().eq("id", produkt_id).execute()
        st.toast(f"Usunięto: {nazwa}")
        st.rerun()
    except Exception as e:
        st.error(f"Błąd usuwania: {e}")

def edytuj_produkt(produkt_id, nowa_nazwa, nowa_cena):
    try:
        supabase.table("produkty").update({
            "nazwa": nowa_nazwa,
            "cena": nowa_cena
        }).eq("id", produkt_id).execute()
        st.success("Zaktualizowano dane produktu!")
        st.rerun()
    except Exception as e:
        st.error(f"Błąd edycji: {e}")

# --- 4. INTERFEJS UŻYTKOWNIKA ---
st.title("📦 System Zarządzania Magazynem")

tab1, tab2, tab3, tab4 = st.tabs(["📊 Stan Magazynu", "➕ Nowy Produkt", "📂 Kategorie", "📈 Statystyki"])

# --- POBIERANIE DANYCH ---
try:
    response = supabase.table("produkty").select("id, nazwa, liczba, cena, kategoria_id, kategorie(nazwa)").order("nazwa").execute()
    wszystkie_produkty = response.data
    
    kat_res = supabase.table("kategorie").select("id, nazwa").execute()
    wszystkie_kategorie = kat_res.data
    kat_map = {k['nazwa']: k['id'] for k in wszystkie_kategorie}
except Exception as e:
    st.error(f"Błąd danych: {e}")
    wszystkie_produkty, wszystkie_kategorie, kat_map = [], [], {}

# --- TAB 1: STAN MAGAZYNU ---
with tab1:
    st.header("Zarządzanie zapasami")
    
    c1, c2 = st.columns([2, 1])
    szukaj = c1.text_input("🔍 Szukaj produktu...", "")
    filtr_kat = c2.selectbox("Kategoria", ["Wszystkie"] + [k['nazwa'] for k in wszystkie_kategorie])

    produkty_wyswietlane = wszystkie_produkty
    if szukaj:
        produkty_wyswietlane = [p for p in produkty_wyswietlane if szukaj.lower() in p['nazwa'].lower()]
    if filtr_kat != "Wszystkie":
        produkty_wyswietlane = [p for p in produkty_wyswietlane if p.get('kategorie', {}).get('nazwa') == filtr_kat]

    if produkty_wyswietlane:
        # Nagłówki tabeli
        st.markdown("---")
        h1, h2, h3, h4, h5 = st.columns([3, 2, 1.5, 3, 0.5])
        h1.caption("**NAZWA / EDYCJA**")
        h2.caption("**KATEGORIA**")
        h3.caption("**CENA**")
        h4.caption("**ZARZĄDZANIE ILOŚCIĄ**")
        h5.caption("**USUŃ**")

        for p in produkty_wyswietlane:
            with st.container():
                col1, col2, col3, col4, col5 = st.columns([3, 2, 1.5, 3, 0.5])
                
                ilosc_akt = p.get('liczba') or 0
                cena_akt = float(p.get('cena') or 0)
                nazwa_akt = p['nazwa']
                
                # Kolumna 1: Nazwa i przycisk edycji
                col1.write(f"**{nazwa_akt}**")
                expander = col1.expander("✏️ Edytuj dane")
                with expander:
                    with st.form(f"edit_form_{p['id']}"):
                        new_name = st.text_input("Nazwa", value=nazwa_akt)
                        new_price = st.number_input("Cena", value=cena_akt, step=0.01)
                        if st.form_submit_button("Zapisz zmiany"):
                            edytuj_produkt(p['id'], new_name, new_price)

                # Kolumna 2 i 3: Kategoria i Cena
                col2.write(p.get('kategorie', {}).get('nazwa', 'Brak'))
                col3.write(f"{cena_akt:.2f} zł")
                
                # Kolumna 4: Zaawansowane zarządzanie ilością
                c_display, c_plus_minus, c_input = col4.columns([1, 1, 2])
                
                c_display.write(f"Stan: **{ilosc_akt}**")
                
                # Przyciski +/- 1
                with c_plus_minus:
                    if st.button("➕", key=f"p1_{p['id']}"):
                        aktualizuj_stan(p['id'], ilosc_akt, 1)
                    if st.button("➖", key=f"m1_{p['id']}"):
                        aktualizuj_stan(p['id'], ilosc_akt, -1)
                
                # Wpisanie konkretnej ilości
                with c_input:
                    delta = st.number_input("Ilość", min_value=1, value=1, key=f"val_{p['id']}", label_visibility="collapsed")
                    btn_add, btn_sub = st.columns(2)
                    if btn_add.button("Dodaj", key=f"add_btn_{p['id']}"):
                        aktualizuj_stan(p['id'], ilosc_akt, delta)
                    if btn_sub.button("Odejmij", key=f"sub_btn_{p['id']}"):
                        aktualizuj_stan(p['id'], ilosc_akt, -delta)

                # Kolumna 5: Usuwanie
                if col5.button("🗑️", key=f"del_{p['id']}"):
                    usun_produkt(p['id'], nazwa_akt)
                
                st.divider()
    else:
        st.info("Nie znaleziono produktów.")

# --- TAB 2: NOWY PRODUKT ---
with tab2:
    st.header("Dodaj nowy towar")
    if not kat_map:
        st.warning("Dodaj najpierw kategorię!")
    else:
        with st.form("form_dodaj_prod", clear_on_submit=True):
            n_nazwa = st.text_input("Nazwa produktu*")
            n_cena = st.number_input("Cena (PLN)", min_value=0.0, step=0.01)
            n_ilosc = st.number_input("Ilość początkowa", min_value=0, step=1)
            n_kat = st.selectbox("Kategoria", options=list(kat_map.keys()))
            if st.form_submit_button("Dodaj do bazy"):
                if n_nazwa:
                    supabase.table("produkty").insert({
                        "nazwa": n_nazwa, "cena": n_cena, 
                        "liczba": n_ilosc, "kategoria_id": kat_map[n_kat]
                    }).execute()
                    st.success(f"Dodano: {n_nazwa}")
                    st.rerun()

# --- TAB 3: KATEGORIE ---
with tab3:
    st.header("Kategorie")
    with st.form("form_kat", clear_on_submit=True):
        n_kat = st.text_input("Nowa nazwa")
        if st.form_submit_button("Dodaj"):
            if n_kat:
                supabase.table("kategorie").insert({"nazwa": n_kat}).execute()
                st.rerun()
    for k in wszystkie_kategorie:
        st.text(f"• {k['nazwa']}")

# --- TAB 4: ANALITYKA ---
with tab4:
    st.header("Statystyki")
    if wszystkie_produkty:
        df = pd.DataFrame([{
            'Kategoria': p.get('kategorie', {}).get('nazwa', 'Brak'),
            'Ilość': p.get('liczba') or 0,
            'Wartość': (p.get('cena') or 0) * (p.get('liczba') or 0)
        } for p in wszystkie_produkty])
        st.bar_chart(df.groupby('Kategoria')['Ilość'].sum())
        st.metric("Całkowita wartość magazynu", f"{df['Wartość'].sum():,.2f} PLN")
