import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, BooleanVar

from .core import CyclingCore
from .simulation import SimulationManager
from .utils import format_lap_duration

class CyclingEventApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Chronomètre 24h - Vélo du Bois de la Cambre")
        self.root.geometry("1200x700")

        self.core = CyclingCore(self)
        self.simulation = SimulationManager(self)

        self.build_ui()

        # Lance la mise à jour en continu (chaque seconde)
        self.core.update_timer()

    def build_ui(self):
        # 1) Top Frame : chrono principal + totaux
        top_frame = ttk.Frame(self.root)
        top_frame.grid(row=0, column=0, columnspan=4, pady=10, sticky="w")

        self.label_elapsed = ttk.Label(top_frame, text="00:00:00", font=("Helvetica", 24))
        self.label_elapsed.pack(side="left", padx=20)

        start_button = ttk.Button(top_frame, text="Démarrer 24h", command=self.core.start_24h)
        start_button.pack(side="left", padx=10)

        # Totaux
        self.label_rouleur_1_total = ttk.Label(top_frame, text="Total Rosaire (Bike 1): 0", font=("Helvetica", 12))
        self.label_rouleur_1_total.pack(side="left", padx=10)

        self.label_peloton_total = ttk.Label(top_frame, text="Total Peloton: 0", font=("Helvetica", 12))
        self.label_peloton_total.pack(side="left", padx=10)

        self.label_tma_total = ttk.Label(top_frame, text="Total TMA: 0", font=("Helvetica", 12))
        self.label_tma_total.pack(side="left", padx=10)

        # 2) Buttons
        buttons_frame = ttk.Frame(self.root)
        buttons_frame.grid(row=1, column=0, columnspan=4, pady=10)

        btn_rouleur1 = ttk.Button(buttons_frame, text="Tour Vélo 1", command=self.core.record_rouleur_1)
        btn_rouleur1.grid(row=0, column=0, padx=5)

        btn_peloton = ttk.Button(buttons_frame, text="Tour Peloton", command=self.core.record_peloton)
        btn_peloton.grid(row=0, column=1, padx=5)

        btn_tma = ttk.Button(buttons_frame, text="Tour TMA", command=self.core.record_tma)
        btn_tma.grid(row=0, column=2, padx=5)

        # Bloc “Sélection multiple”
        selection_box = ttk.Labelframe(buttons_frame, text="Sélection multiple")
        selection_box.grid(row=0, column=3, padx=5)

        self.chk_bike1 = BooleanVar(value=False)
        self.chk_peloton = BooleanVar(value=False)
        self.chk_tma = BooleanVar(value=False)

        c1 = ttk.Checkbutton(selection_box, text="Vélo 1", variable=self.chk_bike1)
        c1.pack(anchor="w")
        c2 = ttk.Checkbutton(selection_box, text="Peloton", variable=self.chk_peloton)
        c2.pack(anchor="w")
        c3 = ttk.Checkbutton(selection_box, text="TMA", variable=self.chk_tma)
        c3.pack(anchor="w")

        btn_selection = ttk.Button(selection_box, text="Tour sélection", command=self.record_selection)
        btn_selection.pack(pady=5)

        dummy_button = ttk.Button(buttons_frame, text="Ajouter Tour Manuellement", command=self.core.add_dummy_lap)
        dummy_button.grid(row=0, column=4, padx=5)

        undo_button = ttk.Button(buttons_frame, text="Annuler Dernier Tour", command=self.core.undo_last_lap)
        undo_button.grid(row=0, column=5, padx=5)

        reset_button = ttk.Button(buttons_frame, text="Réinitialiser", command=self.core.reset_laps)
        reset_button.grid(row=0, column=6, padx=5)

        manage_button = ttk.Button(buttons_frame, text="Gérer Tours", command=self.core.open_lap_management_window)
        manage_button.grid(row=0, column=7, padx=5)

        # 3) Rider selection
        selection_frame = ttk.Frame(self.root)
        selection_frame.grid(row=2, column=0, columnspan=4, pady=5, sticky="w")

        ttk.Label(selection_frame, text="Sélectionnez le rouleur (Bike 1):", font=("Helvetica", 12)).pack(side="left", padx=5)
        self.rider_selector = ttk.Combobox(selection_frame, values=self.core.riders, state="readonly")
        self.rider_selector.current(0)
        self.rider_selector.pack(side="left", padx=5)

        add_rider_button = ttk.Button(selection_frame, text="+", command=self.core.add_new_rider)
        add_rider_button.pack(side="left", padx=5)

        # 4) Gap display
        self.label_gap = ttk.Label(self.root, text="Current gap: N/A", font=("Helvetica", 14, "bold"), foreground="red")
        self.label_gap.grid(row=3, column=0, columnspan=4, pady=10)

        # 5) Tables + entêtes
        tables_frame = ttk.Frame(self.root)
        tables_frame.grid(row=4, column=0, columnspan=4, pady=10)

        # Bike1
        bike1_frame = ttk.Frame(tables_frame)
        bike1_frame.pack(side="left", padx=10)
        self.build_table_with_header(bike1_frame, "Vélo 1")

        # Peloton
        peloton_frame = ttk.Frame(tables_frame)
        peloton_frame.pack(side="left", padx=10)
        self.build_table_with_header(peloton_frame, "Peloton")

        # TMA
        tma_frame = ttk.Frame(tables_frame)
        tma_frame.pack(side="left", padx=10)
        self.build_table_with_header(tma_frame, "TMA")

        # 6) Stats, Export, Simulation
        bottom_frame = ttk.Frame(self.root)
        bottom_frame.grid(row=5, column=0, columnspan=4, pady=10)

        stats_button = ttk.Button(bottom_frame, text="Voir Statistiques", command=self.core.show_stats_window)
        stats_button.pack(side="left", padx=5)

        export_button = ttk.Button(bottom_frame, text="Exporter CSV", command=self.core.export_csv)
        export_button.pack(side="left", padx=5)

        sim_frame = ttk.Labelframe(bottom_frame, text="Simulation")
        sim_frame.pack(side="left", padx=10)

        ttk.Label(sim_frame, text="Durée (min, float) :").pack(side="left", padx=5)
        self.sim_duration_entry = ttk.Entry(sim_frame, width=7)
        self.sim_duration_entry.insert(0, "4.0")
        self.sim_duration_entry.pack(side="left", padx=5)

        sim_button = ttk.Button(sim_frame, text="Démarrer", command=self.start_sim_with_duration)
        sim_button.pack(side="left", padx=5)

    def build_table_with_header(self, parent_frame, type_label):
        header_frame = ttk.Frame(parent_frame)
        header_frame.pack(side="top", fill="x")

        # Current
        label_current = ttk.Label(header_frame, text=f"{type_label} Current: 00:00", font=("Helvetica", 14, "bold"))
        label_current.pack(anchor="w")

        # Moyenne 5 derniers
        label_avg5 = ttk.Label(header_frame, text="Moyenne (5 derniers): N/A", font=("Helvetica", 10))
        label_avg5.pack(anchor="w")

        # Écarts
        label_diff1 = ttk.Label(header_frame, text="Écart vs X: N/A", font=("Helvetica", 10))
        label_diff1.pack(anchor="w")
        label_diff2 = ttk.Label(header_frame, text="Écart vs Y: N/A", font=("Helvetica", 10))
        label_diff2.pack(anchor="w")

        # Tableau
        labelframe = ttk.LabelFrame(parent_frame, text=f"Derniers tours {type_label}")
        labelframe.pack(side="top")

        tree = ttk.Treeview(
            labelframe,
            columns=("lapnum", "rider", "laptime", "timediff", "lapdur"),
            show="headings", height=10
        )
        for col, head in zip(
            ("lapnum", "rider", "laptime", "timediff", "lapdur"),
            ("Lap #", "Rider", "Lap Time", "Time Diff", "Lap Duration")
        ):
            tree.heading(col, text=head)
            tree.column(col, width=90, anchor="center")
        tree.column("lapnum", width=60)
        tree.pack(side="left")

        scroll = ttk.Scrollbar(labelframe, orient="vertical", command=tree.yview)
        scroll.pack(side="right", fill="y")
        tree.configure(yscrollcommand=scroll.set)

        # Stocke les références
        if type_label == "Vélo 1":
            self.header_bike1_current = label_current
            self.header_bike1_avg5 = label_avg5
            self.header_bike1_diff1 = label_diff1
            self.header_bike1_diff2 = label_diff2
            self.bike1_tree = tree
        elif type_label == "Peloton":
            self.header_peloton_current = label_current
            self.header_peloton_avg5 = label_avg5
            self.header_peloton_diff1 = label_diff1
            self.header_peloton_diff2 = label_diff2
            self.peloton_tree = tree
        else:
            self.header_tma_current = label_current
            self.header_tma_avg5 = label_avg5
            self.header_tma_diff1 = label_diff1
            self.header_tma_diff2 = label_diff2
            self.tma_tree = tree

    def record_selection(self):
        checked = []
        if self.chk_bike1.get():
            checked.append("Vélo 1")
        if self.chk_peloton.get():
            checked.append("Peloton")
        if self.chk_tma.get():
            checked.append("TMA")

        if not checked:
            messagebox.showinfo("Info", "Aucune sélection cochée.")
            return

        for grp in checked:
            if grp == "Vélo 1":
                self.core.record_rouleur_1()
            elif grp == "Peloton":
                self.core.record_peloton()
            else:
                self.core.record_tma()

    def start_sim_with_duration(self):
        val = self.sim_duration_entry.get().strip().replace(",", ".")
        try:
            valf = float(val)
            if valf <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Erreur", "Veuillez saisir un nombre > 0 (ex: 2.5 pour 2min30).")
            return
        duration_secs = valf * 60
        self.simulation.start_simulation(duration=duration_secs)

    def run(self):
        self.root.mainloop()
