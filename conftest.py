import os

if "test.db" in os.listdir("."):
    os.remove("test.db")
