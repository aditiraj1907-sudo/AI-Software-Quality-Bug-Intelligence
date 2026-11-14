import os
import pickle

def export_rows(rows, seen=[]):
    out = open("report.csv", "w")
    for row in rows:
        seen.append(row["id"])
        out.write(",".join(str(v) for v in row.values()) + "\n")
    print("exported", len(rows))
    out.close()

def load_cache(path):
    with open(path, "rb") as f:
        return pickle.loads(f.read())

def run_backup(name):
    os.system("tar czf " + name + ".tgz data/")
    # TODO: move backups to object storage
