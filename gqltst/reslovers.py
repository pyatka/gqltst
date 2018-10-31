import random
from datetime import datetime, timedelta

def connection_first_resolver(context):
    for i in [None, random.randint(1, 5)]:
        yield i

def connection_last_resolver(context):
    if list(context["vars"].keys()).pop()[-5:] == "first":
        if context["vars"][list(context["vars"].keys()).pop()] is None:
            yield random.randint(1, 5)

    yield None

def range_resolver(range=[]):
    def func(context):
        for i in range:
            yield i
    return func

def depend_resolver(key, value, match_range=[], un_match_range=[]):
    def func(context):
        if key not in context["vars"].keys():
            raise Exception("Disturbed arguments order")

        if context["vars"][key] == value:
            for i in match_range:
                yield i
        else:
            for i in un_match_range:
                yield i
    return func

def days_ago_resolver(days):
    def func(context):
        now_date = datetime.now()
        for r in [(now_date - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")]:
            yield r
    return func