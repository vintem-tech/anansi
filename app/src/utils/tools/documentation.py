# pylint:disable=missing-function-docstring
# pylint:disable=missing-module-docstring

from functools import wraps


class DocInherit:
    """Docstring inheriting method descriptor; the class itself is
    also used as a decorator. See reference at:
    <http://code.activestate.com/recipes/576862/>
    """

    def __init__(self, method):
        self.method = method
        self.name = method.__name__

    def get_with_instance(self, obj, cls):
        overridden = getattr(super(cls, obj), self.name, None)

        @wraps(self.method, assigned=("__name__", "__module__"))
        def function_(*args, **kwargs):
            return self.method(obj, *args, **kwargs)

        return self.use_parent_doc(function_, overridden)

    def get_no_instance(self, cls):
        for parent in cls.__mro__[1:]:
            overridden = getattr(parent, self.name, None)
            if overridden:
                break

        @wraps(self.method, assigned=("__name__", "__module__"))
        def function_(*args, **kwargs):
            return self.method(*args, **kwargs)

        return self.use_parent_doc(function_, overridden)

    def __get__(self, obj, cls):
        if obj:
            return self.get_with_instance(obj, cls)
        return self.get_no_instance(cls)

    def use_parent_doc(self, func, source):
        if source is None:
            raise NameError("Can't find {} in parents".format(self.name))
        func.__doc__ = source.__doc__
        return func
