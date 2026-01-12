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
    filtr_kat = c2.selectbox("Filtr kategorii", ["Wszystkie"] + [k['nazwa'] for k in wszystkie_kategorie])

    produkty_wyswietlane = wszystkie_produkty
    if szukaj:
        produkty_wyswietlane = [p for p in produkty_wyswietlane if szukaj.lower() in p['nazwa'].lower()]
    if filtr_kat != "Wszystkie":
        produkty_wyswietlane = [p for p in produkty_wyswietlane if p.get('kategorie', {}).get('nazwa') == filtr_kat]

    if produkty_wyswietlane:
        st.markdown("---")
        h1, h2, h3, h4, h5 = st.columns([3, 1.5, 1.5, 3.5, 0.5])
        h1.caption("**STATUS / NAZWA**")
        h2.caption("**KATEGORIA**")
        h3.caption("**CENA**")
        h4.caption("**ZARZĄDZANIE ILOŚCIĄ**")
        h5.caption("**USUŃ**")

        for p in produkty_wyswietlane:
            with st.container():
                col1, col2, col3, col4, col5 = st.columns([3, 1.5, 1.5, 3.5, 0.5])
                
                ilosc_akt = p.get('liczba') or 0
                cena_akt = float(p.get('cena') or 0)
                
                # Przywrócenie znaczników statusu
                status_ikonka = "🔴" if ilosc_akt <= 5 else "🟢"
                label_status = " (ZAMÓW!)" if ilosc_akt <= 5 else ""
                
                # Kolumna 1: Status i Edycja
                col1.write(f"{status_ikonka} **{p['nazwa']}**{label_status}")
                with col1.expander("✏️ Edytuj nazwę/cenę"):
                    with st.form(f"edit_{p['id']}"):
                        n_n = st.text_input("Nazwa", value=p['nazwa'])
                        n_c = st.number_input("Cena", value=cena_akt)
                        if st.form_submit_button("Zapisz"):
                            edytuj_produkt(p['id'], n_n, n_c)

                col2.write(p.get('kategorie', {}).get('nazwa', 'Brak'))
                col3.write(f"{cena_akt:.2f} zł")
                
                # Kolumna 4: Zarządzanie ilością (Plus/Minus oraz Pole wpisywania)
                c_stan, c_quick, c_input = col4.columns([1, 0.8, 2.2])
                c_stan.write(f"Stan: **{ilosc_akt}**")
                
                with c_quick:
                    if st.button("➕", key=f"p_{p['id']}"): aktualizuj_stan(p['id'], ilosc_akt, 1)
                    if st.button("➖", key=f"m_{p['id']}"): aktualizuj_stan(p['id'], ilosc_akt, -1)
                
                with c_input:
                    val = st.number_input("Ilość", min_value=1, value=1, key=f"in_{p['id']}", label_visibility="collapsed")
                    b1, b2 = st.columns(2)
                    if b1.button("Dodaj", key=f"add_{p['id']}"): aktualizuj_stan(p['id'], ilosc_akt, val)
                    if b2.button("Odejmij", key=f"sub_{p['id']}"): aktualizuj_stan(p['id'], ilosc_akt, -val)

                if col5.button("🗑️", key=f"del_{p['id']}"):
                    usun_produkt(p['id'], p['nazwa'])
                st.divider()
    else:
        st.info("Brak produktów.")

# --- TAB 2: NOWY PRODUKT ---
with tab2:
    st.header("Dodaj nowy towar")
    if not kat_map: st.warning("Dodaj kategorię!")
    else:
        with st.form("new_p", clear_on_submit=True):
            n_nazwa = st.text_input("Nazwa*")
            n_cena = st.number_input("Cena", min_value=0.0)
            n_ilosc = st.number_input("Ilość", min_value=0)
            n_kat = st.selectbox("Kategoria", options=list(kat_map.keys()))
            if st.form_submit_button("Dodaj"):
                if n_nazwa:
                    supabase.table("produkty").insert({"nazwa": n_nazwa, "cena": n_cena, "liczba": n_ilosc, "kategoria_id": kat_map[n_kat]}).execute()
                    st.rerun()

# --- TAB 3: KATEGORIE ---
with tab3:
    st.header("Kategorie")
    with st.form("new_k"):
        n_k = st.text_input("Nazwa kategorii")
        if st.form_submit_button("Dodaj"):
            if n_k: supabase.table("kategorie").insert({"nazwa": n_k}).execute(); st.rerun()
    for k in wszystkie_kategorie: st.text(f"• {k['nazwa']}")

# --- TAB 4: STATYSTYKI ---
with tab4:
    st.header("📈 Statystyki i Raporty")
    if wszystkie_produkty:
        df = pd.DataFrame([{
            'Nazwa': p['nazwa'],
            'Kategoria': p.get('kategorie', {}).get('nazwa', 'Brak'),
            'Ilość': p.get('liczba') or 0,
            'Wartość': (p.get('liczba') or 0) * float(p.get('cena') or 0)
        } for p in wszystkie_produkty])

        m1, m2, m3 = st.columns(3)
        m1.metric("Pozycje", len(df))
        m2.metric("Wartość magazynu", f"{df['Wartość'].sum():,.2f} PLN")
        m3.metric("Łączna liczba sztuk", int(df['Ilość'].sum()))

        st.markdown("---")
        c_l, c_r = st.columns(2)
        c_l.subheader("Ilość wg kategorii")
        c_l.bar_chart(df.groupby('Kategoria')['Ilość'].sum())
        c_r.subheader("Wartość wg kategorii")
        c_r.area_chart(df.groupby('Kategoria')['Wartość'].sum())

        st.subheader("⚠️ Produkty do zamówienia (poniżej 5 szt.)")
        braki = df[df['Ilość'] <= 5].sort_values('Ilość')
        if not braki.empty:
            st.dataframe(braki[['Nazwa', 'Ilość', 'Kategoria']], use_container_width=True)
        else:
            st.success("Stany są w normie.")
