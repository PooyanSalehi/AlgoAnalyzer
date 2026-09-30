def linear_search(arr, target):
    """Scan the array left to right; returns first index of target or -1."""
    for i in range(len(arr)):
        if arr[i] == target:
            return i
    return -1
