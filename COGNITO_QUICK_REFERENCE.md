# Cognito Quick Reference - IdentityServer4 Integration

## Key Findings

### Current Cognito Configuration
- **User Pool ID**: us-east-2_HJtK36MHO
- **App Client ID**: 7s84oe77h699j77oc6m8cbvogt
- **Identity Pool ID**: us-east-2:c0f78434-f184-465f-8adb-ff2675227da2
- **Domain**: pdf-ui-auth1rc16k
- **API Gateway**: https://6597iy1nhi.execute-api.us-east-2.amazonaws.com/prod/

### Architecture Overview
```
PDF Processing Backends (No Auth)
├── PDF-to-PDF (app.py) - S3, Lambda, ECS, Step Functions
└── PDF-to-HTML (pdf2html/cdk/lib/pdf2html-stack.js) - Lambda only

UI Backend (Optional, With Auth)
└── CdkBackendStack
    ├── Cognito User Pool
    ├── Cognito Identity Pool
    ├── API Gateway (3 endpoints)
    └── Lambda authorizers (implied)
```

### Files Containing Cognito References

1. **Documentation**
   - `_AWS_RESOURCES.md` (Lines 158-159, 198-217, 403-408, 708)
   - `_DEPLOYMENT_SUMMARY.md` (Lines 49-59)
   - `cleanup.sh` (Line 367)

2. **Configuration**
   - `cdk.json` (Line 43 - authorizer context flag)
   - `.env` (Contains environment variables - not in repo)

3. **Code**
   - `app.py` - No Cognito code (CDK generates infrastructure)
   - `pdf2html/cdk/lib/pdf2html-stack.js` - No Cognito code
   - Lambda functions - No Cognito code

### Hardcoded Values That Need Updating

| Value | Current | Files | Count |
|-------|---------|-------|-------|
| User Pool ID | us-east-2_HJtK36MHO | 3 | 3 |
| App Client ID | 7s84oe77h699j77oc6m8cbvogt | 2 | 2 |
| Identity Pool ID | us-east-2:c0f78434... | 2 | 2 |
| Domain | pdf-ui-auth1rc16k | 2 | 2 |

### Security Gaps

| Gap | Impact | Mitigation |
|-----|--------|-----------|
| No explicit token validation | High | Implement custom Lambda authorizer |
| MFANOT enabled by default | Medium | Configure MFFA in IdentityServer4 |
| No refresh token rotation | Medium | Implement token refresh logic |
| Cognito events not configured | Low | Set up CloudWatch monitoring |

## Migration Checklist

### Phase 1: Planning
- [ ] Set up IdentityServer4 instance
- [ ] Configure OIDC client credentials
- [ ] Document all endpoints and scopes
- [ ] Create user migration strategy

### Phase 2: Infrastructure
- [ ] Update CDK to remove Cognito User Pool definition
- [ ] Create Lambda custom authorizer for token validation
- [ ] Configure API Gateway with new authorizer
- [ ] Update Identity Pool for OIDC provider

### Phase 3: Configuration
- [ ] Update all hardcoded references (5 locations)
- [ ] Update environment variables
- [ ] Update documentation files
- [ ] Configure Secrets Manager for IdentityServer4 credentials

### Phase 4: Frontend
- [ ] Replace Cognito SDK with OIDC library
- [ ] Update authentication flows
- [ ] Implement token refresh handling
- [ ] Test all authentication scenarios

### Phase 5: Deployment
- [ ] Test in non-production environment
- [ ] Plan user migration if needed
- [ ] Deploy to production
- [ ] Decommission Cognito resources
- [ ] Verify monitoring and logging

## Critical Implementation Points

### 1. Lambda Custom Authorizer
Need to create Lambda function that:
- Validates JWT tokens from IdentityServer4
- Checks token expiration and scopes
- Maps user claims to IAM context
- Returns IAM policy for allowed/denied access

### 2. API Gateway Configuration
- Replace Cognito authorizer with Lambda authorizer
- Update API resource policies
- Ensure CORS settings match IdentityServer4 domain

### 3. Frontend Changes
Replace:
```javascript
// Old Cognito
import Amplify, { Auth } from 'aws-amplify';
Amplify.configure({ Auth: { userPoolId: '...', ... } });
```

With:
```javascript
// New OIDC
import { UserManager } from 'oidc-client-ts';
const userManager = new UserManager({
  authority: 'https://identityserver4.example.com',
  client_id: 'your-client-id',
  redirect_uri: 'https://your-app.amplifyapp.com/callback'
});
```

## Estimated Effort

- Planning: 5 hours
- Infrastructure: 8 hours
- Configuration: 4 hours
- Frontend: 6 hours
- Testing: 6 hours
- Deployment: 3 hours
- **Total: 32 hours** (~1 week of development)

## Rollback Procedure

1. Checkout previous git commit with Cognito configuration
2. Run `cdk deploy`
3. Restore frontend code from git history
4. Update environment variables to Cognito values
5. Clear browser cache and restart application

Expected rollback time: 15-30 minutes

## Dependencies & Libraries

### For Lambda Authorizer
```
- PyJWT (for JWT validation)
- requests (for HTTP calls)
- cryptography (for RSA key handling)
```

### For Frontend
```
- oidc-client-ts (or similar OIDC client library)
- axios (for HTTP requests with token)
- react-router (for redirect flows)
```

## Testing Strategy

1. **Unit Tests**
   - Token validation logic
   - Claim mapping
   - Error handling

2. **Integration Tests**
   - IdentityServer4 OIDC discovery
   - Token exchange flow
   - API Gateway authorization

3. **End-to-End Tests**
   - User login flow
   - API access with token
   - Token refresh
   - Logout and cleanup

## Monitoring & Logging

### CloudWatch Metrics to Add
- `IdentityServer4TokenValidationFailures`
- `AuthorizationDenied`
- `TokenValidationLatency`
- `UserLoginAttempts`

### Log Groups
- `/aws/lambda/identity-server-authorizer`
- `/aws/apigateway/pdf-accessibility-api`

## Contact & Support

- **Project**: PDF Accessibility Solutions
- **Contact**: ai-cic@amazon.com
- **Documentation**: See COGNITO_ANALYSIS_REPORT.md for detailed analysis

---

**Last Updated**: November 17, 2025
**Status**: Analysis Complete - Ready for Implementation
