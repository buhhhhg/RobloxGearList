import csv


def csv_to_plaintext(csv_file, txt_file):
    seen = set()

    with open(csv_file, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    with open(txt_file, "w", encoding="utf-8") as out_f:
        for row in rows:
            name = row["name"].strip()
            gear_id = row["id"].strip()
            out = f"ID: {gear_id}, Name: {name}\n"
            if out not in seen:
                seen.add(out)
                out_f.write(out)


if __name__ == "__main__":
    csv_to_plaintext("merged_data.csv", "merged_data.txt")
