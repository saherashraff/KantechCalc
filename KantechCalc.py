#!/usr/bin/env python3
"""
NVR & Storage Calculator — Tkinter GUI
Run: python nvr_calculator.py
"""
import math, re, time, threading
import tkinter as tk
from tkinter import ttk, messagebox, font as tkfont

# ─────────────────────────── Data ──────────────────────────────────────────

NVR_DATA = {
    "American Dynamics": [
        {"name": "Micro",                    "part": "ADVEM00N0NP8AH",  "cameras": 8,   "throughput": 80,   "raid": "JBOD", "price": 1500.0,  "max_drives": 1},
        {"name": "1UJ",                       "part": "ADVER00N0NP16G",  "cameras": 32,  "throughput": 100,  "raid": "JBOD", "price": 3750.0,  "max_drives": 4},
        {"name": "1UR",                       "part": "ADVER00N0NP16G",  "cameras": 32,  "throughput": 50,  "raid": "RAID", "price": 3750.0,  "max_drives": 4},
	{"name": "Compact Desktop",          "part": "ADVED00N0N5G",    "cameras": 32,  "throughput": 100,  "raid": "JBOD", "price": 2500.0,  "max_drives": 1},
        {"name": "Desktop",                  "part": "ADVED00N0N5H",    "cameras": 50,  "throughput": 200,  "raid": "JBOD", "price": 2291.7,  "max_drives": 2},
        {"name": "2U 64 Channels",           "part": "ADVER12R0N2H",    "cameras": 64,  "throughput": 300,  "raid": "RAID", "price": 10416.7, "max_drives": 6},
        {"name": "2U 75 Channels",           "part": "ADVER00N0N2J",    "cameras": 75,  "throughput": 400,  "raid": "JBOD", "price": 5312.5,  "max_drives": 4},
        {"name": "2U 100 Channels",          "part": "ADVER00RN2J",     "cameras": 100, "throughput": 600,  "raid": "RAID", "price": 11666.7, "max_drives": 8},
        {"name": "2U High Cap 128 Channels", "part": "ADVER72R5N2H",    "cameras": 128, "throughput": 600,  "raid": "RAID", "price": 25000.0, "max_drives": 12},
        {"name": "2U High Cap 175 Channels", "part": "ADVER00RN2K",     "cameras": 175, "throughput": 1000, "raid": "RAID", "price": 13854.2, "max_drives": 12},
        {"name": "2U Rack Mount",            "part": "ADVER02RDK",      "cameras": 200, "throughput": 1500, "raid": "RAID", "price": 12812.5, "max_drives": 12},
    ],
    "Holis": [
        {"name": "Holis 8 Channels",  "part": "HRN-08013P", "cameras": 8,  "throughput": 0, "raid": "JBOD", "price": 520.85,  "max_drives": 1},
        {"name": "Holis 16 Channels", "part": "HRN-16023P", "cameras": 16, "throughput": 0, "raid": "JBOD", "price": 770.85,  "max_drives": 1},
    ],
}

DISK_FALLBACK = {
    1: 63.16,  2: 94.72,   3: 105.26,  4: 168.42,
    6: 215.79, 8: 306.42,  10: 355.54, 12: 442.11,
    14: 617.98, 18: 720.55, 20: 750.0,  22: 685.29,
    24: 863.49, 26: 822.89,
}

# ─────────────────────────── Colors ────────────────────────────────────────

BG       = "#0f1520"
SURFACE  = "#151d2e"
SURFACE2 = "#1a2540"
BORDER   = "#253046"
ACCENT   = "#00d4ff"
ACCENT_D = "#0099bb"
GREEN    = "#22d3a5"
GOLD     = "#f59e0b"
RED      = "#f87171"
TEXT     = "#e2e8f0"
TEXT2    = "#7a90b0"
TEXT3    = "#3d5070"
WHITE    = "#ffffff"

# ─────────────────────────── Calculation Logic ─────────────────────────────

def parity_drives(raid_type):
    return {"RAID5": 1, "RAID6": 2}.get(raid_type, 0)

def min_drives_for_raid(raid_type):
    return {"RAID5": 3, "RAID6": 4}.get(raid_type, 1)

def optimize_disk_config(storage_needed_tb, max_drives, raid_type, disk_catalog):
    if not disk_catalog:
        return None
    best = None
    if raid_type == "JBOD":
        for size_tb, price in disk_catalog.items():
            n = max(1, math.ceil(storage_needed_tb / size_tb))
            if n > max_drives:
                continue
            cost = n * price
            if best is None or cost < best["cost"]:
                best = {"drives": n, "drive_size_tb": size_tb,
                        "usable_tb": n * size_tb, "cost": cost,
                        "config": f"{n} x {size_tb} TB  (JBOD)",
                        "price_per_disk": price, "parity": 0}
    else:
        min_d = min_drives_for_raid(raid_type)
        par   = parity_drives(raid_type)
        for size_tb, price in disk_catalog.items():
            for total_d in range(min_d, max_drives + 1):
                data_d = total_d - par
                if data_d < 1:
                    continue
                usable = data_d * size_tb
                if usable < storage_needed_tb:
                    continue
                cost = total_d * price
                if best is None or cost < best["cost"]:
                    best = {"drives": total_d, "drive_size_tb": size_tb,
                            "usable_tb": usable, "cost": cost,
                            "config": f"{total_d} x {size_tb} TB  ({data_d} data + {par} parity, {raid_type})",
                            "price_per_disk": price, "parity": par}
    return best

def calculate(camera_groups, retention_days, raid_pref, brand_pref, disk_catalog, raid_type_pref):
    total_cameras    = sum(g["count"] for g in camera_groups)
    total_throughput = sum(g["count"] * g["throughput_mbps"] for g in camera_groups)
    total_storage_tb = 0.0
    for g in camera_groups:
        gb_per_day        = (g["throughput_mbps"] / 8) * 86400 / 1024
        total_storage_tb += (gb_per_day * retention_days * g["count"]) / 1024

    results = []
    for brand, nvrs in NVR_DATA.items():
        if brand_pref != "any" and brand.lower() != brand_pref.lower():
            continue
        for nvr in nvrs:
            nvr_raid = nvr["raid"]
            if raid_pref != "any" and nvr_raid.lower() != raid_pref.lower():
                continue
            effective_raid = (raid_type_pref if raid_type_pref in ("RAID5","RAID6") else "RAID5") \
                             if nvr_raid == "RAID" else "JBOD"

            nvrs_cam = math.ceil(total_cameras / nvr["cameras"])
            nvrs_tp  = math.ceil(total_throughput / nvr["throughput"]) if nvr["throughput"] > 0 else 1
            nvrs_n   = max(nvrs_cam, nvrs_tp)

            disk_cfg = optimize_disk_config(total_storage_tb / nvrs_n, nvr["max_drives"], effective_raid, disk_catalog)
            if disk_cfg is None:
                continue

            nvr_cost  = nvr["price"] * nvrs_n
            disk_cost = disk_cfg["cost"] * nvrs_n
            results.append({
                "brand": brand, "name": nvr["name"], "part": nvr["part"],
                "effective_raid": effective_raid, "nvrs": nvrs_n,
                "cams_per_nvr": math.ceil(total_cameras / nvrs_n),
                "tp_required": round(total_throughput, 1),
                "tp_available": nvr["throughput"] * nvrs_n if nvr["throughput"] > 0 else None,
                "storage_tb": round(total_storage_tb, 2),
                "disk_cfg": disk_cfg,
                "total_drives": disk_cfg["drives"] * nvrs_n,
                "nvr_cost": round(nvr_cost, 2),
                "disk_cost": round(disk_cost, 2),
                "grand_total": round(nvr_cost + disk_cost, 2),
                "nvr_unit_price": nvr["price"],
            })

    results.sort(key=lambda x: x["grand_total"])
    return results, round(total_storage_tb, 2), total_cameras, round(total_throughput, 1)

def fetch_amazon_prices(sizes_tb, callback):
    """Runs in a background thread. Calls callback(prices_dict, errors_list)."""
    try:
        import requests
        from bs4 import BeautifulSoup
    except ImportError:
        callback({}, ["requests / beautifulsoup4 not installed.\nRun:  pip install requests beautifulsoup4"])
        return

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9,ar;q=0.8",
    }
    prices, errors = {}, []
    session = requests.Session()
    session.headers.update(headers)

    for size_tb in sizes_tb:
        url = f"https://www.amazon.eg/s?k={size_tb}TB+internal+hard+disk+HDD&i=electronics"
        try:
            resp  = session.get(url, timeout=12)
            soup  = BeautifulSoup(resp.text, "html.parser")
            items = soup.select('[data-component-type="s-search-result"]')
            found = False
            for item in items:
                te = item.select_one("h2 a span")
                pe = item.select_one(".a-price .a-offscreen")
                if not te or not pe:
                    continue
                raw = pe.get_text(strip=True)
                num = re.sub(r"[^\d.,]", "", raw.replace("٬","").replace("٫",".")).replace(",","")
                try:
                    prices[size_tb] = float(num)
                    found = True
                    break
                except ValueError:
                    continue
            if not found:
                errors.append(f"{size_tb} TB: not found")
            time.sleep(0.6)
        except Exception as e:
            errors.append(f"{size_tb} TB: {e}")

    callback(prices, errors)

# ─────────────────────────── GUI Helpers ───────────────────────────────────

def styled_frame(parent, bg=SURFACE, **kw):
    return tk.Frame(parent, bg=bg, **kw)

def label(parent, text, size=10, bold=False, color=TEXT, bg=SURFACE, anchor="w", **kw):
    weight = "bold" if bold else "normal"
    return tk.Label(parent, text=text, bg=bg, fg=color,
                    font=("Segoe UI", size, weight), anchor=anchor, **kw)

def entry(parent, textvariable=None, width=14, **kw):
    e = tk.Entry(parent, textvariable=textvariable, width=width,
                 bg=SURFACE2, fg=TEXT, insertbackground=ACCENT,
                 relief="flat", bd=0, font=("Consolas", 10), **kw)
    # Draw border via highlight
    e.config(highlightthickness=1, highlightbackground=BORDER, highlightcolor=ACCENT)
    return e

def separator(parent, bg=BORDER):
    return tk.Frame(parent, bg=bg, height=1)

# ─────────────────────────── Camera Group Row ──────────────────────────────

class CameraGroupRow:
    def __init__(self, parent, idx, on_remove):
        self.idx = idx
        self.frame = styled_frame(parent, bg=SURFACE2)
        self.frame.pack(fill="x", pady=3)

        inner = styled_frame(self.frame, bg=SURFACE2)
        inner.pack(fill="x", padx=10, pady=8)

        label(inner, f"Type {idx}", size=9, color=ACCENT, bg=SURFACE2).grid(row=0, column=0, sticky="w", padx=(0,12))

        label(inner, "Name", size=9, color=TEXT2, bg=SURFACE2).grid(row=0, column=1, sticky="w")
        self.name_var = tk.StringVar(value=f"Type {idx}")
        entry(inner, textvariable=self.name_var, width=14).grid(row=0, column=2, padx=(4,12))

        label(inner, "Cameras", size=9, color=TEXT2, bg=SURFACE2).grid(row=0, column=3, sticky="w")
        self.count_var = tk.StringVar(value="64")
        entry(inner, textvariable=self.count_var, width=7).grid(row=0, column=4, padx=(4,12))

        label(inner, "Throughput (Mbps)", size=9, color=TEXT2, bg=SURFACE2).grid(row=0, column=5, sticky="w")
        self.tp_var = tk.StringVar(value="3.12")
        entry(inner, textvariable=self.tp_var, width=8).grid(row=0, column=6, padx=(4,12))

        if idx > 1:
            btn = tk.Button(inner, text="Remove", bg=SURFACE, fg=RED,
                            font=("Segoe UI", 9), relief="flat", bd=0,
                            activebackground=SURFACE, activeforeground=RED,
                            cursor="hand2", command=lambda: on_remove(self))
            btn.grid(row=0, column=7, padx=(4,0))

    def get_data(self):
        return {
            "name":           self.name_var.get().strip() or f"Type {self.idx}",
            "count":          int(self.count_var.get()),
            "throughput_mbps": float(self.tp_var.get()),
        }

# ─────────────────────────── Main Application ──────────────────────────────

class NVRApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("NVR & Storage Calculator")
        self.configure(bg=BG)
        self.geometry("1100x780")
        self.minsize(900, 600)

        self.disk_catalog = dict(DISK_FALLBACK)
        self.cam_rows     = []
        self.cam_row_idx  = 0

        self._apply_styles()
        self._build_ui()

    # ── ttk styles ────────────────────────────────────────────────────────
    def _apply_styles(self):
        s = ttk.Style(self)
        s.theme_use("clam")

        s.configure("Treeview",
            background=SURFACE, foreground=TEXT,
            fieldbackground=SURFACE, rowheight=26,
            font=("Consolas", 9), borderwidth=0)
        s.configure("Treeview.Heading",
            background=SURFACE2, foreground=ACCENT,
            font=("Segoe UI", 9, "bold"), relief="flat", borderwidth=0)
        s.map("Treeview",
            background=[("selected", ACCENT_D)],
            foreground=[("selected", WHITE)])
        s.map("Treeview.Heading", relief=[("active","flat")])

        s.configure("Vertical.TScrollbar",
            background=BORDER, troughcolor=SURFACE, arrowcolor=TEXT2,
            borderwidth=0, relief="flat")
        s.configure("Horizontal.TScrollbar",
            background=BORDER, troughcolor=SURFACE, arrowcolor=TEXT2,
            borderwidth=0, relief="flat")

        s.configure("TCombobox",
            fieldbackground=SURFACE2, background=SURFACE2,
            foreground=TEXT, bordercolor=BORDER,
            arrowcolor=ACCENT, selectbackground=SURFACE2,
            selectforeground=TEXT, insertcolor=ACCENT)
        s.map("TCombobox",
            fieldbackground=[("readonly", SURFACE2)],
            foreground=[("readonly", TEXT)])

    # ── Build layout ──────────────────────────────────────────────────────
    def _build_ui(self):
        # ── Header ──────────────────────────────────────────────────────
        hdr = styled_frame(self, bg=BG)
        hdr.pack(fill="x", padx=24, pady=(20,0))

        label(hdr, "NVR & Storage Calculator", size=18, bold=True,
              color=WHITE, bg=BG).pack(side="left")
        label(hdr, "  American Dynamics  ·  Holis", size=10,
              color=TEXT3, bg=BG).pack(side="left", pady=(6,0))

        separator(self).pack(fill="x", padx=24, pady=12)

        # ── Two-column body ──────────────────────────────────────────────
        body = styled_frame(self, bg=BG)
        body.pack(fill="both", expand=True, padx=24, pady=(0,16))
        body.columnconfigure(0, weight=0, minsize=380)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)

        left  = styled_frame(body, bg=BG)
        left.grid(row=0, column=0, sticky="nsew", padx=(0,16))

        right = styled_frame(body, bg=BG)
        right.grid(row=0, column=1, sticky="nsew")

        self._build_left(left)
        self._build_right(right)

    # ── Left panel ────────────────────────────────────────────────────────
    def _build_left(self, parent):
        parent.columnconfigure(0, weight=1)

        # ─ Camera Types ─────────────────────────────────────────────────
        self._section_label(parent, "1  Camera Configuration")

        cam_outer = styled_frame(parent, bg=SURFACE)
        cam_outer.pack(fill="x", pady=(0,14))

        self.cam_container = styled_frame(cam_outer, bg=SURFACE)
        self.cam_container.pack(fill="x", padx=2, pady=2)

        self._add_cam_row()   # start with one row

        btn_add = tk.Button(cam_outer, text="+ Add Camera Type",
                            bg=SURFACE2, fg=ACCENT,
                            font=("Segoe UI", 9), relief="flat", bd=0,
                            activebackground=BORDER, activeforeground=ACCENT,
                            cursor="hand2", pady=6, command=self._add_cam_row)
        btn_add.pack(fill="x", padx=2, pady=(0,2))

        # ─ Storage settings ──────────────────────────────────────────────
        self._section_label(parent, "2  Storage & RAID Settings")

        s_frame = styled_frame(parent, bg=SURFACE)
        s_frame.pack(fill="x", pady=(0,14))
        s_inner = styled_frame(s_frame, bg=SURFACE)
        s_inner.pack(fill="x", padx=14, pady=12)

        # Retention
        row1 = styled_frame(s_inner, bg=SURFACE)
        row1.pack(fill="x", pady=4)
        label(row1, "Retention Period (days)", size=9, color=TEXT2, bg=SURFACE, width=22).pack(side="left")
        self.retention_var = tk.StringVar(value="30")
        entry(row1, textvariable=self.retention_var, width=8).pack(side="left", padx=(8,0))

        # Brand
        row2 = styled_frame(s_inner, bg=SURFACE)
        row2.pack(fill="x", pady=4)
        label(row2, "Brand Preference", size=9, color=TEXT2, bg=SURFACE, width=22).pack(side="left")
        self.brand_var = tk.StringVar(value="Any")
        cb_brand = ttk.Combobox(row2, textvariable=self.brand_var, width=20,
                                state="readonly",
                                values=["Any", "American Dynamics", "Holis"])
        cb_brand.pack(side="left", padx=(8,0))

        # NVR Mode
        row3 = styled_frame(s_inner, bg=SURFACE)
        row3.pack(fill="x", pady=4)
        label(row3, "NVR Mode", size=9, color=TEXT2, bg=SURFACE, width=22).pack(side="left")
        self.raid_pref_var = tk.StringVar(value="Any")
        for val in ("Any", "RAID", "JBOD"):
            rb = tk.Radiobutton(row3, text=val, variable=self.raid_pref_var,
                                value=val, bg=SURFACE, fg=TEXT2,
                                selectcolor=SURFACE2, activebackground=SURFACE,
                                activeforeground=TEXT,
                                font=("Segoe UI", 9),
                                command=self._on_raid_pref_change)
            rb.pack(side="left", padx=(8,0))

        # RAID Level
        self.raid_level_frame = styled_frame(s_inner, bg=SURFACE)
        self.raid_level_frame.pack(fill="x", pady=4)
        label(self.raid_level_frame, "RAID Level", size=9, color=TEXT2, bg=SURFACE, width=22).pack(side="left")
        self.raid_type_var = tk.StringVar(value="RAID5")
        for val, desc in (("RAID5", "RAID 5  (1 parity)"), ("RAID6", "RAID 6  (2 parity)")):
            rb = tk.Radiobutton(self.raid_level_frame, text=desc,
                                variable=self.raid_type_var, value=val,
                                bg=SURFACE, fg=TEXT2, selectcolor=SURFACE2,
                                activebackground=SURFACE, activeforeground=TEXT,
                                font=("Segoe UI", 9))
            rb.pack(side="left", padx=(8,0))

        # ─ Disk Pricing ──────────────────────────────────────────────────
        self._section_label(parent, "3  Disk Pricing  (EGP)")

        p_frame = styled_frame(parent, bg=SURFACE)
        p_frame.pack(fill="x", pady=(0,14))
        p_inner = styled_frame(p_frame, bg=SURFACE)
        p_inner.pack(fill="x", padx=14, pady=10)

        btn_fetch = tk.Button(p_inner, text="Fetch Live Prices from amazon.eg",
                              bg=ACCENT_D, fg=WHITE,
                              font=("Segoe UI", 9, "bold"), relief="flat", bd=0,
                              activebackground=ACCENT, activeforeground=WHITE,
                              cursor="hand2", pady=6,
                              command=self._fetch_amazon)
        btn_fetch.pack(fill="x", pady=(0,6))

        self.price_status = label(p_inner, "Using built-in fallback prices", size=9,
                                  color=TEXT2, bg=SURFACE)
        self.price_status.pack(anchor="w", pady=(0,8))

        # Grid of price fields
        pg = styled_frame(p_inner, bg=SURFACE)
        pg.pack(fill="x")
        self.price_vars = {}
        sizes = sorted(DISK_FALLBACK.keys())
        for i, s in enumerate(sizes):
            col, row = (i % 4) * 2, i // 4
            label(pg, f"{s} TB", size=9, color=TEXT2, bg=SURFACE, width=5).grid(
                row=row, column=col, sticky="w", pady=3)
            var = tk.StringVar(value=str(DISK_FALLBACK[s]))
            self.price_vars[s] = var
            entry(pg, textvariable=var, width=8).grid(
                row=row, column=col+1, padx=(2,14), pady=3)

        # ─ Calculate button ───────────────────────────────────────────────
        separator(parent).pack(fill="x", pady=10)

        self.calc_btn = tk.Button(parent, text="Calculate",
                                  bg=ACCENT, fg="#000000",
                                  font=("Segoe UI", 12, "bold"), relief="flat", bd=0,
                                  activebackground=ACCENT_D, activeforeground=WHITE,
                                  cursor="hand2", pady=10,
                                  command=self._run_calculation)
        self.calc_btn.pack(fill="x")

        self.status_label = label(parent, "", size=9, color=TEXT2, bg=BG, anchor="center")
        self.status_label.pack(pady=(6,0))

    # ── Right panel ───────────────────────────────────────────────────────
    def _build_right(self, parent):
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(1, weight=1)

        # Summary row
        self.summary_frame = styled_frame(parent, bg=SURFACE)
        self.summary_frame.pack(fill="x", pady=(0,12))
        self._render_summary(None)

        # Results label
        res_hdr = styled_frame(parent, bg=BG)
        res_hdr.pack(fill="x", pady=(0,6))
        label(res_hdr, "Results", size=12, bold=True, color=WHITE, bg=BG).pack(side="left")
        self.results_count_lbl = label(res_hdr, "", size=9, color=TEXT2, bg=BG)
        self.results_count_lbl.pack(side="left", padx=12, pady=2)

        # Treeview
        tree_frame = styled_frame(parent, bg=BG)
        tree_frame.pack(fill="both", expand=True)
        tree_frame.columnconfigure(0, weight=1)
        tree_frame.rowconfigure(0, weight=1)

        cols = ("rank","brand","model","mode","nvrs","cam_nvr",
                "req_mbps","avail_mbps","storage","disk_cfg","nvr_cost","disk_cost","total")
        hdrs = ("#","Brand","Model","Mode","NVRs","Cam/NVR",
                "Req Mbps","Avail Mbps","Storage TB","Disk Config",
                "NVR Cost","Disk Cost","Total $")
        widths = (30,140,180,65,45,60,70,80,80,220,80,80,90)

        self.tree = ttk.Treeview(tree_frame, columns=cols, show="headings",
                                  selectmode="browse")
        for col, hdr, w in zip(cols, hdrs, widths):
            self.tree.heading(col, text=hdr)
            anchor = "w" if col in ("brand","model","disk_cfg") else "center"
            self.tree.column(col, width=w, minwidth=30, anchor=anchor)

        vsb = ttk.Scrollbar(tree_frame, orient="vertical",   command=self.tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.tree.tag_configure("best",  background="#0d2d1e", foreground=GREEN)
        self.tree.tag_configure("odd",   background=SURFACE)
        self.tree.tag_configure("even",  background=SURFACE2)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)

        # Detail panel
        separator(parent).pack(fill="x", pady=(8,0))
        self.detail_frame = styled_frame(parent, bg=SURFACE)
        self.detail_frame.pack(fill="x", pady=(8,0))
        self.detail_lbl = label(self.detail_frame,
                                "Select a row to see full details",
                                size=9, color=TEXT2, bg=SURFACE)
        self.detail_lbl.pack(anchor="w", padx=12, pady=8)

    # ── Section label helper ──────────────────────────────────────────────
    def _section_label(self, parent, text):
        f = styled_frame(parent, bg=BG)
        f.pack(fill="x", pady=(8,4))
        label(f, text, size=10, bold=True, color=ACCENT, bg=BG).pack(side="left")

    # ── Camera rows ───────────────────────────────────────────────────────
    def _add_cam_row(self):
        self.cam_row_idx += 1
        row = CameraGroupRow(self.cam_container, self.cam_row_idx, self._remove_cam_row)
        self.cam_rows.append(row)

    def _remove_cam_row(self, row):
        row.frame.destroy()
        self.cam_rows.remove(row)

    # ── RAID pref change ─────────────────────────────────────────────────
    def _on_raid_pref_change(self):
        pref = self.raid_pref_var.get()
        state = "normal" if pref in ("Any","RAID") else "disabled"
        for child in self.raid_level_frame.winfo_children():
            if isinstance(child, tk.Radiobutton):
                child.config(state=state)

    # ── Amazon fetch ─────────────────────────────────────────────────────
    def _fetch_amazon(self):
        self.price_status.config(text="Fetching prices from amazon.eg ...", fg=GOLD)
        self.update()
        sizes = sorted(DISK_FALLBACK.keys())

        def done(prices, errors):
            if prices:
                for s, p in prices.items():
                    if s in self.price_vars:
                        self.price_vars[s].set(f"{p:.2f}")
                msg = f"Updated {len(prices)} prices from amazon.eg"
                if errors:
                    msg += f"  ({len(errors)} fallback)"
                self.price_status.config(text=msg, fg=GREEN)
            else:
                err_str = errors[0] if errors else "Unknown error"
                self.price_status.config(text=f"Fetch failed: {err_str[:60]}", fg=RED)

        def worker():
            fetch_amazon_prices(sizes, lambda p, e: self.after(0, lambda: done(p, e)))

        threading.Thread(target=worker, daemon=True).start()

    # ── Run calculation ───────────────────────────────────────────────────
    def _run_calculation(self):
        # Collect camera groups
        camera_groups = []
        for row in self.cam_rows:
            try:
                data = row.get_data()
                if data["count"] <= 0:
                    raise ValueError("Camera count must be > 0")
                camera_groups.append(data)
            except Exception as e:
                messagebox.showerror("Input Error", f"Camera group {row.idx}: {e}")
                return

        if not camera_groups:
            messagebox.showerror("Input Error", "Add at least one camera group.")
            return

        try:
            retention = int(self.retention_var.get())
            if retention < 1:
                raise ValueError
        except ValueError:
            messagebox.showerror("Input Error", "Retention period must be a positive integer.")
            return

        # Collect disk prices
        disk_catalog = {}
        for s, var in self.price_vars.items():
            try:
                p = float(var.get())
                if p > 0:
                    disk_catalog[s] = p
            except ValueError:
                pass
        if not disk_catalog:
            messagebox.showerror("Input Error", "No valid disk prices found.")
            return

        raid_pref      = self.raid_pref_var.get().lower()
        brand_pref     = self.brand_var.get()
        raid_type_pref = self.raid_type_var.get()

        self.calc_btn.config(state="disabled", text="Calculating...")
        self.status_label.config(text="", fg=TEXT2)
        self.update()

        try:
            results, total_storage_tb, total_cams, total_tp = calculate(
                camera_groups, retention, raid_pref, brand_pref,
                disk_catalog, raid_type_pref
            )
        except Exception as e:
            messagebox.showerror("Calculation Error", str(e))
            self.calc_btn.config(state="normal", text="Calculate")
            return

        self._render_summary({
            "total_cams": total_cams,
            "total_tp": total_tp,
            "storage_tb": total_storage_tb,
            "retention": retention,
            "groups": len(camera_groups),
            "solutions": len(results),
        })
        self._render_results(results)
        self.calc_btn.config(state="normal", text="Calculate")

        if results:
            self.status_label.config(
                text=f"Best: {results[0]['brand']} {results[0]['name']}  —  ${results[0]['grand_total']:,.0f}",
                fg=GREEN)
        else:
            self.status_label.config(text="No solutions found. Try relaxing filters.", fg=RED)

    # ── Summary bar ───────────────────────────────────────────────────────
    def _render_summary(self, data):
        for w in self.summary_frame.winfo_children():
            w.destroy()

        items = []
        if data:
            items = [
                ("Cameras",    str(data["total_cams"])),
                ("Throughput", f"{data['total_tp']:.1f} Mbps"),
                ("Storage",    f"{data['storage_tb']:.2f} TB"),
                ("Retention",  f"{data['retention']} days"),
                ("Cam Types",  str(data["groups"])),
                ("Solutions",  str(data["solutions"])),
            ]
        else:
            items = [("Cameras","—"),("Throughput","—"),("Storage","—"),
                     ("Retention","—"),("Cam Types","—"),("Solutions","—")]

        for i, (lbl, val) in enumerate(items):
            cell = styled_frame(self.summary_frame, bg=SURFACE2 if i % 2 == 0 else SURFACE)
            cell.pack(side="left", expand=True, fill="both")
            label(cell, lbl, size=8, color=TEXT3, bg=cell["bg"], anchor="center").pack(pady=(8,2))
            color = ACCENT if lbl == "Storage" else (GREEN if lbl == "Solutions" else TEXT)
            label(cell, val, size=11, bold=True, color=color, bg=cell["bg"], anchor="center").pack(pady=(0,8))

    # ── Results table ─────────────────────────────────────────────────────
    def _render_results(self, results):
        for item in self.tree.get_children():
            self.tree.delete(item)

        self._results = results
        self.results_count_lbl.config(
            text=f"{len(results)} result{'s' if len(results)!=1 else ''}")

        for i, r in enumerate(results):
            ta  = f"{int(r['tp_available'])}" if r["tp_available"] else "N/A"
            cfg = r["disk_cfg"]["config"]
            tag = "best" if i == 0 else ("odd" if i % 2 == 1 else "even")
            self.tree.insert("", "end", iid=str(i), tags=(tag,), values=(
                "★" if i == 0 else str(i+1),
                r["brand"],
                r["name"],
                r["effective_raid"],
                r["nvrs"],
                r["cams_per_nvr"],
                f"{r['tp_required']:.0f}",
                ta,
                f"{r['storage_tb']:.2f}",
                cfg,
                f"${r['nvr_cost']:,.0f}",
                f"${r['disk_cost']:,.0f}",
                f"${r['grand_total']:,.0f}",
            ))

        self.detail_lbl.config(text="Select a row to see full details", fg=TEXT2)

    # ── Row detail ────────────────────────────────────────────────────────
    def _on_tree_select(self, event):
        sel = self.tree.selection()
        if not sel or not hasattr(self, "_results"):
            return
        idx = int(sel[0])
        if idx >= len(self._results):
            return
        r   = self._results[idx]
        cfg = r["disk_cfg"]
        ta  = f"{int(r['tp_available'])} Mbps" if r["tp_available"] else "N/A"

        txt = (
            f"  {r['brand']}  |  {r['name']}  ({r['part']})  |  {r['effective_raid']}   "
            f"      NVRs: {r['nvrs']}   Cams/NVR: {r['cams_per_nvr']}   "
            f"Throughput: {r['tp_required']:.0f} Mbps req / {ta} avail   "
            f"Storage: {r['storage_tb']:.2f} TB   "
            f"Disks/NVR: {cfg['drives']} x {cfg['drive_size_tb']} TB   "
            f"Total drives: {r['total_drives']}   "
            f"Usable: {cfg['usable_tb']:.1f} TB/NVR   "
            f"NVR: ${r['nvr_cost']:,.0f}   Disks: ${r['disk_cost']:,.0f}   "
            f"Grand Total: ${r['grand_total']:,.0f}"
        )
        color = GREEN if idx == 0 else TEXT
        self.detail_lbl.config(text=txt, fg=color, wraplength=self.detail_frame.winfo_width()-24)


# ─────────────────────────── Entry Point ───────────────────────────────────

if __name__ == "__main__":
    app = NVRApp()
    app.mainloop()
