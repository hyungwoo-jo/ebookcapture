
import time
import json
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pynput import mouse, keyboard
import pyautogui

# --- Core Macro Logic ---

class MacroManager:
    def __init__(self):
        self.recorded_events = []
        self.last_time = None
        self.is_recording = False
        self.is_replaying = False
        self.mouse_listener = None
        self.keyboard_listener = None
        self.replay_thread = None
        self.record_thread = None

    def record_event(self, event_type, **kwargs):
        if not self.is_recording:
            return
        current_time = time.time()
        delay = 0
        if self.last_time is not None:
            delay = current_time - self.last_time
        
        event_data = {'action': event_type, 'details': kwargs, 'delay': delay}
        self.recorded_events.append(event_data)
        print(f"Recorded: {event_data}")
        self.last_time = current_time

    def on_move(self, x, y):
        self.record_event('mouse_move', x=x, y=y)

    def on_click(self, x, y, button, pressed):
        action = 'mouse_press' if pressed else 'mouse_release'
        self.record_event(action, x=x, y=y, button=str(button))

    def on_scroll(self, x, y, dx, dy):
        self.record_event('mouse_scroll', x=x, y=y, dx=dx, dy=dy)

    def on_press(self, key):
        if key == keyboard.Key.esc:
            self.stop_recording()
            return False
        try:
            self.record_event('key_press', key=key.char)
        except AttributeError:
            self.record_event('key_press', key=str(key))

    def on_release(self, key):
        try:
            self.record_event('key_release', key=key.char)
        except AttributeError:
            self.record_event('key_release', key=str(key))

    def start_recording(self, status_callback):
        if self.is_recording:
            return
        self.is_recording = True
        self.recorded_events = []
        self.last_time = time.time()
        
        self.mouse_listener = mouse.Listener(on_move=self.on_move, on_click=self.on_click, on_scroll=self.on_scroll)
        self.keyboard_listener = keyboard.Listener(on_press=self.on_press, on_release=self.on_release)

        self.mouse_listener.start()
        self.keyboard_listener.start()
        status_callback("Recording... Press 'Esc' to stop.")
        
        self.record_thread = self.keyboard_listener

    def stop_recording(self, status_callback=None):
        if not self.is_recording:
            return
        if self.mouse_listener:
            self.mouse_listener.stop()
        if self.keyboard_listener:
            self.keyboard_listener.stop()
        self.is_recording = False
        if status_callback:
            status_callback("Recording stopped.")
        print("Recording stopped.")

    def replay_macro(self, events, repetitions, interval, status_callback, done_callback):
        self.is_replaying = True
        pyautogui.FAILSAFE = True

        def task():
            for i in range(repetitions):
                if not self.is_replaying:
                    break
                status_callback(f"Replaying... Repetition {i+1}/{repetitions}")
                for event in events:
                    if not self.is_replaying:
                        break
                    time.sleep(event['delay'])
                    action = event['action']
                    details = event['details']
                    try:
                        if action == 'mouse_move':
                            pyautogui.moveTo(details['x'], details['y'], duration=0.1)
                        elif action == 'mouse_press':
                            btn = str(details['button']).replace('Button.', '')
                            pyautogui.mouseDown(details['x'], details['y'], button=btn)
                        elif action == 'mouse_release':
                            btn = str(details['button']).replace('Button.', '')
                            pyautogui.mouseUp(details['x'], details['y'], button=btn)
                        elif action == 'mouse_scroll':
                            pyautogui.scroll(int(details['dy'] * 100), x=details['x'], y=details['y'])
                        elif action == 'key_press':
                            pyautogui.keyDown(str(details['key']).replace("Key.", ""))
                        elif action == 'key_release':
                            pyautogui.keyUp(str(details['key']).replace("Key.", ""))
                    except Exception as e:
                        print(f"Error replaying event {event}: {e}")
            self.is_replaying = False
            done_callback()

        self.replay_thread = threading.Thread(target=task)
        self.replay_thread.start()

    def stop_replaying(self):
        if not self.is_replaying:
            return
        self.is_replaying = False

    def save_macro(self, filepath):
        with open(filepath, 'w') as f:
            json.dump(self.recorded_events, f, indent=4)
        print(f"Macro saved to {filepath}")

    def load_macro(self, filepath):
        try:
            with open(filepath, 'r') as f:
                self.recorded_events = json.load(f)
            print(f"Macro loaded from {filepath}")
            return self.recorded_events
        except FileNotFoundError:
            print(f"Error: Macro file '{filepath}' not found.")
            return None
        except json.JSONDecodeError:
            print(f"Error: Could not decode JSON from {filepath}.")
            return None

# --- GUI Application ---

class MacroApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Macro Recorder")
        self.root.geometry("400x280")
        self.macro_manager = MacroManager()
        self.hotkey_listener = None
        self.create_widgets()
        self.setup_hotkeys()
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def create_widgets(self):
        self.root.columnconfigure(0, weight=1)
        self.root.columnconfigure(1, weight=1)

        # --- Controls Frame ---
        controls_frame = ttk.LabelFrame(self.root, text="Controls")
        controls_frame.grid(row=0, column=0, columnspan=2, padx=10, pady=10, sticky="ew")
        controls_frame.columnconfigure(0, weight=1)
        controls_frame.columnconfigure(1, weight=1)
        controls_frame.columnconfigure(2, weight=1)

        self.record_btn = ttk.Button(controls_frame, text="Record (F9)", command=self.start_recording)
        self.record_btn.grid(row=0, column=0, padx=5, pady=5, sticky="ew")

        self.stop_btn = ttk.Button(controls_frame, text="Stop (Esc)", command=self.stop_recording, state=tk.DISABLED)
        self.stop_btn.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        self.replay_btn = ttk.Button(controls_frame, text="Replay", command=self.start_replaying)
        self.replay_btn.grid(row=0, column=2, padx=5, pady=5, sticky="ew")

        # --- Replay Options Frame ---
        replay_options_frame = ttk.LabelFrame(self.root, text="Replay Options")
        replay_options_frame.grid(row=1, column=0, columnspan=2, padx=10, pady=5, sticky="ew")
        replay_options_frame.columnconfigure(1, weight=1)

        ttk.Label(replay_options_frame, text="Repetitions:").grid(row=0, column=0, padx=5, pady=2, sticky="w")
        self.repetitions_var = tk.StringVar(value="1")
        self.repetitions_entry = ttk.Entry(replay_options_frame, textvariable=self.repetitions_var, width=10)
        self.repetitions_entry.grid(row=0, column=1, padx=5, pady=2, sticky="ew")

        ttk.Label(replay_options_frame, text="Interval (s):").grid(row=1, column=0, padx=5, pady=2, sticky="w")
        self.interval_var = tk.StringVar(value="1.0")
        self.interval_entry = ttk.Entry(replay_options_frame, textvariable=self.interval_var, width=10)
        self.interval_entry.grid(row=1, column=1, padx=5, pady=2, sticky="ew")
        
        # --- File Frame ---
        file_frame = ttk.LabelFrame(self.root, text="File")
        file_frame.grid(row=2, column=0, columnspan=2, padx=10, pady=5, sticky="ew")
        file_frame.columnconfigure(0, weight=1)
        file_frame.columnconfigure(1, weight=1)

        self.load_btn = ttk.Button(file_frame, text="Load Macro", command=self.load_macro)
        self.load_btn.grid(row=0, column=0, padx=5, pady=5, sticky="ew")

        self.save_btn = ttk.Button(file_frame, text="Save Macro", command=self.save_macro)
        self.save_btn.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        # --- Status Bar ---
        self.status_var = tk.StringVar(value="Idle. Press F9 to start recording.")
        self.status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor="w")
        self.status_bar.grid(row=3, column=0, columnspan=2, sticky="ew")

    def setup_hotkeys(self):
        hotkeys = {
            '<f9>': self.on_hotkey_start
        }
        self.hotkey_listener = keyboard.GlobalHotKeys(hotkeys)
        self.hotkey_listener.start()

    def on_hotkey_start(self):
        # This is called from a non-GUI thread, so we use after_idle
        self.root.after_idle(self.start_recording)

    def on_closing(self):
        if self.hotkey_listener and self.hotkey_listener.is_alive():
            self.hotkey_listener.stop()
        self.root.destroy()

    def update_status(self, message):
        self.status_var.set(message)
        self.root.update_idletasks()

    def start_recording(self):
        # This check prevents starting a new recording if one is already active
        if self.macro_manager.is_recording:
            return
            
        self.record_btn.config(state=tk.DISABLED)
        self.replay_btn.config(state=tk.DISABLED)
        self.load_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.macro_manager.start_recording(self.update_status)
        self.root.after(100, self.check_recording_status)

    def check_recording_status(self):
        if not self.macro_manager.is_recording:
            self.record_btn.config(state=tk.NORMAL)
            self.replay_btn.config(state=tk.NORMAL)
            self.load_btn.config(state=tk.NORMAL)
            self.stop_btn.config(state=tk.DISABLED)
            self.update_status("Idle. Press F9 to start recording.")
        else:
            self.root.after(100, self.check_recording_status)

    def stop_recording(self):
        self.macro_manager.stop_recording(self.update_status)

    def start_replaying(self):
        if not self.macro_manager.recorded_events:
            messagebox.showwarning("No Macro", "No macro recorded or loaded to replay.")
            return
        try:
            repetitions = int(self.repetitions_var.get())
            interval = float(self.interval_var.get())
        except ValueError:
            messagebox.showerror("Invalid Input", "Repetitions and interval must be numbers.")
            return

        self.replay_btn.config(text="Stop Replay", command=self.stop_replaying)
        self.record_btn.config(state=tk.DISABLED)
        self.load_btn.config(state=tk.DISABLED)
        self.save_btn.config(state=tk.DISABLED)

        self.macro_manager.replay_macro(
            self.macro_manager.recorded_events, 
            repetitions, 
            interval, 
            self.update_status,
            self.on_replay_done
        )

    def stop_replaying(self):
        self.macro_manager.stop_replaying()

    def on_replay_done(self):
        self.update_status("Replay finished.")
        self.replay_btn.config(text="Replay", command=self.start_replaying)
        self.record_btn.config(state=tk.NORMAL)
        self.load_btn.config(state=tk.NORMAL)
        self.save_btn.config(state=tk.NORMAL)
        self.update_status("Idle. Press F9 to start recording.")

    def load_macro(self):
        filepath = filedialog.askopenfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            title="Load Macro"
        )
        if filepath:
            if self.macro_manager.load_macro(filepath):
                self.update_status(f"Macro loaded from {filepath.split('/')[-1]}")
            else:
                messagebox.showerror("Load Error", f"Failed to load macro from {filepath}.")

    def save_macro(self):
        if not self.macro_manager.recorded_events:
            messagebox.showwarning("No Macro", "No macro recorded to save.")
            return
        filepath = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            title="Save Macro"
        )
        if filepath:
            self.macro_manager.save_macro(filepath)
            self.update_status(f"Macro saved to {filepath.split('/')[-1]}")

def main():
    root = tk.Tk()
    app = MacroApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
