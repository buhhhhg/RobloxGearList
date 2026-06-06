import re

data = ""
with open("data.txt", "r", encoding="utf-8") as f:
    data = f.read()

regex = r"ID: (\d+), Name: (.*)"


def repl(match: re.Match[str]) -> str:
    gearId, name = match.group(0), match.group(1)
    if gearId and name:
        return f"{gearId},{name}"

    return match.string


new_data = "id,name\n" + re.sub(regex, repl, data)

with open("data.csv", "w", encoding="utf-8") as f:
    f.write(new_data)
