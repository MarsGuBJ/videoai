# SXin iframe URL change

## Goal

Point the SXin assistant iframe at:

`http://10.10.3.100:81/iot-os/sxin/#/mockLogin`

## Scope

- Replace the existing hard-coded iframe `src` in `frontend/src/App.tsx`.
- Preserve the iframe title, route, layout, styling, and surrounding behavior.
- Do not change the existing `sxin-proxy` service or other deployment ports.

## Verification

1. Add an automated source assertion that fails while the old iframe URL remains.
2. Update the iframe URL and confirm the assertion passes.
3. Build the frontend successfully.
4. Deploy the rebuilt frontend to `10.10.3.100`.
5. Confirm the deployed page contains the exact target iframe URL.

## Rollback

Restore the previous iframe URL and rebuild the frontend image.
