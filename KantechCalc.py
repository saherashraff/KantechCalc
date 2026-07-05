import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
import pandas as pd
import numpy as np
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional
import json
import os


@dataclass
class DCDevice:
    """Represents devices on a single DC line"""
    dc_number: int
    smart_card: int = 0
    smart_card_reader: int = 0  
    fingerprint: int = 0  # Biometric
    door_sensor: int = 0
    magnetic_lock: int = 0
    electric_lock: int = 0
    rex_button: int = 0
    push_button: int = 0
    break_glass: int = 0
    buzzer: int = 0
    double_door_lock: int = 0  
    ddl_sensors: int = 0
    unmonitored_single_magnetic_lock: int = 0  
    unmonitored_double_magnetic_lock: int = 0  
    
    def calculate_totals(self):
        """Calculate readers, inputs, outputs for this DC line"""
        readers = self.smart_card + self.fingerprint + self.smart_card_reader
        
        inputs = (self.door_sensor + self.rex_button + self.push_button + 
                 self.break_glass + self.magnetic_lock + 
                 self.ddl_sensors + self.double_door_lock)
        
        outputs = (self.magnetic_lock + self.electric_lock + self.double_door_lock +
                  self.unmonitored_single_magnetic_lock + 
                  self.unmonitored_double_magnetic_lock +
                  self.buzzer)
        
        return {
            'readers': readers,
            'inputs': inputs,
            'outputs': outputs,
            'smart_cards': self.smart_card,
            'smart_card_readers': self.smart_card_reader,
            'fingerprints': self.fingerprint
        }
    
    def add_configuration(self, other_config):
        """Add another configuration to this DC line"""
        self.smart_card += other_config.smart_card
        self.smart_card_reader += other_config.smart_card_reader
        self.fingerprint += other_config.fingerprint
        self.door_sensor += other_config.door_sensor
        self.magnetic_lock += other_config.magnetic_lock
        self.electric_lock += other_config.electric_lock
        self.rex_button += other_config.rex_button
        self.push_button += other_config.push_button
        self.break_glass += other_config.break_glass
        self.buzzer += other_config.buzzer
        self.double_door_lock += other_config.double_door_lock
        self.ddl_sensors += other_config.ddl_sensors
        self.unmonitored_single_magnetic_lock += other_config.unmonitored_single_magnetic_lock
        self.unmonitored_double_magnetic_lock += other_config.unmonitored_double_magnetic_lock


class AccessDoorType:
    """Represents an Access Door Type configuration"""
    def __init__(self, type_id: int, name: str):
        self.type_id = type_id
        self.name = name
        self.config = DCDevice(dc_number=type_id)
    
    def update_config(self, **kwargs):
        """Update the configuration of this door type"""
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
    
    def get_totals(self):
        """Get totals for this door type"""
        return self.config.calculate_totals()
    
    def __str__(self):
        totals = self.get_totals()
        return f"Door Type {self.type_id} ({self.name}): {totals['readers']} readers, {totals['inputs']} inputs, {totals['outputs']} outputs"


class GSTARController:
    def __init__(self, name, readers, inputs, outputs, price, number_of_acm):
        self.name = name
        self.readers = readers
        self.inputs = inputs
        self.outputs = outputs
        self.price = price
        self.number_of_acm = number_of_acm
    
    def can_handle_readers(self, required_readers):
        return self.readers >= required_readers


class SWHControllerCalculator:
    def __init__(self):
        self.gstar_controllers = [
            GSTARController("GSTAR004 (4 readers)", 4, 8, 4, 1395, 0),
            GSTARController("GSTAR004 (8 readers)", 8, 16, 12, 2123, 0),
            GSTARController("GSTAR008", 8, 24, 8, 3125, 1),
            GSTARController("GSTAR016", 16, 48, 16, 4166, 2),
            GSTARController("GSTAR016 (24 readers)", 24, 72, 24, 5166, 3),
            GSTARController("GSTAR016 (32 readers)", 32, 96, 32, 6166, 4)
        ]
        
        self.swh_licenses = [
            {"name": "CC9000-SL", "max_readers": 16, "cost": 0},
            {"name": "CC9000-SM", "max_readers": 32, "cost": 0},
            {"name": "CC9000-SN", "max_readers": 64, "cost": 0},
            {"name": "CC9000-SP", "max_readers": 128, "cost": 0},
            {"name": "CC9000-SQ", "max_readers": 256, "cost": 0},
            {"name": "CC9000-SR", "max_readers": 512, "cost": 0},
            {"name": "CC9000-SRP", "max_readers": 1000, "cost": 0},
            {"name": "CC9000-SS", "max_readers": 2500, "cost": 0},
            {"name": "CC9000-SSP", "max_readers": 3500, "cost": 0},
            {"name": "CC9000-ST", "max_readers": 5000, "cost": 0}
        ]
        
    def select_controller_for_readers(self, required_readers):
        suitable_controllers = [c for c in self.gstar_controllers if c.can_handle_readers(required_readers)]
        if not suitable_controllers:
            return None
        suitable_controllers.sort(key=lambda x: x.price)
        return suitable_controllers[0]
    
    def calculate_expansion_for_swh(self, dc_inputs: int, dc_outputs: int, controller_inputs: int, controller_outputs: int) -> Dict:
        input_shortage = max(0, dc_inputs - controller_inputs)
        output_shortage = max(0, dc_outputs - controller_outputs)
        
        expansion_modules = []
        expansion_cost = 0
        
        if input_shortage > 0:
            as0073_needed = int(np.ceil(input_shortage / 8))
            expansion_modules.append(f"AS0073-000 (x{as0073_needed})")
            expansion_cost += 333 * as0073_needed
        
        if output_shortage > 0:
            as0074_needed = int(np.ceil(output_shortage / 8))
            expansion_modules.append(f"AS0074-000 (x{as0074_needed})")
            expansion_cost += 395 * as0074_needed
        
        return {
            'modules': expansion_modules,
            'cost': expansion_cost,
            'input_shortage': input_shortage,
            'output_shortage': output_shortage
        }


class KantechDCCalculatorGUI:
    def __init__(self):
        self.dc_lines: List[DCDevice] = []
        self.access_door_types: List[AccessDoorType] = []
        self.swh_calculator = SWHControllerCalculator()
        
        self.controllers = [
            {'name': 'kt-1', 'readers': 1, 'smart_card_readers': 1, 'cost': 450, 'inputs': 4, 'outputs': 2},
            {'name': 'kt-2', 'readers': 2, 'smart_card_readers': 2, 'cost': 750, 'inputs': 8, 'outputs': 2},
            {'name': 'kt-4', 'readers': 4, 'smart_card_readers': 4, 'cost': 2395, 'inputs': 16, 'outputs': 4}
        ]
        
        self.expansion_modules = [
            {'name': 'inout16 (16/0)', 'inputs': 16, 'outputs': 0, 'cost': 447},
            {'name': 'inout16 (12/4)', 'inputs': 12, 'outputs': 4, 'cost': 447},
            {'name': 'inout16 (8/8)', 'inputs': 8, 'outputs': 8, 'cost': 447},
            {'name': 'inout16 (4/12)', 'inputs': 4, 'outputs': 12, 'cost': 447},
            {'name': 'inout16 (0/16)', 'inputs': 0, 'outputs': 16, 'cost': 447},
            {'name': 'in16', 'inputs': 16, 'outputs': 0, 'cost': 470},
            {'name': 'r8', 'inputs': 0, 'outputs': 8, 'cost': 470}
        ]
        
        self.license_info = {
            'special': {'name': 'Kantech Special License', 'max_controllers': 32, 'cost': 0},
            'corporate': {'name': 'Kantech Corporate License', 'min_controllers': 33, 'cost': 0},
            'global': {'name': 'Global License', 'cost': 0},
            'gateway': {'name': 'Gateway License', 'cost': 500},
            'redundancy': {'name': 'Redundancy License', 'cost': 750}
        }
        
        self.kantech_all_results = None
        self.kantech_grand_total = 0
        self.gstar_results = None
        
        self.root = tk.Tk()
        self.root.title("Access Control System Calculator")
        self.root.geometry("1200x800")
        
        self.selected_dc_line_var = tk.StringVar()
        self.selected_door_type_var = tk.StringVar()
        self.redundancy_var = tk.BooleanVar(value=False)
        
        self.setup_styles()
        self.create_ui()
        
    def setup_styles(self):
        style = ttk.Style()
        style.configure('Title.TLabel', font=('Arial', 14, 'bold'))
        
    def create_ui(self):
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.create_main_tab()
        self.create_dc_lines_tab()
        self.create_door_types_tab()
        self.create_calculation_tab()
        self.create_license_tab()
        self.create_export_tab()
        
        self.status_bar = tk.Label(self.root, text="Ready", bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
    
    def create_main_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Main")
        
        ttk.Label(tab, text="ACCESS CONTROL SYSTEM CALCULATOR", style='Title.TLabel').pack(pady=20)
        
        info_frame = ttk.LabelFrame(tab, text="System Information", padding=10)
        info_frame.pack(fill=tk.X, padx=20, pady=10)
        self.system_info_text = tk.Text(info_frame, height=8, width=80, state=tk.DISABLED)
        self.system_info_text.pack(fill=tk.BOTH, expand=True)
        
        actions_frame = ttk.LabelFrame(tab, text="Quick Actions", padding=10)
        actions_frame.pack(fill=tk.X, padx=20, pady=10)
        ttk.Button(actions_frame, text="Add DC Line", command=lambda: self.notebook.select(1)).pack(side=tk.LEFT, padx=5)
        ttk.Button(actions_frame, text="Manage Door Types", command=lambda: self.notebook.select(2)).pack(side=tk.LEFT, padx=5)
        ttk.Button(actions_frame, text="Calculate Systems", command=lambda: self.notebook.select(3)).pack(side=tk.LEFT, padx=5)
        
        overview_frame = ttk.LabelFrame(tab, text="System Overview", padding=10)
        overview_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        self.overview_text = scrolledtext.ScrolledText(overview_frame, height=15, state=tk.DISABLED)
        self.overview_text.pack(fill=tk.BOTH, expand=True)
    
    def create_dc_lines_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="DC Lines")
        
        top_frame = ttk.Frame(tab)
        top_frame.pack(fill=tk.X, padx=10, pady=10)
        ttk.Label(top_frame, text="DC Line Management", style='Title.TLabel').pack(side=tk.LEFT)
        
        button_frame = ttk.Frame(top_frame)
        button_frame.pack(side=tk.RIGHT)
        ttk.Button(button_frame, text="Add DC Line", command=self.show_add_dc_line_dialog).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Edit Selected", command=self.edit_selected_dc_line).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Delete Selected", command=self.delete_selected_dc_line).pack(side=tk.LEFT, padx=5)
        
        list_frame = ttk.LabelFrame(tab, text="DC Lines List", padding=10)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        columns = ('DC', 'Card Reader', 'Smart Card Reader', 'Biometric', 'Door Sensor', 'Mag Lock', 'Elec Lock', 
                  'REX', 'Push Button', 'Break Glass', 'Buzzer', 'DDL', 'DDL Sensors',
                  'Unmon Single', 'Unmon Double', 'Readers', 'Inputs', 'Outputs')
        
        self.dc_tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=15)
        for col in columns:
            self.dc_tree.heading(col, text=col)
            self.dc_tree.column(col, width=70, minwidth=40)
            
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.dc_tree.yview)
        self.dc_tree.configure(yscrollcommand=scrollbar.set)
        self.dc_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
    def create_door_types_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Door Types")
        
        top_frame = ttk.Frame(tab)
        
