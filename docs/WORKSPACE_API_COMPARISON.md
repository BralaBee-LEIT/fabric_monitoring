# Fabric Workspace API Comparison

This document explains the differences between the three workspace APIs and when to use each.

## API Overview

| API | Endpoint | Scope | Workspaces Returned | Permissions Required |
|-----|----------|-------|---------------------|---------------------|
| **Legacy Fabric** | `/v1/workspaces` | Member access only | ~139 | Standard Fabric API access |
| **Fabric Admin** | `/v1/admin/workspaces` | Tenant-wide | ~286+ | Fabric Administrator role |
| **Power BI Admin** | `/v1.0/myorg/admin/groups` | Tenant-wide | ~286+ | Tenant.Read.All or Power BI Admin |

## 1. Legacy Fabric API (`/v1/workspaces`)

### Endpoint
```
GET https://api.fabric.microsoft.com/v1/workspaces
```

### What It Returns
- Only workspaces where the **authenticated user/service principal is a member**
- Typically returns ~139 workspaces in your organization
- Does **NOT** return all tenant workspaces

### Use Case
- Monitoring activities for workspaces you have access to
- Extracting data from your own workspaces
- **NOT suitable for tenant-wide enforcement**

### Permissions
- Standard Fabric API authentication (service principal or user token)
- No special admin roles required
- Returns empty list if service principal isn't a workspace member

### Example Response
```json
{
  "value": [
    {
      "id": "workspace-guid",
      "displayName": "My Workspace",
      "type": "Workspace"
    }
  ]
}
```

---

## 2. Fabric Admin API (`/v1/admin/workspaces`)

### Endpoint
```
GET https://api.fabric.microsoft.com/v1/admin/workspaces
```

### What It Returns
- **All tenant workspaces** (shared + personal)
- Returns ~286+ workspaces in your organization
- Includes workspaces where you're not a member

### Use Case
- Tenant-wide workspace governance
- Security group enforcement across all workspaces
- Compliance auditing

### Permissions Required (if returns 0 workspaces)

#### 1. Azure AD/Entra ID Role
Assign one of these roles to your service principal:
- **Fabric Administrator** (recommended)
- **Power Platform Administrator**

Steps:
1. Go to: Azure Portal > Entra ID > Roles and administrators
2. Find "Fabric Administrator"
3. Click "Add assignments"
4. Add your service principal (AZURE_CLIENT_ID)

#### 2. Fabric Admin Portal Settings
Enable API access for service principals:
1. Go to: Fabric Admin Portal (https://app.fabric.microsoft.com/admin)
2. Navigate to: Tenant settings > Developer settings
3. Find: "Service principals can use Fabric APIs"
4. Enable it and add your service principal to the allowed list

#### 3. Verify Credentials
Ensure your `.env` file has correct values:
```bash
AZURE_TENANT_ID=dd29478d-624e-429e-b453-fffc969ac768
AZURE_CLIENT_ID=f094d9cc-6618-40af-87ec-1dc422fc12a1
AZURE_CLIENT_SECRET=HAN8Q~slUi0MARo1NkwkRpxIZI-BXxSlvdGGycB_
```

### Filtering Personal Workspaces
```
GET /v1/admin/workspaces?$filter=type ne 'PersonalGroup'
```

### Rate Limits
- More generous than Power BI API
- No documented hard limits
- Recommended: Use $filter to reduce payload size

---

## 3. Power BI Admin API (`/v1.0/myorg/admin/groups`)

### Endpoint
```
GET https://api.powerbi.com/v1.0/myorg/admin/groups
```

### What It Returns
- **All tenant workspaces** (shared + personal)
- Returns 5000+ workspaces (paginated)
- Most reliable for complete tenant inventory

### Use Case
- Tenant-wide workspace governance (when Fabric Admin API unavailable)
- Complete workspace inventory
- **Currently the only API returning all 286+ workspaces**

### Permissions Required

#### Option A: API Permission (App Registration)
1. Go to: Azure Portal > App Registrations > Your app
2. API Permissions > Add permission > Power BI Service
3. Add: **Tenant.Read.All** (Application permission)
4. Click "Grant admin consent"

#### Option B: User Role (Delegated)
- User must have **Power BI Administrator** or **Fabric Administrator** role

### Rate Limits ⚠️
**This API has very strict rate limits!**

- Commonly returns `429: Too Many Requests`
- Retry-After header typically shows 2000-3600 seconds (~30-60 minutes)
- **Solution**: Use `$filter` to exclude personal workspaces

### Filtering Personal Workspaces
```
GET /v1.0/myorg/admin/groups?$filter=type ne 'PersonalGroup'&$top=200&$skip=0
```

This reduces API calls from ~5000 to ~286 (only shared workspaces).

### Pagination
Power BI API requires **manual skip-based pagination**:
```python
skip = 0
page_size = 200
while True:
    url = f"/v1.0/myorg/admin/groups?$top={page_size}&$skip={skip}"
    response = requests.get(url)
    items = response.json()["value"]
    if not items or len(items) < page_size:
        break
    skip += page_size
```

---

## Recommended Configuration

### For Enforcement (Tenant-Wide)
```bash
# Use Power BI API with personal workspace exclusion
python enforce_workspace_access.py \
  --mode assess \
  --api-preference powerbi \
  # Personal workspaces excluded by default
```

### To Include Personal Workspaces
```bash
python enforce_workspace_access.py \
  --mode assess \
  --api-preference powerbi \
  --include-personal-workspaces
```

### For Monitoring (Member Workspaces Only)
```bash
# Use legacy extractor (default in monitor_hub_pipeline.py)
python monitor_hub_pipeline.py --days 7
```

---

## Troubleshooting

### Issue: Only seeing 139 workspaces
**Cause**: Using legacy API `/v1/workspaces` which only returns member workspaces.

**Solution**: Switch to `--api-preference powerbi` or fix Fabric Admin API permissions.

### Issue: Fabric Admin API returns 0 workspaces
**Cause**: Service principal lacks Fabric Administrator role.

**Solution**: Follow "Fabric Admin API > Permissions Required" section above.

### Issue: Power BI API returns 429 rate limit
**Cause**: Too many API calls, hitting rate limits.

**Solutions**:
1. Wait 30-60 minutes for rate limit reset
2. Use `$filter=type ne 'PersonalGroup'` (now enabled by default)
3. Switch to Fabric Admin API if permissions available
4. Reduce `--max-workspaces` for testing

### Issue: Authentication failures
**Verify**:
```bash
# Test Fabric token
python -c "from src.core.auth import create_authenticator_from_env; auth = create_authenticator_from_env(); print(auth.get_fabric_token())"

# Test Power BI token
python -c "from src.core.auth import create_authenticator_from_env; auth = create_authenticator_from_env(); print(auth.get_powerbi_token())"
```

---

## Summary Table: Which API Should I Use?

| Scenario | Recommended API | Reason |
|----------|----------------|--------|
| **Enforcement across ALL workspaces** | Power BI Admin | Returns all 286+ workspaces; most reliable |
| **Activity monitoring (daily/historical)** | Legacy Fabric | Only need member workspaces for activity data |
| **Compliance audit with Fabric admin role** | Fabric Admin | Fastest if permissions configured correctly |
| **Testing/development** | Power BI Admin | Works with Tenant.Read.All permission |
| **Avoiding rate limits** | Any with `exclude_personal_workspaces=True` | Reduces API calls by ~95% |

---

## Environment Variables

Control API behavior via `.env`:

```bash
# API endpoint overrides (defaults shown)
FABRIC_API_BASE_URL=https://api.fabric.microsoft.com
POWERBI_API_BASE_URL=https://api.powerbi.com

# Enforcement preferences
FABRIC_ENFORCER_API_PREFERENCE=auto  # auto|fabric|powerbi
FABRIC_ENFORCER_PAGE_SIZE=200        # Items per page
FABRIC_ENFORCER_TIMEOUT=30           # Request timeout (seconds)
FABRIC_ENFORCER_MAX_RETRIES=3        # Retry attempts on failure

# Rate limiting
API_RATE_LIMIT_REQUESTS_PER_HOUR=180
```

---

## Current State (18 Nov 2025)

- **Legacy API**: Returns 139 member workspaces ✅
- **Fabric Admin API**: Returns 0 (missing Fabric Administrator role) ❌
- **Power BI Admin API**: Returns 286+ workspaces but hitting rate limits ⚠️

**Action Required**: 
1. Enable `exclude_personal_workspaces=True` (now default) to reduce rate limits
2. OR assign Fabric Administrator role to service principal for Fabric Admin API
3. Wait ~34 minutes for current Power BI rate limit to reset
