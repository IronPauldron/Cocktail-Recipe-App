import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import random
import json
import os
import re

# --- Paths ---
json_path = os.path.join("Reference", "drinks.json")
stock_file = os.path.join("Reference", "stock.json")

# --- Load drinks ---
with open(json_path, "r") as f:
    data = json.load(f)
cocktails = data["cocktails"]
shots = data["shots"]

# --- Load stock ---
if os.path.exists(stock_file):
    with open(stock_file, "r") as f:
        stock_data = json.load(f)
else:
    stock_data = {}

# --- Main window ---
root = tk.Tk()
root.title("Drink Selector")
root.configure(bg="#1c1c1c")
root.state("zoomed")  # Full screen

style = ttk.Style()
style.configure("TFrame", background="#1c1c1c")
style.configure("TLabel", background="#1c1c1c", foreground="white", font=("Arial", 14))
style.configure("Title.TLabel", font=("Arial", 22, "bold"), foreground="#ffcc00", background="#1c1c1c")
style.configure("Nav.TButton", font=("Arial", 16, "bold"), padding=10)
style.configure("Exit.TButton", font=("Arial", 16, "bold"), padding=10)

# --- Top navigation bar ---
nav_bar = ttk.Frame(root)
nav_bar.pack(fill="x", pady=5)

current_list_type = "cocktail"
stock_visible = False  # Track whether stock panel is visible
active_theme_filter = "all"  # Current theme filter

# --- Main frame ---
main_frame = ttk.Frame(root)
main_frame.pack(fill="both", expand=True)

# --- Left list panel ---
list_frame = ttk.Frame(main_frame, width=250)
list_frame.pack(side="left", fill="y", padx=10, pady=10)

# --- Top frame inside list_frame for search and filters ---
list_top_frame = ttk.Frame(list_frame)
list_top_frame.pack(fill="x", pady=5)

# --- Search bar ---
search_var = tk.StringVar()
search_entry = ttk.Entry(list_top_frame, textvariable=search_var, font=("Arial", 16), foreground="grey")
search_entry.pack(fill="x", pady=5)
search_entry.insert(0, "Search by ingredient...")

def clear_placeholder(event):
    if search_entry.get() == "Search by ingredient...":
        search_entry.delete(0, tk.END)
        search_entry.config(foreground="white")

def add_placeholder(event):
    if not search_entry.get():
        search_entry.insert(0, "Search by ingredient...")
        search_entry.config(foreground="grey")

search_entry.bind("<FocusIn>", clear_placeholder)
search_entry.bind("<FocusOut>", add_placeholder)

# --- Filter dropdown ---
filter_frame = ttk.Frame(list_top_frame)
filter_frame.pack(fill="x", pady=5)

# Collect all unique themes from cocktails
all_themes = set()
for data in cocktails.values():
    for t in data.get("theme", []):
        all_themes.add(t.capitalize())

theme_options = ["All"] + sorted(all_themes)  # Add "All" at the top
theme_var = tk.StringVar(value="All")

def theme_selected(event):
    selected_theme = theme_var.get().lower()
    filter_cocktails(selected_theme)

theme_dropdown = ttk.Combobox(filter_frame, textvariable=theme_var, values=theme_options, state="readonly", font=("Arial", 14))
theme_dropdown.pack(fill="x", padx=5)
theme_dropdown.bind("<<ComboboxSelected>>", theme_selected)

# --- Listbox for drinks (below search & filter) ---
item_list = tk.Listbox(list_frame, font=("Arial", 16), bg="#2b2b2b", fg="white", selectbackground="#ffcc00")
item_list.pack(fill="both", expand=True, pady=5)

# --- Drink frame (right panel) ---
drink_frame = ttk.Frame(main_frame)
drink_frame.pack(side="left", fill="both", expand=True)

# Scrollable canvas inside drink_frame
right_canvas = tk.Canvas(drink_frame, bg="#1c1c1c", highlightthickness=0)
scrollbar = ttk.Scrollbar(drink_frame, orient="vertical", command=right_canvas.yview)
scrollable_frame = ttk.Frame(right_canvas)
scrollable_frame.bind("<Configure>", lambda e: right_canvas.configure(scrollregion=right_canvas.bbox("all")))
right_canvas.create_window((0,0), window=scrollable_frame, anchor="nw")
right_canvas.configure(yscrollcommand=scrollbar.set)
right_canvas.pack(side="left", fill="both", expand=True)
scrollbar.pack(side="right", fill="y")

# Drink widgets
cocktail_title = ttk.Label(scrollable_frame, text="Select a drink", style="Title.TLabel")
cocktail_title.pack(pady=10)

top_frame = ttk.Frame(scrollable_frame)
top_frame.pack(fill="x", pady=10)

cocktail_image_label = ttk.Label(top_frame)
cocktail_image_label.pack(side="left", padx=10)

cocktail_description = ttk.Label(top_frame, text="", wraplength=500, justify="left")
cocktail_description.pack(side="left", fill="both", expand=True, padx=10)

cocktail_ingredients = ttk.Label(scrollable_frame, text="", justify="left")
cocktail_ingredients.pack(pady=5, anchor="w", padx=10)

cocktail_recipe = ttk.Label(scrollable_frame, text="", wraplength=600, justify="left")
cocktail_recipe.pack(pady=10, anchor="w", padx=10)

# --- Stock frame ---
stock_frame = ttk.Frame(main_frame)
stock_frame.pack(side="left", fill="both", expand=True)
stock_frame.lower()  # initially hidden

stock_canvas = tk.Canvas(stock_frame, bg="#1c1c1c", highlightthickness=0)
stock_scrollbar = ttk.Scrollbar(stock_frame, orient="vertical", command=stock_canvas.yview)
stock_content = ttk.Frame(stock_canvas)
stock_content.bind("<Configure>", lambda e: stock_canvas.configure(scrollregion=stock_canvas.bbox("all")))
stock_canvas.create_window((0,0), window=stock_content, anchor="nw")
stock_canvas.configure(yscrollcommand=stock_scrollbar.set)
stock_canvas.pack(side="left", fill="both", expand=True)
stock_scrollbar.pack(side="right", fill="y")

stock_entries = {}

def save_stock():
    for ingredient, (var, tick_label) in stock_entries.items():
        try:
            stock_data[ingredient] = int(var.get())
        except ValueError:
            stock_data[ingredient] = 0
        tick_label.config(text="✔" if stock_data[ingredient] > 0 else "✖", foreground="green" if stock_data[ingredient] > 0 else "red")

    with open(stock_file, "w") as f:
        json.dump(stock_data, f, indent=4)
    
    # Refresh drink list highlighting
    if current_list_type == "cocktail":
        filter_cocktails(active_theme_filter)
    else:
        populate_list(shots)
    
    selection = item_list.curselection()
    if selection:
        on_select(None)

def populate_stock():
    for widget in stock_content.winfo_children():
        widget.destroy()
    stock_entries.clear()

    # --- Headers ---
    ttk.Label(stock_content, text="Item", foreground="white", background="#1c1c1c", font=("Arial",14,"bold")).grid(row=0, column=0, padx=10, pady=5)
    ttk.Label(stock_content, text="In-Stock", foreground="white", background="#1c1c1c", font=("Arial",14,"bold")).grid(row=0, column=1, padx=10, pady=5)
    ttk.Label(stock_content, text="Amount", foreground="white", background="#1c1c1c", font=("Arial",14,"bold")).grid(row=0, column=2, padx=10, pady=5)

    row = 1
    for ingredient, quantity in stock_data.items():
        ttk.Label(stock_content, text=ingredient, foreground="white", background="#1c1c1c", font=("Arial",14)).grid(row=row, column=0, sticky="w", padx=10, pady=5)
        tick_label = ttk.Label(stock_content, font=("Arial",14,"bold"))
        tick_label.grid(row=row, column=1, padx=10)
        tick_label.config(text="✔" if quantity > 0 else "✖", foreground="green" if quantity > 0 else "red")

        var = tk.IntVar(value=quantity)
        frame = ttk.Frame(stock_content)
        frame.grid(row=row, column=2, padx=10, pady=5)

        def make_update_fn(ing, v, t, delta):
            def update():
                new_val = max(0, v.get() + delta)
                v.set(new_val)
                stock_data[ing] = new_val
                t.config(text="✔" if new_val > 0 else "✖", foreground="green" if new_val > 0 else "red")
                save_stock()
            return update

        btn_left = ttk.Button(frame, text="◀", width=5, command=make_update_fn(ingredient, var, tick_label, -1))
        btn_left.pack(side="left", padx=5, ipadx=5, ipady=5)
        entry = ttk.Entry(frame, textvariable=var, width=5, justify="center", font=("Arial",16))
        entry.pack(side="left", padx=5, ipady=5)
        btn_right = ttk.Button(frame, text="▶", width=5, command=make_update_fn(ingredient, var, tick_label, 1))
        btn_right.pack(side="left", padx=5, ipadx=5, ipady=5)

        def on_entry_change(var=var, ing=ingredient, tick=tick_label):
            try:
                val = max(0, int(var.get()))
            except ValueError:
                val = 0
            var.set(val)
            stock_data[ing] = val
            tick.config(text="✔" if val > 0 else "✖", foreground="green" if val > 0 else "red")
            save_stock()
        var.trace_add("write", lambda *args: on_entry_change())

        stock_entries[ingredient] = (var, tick_label)
        row += 1

def show_stock():
    global stock_visible
    if stock_visible:
        stock_frame.pack_forget()
        stock_visible = False
    else:
        stock_frame.pack(side="left", fill="both", expand=True)
        populate_stock()
        stock_visible = True

# --- Ingredient helpers ---
def extract_ingredient_name(ingredient_str):
    name = re.sub(r"^\s*\d*\.?\d+\s*(?:oz|ml|tsp)?\s*", "", ingredient_str, flags=re.IGNORECASE)
    name = re.sub(r"\s*\(.*?\)", "", name)
    name = re.sub(r"^Float\s+", "", name, flags=re.IGNORECASE)
    name = re.sub(r"\b(wedges?|slice|slices|dashes)\b", "", name, flags=re.IGNORECASE)
    return name.strip()

def is_out_of_stock(ingredients):
    for item in ingredients:
        base_name = extract_ingredient_name(item)
        in_stock = any(stock_item.lower() == base_name.lower() and qty > 0 for stock_item, qty in stock_data.items())
        if not in_stock:
            return True
    return False

def format_ingredients(ingredients):
    lines = []
    for item in ingredients:
        base_name = extract_ingredient_name(item)
        in_stock = any(stock_item.lower() == base_name.lower() and qty > 0 for stock_item, qty in stock_data.items())
        lines.append(f"• {item}" if in_stock else f"✖ {item}")
    return "\n".join(lines)

# --- Display functions ---
def display_cocktail(name):
    data = cocktails[name]
    cocktail_title.config(text=name)
    cocktail_title.config(foreground="red" if is_out_of_stock(data["ingredients"]) else "#ffcc00")
    try:
        image = Image.open(data["image"]).resize((150,150))
        photo = ImageTk.PhotoImage(image)
        cocktail_image_label.config(image=photo, text="")
        cocktail_image_label.image = photo
    except:
        cocktail_image_label.config(image="", text="(No image)")
    cocktail_description.config(text=data["description"])
    cocktail_ingredients.config(text=format_ingredients(data["ingredients"]))
    cocktail_recipe.config(text="Recipe:\n" + data["recipe"])

def display_shot(name):
    data = shots[name]
    cocktail_title.config(text=name)
    cocktail_title.config(foreground="red" if is_out_of_stock(data["ingredients"]) else "#ffcc00")
    try:
        image = Image.open(data["image"]).resize((150,150))
        photo = ImageTk.PhotoImage(image)
        cocktail_image_label.config(image=photo, text="")
        cocktail_image_label.image = photo
    except:
        cocktail_image_label.config(image="", text="(No image)")
    cocktail_description.config(text=data["description"])
    cocktail_ingredients.config(text=format_ingredients(data["ingredients"]))
    cocktail_recipe.config(text="Recipe:\n" + data["recipe"])

def populate_list(data_dict):
    item_list.delete(0, tk.END)
    for i, name in enumerate(data_dict.keys()):
        item_list.insert(tk.END, name)
        item_list.itemconfig(i, foreground="red" if is_out_of_stock(data_dict[name]["ingredients"]) else "white")

def show_cocktail_list():
    global current_list_type
    current_list_type = "cocktail"
    search_var.set("")
    filter_cocktails(active_theme_filter)
    drink_frame.tkraise()
    if stock_visible:
        stock_frame.pack_forget()

def show_shot_list():
    global current_list_type
    current_list_type = "shot"
    search_var.set("")
    populate_list(shots)
    drink_frame.tkraise()
    if stock_visible:
        stock_frame.pack_forget()

def show_random():
    if current_list_type == "cocktail":
        display_cocktail(random.choice(list(cocktails.keys())))
    else:
        display_shot(random.choice(list(shots.keys())))

def on_select(event):
    selection = item_list.curselection()
    if not selection:
        return
    name = item_list.get(selection[0])
    if current_list_type == "cocktail":
        display_cocktail(name)
    else:
        display_shot(name)

item_list.bind("<<ListboxSelect>>", on_select)

# --- Search and filter functions ---
def filter_cocktails(theme):
    global active_theme_filter
    active_theme_filter = theme
    
    # Get actual query, ignore placeholder
    query = search_var.get()
    if query == "Search by ingredient...":
        query = ""
    query = query.lower()
    
    filtered = {}
    for name, data in cocktails.items():
        cocktail_themes = data.get("theme", [])
        if isinstance(cocktail_themes, str):  # backward compatibility
            cocktail_themes = [cocktail_themes.lower()]
        else:
            cocktail_themes = [t.lower() for t in cocktail_themes]
        
        if theme == "all" or theme.lower() in cocktail_themes:
            if query == "" or any(query in ing.lower() for ing in data["ingredients"]):
                filtered[name] = data

    populate_list(filtered)

def update_search(*args):
    if current_list_type == "cocktail":
        filter_cocktails(active_theme_filter)
    else:
        query = search_var.get().lower()
        filtered = {name: data for name, data in shots.items() if query in " ".join(data["ingredients"]).lower()}
        populate_list(filtered)

search_var.trace_add("write", update_search)

# --- Top nav buttons ---
ttk.Button(nav_bar, text="Cocktails", style="Nav.TButton", command=show_cocktail_list).pack(side="left", padx=5)
ttk.Button(nav_bar, text="Shots", style="Nav.TButton", command=show_shot_list).pack(side="left", padx=5)
ttk.Button(nav_bar, text="🎲 Random", style="Nav.TButton", command=show_random).pack(side="left", padx=5)
ttk.Button(nav_bar, text="Stock", style="Nav.TButton", command=show_stock).pack(side="left", padx=5)
ttk.Button(nav_bar, text="Exit", style="Exit.TButton", command=root.destroy).pack(side="right", padx=5)

# --- Initialize ---
show_cocktail_list()
root.mainloop()
