import random
import uuid
from datetime import datetime, timedelta


class BaseResolver(object):
    def resolve(self, context):
        pass

    def escape(self, value):
        pass

    def validate(self, data):
        return False


class StringResolver(BaseResolver):
    def resolve(self, context):
        for r in ["1111a"]:
            yield r

    def escape(self, value):
        return "\"%s\"" % (str(value))

    def validate(self, data):
        if data is None:
            return True

        return type(data) == str


class DateTimeResolver(BaseResolver):
    def resolve(self, context):
        now_date = datetime.now()
        for r in [(now_date - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S"),
                  (now_date - timedelta(days=2)).strftime("%Y-%m-%d %H:%M:%S")]:
            yield r

    def escape(self, value):
        return "\"%s\"" % (str(value))

    def validate(self, data):
        if data is None:
            return True

        return type(data) == str


class IntResolver(BaseResolver):
    def resolve(self, context):
        yield random.randint(1, 10)

    def escape(self, value):
        if value is not None:
            return int(value)
        return value

    def validate(self, data):
        if data is None:
            return True

        return type(data) == int


class FloatResolver(BaseResolver):
    def resolve(self, context):
        yield random.randint(1, 10)

    def escape(self, value):
        return float(value)

    def validate(self, data):
        if data is None:
            return True

        return type(data) == float


class BooleanResolver(BaseResolver):
    def resolve(self, context):
        yield random.choice([True, False])

    def escape(self, value):
        if value:
            return "true"
        else:
            return "false"

    def validate(self, data):
        return type(data) == bool


class ValidationResult(object):
    def __init__(self, error=None, node=None, data=None):
        if error is None:
            self.success = True
            self.error = None
        else:
            self.success = False
            self.error = error

        self.node = node
        self.data = data

    def __str__(self):
        return "%s" % (str(self.error))

SCALAR_TYPES = {
    "String": StringResolver,
    "DateTime": DateTimeResolver,
    "Boolean": BooleanResolver,
    "Float": FloatResolver,
    "Int": IntResolver,
}