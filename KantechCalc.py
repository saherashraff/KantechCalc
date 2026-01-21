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
    
    def calculate_totals(self):
        """Calculate readers, inputs, outputs for this DC line"""
        # Readers = Smart Card + Fingerprint (Excel Column M)
        readers = self.smart_card + self.fingerprint
        
        # Inputs = Door Sensor + REX Button + Push Button + Break Glass + Buzzer + Magnetic Lock + DDL Sensors + Double Door Lock
        # NOTE: Double Door Lock counts as 1 input
        inputs = (self.door_sensor + self.rex_button + self.push_button + 
                 self.break_glass + self.buzzer + self.magnetic_lock + 
                 self.ddl_sensors + self.double_door_lock)  # Add double_door_lock to inputs
        
        # Outputs = Magnetic Lock + Electric Lock + DDL Sensors + Double Door Lock
        # NOTE: Double Door Lock counts as 1 output
        outputs = (self.magnetic_lock + self.electric_lock + 
                  self.ddl_sensors + self.double_door_lock)  # Add double_door_lock to outputs
        
        return {'readers': readers, 'inputs': inputs, 'outputs': outputs}


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
        
        print(f"\nI/O Analysis:")
        print(f"  Required: {dc_inputs} inputs, {dc_outputs} outputs")
        print(f"  Controller provides: {controller_inputs} inputs, {controller_outputs} outputs")
        print(f"  Shortage: {input_shortage} inputs, {output_shortage} outputs")
        
        if input_shortage == 0 and output_shortage == 0:
            print("  ✅ No expansion modules needed")
            return {'modules': [], 'cost': 0, 'input_modules': 0, 'output_modules': 0}
        
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
        
        print(f"  Expansion solution: {expansion_modules}")
        print(f"  Expansion cost: ${expansion_cost}")
        
        return {
            'modules': expansion_modules,
            'cost': expansion_cost,
            'input_modules': input_modules,
            'output_modules': output_modules
        }


class KantechDCCalculator:
    def __init__(self):
        self.dc_lines: List[DCDevice] = []
        self.swh_calculator = SWHControllerCalculator()  # Add SWH calculator
        
        # Controller models - selected ONLY based on readers
        self.controllers = [
            {'name': 'kt-1', 'readers': 1, 'cost': 450, 'inputs': 4, 'outputs': 2},
            {'name': 'kt-2', 'readers': 2, 'cost': 750, 'inputs': 8, 'outputs': 2},
            {'name': 'kt-400', 'readers': 4, 'cost': 1400, 'inputs': 16, 'outputs': 4}
        ]
        
        # All available expansion modules (from your Excel Sheet2)
        self.expansion_modules = [
            {'name': 'inout16 (16/0)', 'inputs': 16, 'outputs': 0, 'cost': 447},
            {'name': 'inout16 (12/4)', 'inputs': 12, 'outputs': 4, 'cost': 447},
            {'name': 'inout16 (8/8)', 'inputs': 8, 'outputs': 8, 'cost': 447},
            {'name': 'inout16 (4/12)', 'inputs': 4, 'outputs': 12, 'cost': 447},
            {'name': 'inout16 (0/16)', 'inputs': 0, 'outputs': 16, 'cost': 447},
            {'name': 'in16', 'inputs': 16, 'outputs': 0, 'cost': 470},
            {'name': 'r8', 'inputs': 0, 'outputs': 8, 'cost': 470}
        ]
        
        # License information - UPDATED with correct logic
        self.license_info = {
            'special': {
                'name': 'Kantech Special License',
                'max_controllers': 32,
                'description': 'For systems with 32 or fewer controllers (non-redundant)',
                'cost': 0  # License cost included in controller cost
            },
            'corporate': {
                'name': 'Kantech Corporate License',
                'min_controllers': 33,
                'description': 'For systems with more than 32 controllers (non-redundant)',
                'cost': 0  # License cost included in controller cost
            },
            'global': {
                'name': 'Global License',
                'description': 'Required for ANY redundancy configuration (replaces Special/Corporate)',
                'cost': 0  # Base license cost
            },
            'gateway': {
                'name': 'Gateway License',
                'description': 'Required for gateway/server communication in redundant systems',
                'cost': 500  # Example cost
            },
            'redundancy': {
                'name': 'Redundancy License',
                'description': 'Additional license for failover/redundancy capability',
                'cost': 750  # Example cost
            }
        }
    
    def clear_screen(self):
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def print_header(self, title):
        print("=" * 60)
        print(f"{title:^60}")
        print("=" * 60)
        print()
    
    def add_dc_line_interactive(self):
        """Interactive DC line addition"""
        self.clear_screen()
        self.print_header("ADD DC LINE CONFIGURATION")
        
        dc_number = len(self.dc_lines) + 1
        print(f"DC Line {dc_number}")
        print("-" * 40)
        
        dc_line = DCDevice(dc_number=dc_number)
        
        # Get device counts
        print("Enter number of devices for this DC line:")
        print()
        
        devices = [
            ("INDOOR Smart Card Reader", 'smart_card'),
            ("Finger Print Reader", 'fingerprint'),
            ("Door Sensor", 'door_sensor'),
            ("Magnetic Door Lock", 'magnetic_lock'),
            ("Electric Door Lock", 'electric_lock'),
            ("REX Button", 'rex_button'),
            ("Push Button w/ Indicator", 'push_button'),
            ("Break Glass", 'break_glass'),
            ("Buzzer", 'buzzer'),
            ("Double Door Lock", 'double_door_lock'),
            ("DDL Sensors", 'ddl_sensors')
        ]
        
        for display_name, attr_name in devices:
            while True:
                try:
                    value = int(input(f"{display_name}: "))
                    if value < 0:
                        print("Enter 0 or positive number")
                        continue
                    setattr(dc_line, attr_name, value)
                    break
                except ValueError:
                    print("Enter a valid number")
        
        self.dc_lines.append(dc_line)
        totals = dc_line.calculate_totals()
        
        print(f"\n✅ DC Line {dc_number} added:")
        print(f"   Readers: {totals['readers']}")
        print(f"   Inputs:  {totals['inputs']}")
        print(f"   Outputs: {totals['outputs']}")
        
        input("\nPress Enter to continue...")
    
    def edit_dc_line_interactive(self):
        """Edit an existing DC line"""
        if not self.dc_lines:
            print("No DC lines configured yet!")
            input("Press Enter to continue...")
            return
        
        self.clear_screen()
        self.print_header("EDIT DC LINE CONFIGURATION")
        
        print("Select DC line to edit:")
        for dc_line in self.dc_lines:
            totals = dc_line.calculate_totals()
            print(f"DC Line {dc_line.dc_number}: {totals['readers']} readers, "
                  f"{totals['inputs']} inputs, {totals['outputs']} outputs")
        
        try:
            dc_num = int(input("\nEnter DC line number to edit: "))
            
            # Find the DC line
            dc_line = next((dc for dc in self.dc_lines if dc.dc_number == dc_num), None)
            
            if not dc_line:
                print(f"DC Line {dc_num} not found!")
                input("Press Enter to continue...")
                return
            
            self.clear_screen()
            self.print_header(f"EDIT DC LINE {dc_num}")
            
            print("Current values in [brackets]. Press Enter to keep current value.")
            print()
            
            devices = [
                ("INDOOR Smart Card Reader", 'smart_card'),
                ("Finger Print Reader", 'fingerprint'),
                ("Door Sensor", 'door_sensor'),
                ("Magnetic Door Lock", 'magnetic_lock'),
                ("Electric Door Lock", 'electric_lock'),
                ("REX Button", 'rex_button'),
                ("Push Button w/ Indicator", 'push_button'),
                ("Break Glass", 'break_glass'),
                ("Buzzer", 'buzzer'),
                ("Double Door Lock", 'double_door_lock'),
                ("DDL Sensors", 'ddl_sensors')
            ]
            
            for display_name, attr_name in devices:
                current_value = getattr(dc_line, attr_name)
                while True:
                    try:
                        value_str = input(f"{display_name} [{current_value}]: ").strip()
                        if value_str == "":
                            value = current_value  # Keep current value
                        else:
                            value = int(value_str)
                            if value < 0:
                                print("Enter 0 or positive number")
                                continue
                        
                        setattr(dc_line, attr_name, value)
                        break
                    except ValueError:
                        print("Enter a valid number or press Enter to keep current value")
            
            totals = dc_line.calculate_totals()
            
            print(f"\n✅ DC Line {dc_num} updated:")
            print(f"   Readers: {totals['readers']}")
            print(f"   Inputs:  {totals['inputs']}")
            print(f"   Outputs: {totals['outputs']}")
            
        except ValueError:
            print("Please enter a valid DC line number!")
        
        input("\nPress Enter to continue...")
    
    def view_dc_summary(self):
        """View all DC lines and their requirements - ENHANCED VERSION showing all device counts"""
        self.clear_screen()
        self.print_header("DC LINE CONFIGURATION SUMMARY - FULL DETAILS")
        
        if not self.dc_lines:
            print("No DC lines configured yet!")
            input("Press Enter to continue...")
            return
        
        # Display detailed table
        headers = [
            "DC", "Smart Card", "Fingerprint", "Door Sensor", 
            "Mag Lock", "Elec Lock", "REX", "Push Button",
            "Break Glass", "Buzzer", "DDL", "DDL Sensors",
            "Readers", "Inputs", "Outputs"
        ]
        
        # Print header
        print(f"{headers[0]:<4}", end="")
        for header in headers[1:12]:  # Device columns
            print(f"{header[:10]:<12}", end="")
        for header in headers[12:]:  # Total columns
            print(f"{header:<8}", end="")
        print()
        print("-" * 160)
        
        # Print each DC line
        for dc_line in self.dc_lines:
            totals = dc_line.calculate_totals()
            
            # Device counts
            print(f"{dc_line.dc_number:<4}", end="")
            print(f"{dc_line.smart_card:<12}", end="")
            print(f"{dc_line.fingerprint:<12}", end="")
            print(f"{dc_line.door_sensor:<12}", end="")
            print(f"{dc_line.magnetic_lock:<12}", end="")
            print(f"{dc_line.electric_lock:<12}", end="")
            print(f"{dc_line.rex_button:<12}", end="")
            print(f"{dc_line.push_button:<12}", end="")
            print(f"{dc_line.break_glass:<12}", end="")
            print(f"{dc_line.buzzer:<12}", end="")
            print(f"{dc_line.double_door_lock:<12}", end="")
            print(f"{dc_line.ddl_sensors:<12}", end="")
            
            # Totals
            print(f"{totals['readers']:<8}", end="")
            print(f"{totals['inputs']:<8}", end="")
            print(f"{totals['outputs']:<8}", end="")
            print()
        
        # Print totals
        print("-" * 160)
        
        # Calculate grand totals
        total_smart_card = sum(dc.smart_card for dc in self.dc_lines)
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
        
        total_readers = sum(dc.calculate_totals()['readers'] for dc in self.dc_lines)
        total_inputs = sum(dc.calculate_totals()['inputs'] for dc in self.dc_lines)
        total_outputs = sum(dc.calculate_totals()['outputs'] for dc in self.dc_lines)
        
        print(f"{'TOTAL':<4}", end="")
        print(f"{total_smart_card:<12}", end="")
        print(f"{total_fingerprint:<12}", end="")
        print(f"{total_door_sensor:<12}", end="")
        print(f"{total_magnetic_lock:<12}", end="")
        print(f"{total_electric_lock:<12}", end="")
        print(f"{total_rex_button:<12}", end="")
        print(f"{total_push_button:<12}", end="")
        print(f"{total_break_glass:<12}", end="")
        print(f"{total_buzzer:<12}", end="")
        print(f"{total_ddl:<12}", end="")
        print(f"{total_ddl_sensors:<12}", end="")
        print(f"{total_readers:<8}", end="")
        print(f"{total_inputs:<8}", end="")
        print(f"{total_outputs:<8}", end="")
        print()
        
        print("\n" + "=" * 160)
        print("NOTE: Each DC line is calculated INDIVIDUALLY")
        
        input("\nPress Enter to continue...")
    
    def select_controllers_for_dc(self, dc_requirements: Dict) -> Dict:
        """Select controllers for a SINGLE DC line based ONLY on reader count"""
        total_readers = dc_requirements['readers']
        
        # Find optimal controller combination for readers only
        best_solution = None
        best_cost = float('inf')
        
        # Maximum possible of each controller type
        max_kt400 = max(1, total_readers // 4 + 2)
        max_kt2 = max(1, total_readers // 2 + 2)
        max_kt1 = max(1, total_readers + 2)
        
        for kt400 in range(max_kt400 + 1):
            for kt2 in range(max_kt2 + 1):
                for kt1 in range(max_kt1 + 1):
                    readers_provided = (kt400 * 4 + kt2 * 2 + kt1 * 1)
                    cost = (kt400 * 1400 + kt2 * 750 + kt1 * 450)
                    
                    # Must meet or exceed reader requirements
                    if readers_provided >= total_readers:
                        if cost < best_cost:
                            best_cost = cost
                            best_solution = {
                                'kt-400': kt400,
                                'kt-2': kt2,
                                'kt-1': kt1,
                                'readers_provided': readers_provided,
                                'cost': cost,
                                'extra_readers': readers_provided - total_readers
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
                'outputs_provided': outputs_provided
            }
        
        return None
    
    def calculate_expansion_for_dc(self, dc_inputs: int, dc_outputs: int, 
                                 controller_inputs: int, controller_outputs: int) -> Dict:
        """Calculate expansion modules needed for a SINGLE DC line"""
        # Calculate shortages
        input_shortage = max(0, dc_inputs - controller_inputs)
        output_shortage = max(0, dc_outputs - controller_outputs)
        
        print(f"\nI/O Analysis:")
        print(f"  Required: {dc_inputs} inputs, {dc_outputs} outputs")
        print(f"  Controllers provide: {controller_inputs} inputs, {controller_outputs} outputs")
        print(f"  Shortage: {input_shortage} inputs, {output_shortage} outputs")
        
        if input_shortage == 0 and output_shortage == 0:
            print("  ✅ No expansion modules needed")
            return {'modules': [], 'cost': 0}
        
        # Try different module combinations to find the cheapest
        best_solution = {'modules': [], 'cost': float('inf')}
        
        # Try single module that covers both needs
        for module in self.expansion_modules:
            if module['inputs'] >= input_shortage and module['outputs'] >= output_shortage:
                solution = {
                    'modules': [module['name']],
                    'cost': module['cost']
                }
                if solution['cost'] < best_solution['cost']:
                    best_solution = solution
        
        # Try combinations of two modules
        for module1 in self.expansion_modules:
            for module2 in self.expansion_modules:
                total_inputs = module1['inputs'] + module2['inputs']
                total_outputs = module1['outputs'] + module2['outputs']
                total_cost = module1['cost'] + module2['cost']
                
                if total_inputs >= input_shortage and total_outputs >= output_shortage:
                    solution = {
                        'modules': [module1['name'], module2['name']],
                        'cost': total_cost
                    }
                    if solution['cost'] < best_solution['cost']:
                        best_solution = solution
        
        # If no solution found with up to 2 modules, use specialized modules
        if best_solution['cost'] == float('inf'):
            expansion_modules = []
            expansion_cost = 0
            
            # Add input modules if needed
            if input_shortage > 0:
                # Use in16 modules (16 inputs each)
                in16_needed = int(np.ceil(input_shortage / 16))
                expansion_modules.append(f"in16 (x{in16_needed})")
                expansion_cost += 470 * in16_needed
            
            # Add output modules if needed
            if output_shortage > 0:
                # Use r8 modules (8 outputs each)
                r8_needed = int(np.ceil(output_shortage / 8))
                expansion_modules.append(f"r8 (x{r8_needed})")
                expansion_cost += 470 * r8_needed
            
            best_solution = {
                'modules': expansion_modules,
                'cost': expansion_cost
            }
        
        print(f"  Expansion solution: {best_solution['modules']}")
        print(f"  Expansion cost: ${best_solution['cost']}")
        
        return best_solution
    
    def calculate_total_controllers(self):
        """Calculate total number of controllers needed for ALL DC lines"""
        if not self.dc_lines:
            return {'total_controllers': 0, 'kt-400': 0, 'kt-2': 0, 'kt-1': 0}
        
        total_kt400 = 0
        total_kt2 = 0
        total_kt1 = 0
        
        for dc_line in self.dc_lines:
            dc_totals = dc_line.calculate_totals()
            controller_info = self.select_controllers_for_dc(dc_totals)
            
            if controller_info:
                total_kt400 += controller_info['kt-400']
                total_kt2 += controller_info['kt-2']
                total_kt1 += controller_info['kt-1']
        
        total_controllers = total_kt400 + total_kt2 + total_kt1
        
        return {
            'total_controllers': total_controllers,
            'kt-400': total_kt400,
            'kt-2': total_kt2,
            'kt-1': total_kt1,
            'breakdown': f"kt-400: {total_kt400}, kt-2: {total_kt2}, kt-1: {total_kt1}"
        }
    
    def calculate_license_requirements(self, use_redundancy=False):
        """Calculate license requirements based on total controllers"""
        self.clear_screen()
        self.print_header("LICENSE CALCULATION")
        
        # Calculate total controllers
        controller_totals = self.calculate_total_controllers()
        total_controllers = controller_totals['total_controllers']
        
        print("📊 CONTROLLER SUMMARY:")
        print("-" * 40)
        print(f"Total Controllers Needed: {total_controllers}")
        print(f"Controller Breakdown:")
        print(f"  kt-400: {controller_totals['kt-400']} units")
        print(f"  kt-2:   {controller_totals['kt-2']} units")
        print(f"  kt-1:   {controller_totals['kt-1']} units")
        print()
        
        print("🎫 LICENSE REQUIREMENTS:")
        print("-" * 40)
        
        # Determine license type based on controller count
        if total_controllers == 0:
            print("❌ No controllers configured!")
            print("Please add DC lines and calculate controllers first.")
            input("\nPress Enter to continue...")
            return
        
        # UPDATED LOGIC: When redundancy is needed, ALWAYS use Global License
        if use_redundancy:
            print(f"🔴 REDUNDANCY CONFIGURATION SELECTED")
            print(f"✅ Required License: {self.license_info['global']['name']}")
            print(f"   Reason: Redundancy requires Global License (replaces Special/Corporate)")
            print(f"   Description: {self.license_info['global']['description']}")
            
            # Additional licenses for redundancy configuration
            print(f"\n➕ ADDITIONAL LICENSES FOR REDUNDANCY:")
            print(f"   1. {self.license_info['gateway']['name']}")
            print(f"      Cost: ${self.license_info['gateway']['cost']}")
            print(f"      Description: {self.license_info['gateway']['description']}")
            
            print(f"\n   2. {self.license_info['redundancy']['name']}")
            print(f"      Cost: ${self.license_info['redundancy']['cost']}")
            print(f"      Description: {self.license_info['redundancy']['description']}")
            
            license_type = 'global'
            additional_licenses = [
                {'name': self.license_info['gateway']['name'], 'cost': self.license_info['gateway']['cost']},
                {'name': self.license_info['redundancy']['name'], 'cost': self.license_info['redundancy']['cost']}
            ]
            
        else:
            # Non-redundant configuration
            if total_controllers <= 32:
                license_type = 'special'
                print(f"✅ Required License: {self.license_info['special']['name']}")
                print(f"   Reason: {total_controllers} controllers ≤ 32")
                print(f"   Description: {self.license_info['special']['description']}")
            else:
                license_type = 'corporate'
                print(f"✅ Required License: {self.license_info['corporate']['name']}")
                print(f"   Reason: {total_controllers} controllers > 32")
                print(f"   Description: {self.license_info['corporate']['description']}")
            
            additional_licenses = []
        
        # Calculate total license cost
        total_license_cost = 0
        if use_redundancy:
            total_license_cost = (self.license_info['gateway']['cost'] + 
                                 self.license_info['redundancy']['cost'])
        
        # Summary
        print("\n" + "=" * 60)
        print("📝 LICENSE SUMMARY:")
        print("-" * 60)
        print(f"Total Controllers: {total_controllers}")
        print(f"Configuration: {'Redundant' if use_redundancy else 'Non-Redundant'}")
        print()
        
        if use_redundancy:
            print(f"PRIMARY LICENSE:")
            print(f"  • {self.license_info['global']['name']}")
            print(f"\nADDITIONAL LICENSES:")
            for license_item in additional_licenses:
                print(f"  • {license_item['name']}: ${license_item['cost']}")
            print(f"\nTOTAL LICENSE COST: ${total_license_cost}")
        else:
            if total_controllers <= 32:
                print(f"PRIMARY LICENSE:")
                print(f"  • {self.license_info['special']['name']}")
            else:
                print(f"PRIMARY LICENSE:")
                print(f"  • {self.license_info['corporate']['name']}")
            print(f"\nADDITIONAL LICENSES: None")
            print(f"TOTAL LICENSE COST: $0 (included in controller cost)")
        
        print("\n" + "=" * 60)
        
        # Store license info for export
        self.license_result = {
            'total_controllers': total_controllers,
            'primary_license': license_type,
            'use_redundancy': use_redundancy,
            'additional_licenses': additional_licenses,
            'total_license_cost': total_license_cost,
            'controller_breakdown': controller_totals
        }
        
        input("\nPress Enter to continue...")
    
    def calculate_single_dc_line(self, dc_line: DCDevice):
        """Calculate Kantech system for a SINGLE DC line"""
        self.clear_screen()
        self.print_header(f"KANTECH - DC LINE {dc_line.dc_number} CALCULATION")
        
        # Get DC line requirements
        dc_totals = dc_line.calculate_totals()
        
        print("📊 DC LINE REQUIREMENTS:")
        print("-" * 40)
        print(f"Readers: {dc_totals['readers']}")
        print(f"Inputs:  {dc_totals['inputs']}")
        print(f"Outputs: {dc_totals['outputs']}")
        print()
        
        # Step 1: Select controllers based ONLY on readers
        print("STEP 1: SELECT CONTROLLERS (Based on readers only)")
        print("-" * 40)
        
        controller_info = self.select_controllers_for_dc(dc_totals)
        
        if not controller_info:
            print("❌ No controller combination found for this DC line!")
            input("Press Enter to continue...")
            return None
        
        print(f"\n✅ Selected Controllers for DC Line {dc_line.dc_number}:")
        print(f"   kt-400: {controller_info['kt-400']} units")
        print(f"   kt-2:   {controller_info['kt-2']} units")
        print(f"   kt-1:   {controller_info['kt-1']} units")
        print(f"   Controller Cost: ${controller_info['cost']}")
        
        print(f"\n📈 Controller Capabilities:")
        print(f"   Readers provided: {controller_info['readers_provided']} ({controller_info['extra_readers']} extra)")
        print(f"   Inputs provided:  {controller_info['inputs_provided']}")
        print(f"   Outputs provided: {controller_info['outputs_provided']}")
        
        # Step 2: Calculate expansion modules for inputs/outputs
        print("\n" + "=" * 60)
        print("STEP 2: CALCULATE EXPANSION MODULES")
        print("-" * 40)
        
        expansion = self.calculate_expansion_for_dc(
            dc_totals['inputs'],
            dc_totals['outputs'],
            controller_info['inputs_provided'],
            controller_info['outputs_provided']
        )
        
        # Display final results
        print("\n" + "=" * 60)
        print("💰 FINAL COST BREAKDOWN:")
        print("-" * 40)
        total_cost = controller_info['cost'] + expansion['cost']
        print(f"   Controllers: ${controller_info['cost']}")
        print(f"   Expansion:   ${expansion['cost']}")
        print(f"   {'TOTAL:':<12} ${total_cost}")
        print("=" * 60)
        
        # Return calculation results
        return {
            'dc_number': dc_line.dc_number,
            'requirements': dc_totals,
            'controllers': controller_info,
            'expansion': expansion,
            'total_cost': total_cost
        }
    
    def calculate_single_swh_dc_line(self, dc_line: DCDevice):
        """Calculate SWH system for a SINGLE DC line"""
        self.clear_screen()
        self.print_header(f"SWH GSTAR - DC LINE {dc_line.dc_number} CALCULATION")
        
        # Get DC line requirements
        dc_totals = dc_line.calculate_totals()
        
        print("📊 DC LINE REQUIREMENTS:")
        print("-" * 40)
        print(f"Readers: {dc_totals['readers']}")
        print(f"Inputs:  {dc_totals['inputs']}")
        print(f"Outputs: {dc_totals['outputs']}")
        print()
        
        # Step 1: Select controller based ONLY on readers
        print("STEP 1: SELECT GSTAR CONTROLLER (Based on readers only)")
        print("-" * 40)
        
        controller = self.swh_calculator.select_controller_for_readers(dc_totals['readers'])
        
        if not controller:
            print(f"❌ No suitable GSTAR controller found for {dc_totals['readers']} readers!")
            print("   Consider using a different system or multiple DC lines")
            input("Press Enter to continue...")
            return None
        
        print(f"\n✅ Selected Controller for DC Line {dc_line.dc_number}:")
        print(f"   {controller.name}")
        print(f"   Readers provided: {controller.readers}")
        print(f"   Controller Cost: ${controller.price}")
        print(f"   ACM Modules included: {controller.number_of_acm}")
        
        print(f"\n📈 Controller I/O Capabilities:")
        print(f"   Inputs provided:  {controller.inputs}")
        print(f"   Outputs provided: {controller.outputs}")
        
        # Step 2: Calculate expansion modules for inputs/outputs
        print("\n" + "=" * 60)
        print("STEP 2: CALCULATE SWH EXPANSION MODULES")
        print("-" * 40)
        
        expansion = self.swh_calculator.calculate_expansion_for_swh(
            dc_totals['inputs'],
            dc_totals['outputs'],
            controller.inputs,
            controller.outputs
        )
        
        # Display final results for this DC line
        print("\n" + "=" * 60)
        print("💰 FINAL COST BREAKDOWN:")
        print("-" * 40)
        total_cost = controller.price + expansion['cost']
        print(f"   Controller: ${controller.price}")
        print(f"   Expansion:  ${expansion['cost']}")
        print(f"   ACM Modules: {controller.number_of_acm} included")
        print(f"   {'TOTAL:':<12} ${total_cost}")
        print("=" * 60)
        
        # Return calculation results
        return {
            'dc_number': dc_line.dc_number,
            'requirements': dc_totals,
            'controller': controller,
            'expansion': expansion,
            'total_cost': total_cost,
            'status': 'Suitable'
        }
    
    def calculate_all_dc_lines(self):
        """Calculate Kantech system for EACH DC line individually"""
        if not self.dc_lines:
            print("No DC lines configured!")
            input("Press Enter to continue...")
            return
        
        all_results = []
        
        for dc_line in self.dc_lines:
            result = self.calculate_single_dc_line(dc_line)
            if result:
                all_results.append(result)
                # Show detailed info for each line including the last one
                if dc_line != self.dc_lines[-1]:  # If not the last DC line
                    input("\nPress Enter to see next DC line...")
                else:
                    # For the last line, show summary after calculation
                    print("\n" + "=" * 60)
                    print("LAST DC LINE CALCULATION COMPLETE!")
                    print("Press Enter to see summary of all DC lines...")
                    input()
        
        if not all_results:
            return
        
        # Display summary of all DC lines
        self.clear_screen()
        self.print_header("ALL DC LINES CALCULATION SUMMARY")
        
        print("📋 SUMMARY OF ALL DC LINES:")
        print("=" * 90)
        print(f"{'DC Line':<8} {'Requirements':<20} {'Controllers':<25} {'Expansion':<25} {'Total Cost':<12}")
        print("-" * 90)
        
        grand_total_cost = 0
        total_kt400 = 0
        total_kt2 = 0
        total_kt1 = 0
        total_expansion_cost = 0
        
        for result in all_results:
            req = result['requirements']
            controllers = result['controllers']
            expansion = result['expansion']
            total_cost = result['total_cost']
            
            # Build requirement string
            req_str = f"{req['readers']}R/{req['inputs']}I/{req['outputs']}O"
            
            # Build controller string
            controller_str = ""
            if controllers['kt-400'] > 0:
                controller_str += f"kt-400({controllers['kt-400']}) "
            if controllers['kt-2'] > 0:
                controller_str += f"kt-2({controllers['kt-2']}) "
            if controllers['kt-1'] > 0:
                controller_str += f"kt-1({controllers['kt-1']}) "
            if not controller_str:
                controller_str = "None"
            
            # Build expansion string
            expansion_str = ", ".join(expansion['modules']) if expansion['modules'] else "None"
            
            print(f"{result['dc_number']:<8} {req_str:<20} {controller_str:<25} {expansion_str:<25} ${total_cost:<10}")
            
            # Accumulate totals
            grand_total_cost += total_cost
            total_kt400 += controllers['kt-400']
            total_kt2 += controllers['kt-2']
            total_kt1 += controllers['kt-1']
            total_expansion_cost += expansion['cost']
        
        print("-" * 90)
        print(f"{'GRAND TOTAL':<78} ${grand_total_cost}")
        print()
        
        print("\n📊 TOTAL CONTROLLERS NEEDED:")
        print("-" * 40)
        print(f"kt-400: {total_kt400} units  (${total_kt400 * 1400})")
        print(f"kt-2:   {total_kt2} units  (${total_kt2 * 750})")
        print(f"kt-1:   {total_kt1} units  (${total_kt1 * 450})")
        print(f"Total controller cost: ${total_kt400 * 1400 + total_kt2 * 750 + total_kt1 * 450}")
        print(f"Total expansion cost:  ${total_expansion_cost}")
        print(f"GRAND TOTAL:           ${grand_total_cost}")
        
        # Calculate total controllers for license reference
        total_controllers = total_kt400 + total_kt2 + total_kt1
        print(f"\n🎫 LICENSE REFERENCE:")
        print("-" * 40)
        if total_controllers <= 32:
            print(f"Total Controllers: {total_controllers} → Kantech Special License")
            print(f"Note: For redundancy, migrate to Global License + Gateway + Redundancy licenses")
        else:
            print(f"Total Controllers: {total_controllers} → Kantech Corporate License")
            print(f"Note: For redundancy, migrate to Global License + Gateway + Redundancy licenses")
        
        # Store all results for export
        self.all_results = all_results
        self.grand_total = grand_total_cost
        
        input("\nPress Enter to continue...")
    
    def calculate_specific_dc_line(self):
        """Calculate Kantech system for a SPECIFIC DC line"""
        if not self.dc_lines:
            print("No DC lines configured!")
            input("Press Enter to continue...")
            return
        
        self.clear_screen()
        self.print_header("CALCULATE SPECIFIC DC LINE (KANTECH)")
        
        print("Available DC Lines:")
        for dc_line in self.dc_lines:
            totals = dc_line.calculate_totals()
            print(f"DC Line {dc_line.dc_number}: {totals['readers']} readers, "
                  f"{totals['inputs']} inputs, {totals['outputs']} outputs")
        
        try:
            dc_num = int(input("\nEnter DC line number to calculate: "))
            
            # Find the DC line
            dc_line = next((dc for dc in self.dc_lines if dc.dc_number == dc_num), None)
            
            if dc_line:
                result = self.calculate_single_dc_line(dc_line)
                if result:
                    # Store for export
                    if not hasattr(self, 'single_result'):
                        self.single_result = []
                    self.single_result.append(result)
                    
                    # Ask user what to do next
                    print("\nOptions:")
                    print("1. Return to main menu")
                    print("2. Calculate another DC line")
                    
                    choice = input("\nSelect option (1-2): ")
                    if choice == '2':
                        self.calculate_specific_dc_line()
            else:
                print(f"DC Line {dc_num} not found!")
                input("Press Enter to continue...")
                
        except ValueError:
            print("Please enter a valid DC line number!")
            input("Press Enter to continue...")
    
    def calculate_specific_swh_dc_line(self):
        """Calculate SWH system for a SPECIFIC DC line"""
        if not self.dc_lines:
            print("No DC lines configured!")
            input("Press Enter to continue...")
            return
        
        self.clear_screen()
        self.print_header("CALCULATE SPECIFIC DC LINE (SWH GSTAR)")
        
        print("Available DC Lines:")
        for dc_line in self.dc_lines:
            totals = dc_line.calculate_totals()
            print(f"DC Line {dc_line.dc_number}: {totals['readers']} readers, "
                  f"{totals['inputs']} inputs, {totals['outputs']} outputs")
        
        try:
            dc_num = int(input("\nEnter DC line number to calculate: "))
            
            # Find the DC line
            dc_line = next((dc for dc in self.dc_lines if dc.dc_number == dc_num), None)
            
            if dc_line:
                result = self.calculate_single_swh_dc_line(dc_line)
                if result:
                    # Store for export
                    if not hasattr(self, 'single_swh_result'):
                        self.single_swh_result = []
                    self.single_swh_result.append(result)
                    
                    # Ask user what to do next
                    print("\nOptions:")
                    print("1. Return to main menu")
                    print("2. Calculate another SWH DC line")
                    print("3. Calculate SWH license for this line")
                    
                    choice = input("\nSelect option (1-3): ")
                    if choice == '2':
                        self.calculate_specific_swh_dc_line()
                    elif choice == '3':
                        # Calculate license for this single line
                        if hasattr(self, 'single_swh_result'):
                            # Calculate total readers from single result
                            total_readers = result['requirements']['readers']
                            
                            self.clear_screen()
                            self.print_header(f"SWH LICENSE FOR DC LINE {dc_num}")
                            
                            print(f"Total Readers in DC Line {dc_num}: {total_readers}")
                            print()
                            print("Available Licenses:")
                            print("-" * 60)
                            
                            suitable_licenses = []
                            for license_info in self.swh_calculator.swh_licenses:
                                max_readers = license_info['max_readers']
                                status = "✓ Suitable" if max_readers >= total_readers else "✗ Insufficient"
                                print(f"  {license_info['name']:<12} Max Readers: {max_readers:<6} {status}")
                                if max_readers >= total_readers:
                                    suitable_licenses.append(license_info)
                            
                            if suitable_licenses:
                                suitable_licenses.sort(key=lambda x: x['max_readers'])
                                recommended_license = suitable_licenses[0]
                                
                                print(f"\n✅ RECOMMENDED LICENSE:")
                                print(f"   {recommended_license['name']}")
                                print(f"   Supports up to {recommended_license['max_readers']} readers")
                                print(f"   Cost: ${recommended_license['cost']} (included in controller cost)")
                            else:
                                print(f"\n❌ NO SUITABLE LICENSE FOUND!")
                            
                            input("\nPress Enter to continue...")
            else:
                print(f"DC Line {dc_num} not found!")
                input("Press Enter to continue...")
                
        except ValueError:
            print("Please enter a valid DC line number!")
            input("Press Enter to continue...")
    
    def calculate_all_gstar_dc_lines(self):
        """Calculate SWH system for EACH DC line individually"""
        if not self.dc_lines:
            print("No DC lines configured!")
            input("Press Enter to continue...")
            return
        
        all_results = []
        total_system_readers = 0
        
        for dc_line in self.dc_lines:
            result = self.calculate_single_swh_dc_line(dc_line)
            if result:
                all_results.append(result)
                total_system_readers += result['requirements']['readers']
                
                # Show detailed info for each line including the last one
                if dc_line != self.dc_lines[-1]:  # If not the last DC line
                    input("\nPress Enter to see next DC line...")
                else:
                    # For the last line, show summary after calculation
                    print("\n" + "=" * 60)
                    print("LAST DC LINE CALCULATION COMPLETE!")
                    print("Press Enter to see summary of all DC lines...")
                    input()
        
        if not all_results:
            return
        
        # Display summary of all DC lines
        self.clear_screen()
        self.print_header("ALL DC LINES - GSTAR CALCULATION SUMMARY")
        
        print("📋 SUMMARY OF ALL DC LINES (GSTAR SYSTEM):")
        print("=" * 100)
        print(f"{'DC Line':<8} {'Requirements':<20} {'Controller':<25} {'Price':<12} {'Expansion':<25} {'Total Cost':<12}")
        print("-" * 100)
        
        grand_total_cost = 0
        total_controllers = 0
        total_expansion_cost = 0
        total_as0073 = 0  # Input modules
        total_as0074 = 0  # Output modules
        
        for result in all_results:
            req = result['requirements']
            controller = result['controller']
            expansion = result['expansion']
            total_cost = result['total_cost']
            
            # Build requirement string
            req_str = f"{req['readers']}R/{req['inputs']}I/{req['outputs']}O"
            
            # Build controller string
            if controller:
                controller_name = controller.name
                controller_price = f"${controller.price}"
                total_controllers += 1
            else:
                controller_name = "None"
                controller_price = "N/A"
            
            # Build expansion string
            expansion_str = ", ".join(expansion['modules']) if expansion['modules'] else "None"
            
            print(f"{result['dc_number']:<8} {req_str:<20} {controller_name:<25} {controller_price:<12} {expansion_str:<25} ${total_cost:<10}")
            
            # Accumulate totals
            grand_total_cost += total_cost
            total_expansion_cost += expansion['cost']
            
            # Count expansion modules
            total_as0073 += expansion.get('input_modules', 0)
            total_as0074 += expansion.get('output_modules', 0)
        
        print("-" * 100)
        print(f"{'GRAND TOTAL':<78} ${grand_total_cost}")
        print()
        
        print("\n📊 TOTAL HARDWARE NEEDED:")
        print("-" * 40)
        print(f"Total GSTAR Controllers: {total_controllers}")
        print(f"Total Expansion Modules:")
        print(f"  AS0073-000 (8-input): {total_as0073} units  (${total_as0073 * 333})")
        print(f"  AS0074-000 (8-output): {total_as0074} units  (${total_as0074 * 395})")
        print(f"Total controller cost: ${sum(r['controller'].price for r in all_results if r['controller'])}")
        print(f"Total expansion cost:  ${total_expansion_cost}")
        print(f"GRAND TOTAL HARDWARE:  ${grand_total_cost}")
        
        # Store GSTAR results
        self.gstar_results = {
            'all_results': all_results,
            'total_controllers': total_controllers,
            'total_cost': grand_total_cost,
            'total_readers': total_system_readers,
            'total_input_modules': total_as0073,
            'total_output_modules': total_as0074,
            'total_expansion_cost': total_expansion_cost
        }
        
        print(f"\n📈 SYSTEM SUMMARY:")
        print(f"  Total DC Lines: {len(self.dc_lines)}")
        print(f"  Total Controllers Needed: {total_controllers}")
        print(f"  Total Readers in System: {total_system_readers}")
        print(f"  Total System Cost: ${grand_total_cost}")
        
        # Ask if user wants to calculate SWH license
        print("\n🎫 Would you like to calculate SWH License requirements?")
        choice = input("Enter 'Y' for Yes, any other key to skip: ").strip().upper()
        
        if choice == 'Y':
            self.calculate_swh_license()
        
        input("\nPress Enter to continue...")
    
    def calculate_swh_license(self):
        """Calculate SWH license based on total readers"""
        if not hasattr(self, 'gstar_results'):
            print("Please calculate GSTAR controllers first!")
            input("Press Enter to continue...")
            return
        
        self.clear_screen()
        self.print_header("SWH LICENSE CALCULATION (BASED ON TOTAL READERS)")
        
        total_readers = self.gstar_results['total_readers']
        
        print("📊 LICENSE REQUIREMENTS:")
        print("-" * 60)
        print(f"Total Readers in System: {total_readers}")
        print()
        print("Available Licenses (from SWH Access.xlsx):")
        print("-" * 60)
        
        # Display all license options
        for license_info in self.swh_calculator.swh_licenses:
            max_readers = license_info['max_readers']
            status = "✓ Suitable" if max_readers >= total_readers else "✗ Insufficient"
            print(f"  {license_info['name']:<12} Max Readers: {max_readers:<6} {status}")
        
        print("-" * 60)
        
        # Find the cheapest suitable license
        suitable_licenses = []
        for license_info in self.swh_calculator.swh_licenses:
            if license_info['max_readers'] >= total_readers:
                suitable_licenses.append(license_info)
        
        if suitable_licenses:
            # Select the smallest suitable license
            suitable_licenses.sort(key=lambda x: x['max_readers'])
            recommended_license = suitable_licenses[0]
            
            print(f"\n✅ RECOMMENDED LICENSE:")
            print(f"   {recommended_license['name']}")
            print(f"   Supports up to {recommended_license['max_readers']} readers")
            print(f"   Cost: ${recommended_license['cost']} (included in controller cost)")
            
            # Store license result
            self.swh_license_result = {
                'total_readers': total_readers,
                'selected_license': recommended_license['name'],
                'max_readers': recommended_license['max_readers'],
                'cost': recommended_license['cost']
            }
            
            # Export option
            print("\n💾 Would you like to export these results?")
            export_choice = input("Enter 'Y' for Yes, any other key to skip: ").strip().upper()
            if export_choice == 'Y':
                self.export_gstar_results()
        else:
            print(f"\n❌ NO SUITABLE LICENSE FOUND!")
            print(f"   Your system has {total_readers} readers")
            print(f"   Maximum available license supports {self.swh_calculator.swh_licenses[-1]['max_readers']} readers")
            print(f"   Consider splitting the system or contacting SWH for enterprise solutions")
        
        input("\nPress Enter to continue...")
    
    def export_all_results_to_csv(self):
        """Export ALL DC line results to CSV"""
        if not hasattr(self, 'all_results'):
            print("Please run calculations for all DC lines first!")
            input("Press Enter to continue...")
            return
        
        self.clear_screen()
        self.print_header("EXPORT ALL DC LINE RESULTS")
        
        filename = input("Enter filename (default: kantech_dc_lines.csv): ").strip()
        if not filename:
            filename = "kantech_dc_lines.csv"
        
        if not filename.endswith('.csv'):
            filename += '.csv'
        
        # Create DataFrame for export
        data = []
        
        # Add each DC line's results
        for result in self.all_results:
            dc_num = result['dc_number']
            req = result['requirements']
            controllers = result['controllers']
            expansion = result['expansion']
            
            # DC line requirements
            data.append({
                'DC_Line': dc_num,
                'Type': 'Requirements',
                'Readers': req['readers'],
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
            
            # Controllers for this DC line
            data.append({
                'DC_Line': dc_num,
                'Type': 'Controllers',
                'Readers': controllers['readers_provided'],
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
            
            # Expansion modules for this DC line
            if expansion['modules']:
                modules_str = ', '.join(expansion['modules'])
                data.append({
                    'DC_Line': dc_num,
                    'Type': 'Expansion',
                    'Readers': '',
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
                    'Readers': '',
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
                'Readers': '',
                'Inputs': '',
                'Outputs': '',
                'KT400': '',
                'KT2': '',
                'KT1': '',
                'Controller_Cost': '',
                'Expansion_Modules': '',
                'Expansion_Cost': '',
                'Total_Cost': result['total_cost']
            })
            
            # Add empty row between DC lines
            data.append({
                'DC_Line': '',
                'Type': '',
                'Readers': '',
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
        
        # Add license information if available
        if hasattr(self, 'license_result'):
            license_info = self.license_result
            
            # Primary license info
            if license_info['use_redundancy']:
                primary_license_name = self.license_info['global']['name']
            elif license_info['total_controllers'] <= 32:
                primary_license_name = self.license_info['special']['name']
            else:
                primary_license_name = self.license_info['corporate']['name']
            
            data.append({
                'DC_Line': 'LICENSE INFO',
                'Type': 'System Configuration',
                'Readers': f"{'Redundant' if license_info['use_redundancy'] else 'Non-Redundant'}",
                'Inputs': f"Total Controllers: {license_info['total_controllers']}",
                'Outputs': '',
                'KT400': '',
                'KT2': '',
                'KT1': '',
                'Controller_Cost': '',
                'Expansion_Modules': '',
                'Expansion_Cost': '',
                'Total_Cost': ''
            })
            
            data.append({
                'DC_Line': 'LICENSE INFO',
                'Type': 'Primary License',
                'Readers': primary_license_name,
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
            
            # Additional licenses if redundancy
            if license_info['use_redundancy']:
                for license_item in license_info['additional_licenses']:
                    data.append({
                        'DC_Line': 'LICENSE INFO',
                        'Type': 'Additional License',
                        'Readers': license_item['name'],
                        'Inputs': f"Cost: ${license_item['cost']}",
                        'Outputs': '',
                        'KT400': '',
                        'KT2': '',
                        'KT1': '',
                        'Controller_Cost': '',
                        'Expansion_Modules': '',
                        'Expansion_Cost': '',
                        'Total_Cost': ''
                    })
                
                data.append({
                    'DC_Line': 'LICENSE INFO',
                    'Type': 'Total License Cost',
                    'Readers': f"${license_info['total_license_cost']}",
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
        total_kt400 = sum(r['controllers']['kt-400'] for r in self.all_results)
        total_kt2 = sum(r['controllers']['kt-2'] for r in self.all_results)
        total_kt1 = sum(r['controllers']['kt-1'] for r in self.all_results)
        total_controller_cost = sum(r['controllers']['cost'] for r in self.all_results)
        total_expansion_cost = sum(r['expansion']['cost'] for r in self.all_results)
        
        data.append({
            'DC_Line': 'GRAND TOTAL',
            'Type': 'Summary',
            'Readers': '',
            'Inputs': '',
            'Outputs': '',
            'KT400': total_kt400,
            'KT2': total_kt2,
            'KT1': total_kt1,
            'Controller_Cost': total_controller_cost,
            'Expansion_Modules': '',
            'Expansion_Cost': total_expansion_cost,
            'Total_Cost': self.grand_total
        })
        
        df = pd.DataFrame(data)
        df.to_csv(filename, index=False)
        
        print(f"\n✅ All DC line results exported to {filename}")
        input("\nPress Enter to continue...")
    
    def export_gstar_results(self):
        """Export GSTAR controller and license results to CSV"""
        if not hasattr(self, 'gstar_results'):
            print("No GSTAR results to export!")
            input("Press Enter to continue...")
            return
        
        self.clear_screen()
        self.print_header("EXPORT GSTAR RESULTS")
        
        filename = input("Enter filename (default: gstar_results.csv): ").strip()
        if not filename:
            filename = "gstar_results.csv"
        
        if not filename.endswith('.csv'):
            filename += '.csv'
        
        # Prepare data for export
        data = []
        
        # Add GSTAR controller results
        data.append(["GSTAR/SWH SYSTEM RESULTS", "", "", "", "", "", "", ""])
        data.append(["DC Line", "Readers", "Inputs", "Outputs", "Selected Controller", "Price", "Expansion Modules", "Total Cost"])
        
        for result in self.gstar_results['all_results']:
            requirements = result['requirements']
            controller = result['controller']
            expansion = result['expansion']
            total_cost = result['total_cost']
            
            if controller:
                expansion_str = ", ".join(expansion['modules']) if expansion['modules'] else "None"
                data.append([
                    result['dc_number'],
                    requirements['readers'],
                    requirements['inputs'],
                    requirements['outputs'],
                    controller.name,
                    controller.price,
                    expansion_str,
                    total_cost
                ])
            else:
                data.append([
                    result['dc_number'],
                    requirements['readers'],
                    requirements['inputs'],
                    requirements['outputs'],
                    "No suitable controller",
                    "N/A",
                    "N/A",
                    "N/A"
                ])
        
        # Add summary
        data.append(["", "", "", "", "", "", "", ""])
        data.append(["SUMMARY", "", "", "", "", "", "", ""])
        data.append(["Total Controllers", self.gstar_results['total_controllers'], "", "", "Total Cost", self.gstar_results['total_cost'], "", ""])
        data.append(["Total Readers", self.gstar_results['total_readers'], "", "", "Total Expansion Cost", self.gstar_results['total_expansion_cost'], "", ""])
        data.append(["AS0073-000 Modules", self.gstar_results['total_input_modules'], "", "", "AS0074-000 Modules", self.gstar_results['total_output_modules'], "", ""])
        
        # Add license information if available
        if hasattr(self, 'swh_license_result'):
            data.append(["", "", "", "", "", "", "", ""])
            data.append(["LICENSE INFORMATION", "", "", "", "", "", "", ""])
            data.append([
                "Total Readers",
                self.swh_license_result['total_readers'],
                "",
                "",
                "Selected License",
                self.swh_license_result['selected_license'],
                f"Max Readers: {self.swh_license_result['max_readers']}",
                ""
            ])
            data.append(["License Cost", self.swh_license_result['cost'], "", "", "", "", "", ""])
        
        # Export to CSV
        try:
            df = pd.DataFrame(data)
            df.to_csv(filename, index=False, header=False)
            print(f"\n✅ Results exported to {filename}")
        except Exception as e:
            print(f"\n❌ Error exporting: {e}")
        
        input("\nPress Enter to continue...")
    
    def export_menu(self):
        """Menu for export options"""
        self.clear_screen()
        self.print_header("EXPORT RESULTS")
        
        print("Select export option:")
        print("1. Export Kantech Results (All DC lines)")
        print("2. Export GSTAR Results")
        print("3. Back to Main Menu")
        print()
        
        try:
            choice = int(input("Select option (1-3): "))
        except ValueError:
            print("Invalid input!")
            input("Press Enter to continue...")
            return
        
        if choice == 1:
            self.export_all_results_to_csv()
        elif choice == 2:
            self.export_gstar_results()
        elif choice == 3:
            return
        else:
            print("Invalid choice!")
            input("Press Enter to continue...")
    
    def main_menu(self):
        """Display main menu"""
        while True:
            self.clear_screen()
            self.print_header("ACCESS CONTROL SYSTEM CALCULATOR")
            
            print("CALCULATION OPTIONS:")
            print("A. KANTECH SYSTEM (Multiple controllers per DC line)")
            print("   - Each DC line calculated INDIVIDUALLY")
            print("   - Controllers selected based on readers only")
            print("   - Expansion modules for I/O requirements")
            print()
            print("B. GSTAR/SWH SYSTEM (Kantech-style logic)")
            print("   - Each DC line gets ONE GSTAR controller (based on readers only)")
            print("   - AS0073-000 modules for input shortages (8 inputs each, $333)")
            print("   - AS0074-000 modules for output shortages (8 outputs each, $395)")
            print("   - License based on total readers (CC9000 series)")
            print()
            
            if self.dc_lines:
                print(f"📊 CURRENT SYSTEM: {len(self.dc_lines)} DC line(s)")
                total_readers = sum(dc.calculate_totals()['readers'] for dc in self.dc_lines)
                total_inputs = sum(dc.calculate_totals()['inputs'] for dc in self.dc_lines)
                total_outputs = sum(dc.calculate_totals()['outputs'] for dc in self.dc_lines)
                print(f"   Total Requirements: {total_readers} readers, {total_inputs} inputs, {total_outputs} outputs")
            else:
                print("No DC lines configured yet")
            print()
            
            print("MAIN MENU:")
            print("1. Add DC Line Configuration")
            print("2. Edit DC Line Configuration")
            print("3. View DC Lines Summary (Detailed)")
            print("4. Calculate Specific DC Line (Kantech)")
            print("5. Calculate Specific DC Line (SWH GSTAR)")  # NEW OPTION
            print("6. Calculate ALL DC Lines (Kantech)")
            print("7. Calculate ALL DC Lines (SWH GSTAR)")
            print("8. Calculate License Requirements (Kantech)")
            print("9. Calculate SWH License (Based on readers)")
            print("10. Export Results")
            print("11. Clear All Data")
            print("12. Exit")
            print()
            
            try:
                choice = int(input("Select option (1-12): "))
            except ValueError:
                print("Enter a number 1-12")
                input("Press Enter to continue...")
                continue
            
            if choice == 1:
                self.add_dc_line_interactive()
            elif choice == 2:
                self.edit_dc_line_interactive()
            elif choice == 3:
                self.view_dc_summary()  # This now shows detailed view
            elif choice == 4:
                self.calculate_specific_dc_line()
            elif choice == 5:  # NEW: Calculate specific SWH DC line
                self.calculate_specific_swh_dc_line()
            elif choice == 6:
                self.calculate_all_dc_lines()
            elif choice == 7:  # Changed from 6 to 7
                self.calculate_all_gstar_dc_lines()
            elif choice == 8:  # Changed from 7 to 8
                self.calculate_license_menu()
            elif choice == 9:  # Changed from 8 to 9
                if hasattr(self, 'gstar_results'):
                    self.calculate_swh_license()
                else:
                    print("Please calculate GSTAR controllers first!")
                    input("Press Enter to continue...")
            elif choice == 10:  # Changed from 9 to 10
                self.export_menu()
            elif choice == 11:  # Changed from 10 to 11
                self.dc_lines.clear()
                print("All DC line data cleared!")
                input("Press Enter to continue...")
            elif choice == 12:  # Changed from 11 to 12
                print("\nThank you for using Access Control System Calculator!")
                break
            else:
                print("Invalid choice!")
                input("Press Enter to continue...")
    
    def calculate_license_menu(self):
        """Menu for calculating license requirements"""
        self.clear_screen()
        self.print_header("CALCULATE LICENSE REQUIREMENTS")
        
        print("LICENSE RULES:")
        print("-" * 40)
        print("1. NON-REDUNDANT SYSTEMS:")
        print("   • ≤ 32 controllers → Kantech Special License")
        print("   • > 32 controllers → Kantech Corporate License")
        print()
        print("2. REDUNDANT SYSTEMS:")
        print("   • Migrate to Global License (replaces Special/Corporate)")
        print("   • Add Gateway License (for server communication)")
        print("   • Add Redundancy License (for failover capability)")
        print()
        
        # Ask about redundancy
        print("Do you need redundancy configuration?")
        print("(Redundancy provides backup/failover capability)")
        print()
        print("1. Yes, I need redundancy (Global + Gateway + Redundancy licenses)")
        print("2. No, redundancy not needed (Special or Corporate license only)")
        print()
        
        try:
            redundancy_choice = int(input("Select option (1-2): "))
            use_redundancy = (redundancy_choice == 1)
            
            # Calculate license requirements
            self.calculate_license_requirements(use_redundancy)
            
        except ValueError:
            print("Invalid input! Please enter 1 or 2.")
            input("Press Enter to continue...")


def main():
    """Run the calculator"""
    print("Loading Access Control System Calculator...")
    print()
    print("TWO CALCULATION MODES AVAILABLE:")
    print("1. KANTECH SYSTEM:")
    print("   - Multiple controllers per DC line")
    print("   - Controllers based on readers only")
    print("   - Various expansion modules")
    print("   - License: Special/Corporate/Global")
    print()
    print("2. GSTAR/SWH SYSTEM (Kantech-style):")
    print("   - One controller per DC line (based on readers only)")
    print("   - AS0073-000 for input expansion (8 inputs, $333)")
    print("   - AS0074-000 for output expansion (8 outputs, $395)")
    print("   - License based on total readers (CC9000 series)")
    print()
    print("NEW FEATURES:")
    print("• Calculate specific DC line for SWH system")
    print("• Detailed view for last DC line in calculations")
    print()
    input("Press Enter to start...")
    
    calculator = KantechDCCalculator()
    calculator.main_menu()


if __name__ == "__main__":
    main()