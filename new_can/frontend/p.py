import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import json
import os
import threading
import queue
import time
import random
import cantools
from datetime import datetime
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='can_app.log'
)
logger = logging.getLogger(__name__)

class OfflineCANSimulator:
    """Simulates CAN bus activity without actual CAN hardware"""
    
    def __init__(self, db_path=None):
        self.db = None
        self.running = False
        self.message_queue = queue.Queue()
        self.simulation_thread = None
        self.db_path = db_path
        self.messages = {}
        self.load_db(db_path)
        
    def load_db(self, db_path):
        """Load a DBC file"""
        if not db_path or not os.path.exists(db_path):
            logger.warning(f"DBC file not found: {db_path}")
            return False
        
        try:
            self.db = cantools.database.load_file(db_path)
            self.messages = {msg.frame_id: msg for msg in self.db.messages}
            logger.info(f"Loaded DBC file: {db_path} with {len(self.messages)} messages")
            return True
        except Exception as e:
            logger.error(f"Error loading DBC file: {e}")
            return False
            
    def start_simulation(self, frequency=10):
        """Start simulating CAN messages"""
        if self.running or not self.db:
            return False
            
        self.running = True
        self.simulation_thread = threading.Thread(
            target=self._simulation_loop,
            args=(frequency,),
            daemon=True
        )
        self.simulation_thread.start()
        logger.info(f"Started CAN simulation at {frequency}Hz")
        return True
        
    def stop_simulation(self):
        """Stop simulating CAN messages"""
        self.running = False
        if self.simulation_thread:
            self.simulation_thread.join(timeout=1.0)
            self.simulation_thread = None
        logger.info("Stopped CAN simulation")
        
    def _simulation_loop(self, frequency):
        """Generate simulated CAN messages"""
        sleep_time = 1.0 / frequency
        
        while self.running:
            # Choose a random message to simulate
            if not self.messages:
                time.sleep(sleep_time)
                continue
                
            frame_id = random.choice(list(self.messages.keys()))
            msg = self.messages[frame_id]
            
            # Generate random values for signals
            data = {}
            for signal in msg.signals:
                # Generate a value within the signal's range
                min_val = 0
                # Calculate max value based on signal length (accounting for signed values)
                if signal.is_signed:
                    max_val = 2 ** (signal.length - 1) - 1
                else:
                    max_val = 2 ** signal.length - 1
                    
                # For simulation, use values that change slowly over time
                # This is more realistic than completely random values
                range_size = max_val - min_val
                base_value = min_val + (range_size / 2)  # Middle of the range
                variation = range_size * 0.1  # 10% variation
                
                # Sine wave variation based on current time
                time_factor = time.time() * 0.1  # Slow change
                variation_factor = (math.sin(time_factor + hash(signal.name) % 10) + 1) / 2  # 0 to 1
                
                value = int(base_value + (variation * variation_factor))
                data[signal.name] = value
            
            try:
                # Encode the message
                encoded_data = msg.encode(data)
                
                # Create a simulated message
                message = {
                    "timestamp": str(datetime.now()),
                    "name": msg.name,
                    "sender": msg.senders[0] if msg.senders else "Unknown",
                    "arbitration_id": hex(msg.frame_id),
                    "dlc": len(encoded_data),
                    "hex": encoded_data.hex(),
                    "bin_data": ''.join(format(byte, '08b') for byte in encoded_data),
                    "dec": int.from_bytes(encoded_data, byteorder='big', signed=False),
                    "decoded_data": data
                }
                
                # Add to queue
                self.message_queue.put(message)
                
            except Exception as e:
                logger.error(f"Error simulating message {msg.name}: {e}")
            
            time.sleep(sleep_time)
    
    def get_messages(self):
        """Get all queued messages and clear the queue"""
        messages = []
        while not self.message_queue.empty():
            messages.append(self.message_queue.get())
        return messages
        
    def send_message(self, frame_id, signals):
        """Simulate sending a CAN message"""
        if not self.db or frame_id not in self.messages:
            logger.error(f"Unknown frame_id: {frame_id}")
            return False
            
        msg = self.messages[frame_id]
        
        try:
            # Validate signals
            for signal in msg.signals:
                if signal.name not in signals:
                    logger.error(f"Missing signal: {signal.name}")
                    return False
                    
                value = signals[signal.name]
                # Validate signal value against limits
                if signal.is_signed:
                    min_val = -(2 ** (signal.length - 1))
                    max_val = 2 ** (signal.length - 1) - 1
                else:
                    min_val = 0
                    max_val = 2 ** signal.length - 1
                    
                if value < min_val or value > max_val:
                    logger.error(f"Signal value out of range: {signal.name} = {value} (range: {min_val} to {max_val})")
                    return False
            
            # Encode the message
            encoded_data = msg.encode(signals)
            
            # Create a simulated message (as if we received it)
            message = {
                "timestamp": str(datetime.now()),
                "name": msg.name,
                "sender": msg.senders[0] if msg.senders else "Unknown",
                "arbitration_id": hex(msg.frame_id),
                "dlc": len(encoded_data),
                "hex": encoded_data.hex(),
                "bin_data": ''.join(format(byte, '08b') for byte in encoded_data),
                "dec": int.from_bytes(encoded_data, byteorder='big', signed=False),
                "decoded_data": signals
            }
            
            # Add to queue as if we received it
            self.message_queue.put(message)
            logger.info(f"Sent message: {msg.name} with {len(signals)} signals")
            return True
            
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            return False

class DbcFileManager:
    """Manages DBC files locally"""
    
    def __init__(self, base_dir="dbc_files"):
        self.base_dir = base_dir
        self._ensure_dir_exists()
        
    def _ensure_dir_exists(self):
        """Ensure the DBC files directory exists"""
        if not os.path.exists(self.base_dir):
            os.makedirs(self.base_dir)
            
    def get_dbc_files(self):
        """Get list of available DBC files"""
        self._ensure_dir_exists()
        return [f for f in os.listdir(self.base_dir) if f.endswith('.dbc')]
        
    def add_dbc_file(self, file_path):
        """Add a DBC file to the collection"""
        if not os.path.exists(file_path):
            return False
            
        try:
            # Validate it's a proper DBC file by loading it
            db = cantools.database.load_file(file_path)
            
            # Copy to our directory
            filename = os.path.basename(file_path)
            dest_path = os.path.join(self.base_dir, filename)
            
            with open(file_path, 'rb') as src, open(dest_path, 'wb') as dest:
                dest.write(src.read())
                
            return True
        except Exception as e:
            logger.error(f"Error adding DBC file: {e}")
            return False
            
    def get_dbc_path(self, filename):
        """Get the full path to a DBC file"""
        path = os.path.join(self.base_dir, filename)
        if os.path.exists(path):
            return path
        return None
        
    def get_can_messages(self, filename):
        """Get CAN messages defined in a DBC file"""
        path = self.get_dbc_path(filename)
        if not path:
            return {}
            
        try:
            db = cantools.database.load_file(path)
            can_message_dict = {}
            
            for msg in db.messages:
                can_message_dict[msg.frame_id] = {
                    "name": msg.name,
                    "signals": {}
                }
                
                for sig in msg.signals:
                    can_message_dict[msg.frame_id]["signals"][sig.name] = {
                        "length": sig.length,
                        "is_signed": sig.is_signed,
                        "min": sig.minimum if sig.minimum is not None else 0,
                        "max": sig.maximum if sig.maximum is not None else (2**sig.length - 1)
                    }
                    
            return can_message_dict
        except Exception as e:
            logger.error(f"Error getting CAN messages: {e}")
            return {}

class SettingsManager:
    """Manages application settings"""
    
    def __init__(self, settings_file="app_settings.json"):
        self.settings_file = settings_file
        self.settings = self._load_settings()
        
    def _load_settings(self):
        """Load settings from file"""
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading settings: {e}")
                
        # Default settings
        return {
            "simulation_frequency": 10,
            "recent_dbc_files": [],
            "selected_dbc_file": None,
            "window_size": {
                "width": 1024,
                "height": 768
            }
        }
        
    def save_settings(self):
        """Save settings to file"""
        try:
            with open(self.settings_file, 'w') as f:
                json.dump(self.settings, f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Error saving settings: {e}")
            return False
            
    def get_setting(self, key, default=None):
        """Get a setting value"""
        return self.settings.get(key, default)
        
    def set_setting(self, key, value):
        """Set a setting value"""
        self.settings[key] = value
        return self.save_settings()
        
    def add_recent_dbc_file(self, file_path):
        """Add a DBC file to recent files list"""
        recent = self.settings.get("recent_dbc_files", [])
        if file_path in recent:
            recent.remove(file_path)
        recent.insert(0, file_path)
        # Keep only the 5 most recent
        self.settings["recent_dbc_files"] = recent[:5]
        return self.save_settings()

class CANApp:
    """Main application class"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("Offline CAN Bus Monitor")
        self.root.geometry("1024x768")
        
        # Initialize components
        self.settings_manager = SettingsManager()
        self.dbc_manager = DbcFileManager()
        self.simulator = OfflineCANSimulator()
        
        # Load last used DBC file if available
        last_dbc = self.settings_manager.get_setting("selected_dbc_file")
        if last_dbc:
            dbc_path = self.dbc_manager.get_dbc_path(last_dbc)
            if dbc_path:
                self.simulator.load_db(dbc_path)
        
        # Setup UI
        self._create_menu()
        self._create_layout()
        
        # Start the UI update timer
        self.update_timer_id = None
        self._schedule_ui_update()
        
        # Apply window size from settings
        window_size = self.settings_manager.get_setting("window_size", {"width": 1024, "height": 768})
        self.root.geometry(f"{window_size['width']}x{window_size['height']}")
        
        # Track window resize
        self.root.bind("<Configure>", self._on_window_resize)
        
    def _on_window_resize(self, event):
        """Handle window resize event"""
        # Only update if it's the main window and not a child widget
        if event.widget == self.root:
            # Avoid excessive writes by debouncing
            if hasattr(self, "_resize_timer"):
                self.root.after_cancel(self._resize_timer)
                
            self._resize_timer = self.root.after(500, lambda: self._save_window_size(event.width, event.height))
    
    def _save_window_size(self, width, height):
        """Save window size to settings"""
        self.settings_manager.set_setting("window_size", {"width": width, "height": height})
        
    def _create_menu(self):
        """Create the application menu"""
        menubar = tk.Menu(self.root)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Open DBC File", command=self._open_dbc_file)
        
        # Recent files submenu
        self.recent_menu = tk.Menu(file_menu, tearoff=0)
        file_menu.add_cascade(label="Recent Files", menu=self.recent_menu)
        self._update_recent_files_menu()
        
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        menubar.add_cascade(label="File", menu=file_menu)
        
        # Simulation menu
        sim_menu = tk.Menu(menubar, tearoff=0)
        sim_menu.add_command(label="Start Simulation", command=self._start_simulation)
        sim_menu.add_command(label="Stop Simulation", command=self._stop_simulation)
        sim_menu.add_separator()
        sim_menu.add_command(label="Send Custom Message", command=self._show_send_dialog)
        menubar.add_cascade(label="Simulation", menu=sim_menu)
        
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="About", command=self._show_about)
        menubar.add_cascade(label="Help", menu=help_menu)
        
        self.root.config(menu=menubar)
        
    def _update_recent_files_menu(self):
        """Update the recent files menu"""
        # Clear existing items
        self.recent_menu.delete(0, tk.END)
        
        # Add recent files
        recent_files = self.settings_manager.get_setting("recent_dbc_files", [])
        if not recent_files:
            self.recent_menu.add_command(label="No recent files", state=tk.DISABLED)
        else:
            for file_path in recent_files:
                filename = os.path.basename(file_path)
                self.recent_menu.add_command(
                    label=filename,
                    command=lambda path=file_path: self._open_recent_file(path)
                )
                
    def _open_recent_file(self, file_path):
        """Open a recent DBC file"""
        if os.path.exists(file_path):
            self._load_dbc_file(file_path)
        else:
            messagebox.showerror("File Not Found", f"The file {file_path} no longer exists.")
            # Remove from recent files
            recent = self.settings_manager.get_setting("recent_dbc_files", [])
            if file_path in recent:
                recent.remove(file_path)
                self.settings_manager.set_setting("recent_dbc_files", recent)
                self._update_recent_files_menu()
                
    def _create_layout(self):
        """Create the main UI layout"""
        # Create main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Top info frame
        info_frame = ttk.LabelFrame(main_frame, text="CAN Information", padding="5")
        info_frame.pack(fill=tk.X, pady=(0, 10))
        
        # DBC file info
        self.dbc_label = ttk.Label(info_frame, text="No DBC file loaded")
        self.dbc_label.pack(side=tk.LEFT, padx=5)
        
        # Simulation status
        self.sim_status_label = ttk.Label(info_frame, text="Simulation: Stopped")
        self.sim_status_label.pack(side=tk.RIGHT, padx=5)
        
        # Message counter
        self.msg_counter_label = ttk.Label(info_frame, text="Messages: 0")
        self.msg_counter_label.pack(side=tk.RIGHT, padx=5)
        
        # Create notebook for different views
        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill=tk.BOTH, expand=True)
        
        # Messages tab
        messages_frame = ttk.Frame(notebook, padding="5")
        notebook.add(messages_frame, text="Messages")
        
        # Create messages table
        columns = ("Time", "ID", "Name", "Data (Hex)", "DLC")
        self.messages_tree = ttk.Treeview(messages_frame, columns=columns, show="headings")
        
        # Configure columns
        for col in columns:
            self.messages_tree.heading(col, text=col)
            
        self.messages_tree.column("Time", width=150)
        self.messages_tree.column("ID", width=80)
        self.messages_tree.column("Name", width=150)
        self.messages_tree.column("Data (Hex)", width=250)
        self.messages_tree.column("DLC", width=50)
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(messages_frame, orient=tk.VERTICAL, command=self.messages_tree.yview)
        self.messages_tree.configure(yscrollcommand=scrollbar.set)
        
        # Pack widgets
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.messages_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Add detail view when a message is selected
        self.messages_tree.bind("<<TreeviewSelect>>", self._on_message_select)
        
        # Signals tab
        signals_frame = ttk.Frame(notebook, padding="5")
        notebook.add(signals_frame, text="Signals")
        
        # Create signals table
        signal_columns = ("Message", "Signal", "Value", "Min", "Max", "Units")
        self.signals_tree = ttk.Treeview(signals_frame, columns=signal_columns, show="headings")
        
        # Configure columns
        for col in signal_columns:
            self.signals_tree.heading(col, text=col)
            
        # Add scrollbar
        signal_scrollbar = ttk.Scrollbar(signals_frame, orient=tk.VERTICAL, command=self.signals_tree.yview)
        self.signals_tree.configure(yscrollcommand=signal_scrollbar.set)
        
        # Pack widgets
        signal_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.signals_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Status bar
        self.status_bar = ttk.Label(main_frame, text="Ready", relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Instance variables for tracking
        self.message_count = 0
        self.signal_values = {}  # Track latest signal values
        self.message_details_window = None  # Details popup
        
    def _schedule_ui_update(self):
        """Schedule periodic UI updates"""
        self._update_ui()
        self.update_timer_id = self.root.after(100, self._schedule_ui_update)  # Update 10 times per second
        
    def _update_ui(self):
        """Update UI with new messages"""
        # Get new messages
        new_messages = self.simulator.get_messages()
        if not new_messages:
            return
            
        # Update message count
        self.message_count += len(new_messages)
        self.msg_counter_label.config(text=f"Messages: {self.message_count}")
        
        # Update messages table
        for msg in new_messages:
            # Format timestamp
            timestamp = msg["timestamp"].split(".")[0]  # Remove microseconds
            
            # Insert into tree
            item_id = self.messages_tree.insert(
                "",
                0,  # Insert at the top
                values=(
                    timestamp,
                    msg["arbitration_id"],
                    msg["name"],
                    msg["hex"],
                    msg["dlc"]
                )
            )
            
            # Store the full message data in the item
            self.messages_tree.item(item_id, tags=(json.dumps(msg),))
            
            # Limit the number of messages shown (keep 1000 most recent)
            if self.messages_tree.get_children():
                children = self.messages_tree.get_children()
                if len(children) > 1000:
                    self.messages_tree.delete(children[-1])
                    
            # Update signal values
            if "decoded_data" in msg:
                msg_name = msg["name"]
                for signal_name, value in msg["decoded_data"].items():
                    key = f"{msg_name}.{signal_name}"
                    self.signal_values[key] = value
                    
        # Update signals view if needed
        self._update_signals_view()
        
        # Update details window if open
        if self.message_details_window and hasattr(self, "current_message_id"):
            self._refresh_message_details()
            
    def _update_signals_view(self):
        """Update the signals view with latest values"""
        # Clear existing items
        for item in self.signals_tree.get_children():
            self.signals_tree.delete(item)
            
        # Add current signals
        for key, value in self.signal_values.items():
            msg_name, signal_name = key.split(".", 1)
            
            # Get signal info if available
            min_val = "?"
            max_val = "?"
            units = ""
            
            # Find the message and signal in the DB
            if self.simulator.db:
                for msg in self.simulator.db.messages:
                    if msg.name == msg_name:
                        for sig in msg.signals:
                            if sig.name == signal_name:
                                min_val = sig.minimum if sig.minimum is not None else "0"
                                max_val = sig.maximum if sig.maximum is not None else str(2 ** sig.length - 1)
                                units = sig.unit or ""
                                break
                        break
            
            # Insert into tree
            self.signals_tree.insert(
                "",
                tk.END,
                values=(msg_name, signal_name, value, min_val, max_val, units)
            )
            
    def _on_message_select(self, event):
        """Handle message selection in the tree"""
        selection = self.messages_tree.selection()
        if not selection:
            return
            
        # Get the selected item
        item_id = selection[0]
        tags = self.messages_tree.item(item_id, "tags")
        if not tags:
            return
            
        # Parse the message data
        try:
            msg_json = tags[0]
            msg = json.loads(msg_json)
            self._show_message_details(msg)
        except Exception as e:
            logger.error(f"Error showing message details: {e}")
            
    def _show_message_details(self, msg):
        """Show detailed message information"""
        if self.message_details_window:
            self.message_details_window.destroy()
            
        # Create a new window
        self.message_details_window = tk.Toplevel(self.root)
        self.message_details_window.title(f"Message Details: {msg['name']}")
        self.message_details_window.geometry("600x400")
        self.message_details_window.transient(self.root)
        
        # Store current message ID for updates
        self.current_message_id = msg["arbitration_id"]
        
        # Create frames
        main_frame = ttk.Frame(self.message_details_window, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Message info
        info_frame = ttk.LabelFrame(main_frame, text="Message Information", padding="5")
        info_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Create grid of labels
        ttk.Label(info_frame, text="Name:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        ttk.Label(info_frame, text=msg["name"]).grid(row=0, column=1, sticky=tk.W, padx=5, pady=2)
        
        ttk.Label(info_frame, text="ID:").grid(row=0, column=2, sticky=tk.W, padx=5, pady=2)
        ttk.Label(info_frame, text=msg["arbitration_id"]).grid(row=0, column=3, sticky=tk.W, padx=5, pady=2)
        
        ttk.Label(info_frame, text="Timestamp:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        ttk.Label(info_frame, text=msg["timestamp"]).grid(row=1, column=1, sticky=tk.W, padx=5, pady=2)
        
        ttk.Label(info_frame, text="Sender:").grid(row=1, column=2, sticky=tk.W, padx=5, pady=2)
        ttk.Label(info_frame, text=msg["sender"]).grid(row=1, column=3, sticky=tk.W, padx=5, pady=2)
        
        ttk.Label(info_frame, text="Data (Hex):").grid(row=2, column=0, sticky=tk.W, padx=5, pady=2)
        ttk.Label(info_frame, text=msg["hex"]).grid(row=2, column=1, columnspan=3, sticky=tk.W, padx=5, pady=2)
        
        # Decoded data
        if "decoded_data" in msg and msg["decoded_data"]:
            decoded_frame = ttk.LabelFrame(main_frame, text="Decoded Signals", padding="5")
            decoded_frame.pack(fill=tk.BOTH, expand=True)
            
            # Create signals tree
            columns = ("Signal", "Value", "Raw")
            signals_tree = ttk.Treeview(decoded_frame, columns=columns, show="headings")
            
            # Configure columns
            for col in columns:
                signals_tree.heading(col, text=col)
                
            signals_tree.column("Signal", width=200)
            signals_tree.column("Value", width=100)
            signals_tree.column("Raw", width=100)
            
            # Add scrollbar
            scrollbar = ttk.Scrollbar(decoded_frame, orient=tk.VERTICAL, command=signals_tree.yview)
            signals_tree.configure(yscrollcommand=scrollbar.set)
            
            # Pack widgets
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            signals_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            
            # Add signals
            for signal_name, value in msg["decoded_data"].items():
                signals_tree.insert("", tk.END, values=(signal_name, value, f"0x{value:X}" if isinstance(value, int) else value))
                
        # Store signals tree for updates
        self.details_signals_tree = signals_tree if "decoded_data" in msg else None
        
    def _refresh_message_details(self):
        """Refresh message details window with latest data"""
        if not self.message_details_window or not hasattr(self, "current_message_id") or not self.details_signals_tree:
            return
            
        # Find latest message with this ID
        latest_msg = None
        for item_id in self.messages_tree.get_children()[:100]:  # Check recent messages
            tags = self.messages_tree.item(item_id, "tags")
            if tags:
                try:
                    msg = json.loads(tags[0])
                    if msg["arbitration_id"] == self.current_message_id:
                        latest_msg = msg
                        break
                except:
                    pass
                    
        if not latest_msg or "decoded_data" not in latest_msg:
            return
            
        # Update signals tree
        for item in self.details_signals_tree.get_children():
            self.details_signals_tree.delete(item)
            
        for signal_name, value in latest_msg["decoded_data"].items():
            self.details_signals_tree.insert(
                "",
                tk.END,
                values=(
                    signal_name,
                    value,
                    f"0x{value:X}" if isinstance(value, int) else value
                )
            )
            
    def _open_dbc_file(self):
        """Open a DBC file dialog"""
        file_path = filedialog.askopenfilename(
            title="Open DBC File",
            filetypes=[("DBC Files", "*.dbc"), ("All Files", "*.*")]
        )
        
        if file_path:
            self._load_dbc_file(file_path)
            
    def _load_dbc_file(self, file_path):
        """Load a DBC file and update the application"""
        # Add to recent files
        self.settings_manager.add_recent_file(file_path