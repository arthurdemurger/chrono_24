import time
from datetime import timedelta
from tkinter import messagebox, simpledialog, filedialog, Toplevel, ttk
import csv
import sqlite3

from .db import (
    init_db,
    store_lap_data,
    remove_last_db_entry,
    reload_from_db,
    clear_all_laps_db,
    fetch_stats_for_all,
    fetch_stats_per_rider
)
from .utils import format_lap_duration

class CyclingCore:
    def __init__(self, app):
        self.app = app
        self.start_time = None
        self.MIN_LAP_TIME = 30

        # Bike1
        self.last_rouleur_1_time = None
        self.rouleur_1_laps = []
        self.total_rouleur_1 = 0

        # Peloton
        self.last_peloton_time = None
        self.peloton_laps = []
        self.total_peloton = 0

        # TMA
        self.last_tma_time = None
        self.tma_laps = []
        self.total_tma = 0

        # Liste riders
        self.riders = [
            "Lionceau", "Tarpan", "Tamarin", "Ouandji", "Pajero", "Bengali",
            "Kitfox", "Banteng", "Xérus", "Capybara", "Mustela", "Aquila",
            "Chaoui", "Steenbock", "Lycaon", "Kowari", "Jaco", "Markhor",
            "Alaskan", "Chikaree", "Margay", "Mink", "Springbok"
        ]

        self.next_rouleurs_queue = []
        self.current_rouleur = self.riders[0]

        init_db()
        # Lancement du timer => depuis ui.py (self.core.update_timer()) après build_ui

    # ============== Chrono principal ==============
    def start_24h(self):
        """
        Démarre le chrono => start_time = now,
        last_xxx_time = start_time pour réinitialiser les 'current' à 0.
        """
        if not self.start_time:
            self.start_time = time.time()
            self.last_rouleur_1_time = self.start_time
            self.last_peloton_time = self.start_time
            self.last_tma_time = self.start_time

    def update_timer(self):
        """
        Appelé chaque seconde => label principal + update_table_headers()
        """
        if self.start_time:
            elapsed = time.time() - self.start_time
            self.app.label_elapsed.config(text=str(timedelta(seconds=int(elapsed))))

        # Actualise “Current” + écarts en direct
        self.update_table_headers()

        self.app.root.after(1000, self.update_timer)

    def add_new_rider(self):
        new_name = simpledialog.askstring("Nouveau Rouleur", "Nom du nouveau rouleur :")
        if new_name:
            new_name = new_name.strip()
            if new_name:
                self.riders.append(new_name)
                self.app.rider_selector["values"] = self.riders
                messagebox.showinfo("Succès", f"Le rouleur '{new_name}' a été ajouté.")
            else:
                messagebox.showwarning("Attention", "Le nom du rouleur ne peut être vide.")

    # ============== Record TMA ==============
    def record_tma(self):
        if not self.start_time:
            messagebox.showwarning("Attention", "Démarrez d'abord le chronomètre.")
            return

        now = time.time()
        if self.last_tma_time and (now - self.last_tma_time < self.MIN_LAP_TIME):
            messagebox.showwarning("Attention", f"Il faut au moins {self.MIN_LAP_TIME}s entre deux tours TMA.")
            return

        self.total_tma += 1
        rider = "TMA"
        lap_duration = (now - self.last_tma_time) if self.last_tma_time else (now - self.start_time)
        lap_time_str = self.format_time(now)

        store_lap_data(
            lap_type="TMA",
            lap_number=self.total_tma,
            rider_name=rider,
            lap_time=lap_time_str,
            time_diff="N/A",
            cumulative_time=int(now - self.start_time),
            lap_duration=int(lap_duration)
        )
        self.tma_laps.append((self.total_tma, rider, lap_time_str, "N/A", format_lap_duration(lap_duration)))
        self.last_tma_time = now

        self.app.label_tma_total.config(text=f"Total TMA: {self.total_tma}")
        self.update_lap_history()


    # ============== Record Vélo 1 ==============
    def update_queue_display(self):
      for item in self.app.queue_tree.get_children():
          self.app.queue_tree.delete(item)
      for rider in self.next_rouleurs_queue:
          self.app.queue_tree.insert("", "end", values=(rider,))


    def update_current_rouleur_display(self):
      # Mettre à jour l'étiquette du rouleur actuel dans l'interface
      self.app.current_rider_label.config(text=f"Rouleur actuel : {self.current_rouleur}")

    def next_rouleur(self):
        if self.next_rouleurs_queue:
            self.current_rouleur = self.next_rouleurs_queue.pop(0)  # Passe au premier rouleur de la queue
            self.update_queue_display()  # Mettre à jour le tableau après changement
            self.update_current_rouleur_display()  # Mettre à jour l'affichage du rouleur actuel
        else:
            messagebox.showwarning("File vide", "La file d'attente est vide.")

    def add_to_queue(self):
        rider = self.app.rider_selector.get()  # Obtenir le nom du rouleur sélectionné
        self.next_rouleurs_queue.append(rider)  # Ajouter à la queue si non déjà présent
        self.update_queue_display()  # Mettre à jour l'affichage de la file d'attente

    def remove_from_queue(self):
        selected = self.app.queue_tree.selection()
        if not selected:
            messagebox.showinfo("Info", "Veuillez sélectionner un rouleur à retirer dans la liste.")
            return

        index = self.app.queue_tree.index(selected[0])  # <- On récupère l'index directement
        if 0 <= index < len(self.next_rouleurs_queue):
            del self.next_rouleurs_queue[index]  # <- Suppression par index
            self.update_queue_display()

    def move_rider_up(self):
        selected = self.app.queue_tree.selection()
        if selected:
            index = self.app.queue_tree.index(selected[0])
            if index > 0:
                # Échange dans la liste
                self.next_rouleurs_queue[index], self.next_rouleurs_queue[index - 1] = self.next_rouleurs_queue[index - 1], self.next_rouleurs_queue[index]
                self.update_queue_display()
                # Re-sélectionner l'élément déplacé
                new_item = self.app.queue_tree.get_children()[index - 1]
                self.app.queue_tree.selection_set(new_item)

    def move_rider_down(self):
        selected = self.app.queue_tree.selection()
        if selected:
            index = self.app.queue_tree.index(selected[0])
            if index < len(self.next_rouleurs_queue) - 1:
                # Échange dans la liste
                self.next_rouleurs_queue[index], self.next_rouleurs_queue[index + 1] = self.next_rouleurs_queue[index + 1], self.next_rouleurs_queue[index]
                self.update_queue_display()
                # Re-sélectionner l'élément déplacé
                new_item = self.app.queue_tree.get_children()[index + 1]
                self.app.queue_tree.selection_set(new_item)

    def reset_queue(self):
        self.next_rouleurs_queue = []
        self.app.queue_tree.delete(*self.app.queue_tree.get_children())

    def confirm_reset_queue(self):
        confirm = messagebox.askyesno("Confirmation", "Es-tu sûr de vouloir réinitialiser toute la file d'attente ?")
        if confirm:
          self.reset_queue()

    def record_rouleur_1(self):
        if not self.start_time:
            messagebox.showwarning("Attention", "Démarrez d'abord le chronomètre.")
            return
        now = time.time()

        # Vérification du temps entre deux tours
        if self.last_rouleur_1_time and (now - self.last_rouleur_1_time < self.MIN_LAP_TIME):
            messagebox.showwarning("Attention", f"Il faut au moins {self.MIN_LAP_TIME}s entre deux tours Vélo 1.")
            return

        rider = self.current_rouleur or "Vélo1"  # Si la queue est vide, utiliser l'ancien ou "Vélo1"

        self.total_rouleur_1 += 1

        # Calcul du temps du tour
        lap_duration = (now - self.last_rouleur_1_time) if self.last_rouleur_1_time else (now - self.start_time)
        lap_time_str = self.format_time(now)

        # Enregistrer le tour dans la base de données
        store_lap_data(
            lap_type="Vélo 1",
            lap_number=self.total_rouleur_1,
            rider_name=rider,
            lap_time=lap_time_str,
            time_diff="N/A",
            cumulative_time=int(now - self.start_time),
            lap_duration=int(lap_duration)
        )

        # Ajouter le tour à la liste des tours de Vélo 1
        self.rouleur_1_laps.append((self.total_rouleur_1, rider, lap_time_str, "N/A", format_lap_duration(lap_duration)))
        self.last_rouleur_1_time = now

        # Mise à jour de l'affichage du total des tours de Vélo 1
        self.app.label_rouleur_1_total.config(text=f"Total Rosaire (Bike 1): {self.total_rouleur_1}")

        # Mettre à jour l'historique des tours
        self.update_lap_history()

        # Mettre à jour l'affichage de la file d'attente des rouleurs
        self.update_queue_display()  # Assurez-vous que cette méthode est définie dans core.py



    # ============== Record Peloton ==============
    def record_peloton(self):
        if not self.start_time:
            messagebox.showwarning("Attention", "Démarrez d'abord le chronomètre.")
            return
        now = time.time()
        if self.last_peloton_time and (now - self.last_peloton_time < self.MIN_LAP_TIME):
            messagebox.showwarning("Attention", f"Il faut au moins {self.MIN_LAP_TIME}s entre deux tours du Peloton.")
            return

        self.total_peloton += 1
        lap_duration = (now - self.last_peloton_time) if self.last_peloton_time else (now - self.start_time)
        lap_time_str = self.format_time(now)

        store_lap_data(
            lap_type="Peloton",
            lap_number=self.total_peloton,
            rider_name="N/A",
            lap_time=lap_time_str,
            time_diff="N/A",
            cumulative_time=int(now - self.start_time),
            lap_duration=int(lap_duration)
        )
        self.peloton_laps.append((self.total_peloton, "Peloton", lap_time_str, "N/A", format_lap_duration(lap_duration)))
        self.last_peloton_time = now

        self.app.label_peloton_total.config(text=f"Total Peloton: {self.total_peloton}")
        self.update_lap_history()

    # ============== Undo / Reset ==============
    def undo_last_lap(self):
        times = [
            ("Vélo 1", self.last_rouleur_1_time),
            ("Peloton", self.last_peloton_time),
            ("TMA", self.last_tma_time)
        ]
        times = [(typ, t) for (typ, t) in times if t is not None]
        if not times:
            messagebox.showinfo("Info", "Aucun tour enregistré à annuler.")
            return

        last_type, _ = max(times, key=lambda x: x[1])
        if last_type == "Vélo 1":
            if self.total_rouleur_1 > 0:
                remove_last_db_entry("Vélo 1")
                self.total_rouleur_1 -= 1
                if self.rouleur_1_laps:
                    self.rouleur_1_laps.pop()
                self.last_rouleur_1_time = None
                if self.rouleur_1_laps:
                    self.last_rouleur_1_time = self.find_last_timestamp_from_db("Vélo 1")
                self.app.label_rouleur_1_total.config(text=f"Total Rosaire (Bike 1): {self.total_rouleur_1}")
        elif last_type == "Peloton":
            if self.total_peloton > 0:
                remove_last_db_entry("Peloton")
                self.total_peloton -= 1
                if self.peloton_laps:
                    self.peloton_laps.pop()
                self.last_peloton_time = None
                if self.peloton_laps:
                    self.last_peloton_time = self.find_last_timestamp_from_db("Peloton")
                self.app.label_peloton_total.config(text=f"Total Peloton: {self.total_peloton}")
        else:
            if self.total_tma > 0:
                remove_last_db_entry("TMA")
                self.total_tma -= 1
                if self.tma_laps:
                    self.tma_laps.pop()
                self.last_tma_time = None
                if self.tma_laps:
                    self.last_tma_time = self.find_last_timestamp_from_db("TMA")
                self.app.label_tma_total.config(text=f"Total TMA: {self.total_tma}")

        self.update_lap_history()

    def reset_laps(self):
        confirm = messagebox.askyesno("Réinitialiser", "Voulez-vous vraiment tout réinitialiser ?")
        if not confirm:
            return
        self.rouleur_1_laps.clear()
        self.peloton_laps.clear()
        self.tma_laps.clear()

        self.total_rouleur_1 = 0
        self.total_peloton = 0
        self.total_tma = 0

        self.last_rouleur_1_time = None
        self.last_peloton_time = None
        self.last_tma_time = None

        self.app.label_rouleur_1_total.config(text="Total Rosaire (Bike 1): 0")
        self.app.label_peloton_total.config(text="Total Peloton: 0")
        self.app.label_tma_total.config(text="Total TMA: 0")

        for item in self.app.bike1_tree.get_children():
            self.app.bike1_tree.delete(item)
        for item in self.app.peloton_tree.get_children():
            self.app.peloton_tree.delete(item)
        for item in self.app.tma_tree.get_children():
            self.app.tma_tree.delete(item)

        clear_all_laps_db()

    def find_last_timestamp_from_db(self, lap_type):
        with sqlite3.connect("data/laps_data.db") as conn:
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
                return (self.start_time or 0) + ctime
        return None

    # ============== Dummy Lap ==============
    def add_dummy_lap(self):
        lap_type = simpledialog.askstring("Ajouter Tour Manuellement", "Ajouter pour quel type? (Vélo 1 / Peloton / TMA)")
        if lap_type not in ("Vélo 1", "Peloton", "TMA"):
            messagebox.showerror("Erreur", "Type invalide. Entrez 'Vélo 1', 'Peloton' ou 'TMA'.")
            return

        dummy_duration = simpledialog.askinteger("Durée du Tour", "Durée approximative du tour (secondes):", initialvalue=60)
        if dummy_duration is None:
            return

        now = time.time()
        if lap_type == "Vélo 1":
            self.total_rouleur_1 += 1
            rider = self.app.rider_selector.get() or "Vélo1"
            lap_number = self.total_rouleur_1
            self.last_rouleur_1_time = now
            self.app.label_rouleur_1_total.config(text=f"Total Rosaire (Bike 1): {self.total_rouleur_1}")
            self.rouleur_1_laps.append((lap_number, rider, self.format_time(now), "N/A", format_lap_duration(dummy_duration)))
        elif lap_type == "Peloton":
            self.total_peloton += 1
            rider = "N/A"
            lap_number = self.total_peloton
            self.last_peloton_time = now
            self.app.label_peloton_total.config(text=f"Total Peloton: {self.total_peloton}")
            self.peloton_laps.append((lap_number, rider, self.format_time(now), "N/A", format_lap_duration(dummy_duration)))
        else:
            self.total_tma += 1
            rider = "TMA"
            lap_number = self.total_tma
            self.last_tma_time = now
            self.app.label_tma_total.config(text=f"Total TMA: {self.total_tma}")
            self.tma_laps.append((lap_number, rider, self.format_time(now), "N/A", format_lap_duration(dummy_duration)))

        store_lap_data(
            lap_type=lap_type,
            lap_number=lap_number,
            rider_name=rider,
            lap_time=self.format_time(now),
            time_diff="N/A",
            cumulative_time=int((self.start_time and now - self.start_time) or 0),
            lap_duration=dummy_duration
        )
        self.update_lap_history()

    # ============== Update Lap History ==============
    def update_lap_history(self):
        """
        Met à jour les TreeViews, gap.
        Le “current” est mis à jour dans update_timer() (en direct).
        """
        # Bike1
        for item in self.app.bike1_tree.get_children():
            self.app.bike1_tree.delete(item)
        for lap in self.rouleur_1_laps[-10:]:
            self.app.bike1_tree.insert("", "end", values=(lap[0], lap[1], lap[2], lap[3], lap[4]))

        # Peloton
        for item in self.app.peloton_tree.get_children():
            self.app.peloton_tree.delete(item)
        for lap in self.peloton_laps[-10:]:
            self.app.peloton_tree.insert("", "end", values=(lap[0], lap[1], lap[2], lap[3], lap[4]))

        # TMA
        for item in self.app.tma_tree.get_children():
            self.app.tma_tree.delete(item)
        for lap in self.tma_laps[-10:]:
            self.app.tma_tree.insert("", "end", values=(lap[0], lap[1], lap[2], lap[3], lap[4]))

        self.update_gap_display()

    def update_gap_display(self):
        """
        Gap principal entre Bike1 et Peloton en tours.
        Si ex aequo => compare le timestamp => +/- Xs
        """
        lap_diff = self.total_rouleur_1 - self.total_peloton
        if lap_diff > 0:
            self.app.label_gap.config(text=f"Current gap: Bike 1 is {lap_diff} lap(s) ahead.")
        elif lap_diff < 0:
            self.app.label_gap.config(text=f"Current gap: Peloton is {abs(lap_diff)} lap(s) ahead.")
        else:
            if self.last_rouleur_1_time and self.last_peloton_time:
                gap_sec = int(self.last_peloton_time - self.last_rouleur_1_time)
                if gap_sec > 0:
                    self.app.label_gap.config(text=f"Current gap: Same lap. Peloton leads by {gap_sec}s.")
                elif gap_sec < 0:
                    self.app.label_gap.config(text=f"Current gap: Same lap. Bike 1 leads by {abs(gap_sec)}s.")
                else:
                    self.app.label_gap.config(text="Current gap: Exactly simultaneous!")
            else:
                self.app.label_gap.config(text="Current gap: N/A")

    # ============== Update Table Headers ==============
    def update_table_headers(self):
        """Chaque seconde => calcule “current” + écarts."""
        # Bike1
        curr_b1 = self.compute_current_lap_time("Vélo 1")
        curr_b1_str = self.format_secs_as_HHMMSS(curr_b1) if curr_b1 is not None else "N/A"
        self.app.header_bike1_current.config(text=f"Vélo 1 Current: {curr_b1_str}")

        avg_b1 = self.compute_avg_of_last_5(self.rouleur_1_laps)
        if avg_b1:
            self.app.header_bike1_avg5.config(text=f"Moyenne (5 derniers): {format_lap_duration(avg_b1)}")
        else:
            self.app.header_bike1_avg5.config(text="Moyenne (5 derniers): N/A")

        diff_b1_pel = self.compute_diff_current("Vélo 1", "Peloton")
        diff_b1_tma = self.compute_diff_current("Vélo 1", "TMA")
        self.app.header_bike1_diff1.config(text=f"Écart vs Peloton: {diff_b1_pel}")
        self.app.header_bike1_diff2.config(text=f"Écart vs TMA: {diff_b1_tma}")

        # Peloton
        curr_pel = self.compute_current_lap_time("Peloton")
        curr_pel_str = self.format_secs_as_HHMMSS(curr_pel) if curr_pel is not None else "N/A"
        self.app.header_peloton_current.config(text=f"Peloton Current: {curr_pel_str}")

        avg_pel = self.compute_avg_of_last_5(self.peloton_laps)
        if avg_pel:
            self.app.header_peloton_avg5.config(text=f"Moyenne (5 derniers): {format_lap_duration(avg_pel)}")
        else:
            self.app.header_peloton_avg5.config(text="Moyenne (5 derniers): N/A")

        diff_pel_b1 = self.compute_diff_current("Peloton", "Vélo 1")
        diff_pel_tma = self.compute_diff_current("Peloton", "TMA")
        self.app.header_peloton_diff1.config(text=f"Écart vs Vélo 1: {diff_pel_b1}")
        self.app.header_peloton_diff2.config(text=f"Écart vs TMA: {diff_pel_tma}")

        # TMA
        curr_tma = self.compute_current_lap_time("TMA")
        curr_tma_str = self.format_secs_as_HHMMSS(curr_tma) if curr_tma is not None else "N/A"
        self.app.header_tma_current.config(text=f"TMA Current: {curr_tma_str}")

        avg_tma = self.compute_avg_of_last_5(self.tma_laps)
        if avg_tma:
            self.app.header_tma_avg5.config(text=f"Moyenne (5 derniers): {format_lap_duration(avg_tma)}")
        else:
            self.app.header_tma_avg5.config(text="Moyenne (5 derniers): N/A")

        diff_tma_b1 = self.compute_diff_current("TMA", "Vélo 1")
        diff_tma_pel = self.compute_diff_current("TMA", "Peloton")
        self.app.header_tma_diff1.config(text=f"Écart vs Vélo 1: {diff_tma_b1}")
        self.app.header_tma_diff2.config(text=f"Écart vs Peloton: {diff_tma_pel}")

    # -------------- Logique “Current” & écarts --------------
    def compute_current_lap_time(self, group_type):
        """
        Rend le temps (s) écoulé depuis le dernier “record” (ou start_time).
        """
        now = time.time()
        if not self.start_time:
            return None

        if group_type == "Vélo 1":
            ref = self.last_rouleur_1_time or self.start_time
        elif group_type == "Peloton":
            ref = self.last_peloton_time or self.start_time
        else:
            ref = self.last_tma_time or self.start_time

        return now - ref

    def compute_diff_current(self, groupA, groupB):
        """
        diff = tB - tA
         * si diff < 0 => A est en avance de abs(diff)
         * si diff > 0 => A est en retard de diff
        """
        tA = self.compute_current_lap_time(groupA)
        tB = self.compute_current_lap_time(groupB)
        if tA is None or tB is None:
            return "N/A"
        diff = int(tB - tA)
        if diff == 0:
            return "+0s"
        elif diff > 0:
            return f"+{diff}s"  # A est plus lent
        else:
            return f"-{abs(diff)}s"  # A est plus rapide

    def compute_avg_of_last_5(self, laps_list):
        if not laps_list:
            return None
        last_5 = laps_list[-5:]
        total_sec = 0
        count = 0
        for lap in last_5:
            dur_str = lap[4]  # ex. “0:01:20”
            val_sec = self.parse_hms_to_sec(dur_str)
            if val_sec is not None:
                total_sec += val_sec
                count += 1
        if count == 0:
            return None
        return total_sec / count

    def parse_hms_to_sec(self, timestr):
        if timestr in ("N/A", None):
            return None
        parts = timestr.split(":")
        try:
            if len(parts) == 3:
                h, m, s = int(parts[0]), int(parts[1]), int(parts[2])
                return h*3600 + m*60 + s
            elif len(parts) == 2:
                m, s = int(parts[0]), int(parts[1])
                return m*60 + s
        except:
            return None
        return None

    def format_secs_as_HHMMSS(self, secs):
        if secs < 0:
            secs = 0
        td = int(secs)
        return str(timedelta(seconds=td))

    def format_time(self, t):
        """Convertit un timestamp absolu “t” en “HH:MM:SS” depuis self.start_time."""
        if self.start_time:
            return str(timedelta(seconds=int(t - self.start_time)))
        return "N/A"

    # -------------- Stats / Export / Gérer Tours --------------
    def show_stats_window(self):
        stats_win = Toplevel(self.app.root)
        stats_win.title("Statistiques Avancées")

        (avg_bike1, min_bike1, count_bike1,
         avg_peloton, min_peloton, count_peloton) = fetch_stats_for_all()

        overall_text = (
            f"Overall Stats:\n\n"
            f"Bike 1: {count_bike1} laps, Avg Lap: {format_lap_duration(avg_bike1)}, Fastest Lap: {format_lap_duration(min_bike1)}\n\n"
            f"Peloton: {count_peloton} laps, Avg Lap: {format_lap_duration(avg_peloton)}, Fastest Lap: {format_lap_duration(min_peloton)}\n\n"
            f"TMA pas inclus par défaut."
        )
        lbl = ttk.Label(stats_win, text=overall_text, font=("Helvetica", 12))
        lbl.pack(padx=10, pady=10)

        # Stats par rider (Bike 1)
        rider_frame = ttk.Frame(stats_win)
        rider_frame.pack(padx=10, pady=10, fill="x")
        ttk.Label(rider_frame, text="Stats par Rider (Bike 1)", font=("Helvetica", 14, "bold")).pack(pady=5)

        tree = ttk.Treeview(rider_frame, columns=("rider", "laps", "avg", "fastest"), show="headings", height=10)
        tree.heading("rider", text="Rider")
        tree.heading("laps", text="Laps")
        tree.heading("avg", text="Avg Lap")
        tree.heading("fastest", text="Fastest Lap")
        tree.column("rider", width=120, anchor="center")
        tree.column("laps", width=50, anchor="center")
        tree.column("avg", width=100, anchor="center")
        tree.column("fastest", width=100, anchor="center")
        tree.pack(padx=5, pady=5)

        rows = fetch_stats_per_rider()
        for r in rows:
            rider_name, lap_count, avg_dur, min_dur = r
            tree.insert("", "end", values=(
                rider_name,
                lap_count,
                format_lap_duration(avg_dur),
                format_lap_duration(min_dur)
            ))

    def export_csv(self):
        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        if not filename:
            return
        with sqlite3.connect('data/laps_data.db') as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM laps ORDER BY id ASC")
            rows = cursor.fetchall()

        columns = ["id", "type", "lap_number", "rider_name", "lap_time", "time_diff", "cumulative_time", "lap_duration"]
        try:
            with open(filename, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(columns)
                for row in rows:
                    writer.writerow(row)
            messagebox.showinfo("Export CSV", f"Export réussi: {filename}")
        except Exception as e:
            messagebox.showerror("Export CSV", f"Erreur lors de l'export: {e}")

    def open_lap_management_window(self):
        mgmt_win = Toplevel(self.app.root)
        mgmt_win.title("Gestion des Tours")

        tree = ttk.Treeview(
            mgmt_win,
            columns=("id", "type", "lap_number", "rider_name", "lap_time", "time_diff", "cumulative_time", "lap_duration"),
            show="headings", height=20
        )
        for col in ("id", "type", "lap_number", "rider_name", "lap_time", "time_diff", "cumulative_time", "lap_duration"):
            tree.heading(col, text=col)
            tree.column(col, anchor="center", width=100)
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
        with sqlite3.connect('data/laps_data.db') as conn:
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
        current_lap_number = item[2]
        current_rider = item[3]

        new_lap_number = simpledialog.askinteger("Modifier", f"Numéro de tour (actuel: {current_lap_number}):", initialvalue=current_lap_number)
        if new_lap_number is None:
            return
        new_rider = simpledialog.askstring("Modifier", f"Nom du rider (actuel: {current_rider}):", initialvalue=current_rider)
        if new_rider is None:
            return

        with sqlite3.connect('data/laps_data.db') as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE laps SET lap_number = ?, rider_name = ? WHERE id = ?", (new_lap_number, new_rider, lap_id))
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
        with sqlite3.connect('data/laps_data.db') as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM laps WHERE id = ?", (lap_id,))
            conn.commit()
        messagebox.showinfo("Info", "Tour supprimé.")
        self.refresh_management_view(tree)
        self.reload_laps_from_db()

    def reload_laps_from_db(self):
        self.rouleur_1_laps.clear()
        self.peloton_laps.clear()
        self.tma_laps.clear()

        self.total_rouleur_1 = 0
        self.total_peloton = 0
        self.total_tma = 0

        rows = reload_from_db()
        for (lap_number, rider_name, lap_time, time_diff, lap_dur, lap_type) in rows:
            lap_number = int(lap_number)
            if lap_type == "Vélo 1":
                self.rouleur_1_laps.append((lap_number, rider_name, lap_time, time_diff, format_lap_duration(float(lap_dur))))
                self.total_rouleur_1 = max(self.total_rouleur_1, lap_number)
            elif lap_type == "Peloton":
                self.peloton_laps.append((lap_number, rider_name, lap_time, time_diff, format_lap_duration(float(lap_dur))))
                self.total_peloton = max(self.total_peloton, lap_number)
            else:
                self.tma_laps.append((lap_number, rider_name, lap_time, time_diff, format_lap_duration(float(lap_dur))))
                self.total_tma = max(self.total_tma, lap_number)

        self.app.label_rouleur_1_total.config(text=f"Total Rosaire (Bike 1): {self.total_rouleur_1}")
        self.app.label_peloton_total.config(text=f"Total Peloton: {self.total_peloton}")
        self.app.label_tma_total.config(text=f"Total TMA: {self.total_tma}")

        self.update_lap_history()
