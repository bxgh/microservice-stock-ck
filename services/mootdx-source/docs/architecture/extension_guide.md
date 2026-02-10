# Extending the Data Gateway

This guide outlines the steps to add a new data source or data type to the `mootdx-source` gateway.

## Step 1: Define Proto
Add the new `DataType` to `proto/datasource/v1/data_source.proto`.
```protobuf
enum DataType {
  DATA_TYPE_NEW_TYPE = 10;
}
```
Run `protoc` to regenerate Python code (or use built-in build scripts).

## Step 2: Update Enums
Add the type to `services/mootdx-source/src/ds_registry/enums.py`.
```python
class DataType(str, Enum):
    NEW_TYPE = "NEW_TYPE"
```

## Step 3: Implement Handler
Create a new handler in `services/mootdx-source/src/ds_registry/handlers/` or extend an existing one.
The handler should accept `codes` and `params`.

```python
class MyNewHandler:
    async def fetch_data(self, codes: List[str], params: Dict) -> pd.DataFrame:
        # Implementation...
        return df
```

## Step 4: Register Routing
Update `ROUTING_TABLE` in `services/mootdx-source/src/service.py`.

```python
DATA_TYPE_NEW_TYPE: RouteConfig(
    handler="_fetch_new_type_handler",
    source_name=DataSource.MY_SOURCE
),
```

## Step 5: Initialize Handler
In `MooTDXService.initialize`:
```python
self.my_handler = MyNewHandler(config)
await self.my_handler.initialize()
```

## Step 6: Add Validation
Add validation rules in `VALIDATION_RULES` in `service.py`.
```python
"NEW_TYPE": {
    "required_columns": ["code", "value"],
    "min_rows": 1
}
```

## Step 7: Verify
Create a test script using gRPC client to verify the new endpoint.
