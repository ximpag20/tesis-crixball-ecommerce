try:
    import resource
    RLIMIT_TYPE = resource.RLIMIT_DATA
except (ImportError, AttributeError):
    resource = None  # Windows no tiene módulo 'resource'
    RLIMIT_TYPE = None

from django.core.exceptions import ImproperlyConfigured


def is_soft_limit_set_without_hard_limit(soft_limit, hard_limit):
    return soft_limit is not None and hard_limit is None


def is_hard_limit_set_without_soft_limit(soft_limit, hard_limit):
    return hard_limit is not None and soft_limit is None


def validate_and_set_rlimit(soft_limit_in_MB, hard_limit_in_MB):
    """Set the memory limit for the process.

    This function sets the soft and hard memory limits for the process using
    the resource module. The limits are specified in megabytes (MB) and
    are converted to bytes before being set. If the limits are not specified,
    the function sets the limits to infinity (no limit).
    If the soft limit is reached, the process will raise a `MemoryError`.
    """
    
    # Si estamos en Windows, no hacer nada (resource no existe)
    if resource is None:
        return

    try:
        soft_limit_in_MB = int(soft_limit_in_MB) if soft_limit_in_MB else None
        hard_limit_in_MB = int(hard_limit_in_MB) if hard_limit_in_MB else None
    except ValueError as e:
        raise ImproperlyConfigured(
            "Memory limits must be integers(`SOFT_MEMORY_LIMIT_IN_MB` or `HARD_MEMORY_LIMIT_IN_MB`)."
        ) from e

    if is_soft_limit_set_without_hard_limit(
        soft_limit_in_MB, hard_limit_in_MB
    ) or is_hard_limit_set_without_soft_limit(soft_limit_in_MB, hard_limit_in_MB):
        raise ImproperlyConfigured(
            "Both `SOFT_MEMORY_LIMIT_IN_MB` and `HARD_MEMORY_LIMIT_IN_MB` must be set to enable memory limits."
        )

    soft_memory_limit = (
        soft_limit_in_MB * 1000 * 1000 if soft_limit_in_MB else resource.RLIM_INFINITY
    )
    hard_memory_limit = (
        hard_limit_in_MB * 1000 * 1000 if hard_limit_in_MB else resource.RLIM_INFINITY
    )
    if soft_memory_limit > hard_memory_limit:
        raise ImproperlyConfigured(
            "Soft memory limit cannot be greater than hard memory limit."
        )
    if soft_memory_limit < 0 and soft_memory_limit != resource.RLIM_INFINITY:
        raise ImproperlyConfigured(
            "Soft memory limit(SOFT_MEMORY_LIMIT_IN_MB) cannot be negative."
        )
    if hard_memory_limit < 0 and hard_memory_limit != resource.RLIM_INFINITY:
        raise ImproperlyConfigured(
            "Hard memory limit(HARD_MEMORY_LIMIT_IN_MB) cannot be negative."
        )

    resource.setrlimit(RLIMIT_TYPE, (soft_memory_limit, hard_memory_limit))