import csv
import os

def find_all_folders(latest_fold):
    folders = []
    for entry in os.scandir("."):
        if (entry.is_dir() and
            entry.name != latest_fold and
            entry.name != ".git" and
            not entry.name.startswith(".")):
            folders.append(entry.name)
    return folders

def merge_csv(latest_fold):
    unique_rows = set()
    header = None

    old_folders = find_all_folders(latest_fold)
    all_sources = old_folders + [latest_fold, "."]

    for source in all_sources:
        csv_path = "data.csv" if source == "." else os.path.join(source, "data.csv")

        if os.path.exists(csv_path):
            with open(csv_path, "r", newline="", encoding="utf-8") as f:
                reader = csv.reader(f)
                file_header = next(reader, None)
                if file_header and header is None:
                    header = [field.strip() for field in file_header]
                for row in reader:
                    if row:
                        unique_rows.add(tuple(field.strip() for field in row))
            print(f"  Read {csv_path}")

    if not unique_rows:
        print("No data found.")
        return

    with open("merged_data.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(header or ["id", "name"])
        writer.writerows(sorted(unique_rows))

    print(f"\nMerged {len(unique_rows)} unique rows → merged_data.csv")

if __name__ == "__main__":
    latest_fold = input("Enter latest folder name: ").strip()
    merge_csv(latest_fold)