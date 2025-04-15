import streamlit as st
import sqlite3
from datetime import datetime, timedelta, date
import calendar

st.set_page_config(page_title="Stall App", layout="centered")

st.markdown("""
    <style>
        .stApp { background-color: #006400; }  /* Dunkleres Grün für besseren Kontrast */
        .highlight-event {
            border: 2px solid gold;
            padding: 4px;
            border-radius: 6px;
            display: inline-block;
        }
        .calendar-day {
            display: inline-block;
            width: 40px;
            text-align: center;
            margin: 2px;
            font-size: 14px;
        }
        .own-duty {
            background-color: #ccffcc;
            border-radius: 4px;
            padding: 2px;
        }
        .occupied {
            background-color: #ffcccc;
            border-radius: 4px;
            padding: 2px;
        }
    </style>
""", unsafe_allow_html=True)

DB = "stall_app_final_full.db"

def get_connection():
    return sqlite3.connect(DB, check_same_thread=False)

def login_user(username, password):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id, role FROM users WHERE username=? AND password=?", (username, password))
        return cur.fetchone()

def get_all_duties():
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT users.username, muck_duties.date
            FROM muck_duties
            JOIN users ON users.id = muck_duties.user_id
            ORDER BY muck_duties.date ASC
        """)
        return cur.fetchall()

def get_month_events(year, month):
    start = date(year, month, 1)
    end = date(year, month, calendar.monthrange(year, month)[1])
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT date FROM calendar_comments WHERE date BETWEEN ? AND ?", (start.isoformat(), end.isoformat()))
        return set(row[0] for row in cur.fetchall())

def get_all_muck_dates():
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT date FROM muck_duties")
        return [row[0] for row in cur.fetchall()]

# Öffentliche Ansicht der Mistdienste
st.title("🐴 Stallverwaltung – Mistdienstübersicht")
all_duties = get_all_duties()
for username, duty_date in all_duties:
    st.write(f"🧹 {duty_date} – {username}")

st.divider()

if "user" not in st.session_state:
    st.subheader("🔐 Login für Änderungen")
    username = st.text_input("Benutzername")
    password = st.text_input("Passwort", type="password")
    if st.button("Einloggen"):
        user = login_user(username, password)
        if user:
            st.session_state.user = {"id": user[0], "role": user[1], "username": username}
            st.rerun()
        else:
            st.error("Login fehlgeschlagen")
else:
    user = st.session_state.user
    st.success(f"Eingeloggt als {user['username']} ({user['role']})")
    if st.button("Logout"):
        del st.session_state.user
        st.rerun()

    def get_horses(user_id):
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT name FROM horses WHERE owner_id=?", (user_id,))
            return [row[0] for row in cur.fetchall()]

    def get_muck_duties(user_id):
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT id, date FROM muck_duties WHERE user_id=?", (user_id,))
            return cur.fetchall()

    def get_tomorrow_duties(user_id):
        tomorrow = (date.today() + timedelta(days=1)).isoformat()
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT date FROM muck_duties WHERE user_id=? AND date=?", (user_id, tomorrow))
            return cur.fetchall()

    def add_duty(user_id, duty_date):
    # Überprüfe, ob der Tag bereits vergeben ist
        with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM muck_duties WHERE date=?", (duty_date,))
        existing_entry = cur.fetchone()

        if existing_entry:
        # Zeige eine Fehlermeldung an, wenn der Tag bereits gebucht ist
        st.error(f"❌ Der Tag {duty_date} ist bereits gebucht!")
        else:
        # Wenn der Tag frei ist, füge den Eintrag hinzu
            with get_connection() as conn:
            cur = conn.cursor()
            cur.execute("INSERT INTO muck_duties (user_id, date) VALUES (?, ?)", (user_id, duty_date))
            conn.commit()
            st.success(f"✅ Mistdienst für {duty_date} erfolgreich eingetragen!")


    def delete_duty(entry_id):
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM muck_duties WHERE id=?", (entry_id,))
            conn.commit()

    def update_duty(entry_id, new_date):
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute("UPDATE muck_duties SET date=? WHERE id=?", (new_date, entry_id))
            conn.commit()

    def get_user_payment(user_id):
        this_month = datetime.today().strftime("%Y-%m")
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT status FROM payments WHERE user_id=? AND month=?", (user_id, this_month))
            result = cur.fetchone()
            return result[0] if result else "offen"

    if user["role"] == "einsteller":
        st.header("🧹 Mein Mistdienst")

        if get_tomorrow_duties(user["id"]):
            st.warning("❗ Du hast morgen Mistdienst!")

        horses = get_horses(user["id"])
        pflicht_pro_woche = len(horses) * 2
        today = date.today()
        start_week = today - timedelta(days=today.weekday())
        end_week = start_week + timedelta(days=6)

        duties = get_muck_duties(user["id"])
        anzahl_diese_woche = sum(start_week <= datetime.strptime(d[1], "%Y-%m-%d").date() <= end_week for d in duties)

        st.info(f"Diese Woche eingetragen: {anzahl_diese_woche} / {pflicht_pro_woche} Dienste")

        status = get_user_payment(user["id"])
        st.info(f"💰 Zahlungsstatus für {datetime.today().strftime('%B %Y')}: **{status.upper()}**")

        st.subheader("Meine Einträge")
        for entry_id, duty_date in duties:
            col1, col2, col3 = st.columns([3, 3, 1])
            with col1:
                st.write(duty_date)
            with col2:
                new_date = st.date_input("Ändern auf", value=datetime.fromisoformat(duty_date).date(), key=f"d{entry_id}")
            with col3:
                if st.button("Speichern", key=f"u{entry_id}"):
                    update_duty(entry_id, new_date.isoformat())
                    st.rerun()
                if st.button("🗑️", key=f"x{entry_id}"):
                    delete_duty(entry_id)
                    st.rerun()

        st.subheader("Neuen Mistdienst eintragen")
        new_duty_date = st.date_input("Datum wählen", min_value=date.today())
        if st.button("Eintragen"):
            add_duty(user["id"], new_duty_date.isoformat())
            st.success("Mistdienst gespeichert")
            st.rerun()

    if user["role"] == "admin":
        def add_user_with_horses(username, password, horses):
            with get_connection() as conn:
                cur = conn.cursor()
                cur.execute("INSERT INTO users (username, password, role) VALUES (?, ?, 'einsteller')", (username, password))
                user_id = cur.lastrowid
                for horse in horses:
                    cur.execute("INSERT INTO horses (name, owner_id) VALUES (?, ?)", (horse, user_id))
                conn.commit()

        def update_payment(user_id, month, status):
            with get_connection() as conn:
                cur = conn.cursor()
                cur.execute("SELECT id FROM payments WHERE user_id=? AND month=?", (user_id, month))
                existing = cur.fetchone()
                if existing:
                    cur.execute("UPDATE payments SET status=? WHERE user_id=? AND month=?", (status, user_id, month))
                else:
                    cur.execute("INSERT INTO payments (user_id, month, status) VALUES (?, ?, ?)", (user_id, month, status))
                conn.commit()

        def get_all_payments():
            this_month = datetime.today().strftime("%Y-%m")
            with get_connection() as conn:
                cur = conn.cursor()
                cur.execute("""
                    SELECT u.id, u.username, COALESCE(p.month, ?), COALESCE(p.status, 'offen')
                    FROM users u
                    LEFT JOIN payments p ON u.id = p.user_id AND p.month = ?
                    WHERE u.role = 'einsteller'
                """, (this_month, this_month))
                return cur.fetchall()

        def add_calendar_comment(date_str, comment):
            with get_connection() as conn:
                cur = conn.cursor()
                cur.execute("INSERT INTO calendar_comments (date, comment, created_by) VALUES (?, ?, ?)", (date_str, comment, user["id"]))
                conn.commit()

        def get_all_users():
            with get_connection() as conn:
                cur = conn.cursor()
                cur.execute("SELECT id, username FROM users WHERE role='einsteller'")
                return cur.fetchall()

        def delete_user_and_data(user_id):
            with get_connection() as conn:
                cur = conn.cursor()
                cur.execute("DELETE FROM muck_duties WHERE user_id=?", (user_id,))
                cur.execute("DELETE FROM horses WHERE owner_id=?", (user_id,))
                cur.execute("DELETE FROM payments WHERE user_id=?", (user_id,))
                cur.execute("DELETE FROM users WHERE id=?", (user_id,))
                conn.commit()

        st.header("⚙️ Adminbereich")

        st.subheader("Neuen Einsteller + Pferde anlegen")
        new_user = st.text_input("Benutzername")
        new_pw = st.text_input("Passwort", type="password")
        new_horses = st.text_area("Pferdenamen (jeweils eine Zeile)").splitlines()
        if st.button("Anlegen"):
            add_user_with_horses(new_user, new_pw, new_horses)
            st.success("Nutzer mit Pferden angelegt")

        st.subheader("Zahlungsstatus setzen")
        payment_data = get_all_payments()
        for uid, uname, monat, status in payment_data:
            st.write(f"{uname} – {monat} – aktuell: {status}")
            new_status = st.selectbox("Status setzen", ["offen", "bezahlt"], index=0, key=f"{uname}-{monat}")
            if st.button("Speichern", key=f"s{uname}-{monat}"):
                update_payment(uid, monat, new_status)
                st.rerun()

        st.subheader("Einsteller löschen")
        all_users = get_all_users()
        for uid, uname in all_users:
            col1, col2 = st.columns([4,1])
            with col1:
                st.write(uname)
            with col2:
                if st.button("❌ Löschen", key=f"del{uid}"):
                    delete_user_and_data(uid)
                    st.success(f"{uname} gelöscht")
                    st.rerun()

        st.subheader("Kalender-Kommentar hinzufügen")
        comment_date = st.date_input("Datum")
        comment_text = st.text_input("Kommentar")
        if st.button("Speichern Kommentar"):
            add_calendar_comment(comment_date.isoformat(), comment_text)
            st.success("Kommentar gespeichert")
            st.rerun()
    st.subheader("📅 Monatsübersicht")

    today = date.today()
    events = get_month_events(today.year, today.month)
    all_muck_dates = set(get_all_muck_dates())
    own_dates = set(d[1] for d in get_muck_duties(user["id"])) if user["role"] == "einsteller" else set()

    cal = calendar.Calendar()
    weeks = cal.monthdayscalendar(today.year, today.month)
    for week in weeks:
        row = ""
        for day in week:
            if day == 0:
                row += "<span class='calendar-day'> </span>"
            else:
                dstr = f"{today.year}-{today.month:02d}-{day:02d}"
                classes = ["calendar-day"]
                if dstr in events:
                    classes.append("highlight-event")
                if dstr in own_dates:
                    classes.append("own-duty")
                elif dstr in all_muck_dates:
                    classes.append("occupied")
                row += f"<span class='{' '.join(classes)}'>{day:02d}</span>"
        st.markdown(row, unsafe_allow_html=True)
