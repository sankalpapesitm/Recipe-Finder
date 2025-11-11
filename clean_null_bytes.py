# Create a script to clean config.py as well
with open("advanced_recipe_finder/config.py", "rb") as f:
    data = f.read().replace(b'\x00', b'')

with open("advanced_recipe_finder/config.py", "wb") as f:
    f.write(data)
