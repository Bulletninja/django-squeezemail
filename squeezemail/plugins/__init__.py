try:
    import feincms_cleanse
except ImportError:  # pragma: no cover
    pass
else:
    from .richtext import *