import streamlit as st
from supabase import create_client, Client

# --- KONFIGURACJA STRONY ---
st.set_page_config(page_title="Pro Magazyn", layout="wide", page_icon="📦")

# --- POŁĄCZENIE Z SUPABASE ---
try:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(url, key)
except Exception as e:
    st.error("Błąd konfiguracji kluczy API. Sprawdź plik .streamlit/secrets.toml")
    st.stop()

# --- FUNKCJE POMOCNICZE ---
def zmien_ilosc(produkt_id, nowa_ilosc):
    if nowa_ilosc >= 0:
        supabase.table("produkty").update({"liczba": nowa_ilosc}).eq("id", produkt_id).execute()
        st.rerun()

def usun_produkt(produkt_id):
    supabase.table("produkty").delete().eq("id", produkt_id).execute()
    st.rerun()

st.title("📦 System Zarządzania Magazynem")

tab1, tab2, tab3 = st.tabs(["📊 Podgląd i Zarządzanie", "➕ Dodaj Produkt", "📂 Kategorie"])

# --- TAB 1: PODGLĄD I ZARZĄDZANIE ---
with tab1:
    st.header("Aktualny Stan Magazynowy")
    
    # Wyszukiwarka
    search_query = st.text_input("🔍 Szukaj produktu po nazwie...")
    
    try:
        query = supabase.table("produkty").select("id, nazwa, liczba, cena, kategorie(nazwa)")
        if search_query:
            query = query.ilike("nazwa", f"%{search_query}%")
        
        res = query.execute()
        dane = res.data

        if dane:
            # Obliczanie statystyk
            total_val = sum((item['cena'] or 0) * (item['liczba'] or 0) for item in dane)
            
            col1, col2 = st.columns(2)
            col1.metric("Liczba pozycji", len(dane))
            col2.metric("Łączna wartość magazynu", f"{total_val:,.2f} PLN")

            st.write("---")

            # Nagłówki tabeli
            h_col1, h_col2, h_col3, h_col4, h_col5 = st.columns([3, 2, 2, 2, 2])
            h_col1.write("**Produkt**")
            h_col2.write("**Kategoria**")
            h_col3.write("**Cena**")
            h_col4.write("**Ilość (Edycja)**")
            h_col5.write("**Akcje**")

            for item in dane:
                with st.container():
                    c1, c2, c3, c4, c5 = st.columns([3, 2, 2, 2, 2])
                    
                    c1.write(item['nazwa'])
                    c2.write(item['kategorie']['nazwa'] if item['kategorie'] else "Brak")
                    c3.write(f"{item['cena']:.2f} zł")
                    
                    # Edycja ilości
                    col_minus, col_num, col_plus = c4.columns([1, 2, 1])
                    if col_minus.button("➖", key=f"min_{item['id']}"):
                        zmien_ilosc(item['id'], item['liczba'] - 1)
                    col_num.write(f"**{item['liczba']}**")
                    if col_plus.button("➕", key=f"plus_{item['id']}"):
                        zmien_ilosc(item['id'], item['liczba'] + 1)
                    
                    # Usuwanie
                    if c5.button("🗑️ Usuń", key=f"del_{item['id']}", type="secondary"):
                        usun_produkt(item['id'])
                    st.divider()
        else:
            st.info("Brak produktów spełniających kryteria.")
    except Exception as e:
        st.error(f"Błąd pobierania danych: {e}")

# --- TAB 2: DODAWANIE PRODUKTU ---
with tab2:
    st.header("Dodaj Nowy Produkt")
    try:
        kat_res = supabase.table("kategorie").select("id, nazwa").execute()
        kategorie_map = {k['nazwa']: k['id'] for k in kat_res.data}

        if not kategorie_map:
            st.warning("Najpierw musisz dodać przynajmniej jedną kategorię.")
        else:
            with st.form("add_product_form", clear_on_submit=True):
                n = st.text_input("Nazwa produktu*")
                l = st.number_input("Ilość na start", min_value=0, step=1)
                c = st.number_input("Cena jednostkowa (PLN)", min_value=0.0, format="%.2f")
                k = st.selectbox("Wybierz kategorię", options=list(kategorie_map.keys()))
                
                if st.form_submit_button("✨ Dodaj do bazy"):
                    if n:
                        supabase.table("produkty").insert({
                            "nazwa": n, "liczba": l, "cena": c, "kategoria_id": kategorie_map[k]
                        }).execute()
                        st.success(f"Produkt {n} został dodany!")
                        st.rerun()
                    else:
                        st.error("Nazwa produktu jest wymagana!")
    except Exception as e:
        st.error(f"Błąd formularza: {e}")

# --- TAB 3: KATEGORIE ---
with tab3:
    st.header("Zarządzanie Kategoriami")
    with st.form("add_cat_form", clear_on_submit=True):
        new_cat = st.text_input("Nazwa nowej kategorii")
        if st.form_submit_button("Dodaj kategorię"):
            if new_cat:
                supabase.table("kategorie").insert({"nazwa": new_cat}).execute()
                st.success("Dodano kategorię!")
                st.rerun()
    
    st.write("### Twoje Kategorie")
    try:
        kat_list = supabase.table("kategorie").select("nazwa").execute()
        for kl in kat_list.data:
            st.text(f"• {kl['nazwa']}")
    except:
        pass
