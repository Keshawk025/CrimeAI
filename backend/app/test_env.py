import os
print("OS NAME:", os.name)
print("PG ENV:", {k: v for k, v in os.environ.items() if "PG" in k})
