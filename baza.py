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

# --- 4. INTERFEJS UŻYTKOWNIKA ---
st.title("📦 System Zarządzania Magazynem")

tab1, tab2, tab3, tab4 = st.tabs(["📊 Stan Magazynu", "➕ Nowy Produkt", "📂 Kategorie", "📈 Statystyki"])

# --- POBIERANIE DANYCH (Wspólne dla Tab 1 i Tab 4) ---
try:
    response = supabase.table("produkty").select("id, nazwa, liczba, cena, kategoria_id, kategorie(nazwa)").order("nazwa").execute()
    wszystkie_produkty = response.data
    
    kat_res = supabase.table("kategorie").select("id, nazwa").execute()
    wszystkie_kategorie = kat_res.data
    kat_map = {k['nazwa']: k['id'] for k in wszystkie_kategorie}
except Exception as e:
    st.error(f"Błąd pobierania danych: {e}")
    wszystkie_produkty = []
    wszystkie_kategorie = []

# --- TAB 1: STAN MAGAZYNU ---
with tab1:
    st.header("Zarządzanie zapasami")
    
    c1, c2 = st.columns([2, 1])
    szukaj = c1.text_input("🔍 Szukaj po nazwie...", "")
    filtr_kat = c2.selectbox("Filter kategorii", ["Wszystkie"] + [k['nazwa'] for k in wszystkie_kategorie])

    # Filtrowanie lokalne (oszczędza zapytania do bazy)
    produkty_wyswietlane = wszystkie_produkty
    if szukaj:
        produkty_wyswietlane = [p for p in produkty_wyswietlane if szukaj.lower() in p['nazwa'].lower()]
    if filtr_kat != "Wszystkie":
        produkty_wyswietlane = [p for p in produkty_wyswietlane if p.get('kategorie', {}).get('nazwa') == filtr_kat]

    if produkty_wyswietlane:
        # Statystyki szybkiego podglądu
        total_wartosc = sum((p.get('cena') or 0) * (p.get('liczba') or 0) for p in produkty_wyswietlane)
        m1, m2, m3 = st.columns(3)
        m1.metric("Pozycje", len(produkty_wyswietlane))
        m2.metric("Łączna wartość", f"{total_wartosc:,.2f} PLN")
        
        # Funkcja eksportu do CSV
        df_csv = pd.DataFrame([{
            'Nazwa': p['nazwa'],
            'Kategoria': p.get('kategorie', {}).get('nazwa', 'Brak'),
            'Cena': p['cena'],
            'Ilość': p['liczba'],
            'Wartość': (p['cena'] or 0) * (p['liczba'] or 0)
        } for p in produkty_wyswietlane])
        
        st.download_button("📥 Pobierz listę jako CSV", df_csv.to_csv(index=False).encode('utf-8'), "magazyn.csv", "text/csv")

        st.markdown("---")
        
        # Nagłówki
        h1, h2, h3, h4, h5 = st.columns([3, 2, 2, 2, 1])
        h1.caption("**NAZWA**")
        h2.caption("**KATEGORIA**")
        h3.caption("**CENA**")
        h4.caption("**ILOŚĆ (ZMIANA)**")
        h5.caption("**AKCJA**")

        for p in produkty_wyswietlane:
            with st.container():
                col1, col2, col3, col4, col5 = st.columns([3, 2, 2, 2, 1])
                
                # Alerty kolorystyczne dla ilości
                ilosc = p.get('liczba') or 0
                kolor = "🔴" if ilosc <= 5 else "🟢"
                
                cena_f = f"{float(p.get('cena') or 0):.2f} zł"
                kat_nazwa = p.get('kategorie', {}).get('nazwa', 'Brak')

                col1.write(f"{kolor} **{p['nazwa']}**")
                col2.write(kat_nazwa)
                col3.write(cena_f)
                
                # Przycisk +/-
                c_btn1, c_num, c_btn2 = col4.columns([1, 1, 1])
                if c_btn1.button("➖", key=f"m_{p['id']}"):
                    aktualizuj_stan(p['id'], ilosc, -1)
                c_num.write(f"**{ilosc}**")
                if c_btn2.button("➕", key=f"p_{p['id']}"):
                    aktualizuj_stan(p['id'], ilosc, 1)
                
                if col5.button("🗑️", key=f"del_{p['id']}"):
                    usun_produkt(p['id'], p['nazwa'])
                st.divider()
    else:
        st.info("Brak produktów spełniających kryteria.")

# --- TAB 2: DODAWANIE PRODUKTU ---
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
    st.header("Zarządzanie kategoriami")
    with st.form("form_kat", clear_on_submit=True):
        n_kat = st.text_input("Nowa nazwa kategorii")
        if st.form_submit_button("Zapisz kategorię"):
            if n_kat:
                supabase.table("kategorie").insert({"nazwa": n_kat}).execute()
                st.rerun()

    st.subheader("Istniejące kategorie")
    for k in wszystkie_kategorie:
        st.text(f"• {k['nazwa']}")

# --- TAB 4: STATYSTYKI ---
with tab4:
    st.header("Analityka zapasów")
    if wszystkie_produkty:
        df = pd.DataFrame([{
            'Kategoria': p.get('kategorie', {}).get('nazwa', 'Brak'),
            'Ilość': p.get('liczba') or 0,
            'Wartość': (p.get('cena') or 0) * (p.get('liczba') or 0)
        } for p in wszystkie_produkty])

        col_left, col_right = st.columns(2)
        
        with col_left:
            st.subheader("Ilość towaru wg kategorii")
            # Agregacja danych do wykresu
            chart_data = df.groupby('Kategoria')['Ilość'].sum()
            st.bar_chart(chart_data)

        with col_right:
            st.subheader("Wartość towaru (PLN)")
            val_data = df.groupby('Kategoria')['Wartość'].sum()
            st.area_chart(val_data)
            
        st.subheader("Produkty wymagające zamówienia (poniżej 5 sztuk)")
        braki = [p for p in wszystkie_produkty if (p.get('liczba') or 0) <= 5]
        if braki:
            st.table(pd.DataFrame(braki)[['nazwa', 'liczba']])
        else:
            st.success("Wszystkie stany są optymalne!")
    else:
        st.info("Brak danych do analizy.")
