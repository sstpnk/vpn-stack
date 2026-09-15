# API Handoff: AmneziaWG 3.1 Config Contract

## Business Context
Freedom Access now supports a server-generated AmneziaWG 3.1 configuration contract in AWG Easy while remaining legacy-safe by default. The admin UI can create clients with old H/I masking fields and, when the server runs in `AWG_PROTOCOL_VERSION=3.1`, additional 3.1 client masking fields. Client applications such as Freedom Cat should import generated `.conf` files as the source of truth instead of inventing defaults.

## Endpoints

### GET /api/wireguard/masking-presets
- **Purpose**: Return current server masking defaults and selectable masking presets for the create-client dialog.
- **Auth**: Requires an authenticated AWG Easy session when `PASSWORD` is configured; public otherwise.
- **Request**: none.
- **Response** (success):
  ```json
  {
    "defaults": {
      "id": "system-defaults",
      "name": "System defaults",
      "description": "Текущие параметры сервера",
      "awgProtocolVersion": "legacy | 3.1",
      "h1": "string numeric value or range",
      "h2": "string numeric value or range",
      "h3": "string numeric value or range",
      "h4": "string numeric value or range",
      "s3": "string numeric value or range",
      "s4": "string numeric value or range",
      "i1": "string packet template",
      "i2": "string packet template",
      "i3": "string packet template",
      "i4": "string packet template",
      "i5": "string packet template",
      "initPacketDelay": "string, empty by default",
      "headerProtectionKey": "string base64 server key, optional env override",
      "contentPaddingAddition": "string numeric value or range",
      "rekeyAfterTime": "string numeric value or range",
      "rekeyTimeout": "string numeric value or range",
      "rejectAfterTime": "string numeric value or range",
      "keepaliveTimeout": "string numeric value or range",
      "maxHandshakeAttempts": "string numeric value or range",
      "randomTrailers": "on | off",
      "disableCookies": "on | off"
    },
    "presets": [
      {
        "id": "tls-chrome",
        "name": "TLS Chrome-like",
        "description": "Preset label",
        "h1": "string",
        "h2": "string",
        "h3": "string",
        "h4": "string",
        "i1": "string",
        "i2": "string",
        "i3": "string",
        "i4": "string",
        "i5": "string"
      }
    ]
  }
  ```
- **Response** (error): `401 {"error":"Not Logged In"}` when password auth is enabled and the session is not authenticated.
- **Notes**: `headerProtectionKey` is a server-owned value. UI must not expose it as a client override; generated client configs receive the persisted server key.

### POST /api/wireguard/client
- **Purpose**: Create a WireGuard/AmneziaWG client and persist optional masking overrides.
- **Auth**: Requires an authenticated AWG Easy session when `PASSWORD` is configured; public otherwise.
- **Request**:
  ```json
  {
    "name": "string, required",
    "maskingPreset": "string preset id, optional",
    "masking": {
      "h1": "string numeric value or range, optional",
      "h2": "string numeric value or range, optional",
      "h3": "string numeric value or range, optional",
      "h4": "string numeric value or range, optional",
      "s3": "string numeric value or range, optional, 3.1 config output only",
      "s4": "string numeric value or range, optional, 3.1 config output only",
      "i1": "string packet template, optional",
      "i2": "string packet template, optional",
      "i3": "string packet template, optional",
      "i4": "string packet template, optional",
      "i5": "string packet template, optional",
      "initPacketDelay": "integer >= 0, optional",
      "contentPaddingAddition": "string numeric value or range, optional, 3.1 config output only",
      "rekeyAfterTime": "string numeric value or range, optional, 3.1 config output only",
      "rekeyTimeout": "string numeric value or range, optional, 3.1 config output only",
      "rejectAfterTime": "string numeric value or range, optional, 3.1 config output only",
      "keepaliveTimeout": "string numeric value or range, optional, 3.1 config output only",
      "maxHandshakeAttempts": "string numeric value or range, optional, 3.1 config output only",
      "randomTrailers": "on | off, optional, 3.1 config output only",
      "disableCookies": "on | off, optional, 3.1 config output only"
    }
  }
  ```
- **Response** (success):
  ```json
  {
    "id": "uuid",
    "name": "string",
    "address": "10.8.0.2",
    "privateKey": "string",
    "publicKey": "string",
    "preSharedKey": "string",
    "createdAt": "ISO 8601 timestamp",
    "updatedAt": "ISO 8601 timestamp",
    "enabled": true,
    "masking": "object, present only when overrides were accepted"
  }
  ```
- **Response** (error): `400` for unknown masking preset or invalid masking field; `401` when unauthenticated; generic error when `name` is missing.
- **Notes**: `maskingPreset` and `masking` are merged with explicit `masking` values taking precedence. Empty strings are ignored. `headerProtectionKey` in `masking` is ignored by design.

### GET /api/wireguard/client/:clientId/configuration
- **Purpose**: Download the generated `.conf` consumed by Freedom Cat and other clients.
- **Auth**: Requires an authenticated AWG Easy session when `PASSWORD` is configured; public otherwise.
- **Request**: none.
- **Response** (success): `text/plain` WireGuard/AmneziaWG config.
- **Response** (error): `404` when the client does not exist; `401` when unauthenticated.
- **Notes**: In legacy mode, the generated config omits all AmneziaWG 3.1-only fields. In 3.1 mode, the generated client config includes `S3`, `S4`, `HeaderProtectionKey`, `ContentPaddingAddition`, `RekeyAfterTime`, `RekeyTimeout`, `RejectAfterTime`, `KeepaliveTimeout`, `MaxHandshakeAttempts`, `RandomTrailers`, and `DisableCookies`.

## Data Models / DTOs

```typescript
type AwgProtocolVersion = 'legacy' | '3.1';
type AwgSwitch = 'on' | 'off';
type AwgNumericOrRange = `${number}` | `${number}-${number}`;

interface MaskingDefaultsDto {
  id: 'system-defaults';
  name: string;
  description: string;
  awgProtocolVersion: AwgProtocolVersion;
  h1: AwgNumericOrRange;
  h2: AwgNumericOrRange;
  h3: AwgNumericOrRange;
  h4: AwgNumericOrRange;
  s3: AwgNumericOrRange;
  s4: AwgNumericOrRange;
  i1: string;
  i2: string;
  i3: string;
  i4: string;
  i5: string;
  initPacketDelay: '';
  headerProtectionKey: string;
  contentPaddingAddition: AwgNumericOrRange;
  rekeyAfterTime: AwgNumericOrRange;
  rekeyTimeout: AwgNumericOrRange;
  rejectAfterTime: AwgNumericOrRange;
  keepaliveTimeout: AwgNumericOrRange;
  maxHandshakeAttempts: AwgNumericOrRange;
  randomTrailers: AwgSwitch;
  disableCookies: AwgSwitch;
}

interface ClientMaskingRequest {
  h1?: AwgNumericOrRange | '';
  h2?: AwgNumericOrRange | '';
  h3?: AwgNumericOrRange | '';
  h4?: AwgNumericOrRange | '';
  s3?: AwgNumericOrRange | '';
  s4?: AwgNumericOrRange | '';
  i1?: string;
  i2?: string;
  i3?: string;
  i4?: string;
  i5?: string;
  initPacketDelay?: number | string | '';
  contentPaddingAddition?: AwgNumericOrRange | '';
  rekeyAfterTime?: AwgNumericOrRange | '';
  rekeyTimeout?: AwgNumericOrRange | '';
  rejectAfterTime?: AwgNumericOrRange | '';
  keepaliveTimeout?: AwgNumericOrRange | '';
  maxHandshakeAttempts?: AwgNumericOrRange | '';
  randomTrailers?: AwgSwitch | '';
  disableCookies?: AwgSwitch | '';
}
```

## Enums & Constants

| Value | Meaning | Display Label |
|-------|---------|---------------|
| `legacy` | Generate the existing AmneziaWG 3.0-compatible contract only. | Legacy |
| `3.1` | Generate the AmneziaWG 3.1 contract and expose 3.1 client masking controls. | AmneziaWG 3.1 |
| `on` | Enabled protocol switch. | on |
| `off` | Disabled protocol switch. | off |

## Validation Rules
- `h1`, `h2`, `h3`, `h4`, `s3`, `s4`, and 3.1 timing/padding/attempt fields must match `^\d+(?:-\d+)?$`.
- `i1` through `i5` must be one or more packet tokens like `<b 0x160301>` or `<r 32>`.
- `initPacketDelay` must be an integer greater than or equal to `0`.
- `randomTrailers` and `disableCookies` must be `on` or `off`.
- Empty strings are ignored and fall back to preset/server defaults during generated config assembly.
- `headerProtectionKey` is generated or read from server env/state and must not be sent as a client-editable field.

## Business Logic & Edge Cases
- `AWG_PROTOCOL_VERSION=legacy` is the default; no 3.1 fields are emitted in server or client configs.
- First enabling `AWG_PROTOCOL_VERSION=3.1` on legacy state migrates server `H1-H4` to `1/2/3/4` compatibility values.
- Existing persisted 3.1 server state is not overwritten by new env defaults except where fields are still missing.
- If `HEADER_PROTECTION_KEY` is not provided, the server generates and persists a 32-byte base64 key in `wg0.json`.
- The generated `.conf` is the integration contract for Freedom Cat import; direct API DTOs are admin-facing.

## Integration Notes
- **Recommended flow**: authenticate if needed, fetch `/api/wireguard/masking-presets`, render the create form, create a client, then fetch `/api/wireguard/client/:clientId/configuration` for import/QR/download.
- **Optimistic UI**: safe only after `POST /api/wireguard/client` succeeds because IP allocation and key generation happen server-side.
- **Caching**: do not cache generated client configs or QR codes; QR endpoint already returns `Cache-Control: no-store`.
- **Real-time**: no websocket contract; refresh client list after create/delete/enable/disable operations.

## Test Scenarios
1. **Legacy happy path**: create a client with default masking while `AWG_PROTOCOL_VERSION=legacy`; downloaded config does not contain `HeaderProtectionKey`, `S3`, `S4`, `RandomTrailers`, or `DisableCookies`.
2. **3.1 happy path**: create a client while `AWG_PROTOCOL_VERSION=3.1`; downloaded config contains the complete 3.1 field set and the server-persisted `HeaderProtectionKey`.
3. **Custom 3.1 masking**: submit `s3`, `s4`, range fields, `randomTrailers`, and `disableCookies`; downloaded client config uses the custom values while server config keeps server defaults.
4. **Invalid masking**: submit a non-numeric range or a switch outside `on/off`; API returns `400`.
5. **Header key protection**: submit `headerProtectionKey` in `masking`; generated config still uses the server key and does not persist the submitted field.

## Open Questions / TODOs
- Docker image build and runtime smoke were not verified locally because Docker CLI is not available on this workstation.
- Freedom Cat importer/runtime compatibility with the generated AWG 3.1 `.conf` still needs Android-side verification.
