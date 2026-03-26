import tkinter as tk
from tkinter import ttk, messagebox
import math

# ─────────────────────────── NVR & Storage Data ────────────────────────────

NVR_DATA = {
    "American Dynamics": [
        {"name": "Micro",                        "part": "ADVEM00N0NP8AH",  "cameras": 8,   "throughput": 80,   "drives": 1,  "raid": "JBOD", "price": 1500.0,   "max_storage_tb": 12},
        {"name": "1U",                           "part": "ADVER00N0NP16G",  "cameras": 32,  "throughput": 100,  "drives": 4,  "raid": "JBOD", "price": 3750.0,   "max_storage_tb": 24},
        {"name": "Compact Desktop",              "part": "ADVED00N0N5G",    "cameras": 32,  "throughput": 100,  "drives": 1,  "raid": "JBOD", "price": 2500.0,   "max_storage_tb": 12},
        {"name": "Desktop",                      "part": "ADVED00N0N5H",    "cameras": 50,  "throughput": 200,  "drives": 2,  "raid": "JBOD", "price": 2291.7,   "max_storage_tb": 40},
        {"name": "2U 64 Channels",               "part": "ADVER12R0N2H",    "cameras": 64,  "throughput": 300,  "drives": 6,  "raid": "RAID", "price": 10416.7,  "max_storage_tb": 60},
        {"name": "2U 75 Channels",               "part": "ADVER00N0N2J",    "cameras": 75,  "throughput": 400,  "drives": 4,  "raid": "JBOD", "price": 5312.5,   "max_storage_tb": 48},
        {"name": "2U 100 Channels",              "part": "ADVER00RN2J",     "cameras": 100, "throughput": 600,  "drives": 8,  "raid": "RAID", "price": 11666.7,  "max_storage_tb": 112},
        {"name": "2U High Cap 128 Channels",     "part": "ADVER72R5N2H",    "cameras": 128, "throughput": 600,  "drives": 12, "raid": "RAID", "price": 25000.0,  "max_storage_tb": 120},
        {"name": "2U High Cap 175 Channels",     "part": "ADVER00RN2K",     "cameras": 175, "throughput": 1000, "drives": 12, "raid": "RAID", "price": 13854.2,  "max_storage_tb": 200},
        {"name": "2U Rack Mount",                "part": "ADVER02RDK",      "cameras": 200, "throughput": 1500, "drives": 12, "raid": "RAID", "price": 12812.5,  "max_storage_tb": 200},
    ],
    "Holis": [
        {"name": "Holis 8 Channels",  "part": "HRN-08013P", "cameras": 8,  "throughput": 0, "drives": 1, "raid": "JBOD", "price": 520.85,  "max_storage_tb": 10},
        {"name": "Holis 16 Channels", "part": "HRN-16023P", "cameras": 16, "throughput": 0, "drives": 1, "raid": "JBOD", "price": 770.85,  "max_storage_tb": 10},
    ],
}

# Storage unit options: (TB per disk, price per unit)
STORAGE_UNITS = [
    (1,  63.157895),
    (2,  94.715789),
    (3,  105.263158),
    (4,  168.421053),
    (6,  215.789474),
    (8,  306.421053),
    (10, 355.536842),
    (12, 442.105263),
    (14, 617.983651),
    (18, 720.55),
    (22, 685.286104),
    (24, 863.487738),
    (26, 822.888283),
]

# ─────────────────────────────── Logic ─────────────────────────────────────

def calculate(num_cameras, throughput_per_camera, retention_days, preferred_raid, preferred_brand, disk_size_tb):
    total_throughput = num_cameras * throughput_per_camera  # Mbps

    # Storage: Mbps → MB/s → GB/day → TB total
    mbps = throughput_per_camera
    gb_per_day = (mbps / 8) * 3600 * 24 / 1024  # MB/s * seconds/day / 1024
    total_storage_tb = (gb_per_day * retention_days * num_cameras) / 1024

    results = []

    for brand, nvrs in NVR_DATA.items():
        if preferred_brand != "Any" and brand != preferred_brand:
            continue
        for nvr in nvrs:
            # Filter by RAID preference
            if preferred_raid != "Any" and nvr["raid"] != preferred_raid:
                continue
            if throughput_per_camera > 0 and nvr["throughput"] > 0 and total_throughput > nvr["throughput"]:
                # Check if multiple units can share load — yes, count how many needed
                pass

            nvrs_needed_cam = math.ceil(num_cameras / nvr["cameras"])
            nvrs_needed_tp = 1
            if nvr["throughput"] > 0:
                nvrs_needed_tp = math.ceil(total_throughput / nvr["throughput"])
            nvrs_needed = max(nvrs_needed_cam, nvrs_needed_tp)

            # Storage disks per NVR
            storage_per_nvr_tb = total_storage_tb / nvrs_needed
            disks_per_nvr = math.ceil(storage_per_nvr_tb / disk_size_tb)
            total_disks = disks_per_nvr * nvrs_needed

            # Cost
            nvr_total_cost = nvr["price"] * nvrs_needed
            disk_price = next((p for tb, p in STORAGE_UNITS if tb == disk_size_tb), None)
            disk_total_cost = (disk_price * total_disks) if disk_price else 0

            results.append({
                "brand": brand,
                "name": nvr["name"],
                "part": nvr["part"],
                "raid": nvr["raid"],
                "nvrs_needed": nvrs_needed,
                "cameras_per_nvr": math.ceil(num_cameras / nvrs_needed),
                "throughput_required": total_throughput,
                "throughput_available": nvr["throughput"] * nvrs_needed if nvr["throughput"] > 0 else "N/A",
                "total_storage_tb": total_storage_tb,
                "disks_per_nvr": disks_per_nvr,
                "total_disks": total_disks,
                "disk_size_tb": disk_size_tb,
                "nvr_unit_price": nvr["price"],
                "nvr_total_cost": nvr_total_cost,
                "disk_total_cost": disk_total_cost,
                "grand_total": nvr_total_cost + disk_total_cost,
            })

    results.sort(key=lambda x: x["grand_total"])
    return results, total_storage_tb

# ─────────────────────────────── GUI ───────────────────────────────────────

DARK_BG     = "#0f1117"
PANEL_BG    = "#181c24"
ACCENT      = "#00d4ff"
ACCENT2     = "#7c3aed"
TEXT_MAIN   = "#e8eaf0"
TEXT_DIM    = "#8892a4"
SUCCESS     = "#22c55e"
WARNING     = "#f59e0b"
DANGER      = "#ef4444"
BORDER      = "#2a3040"
ENTRY_BG    = "#1e2433"
BTN_BG      = "#00d4ff"
BTN_FG      = "#0f1117"
ROW_ALT     = "#1a1f2e"
ROW_HOVER   = "#232a3b"

FONT_TITLE  = ("Courier New", 22, "bold")
FONT_SUB    = ("Courier New", 11)
FONT_LABEL  = ("Segoe UI", 10, "bold")
FONT_VALUE  = ("Segoe UI", 10)
FONT_SMALL  = ("Segoe UI", 9)
FONT_MONO   = ("Courier New", 10)
FONT_BTN    = ("Segoe UI", 11, "bold")


class NVRCalculator(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("NVR & Storage Calculator")
        self.configure(bg=DARK_BG)
        self.geometry("1280x800")
        self.minsize(900, 600)
        self._build_ui()

    def _build_ui(self):
        # ── Header ──
        hdr = tk.Frame(self, bg=DARK_BG)
        hdr.pack(fill="x", padx=28, pady=(22, 0))

        tk.Label(hdr, text="NVR  &  STORAGE  CALCULATOR",
                 font=FONT_TITLE, fg=ACCENT, bg=DARK_BG).pack(side="left")
        tk.Label(hdr, text="American Dynamics · Holis",
                 font=FONT_SUB, fg=TEXT_DIM, bg=DARK_BG).pack(side="left", padx=(18, 0), pady=(8, 0))

        # Separator
        sep = tk.Frame(self, bg=ACCENT2, height=2)
        sep.pack(fill="x", padx=28, pady=(10, 0))

        # ── Body ──
        body = tk.Frame(self, bg=DARK_BG)
        body.pack(fill="both", expand=True, padx=28, pady=16)

        # Left: inputs
        left = tk.Frame(body, bg=PANEL_BG, bd=0, relief="flat",
                        highlightbackground=BORDER, highlightthickness=1)
        left.pack(side="left", fill="y", padx=(0, 14), ipadx=18, ipady=18)

        # Right: results
        right = tk.Frame(body, bg=DARK_BG)
        right.pack(side="left", fill="both", expand=True)

        self._build_inputs(left)
        self._build_results(right)

    def _build_inputs(self, parent):
        tk.Label(parent, text="CONFIGURATION", font=("Segoe UI", 9, "bold"),
                 fg=ACCENT, bg=PANEL_BG, letter_spacing=2).pack(anchor="w", padx=4, pady=(4, 12))

        fields = [
            ("Number of Cameras",         "num_cameras",          "213"),
            ("Throughput per Camera (Mbps)", "throughput",         "3.12"),
            ("Retention Period (Days)",    "retention_days",       "30"),
            ("Disk Size (TB)",             "disk_size",            "10"),
        ]

        self.vars = {}
        for label, key, default in fields:
            row = tk.Frame(parent, bg=PANEL_BG)
            row.pack(fill="x", pady=6, padx=4)
            tk.Label(row, text=label, font=FONT_LABEL, fg=TEXT_DIM,
                     bg=PANEL_BG, anchor="w", width=26).pack(side="left")
            var = tk.StringVar(value=default)
            self.vars[key] = var
            ent = tk.Entry(row, textvariable=var, font=FONT_VALUE,
                           bg=ENTRY_BG, fg=TEXT_MAIN, insertbackground=ACCENT,
                           relief="flat", bd=0, highlightthickness=1,
                           highlightbackground=BORDER, highlightcolor=ACCENT, width=10)
            ent.pack(side="left", padx=(8, 0), ipady=4, ipadx=6)

        # Dropdowns
        self._add_dropdown(parent, "RAID / JBOD Preference", "raid_pref",
                           ["Any", "RAID", "JBOD"])
        self._add_dropdown(parent, "Brand Preference", "brand_pref",
                           ["Any", "American Dynamics", "Holis"])

        # Divider
        tk.Frame(parent, bg=BORDER, height=1).pack(fill="x", padx=4, pady=16)

        # Calculate button
        btn = tk.Button(parent, text="  CALCULATE  ", font=FONT_BTN,
                        bg=ACCENT, fg=BTN_FG, relief="flat", bd=0,
                        activebackground="#00b8d9", activeforeground=BTN_FG,
                        cursor="hand2", command=self._calculate,
                        padx=12, pady=8)
        btn.pack(fill="x", padx=4)

        # Summary panel
        tk.Frame(parent, bg=BORDER, height=1).pack(fill="x", padx=4, pady=16)
        tk.Label(parent, text="SUMMARY", font=("Segoe UI", 9, "bold"),
                 fg=ACCENT, bg=PANEL_BG).pack(anchor="w", padx=4)
        self.summary_frame = tk.Frame(parent, bg=PANEL_BG)
        self.summary_frame.pack(fill="x", padx=4, pady=(8, 0))

    def _add_dropdown(self, parent, label, key, options):
        row = tk.Frame(parent, bg=PANEL_BG)
        row.pack(fill="x", pady=6, padx=4)
        tk.Label(row, text=label, font=FONT_LABEL, fg=TEXT_DIM,
                 bg=PANEL_BG, anchor="w", width=26).pack(side="left")
        var = tk.StringVar(value=options[0])
        self.vars[key] = var
        combo = ttk.Combobox(row, textvariable=var, values=options,
                             state="readonly", width=12, font=FONT_VALUE)
        combo.pack(side="left", padx=(8, 0))
        # Style
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TCombobox",
                        fieldbackground=ENTRY_BG, background=ENTRY_BG,
                        foreground=TEXT_MAIN, bordercolor=BORDER,
                        arrowcolor=ACCENT, selectbackground=ENTRY_BG,
                        selectforeground=TEXT_MAIN)

    def _build_results(self, parent):
        tk.Label(parent, text="MATCHING NVR SOLUTIONS", font=("Segoe UI", 9, "bold"),
                 fg=ACCENT, bg=DARK_BG).pack(anchor="w", pady=(0, 8))

        # Table
        cols = ("Brand", "NVR Model", "RAID", "# NVRs", "Cams/NVR",
                "Throughput (Mbps)", "Storage (TB)", "Disks/NVR", "Total Disks",
                "Disk Size", "NVR Cost ($)", "Disk Cost ($)", "Total ($)")

        style = ttk.Style()
        style.configure("Dark.Treeview",
                        background=PANEL_BG, foreground=TEXT_MAIN,
                        fieldbackground=PANEL_BG, borderwidth=0,
                        rowheight=28, font=FONT_VALUE)
        style.configure("Dark.Treeview.Heading",
                        background=ENTRY_BG, foreground=ACCENT,
                        borderwidth=0, font=("Segoe UI", 9, "bold"), relief="flat")
        style.map("Dark.Treeview",
                  background=[("selected", ACCENT2)],
                  foreground=[("selected", "#ffffff")])
        style.layout("Dark.Treeview", [("Dark.Treeview.treearea", {"sticky": "nswe"})])

        frame = tk.Frame(parent, bg=DARK_BG)
        frame.pack(fill="both", expand=True)

        self.tree = ttk.Treeview(frame, columns=cols, show="headings",
                                 style="Dark.Treeview", selectmode="browse")

        col_widths = [120, 190, 55, 55, 70, 125, 95, 75, 80, 75, 95, 95, 90]
        for col, w in zip(cols, col_widths):
            self.tree.heading(col, text=col)
            self.tree.column(col, width=w, anchor="center", minwidth=50)

        vsb = ttk.Scrollbar(frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        style.configure("Vertical.TScrollbar", background=BORDER, troughcolor=PANEL_BG,
                        arrowcolor=ACCENT)
        style.configure("Horizontal.TScrollbar", background=BORDER, troughcolor=PANEL_BG,
                        arrowcolor=ACCENT)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)

        self.tree.tag_configure("jbod", background=PANEL_BG)
        self.tree.tag_configure("raid", background=ROW_ALT)
        self.tree.tag_configure("best", background="#14271a", foreground=SUCCESS)

        # Detail panel below
        detail = tk.Frame(parent, bg=PANEL_BG,
                          highlightbackground=BORDER, highlightthickness=1)
        detail.pack(fill="x", pady=(10, 0), ipady=10)
        self.detail_label = tk.Label(detail,
            text="Select a row to see details · Results sorted by total cost (lowest first)",
            font=FONT_SMALL, fg=TEXT_DIM, bg=PANEL_BG, justify="left", anchor="w")
        self.detail_label.pack(padx=14, pady=4, anchor="w")

        self.tree.bind("<<TreeviewSelect>>", self._on_select)

    def _on_select(self, event):
        sel = self.tree.selection()
        if not sel:
            return
        item = self.tree.item(sel[0])["values"]
        if not item or not hasattr(self, "_results"):
            return
        idx = self.tree.index(sel[0])
        if idx >= len(self._results):
            return
        r = self._results[idx]
        ta = r["throughput_available"]
        ta_str = f"{ta} Mbps" if ta != "N/A" else "N/A"
        detail = (
            f"  ▸  {r['brand']}  ·  {r['name']}  ({r['part']})  ·  {r['raid']}   "
            f"│  NVRs: {r['nvrs_needed']}  "
            f"│  Cams/NVR: {r['cameras_per_nvr']}  "
            f"│  Required throughput: {r['throughput_required']:.1f} Mbps  "
            f"│  Available: {ta_str}  "
            f"│  Total storage: {r['total_storage_tb']:.2f} TB  "
            f"│  Disks/NVR: {r['disks_per_nvr']} × {r['disk_size_tb']} TB  "
            f"│  Total disks: {r['total_disks']}  "
            f"│  Grand total: ${r['grand_total']:,.2f}"
        )
        self.detail_label.config(text=detail, fg=TEXT_MAIN)

    def _calculate(self):
        try:
            num_cameras   = int(self.vars["num_cameras"].get())
            throughput    = float(self.vars["throughput"].get())
            retention     = int(self.vars["retention_days"].get())
            disk_size     = int(self.vars["disk_size"].get())
            raid_pref     = self.vars["raid_pref"].get()
            brand_pref    = self.vars["brand_pref"].get()
        except ValueError:
            messagebox.showerror("Input Error", "Please enter valid numeric values.")
            return

        if disk_size not in [tb for tb, _ in STORAGE_UNITS]:
            messagebox.showerror("Disk Size",
                f"Disk size {disk_size} TB is not available.\n"
                f"Available: {[tb for tb, _ in STORAGE_UNITS]}")
            return

        results, total_storage_tb = calculate(
            num_cameras, throughput, retention, raid_pref, brand_pref, disk_size)

        # Clear tree
        for item in self.tree.get_children():
            self.tree.delete(item)

        self._results = results

        for i, r in enumerate(results):
            ta = r["throughput_available"]
            ta_str = str(ta) if ta == "N/A" else f"{ta}"
            tag = "best" if i == 0 else ("raid" if r["raid"] == "RAID" else "jbod")
            self.tree.insert("", "end", values=(
                r["brand"],
                r["name"],
                r["raid"],
                r["nvrs_needed"],
                r["cameras_per_nvr"],
                f"{r['throughput_required']:.1f} / {ta_str}",
                f"{r['total_storage_tb']:.2f}",
                r["disks_per_nvr"],
                r["total_disks"],
                f"{r['disk_size_tb']} TB",
                f"${r['nvr_total_cost']:,.0f}",
                f"${r['disk_total_cost']:,.0f}",
                f"${r['grand_total']:,.0f}",
            ), tags=(tag,))

        # Summary
        for w in self.summary_frame.winfo_children():
            w.destroy()

        def sumrow(label, value, color=TEXT_MAIN):
            row = tk.Frame(self.summary_frame, bg=PANEL_BG)
            row.pack(fill="x", pady=2)
            tk.Label(row, text=label, font=FONT_SMALL, fg=TEXT_DIM,
                     bg=PANEL_BG, width=22, anchor="w").pack(side="left")
            tk.Label(row, text=value, font=("Segoe UI", 10, "bold"),
                     fg=color, bg=PANEL_BG, anchor="w").pack(side="left")

        total_tp = num_cameras * throughput
        sumrow("Cameras:", str(num_cameras))
        sumrow("Throughput/cam:", f"{throughput} Mbps")
        sumrow("Total throughput:", f"{total_tp:.1f} Mbps")
        sumrow("Retention:", f"{retention} days")
        sumrow("Storage needed:", f"{total_storage_tb:.2f} TB", ACCENT)
        sumrow("Disk size:", f"{disk_size} TB")
        sumrow("Solutions found:", str(len(results)), SUCCESS if results else DANGER)

        if results:
            best = results[0]
            sumrow("Best option:", best["name"], SUCCESS)
            sumrow("Best cost:", f"${best['grand_total']:,.0f}", SUCCESS)

        self.detail_label.config(
            text="  ★  Best match highlighted in green  ·  Click any row for details",
            fg=TEXT_DIM)


if __name__ == "__main__":
    app = NVRCalculator()
    app.mainloop()
