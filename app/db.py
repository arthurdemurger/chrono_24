import sqlite3
def init_db():
    with sqlite3.connect("data/laps_data.db") as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS laps (
                id INTEGER PRIMARY KEY,
                type TEXT,
                lap_number INTEGER,
                rider_name TEXT,
                lap_time TEXT,
                time_diff TEXT,
                cumulative_time TEXT,
                lap_duration TEXT
            )
        ''')
        conn.commit()

def store_lap_data(lap_type, lap_number, rider_name, lap_time, time_diff, cumulative_time, lap_duration):
    with sqlite3.connect("data/laps_data.db") as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO laps
            (type, lap_number, rider_name, lap_time, time_diff, cumulative_time, lap_duration)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (lap_type, lap_number, rider_name, lap_time, time_diff, str(cumulative_time), str(lap_duration)))
        conn.commit()

def remove_last_db_entry(lap_type):
    with sqlite3.connect("data/laps_data.db") as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id FROM laps
            WHERE type = ?
            ORDER BY id DESC
            LIMIT 1
        """, (lap_type,))
        row = cursor.fetchone()
        if row:
            last_id = row[0]
            cursor.execute("DELETE FROM laps WHERE id = ?", (last_id,))
            conn.commit()

def clear_all_laps_db():
    with sqlite3.connect("data/laps_data.db") as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM laps")
        conn.commit()

def reload_from_db():
    with sqlite3.connect("data/laps_data.db") as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT lap_number, rider_name, lap_time, time_diff, lap_duration, type
            FROM laps
            ORDER BY lap_number ASC, id ASC
        """)
        rows = cursor.fetchall()
    data = []
    for row in rows:
        lap_number, rider_name, lap_time, time_diff, lap_duration, lap_type = row
        data.append((int(lap_number), rider_name, lap_time, time_diff, lap_duration, lap_type))
    return data

def fetch_stats_for_all():
    with sqlite3.connect("data/laps_data.db") as conn:
        cursor = conn.cursor()

        cursor.execute("SELECT AVG(lap_duration), MIN(lap_duration), COUNT(*) FROM laps WHERE type='Vélo 1'")
        row_bike1 = cursor.fetchone()
        avg_bike1 = float(row_bike1[0]) if row_bike1 and row_bike1[0] else 0
        min_bike1 = float(row_bike1[1]) if row_bike1 and row_bike1[1] else 0
        count_bike1 = int(row_bike1[2]) if row_bike1 and row_bike1[2] else 0

        cursor.execute("SELECT AVG(lap_duration), MIN(lap_duration), COUNT(*) FROM laps WHERE type='Peloton'")
        row_peloton = cursor.fetchone()
        avg_peloton = float(row_peloton[0]) if row_peloton and row_peloton[0] else 0
        min_peloton = float(row_peloton[1]) if row_peloton and row_peloton[1] else 0
        count_peloton = int(row_peloton[2]) if row_peloton and row_peloton[2] else 0

    return (avg_bike1, min_bike1, count_bike1, avg_peloton, min_peloton, count_peloton)

def fetch_stats_per_rider():
    with sqlite3.connect("data/laps_data.db") as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT rider_name, COUNT(*), AVG(lap_duration), MIN(lap_duration)
            FROM laps
            WHERE type='Vélo 1'
            GROUP BY rider_name
        """)
        rows = cursor.fetchall()
    return rows
