import requests
import copy
import json

from collections import OrderedDict
from gqltst.types import SCALAR_TYPES
from gqltst.reslovers import enum_resolver, input_object_resolver

TYPES_CACHE = {}
structure_query = """query IntrospectionQuery{__schema{types{kindenumValues{name},name,fields(includeDeprecated: false) {name,args {name,type { ...TypeRef }defaultValue}, type { ...TypeRef }}}}} fragment TypeRef on __Type {kind,name,interfaces{name,enumValues{name,}},ofType {kind,name,interfaces{name,enumValues{name,}},ofType {kind,name,ofType {kind,name,ofType {kind,name,ofType {kind, name,ofType {kind,name,ofType {kind,name,}}}}}}}}"""


class QueryInfo(object):
    def __init__(self, resolvers):
        self.path = []
        self.variables = OrderedDict()
        self.resolvers = resolvers

    def add_to_path(self, obj):
        self.path.append(obj)

        key = [p.name for p in self.path]
        if len(obj.args.keys()) > 0:
            self.variables[".".join(key)] = copy.deepcopy(obj.args)
            for _, arg in self.variables[".".join(key)].items():
                arg.resolver = arg.prepare_resolver(copy.deepcopy(key), self.resolvers)

    def get_query(self):
        result_query = ""
        for item in reversed(self.path):
            if result_query == "":
                result_query = item.get_query()
            else:
                result_query = "%s{%s}" % (item.name, result_query)

        return result_query

    def __str__(self):
        return " -> ".join([str(obj) for obj in self.path])


class GqlScalar(object):
    def __init__(self):
        self.non_null = False
        self.is_list = False
        self.is_enum = False
        self.kind = None
        self.name = None

    def __str__(self):
        output = "%s: %s" % (self.name, self.kind)

        if self.is_list:
            output = "LIST of %s" % output

        if self.non_null:
            output = "%s NON NULL" % output

        return output


class GqlObject(object):
    def parse_type(self, data, scalar=None):
        if scalar is None:
            scalar = GqlScalar()

        if data["kind"] == "NON_NULL":
            scalar.non_null = True
        elif data["kind"] == "LIST":
            scalar.is_list = True
        elif data["kind"] == "ENUM":
            scalar.is_enum = True
            scalar.name = data["name"]
            scalar.kind = data["kind"]
        elif data["kind"] in ["OBJECT", "SCALAR", "INTERFACE", "INPUT_OBJECT", "UNION"]:
            scalar.name = data["name"]
            scalar.kind = data["kind"]

        if data["ofType"] is not None:
            return self.parse_type(data["ofType"], scalar)
        else:
            return scalar

    def get_type_object(self, otype):
        if otype.name in TYPES_CACHE.keys():
            return TYPES_CACHE[otype.name]
        else:
            raise Exception("Fail to found type %s" % str(otype))

    def get_dict_value(self, data, path):
        key = path.pop(0)
        if key in data.keys():
            if type(data[key]) == dict:
                return self.get_dict_value(data[key], path)
            else:
                return data[key]
        else:
            return None

    def __str__(self):
        return "%s" % self.name



class GqlEnumValue(GqlObject):
    def __init__(self, data):
        self.name = data["name"]
        self.description = data["description"]
        self.is_deprecated = data["isDeprecated"]
        self.deprecation_reason = data["deprecationReason"]


class GqlInputField(GqlObject):
    def __init__(self, data):
        self.name = data["name"]
        self.description = data["description"]
        self.default_value = data["defaultValue"]

        self.type = None
        if "type" in data.keys() and data["type"] is not None:
            self.type = self.parse_type(data["type"])


class GqlInterface(GqlObject):
    def __init__(self, data):
        self.kind = data["kind"]
        self.name = data["name"]

        self.type = None
        if "type" in data.keys() and data["type"] is not None:
            self.type = self.parse_type(data["type"])


class GqlArgument(GqlObject):
    def __init__(self, data):
        self.name = data["name"]
        self.description = data["description"]
        self.default_value = data["defaultValue"]
        self.resolver = None

        self.type = None
        if "type" in data.keys() and data["type"] is not None:
            self.type = self.parse_type(data["type"])

    def prepare_resolver(self, path, resolvers, obj_type=None):
        if obj_type is None:
            obj_type = self.type

        resolver = self.get_dict_value(resolvers, path)
        if resolver is None:
            if obj_type.kind == "SCALAR":
                resolver = self.get_scalar_resolver(obj_type)
            elif obj_type.kind == "ENUM":
                resolver = enum_resolver(TYPES_CACHE[obj_type.name].enum_values, obj_type.is_list, obj_type.non_null)
            elif obj_type.kind == "INPUT_OBJECT":
                input_data = OrderedDict()
                for ifld in TYPES_CACHE[obj_type.name].input_fields.values():
                    ifld_path = copy.deepcopy(path)
                    ifld_path.append(ifld.name)

                    input_data[ifld.name] = self.get_dict_value(resolvers, ifld_path)
                    if input_data[ifld.name] is None:
                        input_data[ifld.name] = self.prepare_resolver(ifld_path, resolvers, ifld.type)

                resolver = input_object_resolver(input_data)

        if resolver is None:
            raise Exception("NULL resolver %s.%s" % (".".join(path), self.name))

        return resolver

    def get_scalar_resolver(self, scalar_type):
        if scalar_type.name in SCALAR_TYPES.keys():
            return SCALAR_TYPES[scalar_type.name].resolve
        else:
            raise Exception("Unknown scalar %s" % scalar_type.name)

    def __str__(self):
        output = "%s" % self.name

        if self.type is not None:
            output = "%s [%s]" % (output, str(self.type))

        return output


class GqlInputField(GqlObject):
    def __init__(self, data):
        self.name = data["name"]
        self.description = data["description"]
        self.default_value = data["defaultValue"]

        self.type = None
        if "type" in data.keys() and data["type"] is not None:
            self.type = self.parse_type(data["type"])


class GqlField(GqlObject):
    def __init__(self, data):
        self.name = data["name"]
        self.description = data["description"]
        self.is_deprecated = data["isDeprecated"]
        self.deprecation_reason = data["deprecationReason"]

        self.args = OrderedDict()
        if "args" in data.keys() and data["args"] is not None:
            for arg in data["args"]:
                self.args[arg["name"]] = GqlArgument(arg)

        self.type = None
        if "type" in data.keys() and data["type"] is not None:
            self.type = self.parse_type(data["type"])

    def prepare_queries(self, resolvers={}, query_info=None):
        if query_info is None:
            query_info = QueryInfo(resolvers)
            query_info.add_to_path(self)
        else:
            query_info.add_to_path(self)

        need_to_own_quering = False
        subqueries = []
        for key, field in self.get_type_object(self.type).fields.items():
            if not field.is_argumented():
                if not self.get_type_object(field.type).has_argumented_fields():
                    need_to_own_quering = True
            else:
                subqueries.extend(field.prepare_queries(resolvers, copy.deepcopy(query_info)))

        if need_to_own_quering:
            subqueries.append(query_info)

        return subqueries

    def is_argumented(self):
        return len(self.args.keys()) > 0

    def get_query(self):
        return self.name

    def __str__(self, tab=0):
        output = "%s" % self.name

        if len(self.args.keys()) > 0:
            output = "%s (%s)" % (output, ", ".join([str(a) for a in self.args.values()]))

        if self.type is not None:
            output = "%s [%s]" % (output, str(self.type))

        return output

class GqlType(GqlObject):
    def __init__(self, data):
        self.name = data["name"]
        self.kind = data["kind"]

        self.enum_values = {}
        if "enumValues" in data.keys() and data["enumValues"] is not None:
            for ev in data["enumValues"]:
                self.enum_values[ev["name"]] = GqlEnumValue(ev)

        self.description = None
        if "description" in data.keys():
            self.description = data["description"]

        self.possible_types = []
        if "possibleTypes" in data.keys() and data["possibleTypes"] is not None:
            for pt in data["possibleTypes"]:
                self.possible_types.append(GqlType(pt))

        self.interfaces = []
        if "interfaces" in data.keys() and data["interfaces"] is not None:
            for interface in data["interfaces"]:
                self.possible_types.append(GqlInterface(interface))

        self.fields = OrderedDict()
        if "fields" in data.keys() and data["fields"] is not None:
            for field in data["fields"]:
                self.fields[field["name"]] = GqlField(field)

        self.input_fields = OrderedDict()
        if "inputFields" in data.keys() and data["inputFields"] is not None:
            for ifield in data["inputFields"]:
                self.input_fields[ifield["name"]] = GqlInputField(ifield)

        self.args = OrderedDict()
        if "args" in data.keys() and data["args"] is not None:
            for arg in data["args"]:
                self.args[arg["name"]] = GqlArgument(arg)

    def has_argumented_fields(self):
        for _, field in self.fields.items():
            if field.is_argumented():
                return True
            else:
                return self.get_type_object(field.type).has_argumented_fields()

        return False

    def __str__(self, tab=0):
        output = self.name

        if len(self.args.keys()) > 0:
            output = "%s(%s)" % (output, ", ".join([str(a) for a in self.args.values()]))

        if len(self.fields.keys()) > 0:
            output = "%s%s" % (output, ("\r\n  %s" % ("  " * tab)).join([str(f) for f in self.fields.values()]))

        return output


class TestProposition(object):
    def __init__(self):
        self.position = 0
        self.values = OrderedDict()

    def set_value(self, resolver_dict, value):
        if resolver_dict["key"] not in self.values.keys():
            self.values[resolver_dict["key"]] = OrderedDict()

        self.values[resolver_dict["key"]][resolver_dict["name"]] = value

    def __str__(self):
        return " -> ".join([k for k in self.values.keys()])


class Schema(object):
    def __init__(self, url, headers={}):
        self.url = url
        self.headers = headers

        self.queries = []

        print("Requesting structure...", end='\r', flush=True)
        structure = requests.get(self.url, headers=self.headers, params={"query": structure_query})
        print("Building caches...", end='\r', flush=True)

        if structure.status_code == 200:
            for d in structure.json()["data"]["__schema"]["types"]:
                TYPES_CACHE[d["name"]] = GqlType(d)
        else:
            print(structure.status_code)

        print("Initialization done!", end='\r', flush=True)

    def register_scalar(self, name, resolver):
        SCALAR_TYPES[name] = resolver

    def prepare_queries(self, resolvers={}):
        for key, obj in TYPES_CACHE["Query"].fields.items():
            for qi in obj.prepare_queries(resolvers):
                self.queries.append(qi)

    def calculate_query_values(self, resolvers_list={}, proposition=None):
        if proposition is None:
            resolver = resolvers_list[list(resolvers_list.keys())[0]]
            proposition = TestProposition()
        else:
            resolver = resolvers_list[list(resolvers_list.keys())[proposition.position]]

        result = []

        for value in resolver["obj"].resolver(proposition):
            new_proposition = copy.deepcopy(proposition)
            new_proposition.set_value(resolver, value)
            if len(resolvers_list) > new_proposition.position + 1:
                new_proposition.position += 1
                result.extend(self.calculate_query_values(resolvers_list, new_proposition))
            else:
                result.append(new_proposition)

        return result

    def test(self):
        for query_info in self.queries:
            resolvers_list = OrderedDict()
            for key, var in query_info.variables.items():
                for vname, v in var.items():
                    resolvers_list["%s.%s" % (key, vname)] = {
                        "key": key,
                        "name": vname,
                        "obj": v,
                    }

            if len(resolvers_list.keys()) > 0:
                print([str(p) for p in self.calculate_query_values(resolvers_list)])
            else:
                print("!!!!!", query_info)
