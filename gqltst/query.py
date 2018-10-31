import copy
from gqltst.reslovers import connection_first_resolver, connection_last_resolver
from collections import OrderedDict

class QueryData(object):
    def __init__(self):
        self.path = []
        self.variables = OrderedDict()

    def get_var_name(self, key, node):
        var_name = "$%s_%s" % ("_".join([a for a in self.path]), key)
        self.variables[var_name] = {
            "path": "_".join([a for a in self.path]),
            "node": node,
            "key": key
        }
        return var_name


class TestQuery(object):
    def __init__(self, query, query_data, schema_objects):
        self.query = query
        self.query_data = query_data
        self.schema_objects = schema_objects

    def get_query(self, scalars={}, args={}, validators={}):
        tested_object = self._get_object_by_path(self.query_data.path, self.schema_objects)
        for key, var in self.query_data.variables.items():
            path = self._get_path_from_key(key)

            var["resolver"] = None

            if tested_object.is_connection and tested_object.name == var["path"].split("_").pop():
                if var["key"] == "first":
                    var["resolver"] = connection_first_resolver
                elif var["key"] == "last":
                    var["resolver"] = connection_last_resolver

            if var["resolver"] is None:
                next_path = copy.deepcopy(path)
                next_path.append(var["key"])
                var["resolver"] = self._get_dict_by_path(next_path, args)

            if var["resolver"] is None:
                if var["node"].type in scalars.keys():
                    var["resolver"] = scalars[var["node"].type].resolve

            if var["resolver"] is None:
                raise Exception("Unknown resolver %s: %s" % (key, var["node"].type))

        for values in [r for r in self._get_variables(0)]:
            prepared_variables = {}
            i = 0
            for key, var in self.query_data.variables.items():
                if var["path"] not in prepared_variables.keys():
                    prepared_variables[var["path"]] = {}

                prepared_variables[var["path"]][key] = {
                    "value": values[i],
                    "key": var["key"],
                    "escaped": scalars[var["node"].type].escape(values[i])
                }
                i += 1

            yield "query{%s}" % self._prepare_query(prepared_variables), values

    def _prepare_query(self, variables):
        prepared_query = copy.deepcopy(self.query)
        for key, var in variables.items():
            value_list = []
            for varname, value in var.items():
                if value["value"] is not None:
                    value_list.append("%s: %s" % (value["key"], value["escaped"]))

            if len(value_list) > 0:
                prepared_query = prepared_query.replace("($%s)" % key, "(%s)" % (", ".join(value_list)))
            else:
                prepared_query = prepared_query.replace("($%s)" % key, "")

        return prepared_query

    def _get_variables(self, i, context={}):
        if "vars" not in context.keys():
            context["vars"] = OrderedDict()

        for res in list(self.query_data.variables.values())[i]["resolver"](context):
            context["vars"][list(self.query_data.variables.keys())[i]] = res
            if len(self.query_data.variables.values()) > i + 1:
                for r in self._get_variables(i+1, copy.deepcopy(context)):
                    if type(r) is list:
                        nr = [res]
                        nr.extend(r)
                        yield nr
                    else:
                        yield [res, r]
            else:
                yield [res]

    def _get_path_from_key(self, key):
        return key[1:].split("_")[:-1]

    def _get_dict_by_path(self, path, obj):
        key = path.pop(0)

        if key in obj.keys():
            obj = obj[key]

            while key is not None and len(path) > 0:
                key = path.pop(0)
                if key in obj.keys():
                    obj = obj[key]
                else:
                    return None

            return obj
        else:
            return None

    def _get_object_by_path(self, path, obj):
        key = path.pop(0)

        if key in obj.keys():
            obj = obj[key]

            while key is not None and len(path) > 0:
                key = path.pop(0)
                if key in obj.fields.keys():
                    obj = obj.fields[key]
                else:
                    return None

            return obj
        else:
            return None