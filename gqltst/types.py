import random
import uuid
from datetime import datetime, timedelta


class BaseResolver(object):
    def resolve(self, context):
        pass

    def escape(self, value):
        pass

    def validate(self, data):
        print(data)
        return True


class StringResolver(BaseResolver):
    def resolve(self, context):
        for r in ["1111a"]:
            yield r

    def escape(self, value):
        return "\"%s\"" % (str(value))


class DateTimeResolver(BaseResolver):
    def resolve(self, context):
        now_date = datetime.now()
        for r in [(now_date - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S"),
                  (now_date - timedelta(days=2)).strftime("%Y-%m-%d %H:%M:%S")]:
            yield r

    def escape(self, value):
        return "\"%s\"" % (str(value))


class IntResolver(BaseResolver):
    def resolve(self, context):
        yield random.randint(1, 10)

    def escape(self, value):
        return int(value)


class BooleanResolver(BaseResolver):
    def resolve(self, context):
        yield random.choice([True, False])

    def escape(self, value):
        if value:
            return "true"
        else:
            return "false"

SCALAR_TYPES = {
    "String": StringResolver,
    "DateTime": DateTimeResolver,
    "Boolean": BooleanResolver,
    "Int": IntResolver,
}