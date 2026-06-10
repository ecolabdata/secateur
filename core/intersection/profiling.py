from time import perf_counter


def timed_call(
    func,
    *args,
    **kwargs,
):
    start = perf_counter()

    result = func(
        *args,
        **kwargs,
    )

    return result, perf_counter() - start
