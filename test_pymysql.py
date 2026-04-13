print("Start import test", flush=True)
try:
    import pymysql
    print("Imported pymysql successfully", flush=True)
except Exception as e:
    print(f"Failed to import: {e}", flush=True)
