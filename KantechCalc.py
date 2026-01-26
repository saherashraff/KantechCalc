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
    smart_card_reader: int = 0  # NEW: smart card readers (different from regular smart cards)
    fingerprint: int = 0
    door_sensor: int = 0
    magnetic_lock: int = 0
    electric_lock: int = 0
    rex_button: int = 0
    push_button: int = 0
    break_glass: int = 0
    buzzer: int = 0
    double_door_lock: int = 0  # Counts as BOTH 1 input AND 1 output
    ddl_sensors: int = 0
    unmonitored_single_magnetic_lock: int = 0  # New: counts as output
    unmonitored_double_magnetic_lock: int = 0  # New: counts as output
    
    def calculate_totals(self):
        """Calculate readers, inputs, outputs for this DC line"""
        # Readers = Card Reader + Bio-metric Reader + Smart Card Reader
        readers = self.smart_card + self.fingerprint + self.smart_card_reader
        
        # Inputs = Door Sensor + REX Button + Push Button + Break Glass + Buzzer + Magnetic Lock + DDL Sensors + Double Door Lock
        # NOTE: Double Door Lock counts as 1 input
        inputs = (self.door_sensor + self.rex_button + self.push_button + 
                 self.break_glass + self.buzzer + self.magnetic_lock + 
                 self.ddl_sensors + self.double_door_lock)
        
        # Outputs = Magnetic Lock + Electric Lock + DDL Sensors + Double Door Lock + 
        #           Unmonitored Single Magnetic Lock + Unmonitored Double Magnetic Lock
        # NOTE: Double Door Lock counts as 1 output
        outputs = (self.magnetic_lock + self.electric_lock + 
                  self.ddl_sensors + self.double_door_lock +
                  self.unmonitored_single_magnetic_lock + 
                  self.unmonitored_double_magnetic_lock)
        
        return {
            'readers': readers,
            'inputs': inputs,
            'outputs': outputs,
            'smart_cards': self.smart_card,
            'smart_card_readers': self.smart_card_reader,  # NEW
            'fingerprints': self.fingerprint
        }
    
    def add_configuration(self, other_config):
        """Add another configuration to this DC line"""
        self.smart_card += other_config.smart_card
        self.smart_card_reader += other_config.smart_card_reader  # NEW
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
    """GSTAR controller information from SWH Access.xlsx"""
    def __init__(self, name, readers, inputs, outputs, price, number_of_acm):
        self.name = name
        self.readers = readers
        self.inputs = inputs
        self.outputs = outputs
        self.price = price
        self.number_of_acm = number_of_acm
    
    def can_handle_readers(self, required_readers):
        """Check if this controller can handle the reader requirements"""
        return self.readers >= required_readers


class SWHControllerCalculator:
    """Calculator for SWH GSTAR controllers (one controller per DC line)"""
    def __init__(self):
        # GSTAR controllers from the Excel sheet
        self.gstar_controllers = [
            GSTARController("GSTAR004 (4 readers)", 4, 8, 4, 1395, 0),
            GSTARController("GSTAR004 (8 readers)", 8, 16, 12, 2123, 0),
            GSTARController("GSTAR008", 8, 24, 8, 3125, 1),
            GSTARController("GSTAR016", 16, 48, 16, 4166, 2),
            GSTARController("GSTAR016 (24 readers)", 24, 72, 24, 5166, 3),
            GSTARController("GSTAR016 (32 readers)", 32, 96, 32, 6166, 4)
        ]
        
        # SWH License tiers
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
        
        # SWH Expansion modules from the table
        self.swh_expansion_modules = [
            {'name': 'AS0073-000', 'inputs': 8, 'outputs': 0, 'cost': 333},
            {'name': 'AS0074-000', 'inputs': 0, 'outputs': 8, 'cost': 395}
        ]
    
    def select_controller_for_readers(self, required_readers):
        """Select the cheapest GSTAR controller that meets or exceeds reader requirements"""
        suitable_controllers = []
        for controller in self.gstar_controllers:
            if controller.can_handle_readers(required_readers):
                suitable_controllers.append(controller)
        
        if not suitable_controllers:
            return None
        
        # Sort by price (cheapest first)
        suitable_controllers.sort(key=lambda x: x.price)
        
        # Return the cheapest suitable controller
        return suitable_controllers[0]
    
    def calculate_expansion_for_swh(self, dc_inputs: int, dc_outputs: int, 
                                  controller_inputs: int, controller_outputs: int) -> Dict:
        """Calculate SWH expansion modules needed for a DC line"""
        # Calculate shortages
        input_shortage = max(0, dc_inputs - controller_inputs)
        output_shortage = max(0, dc_outputs - controller_outputs)
        
        result = ""
        result += f"\nI/O Analysis:\n"
        result += f"  Required: {dc_inputs} inputs, {dc_outputs} outputs\n"
        result += f"  Controller provides: {controller_inputs} inputs, {controller_outputs} outputs\n"
        result += f"  Shortage: {input_shortage} inputs, {output_shortage} outputs\n"
        
        if input_shortage == 0 and output_shortage == 0:
            result += "  ✅ No expansion modules needed\n"
            return {'modules': [], 'cost': 0, 'input_modules': 0, 'output_modules': 0, 'result': result}
        
        # Calculate expansion modules needed
        expansion_modules = []
        expansion_cost = 0
        
        input_modules = 0
        output_modules = 0
        
        # Add input modules if needed
        if input_shortage > 0:
            # Use AS0073-000 modules (8 inputs each)
            as0073_needed = int(np.ceil(input_shortage / 8))
            expansion_modules.append(f"AS0073-000 (x{as0073_needed})")
            expansion_cost += 333 * as0073_needed
            input_modules = as0073_needed
        
        # Add output modules if needed
        if output_shortage > 0:
            # Use AS0074-000 modules (8 outputs each)
            as0074_needed = int(np.ceil(output_shortage / 8))
            expansion_modules.append(f"AS0074-000 (x{as0074_needed})")
            expansion_cost += 395 * as0074_needed
            output_modules = as0074_needed
        
        result += f"  Expansion solution: {expansion_modules}\n"
        result += f"  Expansion cost: ${expansion_cost}\n"
        
        return {
            'modules': expansion_modules,
            'cost': expansion_cost,
            'input_modules': input_modules,
            'output_modules': output_modules,
            'result': result
        }


class KantechDCCalculatorGUI:
    def __init__(self):
        self.dc_lines: List[DCDevice] = []
        self.access_door_types: List[AccessDoorType] = []
        self.swh_calculator = SWHControllerCalculator()
        
        # Controller models with SMART CARD READER capacity
        self.controllers = [
            {'name': 'kt-1', 'readers': 1, 'smart_card_readers': 1, 'cost': 450, 'inputs': 4, 'outputs': 2},
            {'name': 'kt-2', 'readers': 2, 'smart_card_readers': 2, 'cost': 750, 'inputs': 8, 'outputs': 2},
            {'name': 'kt-400', 'readers': 4, 'smart_card_readers': 4, 'cost': 1400, 'inputs': 16, 'outputs': 4}
        ]
        
        # All available expansion modules
        self.expansion_modules = [
            {'name': 'inout16 (16/0)', 'inputs': 16, 'outputs': 0, 'cost': 447},
            {'name': 'inout16 (12/4)', 'inputs': 12, 'outputs': 4, 'cost': 447},
            {'name': 'inout16 (8/8)', 'inputs': 8, 'outputs': 8, 'cost': 447},
            {'name': 'inout16 (4/12)', 'inputs': 4, 'outputs': 12, 'cost': 447},
            {'name': 'inout16 (0/16)', 'inputs': 0, 'outputs': 16, 'cost': 447},
            {'name': 'in16', 'inputs': 16, 'outputs': 0, 'cost': 470},
            {'name': 'r8', 'inputs': 0, 'outputs': 8, 'cost': 470}
        ]
        
        # License information
        self.license_info = {
            'special': {
                'name': 'Kantech Special License',
                'max_controllers': 32,
                'description': 'For systems with 32 or fewer controllers (non-redundant)',
                'cost': 0
            },
            'corporate': {
                'name': 'Kantech Corporate License',
                'min_controllers': 33,
                'description': 'For systems with more than 32 controllers (non-redundant)',
                'cost': 0
            },
            'global': {
                'name': 'Global License',
                'description': 'Required for ANY redundancy configuration (replaces Special/Corporate)',
                'cost': 0
            },
            'gateway': {
                'name': 'Gateway License',
                'description': 'Required for gateway/server communication in redundant systems',
                'cost': 500
            },
            'redundancy': {
                'name': 'Redundancy License',
                'description': 'Additional license for failover/redundancy capability',
                'cost': 750
            }
        }
        
        # Create main window FIRST
        self.root = tk.Tk()
        self.root.title("Access Control System Calculator")
        self.root.geometry("1200x800")
        
        # Now create tkinter variables AFTER root window is created
        self.selected_dc_line_var = tk.StringVar()
        self.selected_door_type_var = tk.StringVar()
        self.redundancy_var = tk.BooleanVar(value=False)
        
        # Initialize data storage for results
        self.kantech_all_results = None
        self.kantech_grand_total = 0
        self.gstar_results = None
        self.swh_license_result = None
        self.kantech_single_result = []
        self.swh_single_result = []
        
        # Configure styles
        self.setup_styles()
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create tabs
        self.create_main_tab()
        self.create_dc_lines_tab()
        self.create_door_types_tab()
        self.create_calculation_tab()
        self.create_license_tab()
        self.create_export_tab()
        
        # Status bar
        self.status_bar = tk.Label(self.root, text="Ready", bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
    def setup_styles(self):
        """Configure ttk styles"""
        style = ttk.Style()
        style.configure('Title.TLabel', font=('Arial', 14, 'bold'))
        style.configure('Heading.TLabel', font=('Arial', 12, 'bold'))
        style.configure('Subheading.TLabel', font=('Arial', 10, 'bold'))
        
    # [Previous methods remain the same until we get to the modified ones...]
    
    def update_dc_lines_list(self):
        """Update DC lines treeview"""
        # Clear existing items
        for item in self.dc_tree.get_children():
            self.dc_tree.delete(item)
        
        # Update columns to include smart_card_reader
        columns = ('DC', 'Card Reader', 'Smart Card Reader', 'Bio-metric', 'Door Sensor', 'Mag Lock', 'Elec Lock', 
                  'REX', 'Push Button', 'Break Glass', 'Buzzer', 'DDL', 'DDL Sensors',
                  'Unmon Single', 'Unmon Double', 'Readers', 'Inputs', 'Outputs')
        
        # Reconfigure tree columns
        self.dc_tree['columns'] = columns
        
        # Clear existing headings and columns
        for col in self.dc_tree['columns']:
            self.dc_tree.heading(col, text='')
            self.dc_tree.column(col, width=0)
        
        # Configure new columns
        for col in columns:
            self.dc_tree.heading(col, text=col)
            self.dc_tree.column(col, width=80, minwidth=50)
        
        # Add DC lines
        for dc in self.dc_lines:
            totals = dc.calculate_totals()
            values = (
                dc.dc_number,
                dc.smart_card,
                dc.smart_card_reader,  # NEW
                dc.fingerprint,
                dc.door_sensor,
                dc.magnetic_lock,
                dc.electric_lock,
                dc.rex_button,
                dc.push_button,
                dc.break_glass,
                dc.buzzer,
                dc.double_door_lock,
                dc.ddl_sensors,
                dc.unmonitored_single_magnetic_lock,
                dc.unmonitored_double_magnetic_lock,
                totals['readers'],
                totals['inputs'],
                totals['outputs']
            )
            self.dc_tree.insert('', tk.END, values=values)
        
        # Update combobox
        dc_line_options = [f"DC Line {dc.dc_number}" for dc in self.dc_lines]
        self.dc_line_combo['values'] = dc_line_options
        self.swh_dc_line_combo['values'] = dc_line_options
        
        if dc_line_options:
            self.selected_dc_line_var.set(dc_line_options[0])
        
        # Update system info and overview
        self.update_system_info()
        self.update_overview()
        
    def show_add_dc_line_dialog(self):
        """Show dialog to add DC line"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Add DC Line")
        dialog.geometry("500x650")  # Increased height for new field
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Method selection
        method_frame = ttk.LabelFrame(dialog, text="Add Method", padding=10)
        method_frame.pack(fill=tk.X, padx=10, pady=10)
        
        method_var = tk.StringVar(value="manual")
        
        ttk.Radiobutton(method_frame, text="Manual Entry", 
                       variable=method_var, value="manual").pack(anchor=tk.W, pady=5)
        ttk.Radiobutton(method_frame, text="Combine Door Types", 
                       variable=method_var, value="combine").pack(anchor=tk.W, pady=5)
        
        # Manual entry frame
        manual_frame = ttk.LabelFrame(dialog, text="Manual Configuration", padding=10)
        
        devices = [
            ("Card Reader", 'smart_card'),
            ("Smart Card Reader", 'smart_card_reader'),  # NEW
            ("Bio-metric Reader", 'fingerprint'),
            ("Door Sensor", 'door_sensor'),
            ("Magnetic Door Lock", 'magnetic_lock'),
            ("Electric Door Lock", 'electric_lock'),
            ("REX Button", 'rex_button'),
            ("Push Button w/ Indicator", 'push_button'),
            ("Break Glass", 'break_glass'),
            ("Buzzer", 'buzzer'),
            ("Double Door Lock", 'double_door_lock'),
            ("DDL Sensors", 'ddl_sensors'),
            ("Unmonitored Single Magnetic Lock", 'unmonitored_single_magnetic_lock'),
            ("Unmonitored Double Magnetic Lock", 'unmonitored_double_magnetic_lock')
        ]
        
        entries = {}
        for i, (label, key) in enumerate(devices):
            ttk.Label(manual_frame, text=label + ":").grid(row=i, column=0, sticky=tk.W, padx=5, pady=2)
            entry = ttk.Entry(manual_frame, width=10)
            entry.insert(0, "0")
            entry.grid(row=i, column=1, padx=5, pady=2)
            entries[key] = entry
        
        # [Rest of the method remains similar...]
        # Door types selection frame - SIMPLIFIED VERSION WITH QUANTITY FOR EACH DOOR TYPE
        combine_frame = ttk.LabelFrame(dialog, text="Select Door Types and Quantities", padding=10)
        
        # Create a scrollable frame for door types
        canvas = tk.Canvas(combine_frame)
        scrollbar = ttk.Scrollbar(combine_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Dictionary to store quantity entries for each door type
        quantity_entries = {}
        
        # Create quantity entries for each door type
        if self.access_door_types:
            for i, dt in enumerate(self.access_door_types):
                frame = ttk.Frame(scrollable_frame)
                frame.pack(fill=tk.X, pady=2, padx=5)
                
                ttk.Label(frame, text=f"{dt.name}:", width=30).pack(side=tk.LEFT)
                entry = ttk.Entry(frame, width=10)
                entry.insert(0, "0")
                entry.pack(side=tk.RIGHT, padx=5)
                quantity_entries[dt.type_id] = entry
        else:
            ttk.Label(scrollable_frame, text="No door types defined yet!", 
                     font=('Arial', 10, 'italic')).pack(pady=20)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        def add_selected_door_types():
            # Create DC line by combining door types with quantities
            dc_number = len(self.dc_lines) + 1
            new_dc_line = DCDevice(dc_number=dc_number)
            
            total_quantity = 0
            
            # Get quantities for each door type
            for dt in self.access_door_types:
                try:
                    quantity = int(quantity_entries[dt.type_id].get())
                    if quantity < 0:
                        messagebox.showerror("Error", f"Quantity for '{dt.name}' cannot be negative")
                        return
                    
                    # Add the door type configuration multiple times based on quantity
                    for _ in range(quantity):
                        new_dc_line.add_configuration(dt.config)
                    
                    total_quantity += quantity
                        
                except ValueError:
                    messagebox.showerror("Error", f"Invalid quantity for '{dt.name}'. Please enter a number.")
                    return
            
            # Check if at least one door type was added
            if total_quantity == 0:
                messagebox.showwarning("Warning", "Please enter quantity > 0 for at least one door type")
                return
            
            self.dc_lines.append(new_dc_line)
            self.update_dc_lines_list()
            dialog.destroy()
            messagebox.showinfo("Success", f"DC Line {dc_number} created successfully with {total_quantity} door type(s)!")
        
        def show_selected_frame():
            if method_var.get() == "manual":
                manual_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
                combine_frame.pack_forget()
                add_button.config(command=add_manual_dc_line)
            else:
                combine_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
                manual_frame.pack_forget()
                add_button.config(command=add_selected_door_types)
        
        method_var.trace('w', lambda *args: show_selected_frame())
        
        def add_manual_dc_line():
            try:
                dc_number = len(self.dc_lines) + 1
                config = {}
                
                for key, entry in entries.items():
                    value = int(entry.get())
                    if value < 0:
                        raise ValueError(f"{key} cannot be negative")
                    config[key] = value
                
                new_dc_line = DCDevice(dc_number=dc_number, **config)
                self.dc_lines.append(new_dc_line)
                self.update_dc_lines_list()
                dialog.destroy()
                messagebox.showinfo("Success", f"DC Line {dc_number} added successfully!")
                
            except ValueError as e:
                messagebox.showerror("Error", f"Invalid input: {str(e)}")
        
        # Buttons
        button_frame = ttk.Frame(dialog)
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        add_button = ttk.Button(button_frame, text="Add DC Line")
        add_button.pack(side=tk.RIGHT, padx=5)
        
        ttk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(side=tk.RIGHT, padx=5)
        
        # Show initial frame
        show_selected_frame()
        
    def show_add_door_type_dialog(self):
        """Show dialog to add door type"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Add Access Door Type")
        dialog.geometry("400x550")  # Increased height
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Name entry
        ttk.Label(dialog, text="Door Type Name:").pack(anchor=tk.W, padx=10, pady=(10, 0))
        name_entry = ttk.Entry(dialog, width=30)
        name_entry.pack(fill=tk.X, padx=10, pady=5)
        
        # Configuration frame
        config_frame = ttk.LabelFrame(dialog, text="Device Configuration", padding=10)
        config_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        devices = [
            ("Card Reader", 'smart_card'),
            ("Smart Card Reader", 'smart_card_reader'),  # NEW
            ("Bio-metric Reader", 'fingerprint'),
            ("Door Sensor", 'door_sensor'),
            ("Magnetic Door Lock", 'magnetic_lock'),
            ("Electric Door Lock", 'electric_lock'),
            ("REX Button", 'rex_button'),
            ("Push Button w/ Indicator", 'push_button'),
            ("Break Glass", 'break_glass'),
            ("Buzzer", 'buzzer'),
            ("Double Door Lock", 'double_door_lock'),
            ("DDL Sensors", 'ddl_sensors'),
            ("Unmonitored Single Magnetic Lock", 'unmonitored_single_magnetic_lock'),
            ("Unmonitored Double Magnetic Lock", 'unmonitored_double_magnetic_lock')
        ]
        
        entries = {}
        for i, (label, key) in enumerate(devices):
            frame = ttk.Frame(config_frame)
            frame.pack(fill=tk.X, pady=2)
            
            ttk.Label(frame, text=label, width=25).pack(side=tk.LEFT)
            entry = ttk.Entry(frame, width=10)
            entry.insert(0, "0")
            entry.pack(side=tk.RIGHT, padx=5)
            entries[key] = entry
        
        def add_door_type():
            try:
                name = name_entry.get().strip()
                if not name:
                    messagebox.showerror("Error", "Please enter a door type name")
                    return
                
                type_id = len(self.access_door_types) + 1
                config = {}
                
                for key, entry in entries.items():
                    value = int(entry.get())
                    if value < 0:
                        raise ValueError(f"{key} cannot be negative")
                    config[key] = value
                
                door_type = AccessDoorType(type_id=type_id, name=name)
                door_type.update_config(**config)
                self.access_door_types.append(door_type)
                
                self.update_door_types_list()
                dialog.destroy()
                messagebox.showinfo("Success", f"Door Type '{name}' added successfully!")
                
            except ValueError as e:
                messagebox.showerror("Error", f"Invalid input: {str(e)}")
        
        # Buttons
        button_frame = ttk.Frame(dialog)
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Button(button_frame, text="Add", command=add_door_type).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(side=tk.RIGHT, padx=5)
        
    def show_edit_dc_line_dialog(self, dc_line):
        """Show dialog to edit DC line"""
        dialog = tk.Toplevel(self.root)
        dialog.title(f"Edit DC Line {dc_line.dc_number}")
        dialog.geometry("400x550")  # Increased height
        dialog.transient(self.root)
        dialog.grab_set()
        
        ttk.Label(dialog, text=f"Edit DC Line {dc_line.dc_number}", 
                 style='Title.TLabel').pack(pady=10)
        
        # Configuration frame
        config_frame = ttk.LabelFrame(dialog, text="Device Configuration", padding=10)
        config_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        devices = [
            ("Card Reader", 'smart_card'),
            ("Smart Card Reader", 'smart_card_reader'),  # NEW
            ("Bio-metric Reader", 'fingerprint'),
            ("Door Sensor", 'door_sensor'),
            ("Magnetic Door Lock", 'magnetic_lock'),
            ("Electric Door Lock", 'electric_lock'),
            ("REX Button", 'rex_button'),
            ("Push Button w/ Indicator", 'push_button'),
            ("Break Glass", 'break_glass'),
            ("Buzzer", 'buzzer'),
            ("Double Door Lock", 'double_door_lock'),
            ("DDL Sensors", 'ddl_sensors'),
            ("Unmonitored Single Magnetic Lock", 'unmonitored_single_magnetic_lock'),
            ("Unmonitored Double Magnetic Lock", 'unmonitored_double_magnetic_lock')
        ]
        
        entries = {}
        for i, (label, key) in enumerate(devices):
            frame = ttk.Frame(config_frame)
            frame.pack(fill=tk.X, pady=2)
            
            ttk.Label(frame, text=label, width=25).pack(side=tk.LEFT)
            entry = ttk.Entry(frame, width=10)
            entry.insert(0, str(getattr(dc_line, key)))
            entry.pack(side=tk.RIGHT, padx=5)
            entries[key] = entry
        
        def save_changes():
            try:
                config = {}
                for key, entry in entries.items():
                    value = int(entry.get())
                    if value < 0:
                        raise ValueError(f"{key} cannot be negative")
                    config[key] = value
                
                for key, value in config.items():
                    setattr(dc_line, key, value)
                
                self.update_dc_lines_list()
                dialog.destroy()
                messagebox.showinfo("Success", f"DC Line {dc_line.dc_number} updated successfully!")
                
            except ValueError as e:
                messagebox.showerror("Error", f"Invalid input: {str(e)}")
        
        # Buttons
        button_frame = ttk.Frame(dialog)
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Button(button_frame, text="Save", command=save_changes).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(side=tk.RIGHT, padx=5)
        
    def show_edit_door_type_dialog(self, door_type):
        """Show dialog to edit door type"""
        dialog = tk.Toplevel(self.root)
        dialog.title(f"Edit Door Type: {door_type.name}")
        dialog.geometry("400x550")  # Increased height
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Name entry
        ttk.Label(dialog, text="Door Type Name:").pack(anchor=tk.W, padx=10, pady=(10, 0))
        name_entry = ttk.Entry(dialog, width=30)
        name_entry.insert(0, door_type.name)
        name_entry.pack(fill=tk.X, padx=10, pady=5)
        
        # Configuration frame
        config_frame = ttk.LabelFrame(dialog, text="Device Configuration", padding=10)
        config_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        devices = [
            ("Card Reader", 'smart_card'),
            ("Smart Card Reader", 'smart_card_reader'),  # NEW
            ("Bio-metric Reader", 'fingerprint'),
            ("Door Sensor", 'door_sensor'),
            ("Magnetic Door Lock", 'magnetic_lock'),
            ("Electric Door Lock", 'electric_lock'),
            ("REX Button", 'rex_button'),
            ("Push Button w/ Indicator", 'push_button'),
            ("Break Glass", 'break_glass'),
            ("Buzzer", 'buzzer'),
            ("Double Door Lock", 'double_door_lock'),
            ("DDL Sensors", 'ddl_sensors'),
            ("Unmonitored Single Magnetic Lock", 'unmonitored_single_magnetic_lock'),
            ("Unmonitored Double Magnetic Lock", 'unmonitored_double_magnetic_lock')
        ]
        
        entries = {}
        for i, (label, key) in enumerate(devices):
            frame = ttk.Frame(config_frame)
            frame.pack(fill=tk.X, pady=2)
            
            ttk.Label(frame, text=label, width=25).pack(side=tk.LEFT)
            entry = ttk.Entry(frame, width=10)
            entry.insert(0, str(getattr(door_type.config, key)))
            entry.pack(side=tk.RIGHT, padx=5)
            entries[key] = entry
        
        def save_changes():
            try:
                name = name_entry.get().strip()
                if not name:
                    messagebox.showerror("Error", "Please enter a door type name")
                    return
                
                config = {}
                for key, entry in entries.items():
                    value = int(entry.get())
                    if value < 0:
                        raise ValueError(f"{key} cannot be negative")
                    config[key] = value
                
                door_type.name = name
                door_type.update_config(**config)
                
                self.update_door_types_list()
                dialog.destroy()
                messagebox.showinfo("Success", f"Door Type '{name}' updated successfully!")
                
            except ValueError as e:
                messagebox.showerror("Error", f"Invalid input: {str(e)}")
        
        # Buttons
        button_frame = ttk.Frame(dialog)
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Button(button_frame, text="Save", command=save_changes).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(side=tk.RIGHT, padx=5)
        
    def select_controllers_for_dc(self, dc_requirements: Dict) -> Dict:
        """Select controllers for a SINGLE DC line with SMART CARD READER support"""
        total_normal_readers = dc_requirements['smart_cards'] + dc_requirements['fingerprints']
        total_smart_readers = dc_requirements['smart_card_readers']
        
        # NEW: Special algorithm for smart card readers
        if total_smart_readers > 0:
            return self.select_controllers_with_smart_readers(total_normal_readers, total_smart_readers)
        else:
            # Original algorithm for no smart card readers
            return self.select_controllers_no_smart_readers(total_normal_readers)
    
    def select_controllers_no_smart_readers(self, total_normal_readers):
        """Original algorithm for systems without smart card readers"""
        best_solution = None
        best_cost = float('inf')
        
        # Maximum possible of each controller type
        max_kt400 = max(1, total_normal_readers // 4 + 2)
        max_kt2 = max(1, total_normal_readers // 2 + 2)
        max_kt1 = max(1, total_normal_readers + 2)
        
        for kt400 in range(max_kt400 + 1):
            for kt2 in range(max_kt2 + 1):
                for kt1 in range(max_kt1 + 1):
                    readers_provided = (kt400 * 4 + kt2 * 2 + kt1 * 1)
                    cost = (kt400 * 1400 + kt2 * 750 + kt1 * 450)
                    
                    # Must meet or exceed reader requirements
                    if readers_provided >= total_normal_readers:
                        if cost < best_cost:
                            best_cost = cost
                            best_solution = {
                                'kt-400': kt400,
                                'kt-2': kt2,
                                'kt-1': kt1,
                                'readers_provided': readers_provided,
                                'cost': cost,
                                'extra_readers': readers_provided - total_normal_readers,
                                'smart_card_readers_provided': 0
                            }
        
        if best_solution:
            # Calculate inputs/outputs provided by these controllers
            inputs_provided = (best_solution['kt-400'] * 16 + 
                             best_solution['kt-2'] * 8 + 
                             best_solution['kt-1'] * 4)
            
            outputs_provided = (best_solution['kt-400'] * 4 + 
                              best_solution['kt-2'] * 2 + 
                              best_solution['kt-1'] * 2)
            
            return {
                **best_solution,
                'inputs_provided': inputs_provided,
                'outputs_provided': outputs_provided,
                'algorithm': 'standard'
            }
        
        return None
    
    def select_controllers_with_smart_readers(self, total_normal_readers, total_smart_readers):
        """NEW: Special algorithm for systems WITH smart card readers"""
        best_solution = None
        best_cost = float('inf')
        
        # Maximum possible of each controller type
        max_kt400 = max(1, (total_normal_readers + total_smart_readers) // 4 + 2)
        max_kt2 = max(1, (total_normal_readers + total_smart_readers) // 2 + 2)
        max_kt1 = max(1, (total_normal_readers + total_smart_readers) + 2)
        
        for kt400 in range(max_kt400 + 1):
            for kt2 in range(max_kt2 + 1):
                for kt1 in range(max_kt1 + 1):
                    # Calculate capacities
                    normal_capacity = (kt400 * 4 + kt2 * 2 + kt1 * 1)
                    smart_capacity = (kt400 * 4 + kt2 * 2 + kt1 * 1)  # Same capacity for smart readers
                    
                    cost = (kt400 * 1400 + kt2 * 750 + kt1 * 450)
                    
                    # Check if this combination can handle both normal and smart readers
                    # Smart readers can use EITHER normal capacity OR smart card reader capacity
                    # So we need to check if total capacity is sufficient
                    total_capacity = normal_capacity + smart_capacity
                    total_required = total_normal_readers + total_smart_readers
                    
                    # Also check that we don't exceed smart reader specific capacity
                    # (smart readers should preferably use smart reader capacity)
                    available_smart_slots = (kt400 * 4 + kt2 * 2 + kt1 * 1)
                    
                    # Combination is valid if:
                    # 1. Total capacity is sufficient for all readers
                    # 2. We have enough smart-specific capacity for smart readers
                    #    (or we can use some normal capacity for smart readers)
                    if (total_capacity >= total_required and 
                        (available_smart_slots >= total_smart_readers or 
                         total_capacity >= total_required)):
                        
                        if cost < best_cost:
                            best_cost = cost
                            
                            # Calculate how capacity is used
                            smart_used = min(total_smart_readers, available_smart_slots)
                            normal_used_for_smart = max(0, total_smart_readers - available_smart_slots)
                            normal_used_for_normal = total_normal_readers
                            
                            best_solution = {
                                'kt-400': kt400,
                                'kt-2': kt2,
                                'kt-1': kt1,
                                'readers_provided': normal_capacity,
                                'smart_card_readers_provided': smart_capacity,
                                'cost': cost,
                                'extra_normal_readers': max(0, normal_capacity - (normal_used_for_normal + normal_used_for_smart)),
                                'extra_smart_readers': max(0, smart_capacity - smart_used),
                                'smart_used': smart_used,
                                'normal_used_for_smart': normal_used_for_smart,
                                'normal_used_for_normal': normal_used_for_normal
                            }
        
        if best_solution:
            # Calculate inputs/outputs provided by these controllers
            inputs_provided = (best_solution['kt-400'] * 16 + 
                             best_solution['kt-2'] * 8 + 
                             best_solution['kt-1'] * 4)
            
            outputs_provided = (best_solution['kt-400'] * 4 + 
                              best_solution['kt-2'] * 2 + 
                              best_solution['kt-1'] * 2)
            
            return {
                **best_solution,
                'inputs_provided': inputs_provided,
                'outputs_provided': outputs_provided,
                'algorithm': 'smart_reader'
            }
        
        return None
        
    def calculate_all_kantech(self):
        """Calculate Kantech system for all DC lines"""
        if not self.dc_lines:
            messagebox.showwarning("Warning", "No DC lines configured!")
            return
        
        self.kantech_results_text.delete(1.0, tk.END)
        
        all_results = []
        grand_total_cost = 0
        total_kt400 = 0
        total_kt2 = 0
        total_kt1 = 0
        total_expansion_cost = 0
        total_smart_readers = 0
        
        for dc_line in self.dc_lines:
            # Get DC line requirements
            dc_totals = dc_line.calculate_totals()
            
            # Select controllers
            controller_info = self.select_controllers_for_dc(dc_totals)
            
            if not controller_info:
                self.kantech_results_text.insert(tk.END, f"❌ No controller combination found for DC Line {dc_line.dc_number}!\n\n")
                continue
            
            # Calculate expansion
            expansion = self.calculate_expansion_for_dc(
                dc_totals['inputs'],
                dc_totals['outputs'],
                controller_info['inputs_provided'],
                controller_info['outputs_provided']
            )
            
            total_cost = controller_info['cost'] + expansion['cost']
            
            # Add to results
            all_results.append({
                'dc_number': dc_line.dc_number,
                'requirements': dc_totals,
                'controllers': controller_info,
                'expansion': expansion,
                'total_cost': total_cost
            })
            
            # Accumulate totals
            grand_total_cost += total_cost
            total_kt400 += controller_info['kt-400']
            total_kt2 += controller_info['kt-2']
            total_kt1 += controller_info['kt-1']
            total_expansion_cost += expansion['cost']
            total_smart_readers += dc_totals.get('smart_card_readers', 0)
        
        # Display results
        result_text = "KANTECH SYSTEM CALCULATION - ALL DC LINES\n"
        result_text += "=" * 60 + "\n\n"
        
        for result in all_results:
            req = result['requirements']
            controllers = result['controllers']
            expansion = result['expansion']
            
            result_text += f"DC Line {result['dc_number']}:\n"
            result_text += f"  Requirements: {req['readers']} readers "
            if req.get('smart_card_readers', 0) > 0:
                result_text += f"({req['smart_cards']} card, {req['smart_card_readers']} smart card, {req['fingerprints']} bio)\n"
            else:
                result_text += f"({req['smart_cards']} card, {req['fingerprints']} bio)\n"
            result_text += f"  Inputs: {req['inputs']}, Outputs: {req['outputs']}\n"
            
            if controllers.get('algorithm') == 'smart_reader':
                result_text += f"  [SMART CARD READER MODE]\n"
                result_text += f"  Controllers: kt-400({controllers['kt-400']}), kt-2({controllers['kt-2']}), kt-1({controllers['kt-1']})\n"
                result_text += f"  Normal reader capacity: {controllers['readers_provided']}\n"
                result_text += f"  Smart reader capacity: {controllers['smart_card_readers_provided']}\n"
                result_text += f"  Allocation: {controllers['smart_used']} smart on smart slots, "
                result_text += f"{controllers['normal_used_for_smart']} smart on normal slots, "
                result_text += f"{controllers['normal_used_for_normal']} normal readers\n"
            else:
                result_text += f"  Controllers: kt-400({controllers['kt-400']}), kt-2({controllers['kt-2']}), kt-1({controllers['kt-1']})\n"
            
            result_text += f"  Controller Cost: ${controllers['cost']}\n"
            result_text += expansion['result']
            result_text += f"  Total Cost for this line: ${result['total_cost']}\n"
            result_text += "-" * 40 + "\n\n"
        
        # Summary
        result_text += "SUMMARY:\n"
        result_text += "=" * 60 + "\n"
        result_text += f"Total Controllers Needed:\n"
        result_text += f"  kt-400: {total_kt400} units  (${total_kt400 * 1400})\n"
        result_text += f"  kt-2:   {total_kt2} units  (${total_kt2 * 750})\n"
        result_text += f"  kt-1:   {total_kt1} units  (${total_kt1 * 450})\n"
        if total_smart_readers > 0:
            result_text += f"  Smart Card Readers in system: {total_smart_readers}\n"
            result_text += f"  Note: Using smart card reader optimized algorithm\n"
        result_text += f"Total controller cost: ${total_kt400 * 1400 + total_kt2 * 750 + total_kt1 * 450}\n"
        result_text += f"Total expansion cost:  ${total_expansion_cost}\n"
        result_text += f"GRAND TOTAL:           ${grand_total_cost}\n"
        
        total_controllers = total_kt400 + total_kt2 + total_kt1
        result_text += f"\nLicense Reference:\n"
        if total_controllers <= 32:
            result_text += f"Total Controllers: {total_controllers} → Kantech Special License\n"
        else:
            result_text += f"Total Controllers: {total_controllers} → Kantech Corporate License\n"
        result_text += f"Note: For redundancy, migrate to Global License + Gateway + Redundancy licenses\n"
        
        self.kantech_results_text.insert(1.0, result_text)
        
        # Store results for export
        self.kantech_all_results = all_results
        self.kantech_grand_total = grand_total_cost
        
    def calculate_selected_kantech(self):
        """Calculate Kantech system for selected DC line"""
        selected = self.selected_dc_line_var.get()
        if not selected or selected == "":
            messagebox.showwarning("Warning", "Please select a DC line")
            return
        
        # Extract DC line number
        try:
            dc_num = int(selected.split(" ")[2])
        except:
            messagebox.showerror("Error", "Invalid DC line selection")
            return
        
        # Find DC line
        dc_line = next((dc for dc in self.dc_lines if dc.dc_number == dc_num), None)
        if not dc_line:
            messagebox.showerror("Error", "DC line not found")
            return
        
        self.kantech_results_text.delete(1.0, tk.END)
        
        # Get DC line requirements
        dc_totals = dc_line.calculate_totals()
        
        result_text = f"KANTECH SYSTEM CALCULATION - DC LINE {dc_num}\n"
        result_text += "=" * 60 + "\n\n"
        result_text += f"Requirements:\n"
        result_text += f"  Total Readers: {dc_totals['readers']}\n"
        result_text += f"  - Card Readers: {dc_totals['smart_cards']}\n"
        result_text += f"  - Smart Card Readers: {dc_totals['smart_card_readers']}\n"
        result_text += f"  - Bio-metric Readers: {dc_totals['fingerprints']}\n"
        result_text += f"  Inputs:  {dc_totals['inputs']}\n"
        result_text += f"  Outputs: {dc_totals['outputs']}\n\n"
        
        # Select controllers
        controller_info = self.select_controllers_for_dc(dc_totals)
        
        if not controller_info:
            result_text += "❌ No controller combination found for this DC line!\n"
            self.kantech_results_text.insert(1.0, result_text)
            return
        
        # Show algorithm used
        if dc_totals['smart_card_readers'] > 0:
            result_text += "⚠️  SMART CARD READER OPTIMIZATION ACTIVE\n"
            result_text += "   Smart card readers use dedicated capacity on controllers\n\n"
        
        result_text += "STEP 1: SELECT CONTROLLERS\n"
        result_text += "-" * 40 + "\n"
        result_text += f"Selected Controllers for DC Line {dc_line.dc_number}:\n"
        result_text += f"  kt-400: {controller_info['kt-400']} units\n"
        result_text += f"  kt-2:   {controller_info['kt-2']} units\n"
        result_text += f"  kt-1:   {controller_info['kt-1']} units\n"
        result_text += f"  Controller Cost: ${controller_info['cost']}\n\n"
        
        if controller_info.get('algorithm') == 'smart_reader':
            result_text += f"SMART CARD READER ALLOCATION:\n"
            result_text += f"  Normal reader capacity: {controller_info['readers_provided']}\n"
            result_text += f"  Smart reader capacity: {controller_info['smart_card_readers_provided']}\n"
            result_text += f"  Smart readers on smart slots: {controller_info['smart_used']}\n"
            result_text += f"  Smart readers on normal slots: {controller_info['normal_used_for_smart']}\n"
            result_text += f"  Normal readers: {controller_info['normal_used_for_normal']}\n"
            result_text += f"  Extra normal capacity: {controller_info['extra_normal_readers']}\n"
            result_text += f"  Extra smart capacity: {controller_info['extra_smart_readers']}\n\n"
        else:
            result_text += f"Controller Capabilities:\n"
            result_text += f"  Readers provided: {controller_info['readers_provided']} ({controller_info['extra_readers']} extra)\n"
        
        result_text += f"I/O Capabilities:\n"
        result_text += f"  Inputs provided:  {controller_info['inputs_provided']}\n"
        result_text += f"  Outputs provided: {controller_info['outputs_provided']}\n\n"
        
        # Calculate expansion
        expansion = self.calculate_expansion_for_dc(
            dc_totals['inputs'],
            dc_totals['outputs'],
            controller_info['inputs_provided'],
            controller_info['outputs_provided']
        )
        
        result_text += expansion['result'] + "\n"
        
        total_cost = controller_info['cost'] + expansion['cost']
        
        result_text += "FINAL COST BREAKDOWN:\n"
        result_text += "-" * 40 + "\n"
        result_text += f"  Controllers: ${controller_info['cost']}\n"
        result_text += f"  Expansion:   ${expansion['cost']}\n"
        result_text += f"  TOTAL:       ${total_cost}\n"
        
        self.kantech_results_text.insert(1.0, result_text)
        
        # Store for export
        if not hasattr(self, 'kantech_single_result'):
            self.kantech_single_result = []
        self.kantech_single_result.append({
            'dc_number': dc_line.dc_number,
            'requirements': dc_totals,
            'controllers': controller_info,
            'expansion': expansion,
            'total_cost': total_cost
        })
        
    def export_kantech_results(self):
        """Export Kantech results to CSV"""
        if not hasattr(self, 'kantech_all_results'):
            messagebox.showwarning("Warning", "Please run Kantech calculations first!")
            return
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            initialfile="kantech_results.csv"
        )
        
        if filename:
            try:
                data = []
                
                for result in self.kantech_all_results:
                    dc_num = result['dc_number']
                    req = result['requirements']
                    controllers = result['controllers']
                    expansion = result['expansion']
                    total_cost = result['total_cost']
                    
                    # DC line requirements
                    data.append({
                        'DC_Line': dc_num,
                        'Type': 'Requirements',
                        'Total_Readers': req['readers'],
                        'Card_Readers': req['smart_cards'],
                        'Smart_Card_Readers': req['smart_card_readers'],
                        'Bio_Readers': req['fingerprints'],
                        'Inputs': req['inputs'],
                        'Outputs': req['outputs'],
                        'KT400': '',
                        'KT2': '',
                        'KT1': '',
                        'Controller_Cost': '',
                        'Expansion_Modules': '',
                        'Expansion_Cost': '',
                        'Total_Cost': ''
                    })
                    
                    # Controllers
                    if controllers.get('algorithm') == 'smart_reader':
                        data.append({
                            'DC_Line': dc_num,
                            'Type': 'Controllers (Smart Mode)',
                            'Total_Readers': controllers['readers_provided'] + controllers['smart_card_readers_provided'],
                            'Card_Readers': '',
                            'Smart_Card_Readers': '',
                            'Bio_Readers': '',
                            'Inputs': controllers['inputs_provided'],
                            'Outputs': controllers['outputs_provided'],
                            'KT400': controllers['kt-400'],
                            'KT2': controllers['kt-2'],
                            'KT1': controllers['kt-1'],
                            'Controller_Cost': controllers['cost'],
                            'Expansion_Modules': '',
                            'Expansion_Cost': '',
                            'Total_Cost': ''
                        })
                    else:
                        data.append({
                            'DC_Line': dc_num,
                            'Type': 'Controllers',
                            'Total_Readers': controllers['readers_provided'],
                            'Card_Readers': '',
                            'Smart_Card_Readers': '',
                            'Bio_Readers': '',
                            'Inputs': controllers['inputs_provided'],
                            'Outputs': controllers['outputs_provided'],
                            'KT400': controllers['kt-400'],
                            'KT2': controllers['kt-2'],
                            'KT1': controllers['kt-1'],
                            'Controller_Cost': controllers['cost'],
                            'Expansion_Modules': '',
                            'Expansion_Cost': '',
                            'Total_Cost': ''
                        })
                    
                    # Expansion
                    if expansion['modules']:
                        modules_str = ', '.join(expansion['modules'])
                        data.append({
                            'DC_Line': dc_num,
                            'Type': 'Expansion',
                            'Total_Readers': '',
                            'Card_Readers': '',
                            'Smart_Card_Readers': '',
                            'Bio_Readers': '',
                            'Inputs': '',
                            'Outputs': '',
                            'KT400': '',
                            'KT2': '',
                            'KT1': '',
                            'Controller_Cost': '',
                            'Expansion_Modules': modules_str,
                            'Expansion_Cost': expansion['cost'],
                            'Total_Cost': ''
                        })
                    else:
                        data.append({
                            'DC_Line': dc_num,
                            'Type': 'Expansion',
                            'Total_Readers': '',
                            'Card_Readers': '',
                            'Smart_Card_Readers': '',
                            'Bio_Readers': '',
                            'Inputs': '',
                            'Outputs': '',
                            'KT400': '',
                            'KT2': '',
                            'KT1': '',
                            'Controller_Cost': '',
                            'Expansion_Modules': 'None',
                            'Expansion_Cost': 0,
                            'Total_Cost': ''
                        })
                    
                    # Total for this DC line
                    data.append({
                        'DC_Line': dc_num,
                        'Type': 'TOTAL',
                        'Total_Readers': '',
                        'Card_Readers': '',
                        'Smart_Card_Readers': '',
                        'Bio_Readers': '',
                        'Inputs': '',
                        'Outputs': '',
                        'KT400': '',
                        'KT2': '',
                        'KT1': '',
                        'Controller_Cost': '',
                        'Expansion_Modules': '',
                        'Expansion_Cost': '',
                        'Total_Cost': total_cost
                    })
                    
                    # Empty row
                    data.append({
                        'DC_Line': '',
                        'Type': '',
                        'Total_Readers': '',
                        'Card_Readers': '',
                        'Smart_Card_Readers': '',
                        'Bio_Readers': '',
                        'Inputs': '',
                        'Outputs': '',
                        'KT400': '',
                        'KT2': '',
                        'KT1': '',
                        'Controller_Cost': '',
                        'Expansion_Modules': '',
                        'Expansion_Cost': '',
                        'Total_Cost': ''
                    })
                
                # Add grand total
                total_kt400 = sum(r['controllers']['kt-400'] for r in self.kantech_all_results)
                total_kt2 = sum(r['controllers']['kt-2'] for r in self.kantech_all_results)
                total_kt1 = sum(r['controllers']['kt-1'] for r in self.kantech_all_results)
                total_controller_cost = sum(r['controllers']['cost'] for r in self.kantech_all_results)
                total_expansion_cost = sum(r['expansion']['cost'] for r in self.kantech_all_results)
                
                data.append({
                    'DC_Line': 'GRAND TOTAL',
                    'Type': 'Summary',
                    'Total_Readers': '',
                    'Card_Readers': '',
                    'Smart_Card_Readers': '',
                    'Bio_Readers': '',
                    'Inputs': '',
                    'Outputs': '',
                    'KT400': total_kt400,
                    'KT2': total_kt2,
                    'KT1': total_kt1,
                    'Controller_Cost': total_controller_cost,
                    'Expansion_Modules': '',
                    'Expansion_Cost': total_expansion_cost,
                    'Total_Cost': self.kantech_grand_total
                })
                
                df = pd.DataFrame(data)
                df.to_csv(filename, index=False)
                
                self.export_status.config(text=f"✅ Results exported to {filename}")
                messagebox.showinfo("Success", f"Results exported to {filename}")
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to export: {str(e)}")
                
    def export_system_summary(self):
        """Export system summary to CSV"""
        if not self.dc_lines:
            messagebox.showwarning("Warning", "No DC lines configured!")
            return
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            initialfile="system_summary.csv"
        )
        
        if filename:
            try:
                data = []
                
                # DC lines summary
                data.append(["DC LINES SUMMARY", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", ""])
                data.append(["DC", "Card Reader", "Smart Card Reader", "Bio-metric", "Door Sensor", "Mag Lock", "Elec Lock", 
                           "REX", "Push Button", "Break Glass", "Buzzer", "DDL", "DDL Sensors",
                           "Unmon Single", "Unmon Double", "Readers", "Inputs", "Outputs"])
                
                for dc in self.dc_lines:
                    totals = dc.calculate_totals()
                    data.append([
                        dc.dc_number,
                        dc.smart_card,
                        dc.smart_card_reader,  # NEW
                        dc.fingerprint,
                        dc.door_sensor,
                        dc.magnetic_lock,
                        dc.electric_lock,
                        dc.rex_button,
                        dc.push_button,
                        dc.break_glass,
                        dc.buzzer,
                        dc.double_door_lock,
                        dc.ddl_sensors,
                        dc.unmonitored_single_magnetic_lock,
                        dc.unmonitored_double_magnetic_lock,
                        totals['readers'],
                        totals['inputs'],
                        totals['outputs']
                    ])
                
                # Totals
                total_smart_card = sum(dc.smart_card for dc in self.dc_lines)
                total_smart_card_reader = sum(dc.smart_card_reader for dc in self.dc_lines)  # NEW
                total_fingerprint = sum(dc.fingerprint for dc in self.dc_lines)
                total_door_sensor = sum(dc.door_sensor for dc in self.dc_lines)
                total_magnetic_lock = sum(dc.magnetic_lock for dc in self.dc_lines)
                total_electric_lock = sum(dc.electric_lock for dc in self.dc_lines)
                total_rex_button = sum(dc.rex_button for dc in self.dc_lines)
                total_push_button = sum(dc.push_button for dc in self.dc_lines)
                total_break_glass = sum(dc.break_glass for dc in self.dc_lines)
                total_buzzer = sum(dc.buzzer for dc in self.dc_lines)
                total_ddl = sum(dc.double_door_lock for dc in self.dc_lines)
                total_ddl_sensors = sum(dc.ddl_sensors for dc in self.dc_lines)
                total_unmon_single = sum(dc.unmonitored_single_magnetic_lock for dc in self.dc_lines)
                total_unmon_double = sum(dc.unmonitored_double_magnetic_lock for dc in self.dc_lines)
                total_readers = sum(dc.calculate_totals()['readers'] for dc in self.dc_lines)
                total_inputs = sum(dc.calculate_totals()['inputs'] for dc in self.dc_lines)
                total_outputs = sum(dc.calculate_totals()['outputs'] for dc in self.dc_lines)
                
                data.append(["TOTAL", 
                           total_smart_card, total_smart_card_reader, total_fingerprint, total_door_sensor,
                           total_magnetic_lock, total_electric_lock, total_rex_button,
                           total_push_button, total_break_glass, total_buzzer,
                           total_ddl, total_ddl_sensors,
                           total_unmon_single, total_unmon_double,
                           total_readers, total_inputs, total_outputs])
                
                # Door types summary
                data.append(["", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", ""])
                data.append(["DOOR TYPES SUMMARY", "", "", "", "", "", "", "", ""])
                data.append(["ID", "Name", "Card Reader", "Smart Card Reader", "Bio-metric", "Door Sensor", "Readers", "Inputs", "Outputs"])
                
                for dt in self.access_door_types:
                    totals = dt.get_totals()
                    data.append([
                        dt.type_id,
                        dt.name,
                        dt.config.smart_card,
                        dt.config.smart_card_reader,  # NEW
                        dt.config.fingerprint,
                        dt.config.door_sensor,
                        totals['readers'],
                        totals['inputs'],
                        totals['outputs']
                    ])
                
                df = pd.DataFrame(data)
                df.to_csv(filename, index=False, header=False)
                
                self.export_status.config(text=f"✅ System summary exported to {filename}")
                messagebox.showinfo("Success", f"System summary exported to {filename}")
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to export: {str(e)}")
    
    # [Other methods remain the same...]
    
    def run(self):
        """Run the GUI application"""
        # Initial updates
        self.update_dc_lines_list()
        self.update_door_types_list()
        # Also update main tab displays
        self.update_system_info()
        self.update_overview()
        
        self.root.mainloop()


def main():
    """Main function to run the application"""
    app = KantechDCCalculatorGUI()
    app.run()


if __name__ == "__main__":
    main()
