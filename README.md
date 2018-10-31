# gqltst  
Framework for automatic GraphQL testing. The framework takes url of your GraphQL endpoint, builds schema and generates http queries for testing.
 
![Example](example.png)

# Installation

    pip3 install gqltst
    
# Usage
Prepare your schema
```python
    import gqltst
    schema = gqltst.Schema("https://example.com")
```
There're already prepared resolvers for Integer, String, Boolean, DateTime and Float, but you can register own resolver for your scalars.
```python
    from gqltst.types import BaseResolver
    
    class YourResolver(BaseResolver):  
	    def resolve(self, context):  
	        yield "Hello world"
	  
	    def escape(self, value):  
	        return "\"%s\"" % (str(value))  
	  
	    def validate(self, data):  
	        return type(data) == int 
	        
    schema.register_scalar("Myscalar", YourResolver)
```
Start test with own parameter resolvers
```python
    from gqltst.reslovers import range_resolver, depend_resolver
    from datetime import datetime, timedelta
    from gqltst.types import ValidationResult
    
    def date_resolver(context):
        now_date = datetime.now()
        for generated_date in [(now_date - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S"),
                                (now_date - timedelta(days=2)).strftime("%Y-%m-%d %H:%M:%S")]:
            yield generated_date
    
    args = {
        "environment": {
            "token": range_resolver(["token1", "token2"]),
            "search": {
                "items": {
                    "name": range_resolver(["name1", None, "name3"]),
                    "surname": depend_resolver("$environment_search_items_name", None, ["A", "B"], [None]),
                    "dateFrom": date_resolver,
                    "records": {
                        "first": range_resolver([0]),
                        "step": range_resolver([1]),
                    }
                }
            }
        }
    }
    
    def test_validator(data, node):
        if data == "Paul":
            return [ValidationResult("It's not our manager", node, data))]
        else:
            return []
    
    validators = {
        "environment.items.surname": [
            test_validator,
        ],
    }
    
    schema.test(args=args, validators=validators)
```
