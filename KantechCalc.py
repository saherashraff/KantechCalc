import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import math
import itertools
import json
import os

DATA_FILE = "system_data.json"

# --- CORE MATH ENGINE ---
def get_best_hdd(required_tb, slots, parity, price_dict):
    if required_tb <= 0.01: return 0, {"qty": 0, "cap": 0, "cost": 0, "total_tb": 0}
    best_h_cost, best_h_cfg = float('inf'), None
    for cap in sorted(price_dict.keys()):
        price = price_dict[cap]
        min_d = 1 if parity == 0 else 2
        data_req = max(math.ceil(required_tb / cap), min_d)
        total_drives = data_req + parity
        if total_drives <= slots:
            cost = total_drives * price
            if cost < best_h_cost:
                best_h_cost, best_h_cfg = cost, {"qty": total_drives, "cap": cap, "cost": cost, "total_tb": (data_req * cap)}
    return (best_h_cost, best_h_cfg) if best_h_cfg else (None, None)

class CCTVApp:
    def __init__(self, root):
        self.root = root
        self.root.title("CCTV MASTER V37.0 - 10 UNIT BRUTE FORCE")
        self.load_all_data()
        self.setup_ui()
        self.last_config = None

    def load_all_data(self):
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, "r") as f:
                    data = json.load(f)
                    self.hdd_prices = {int(k): float(v) for k, v in data.get("hdd", {}).items()}
                    self.nvr_list = data.get("nvr", [])
            except: pass
        # Fallback to defaults if load fails
        if not hasattr(self, 'hdd_prices') or not self.hdd_prices:
            self.hdd_prices = {1:87, 2:131, 4:239, 8:427, 12:614, 18:1291, 22:1226}
        if not hasattr(self, 'nvr_list') or not self.nvr_list:
            self.nvr_list = [
                ["1U RAID", "ADVER00N0NP16G", 32, 50, 4, 3750.0, "RAID"],
                ["2U Rack 200 Ch", "ADVER02RDK", 200, 1500, 12, 12812.5, "RAID"]
            ]

    def setup_ui(self):
        self.nb = ttk.Notebook(self.root)
        self.nb.pack(fill="both", expand=True)
        self.tabs = [ttk.Frame(self.nb) for _ in range(3)]
        self.nb.add(self.tabs[0], text="1. Setup Cameras")
        self.nb.add(self.tabs[1], text="2. Deep Search Auto")
        self.nb.add(self.tabs[2], text="3. Manual Override")

        # Tab 1: Cameras
        f_in = ttk.Frame(self.tabs[0], padding=10); f_in.pack(fill="x")
        self.ents = {}
        for i, label in enumerate(["Name", "Qty", "Mbps", "GB"]):
            ttk.Label(f_in, text=label).grid(row=0, column=i*2)
            e = ttk.Entry(f_in, width=10); e.grid(row=0, column=i*2+1); self.ents[label] = e
        ttk.Button(self.tabs[0], text="Add/Update Camera", command=self.add_cam).pack(pady=5)
        self.tree = ttk.Treeview(self.tabs[0], columns=("N","Q","M","G"), show="headings")
        for c, h in zip(self.tree["columns"], ["Name","Qty","Mbps","GB"]): self.tree.heading(c, text=h)
        self.tree.pack(fill="both", expand=True)

        # Tab 2: Auto
        f_a = ttk.Frame(self.tabs[1], padding=10); f_a.pack(fill="x")
        self.auto_mode = tk.StringVar(value="RAID 5")
        ttk.Combobox(f_a, textvariable=self.auto_mode, values=["RAID 5", "RAID 6", "JBOD"]).pack(side="left")
        ttk.Button(f_a, text="RUN 10-UNIT DEEP SEARCH", command=lambda: self.run_logic(True)).pack(side="left", padx=10)
        self.res_txt = tk.Text(self.tabs[1], font=("Consolas", 10)); self.res_txt.pack(fill="both", expand=True)

    def add_cam(self):
        v = [self.ents[k].get() for k in ["Name", "Qty", "Mbps", "GB"]]
        self.tree.insert("", "end", values=v)

    def calc_engine(self, cams, hw_c, split_ratio):
        """
        The "Split" Logic: 
        Takes a 'split_ratio' from 1% to 100%. 
        It attempts to pack NVRs at that specific density to find the cheapest HDD/Chassis balance.
        """
        u_list = []
        remaining_cams = [dict(c) for c in cams]
        
        for i, hw in enumerate(hw_c):
            u_brk, u_mb, u_tb, u_c = {}, 0, 0, 0
            
            for c in remaining_cams:
                if c['qty'] <= 0: continue
                
                # We try to take a specific portion based on the ratio sweep
                # This simulates 'trying every split' by shifting the density per NVR
                can_take_ch = hw['m'][2] - u_c
                can_take_mb = (hw['m'][3] - u_mb) / c['mbps']
                
                limit = min(can_take_ch, can_take_mb)
                # Apply the ratio to the total camera qty to see how much goes in this unit
                attempt_take = math.floor(c['total_orig'] * split_ratio) if i < len(hw_c)-1 else c['qty']
                
                actual_take = max(0, min(attempt_take, limit, c['qty']))
                
                if actual_take > 0:
                    u_brk[c['name']] = int(actual_take)
                    u_mb += actual_take * c['mbps']
                    u_tb += actual_take * c['tb']
                    u_c += actual_take
                    c['qty'] -= actual_take

            p = 0 if hw['m'][6]=="JBOD" else (1 if hw['mode']=="RAID 5" else 2)
            cost, hdd = get_best_hdd(u_tb, hw['m'][4], p, self.hdd_prices)
            if not hdd and u_tb > 0.01: return None # Hardware cannot hold this storage
            
            u_list.append({
                "m": hw['m'], "c_total": int(u_c), "c_list": u_brk,
                "mb": u_mb, "tb": u_tb, "h": hdd or {"qty":0,"cap":0,"cost":0}, "mode": hw['mode']
            })

        # Ensure ALL cameras were placed
        if sum(c['qty'] for c in remaining_cams) > 0: return None
        return u_list

    def run_logic(self, auto):
        cams = []
        for i in self.tree.get_children():
            v = self.tree.item(i)['values']
            cams.append({"name": v[0], "total_orig": int(v[1]), "qty": int(v[1]), "mbps": float(v[2]), "tb": float(v[3])/1024})
        
        if not cams: return
        best_cfg, best_cost = None, float('inf')
        
        if auto:
            mode = self.auto_mode.get()
            pool = [n for n in self.nvr_list if n[6] == ("JBOD" if mode=="JBOD" else "RAID")]
            
            # 1 to 10 NVRs
            for n_u in range(1, 11):
                # Search across all combinations of hardware
                for combo in itertools.combinations_with_replacement(pool, n_u):
                    hw_c = [{"m": n, "mode": mode} for n in combo]
                    
                    # 1% Granularity Sweep (tries 100 different camera distribution styles per combo)
                    for r in range(1, 101):
                        res = self.calc_engine(cams, hw_c, r/100.0)
                        if res:
                            cost = sum(x['m'][5] + x['h']['cost'] for x in res)
                            if cost < best_cost:
                                best_cost = cost
                                best_cfg = {"total": cost, "units": res}
                                # Feedback to UI so user knows it's working
                                self.res_txt.delete("1.0", tk.END)
                                self.res_txt.insert("1.0", f"Found cheaper: ${cost:,.2f}...\n")
                                self.root.update()

        if best_cfg:
            self.res_txt.delete("1.0", tk.END)
            self.res_txt.insert("1.0", self.generate_report(best_cfg))
        else:
            messagebox.showerror("Limit Error", "Could not fit cameras even in 10 units.")

    def generate_report(self, cfg):
        out = f"=== OPTIMIZED DESIGN REPORT ===\nTOTAL SYSTEM COST: ${cfg['total']:,.2f}\n" + "="*40 + "\n"
        for i, u in enumerate(cfg['units']):
            out += f"\nUNIT #{i+1}: {u['m'][0]} ({u['m'][1]})\n"
            out += f"  - HARDWARE: ${u['m'][5]:,.2f} | STORAGE: ${u['h']['cost']:,.2f}\n"
            out += f"  - CONFIG: {u['h']['qty']} x {u['h']['cap']}TB drives ({u['mode']})\n"
            out += f"  - ASSIGNED CAMERAS ({u['c_total']} Total):\n"
            for name, qty in u['c_list'].items():
                out += f"      > {name}: {qty} units\n"
            out += "-"*20 + f" Subtotal: ${(u['m'][5]+u['h']['cost']):,.2f}\n"
        return out

if __name__ == "__main__":
    root = tk.Tk(); root.geometry("1100x900"); app = CCTVApp(root); root.mainloop()
