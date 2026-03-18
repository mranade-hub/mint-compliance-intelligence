import os
import zipfile

def extract_zip(uploaded_file, company):
    path = f"downloads/{company}"
    os.makedirs(path, exist_ok=True)

    with zipfile.ZipFile(uploaded_file, 'r') as zip_ref:
        zip_ref.extractall(path)

    return path


def scan_and_group(base_path):
    phase_map = {phase: [] for phase in [
        "Engage", "Design", "Build",
        "Partner OnBoarding", "Validation", "Closure"
    ]}

    for root, dirs, files in os.walk(base_path):
        for file in files:
            full = os.path.join(root, file)
            folder = root.lower()

            if "engage" in folder:
                phase_map["Engage"].append(full)
            elif "design" in folder:
                phase_map["Design"].append(full)
            elif "build" in folder and "partner" not in folder:
                phase_map["Build"].append(full)
            elif "partner" in folder:
                phase_map["Partner OnBoarding"].append(full)
            elif "validation" in folder or "execute" in folder:
                phase_map["Validation"].append(full)
            elif "closure" in folder or "hypercare" in folder:
                phase_map["Closure"].append(full)

    return phase_map