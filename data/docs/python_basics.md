# Python Basics

## List Comprehensions

```python
squares = [x * x for x in range(5)]
```

## Functions

```python
def add(a, b):
    return a + b
```

## Decorators

```python
def loud(fn):
    def wrapper(*args, **kwargs):
        print("Calling", fn.__name__)
        return fn(*args, **kwargs)
    return wrapper
```

