import win32com.client

print("开始创建 COM 对象...")

try:
    ths = win32com.client.Dispatch("HexinTrade.Application")
    print("✅ COM 对象创建成功:", ths)

    try:
        logged = ths.IsLogined()
        print("IsLogined():", logged)
    except Exception as e:
        print("⚠️ COM 存在，但接口不可用:", e)

except Exception as e:
    print("❌ COM 创建失败:", e)
