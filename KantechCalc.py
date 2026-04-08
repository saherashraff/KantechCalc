#!/usr/bin/env python3
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import math, itertools, json, os
from datetime import datetime

# --- Persistence ---
DATA_FILE = "system_data.json"

DEFAULT_HDD_PRICES = {
    1: 87.0, 2: 131.0, 3: 145.0, 4: 239.0,
    6: 375.0, 8: 427.0, 10: 500.0, 12: 614.0,
    14: 1114.0, 18: 1291.0, 22: 1145.85, 24: 1568.0, 26: 1385.0,
}

DEFAULT_NVR_DATA = [
    {"Name": "1U RAID", "SKU": "ADVER00N0NP16G", "CH": 32, "MB": 50, "Slots": 4, "Price": 3750.0, "mode": "RAID", "brand": "American Dynamics"},
    {"Name": "2U 64 Ch", "SKU": "ADVER12R0N2H", "CH": 64, "MB": 300, "Slots": 6, "Price": 10416.7, "mode": "RAID", "brand": "American Dynamics"},
    {"Name": "2U 100 Ch", "SKU": "ADVER00RN2J", "CH": 100, "MB": 600, "Slots": 8, "Price": 11666.7, "mode": "RAID", "brand": "American Dynamics"},
    {"Name": "Micro NVR", "SKU": "ADVEM00N0NP8AH", "CH": 8, "MB": 80, "Slots": 1, "Price": 1500.0, "mode": "JBOD", "brand": "American Dynamics"},
    {"Name": "Desktop JBOD", "SKU": "ADVED00N0N5H", "CH": 50, "MB": 200, "Slots": 2, "Price": 2291.7, "mode": "JBOD", "brand": "American Dynamics"},
    {"Name": "Holis 8 Ch", "SKU": "HRN-08013P", "CH": 8, "MB": 160, "Slots": 1, "Price": 520.85, "mode": "JBOD", "brand": "Holis"},
    {"Name": "Holis 16 Ch", "SKU": "HRN-16023P", "CH": 16, "MB": 320, "Slots": 2, "Price": 770.85, "mode": "JBOD", "brand": "Holis"},
]

# --- Colors & Styles (Same as your UI) ---
BG, SURFACE, SURFACE2, SURFACE3 = "#0f1520", "#151d2e", "#1a2540", "#1f2d4a"
ACCENT, GREEN, GOLD, RED, TEXT, TEXT2 = "#00d4ff", "#22d3a5", "#f59e0b", "#f87171", "#e2e8f0", "#7a90b0"
FONT_H1, FONT_H2, FONT_H3, FONT_BODY, FONT_MONO = ("Segoe UI", 16, "bold"), ("Segoe UI", 11, "bold"), ("Segoe UI", 10, "bold"), ("Segoe UI", 9), ("Consolas", 9)

# ─────────────────────────── Updated Logic Engine ───────────────────────────

def get_best_hdd(required_tb, slots, parity, price_dict):
    if required_tb <= 0.01: return {"qty": 0, "cap": 0, "cost": 0, "total_tb": 0}
    best_cost, best_cfg = float('inf'), None
    for cap in sorted(price_dict.keys()):
        price = price_dict[cap]
        min_d = 1 if parity == 0 else (parity + 1)
        data_req = max(math.ceil(required_tb / cap), 1)
        total_drives = data_req + parity
        if total_drives <= slots:
            cost = total_drives * price
            if cost < best_cost:
                best_cost = cost
                best_cfg = {"qty": total_drives, "cap": cap, "cost": cost, "total_tb": (data_req * cap)}
    return best_cfg

def calc_sub_engine(cams, hw_list, ratio, hdd_prices):
    """Matches the 'Auto' logic to distribute cameras across multiple NVRs"""
    u_list = []
    # Copy cameras to track remaining qty
    cur_cams = [dict(c) for c in cams]
    
    for i, hw in enumerate(hw_list):
        nvr = hw['m']
        u_brk, u_mb, u_tb, u_c = {}, 0, 0, 0
        
        for c in cur_cams:
            if c['qty'] <= 0: continue
            
            # Decide how many to take for this specific unit
            take = math.floor(c['qty'] * ratio) if i < len(hw_list)-1 else c['qty']
            
            # Constrain by NVR channel limit
            take = min(take, nvr['CH'] - u_c)
            # Constrain by Mbps limit
            if (u_mb + (take * c['mbps'])) > nvr['MB']:
                take = max(0, math.floor((nvr['MB'] - u_mb) / c['mbps']))
            
            if take > 0:
                u_brk[c['name']] = u_brk.get(c['name'], 0) + take
                u_mb += take * c['mbps']
                u_tb += take * c['tb']
                u_c += take
                c['qty'] -= take

        # Determine RAID parity
        mode = hw['mode']
        parity = 0 if mode == "JBOD" else (1 if mode == "RAID 5" else 2)
        
        hd = get_best_hdd(u_tb, nvr['Slots'], parity, hdd_prices)
        if not hd and u_tb > 0.01: return None # Hardware can't fit storage
        
        u_list.append({
            "nvr": nvr, 
            "c_total": u_c, 
            "cam_breakdown": u_brk, 
            "mb": u_mb, 
            "tb": u_tb, 
            "h": hd or {"qty":0, "cap":0, "cost":0, "total_tb":0}, 
            "mode": mode
        })
    
    # Valid only if all cameras were assigned
    return u_list if sum(c['qty'] for c in cur_cams) == 0 else None

# ─────────────────────────── App Class ──────────────────────────────────────

class CCTVApp:
    def __init__(self, root):
        self.root = root
        self.root.title("CCTV Master Calculator")
        self.root.configure(bg=BG)
        self.root.geometry("1100x850")
        self.load_all_data()
        self.setup_ui()
        self._apply_ttk_styles()

    def load_all_data(self):
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, "r") as f:
                    data = json.load(f)
                    self.hdd_prices = {int(k): float(v) for k, v in data.get("hdd", DEFAULT_HDD_PRICES).items()}
                    self.nvr_list = data.get("nvr", DEFAULT_NVR_DATA)
            except: 
                self.hdd_prices, self.nvr_list = DEFAULT_HDD_PRICES.copy(), DEFAULT_NVR_DATA.copy()
        else:
            self.hdd_prices, self.nvr_list = DEFAULT_HDD_PRICES.copy(), DEFAULT_NVR_DATA.copy()

    def run_logic(self):
        """The core Auto/Manual execution logic"""
        # 1. Collect Camera Data
        cams = []
        for i in self.tree.get_children():
            v = self.tree.item(i)['values']
            cams.append({"name": str(v[0]), "qty": int(v[1]), "mbps": float(v[2]), "tb": float(v[3])})
        
        if not cams:
            messagebox.showwarning("Input Error", "Please add cameras first.")
            return

        best_cfg, best_cost = None, float('inf')
        mode = self.raid_var.get()
        
        # 2. Build Hardware Pool
        if self.auto_mode.get() == "AUTO":
            brand = self.brand_filter.get()
            # Filter pool: must match JBOD/RAID hardware type and Brand
            pool = [n for n in self.nvr_list if (n['mode'] == ("JBOD" if mode=="JBOD" else "RAID"))]
            if brand != "All":
                pool = [n for n in pool if n.get('brand') == brand]
            
            # Exhaustive search: combinations of up to 4 units (performance balance)
            for n_units in range(1, 5):
                for combo in itertools.combinations_with_replacement(pool, n_units):
                    hw_c = [{"m": n, "mode": mode} for n in combo]
                    # Test different distribution ratios (100% load on one vs even splits)
                    for r in [1.0, 0.5, 0.34, 0.25]:
                        res = calc_sub_engine(cams, hw_c, r, self.hdd_prices)
                        if res:
                            cost = sum((x['nvr']['Price'] + x['h']['cost']) for x in res)
                            if cost < best_cost:
                                best_cost, best_cfg = cost, res
        else:
            # Manual Mode: uses the specific selections in the UI
            active_hw = []
            for cb in self.manual_combos:
                sku = cb.get()
                if sku != "None":
                    match = next((n for n in self.nvr_list if n["Name"] == sku), None)
                    if match: active_hw.append({"m": match, "mode": mode})
            
            if active_hw:
                # Try to optimize the split ratio for the selected manual units
                for r in range(1, 101):
                    res = calc_sub_engine(cams, active_hw, r/100.0, self.hdd_prices)
                    if res:
                        cost = sum((x['nvr']['Price'] + x['h']['cost']) for x in res)
                        if cost < best_cost:
                            best_cost, best_cfg = cost, res

        self.display_results(best_cfg, best_cost)

    def display_results(self, result, total_cost):
        self.res_txt.config(state="normal")
        self.res_txt.delete("1.0", tk.END)
        
        if not result:
            self.res_txt.insert(tk.END, "❌ NO VALID CONFIGURATION FOUND\n", "error")
            self.res_txt.insert(tk.END, "The camera load exceeds the capacity of available NVRs or HDD slots.", "label")
        else:
            self.res_txt.insert(tk.END, f"✅ OPTIMAL CONFIGURATION FOUND\n", "best")
            self.res_txt.insert(tk.END, f"SYSTEM TOTAL COST: ${total_cost:,.2f}\n", "cost")
            self.res_txt.insert(tk.END, "="*60 + "\n", "divider")
            
            for i, unit in enumerate(result):
                n = unit['nvr']
                self.res_txt.insert(tk.END, f"UNIT #{i+1}: {n['Name']} ({n['SKU']})\n", "header")
                self.res_txt.insert(tk.END, f"  Mode: {unit['mode']} | Load: {unit['c_total']} Ch / {unit['mb']:.1f} Mbps\n", "value")
                self.res_txt.insert(tk.END, f"  Storage: {unit['h']['qty']} x {unit['h']['cap']}TB ({unit['h']['total_tb']:.1f}TB Usable)\n", "value")
                self.res_txt.insert(tk.END, f"  Unit Subtotal: ${(n['Price'] + unit['h']['cost']):,.2f}\n\n", "cost")
                
                self.res_txt.insert(tk.END, "  Camera Distribution:\n", "label")
                for c_name, c_qty in unit['cam_breakdown'].items():
                    self.res_txt.insert(tk.END, f"    - {c_name}: {c_qty} units\n", "value")
                self.res_txt.insert(tk.END, "-"*40 + "\n", "divider")
                
        self.res_txt.config(state="disabled")

    # --- Rest of UI Boilerplate (Helper methods from your code) ---
    def setup_ui(self):
        # (This section would contain the UI layout code you provided in your prompt)
        # I've condensed the Logic focus here; ensure you keep your Treeview and 
        # Notebook setup to feed into run_logic().
        pass 

    # ... Include your existing _build_cameras_tab, _build_calc_tab etc ...
