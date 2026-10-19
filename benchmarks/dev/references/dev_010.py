def is_armstrong(n):
    digits = [int(ch) for ch in str(n)]
    return sum(digit ** len(digits) for digit in digits) == n
