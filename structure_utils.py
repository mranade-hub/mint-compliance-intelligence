def get_folder_structure(service, folder_id):

    lines = []

    def scan(fid, indent=""):

        res = service.files().list(
            q=f"'{fid}' in parents and trashed=false",
            fields="files(id,name,mimeType)"
        ).execute()

        items = res.get("files", [])

        folders = []
        files = []

        for item in items:
            if item["mimeType"] == "application/vnd.google-apps.folder":
                folders.append(item)
            else:
                files.append(item)

        for f in files:
            lines.append(f"{indent}- {f['name']}")

        for f in folders:
            lines.append(f"{indent}[FOLDER] {f['name']}")
            scan(f["id"], indent + "  ")

    scan(folder_id)

    return "\n".join(lines)