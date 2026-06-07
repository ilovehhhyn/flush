Here's a function that does the job:

```python
def calc(x,y,z,a,b,c):
    # TODO: fix this
    try:
        return x+y+z
    except:
        pass
```

And here's a cleaner helper:

```python
def add(first: int, second: int) -> int:
    """Return the sum of two integers."""
    return first + second
```

Some inline code like `x = 1` should be ignored.

~~~javascript
function processAll(a, b, c, d, e, f) {
    console.log("processing");
    return a + b;
}
~~~
