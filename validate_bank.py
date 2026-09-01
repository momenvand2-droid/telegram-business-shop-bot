from response_bank_100k import RESPONSES
all_items=[x for group in RESPONSES.values() for x in group]
print("categories:", len(RESPONSES))
print("responses:", len(all_items))
print("unique:", len(set(all_items)))
assert len(RESPONSES)==200
assert len(all_items)==100000
assert len(set(all_items))==100000
print("OK: exactly 100,000 unique categorized responses")
