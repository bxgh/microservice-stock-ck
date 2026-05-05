import sys
import pywencai

print(f"Python: {sys.version}")
print("Testing pywencai.get()...")

try:
    # Simple query to test connectivity and headless browser
    res = pywencai.get(question="今日行业涨幅榜", loop=True)
    if res is not None:
        print(f"Success! Result Type: {type(res)}")
        if hasattr(res, 'shape'):
             print(f"Shape: {res.shape}")
    else:
        print("Result is None")
except Exception as e:
    print(f"Error: {e}")
