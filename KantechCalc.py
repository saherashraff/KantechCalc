import tkinter as tk
from tkinter import ttk, messagebox
import math
import itertools
import json
import os

# --- FILE SETTINGS ---
DATA_FILE = "system_data.json"

# --- DEFAULT DATA ---
DEFAULT_NVR_DATA = [
    ["1U RAID", "ADVER00N0NP16G", 32, 50, 4, 3750.00, "RAID"],
    ["2U 64 Ch", "ADVER12R0N2H", 64, 300, 6, 10416.70, "RAID"],
    ["2U 100 Ch", "ADVER00RN2J", 100, 600, 8, 11666.70, "RAID"],
    ["2U 128 Ch", "ADVER72R5N2H", 128, 600, 12, 25000.00, "RAID"],
    ["2U Rack 175 Ch", "ADVER02RDK", 175, 1000, 12, 13854.20, "RAID"],
    ["2U Rack 200 Ch", "ADVER02RDK", 200, 1500, 12, 12812.50, "RAID"],
    ["Micro NVR", "ADVEM00N0NP8AH", 8, 80, 1, 1500.00, "JBOD"],
    ["Desktop JBOD", "ADVED00N0N5H", 50, 200, 2, 2291.70, "JBOD"],
    ["2U 75 Ch", "ADVER00N0N2J", 75, 400, 4, 5312.50, "JBOD"],
    ["Holis 8 Ch", "HRN-08013P", 8, 160, 1, 520.85, "JBOD"],
    ["Holis 16 Ch", "HRN-16023P", 16, 320, 2, 770.85, "JBOD"]
]
DEFAULT_HDD_PRICES = {1: 93.75, 2: 122.95, 4: 218.75, 6: 281.25, 8: 395.85, 10: 416.7, 12: 687.50, 14: 1041.7, 18: 1052.1, 22: 1145.85, 24: 1447.95, 26: 1700.00}

def get_best_hdd(required_tb, slots, parity, price_dict):
    if required_tb <= 1e-6: return 0, {"qty": 0, "cap": 0, "cost": 0, "total_tb": 0}
    best_h_cost, best_h_cfg = float('inf'), None
    for cap, price in sorted(price_dict.items()):
        min_d = 1 if parity == 0 else 2
        data_drives = max(math.ceil(required_tb / cap), min_d)
        total_drives = data_drives + parity
        if total_drives <= slots:
            curr_cost = total_drives * price
            if curr_cost < best_h_cost:
                best_h_cost, best_h_cfg = curr_cost, {"qty": total_drives, "cap": cap, "cost": curr_cost, "total_tb": (data_drives * cap)}
    return best_h_cost, best_h_cfg

class CCTVApp:
    def __init__(self, root):
        self.root = root
        self.root.title("CCTV MASTER V30.0 - 1% BRUTE FORCE")
        self.load_all_data()
        self.setup_ui()

    def load_all_data(self):
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, "r") as f:
                    data = json.load(f)
                    self.hdd_prices = {int(k): float(v) for k, v in data.get("hdd", DEFAULT_HDD_PRICES).items()}
                    self.nvr_list = data.get("nvr", DEFAULT_NVR_DATA)
            except:
                self.hdd_prices, self.nvr_list = DEFAULT_HDD_PRICES.copy(), [list(x) for x in DEFAULT_NVR_DATA]
        else:
            self.hdd_prices, self.nvr_list = DEFAULT_HDD_PRICES.copy(), [list(x) for x in DEFAULT_NVR_DATA]

    def save_all_data(self):
        with open(DATA_FILE, "w") as f:
            json.dump({"hdd": self.hdd_prices, "nvr": self.nvr_list}, f)

    def setup_ui(self):
        self.nb = ttk.Notebook(self.root); self.nb.pack(fill="both", expand=True, padx=5, pady=5)
        self.tabs = [ttk.Frame(self.nb) for _ in range(6)]
        titles = ["1. Cameras", "2. Auto Audit", "3. Manual Split", "4. HDD Prices", "5. NVR Prices", "6. Add NVR"]
        for tab, title in zip(self.tabs, titles): self.nb.add(tab, text=title)

        # TAB 1: CAMERAS
        f_in = ttk.Frame(self.tabs[0], padding=10); f_in.pack(fill="x")
        self.ents = {}
        for i, label in enumerate(["Name", "Qty", "Mbps", "GB"]):
            ttk.Label(f_in, text=label).grid(row=0, column=i*2)
            e = ttk.Entry(f_in, width=10); e.grid(row=0, column=i*2+1, padx=5); self.ents[label] = e
        ttk.Button(self.tabs[0], text="Add Camera", command=self.save_camera).pack(pady=5)
        self.tree = ttk.Treeview(self.tabs[0], columns=("N","Q","M","G"), show="headings"); self.tree.pack(fill="both", expand=True)
        for c, h in zip(self.tree["columns"], ["Name","Qty","Mbps","GB"]): self.tree.heading(c, text=h)

        # TAB 2: AUTO
        self.mode_var = tk.StringVar(value="RAID 5")
        f_a = ttk.Frame(self.tabs[1], padding=10); f_a.pack(fill="x")
        ttk.Combobox(f_a, textvariable=self.mode_var, values=["RAID 5", "RAID 6", "JBOD"]).pack(side="left")
        ttk.Button(f_a, text="RUN 1% ACCURACY AUTO", command=lambda: self.run_logic(True)).pack(side="left", padx=10)
        self.res_txt = tk.Text(self.tabs[1], font=("Consolas", 10)); self.res_txt.pack(fill="both", expand=True)

        # TAB 3: MANUAL
        self.manual_slots = []
        for i in range(4):
            f = ttk.Frame(self.tabs[2], padding=5); f.pack(fill="x")
            nv, mv = tk.StringVar(value="None"), tk.StringVar(value="RAID 5")
            cb = ttk.Combobox(f, textvariable=nv, width=30); cb.pack(side="left")
            ttk.Combobox(f, textvariable=mv, values=["RAID 5", "RAID 6", "JBOD"], width=10).pack(side="left", padx=5)
            self.manual_slots.append((nv, mv, cb))
        ttk.Button(self.tabs[2], text="RUN MANUAL SPLIT", command=lambda: self.run_logic(False)).pack()
        self.man_txt = tk.Text(self.tabs[2], font=("Consolas", 10), bg="#f9f9f9"); self.man_txt.pack(fill="both", expand=True)
        self.refresh_nvr_dropdowns()

        # TABS 4, 5, 6: (HDD/NVR Management - preserved from previous version)
        self.setup_management_tabs()

    def setup_management_tabs(self):
        # HDD Prices
        self.hdd_entries = {}
        f_h = ttk.Frame(self.tabs[3], padding=20); f_h.pack()
        for i, cap in enumerate(sorted(self.hdd_prices.keys())):
            r, c = divmod(i, 2)
            ttk.Label(f_h, text=f"{cap}TB: $").grid(row=r, column=c*2)
            e = ttk.Entry(f_h, width=10); e.insert(0, f"{self.hdd_prices[cap]:.2f}"); e.grid(row=r, column=c*2+1)
            self.hdd_entries[cap] = e
        ttk.Button(self.tabs[3], text="Save HDD Prices", command=self.save_hdd_ui).pack()
        # NVR Prices
        self.nvr_container = ttk.Frame(self.tabs[4]); self.nvr_container.pack(fill="both", expand=True, padx=20, pady=20)
        self.refresh_nvr_price_tab()
        # Add NVR
        f_new = ttk.Frame(self.tabs[5], padding=20); f_new.pack()
        self.new_nvr_fields = {}
        for i, lab in enumerate(["Name", "SKU", "CH", "MB", "Slots", "Price"]):
            ttk.Label(f_new, text=lab).grid(row=i, column=0, sticky="w")
            e = ttk.Entry(f_new); e.grid(row=i, column=1); self.new_nvr_fields[lab] = e
        self.new_nvr_arch = tk.StringVar(value="RAID")
        ttk.Combobox(f_new, textvariable=self.new_nvr_arch, values=["RAID", "JBOD"]).grid(row=6, column=1)
        ttk.Button(f_new, text="ADD NVR", command=self.add_new_nvr).grid(row=7, columnspan=2)

    def refresh_nvr_dropdowns(self):
        names = ["None"] + [n[1] for n in self.nvr_list]
        for nv, _, cb in self.manual_slots: cb['values'] = names

    def refresh_nvr_price_tab(self):
        for widget in self.nvr_container.winfo_children(): widget.destroy()
        self.nvr_price_entries = []
        for i, nvr in enumerate(self.nvr_list):
            ttk.Label(self.nvr_container, text=f"{nvr[0]}").grid(row=i, column=0, sticky="w")
            e = ttk.Entry(self.nvr_container, width=15); e.insert(0, f"{nvr[5]:.2f}"); e.grid(row=i, column=1)
            self.nvr_price_entries.append(e)
        ttk.Button(self.nvr_container, text="Save NVR Prices", command=self.save_nvr_prices_ui).grid(row=len(self.nvr_list), columnspan=2)

    def add_new_nvr(self):
        try:
            row = [self.new_nvr_fields[x].get() for x in ["Name", "SKU"]] + [int(self.new_nvr_fields[x].get()) for x in ["CH", "MB", "Slots"]] + [float(self.new_nvr_fields["Price"].get()), self.new_nvr_arch.get()]
            self.nvr_list.append(row); self.save_all_data(); self.refresh_nvr_dropdowns(); self.refresh_nvr_price_tab()
        except: messagebox.showerror("Error", "Check inputs")

    def save_hdd_ui(self):
        try:
            for cap, ent in self.hdd_entries.items(): self.hdd_prices[cap] = float(ent.get())
            self.save_all_data(); messagebox.showinfo("Saved", "HDD database updated.")
        except: messagebox.showerror("Error", "Invalid prices.")

    def save_nvr_prices_ui(self):
        try:
            for i, ent in enumerate(self.nvr_price_entries): self.nvr_list[i][5] = float(ent.get())
            self.save_all_data(); messagebox.showinfo("Saved", "NVR prices updated.")
        except: messagebox.showerror("Error", "Invalid prices.")

    def save_camera(self):
        v = [self.ents[k].get() for k in ["Name", "Qty", "Mbps", "GB"]]
        if all(v): self.tree.insert("", "end", values=v)

    def run_logic(self, auto):
        cams = []
        for i in self.tree.get_children():
            v = self.tree.item(i)['values']
            cams.append({"name": v[0], "qty": int(v[1]), "mbps": float(v[2]), "tb": float(v[3])/1024})
        if not cams: return
        
        best_cfg, best_total_cost = None, float('inf')
        mode = self.mode_var.get()
        parity = 1 if mode == "RAID 5" else 2 if mode == "RAID 6" else 0
        search_list = [n for n in self.nvr_list if n[6] == "RAID"] if parity > 0 else self.nvr_list

        if auto:
            # Check 1 NVR and 2 NVR combos
            for num_units in range(1, 3):
                for combo in itertools.combinations_with_replacement(search_list, num_units):
                    # --- 1% INCREMENT LOGIC ---
                    splits = [1.0] if num_units == 1 else [x/100.0 for x in range(1, 100)]
                    for r1 in splits:
                        u_list, cur_cams = [], [dict(c) for c in cams]
                        ratios = [r1, 1.0-r1] if num_units == 2 else [1.0]
                        valid = True
                        for i, ratio in enumerate(ratios):
                            u_brk, u_mb, u_tb, u_c = {}, 0, 0, 0
                            for c in cur_cams:
                                # First NVR gets the floor, second gets the remainder
                                take = math.floor(c['qty']*ratio) if i == 0 and num_units > 1 else c['qty']
                                u_brk[c['name']] = take; u_mb += take*c['mbps']; u_tb += take*c['tb']; u_c += take
                                c['qty'] -= take
                            
                            hc, hd = get_best_hdd(u_tb, combo[i][4], parity, self.hdd_prices)
                            if hd and u_c <= combo[i][2] and u_mb <= combo[i][3]:
                                u_list.append({"m": combo[i], "c_total": u_c, "cam_breakdown": u_brk, "mb": u_mb, "tb": u_tb, "h": hd, "mode": mode})
                            else: valid = False; break
                        
                        if valid:
                            total = sum(u['m'][5] + u['h']['cost'] for u in u_list)
                            if total < best_total_cost: best_total_cost, best_cfg = total, {"total": total, "units": u_list}
        
        txt = self.res_txt if auto else self.man_txt
        txt.delete("1.0", tk.END)
        if best_cfg:
            report = f"--- RESULT ---\nTOTAL COST: ${best_cfg['total']:,.2f}\n" + "="*50 + "\n"
            for i, u in enumerate(best_cfg['units']):
                report += f"UNIT #{i+1}: {u['m'][0]} | CAMS: {u['c_total']}\n"
                for cn, cq in u['cam_breakdown'].items():
                    if cq > 0: report += f"  - {cn}: {cq}\n"
                report += f"Storage: {u['h']['qty']}x {u['h']['cap']}TB\n\n"
            txt.insert("1.0", report)
        else: txt.insert("1.0", "NO SOLUTION FOUND")

if __name__ == "__main__":
    root = tk.Tk(); root.geometry("1100x900"); app = CCTVApp(root); root.mainloop()
