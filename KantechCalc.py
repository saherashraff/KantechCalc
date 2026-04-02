import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import math
import itertools
import json
import os
from datetime import datetime

# --- DATA PERSISTENCE ---
DATA_FILE = "system_data.json"

# UPDATED HDD PRICES AS PER YOUR REQUEST
DEFAULT_HDD_PRICES = {
    1: 87.00, 2: 131.00, 3: 145.00, 4: 239.00, 6: 375.00, 
    8: 427.00, 10: 500.00, 12: 614.00, 14: 1114.00, 
    18: 1291.00, 22: 1226.00, 24: 1568.00, 26: 2600.00
}

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

def get_best_hdd(required_tb, slots, parity, price_dict):
    if required_tb <= 1e-6: return 0, {"qty": 0, "cap": 0, "cost": 0, "total_tb": 0}
    best_h_cost, best_h_cfg = float('inf'), None
    # Sort capacities to ensure we check smallest to largest
    for cap in sorted(price_dict.keys()):
        price = price_dict[cap]
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
        self.root.title("CCTV MASTER V33.4 - UPDATED PRICING")
        self.last_report = ""
        self.load_all_data()
        self.setup_ui()

    def load_all_data(self):
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, "r") as f:
                    data = json.load(f)
                    self.hdd_prices = {int(k): float(v) for k, v in data.get("hdd", DEFAULT_HDD_PRICES).items()}
                    self.nvr_list = data.get("nvr", DEFAULT_NVR_DATA)
            except: self.hdd_prices, self.nvr_list = DEFAULT_HDD_PRICES.copy(), [list(x) for x in DEFAULT_NVR_DATA]
        else: self.hdd_prices, self.nvr_list = DEFAULT_HDD_PRICES.copy(), [list(x) for x in DEFAULT_NVR_DATA]

    def save_all_data(self):
        with open(DATA_FILE, "w") as f: json.dump({"hdd": self.hdd_prices, "nvr": self.nvr_list}, f)

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
            e = ttk.Entry(f_in, width=12); e.grid(row=0, column=i*2+1, padx=5); self.ents[label] = e
        btn_f = ttk.Frame(self.tabs[0]); btn_f.pack(pady=5)
        ttk.Button(btn_f, text="Add/Update", command=self.save_camera).pack(side="left", padx=5)
        ttk.Button(btn_f, text="Delete", command=self.delete_camera).pack(side="left", padx=5)
        self.tree = ttk.Treeview(self.tabs[0], columns=("N","Q","M","G"), show="headings", selectmode="browse"); self.tree.pack(fill="both", expand=True)
        for c, h in zip(self.tree["columns"], ["Name","Qty","Mbps","GB"]): self.tree.heading(c, text=h)
        self.tree.bind("<Double-1>", self.load_camera_to_edit)

        # LOGIC TABS
        self.mode_var = tk.StringVar(value="RAID 5")
        f_a = ttk.Frame(self.tabs[1], padding=10); f_a.pack(fill="x")
        ttk.Combobox(f_a, textvariable=self.mode_var, values=["RAID 5", "RAID 6", "JBOD"], state="readonly").pack(side="left")
        ttk.Button(f_a, text="RUN AUTO", command=lambda: self.run_logic(True)).pack(side="left", padx=10)
        self.res_txt = tk.Text(self.tabs[1], font=("Consolas", 10)); self.res_txt.pack(fill="both", expand=True)

        self.manual_slots = []
        for i in range(5):
            f = ttk.Frame(self.tabs[2], padding=5); f.pack(fill="x")
            nv, mv = tk.StringVar(value="None"), tk.StringVar(value="RAID 5")
            cb = ttk.Combobox(f, textvariable=nv, width=35, state="readonly"); cb.pack(side="left")
            ttk.Combobox(f, textvariable=mv, values=["RAID 5", "RAID 6", "JBOD"], width=10, state="readonly").pack(side="left", padx=5)
            self.manual_slots.append((nv, mv, cb))
        ttk.Button(self.tabs[2], text="CALCULATE MANUAL", command=lambda: self.run_logic(False)).pack(pady=5)
        ttk.Button(self.tabs[2], text="Export to File", command=self.export_to_file).pack(pady=2)
        self.man_txt = tk.Text(self.tabs[2], font=("Consolas", 10), bg="#f4f4f4"); self.man_txt.pack(fill="both", expand=True)
        
        self.refresh_nvr_dropdowns(); self.setup_mgt()

    def load_camera_to_edit(self, event):
        item = self.tree.selection()[0]; vals = self.tree.item(item)['values']
        for k, v in zip(["Name", "Qty", "Mbps", "GB"], vals): self.ents[k].delete(0, tk.END); self.ents[k].insert(0, v)

    def save_camera(self):
        v = [self.ents[k].get() for k in ["Name", "Qty", "Mbps", "GB"]]
        if all(v): 
            for item in self.tree.get_children():
                if str(self.tree.item(item)['values'][0]) == v[0]: self.tree.delete(item)
            self.tree.insert("", "end", values=v)

    def delete_camera(self): 
        for s in self.tree.selection(): self.tree.delete(s)

    def refresh_nvr_dropdowns(self):
        names = ["None"] + [n[1] for n in self.nvr_list]
        for nv, _, cb in self.manual_slots: cb['values'] = names

    def generate_detailed_report(self, cfg, title):
        report = f"{'='*80}\n{title} SYSTEM DESIGN SPECIFICATION\n{'='*80}\n"
        report += f"TOTAL SYSTEM COST: ${cfg['total']:,.2f}\n\n"
        for i, u in enumerate(cfg['units']):
            report += f"UNIT #{i+1} [SKU: {u['m'][1]}]\n{'-'*40}\n"
            report += f"  Model: {u['m'][0]} ({u['mode']})\n  Cameras: {u['c_total']} Total Units\n"
            for c_n, c_q in u['cam_breakdown'].items():
                if c_q > 0: report += f"    - {c_n}: {c_q}\n"
            report += f"  Throughput: {u['mb']:.2f} / {u['m'][3]} Mbps\n"
            report += f"  Storage: {u['h']['qty']}x {u['h']['cap']}TB ({u['h']['total_tb']:.2f} TB Usable)\n"
            report += f"  HDD Cost: ${u['h']['cost']:,.2f}\n\n"
        self.last_report = report
        return report

    def setup_mgt(self):
        self.hdd_entries = {}
        fh = ttk.Frame(self.tabs[3], padding=20); fh.pack()
        for i, cap in enumerate(sorted(self.hdd_prices.keys())):
            r, c = divmod(i, 2); ttk.Label(fh, text=f"{cap}TB: $").grid(row=r, column=c*2)
            e = ttk.Entry(fh, width=10); e.insert(0, f"{self.hdd_prices[cap]:.2f}"); e.grid(row=r, column=c*2+1); self.hdd_entries[cap] = e
        ttk.Button(self.tabs[3], text="Save HDDs", command=self.save_hdd_ui).pack()
        self.nvr_container = ttk.Frame(self.tabs[4]); self.nvr_container.pack(fill="both", expand=True)
        self.refresh_nvr_price_tab()

    def save_hdd_ui(self):
        for c, e in self.hdd_entries.items(): self.hdd_prices[c] = float(e.get())
        self.save_all_data(); messagebox.showinfo("Saved", "HDD Prices Updated")

    def refresh_nvr_price_tab(self):
        for w in self.nvr_container.winfo_children(): w.destroy()
        self.npe = []
        for i, n in enumerate(self.nvr_list):
            ttk.Label(self.nvr_container, text=f"{n[0]}").grid(row=i, column=0); e = ttk.Entry(self.nvr_container, width=12)
            e.insert(0, f"{n[5]:.2f}"); e.grid(row=i, column=1); self.npe.append(e)
        ttk.Button(self.nvr_container, text="Update", command=lambda: messagebox.showinfo("Info", "Use Add NVR tab to update list")).grid(row=len(self.nvr_list), columnspan=2)

    def export_to_file(self):
        if self.last_report:
            f = filedialog.asksaveasfilename(defaultextension=".txt"); 
            if f: 
                with open(f, "w") as file: file.write(self.last_report)

    def calculate_units(self, cam_list, hw_config, use_even_split=False):
        u_list, cur_cams = [], [dict(c) for c in cam_list]
        num = len(hw_config)
        for i in range(num):
            u_brk, u_mb, u_tb, u_c = {}, 0, 0, 0
            for c in cur_cams:
                take = math.ceil(c['qty'] / (num - i)) if use_even_split else c['qty']
                take = min(c['qty'], take)
                u_brk[c['name']] = take; u_mb += take * c['mbps']; u_tb += take * c['tb']; u_c += take
                c['qty'] -= take
            hc, hd = get_best_hdd(u_tb, hw_config[i]['m'][4], hw_config[i]['p'], self.hdd_prices)
            fails = []
            if u_c > hw_config[i]['m'][2]: fails.append(f"CH({u_c}/{hw_config[i]['m'][2]})")
            if u_mb > hw_config[i]['m'][3]: fails.append(f"MB({u_mb}/{hw_config[i]['m'][3]})")
            if not hd: fails.append("HDD Slots")
            if fails: return None, fails
            u_list.append({"m": hw_config[i]['m'], "c_total": u_c, "cam_breakdown": u_brk, "mb": u_mb, "tb": u_tb, "h": hd, "mode": hw_config[i]['mode']})
        return u_list, None

    def run_logic(self, auto):
        cams = []
        for i in self.tree.get_children():
            v = self.tree.item(i)['values']
            cams.append({"name": str(v[0]), "qty": int(v[1]), "mbps": float(v[2]), "tb": float(v[3])/1024})
        if not cams: return
        best_cfg, best_total_cost, debug_info = None, float('inf'), []

        if auto:
            # (Simplified Auto)
            mode = self.mode_var.get(); parity = 1 if mode == "RAID 5" else 2 if mode == "RAID 6" else 0
            for n_u in range(1, 3):
                for combo in itertools.combinations_with_replacement(self.nvr_list, n_u):
                    hw_c = [{"m": n, "mode": mode, "p": parity} for n in combo]
                    res, err = self.calculate_units(cams, hw_c, True)
                    if res:
                        cost = sum(x['m'][5] + x['h']['cost'] for x in res)
                        if cost < best_total_cost: best_total_cost, best_cfg = cost, {"total": cost, "units": res}
        else:
            active_hw = []
            for nv, mv, cb in self.manual_slots:
                if nv.get() != "None":
                    hw = next(n for n in self.nvr_list if n[1] == nv.get())
                    active_hw.append({"m": hw, "mode": mv.get(), "p": (1 if mv.get() == "RAID 5" else 2 if mv.get() == "RAID 6" else 0)})
            if active_hw:
                # TRY OPTIMIZED -> THEN TRY BALANCED
                res, err = self.calculate_units(cams, active_hw, False)
                if not res: res, err = self.calculate_units(cams, active_hw, True)
                if res: best_cfg = {"total": sum(x['m'][5] + x['h']['cost'] for x in res), "units": res}
                else: debug_info = err

        txt = self.res_txt if auto else self.man_txt
        txt.delete("1.0", tk.END)
        if best_cfg: txt.insert("1.0", self.generate_detailed_report(best_cfg, "AUTO" if auto else "MANUAL"))
        else: txt.insert("1.0", f"FAILED: {debug_info}")

if __name__ == "__main__":
    root = tk.Tk(); root.geometry("1100x950"); app = CCTVApp(root); root.mainloop()
