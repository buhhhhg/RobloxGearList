import csv

def csv_to_plaintext(csv_file, txt_file):
    with open(csv_file, "r", newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        next(reader)
        with open(txt_file, "w", encoding="utf-8") as out_f:
            for row in reader:
                out_f.write(f"ID: {row[0]}, Name: {row[1]}\n")

if __name__ == "__main__":
    csv_to_plaintext("merged_data.csv", "merged_data.txt")