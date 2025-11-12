# Coding Standards

## Critical Fullstack Rules

- **Type Sharing:** Always define types in packages/shared and import from there
- **API Calls:** Never make direct HTTP calls - use the service layer
- **Environment Variables:** Access only through config objects, never process.env directly
- **Error Handling:** All API routes must use the standard error handler
- **State Updates:** Never mutate state directly - use proper state management patterns
- **Database Transactions:** Always use database transactions for multi-table operations
- **Logging:** Use structured JSON logging with consistent format across all services
- **Docker Images:** Always use specific version tags, never 'latest' in production

## Naming Conventions

| Element | Frontend | Backend | Example |
|---------|----------|---------|---------|
| Components | PascalCase | - | `UserProfile.tsx` |
| Hooks | camelCase with 'use' | - | `useAuth.ts` |
| API Routes | - | kebab-case | `/api/user-profile` |
| Database Tables | - | snake_case | `user_profiles` |
| Environment Variables | UPPER_SNAKE_CASE | UPPER_SNAKE_CASE | `DATABASE_URL` |
| Functions | camelCase | snake_case | `getUserData()` / `get_user_data()` |
