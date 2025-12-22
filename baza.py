import streamlit as st
from supabase import create_client, Client

# --- KONFIGURACJA STRONY ---
st.set_page_config(page_title="Magazyn Supabase", layout="centered")

# --- POŁĄCZENIE Z SUPABASE ---
try:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(url, key)
except Exception as e:
    st.error("Błąd konfiguracji kluczy API. Sprawdź plik secrets.")
    st.stop()

st.title("📦 Zarządzanie Produktami i Kategoriami")

# Zakładki
tab1, tab2, tab3 = st.tabs(["Dodaj Produkt", "Dodaj Kategorię", "Podgląd Bazy"])

# --- TAB 1: DODAWANIE PRODUKTU ---
with tab1:
    st.header("Nowy Produkt")
    
    try:
        # Zmiana na małe litery: 'kategorie'
        kat_res = supabase.table("kategorie").select("id, nazwa").execute()
        kategorie_opcje = {item['nazwa']: item['id'] for item in kat_res.data}
        
        if not kategorie_opcje:
            st.warning("Najpierw dodaj przynajmniej jedną kategorię!")
        else:
            with st.form("form_produkt"):
                nazwa_p = st.text_input("Nazwa produktu")
                liczba_p = st.number_input("Liczba sztuk", min_value=0, step=1)
                cena_p = st.number_input("Cena (PLN)", min_value=0.0, step=0.01, format="%.2f")
                wybrana_kat = st.selectbox("Kategoria", options=list(kategorie_opcje.keys()))
                
                btn_produkt = st.form_submit_button("Zapisz produkt")
                
                if btn_produkt:
                    if nazwa_p:
                        nowy_produkt = {
                            "nazwa": nazwa_p,
                            "liczba": liczba_p,
                            "cena": cena_p,
                            "kategoria_id": kategorie_opcje[wybrana_kat] # Małe litery
                        }
                        # Zmiana na małe litery: 'produkty'
                        supabase.table("produkty").insert(nowy_produkt).execute()
                        st.success(f"Dodano produkt: {nazwa_p}")
                    else:
                        st.error("Nazwa produktu nie może być pusta.")
    except Exception as e:
        st.error(f"Błąd: {e}")

# --- TAB 2: DODAWANIE KATEGORII ---
with tab2:
    st.header("Nowa Kategoria")
    with st.form("form_kategoria"):
        nazwa_k = st.text_input("Nazwa kategorii")
        opis_k = st.text_area("Opis kategorii")
        
        btn_kategoria = st.form_submit_button("Zapisz kategorię")
        
        if btn_kategoria:
            if nazwa_k:
                # Zmiana na małe litery: 'kategorie'
                nowa_kat = {"nazwa": nazwa_k, "opis": opis_k}
                supabase.table("kategorie").insert(nowa_kat).execute()
                st.success(f"Dodano kategorię: {nazwa_k}")
                st.rerun()
            else:
                st.error("Nazwa kategorii jest wymagana.")

# --- TAB 3: PODGLĄD BAZY ---
with tab3:
    st.header("Aktualny stan magazynu")
    try:
        # Zmiana na małe litery i poprawne złączenie (JOIN)
        widok = supabase.table("produkty").select("nazwa, liczba, cena, kategorie(nazwa)").execute()
        
        if widok.data:
            formatted_data = []
            for item in widok.data:
                formatted_data.append({
                    "Produkt": item['nazwa'],
                    "Ilość": item['liczba'],
                    "Cena": f"{item['cena']:.2f} zł",
                    "Kategoria": item['kategorie']['nazwa'] if item.get('kategorie') else "Brak"
                })
            st.table(formatted_data)
        else:
            st.info("Baza danych jest pusta.")
    except Exception as e:
        st.error(f"Błąd wyświetlania danych: {e}")
