# SecretariatPro V1 — Licensing and access rules

## Commercial plans

### Solo
- 1 broadcaster account
- 1 competition
- 1 shared visual identity
- Manager included
- Match assignment included
- Live included

### Club
- 1 broadcaster account
- Up to 3 competitions
- 1 shared visual identity
- Manager included
- Match assignment included
- Live included

### Competition
- Up to 3 broadcaster accounts
- Up to 3 competitions
- Separate visual identity per competition
- Manager included
- Match assignment included
- Live included

### Federation
- High volume / custom limits
- Commercial contact required
- Custom broadcasters, competitions, identity and support

## Device rule
A broadcaster or manager account may have only one active device identity within a rolling 72-hour device-change window.

Recommended enforcement:
1. Generate a stable installation/device ID in Live/Manager.
2. Store `current_device_id`, `device_bound_at` and `last_seen_at` in Supabase.
3. On login, compare the current installation ID with the stored ID.
4. If different and fewer than 72 hours have elapsed since the last device binding, reject login and explain when the device can be changed again.
5. Allow an administrator/support override for legitimate hardware replacement.
6. This must be enforced server-side (Supabase/Edge Function or RPC), not only in the desktop UI.

The website states this commercial/access policy, but the actual 72-hour enforcement still has to be implemented in Live/Manager and Supabase for V1.
