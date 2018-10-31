import requests
import copy
import json
from gqltst.query import TestQuery, QueryData
from gqltst.types import SCALAR_TYPES, ValidationResult

structure_query = """
query IntrospectionQuery {
  __schema {
    types {
      kind
      enumValues{
        name
      }
      name
      fields(includeDeprecated: false) {
        name
        args {
          name
          type {
            ...TypeRef
          }
          defaultValue
        }
        type {
          ...TypeRef
        }
      }
    }
  }
}

fragment TypeRef on __Type {
  kind
  name
  interfaces{
    name,
    enumValues{
      name
    }
  }
  ofType {
    kind
    name
    interfaces{
    name,
      enumValues{
        name
      }
    }
    ofType {
      kind
      name
      ofType {
        kind
        name
        ofType {
          kind
          name
          ofType {
            kind
            name
            ofType {
              kind
              name
              ofType {
                kind
                name
              }
            }
          }
        }
      }
    }
  }
}
"""


class Node(object):
    def __init__(self, path=[]):
        self.path = path
        self.fields = {}
        self.args = {}
        self.name = ""
        self.type = ""
        self.kind = ""
        self.non_null = False
        self.is_list = False
        self.is_connection = False

    def validate(self, data, scalars={}, validators={}):
        validation_result = []

        if self.is_list:
            if type(data) is not list:
                validation_result = [ValidationResult("Field %s must be list" % (self.name), self, data)]
            else:
                errors = []

                self.is_list = False
                for d in data:
                    validation_result = self.validate(d, scalars, validators)
                    if len(validation_result) > 0:
                        errors.extend(validation_result)
                self.is_list = True
                validation_result = errors
        else:
            if self.kind == "SCALAR":
                if scalars[self.type].validate(data):
                    validation_result = []
                else:
                    validation_result = [ValidationResult("Field %s: %s type validation error, received data: %s" % (self.name, self.type, data), self, data)]
            else:
                errors = []

                if data is None:
                    if self.non_null:
                        errors.append(ValidationResult("Field %s: %s must not be NULL" % (self.name, self.type), self, data))
                else:
                    for key, item in data.items():
                        validation_result = self.fields[key].validate(item, scalars, validators)
                        if len(validation_result) > 0:
                            errors.extend(validation_result)

                validation_result = errors

        if ".".join(self.path) in validators.keys():
            for func in validators[".".join(self.path)]:
                validation_result.extend(func(data, self))

        return validation_result

    def get_query(self, query_data=None):
        if query_data is None:
            query_data = QueryData()

        query_data.path.append(self.name)

        field_query = self.name

        if len(self.args.keys()) > 0:
            [query_data.get_var_name(k, a) for k, a in self.args.items()]
            field_query = "%s(%s)" % (field_query, "$%s" % "_".join(query_data.path))

        if len(self.fields.keys()) > 0:
            static_fields = []

            for key, field in self.fields.items():
                if field.name != "ID":
                    if len(field.args.keys()) > 0:
                        for sfq, resulted_query_data in field.get_query(copy.deepcopy(query_data)):
                            yield "%s{%s}" % (field_query, sfq), resulted_query_data
                    else:
                        if not field.has_argumented_child():
                            for sfq, resulted_query_data in field.get_query(copy.deepcopy(query_data)):
                                static_fields.append(sfq)
                        else:
                            for sfq, resulted_query_data in field.get_query(copy.deepcopy(query_data)):
                                yield "%s{%s}" % (field_query, sfq), resulted_query_data

            if len(static_fields) > 0:
                yield "%s{%s}" % (field_query, ",".join(static_fields)), query_data
        else:
            yield field_query, query_data

    def has_argumented_child(self):
        if len(self.args.keys()) > 0:
            return True

        for _, field in self.fields.items():
            if len(field.fields.keys()) > 0:
                if len(field.args.keys()) > 0:
                    return True

            if field.has_argumented_child():
                return True
        return False

    def __str__(self, iteration=1, is_arg=False):
        otype = "%s | %s" % (self.type, self.kind)

        if self.is_list:
            otype = "list of %s" % otype

        if self.non_null:
            otype = "%s (NOT NULL)" % otype

        args = ", ".join([a.__str__(1, True) for k, a in self.args.items()])

        if is_arg:
            return "%s: %s | %s" % (self.name, otype, self.kind)
        else:
            return "%s\r\n%s" % ("%s (%s) : %s" % (self.name, args, otype), "".join(["%s%s" % ("    " * iteration, f.__str__(iteration + 1)) for k, f in self.fields.items()]))


def node_from_data(data, types_cache, path=[]):
    new_node = Node(path)
    object_data = None

    if data["type"]["kind"] == "OBJECT":
        object_data = types_cache[data["type"]["name"]]
    elif data["type"]["kind"] == "NON_NULL":
        new_node.non_null = True
        if data["type"]["ofType"]["kind"] == "LIST":
            new_node.is_list = True
            object_data = types_cache[data["type"]["ofType"]["ofType"]["name"]]
        else:
            object_data = types_cache[data["type"]["ofType"]["name"]]
    elif data["type"]["kind"] == "SCALAR":
        object_data = types_cache[data["type"]["name"]]
    elif data["type"]["kind"] == "LIST":
        new_node.is_list = True
        object_data = types_cache[data["type"]["ofType"]["name"]]

    new_node.name = data["name"]
    new_node.kind = object_data["kind"]
    new_node.type = object_data["name"]
    new_node.path.append(new_node.name)

    if "args" in data.keys() and data["args"] is not None:
        is_connection = "fields" in object_data.keys() and object_data["fields"] is not None and "pageInfo" in [f["name"] for f in object_data["fields"]]

        new_node.is_connection = is_connection

        for arg in data["args"]:
            if is_connection and arg["name"] in ["before", "after"]:
                pass
            else:
                new_node.args[arg["name"]] = node_from_data(arg, types_cache, copy.deepcopy(new_node.path))

    if "fields" in object_data.keys() and object_data["fields"] is not None:
        for field in object_data["fields"]:
            if field["name"] == "id" and field["type"]["ofType"]["name"] == "ID":
                pass
            else:
                new_node.fields[field["name"]] = node_from_data(field, types_cache, copy.deepcopy(new_node.path))

    return new_node


class Schema(object):
    def __init__(self, url):
        self.url = url

        print("Requesting structure...", end='\r', flush=True)
        structure = requests.get(self.url, params={"query": structure_query})
        print("Building caches...", end='\r', flush=True)

        types_cache = {}
        self.schema_objects = {}

        self.test_queries = []
        self.scalars = {}

        if structure.status_code == 200:
            for d in structure.json()["data"]["__schema"]["types"]:
                types_cache[d["name"]] = d

            for obj in types_cache["Query"]["fields"]:
                self.schema_objects[obj["name"]] = node_from_data(obj, types_cache)

        del types_cache

        for type_name, class_obj in SCALAR_TYPES.items():
            self.register_scalar(type_name, class_obj)

        print("Initialization done!", end='\r', flush=True)

    def register_scalar(self, name, resolver):
        self.scalars[name] = resolver()

    def prepare_test_queries(self):
        self.test_queries = []
        for _, obj in self.schema_objects.items():
            for query, data in obj.get_query():
                self.test_queries.append(TestQuery(query, data, self.schema_objects))

    def test(self, args={}, validators={}):
        test_save_data = {
            "url": self.url,
            "tests": [],
        }
        self.prepare_test_queries()
        for test in self.test_queries:
            test_query_path = ".".join(test.query_data.path)
            test_data = {
                "path": test_query_path,
                "queries": [],
            }
            print("Test %s" % (test_query_path), end='\r', flush=True)
            test_iteration = 0
            failed_tests = 0
            response_time = []
            for query, values in test.get_query(self.scalars, args=args, validators=validators):
                test_iteration += 1
                result = requests.get(self.url, params={"query": query})
                response_time.append(result.elapsed.total_seconds())
                errors = []
                if result.status_code == 200:
                    response_data = result.json()
                    errors = self.validate_response(response_data["data"], validators)

                    if len(errors) > 0:
                        failed_tests += 1

                    if failed_tests > 0:
                        print("Test %s (%s/%s) [%0.2fs] - FAIL" % (test_query_path, failed_tests, test_iteration, sum(response_time)/len(response_time)), end='\r',
                              flush=True)
                    else:
                        print("Test %s (0/%s) [%0.2fs]" % (test_query_path, test_iteration, sum(response_time)/len(response_time)), end='\r', flush=True)
                else:
                    failed_tests += 1
                    print("Test %s (%s/%s) [%0.2fs] - FAIL" % (test_query_path, failed_tests, test_iteration, sum(response_time)/len(response_time)), end='\r',
                          flush=True)

                test_query_data = {
                    "query": query,
                    "values": values,
                    "errors": [str(r) for r in errors],
                    "response": {
                        "code": result.status_code,
                        "data": None,
                    },
                    "time": result.elapsed.total_seconds(),
                }

                try:
                    test_query_data["response"]["data"] = result.text
                except:
                    pass

                test_data["queries"].append(test_query_data)

            test_data["failed"] = failed_tests
            test_data["total"] = test_iteration
            test_data["time"] = {
                "total": sum(response_time),
                "average": sum(response_time)/len(response_time),
            }

            test_save_data["tests"].append(test_data)

            if failed_tests > 0:
                print("Test %s (%s/%s) [average %0.2fs / total %0.2fs] - FAIL" % (test_query_path, test_iteration - failed_tests, test_iteration, sum(response_time)/len(response_time), sum(response_time)))
            else:
                print("Test %s (%s/%s) [average %0.2fs / total %0.2fs] - DONE" % (test_query_path, test_iteration, test_iteration, sum(response_time)/len(response_time), sum(response_time)))

        with open("result.json", "w") as rf:
            rf.write(json.dumps(test_save_data))

        print("Check results in result.json")

    def validate_response(self, response_data, validators):
        for key in response_data.keys():
            tested_obj = self.schema_objects[key]
            return tested_obj.validate(response_data[key], self.scalars, validators)
