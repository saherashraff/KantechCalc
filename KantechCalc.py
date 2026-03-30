import tkinter as tk
from tkinter import ttk, messagebox
import math

# --- DATA ---
RAID_DATA = [
    ["1U RAID", "ADVER00N0NP16G", 32, 50, 4, 3750.00],
    ["2U 64 Ch", "ADVER12R0N2H", 64, 300, 6, 10416.70],
    ["2U 100 Ch", "ADVER00RN2J", 100, 600, 8, 11666.70],
    ["2U 128 Ch", "ADVER72R5N2H", 128, 600, 12, 25000.00],
    ["2U Rack 175 Ch", "ADVER02RDK", 175, 1000, 12, 13854.20],
    ["2U Rack 200 Ch", "ADVER02RDK", 200, 1500, 12, 12812.50],
]
JBOD_ONLY_DATA = [
    ["Micro NVR", "ADVEM00N0NP8AH", 8, 80, 1, 1500.00],
    ["Desktop JBOD", "ADVED00N0N5H", 50, 200, 2, 2291.70],
    ["2U 75 Ch", "ADVER00N0N2J", 75, 400, 4, 5312.50],
]
HOLIS_DATA = [
    ["Holis 8 Ch", "HRN-08013P", 8, 160, 1, 520.85],
    ["Holis 16 Ch", "HRN-16023P", 16, 320, 2, 770.85],
]
ALL_MODELS = RAID_DATA + JBOD_ONLY_DATA + HOLIS_DATA
DEFAULT_HDD_PRICES = {1: 93.75, 2: 122.95, 4: 218.75, 6: 281.25, 8: 395.85, 10: 416.7, 12: 687.50, 14: 1041.7, 18: 1052.1, 22: 1145.85, 24: 1447.95, 26: 1700.00}

def get_best_hdd(required_tb, slots, parity, price_dict):
    if required_tb <= 1e-6: return 0, {"qty": 0, "cap": 0, "cost": 0, "total_tb": 0}
    best_h_cost, best_h_cfg = float('inf'), None
    for cap, price in sorted(price_dict.items()):
        min_d = 2 if parity > 0 else 1
        data_drives = max(math.ceil(required_tb / cap), min_d)
        total_drives = data_drives + parity
        if total_drives <= slots:
            if (total_drives * price) < best_h_cost:
                best_h_cost = total_drives * price
                best_h_cfg = {"qty": total_drives, "cap": cap, "cost": best_h_cost, "total_tb": (data_drives * cap)}
    return best_h_cost, best_h_cfg

class CCTVApp:
    def __init__(self, root):
        self.root = root
        self.root.title("CCTV MASTER V22.5 - RATIO ENGINE FIX")
        self.hdd_prices = DEFAULT_HDD_PRICES.copy()
        self.setup_ui()

    def setup_ui(self):
        self.nb = ttk.Notebook(self.root)
        self.nb.pack(fill="both", expand=True, padx=5, pady=5)
        self.t1, self.t2, self.t4, self.t3 = ttk.Frame(self.nb), ttk.Frame(self.nb), ttk.Frame(self.nb), ttk.Frame(self.nb)
        self.nb.add(self.t1, text=" 1. Cameras "); self.nb.add(self.t2, text=" 2. Auto "); self.nb.add(self.t4, text=" 3. Manual "); self.nb.add(self.t3, text=" 4. HDD ")

        # TAB 1
        f_in = ttk.Frame(self.t1, padding=10); f_in.pack(fill="x")
        self.ents = {}
        for i, label in enumerate(["Name", "Qty", "Mbps", "GB"]):
            ttk.Label(f_in, text=label).grid(row=0, column=i*2)
            e = ttk.Entry(f_in, width=10); e.grid(row=0, column=i*2+1, padx=5); self.ents[label] = e
        btn_f = ttk.Frame(self.t1); btn_f.pack(fill="x", padx=10)
        ttk.Button(btn_f, text="Add", command=self.save_camera).pack(side="left")
        ttk.Button(btn_f, text="Delete", command=self.delete_camera).pack(side="left")
        self.tree = ttk.Treeview(self.t1, columns=("N","Q","M","G"), show="headings", height=15)
        for c, h in zip(self.tree["columns"], ["Name","Qty","Mbps","GB"]): self.tree.heading(c, text=h)
        self.tree.pack(fill="both", expand=True, padx=10, pady=5)

        # TAB 2 (AUTO)
        f_b = ttk.Frame(self.t2, padding=10); f_b.pack(fill="x")
        self.mode_var = tk.StringVar(value="RAID 5")
        ttk.Combobox(f_b, textvariable=self.mode_var, values=["RAID 5", "RAID 6", "JBOD"]).pack(side="left")
        ttk.Button(f_b, text="RUN AUTO", command=lambda: self.run_logic(True)).pack(side="left", padx=5)
        self.res_txt = tk.Text(self.t2, font=("Consolas", 9)); self.res_txt.pack(fill="both", expand=True)

        # TAB 3 (MANUAL FIX)
        f_m = ttk.Frame(self.t4, padding=10); f_m.pack(fill="x")
        self.manual_slots = []
        for i, char in enumerate(["A", "B", "C", "D"]):
            ttk.Label(f_m, text=f"NVR {char}:").grid(row=i, column=0)
            n_v, m_v = tk.StringVar(value="None"), tk.StringVar(value="RAID 5")
            cb = ttk.Combobox(f_m, textvariable=n_v, values=["None"]+[m[1] for m in ALL_MODELS], width=30, state="readonly")
            cb.grid(row=i, column=1, pady=2); ttk.Combobox(f_m, textvariable=m_v, values=["RAID 5", "RAID 6", "JBOD"], width=10).grid(row=i, column=2)
            self.manual_slots.append({"nvr": n_v, "mode": m_v})
        ttk.Button(f_m, text="CALCULATE RATIO SPLIT", command=lambda: self.run_logic(False)).grid(row=5, column=1, pady=10)
        self.man_txt = tk.Text(self.t4, font=("Consolas", 9)); self.man_txt.pack(fill="both", expand=True)

    def save_camera(self):
        v = [self.ents[k].get() for k in ["Name", "Qty", "Mbps", "GB"]]
        if all(v): self.tree.insert("", "end", values=v)
    def delete_camera(self):
        for i in self.tree.selection(): self.tree.delete(i)

    def run_logic(self, auto):
        cams = []
        for i in self.tree.get_children():
            v = self.tree.item(i)['values']
            cams.append({"name": v[0], "qty": int(v[1]), "mbps": float(v[2]), "tb": float(v[3])/1024})
        if not cams: return messagebox.showwarning("Error", "Add cameras first")

        t_c, t_m, t_t = sum(c['qty'] for c in cams), sum(c['qty']*c['mbps'] for c in cams), sum(c['qty']*c['tb'] for c in cams)
        best_cost, best_cfg = float('inf'), None

        if auto:
            # Simple Auto logic for brevity
            hw_pool = [m for m in ALL_MODELS]
            for m in hw_pool:
                if t_c <= m[2] and t_m <= m[3]:
                    h_c, h_d = get_best_hdd(t_t, m[4], 1, self.hdd_prices)
                    if h_d and (m[5] + h_c) < best_cost:
                        best_cost = m[5] + h_c
                        best_cfg = {"total": best_cost, "units": [{"m": m, "c": t_c, "mb": t_m, "tb": t_t, "h": h_d, "mode": "AUTO"}]}
        else:
            # MANUAL RATIO ENGINE
            active = []
            for s in self.manual_slots:
                if s['nvr'].get() != "None":
                    hw = [m for m in ALL_MODELS if m[1] == s['nvr'].get()][0]
                    p = 1 if s['mode'].get()=="RAID 5" else 2 if s['mode'].get()=="RAID 6" else 0
                    active.append({"hw": hw, "mode": s['mode'].get(), "parity": p})
            
            if not active: return messagebox.showerror("Error", "Select at least NVR A")

            # Check every split ratio (1% to 100% on unit 1)
            for r in range(1, 101):
                ratio = r / 100.0
                c1, m1, t1 = round(t_c * ratio), t_m * ratio, t_t * ratio
                if c1 == 0 or c1 > active[0]['hw'][2] or m1 > active[0]['hw'][3]: continue
                
                h1_c, h1_d = get_best_hdd(t1, active[0]['hw'][4], active[0]['parity'], self.hdd_prices)
                if not h1_d: continue

                # Split remainder among others
                rem_c, rem_m, rem_t = t_c - c1, t_m * (1-ratio), t_t * (1-ratio)
                if rem_c == 0:
                    current_total = active[0]['hw'][5] + h1_c
                    if current_total < best_cost:
                        best_cost = current_total
                        best_cfg = {"total": best_cost, "units": [{"m": active[0]['hw'], "c": c1, "mb": m1, "tb": t1, "h": h1_d, "mode": active[0]['mode']}]}
                elif len(active) > 1:
                    # Logic for remaining units
                    other_units = active[1:]
                    share_c = rem_c // len(other_units)
                    valid_others = True
                    other_configs = []
                    other_h_cost = 0
                    for u in other_units:
                        # Simplified even split for others based on ratio
                        o_ratio = (1-ratio)/len(other_units)
                        mu, tu = t_m * o_ratio, t_t * o_ratio
                        if share_c > u['hw'][2] or mu > u['hw'][3]: valid_others = False; break
                        hc, hd = get_best_hdd(tu, u['hw'][4], u['parity'], self.hdd_prices)
                        if not hd: valid_others = False; break
                        other_h_cost += hc
                        other_configs.append({"m": u['hw'], "c": share_c, "mb": mu, "tb": tu, "h": hd, "mode": u['mode']})
                    
                    if valid_others:
                        total = active[0]['hw'][5] + h1_c + sum(x['m'][5] for x in other_configs) + other_h_cost
                        if total < best_cost:
                            best_cost = total
                            best_cfg = {"total": total, "units": [{"m": active[0]['hw'], "c": c1, "mb": m1, "tb": t1, "h": h1_d, "mode": active[0]['mode']}] + other_configs}

        txt = self.res_txt if auto else self.man_txt
        txt.delete("1.0", tk.END)
        if best_cfg:
            res = f"TOTAL COST: ${best_cfg['total']:,.2f}\n" + "="*40 + "\n"
            for i, u in enumerate(best_cfg['units']):
                res += f"NVR {i+1}: {u['m'][0]}\n - Ch: {u['c']} | BW: {u['mb']:.1f}Mbps\n - HDD: {u['h']['qty']}x{u['h']['cap']}TB\n\n"
            txt.insert("1.0", res)
        else:
            txt.insert("1.0", "NO VALID CONFIG FOUND")

if __name__ == "__main__":
    root = tk.Tk()
    root.geometry("800x700")
    app = CCTVApp(root)
    root.mainloop()
