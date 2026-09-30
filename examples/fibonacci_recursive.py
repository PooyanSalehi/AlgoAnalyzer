def fibonacci(n):
    """Naive recursive Fibonacci — recomputes overlapping subproblems."""
    if n <= 1:
        return n
    return fibonacci(n - 1) + fibonacci(n - 2)
