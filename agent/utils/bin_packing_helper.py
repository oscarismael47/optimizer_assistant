import matplotlib.pyplot as plt
from rectpack import newPacker


# -------------------------------
# Pallet & Container Definitions
# -------------------------------
def create_pallet(width, height, buffer=0):
    """Return pallet dimensions with optional buffer included."""
    return [width + buffer, height + buffer]


def create_container(width, height):
    """Return container size (width, height)."""
    return [(width, height)]


# -------------------------------
# Solver
# -------------------------------
def solve_bin_packing(pallets, bins):
    """
    pallets: list of (pallet, quantity) e.g. [(pal_812, 10), (pal_1012, 5)]
    bins: list of containers (width, height)
    """
    rectangles = []
    for pallet, qty in pallets:
        rectangles.extend([pallet] * qty)

    pack = newPacker()

    # Add pallets
    for r in rectangles:
        pack.add_rect(*r)

    # Add containers
    for b in bins:
        pack.add_bin(*b)

    # Run packing
    pack.pack()

    all_rects = pack.rect_list()
    all_pals = [sorted([p[3], p[4]]) for p in all_rects]

    # Print summary
    for pallet, qty in pallets:
        count = all_pals.count(sorted(pallet))
        print(f"{count}/{qty} Pallets {pallet[0]}x{pallet[1]} cm")

    return all_rects, all_pals


# -------------------------------
# Plotting
# -------------------------------
def plot_solution(all_rects, pallets, bin_size):
    """Visualize packing solution with labels and colors."""
    plt.figure(figsize=(12, 6))
    
    bx, by = bin_size
    # Draw container outline
    plt.plot([0, bx, bx, 0, 0], [0, 0, by, by, 0],
             'k-', linewidth=2, label="Container")
    
    colors = ["blue", "red", "green", "orange", "purple"]  # extend if needed

    for i, rect in enumerate(all_rects):
        b, x, y, w, h, rid = rect
        pallet_type = sorted([w, h])

        # Find index of pallet type
        idx = None
        for j, (pallet, qty) in enumerate(pallets):
            if sorted(pallet) == pallet_type:
                idx = j
                break

        color = colors[idx % len(colors)] if idx is not None else "gray"

        # Draw pallet
        plt.fill([x, x+w, x+w, x], [y, y, y+h, y+h],
                 alpha=0.3, color=color, edgecolor='black')
        plt.text(x + w/2, y + h/2, f"P{i+1}",
                 ha='center', va='center', fontsize=8, color='black')
    
    plt.gca().set_aspect('equal', adjustable='box')
    plt.xlim(0, bx+10)
    plt.ylim(0, by+10)
    plt.xlabel("cm")
    plt.ylabel("cm")
    plt.title("Container Loading Plan")
    
    legend_labels = [f"Pallet {p[0]}x{p[1]} cm" for p, _ in pallets]
    plt.legend(["Container"] + legend_labels, loc="upper right")
    plt.grid(True, linestyle="--", alpha=0.5)
    plt.show()


# -------------------------------
# Example Usage
# -------------------------------
if __name__ == "__main__":
    # ejemplo: un solo contenedor de 300x600 cm
    my_container = create_container(300, 600)

    # pallets definidos por el usuario
    pal1 = create_pallet(80, 120, buffer=5)
    pal2 = create_pallet(100, 120, buffer=5)

    # cantidades de pallets
    pallets = [(pal1, 8), (pal2, 6)]

    # resolver
    all_rects, all_pals = solver(pallets, my_container)

    # graficar
    plot_solution(all_rects, pallets, my_container[0])