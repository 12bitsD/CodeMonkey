# Design: Unify Edge Field Names to from/to

## Summary
Unify the `Edge` field names from `from_node`/`to_node` to `from`/`to` in the backend API to match the frontend's internal usage. This will simplify the frontend's API layer and ensure consistency across the stack.

## Approaches Considered

### Approach 1: Use Pydantic Aliases for Serialization (Recommended)
- **Backend**: Rename `from_node` and `to_node` in `Edge` and `GraphEdge` models to `from_` and `to_` (to avoid keyword conflict). Use `Field(alias="from", serialization_alias="from")` and `Field(alias="to", serialization_alias="to")`.
- **Backend Routers**: Update `get_graph`, `create_plan`, `recommend_next`, etc., to use the new field names.
- **Frontend**: Remove `mapEdgesFromBackend` and `mapEdgesToBackend` logic (or simplify it to a pass-through).
- **Pros**: Cleanest API for the frontend, follows Pydantic best practices.
- **Cons**: Requires updating all backend references to the field names.

### Approach 2: Use FastAPI `response_model_by_alias=True`
- **Backend**: Keep the current `Edge` model with `from_node: str = Field(alias="from")`.
- **Backend Routers**: Add `response_model_by_alias=True` to all relevant route decorators.
- **Frontend**: Same as Approach 1.
- **Pros**: Minimal changes to the backend models.
- **Cons**: Easy to forget to add the parameter to new routes.

## Selected Design: Approach 1

### Backend Changes

#### `models.py`
Update `Edge` and `GraphEdge` models:
```python
class Edge(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    from_: str = Field(alias="from", serialization_alias="from")
    to_: str = Field(alias="to", serialization_alias="to")

class GraphEdge(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    from_: str = Field(alias="from", serialization_alias="from")
    to_: str = Field(alias="to", serialization_alias="to")
```

#### `routers/graph.py`
Update `get_graph` to use the new field names if necessary (though it currently returns a dict).

#### `routers/plans.py`
Update `create_plan` to use `edge.from_` and `edge.to_`.

#### `routers/ai.py`
Update `recommend_next` to use `from_` and `to_` keys in the graph dictionary.

### Frontend Changes

#### `services/api.js`
Simplify `mapEdgesFromBackend` and `mapEdgesToBackend` to just return the edges as-is.

## Success Criteria
- Backend API returns `from` and `to` in JSON for all edge-related endpoints.
- Frontend can correctly parse the edges without complex mapping.
- All existing functionality (creating plans, generating graphs, recommending next nodes) remains intact.
