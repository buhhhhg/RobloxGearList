import csv
import os

def merge_csv():
    old_csv_path = os.path.join("3-10-2025", "data.csv")
    new_csv_path = "data.csv"
    merged_csv_path = "merged_data.csv"
    
    unique_rows = set()
    
    for file_path in [old_csv_path, new_csv_path]:
        if os.path.exists(file_path):
            with open(file_path, "r", newline="", encoding="utf-8") as f:
                reader = csv.reader(f)
                header = next(reader)
                for row in reader:
                    unique_rows.add(tuple(row))
    
    with open(merged_csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["id", "name"])
        writer.writerows(unique_rows)

if __name__ == "__main__":
    merge_csv()
