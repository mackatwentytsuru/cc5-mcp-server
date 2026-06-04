import sys

Q = chr(34)
path = r"C:/Users/macka/Projects/cc5-mcp-server/cc5-plugin/cc5_api.py"

with open(path, "r", encoding="utf-8") as f:
    original = f.readlines()

keep = original[:2650]

print(f"keep {|en(keep)} lines, last: {repr(keep[-1])}")
with open(path, "w", encoding="utf-8") as f:
    f.writelines(keep)
    f.write("\n# UR-02 TEST OK\n")
print("Wrote test")
