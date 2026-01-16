import asyncio
import xxhash
from typing import List

def get_shard_id(code: str) -> int:
    return xxhash.xxh64(code).intdigest() % 3

def test_grouping():
    test_codes = ["000001", "600519", "300750", "002415", "601318", "000858"]
    groups = {0: [], 1: [], 2: []}
    for code in test_codes:
        sid = get_shard_id(code)
        groups[sid].append(code)
    
    print("\n--- xxhash Grouping Test ---")
    for sid, codes in groups.items():
        print(f"Shard {sid}: {codes}")

def calculate_strategy(failed_count: int, coverage: float):
    print(f"\n--- Strategy Decision Test (Failed: {failed_count}, Coverage: {coverage:.2f}%) ---")
    
    # Simulate Gate-3 logic
    if 1 <= failed_count <= 50:
        return "Strategy 1: Single Node Targeted Supplement (stock_data_supplement)"
    elif 51 <= failed_count <= 200:
        return "Strategy 2: Parallel Shard Supplement (stock_data_supplement per shard)"
    elif failed_count > 200:
        if coverage < 50.0:
            return "Strategy 3: Full Shard Repair (repair_tick --scope all)"
        else:
            return "Strategy 3: Targeted Shard Repair (repair_tick --stock-codes)"
    return "No actions needed"

if __name__ == "__main__":
    test_grouping()
    
    # Scenario 1: Minor failures
    print(calculate_strategy(10, 99.5))
    
    # Scenario 2: Moderate failures
    print(calculate_strategy(75, 98.0))
    
    # Scenario 3: Major failures (Above 200 but good coverage)
    print(calculate_strategy(250, 95.0))
    
    # Scenario 4: Major failures (Low coverage)
    print(calculate_strategy(250, 45.0))
