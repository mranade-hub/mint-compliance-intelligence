import os

def create_phase_folders(company):

    base = f"downloads/{company}"
    os.makedirs(base, exist_ok=True)

    phases = ["Engage","Design","Build","Partner","Validation","Closure"]

    for p in phases:
        os.makedirs(f"{base}/{p}", exist_ok=True)