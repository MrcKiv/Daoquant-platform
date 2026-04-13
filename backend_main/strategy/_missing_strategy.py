def missing_strategy(name):
    def _missing(*args, **kwargs):
        raise RuntimeError(
            f"Strategy '{name}' is not available in this deployment because its source file is missing."
        )

    return _missing


def unavailable_strategy(name, reason):
    message = f"Strategy '{name}' is not available in this deployment: {reason}"

    def _unavailable(*args, **kwargs):
        raise RuntimeError(message)

    return _unavailable
