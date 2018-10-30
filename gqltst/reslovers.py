import random

def connection_first_resolver(context):
    for i in [None, random.randint(1, 5)]:
        yield i

def connection_last_resolver(context):
    if list(context["vars"].keys()).pop()[-5:] == "first":
        if context["vars"][list(context["vars"].keys()).pop()] is None:
            yield random.randint(1, 5)

    yield None
