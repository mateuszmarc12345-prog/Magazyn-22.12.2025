import streamlit as st
from supabase import create_client, Client

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
    # Zabezpieczenie przed błędem unsupported operand type for +: 'NoneType' and 'int'
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

tab1, tab2, tab3 = st.tabs(["📊 Stan Magazynu", "➕ Nowy Produkt", "📂 Kategorie"])

# --- TAB 1: STAN MAGAZYNU ---
with tab1:
    st.header("Zarządzanie zapasami")
    
    szukaj = st.text_input("🔍 Szukaj po nazwie...", "")

    try:
        # Pobieranie danych z relacją do kategorii
        query = supabase.table("produkty").select("id, nazwa, liczba, cena, kategoria_id, kategorie(nazwa)")
        if szukaj:
            query = query.ilike("nazwa", f"%{szukaj}%")
        
        response = query.order("nazwa").execute()
        produkty = response.data

        if produkty:
            # Obliczanie statystyk z obsługą wartości None
            total_wartosc = sum((p.get('cena') or 0) * (p.get('liczba') or 0) for p in produkty)
            
            m1, m2 = st.columns(2)
            m1.metric("Pozycje w bazie", len(produkty))
            m2.metric("Łączna wartość", f"{total_wartosc:,.2f} PLN")

            st.markdown("---")
            
            # Nagłówki tabeli
            h1, h2, h3, h4, h5 = st.columns([3, 2, 2, 2, 1])
            h1.caption("**NAZWA**")
            h2.caption("**KATEGORIA**")
            h3.caption("**CENA**")
            h4.caption("**ILOŚĆ (ZMIANA)**")
            h5.caption("**AKCJA**")

            for p in produkty:
                with st.container():
                    col1, col2, col3, col4, col5 = st.columns([3, 2, 2, 2, 1])
                    
                    # 1. Bezpieczne formatowanie ceny (naprawa błędu NoneType.format)
                    cena_raw = p.get('cena')
                    cena_f = f"{float(cena_raw):.2f} zł" if cena_raw is not None else "0.00 zł"
                    
                    # 2. Bezpieczna ilość dla interfejsu i obliczeń
                    ilosc_raw = p.get('liczba')
                    ilosc_pokazowa = ilosc_raw if ilosc_raw is not None else 0
                    
                    kat_nazwa = p.get('kategorie', {}).get('nazwa', 'Brak') if p.get('kategorie') else "Brak"

                    col1.write(f"**{p['nazwa']}**")
                    col2.write(kat_nazwa)
                    col3.write(cena_f)
                    
                    # 3. Kontrola ilości (przyciski + / -)
                    c_btn1, c_num, c_btn2 = col4.columns([1, 2, 1])
                    if c_btn1.button("➖", key=f"m_{p['id']}"):
                        aktualizuj_stan(p['id'], ilosc_raw, -1)
                    
                    c_num.write(f"**{ilosc_pokazowa}**")
                    
                    if c_btn2.button("➕", key=f"p_{p['id']}"):
                        aktualizuj_stan(p['id'], ilosc_raw, 1)
                    
                    # 4. Usuwanie
                    if col5.button("🗑️", key=f"del_{p['id']}"):
                        usun_produkt(p['id'], p['nazwa'])
                    
                    st.divider()
        else:
            st.info("Magazyn jest pusty lub nie znaleziono produktów.")
    except Exception as e:
        st.error(f"Wystąpił nieoczekiwany błąd: {e}")

# --- TAB 2: DODAWANIE PRODUKTU ---
with tab2:
    st.header("Dodaj nowy towar")
    try:
        kat_res = supabase.table("kategorie").select("id, nazwa").execute()
        kat_map = {k['nazwa']: k['id'] for k in kat_res.data}

        if not kat_map:
            st.warning("Dodaj najpierw kategorię w zakładce 'Kategorie'!")
        else:
            with st.form("form_dodaj_prod", clear_on_submit=True):
                nazwa = st.text_input("Nazwa produktu*")
                cena = st.number_input("Cena (PLN)", min_value=0.0, value=0.0, step=0.01, format="%.2f")
                ilosc = st.number_input("Ilość początkowa", min_value=0, value=0, step=1)
                kat = st.selectbox("Kategoria", options=list(kat_map.keys()))
                
                if st.form_submit_button("Dodaj do bazy"):
                    if nazwa:
                        supabase.table("produkty").insert({
                            "nazwa": nazwa,
                            "cena": cena,
                            "liczba": ilosc,
                            "kategoria_id": kat_map[kat]
                        }).execute()
                        st.success(f"Dodano: {nazwa}")
                        st.rerun()
                    else:
                        st.error("Musisz podać nazwę produktu.")
    except Exception as e:
        st.error(f"Błąd formularza: {e}")

# --- TAB 3: KATEGORIE ---
with tab3:
    st.header("Kategorie")
    with st.form("form_kat", clear_on_submit=True):
        n_kat = st.text_input("Nowa kategoria")
        if st.form_submit_button("Zapisz kategorię"):
            if n_kat:
                supabase.table("kategorie").insert({"nazwa": n_kat}).execute()
                st.success("Dodano kategorię!")
                st.rerun()

    st.subheader("Lista kategorii")
    try:
        kat_list = supabase.table("kategorie").select("nazwa").execute().data
        if kat_list:
            for k in kat_list:
                st.text(f"• {k['nazwa']}")
    except:
        st.info("Brak kategorii.")
