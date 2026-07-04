import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import random
import json
import os
import re

# --- Paths ---
script_dir = os.path.dirname(os.path.abspath(__file__))
json_path = os.path.join(script_dir, "Reference", "drinks.json")
stock_file = os.path.join(script_dir, "Reference", "stock.json")

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
root.attributes('-fullscreen', True)

style = ttk.Style()
style.configure("TFrame", background="#1c1c1c")
style.configure("TLabel", background="#1c1c1c", foreground="white", font=("Arial", 18))
style.configure("Title.TLabel", font=("Arial", 30, "bold"), foreground="#ffcc00", background="#1c1c1c")
style.configure("Nav.TButton", font=("Arial", 22, "bold"), padding=15)
style.configure("Exit.TButton", font=("Arial", 18, "bold"), padding=10)

# --- Top navigation bar ---
nav_bar = ttk.Frame(root)
nav_bar.pack(fill="x", pady=5)

current_list_type = "cocktail"
stock_visible = False
active_theme_filter = "all"

# ============================================================
# PERFORMANCE: precomputed lookups & caches
# ============================================================

# Lowercase set of in-stock ingredient names. Rebuilt only when
# stock actually changes -- is_out_of_stock becomes a set lookup
# instead of a nested loop over stock_data for every ingredient.
in_stock_lower = set()

def rebuild_stock_lookup():
    global in_stock_lower
    in_stock_lower = {name.lower() for name, qty in stock_data.items() if qty > 0}

rebuild_stock_lookup()

# Ingredient strings never change at runtime, so the regex parsing
# only ever needs to happen once per unique string.
_ingredient_name_cache = {}

def extract_ingredient_name(ingredient_str):
    cached = _ingredient_name_cache.get(ingredient_str)
    if cached is not None:
        return cached
    name = re.sub(r"^\s*\d*\.?\d+\s*(?:oz|ml|tsp)?\s*", "", ingredient_str, flags=re.IGNORECASE)
    name = re.sub(r"\s*\(.*?\)", "", name)
    name = re.sub(r"^Float\s+", "", name, flags=re.IGNORECASE)
    name = re.sub(r"\b(wedges?|slice|slices|dashes)\b", "", name, flags=re.IGNORECASE)
    name = name.strip()
    _ingredient_name_cache[ingredient_str] = name
    return name

def is_out_of_stock(ingredients):
    return any(
        extract_ingredient_name(item).lower() not in in_stock_lower
        for item in ingredients
    )

def format_ingredients(ingredients):
    lines = []
    for item in ingredients:
        ok = extract_ingredient_name(item).lower() in in_stock_lower
        lines.append(f"\u2022 {item}" if ok else f"\u2716 {item}")
    return "\n".join(lines)

# ============================================================
# PERFORMANCE: debounced saving
# ============================================================
# Rapid taps on +/- used to trigger a full JSON write and a full
# drink-list rebuild PER TAP (twice, actually -- once from the
# button command and once from the variable trace). Now we just
# update stock_data in memory and write the file once things have
# been quiet for 750ms.

_save_job = None

def schedule_save():
    global _save_job
    if _save_job is not None:
        root.after_cancel(_save_job)
    _save_job = root.after(750, _do_save)

def _do_save():
    global _save_job
    _save_job = None
    with open(stock_file, "w") as f:
        json.dump(stock_data, f, indent=4)

def flush_save():
    """Write immediately (used on exit so nothing is lost)."""
    global _save_job
    if _save_job is not None:
        root.after_cancel(_save_job)
        _save_job = None
    _do_save()

# --- Main frame ---
main_frame = ttk.Frame(root)
main_frame.pack(fill="both", expand=True)

# --- Left list panel ---
list_frame = ttk.Frame(main_frame, width=350)
list_frame.pack(side="left", fill="y", padx=10, pady=10)

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

all_themes = set()
for d in cocktails.values():
    for t in d.get("theme", []):
        all_themes.add(t.capitalize())

theme_options = ["All"] + sorted(all_themes)
theme_var = tk.StringVar(value="All")

def theme_selected(event):
    filter_cocktails(theme_var.get().lower())

theme_dropdown = ttk.Combobox(filter_frame, textvariable=theme_var, values=theme_options, state="readonly", font=("Arial", 14))
theme_dropdown.pack(fill="x", padx=5)
theme_dropdown.bind("<<ComboboxSelected>>", theme_selected)

# --- Listbox for drinks ---
item_list = tk.Listbox(list_frame, font=("Arial", 16), bg="#2b2b2b", fg="white", selectbackground="#ffcc00")
item_list.pack(fill="both", expand=True, pady=5)

# --- Drink frame (right panel) ---
drink_frame = ttk.Frame(main_frame)
drink_frame.pack(side="left", fill="both", expand=True)

right_canvas = tk.Canvas(drink_frame, bg="#1c1c1c", highlightthickness=0)
scrollbar = ttk.Scrollbar(drink_frame, orient="vertical", command=right_canvas.yview)
scrollable_frame = ttk.Frame(right_canvas)
scrollable_frame.bind("<Configure>", lambda e: right_canvas.configure(scrollregion=right_canvas.bbox("all")))
right_canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
right_canvas.configure(yscrollcommand=scrollbar.set)
right_canvas.pack(side="left", fill="both", expand=True)
scrollbar.pack(side="right", fill="y")

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
# NOTE: not packed at startup -- it only takes space when shown.

stock_canvas = tk.Canvas(stock_frame, bg="#1c1c1c", highlightthickness=0)
stock_scrollbar = ttk.Scrollbar(stock_frame, orient="vertical", command=stock_canvas.yview)
stock_content = ttk.Frame(stock_canvas)
stock_content.bind("<Configure>", lambda e: stock_canvas.configure(scrollregion=stock_canvas.bbox("all")))
stock_canvas.create_window((0, 0), window=stock_content, anchor="nw")
stock_canvas.configure(yscrollcommand=stock_scrollbar.set)
stock_canvas.pack(side="left", fill="both", expand=True)
stock_scrollbar.pack(side="right", fill="y")

# ============================================================
# PERFORMANCE: stock rows are built ONCE, then only updated.
# Destroying and recreating ~250 widgets every time the panel
# opened was the main cause of the multi-second Stock delay.
# ============================================================

stock_entries = {}      # ingredient -> (StringVar, tick_label)
_stock_rows_built = False
_drink_list_dirty = False  # stock changed while stock panel open

def _set_tick(tick_label, qty):
    tick_label.config(
        text="\u2714" if qty > 0 else "\u2716",
        foreground="green" if qty > 0 else "red",
    )

def _apply_stock_change(ingredient, new_qty):
    """Single place every stock mutation goes through."""
    global _drink_list_dirty
    new_qty = max(0, new_qty)
    if stock_data.get(ingredient) == new_qty:
        return
    stock_data[ingredient] = new_qty
    var, tick = stock_entries[ingredient]
    if var.get() != str(new_qty):
        var.set(str(new_qty))
    _set_tick(tick, new_qty)
    rebuild_stock_lookup()
    schedule_save()
    _drink_list_dirty = True  # drink list refreshes when we go back to it

def build_stock_rows():
    global _stock_rows_built
    if _stock_rows_built:
        return
    _stock_rows_built = True

    ttk.Label(stock_content, text="Item", foreground="white", background="#1c1c1c", font=("Arial", 14, "bold")).grid(row=0, column=0, padx=10, pady=5)
    ttk.Label(stock_content, text="In-Stock", foreground="white", background="#1c1c1c", font=("Arial", 14, "bold")).grid(row=0, column=1, padx=10, pady=5)
    ttk.Label(stock_content, text="Amount", foreground="white", background="#1c1c1c", font=("Arial", 14, "bold")).grid(row=0, column=2, padx=10, pady=5)

    row = 1
    for ingredient in sorted(stock_data.keys(), key=str.lower):
        quantity = stock_data[ingredient]

        ttk.Label(stock_content, text=ingredient, foreground="white", background="#1c1c1c", font=("Arial", 14)).grid(row=row, column=0, sticky="w", padx=10, pady=5)

        tick_label = ttk.Label(stock_content, font=("Arial", 14, "bold"))
        tick_label.grid(row=row, column=1, padx=10)
        _set_tick(tick_label, quantity)

        # StringVar rather than IntVar: an empty entry makes
        # IntVar.get() raise tk.TclError, and we don't want a
        # write-trace firing on every keystroke anyway.
        var = tk.StringVar(value=str(quantity))

        frame = ttk.Frame(stock_content)
        frame.grid(row=row, column=2, padx=10, pady=5)

        def make_step_fn(ing, delta):
            def step():
                _apply_stock_change(ing, stock_data.get(ing, 0) + delta)
            return step

        def make_commit_fn(ing, v):
            def commit(event=None):
                try:
                    val = int(v.get())
                except (ValueError, tk.TclError):
                    val = stock_data.get(ing, 0)
                _apply_stock_change(ing, val)
                v.set(str(stock_data[ing]))
            return commit

        btn_left = ttk.Button(frame, text="\u25c0", width=5, command=make_step_fn(ingredient, -1))
        btn_left.pack(side="left", padx=5, ipadx=5, ipady=5)

        entry = ttk.Entry(frame, textvariable=var, width=5, justify="center", font=("Arial", 16))
        entry.pack(side="left", padx=5, ipady=5)
        # Commit typed values when the user leaves the field or
        # presses Return -- NOT on every keystroke.
        commit = make_commit_fn(ingredient, var)
        entry.bind("<FocusOut>", commit)
        entry.bind("<Return>", commit)

        btn_right = ttk.Button(frame, text="\u25b6", width=5, command=make_step_fn(ingredient, 1))
        btn_right.pack(side="left", padx=5, ipadx=5, ipady=5)

        stock_entries[ingredient] = (var, tick_label)
        row += 1

def refresh_stock_display():
    """Sync existing widgets with stock_data (no rebuilding)."""
    for ingredient, (var, tick) in stock_entries.items():
        qty = stock_data.get(ingredient, 0)
        if var.get() != str(qty):
            var.set(str(qty))
        _set_tick(tick, qty)

def show_stock():
    global stock_visible
    if stock_visible:
        hide_stock()
    else:
        build_stock_rows()          # no-op after the first time
        refresh_stock_display()
        stock_frame.pack(side="left", fill="both", expand=True)
        stock_visible = True

def hide_stock():
    global stock_visible
    if stock_visible:
        stock_frame.pack_forget()
        stock_visible = False
    refresh_drink_list_if_dirty()

def refresh_drink_list_if_dirty():
    global _drink_list_dirty
    if not _drink_list_dirty:
        return
    _drink_list_dirty = False
    if current_list_type == "cocktail":
        filter_cocktails(active_theme_filter)
    else:
        populate_list(shots)
    selection = item_list.curselection()
    if selection:
        on_select(None)

# --- Display functions ---
def _display_drink(name, data, img_size):
    cocktail_title.config(text=name)
    cocktail_title.config(foreground="red" if is_out_of_stock(data["ingredients"]) else "#ffcc00")
    try:
        image = Image.open(data["image"]).resize(img_size)
        photo = ImageTk.PhotoImage(image)
        cocktail_image_label.config(image=photo, text="")
        cocktail_image_label.image = photo
    except Exception:
        cocktail_image_label.config(image="", text="(No image)")
        cocktail_image_label.image = None
    cocktail_description.config(text=data["description"])
    cocktail_ingredients.config(text=format_ingredients(data["ingredients"]))
    cocktail_recipe.config(text="Recipe:\n" + data["recipe"])

def display_cocktail(name):
    _display_drink(name, cocktails[name], (200, 250))

def display_shot(name):
    _display_drink(name, shots[name], (150, 150))

def populate_list(data_dict):
    item_list.delete(0, tk.END)

    in_stock_items = []
    out_of_stock_items = []
    for name, d in data_dict.items():
        (out_of_stock_items if is_out_of_stock(d["ingredients"]) else in_stock_items).append(name)

    in_stock_items.sort()
    out_of_stock_items.sort()

    for i, name in enumerate(in_stock_items):
        item_list.insert(tk.END, name)
        item_list.itemconfig(i, foreground="white")

    offset = len(in_stock_items)
    for i, name in enumerate(out_of_stock_items):
        item_list.insert(tk.END, name)
        item_list.itemconfig(offset + i, foreground="red")

def show_cocktail_list():
    global current_list_type, _drink_list_dirty
    current_list_type = "cocktail"
    _drink_list_dirty = False
    search_var.set("")
    filter_cocktails(active_theme_filter)
    hide_stock()

def show_shot_list():
    global current_list_type, _drink_list_dirty
    current_list_type = "shot"
    _drink_list_dirty = False
    search_var.set("")
    populate_list(shots)
    hide_stock()

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

    query = search_var.get()
    if query == "Search by ingredient...":
        query = ""
    query = query.lower()

    filtered = {}
    for name, d in cocktails.items():
        cocktail_themes = d.get("theme", [])
        if isinstance(cocktail_themes, str):
            cocktail_themes = [cocktail_themes.lower()]
        else:
            cocktail_themes = [t.lower() for t in cocktail_themes]

        if theme == "all" or theme.lower() in cocktail_themes:
            if query == "" or any(query in ing.lower() for ing in d["ingredients"]):
                filtered[name] = d

    populate_list(filtered)

# PERFORMANCE: debounce search too, so the list rebuilds once when
# you pause typing rather than on every single keystroke.
_search_job = None

def update_search(*args):
    global _search_job
    if _search_job is not None:
        root.after_cancel(_search_job)
    _search_job = root.after(200, _do_search)

def _do_search():
    global _search_job
    _search_job = None
    if current_list_type == "cocktail":
        filter_cocktails(active_theme_filter)
    else:
        query = search_var.get()
        if query == "Search by ingredient...":
            query = ""
        query = query.lower()
        filtered = {name: d for name, d in shots.items() if query in " ".join(d["ingredients"]).lower()}
        populate_list(filtered)

search_var.trace_add("write", update_search)

def exit_app():
    flush_save()  # make sure a pending debounced save isn't lost
    root.destroy()

# --- Top nav buttons ---
ttk.Button(nav_bar, text="Cocktails", style="Nav.TButton", command=show_cocktail_list).pack(side="left", padx=5)
ttk.Button(nav_bar, text="Shots", style="Nav.TButton", command=show_shot_list).pack(side="left", padx=5)
ttk.Button(nav_bar, text="\U0001f3b2 Random", style="Nav.TButton", command=show_random).pack(side="left", padx=5)
ttk.Button(nav_bar, text="Stock", style="Nav.TButton", command=show_stock).pack(side="left", padx=5)
ttk.Button(nav_bar, text="Exit", style="Exit.TButton", command=exit_app).pack(side="right", padx=5)

# --- Initialize ---
show_cocktail_list()
root.mainloop()