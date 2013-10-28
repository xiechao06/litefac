#-*- coding:utf-8 -*-
from collections import deque


class Notification(object):

    __slots__ = "dictionary",

    __maxsize__ = 5

    def __init__(self, *args, **kwargs):
        self.dictionary = {}
        if kwargs.has_key("maxsize"):
            self.__maxsize__ = int(kwargs.get("maxsize"))

    def delete(self, key):
        """Deletes the `key` from the dictionary."""
        if key in self.dictionary:
            del self.dictionary[key]
            return 1
        return 0

    def add(self, key, val):
        q = self.dictionary.setdefault(key , deque(maxlen=self.__maxsize__))
        q.appendleft(val)
        return 1

    def pop(self, key):
        """Retrieves a value of the `key` from the internal dictionary."""
        try:
            q = self.dictionary.pop(key)
            return list(q)
        except KeyError:
            return []

    def __repr__(self):
        modname = "" if __name__ == "__main__" else __name__ + "."
        return "<%s %r>" % (modname, self.dictionary)

notifications = Notification()
