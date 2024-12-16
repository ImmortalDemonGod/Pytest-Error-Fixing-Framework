# Getting Started with Hypothesis: A Practical Guide

## Introduction
Hypothesis is a powerful property-based testing library for Python that helps you find edge cases and errors in your code by generating test data. This guide will walk you through common use cases and best practices.

## 1. Basic Usage

### Simple Example
Let's start with a basic example testing a string reversal function:

```python
from hypothesis import given
import hypothesis.strategies as st

@given(st.text())
def test_string_reversal(s):
    # Reverse string twice
    twice_reversed = reverse_string(reverse_string(s))
    # Should get back original string
    assert twice_reversed == s
```

### Understanding @given
The `@given` decorator tells Hypothesis what kind of data to generate. It will repeatedly call your test with different inputs, trying to find failing cases.

## 2. Common Strategies

Hypothesis provides many built-in strategies for generating test data:

```python
# Numbers
st.integers(min_value=0, max_value=100)  # Integers 0-100
st.floats(min_value=0, max_value=1)      # Floating point 0-1
st.decimals()                            # Decimal numbers

# Text and Binary
st.text()                                # Unicode strings
st.binary()                              # Binary data
st.characters()                          # Single characters

# Collections
st.lists(st.integers())                  # Lists of integers
st.sets(st.integers())                   # Sets of integers
st.dictionaries(st.text(), st.integers()) # Dictionaries

# Others
st.booleans()                           # True/False
st.datetimes()                          # DateTime objects
st.emails()                             # Email addresses
```

## 3. Composing Tests

### Filtering Values
Use `assume()` to filter out unwanted test cases:

```python
from hypothesis import given, assume
import hypothesis.strategies as st

@given(st.integers())
def test_sqrt_is_positive(x):
    assume(x >= 0)  # Only test non-negative numbers
    result = my_sqrt(x)
    assert result >= 0
```

### Combining Strategies
Create complex test data by combining simpler strategies:

```python
# Custom class strategy
class User:
    def __init__(self, name, age):
        self.name = name
        self.age = age

user_strategy = st.builds(
    User,
    name=st.text(min_size=1),
    age=st.integers(min_value=0, max_value=120)
)

@given(user_strategy)
def test_user_validation(user):
    assert validate_user(user)
```

## 4. Advanced Features

### Settings
Control test behavior using settings:

```python
from hypothesis import settings, given

@settings(max_examples=1000)  # Run more examples than default
@given(st.integers())
def test_with_more_examples(x):
    pass
```

### Custom Composite Strategies
Create reusable complex strategies using `@composite`:

```python
from hypothesis import strategies as st
from hypothesis.strategies import composite

@composite
def sorted_lists(draw):
    # Generate a list and sort it
    lst = draw(st.lists(st.integers()))
    return sorted(lst)

@given(sorted_lists())
def test_binary_search(sorted_list):
    # Test binary search on pre-sorted lists
    pass
```

## 5. Best Practices

1. **Keep Tests Focused**: Test one property at a time
2. **Use Appropriate Strategies**: Choose strategies that match your domain
3. **Handle Edge Cases**: Consider empty collections, None values, etc.
4. **Use Explicit Examples**: Add `@example()` for important cases
5. **Manage Test Performance**: Use appropriate settings for test runtime

## 6. Debugging Failed Tests

When Hypothesis finds a failing test, it will:
1. Show the minimal failing example
2. Print the seed for reproducibility
3. Save the example for future runs

Example of handling a failure:

```python
from hypothesis import given, example
import hypothesis.strategies as st

@given(st.lists(st.integers()))
@example([])  # Always test empty list
def test_list_processing(lst):
    result = process_list(lst)
    
    # If this fails, Hypothesis will show the minimal failing case
    assert len(result) >= len(lst)
```

## 7. Common Patterns

### Testing Properties
Test mathematical properties of your functions:

```python
@given(st.integers(), st.integers())
def test_addition_commutative(a, b):
    assert a + b == b + a

@given(st.lists(st.integers()))
def test_reverse_twice_is_identity(xs):
    assert reversed(reversed(xs)) == xs
```

### Testing Invariants
Verify that operations maintain important invariants:

```python
@given(st.lists(st.integers()))
def test_sort_maintains_length(lst):
    sorted_lst = sorted(lst)
    assert len(sorted_lst) == len(lst)
```

## Conclusion

Hypothesis is a powerful tool that can help you find bugs before they reach production. By generating test cases automatically and shrinking them to minimal failing examples, it makes it easier to write robust tests and fix issues quickly.

For more information:
- Read the [full documentation](https://hypothesis.readthedocs.io)
- Check the example database in `.hypothesis/examples/`
- Use the `--hypothesis-show-statistics` flag with pytest