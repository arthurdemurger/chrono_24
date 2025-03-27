import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
import time
import sqlite3
import csv
import math
from datetime import timedelta
import json

class CyclingEventApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Chronomètre 24h - Vélo du Bois de la Cambre")
        self.root.geometry("1000x700")
        input_file = 'coordinates_transformed.json'

        # 1. Define a custom style for ttk.LabelFrame (to mimic a 'bold' label font)
        self.style = ttk.Style(self.root)
        self.style.configure("Bold.TLabelframe.Label", font=("Helvetica", 12, "bold"))

      # For map simulation
        self.simulation_running = False
        self.simulation_start_time = None
        self.simulation_dot = None

        # Load coordinates from the pre-calculated JSON file
        self.load_coordinates()

    def load_coordinates(self):
        """Loads pre-calculated coordinates from the JSON file."""
        input_file = 'coordinates_transformed.json'
        with open(input_file, 'r') as f:
            self.coordinates = json.load(f)
        self.simulation_index = 0  # To track the current position in the coordinates

        # -----------------------------
        # 2. Core State & Configuration
        # -----------------------------
        self.start_time = None
        self.last_peloton_time = None
        self.last_rouleur_1_time = None

        # Lap lists: each lap stored as: (lap_number, rider, lap_time_str, time_diff_str, lap_duration_str)
        self.rouleur_1_laps = []
        self.peloton_laps = []

        self.total_rouleur_1 = 0
        self.total_peloton = 0
        self.MIN_LAP_TIME = 30

        self.riders = [
            "Lionceau", "Tarpan", "Tamarin", "Ouandji", "Pajero", "Bengali",
            "Kitfox", "Banteng", "Xérus", "Capybara", "Mustela", "Aquila",
            "Chaoui", "Steenbock", "Lycaon", "Kowari", "Jaco", "Markhor",
            "Alaskan", "Chikaree", "Margay", "Mink", "Springbok"
        ]

        # Initialize DB and build UI
        self.init_db()
        self.build_ui()

    # -----------------------------
    # 2. Database Initialization
    # -----------------------------
    def init_db(self):
        with sqlite3.connect('laps_data.db') as conn:
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

    # -----------------------------
    # 3. UI Building
    # -----------------------------
    def build_ui(self):
        # Row 0: Top Frame
        top_frame = ttk.Frame(self.root)
        top_frame.grid(row=0, column=0, columnspan=4, pady=10)

        self.label_elapsed = ttk.Label(top_frame, text="00:00:00", font=("Helvetica", 24))
        self.label_elapsed.pack(side="left", padx=20)

        start_button = ttk.Button(top_frame, text="Démarrer 24h", command=self.start_24h)
        start_button.pack(side="left", padx=20)

        self.label_rouleur_1_total = ttk.Label(top_frame, text="Total Rosaire (Bike 1): 0", font=("Helvetica", 12))
        self.label_rouleur_1_total.pack(side="left", padx=20)

        self.label_peloton_total = ttk.Label(top_frame, text="Total Peloton: 0", font=("Helvetica", 12))
        self.label_peloton_total.pack(side="left", padx=20)

        # Row 1: Buttons Frame
        buttons_frame = ttk.Frame(self.root)
        buttons_frame.grid(row=1, column=0, columnspan=4, pady=10)

        btn_rouleur1 = ttk.Button(buttons_frame, text="Tour Vélo 1", command=self.record_rouleur_1)
        btn_rouleur1.grid(row=0, column=0, padx=10)

        btn_peloton = ttk.Button(buttons_frame, text="Tour Peloton", command=self.record_peloton)
        btn_peloton.grid(row=0, column=1, padx=10)

        btn_both = ttk.Button(buttons_frame, text="Tour Peloton + Vélo 1", command=self.record_both)
        btn_both.grid(row=0, column=2, padx=10)

        # New: Manual Adjustment button
        dummy_button = ttk.Button(buttons_frame, text="Ajouter Tour Manuellement", command=self.add_dummy_lap)
        dummy_button.grid(row=0, column=3, padx=10)

        undo_button = ttk.Button(buttons_frame, text="Annuler Dernier Tour", command=self.undo_last_lap)
        undo_button.grid(row=0, column=4, padx=10)

        reset_button = ttk.Button(buttons_frame, text="Réinitialiser", command=self.reset_laps)
        reset_button.grid(row=0, column=5, padx=10)

        # New: Manage Laps Button
        manage_button = ttk.Button(buttons_frame, text="Gérer Tours", command=self.open_lap_management_window)
        manage_button.grid(row=0, column=6, padx=10)

        # Row 2: Last Lap Times
        lap_time_frame = ttk.Frame(self.root)
        lap_time_frame.grid(row=2, column=0, columnspan=4, pady=10)

        self.label_bike1_time = ttk.Label(lap_time_frame, text="Bike 1 time: N/A", font=("Helvetica", 12))
        self.label_bike1_time.pack(side="left", padx=40)

        self.label_peloton_time = ttk.Label(lap_time_frame, text="Peloton time: N/A", font=("Helvetica", 12))
        self.label_peloton_time.pack(side="left", padx=40)

        # Row 3: Gap Display
        self.label_gap = ttk.Label(self.root, text="Current gap: N/A", font=("Helvetica", 14, "bold"), foreground="red")
        self.label_gap.grid(row=3, column=0, columnspan=4, pady=10)

        # Row 4: Rider Selection
        selection_frame = ttk.Frame(self.root)
        selection_frame.grid(row=4, column=0, columnspan=4, pady=5)
        ttk.Label(selection_frame, text="Sélectionnez le rouleur (Bike 1):", font=("Helvetica", 12)).pack(side="left", padx=5)
        self.rider_selector = ttk.Combobox(selection_frame, values=self.riders, state="readonly")
        self.rider_selector.current(0)
        self.rider_selector.pack(side="left", padx=5)

        # Row 5: Lap History (Treeviews)
        history_frame = ttk.Frame(self.root)
        history_frame.grid(row=5, column=0, columnspan=4, pady=10)

        bike1_labelframe = ttk.LabelFrame(history_frame, text="Derniers tours Vélo 1", style="Bold.TLabelframe")
        bike1_labelframe.pack(side="left", padx=20)

        self.bike1_tree = ttk.Treeview(bike1_labelframe,
                                       columns=("lapnum", "rider", "laptime", "timediff", "lapdur"),
                                       show="headings", height=10)
        for col, head in zip(("lapnum", "rider", "laptime", "timediff", "lapdur"),
                              ("Lap #", "Rider", "Lap Time", "Time Diff", "Lap Duration")):
            self.bike1_tree.heading(col, text=head)
        self.bike1_tree.column("lapnum", width=50, anchor="center")
        self.bike1_tree.column("rider", width=80, anchor="center")
        self.bike1_tree.column("laptime", width=100, anchor="center")
        self.bike1_tree.column("timediff", width=100, anchor="center")
        self.bike1_tree.column("lapdur", width=100, anchor="center")
        self.bike1_tree.pack(side="left")
        scroll_bike1 = ttk.Scrollbar(bike1_labelframe, orient="vertical", command=self.bike1_tree.yview)
        scroll_bike1.pack(side="right", fill="y")
        self.bike1_tree.configure(yscrollcommand=scroll_bike1.set)

        peloton_labelframe = ttk.LabelFrame(history_frame, text="Derniers tours Peloton", style="Bold.TLabelframe")
        peloton_labelframe.pack(side="left", padx=20)
        self.peloton_tree = ttk.Treeview(peloton_labelframe,
                                         columns=("lapnum", "rider", "laptime", "timediff", "lapdur"),
                                         show="headings", height=10)
        for col, head in zip(("lapnum", "rider", "laptime", "timediff", "lapdur"),
                              ("Lap #", "Rider", "Lap Time", "Time Diff", "Lap Duration")):
            self.peloton_tree.heading(col, text=head)
        self.peloton_tree.column("lapnum", width=50, anchor="center")
        self.peloton_tree.column("rider", width=80, anchor="center")
        self.peloton_tree.column("laptime", width=100, anchor="center")
        self.peloton_tree.column("timediff", width=100, anchor="center")
        self.peloton_tree.column("lapdur", width=100, anchor="center")
        self.peloton_tree.pack(side="left")
        scroll_peloton = ttk.Scrollbar(peloton_labelframe, orient="vertical", command=self.peloton_tree.yview)
        scroll_peloton.pack(side="right", fill="y")
        self.peloton_tree.configure(yscrollcommand=scroll_peloton.set)

        # Row 6: Stats, Export, Simulation
        stats_frame = ttk.Frame(self.root)
        stats_frame.grid(row=6, column=0, columnspan=4, pady=10)

        stats_button = ttk.Button(stats_frame, text="Voir Statistiques", command=self.show_stats_window)
        stats_button.pack(side="left", padx=10)

        export_button = ttk.Button(stats_frame, text="Exporter CSV", command=self.export_csv)
        export_button.pack(side="left", padx=10)

        simulation_button = ttk.Button(stats_frame, text="Démarrer Simulation (4min)", command=self.start_map_simulation)
        simulation_button.pack(side="left", padx=10)

    # -----------------------------
    # 4. Timer & Updates
    # -----------------------------
    def start_24h(self):
        if not self.start_time:
            self.start_time = time.time()
        self.update_timer()

    def update_timer(self):
        if self.start_time:
            elapsed = time.time() - self.start_time
            self.label_elapsed.config(text=str(timedelta(seconds=int(elapsed))))
        self.root.after(1000, self.update_timer)

    def format_time(self, t):
        if self.start_time:
            return str(timedelta(seconds=int(t - self.start_time)))
        return "N/A"

    def calculate_time_diff(self, current_time, reference_time):
        if reference_time:
            return str(timedelta(seconds=int(current_time - reference_time)))
        return "N/A"

    def format_lap_duration(self, duration_seconds):
        if duration_seconds <= 0:
            return "N/A"
        return str(timedelta(seconds=int(duration_seconds)))

    # -----------------------------
    # 5. Recording Laps
    # -----------------------------
    def record_rouleur_1(self):
        if not self.start_time:
            messagebox.showwarning("Attention", "Démarrez d'abord le chronomètre.")
            return

        now = time.time()
        if self.last_rouleur_1_time and (now - self.last_rouleur_1_time < self.MIN_LAP_TIME):
            messagebox.showwarning("Attention", f"Il faut au moins {self.MIN_LAP_TIME}s entre deux tours Vélo 1.")
            return

        rider = self.rider_selector.get()
        if not rider:
            messagebox.showwarning("Attention", "Veuillez sélectionner un rouleur.")
            return

        self.total_rouleur_1 += 1
        current_time = now
        lap_duration = (current_time - self.last_rouleur_1_time) if self.last_rouleur_1_time else (current_time - self.start_time)
        lap_time_str = self.format_time(current_time)
        time_diff_str = self.calculate_time_diff(current_time, self.last_peloton_time)
        lap_duration_str = self.format_lap_duration(lap_duration)

        self.store_lap_data("Vélo 1", self.total_rouleur_1, rider, lap_time_str, time_diff_str,
                            (current_time - self.start_time), lap_duration)

        self.rouleur_1_laps.append((self.total_rouleur_1, rider, lap_time_str, time_diff_str, lap_duration_str))
        self.last_rouleur_1_time = current_time

        self.label_rouleur_1_total.config(text=f"Total Rosaire (Bike 1): {self.total_rouleur_1}")
        self.label_bike1_time.config(text=f"Bike 1 time: {lap_time_str}")
        self.update_gap_display()
        self.update_lap_history()

    def record_peloton(self):
        if not self.start_time:
            messagebox.showwarning("Attention", "Démarrez d'abord le chronomètre.")
            return

        now = time.time()
        if self.last_peloton_time and (now - self.last_peloton_time < self.MIN_LAP_TIME):
            messagebox.showwarning("Attention", f"Il faut au moins {self.MIN_LAP_TIME}s entre deux tours du Peloton.")
            return

        self.total_peloton += 1
        current_time = now
        lap_duration = (current_time - self.last_peloton_time) if self.last_peloton_time else (current_time - self.start_time)
        lap_time_str = self.format_time(current_time)
        time_diff_str = self.calculate_time_diff(current_time, self.last_rouleur_1_time)
        lap_duration_str = self.format_lap_duration(lap_duration)

        self.store_lap_data("Peloton", self.total_peloton, "N/A", lap_time_str, time_diff_str,
                            (current_time - self.start_time), lap_duration)

        self.peloton_laps.append((self.total_peloton, "Peloton", lap_time_str, time_diff_str, lap_duration_str))
        self.last_peloton_time = current_time

        self.label_peloton_total.config(text=f"Total Peloton: {self.total_peloton}")
        self.label_peloton_time.config(text=f"Peloton time: {lap_time_str}")
        self.update_gap_display()
        self.update_lap_history()

    def record_both(self):
        if not self.start_time:
            messagebox.showwarning("Attention", "Démarrez d'abord le chronomètre.")
            return

        now = time.time()
        if self.last_rouleur_1_time and (now - self.last_rouleur_1_time < self.MIN_LAP_TIME):
            messagebox.showwarning("Attention", f"Il faut au moins {self.MIN_LAP_TIME}s entre deux tours Vélo 1.")
            return
        if self.last_peloton_time and (now - self.last_peloton_time < self.MIN_LAP_TIME):
            messagebox.showwarning("Attention", f"Il faut au moins {self.MIN_LAP_TIME}s entre deux tours du Peloton.")
            return

        self.record_rouleur_1()
        self.record_peloton()

    # -----------------------------
    # 6. Database Insertion
    # -----------------------------
    def store_lap_data(self, lap_type, lap_number, rider_name, lap_time, time_diff, cumulative_time, lap_duration):
        with sqlite3.connect('laps_data.db') as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO laps 
                (type, lap_number, rider_name, lap_time, time_diff, cumulative_time, lap_duration)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (lap_type, lap_number, rider_name, lap_time, time_diff,
                  str(int(cumulative_time)), str(int(lap_duration))))
            conn.commit()

    # -----------------------------
    # 7. Undo / Reset / Gap Display
    # -----------------------------
    def undo_last_lap(self):
        if not self.last_rouleur_1_time and not self.last_peloton_time:
            messagebox.showinfo("Info", "Aucun tour enregistré à annuler.")
            return

        if (self.last_rouleur_1_time or 0) > (self.last_peloton_time or 0):
            if self.total_rouleur_1 > 0:
                self.remove_last_db_entry("Vélo 1")
                self.total_rouleur_1 -= 1
                if self.rouleur_1_laps:
                    self.rouleur_1_laps.pop()
                self.last_rouleur_1_time = None
                if self.rouleur_1_laps:
                    self.last_rouleur_1_time = self.get_timestamp_for_last_lap("Vélo 1")
                self.label_rouleur_1_total.config(text=f"Total Rosaire (Bike 1): {self.total_rouleur_1}")
            else:
                messagebox.showinfo("Info", "Aucun tour Vélo 1 à annuler.")
        else:
            if self.total_peloton > 0:
                self.remove_last_db_entry("Peloton")
                self.total_peloton -= 1
                if self.peloton_laps:
                    self.peloton_laps.pop()
                self.last_peloton_time = None
                if self.peloton_laps:
                    self.last_peloton_time = self.get_timestamp_for_last_lap("Peloton")
                self.label_peloton_total.config(text=f"Total Peloton: {self.total_peloton}")
            else:
                messagebox.showinfo("Info", "Aucun tour Peloton à annuler.")

        self.update_gap_display()
        self.update_lap_history()

    def remove_last_db_entry(self, lap_type):
        with sqlite3.connect('laps_data.db') as conn:
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

    def get_timestamp_for_last_lap(self, lap_type):
        with sqlite3.connect('laps_data.db') as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT cumulative_time FROM laps
                WHERE type = ?
                ORDER BY id DESC
                LIMIT 1
            """, (lap_type,))
            row = cursor.fetchone()
            if row:
                ctime = float(row[0])
                return self.start_time + ctime
        return None

    def reset_laps(self):
        confirm = messagebox.askyesno("Réinitialiser", "Voulez-vous vraiment tout réinitialiser ?")
        if not confirm:
            return

        self.rouleur_1_laps.clear()
        self.peloton_laps.clear()
        self.total_rouleur_1 = 0
        self.total_peloton = 0

        self.label_rouleur_1_total.config(text="Total Rosaire (Bike 1): 0")
        self.label_peloton_total.config(text="Total Peloton: 0")
        self.label_bike1_time.config(text="Bike 1 time: N/A")
        self.label_peloton_time.config(text="Peloton time: N/A")
        self.label_gap.config(text="Current gap: N/A")

        for item in self.bike1_tree.get_children():
            self.bike1_tree.delete(item)
        for item in self.peloton_tree.get_children():
            self.peloton_tree.delete(item)

        self.last_rouleur_1_time = None
        self.last_peloton_time = None

        # Optionally, you might also clear the DB (commented out):
        # with sqlite3.connect('laps_data.db') as conn:
        #     cursor = conn.cursor()
        #     cursor.execute("DELETE FROM laps")
        #     conn.commit()

    def update_gap_display(self):
        lap_diff = self.total_rouleur_1 - self.total_peloton
        if lap_diff > 0:
            self.label_gap.config(text=f"Current gap: Bike 1 is {lap_diff} lap(s) ahead.")
        elif lap_diff < 0:
            self.label_gap.config(text=f"Current gap: Peloton is {abs(lap_diff)} lap(s) ahead.")
        else:
            if self.last_rouleur_1_time and self.last_peloton_time:
                if self.last_rouleur_1_time < self.last_peloton_time:
                    gap_sec = int(self.last_peloton_time - self.last_rouleur_1_time)
                    self.label_gap.config(text=f"Current gap: Same lap. Bike 1 leads by {gap_sec}s.")
                elif self.last_peloton_time < self.last_rouleur_1_time:
                    gap_sec = int(self.last_rouleur_1_time - self.last_peloton_time)
                    self.label_gap.config(text=f"Current gap: Same lap. Peloton leads by {gap_sec}s.")
                else:
                    self.label_gap.config(text="Current gap: Exactly simultaneous!")
            else:
                self.label_gap.config(text="Current gap: N/A")

    def update_lap_history(self):
        for item in self.bike1_tree.get_children():
            self.bike1_tree.delete(item)
        for lap in self.rouleur_1_laps[-10:]:
            self.bike1_tree.insert("", "end", values=(lap[0], lap[1], lap[2], lap[3], lap[4]))

        for item in self.peloton_tree.get_children():
            self.peloton_tree.delete(item)
        for lap in self.peloton_laps[-10:]:
            self.peloton_tree.insert("", "end", values=(lap[0], lap[1], lap[2], lap[3], lap[4]))

    # -----------------------------
    # 8. Advanced Statistics & Export
    # -----------------------------
    def show_stats_window(self):
        stats_win = tk.Toplevel(self.root)
        stats_win.title("Statistiques Avancées")

        # Overall stats for Bike 1 and Peloton
        with sqlite3.connect('laps_data.db') as conn:
            cursor = conn.cursor()

            # Overall for Bike 1
            cursor.execute("SELECT AVG(lap_duration), MIN(lap_duration), COUNT(*) FROM laps WHERE type='Vélo 1'")
            row = cursor.fetchone()
            avg_bike1 = float(row[0]) if row and row[0] else 0
            min_bike1 = float(row[1]) if row and row[1] else 0
            count_bike1 = int(row[2]) if row and row[2] else 0

            # Overall for Peloton
            cursor.execute("SELECT AVG(lap_duration), MIN(lap_duration), COUNT(*) FROM laps WHERE type='Peloton'")
            row = cursor.fetchone()
            avg_peloton = float(row[0]) if row and row[0] else 0
            min_peloton = float(row[1]) if row and row[1] else 0
            count_peloton = int(row[2]) if row and row[2] else 0

        overall_text = (
            f"Overall Stats:\n\n"
            f"Bike 1: {count_bike1} laps, Avg Lap: {self.format_seconds(avg_bike1)}, Fastest Lap: {self.format_seconds(min_bike1)}\n\n"
            f"Peloton: {count_peloton} laps, Avg Lap: {self.format_seconds(avg_peloton)}, Fastest Lap: {self.format_seconds(min_peloton)}"
        )
        overall_label = ttk.Label(stats_win, text=overall_text, font=("Helvetica", 12))
        overall_label.pack(padx=10, pady=10)

        # Per-Rider stats for Bike 1
        rider_frame = ttk.Frame(stats_win)
        rider_frame.pack(padx=10, pady=10, fill="x")
        ttk.Label(rider_frame, text="Stats par Rider (Bike 1)", font=("Helvetica", 14, "bold")).pack(pady=5)

        tree = ttk.Treeview(rider_frame, columns=("rider", "laps", "avg", "fastest"), show="headings", height=10)
        tree.heading("rider", text="Rider")
        tree.heading("laps", text="Laps")
        tree.heading("avg", text="Avg Lap")
        tree.heading("fastest", text="Fastest Lap")
        tree.column("rider", width=100, anchor="center")
        tree.column("laps", width=50, anchor="center")
        tree.column("avg", width=100, anchor="center")
        tree.column("fastest", width=100, anchor="center")
        tree.pack(padx=5, pady=5)

        with sqlite3.connect('laps_data.db') as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT rider_name, COUNT(*), AVG(lap_duration), MIN(lap_duration)
                FROM laps
                WHERE type = 'Vélo 1'
                GROUP BY rider_name
            """)
            rows = cursor.fetchall()

        for r in rows:
            rider_name, lap_count, avg_dur, min_dur = r
            tree.insert("", "end", values=(rider_name, lap_count, self.format_seconds(avg_dur), self.format_seconds(min_dur)))

    def format_seconds(self, sec):
        try:
            sec = float(sec)
        except (TypeError, ValueError):
            return "N/A"
        if sec <= 0:
            return "N/A"
        return str(timedelta(seconds=int(sec)))

    def export_csv(self):
        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        if not filename:
            return
        with sqlite3.connect('laps_data.db') as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM laps ORDER BY id ASC")
            rows = cursor.fetchall()
        columns = ["id", "type", "lap_number", "rider_name", "lap_time",
                   "time_diff", "cumulative_time", "lap_duration"]
        try:
            with open(filename, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(columns)
                for row in rows:
                    writer.writerow(row)
            messagebox.showinfo("Export CSV", f"Export réussi: {filename}")
        except Exception as e:
            messagebox.showerror("Export CSV", f"Erreur lors de l'export: {e}")

    # -----------------------------
    # 9. Lap Management Window
    # -----------------------------
    def open_lap_management_window(self):
        """Opens a window showing all laps from the DB and allows editing or deletion."""
        mgmt_win = tk.Toplevel(self.root)
        mgmt_win.title("Gestion des Tours")

        tree = ttk.Treeview(mgmt_win,
                            columns=("id", "type", "lap_number", "rider_name", "lap_time", "time_diff", "cumulative_time", "lap_duration"),
                            show="headings", height=20)
        for col in ("id", "type", "lap_number", "rider_name", "lap_time", "time_diff", "cumulative_time", "lap_duration"):
            tree.heading(col, text=col)
            tree.column(col, anchor="center")
        tree.pack(side="left", fill="both", expand=True)

        scrollbar = ttk.Scrollbar(mgmt_win, orient="vertical", command=tree.yview)
        scrollbar.pack(side="right", fill="y")
        tree.configure(yscrollcommand=scrollbar.set)

        btn_frame = ttk.Frame(mgmt_win)
        btn_frame.pack(pady=5)

        edit_btn = ttk.Button(btn_frame, text="Modifier", command=lambda: self.edit_lap_record(tree))
        edit_btn.pack(side="left", padx=5)
        delete_btn = ttk.Button(btn_frame, text="Supprimer", command=lambda: self.delete_lap_record(tree))
        delete_btn.pack(side="left", padx=5)
        refresh_btn = ttk.Button(btn_frame, text="Rafraîchir", command=lambda: self.refresh_management_view(tree))
        refresh_btn.pack(side="left", padx=5)

        self.refresh_management_view(tree)

    def refresh_management_view(self, tree):
        for row in tree.get_children():
            tree.delete(row)
        with sqlite3.connect('laps_data.db') as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM laps ORDER BY lap_number ASC, id ASC")
            rows = cursor.fetchall()
        for r in rows:
            tree.insert("", "end", values=r)

    def edit_lap_record(self, tree):
        selection = tree.selection()
        if not selection:
            messagebox.showwarning("Attention", "Veuillez sélectionner un tour à modifier.")
            return
        item = tree.item(selection[0], "values")
        lap_id = item[0]
        current_type = item[1]
        current_lap_number = item[2]
        current_rider = item[3]
        current_lap_time = item[4]
        current_time_diff = item[5]
        current_cumulative = item[6]
        current_lap_duration = item[7]

        new_lap_number = simpledialog.askinteger("Modifier", f"Numéro de tour (actuel: {current_lap_number}):", initialvalue=current_lap_number)
        if new_lap_number is None:
            return
        new_rider = simpledialog.askstring("Modifier", f"Nom du rider (actuel: {current_rider}):", initialvalue=current_rider)
        if new_rider is None:
            return

        # For simplicity, we update only lap_number and rider_name.
        with sqlite3.connect('laps_data.db') as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE laps
                SET lap_number = ?, rider_name = ?
                WHERE id = ?
            """, (new_lap_number, new_rider, lap_id))
            conn.commit()

        messagebox.showinfo("Info", "Tour modifié avec succès.")
        self.refresh_management_view(tree)
        self.reload_laps_from_db()

    def delete_lap_record(self, tree):
        selection = tree.selection()
        if not selection:
            messagebox.showwarning("Attention", "Veuillez sélectionner un tour à supprimer.")
            return
        item = tree.item(selection[0], "values")
        lap_id = item[0]
        confirm = messagebox.askyesno("Confirmer", f"Supprimer le tour ID {lap_id} ?")
        if not confirm:
            return
        with sqlite3.connect('laps_data.db') as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM laps WHERE id = ?", (lap_id,))
            conn.commit()
        messagebox.showinfo("Info", "Tour supprimé.")
        self.refresh_management_view(tree)
        self.reload_laps_from_db()

    def reload_laps_from_db(self):
        """Reloads lap data from the database and re-synchronizes in-memory lists and counters."""
        self.rouleur_1_laps.clear()
        self.peloton_laps.clear()
        self.total_rouleur_1 = 0
        self.total_peloton = 0

        with sqlite3.connect('laps_data.db') as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT lap_number, rider_name, lap_time, time_diff, lap_duration, type FROM laps ORDER BY lap_number ASC, id ASC")
            rows = cursor.fetchall()

        for row in rows:
            lap_number, rider_name, lap_time, time_diff, lap_duration, lap_type = row
            if lap_type == "Vélo 1":
                self.rouleur_1_laps.append((lap_number, rider_name, lap_time, time_diff, self.format_lap_duration(float(lap_duration))))
                self.total_rouleur_1 = max(self.total_rouleur_1, lap_number)
                # Update last_rouleur_1_time from cumulative_time if needed.
            elif lap_type == "Peloton":
                self.peloton_laps.append((lap_number, rider_name, lap_time, time_diff, self.format_lap_duration(float(lap_duration))))
                self.total_peloton = max(self.total_peloton, lap_number)

        self.label_rouleur_1_total.config(text=f"Total Rosaire (Bike 1): {self.total_rouleur_1}")
        self.label_peloton_total.config(text=f"Total Peloton: {self.total_peloton}")
        self.update_lap_history()
        self.update_gap_display()

    # -----------------------------
    # 10. Manual Lap Adjustment (Dummy Lap)
    # -----------------------------
    def add_dummy_lap(self):
        """Allows the user to manually add a lap (e.g. a missed lap)."""
        lap_type = simpledialog.askstring("Ajouter Tour Manuellement", "Ajouter pour quel type? (Vélo 1 / Peloton)")
        if lap_type not in ("Vélo 1", "Peloton"):
            messagebox.showerror("Erreur", "Type invalide. Entrez 'Vélo 1' ou 'Peloton'.")
            return

        # Optionally, ask for an approximate lap duration (in seconds)
        dummy_duration = simpledialog.askinteger("Durée du Tour", "Durée approximative du tour (secondes):", initialvalue=60)
        if dummy_duration is None:
            return

        now = time.time()
        if lap_type == "Vélo 1":
            self.total_rouleur_1 += 1
            lap_number = self.total_rouleur_1
            rider = self.rider_selector.get()
            # For a dummy lap, use 'now' for lap_time and dummy_duration for lap duration.
            lap_time_str = self.format_time(now)
            # We'll set time_diff to N/A since it's a dummy lap.
            time_diff_str = "N/A"
            lap_duration = dummy_duration
            lap_duration_str = self.format_lap_duration(lap_duration)
            self.store_lap_data(lap_type, lap_number, rider, lap_time_str, time_diff_str, (now - self.start_time), lap_duration)
            self.rouleur_1_laps.append((lap_number, rider, lap_time_str, time_diff_str, lap_duration_str))
            self.last_rouleur_1_time = now
            self.label_rouleur_1_total.config(text=f"Total Rosaire (Bike 1): {self.total_rouleur_1}")
            self.label_bike1_time.config(text=f"Bike 1 time: {lap_time_str}")
        else:  # Peloton
            self.total_peloton += 1
            lap_number = self.total_peloton
            rider = "N/A"
            lap_time_str = self.format_time(now)
            time_diff_str = "N/A"
            lap_duration = dummy_duration
            lap_duration_str = self.format_lap_duration(lap_duration)
            self.store_lap_data(lap_type, lap_number, rider, lap_time_str, time_diff_str, (now - self.start_time), lap_duration)
            self.peloton_laps.append((lap_number, rider, lap_time_str, time_diff_str, lap_duration_str))
            self.last_peloton_time = now
            self.label_peloton_total.config(text=f"Total Peloton: {self.total_peloton}")
            self.label_peloton_time.config(text=f"Peloton time: {lap_time_str}")

        self.update_gap_display()
        self.update_lap_history()

    # -----------------------------
    # 11. Map Simulation (4-minute)
    # -----------------------------
    def start_map_simulation(self):
        if self.simulation_running:
            return

        self.simulation_running = True
        self.start_time = time.time()  # Marquer le début de la simulation

        # Crée une nouvelle fenêtre pour la simulation
        self.map_win = tk.Toplevel(self.root)
        self.map_win.title("Simulation du Tour (4 minutes)")

        self.canvas = tk.Canvas(self.map_win, width=400, height=400, bg="white")
        self.canvas.pack()

        # Trace du parcours en reliant les points
        for i in range(1, len(self.coordinates)):
            self.canvas.create_line(self.coordinates[i-1][0], self.coordinates[i-1][1],
                                    self.coordinates[i][0], self.coordinates[i][1], fill="blue")

        # Crée un point rouge pour simuler le mouvement
        self.simulation_dot = self.canvas.create_oval(self.coordinates[0][0]-5, self.coordinates[0][1]-5,
                                                      self.coordinates[0][0]+5, self.coordinates[0][1]+5, fill="red")

        # Lancer la simulation du mouvement du cycliste
        self.update_simulation()

    def update_simulation(self):
        # Calcule le temps écoulé
        elapsed_time = time.time() - self.start_time

        # Le temps total pour la simulation est de 4 minutes, soit 240 secondes
        total_time = 240  # 4 minutes en secondes
        progress = elapsed_time / total_time

        # Si la simulation n'est pas encore terminée
        if progress < 1.0:
            # Calcul de l'index du point à afficher en fonction du temps écoulé
            index = int(progress * len(self.coordinates))

            # Déplace le point rouge à la nouvelle position
            self.canvas.coords(self.simulation_dot,
                               self.coordinates[index][0] - 5, self.coordinates[index][1] - 5,
                               self.coordinates[index][0] + 5, self.coordinates[index][1] + 5)

            # Mettre à jour la simulation toutes les 50ms
            self.map_win.after(50, self.update_simulation)
        else:
            # Si la simulation est terminée, désactive la variable de contrôle
            self.simulation_running = False


    # -----------------------------
    # 12. Mainloop
    # -----------------------------
    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    root = tk.Tk()
    app = CyclingEventApp(root)
    app.run()