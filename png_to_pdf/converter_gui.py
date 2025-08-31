
import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image
import threading

class PngToPdfConverterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("PNG to PDF Converter")
        self.root.geometry("500x300")

        self.input_folder = tk.StringVar()
        self.sort_order = tk.StringVar(value="name")
        self.is_converting = False

        self.create_widgets()

    def create_widgets(self):
        self.root.columnconfigure(0, weight=1)

        # --- Input Frame ---
        input_frame = ttk.LabelFrame(self.root, text="Input Folder")
        input_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        input_frame.columnconfigure(0, weight=1)
        input_frame.columnconfigure(1, weight=0)

        self.folder_entry = ttk.Entry(input_frame, textvariable=self.input_folder, state="readonly")
        self.folder_entry.grid(row=0, column=0, padx=5, pady=5, sticky="ew")

        self.browse_btn = ttk.Button(input_frame, text="Browse...", command=self.select_folder)
        self.browse_btn.grid(row=0, column=1, padx=5, pady=5)

        # --- Options Frame ---
        options_frame = ttk.LabelFrame(self.root, text="Options")
        options_frame.grid(row=1, column=0, padx=10, pady=5, sticky="ew")

        ttk.Label(options_frame, text="Sort by:").pack(side=tk.LEFT, padx=5, pady=5)
        
        name_radio = ttk.Radiobutton(options_frame, text="File Name", variable=self.sort_order, value="name")
        name_radio.pack(side=tk.LEFT, padx=5)
        
        date_radio = ttk.Radiobutton(options_frame, text="Modified Date", variable=self.sort_order, value="date")
        date_radio.pack(side=tk.LEFT, padx=5)

        # --- Action Frame ---
        action_frame = ttk.Frame(self.root)
        action_frame.grid(row=2, column=0, padx=10, pady=10, sticky="ew")
        action_frame.columnconfigure(0, weight=1)

        self.convert_btn = ttk.Button(action_frame, text="Convert to PDF", command=self.start_conversion)
        self.convert_btn.grid(row=0, column=0, padx=5, pady=5, sticky="ew")

        # --- Progress & Status ---
        status_frame = ttk.LabelFrame(self.root, text="Status")
        status_frame.grid(row=3, column=0, padx=10, pady=5, sticky="ew")
        status_frame.columnconfigure(0, weight=1)

        self.progress_bar = ttk.Progressbar(status_frame, orient="horizontal", mode="determinate")
        self.progress_bar.grid(row=0, column=0, padx=5, pady=5, sticky="ew")

        self.status_label = ttk.Label(status_frame, text="Select a folder to begin.")
        self.status_label.grid(row=1, column=0, padx=5, pady=5, sticky="w")

    def select_folder(self):
        folder_path = filedialog.askdirectory(title="Select Folder with PNG images")
        if folder_path:
            self.input_folder.set(folder_path)
            self.status_label.config(text=f"{len(self.get_png_files())} PNG files found.")

    def get_png_files(self):
        folder = self.input_folder.get()
        if not folder:
            return []
        return [os.path.join(folder, f) for f in os.listdir(folder) if f.lower().endswith('.png')]

    def start_conversion(self):
        if self.is_converting:
            return

        if not self.input_folder.get():
            messagebox.showerror("Error", "Please select an input folder first.")
            return

        png_files = self.get_png_files()
        if not png_files:
            messagebox.showwarning("Warning", "No PNG files found in the selected folder.")
            return

        output_pdf_path = filedialog.asksaveasfilename(
            title="Save PDF As...",
            defaultextension=".pdf",
            filetypes=[("PDF Documents", "*.pdf")]
        )

        if not output_pdf_path:
            return

        self.is_converting = True
        self.convert_btn.config(state=tk.DISABLED)
        self.browse_btn.config(state=tk.DISABLED)
        self.progress_bar["value"] = 0

        # Run conversion in a separate thread to keep UI responsive
        threading.Thread(
            target=self.convert_thread,
            args=(png_files, output_pdf_path, self.sort_order.get()),
            daemon=True
        ).start()

    def convert_thread(self, png_files, output_pdf_path, sort_order):
        try:
            # --- Sorting ---
            self.update_status("Sorting files...")
            if sort_order == "name":
                png_files.sort()
            elif sort_order == "date":
                png_files.sort(key=os.path.getmtime)

            # --- Image Conversion ---
            self.update_status("Converting images...")
            image_list = []
            total_files = len(png_files)
            for i, filename in enumerate(png_files):
                self.update_status(f"Processing {i+1}/{total_files}: {os.path.basename(filename)}")
                self.update_progress((i + 1) / total_files * 100)
                img = Image.open(filename)
                img = img.convert('RGB') # Convert to RGB for PDF compatibility
                image_list.append(img)

            if not image_list:
                raise ValueError("No images to convert.")

            # --- Saving to PDF ---
            self.update_status("Saving PDF...")
            image_list[0].save(
                output_pdf_path,
                save_all=True,
                append_images=image_list[1:]
            )

            self.conversion_finished(f"Successfully saved to {os.path.basename(output_pdf_path)}")
        except Exception as e:
            self.conversion_error(f"Error: {e}")

    def update_status(self, message):
        self.root.after(0, lambda: self.status_label.config(text=message))

    def update_progress(self, value):
        self.root.after(0, lambda: self.progress_bar.config(value=value))

    def conversion_finished(self, message):
        self.root.after(0, lambda:
            {
                messagebox.showinfo("Success", message),
                self.reset_ui(),
                self.update_status(message)
            }
        )

    def conversion_error(self, error_message):
        self.root.after(0, lambda:
            {
                messagebox.showerror("Conversion Failed", error_message),
                self.reset_ui()
            }
        )

    def reset_ui(self):
        self.is_converting = False
        self.convert_btn.config(state=tk.NORMAL)
        self.browse_btn.config(state=tk.NORMAL)
        self.progress_bar["value"] = 0
        self.status_label.config(text="Ready for next conversion.")

if __name__ == "__main__":
    root = tk.Tk()
    app = PngToPdfConverterApp(root)
    root.mainloop()
