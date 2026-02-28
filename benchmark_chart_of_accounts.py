import time
import random

# Mock data generation
def generate_accounts(n=100000):
    accounts = []
    for _ in range(n):
        accounts.append({
            'account_name_of_catogory_PL': 'PL' if random.random() > 0.5 else None,
            'account_name_of_catogory_Balace_sheet': 'BS' if random.random() > 0.5 else None,
            'other_data': 'some data'
        })
    return accounts

def original_logic(accounts):
    pl_count = len([a for a in accounts if a['account_name_of_catogory_PL']])
    bs_count = len([a for a in accounts if a['account_name_of_catogory_Balace_sheet']])
    return pl_count, bs_count

def optimized_logic(accounts):
    pl_count = 0
    bs_count = 0
    for a in accounts:
        if a['account_name_of_catogory_PL']:
            pl_count += 1
        if a['account_name_of_catogory_Balace_sheet']:
            bs_count += 1
    return pl_count, bs_count

def run_benchmark():
    n = 1000000 # 1 million records to make it noticeable
    print(f"Generating {n} accounts...")
    accounts = generate_accounts(n)

    print("Running original logic...")
    start_time = time.time()
    pl1, bs1 = original_logic(accounts)
    end_time = time.time()
    original_duration = end_time - start_time
    print(f"Original logic took: {original_duration:.6f} seconds")

    print("Running optimized logic...")
    start_time = time.time()
    pl2, bs2 = optimized_logic(accounts)
    end_time = time.time()
    optimized_duration = end_time - start_time
    print(f"Optimized logic took: {optimized_duration:.6f} seconds")

    assert pl1 == pl2
    assert bs1 == bs2
    print("Results match.")

    improvement = (original_duration - optimized_duration) / original_duration * 100
    print(f"Improvement: {improvement:.2f}%")

if __name__ == "__main__":
    run_benchmark()
