import patch_ng
from pathlib import Path
from io import BytesIO

# Load patch as bytes
patch_bytes = Path(r"C:\Users\laure\PycharmProjects\mediaplanpy\dev\fixtures\upgrade.patch").read_bytes()
print(patch_bytes)

# Use BytesIO directly with PatchSet
pset = patch_ng.PatchSet(BytesIO(patch_bytes))
print(pset)

# Apply the patch
if not pset.apply():
    raise Exception("Patch failed to apply.")
