from time import perf_counter


def timed_call(
    func,
    *args,
    **kwargs,
):
    """Call *func* with the given arguments and measure its execution time.

    Returns:
        A tuple of (the return value of ``func``, elapsed time in seconds).
    """
    start = perf_counter()

    result = func(
        *args,
        **kwargs,
    )

    return result, perf_counter() - start
