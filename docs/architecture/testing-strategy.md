# Testing Strategy

## Testing Pyramid

```
E2E Tests (10%)
/        \
Integration Tests (20%)
/            \
Frontend Unit (35%)  Backend Unit (35%)
```

## Test Organization

**Frontend Tests:**
```
services/web-ui/src/
├── components/__tests__/
├── hooks/__tests__/
└── services/__tests__/
```

**Backend Tests:**
```
services/task-scheduler/src/
├── routes/__tests__/
├── services/__tests__/
└── models/__tests__/
```
