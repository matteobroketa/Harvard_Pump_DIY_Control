# Global Start Controls Design

## Goal

Add two global toolbar actions next to `STOP ALL PUMPS`:

- `START ALL PUMPS`
- `START ALL PROFILES`

These actions should operate across all current pump sessions while preserving each panel's local settings and existing execution logic.

## Scope

This design covers:

- main-window toolbar changes,
- global orchestration across connected sessions,
- fallback behavior for sessions without a loaded profile,
- user messaging for fallback cases,
- test coverage for the new global actions.

This design does not introduce scheduled absolute-time profile starts, new persistence, or changes to per-session profile semantics.

## Behavior

### Start All Pumps

When the user presses `START ALL PUMPS`:

- iterate over all current sessions,
- skip sessions that are not connected,
- for each connected session, use that panel's current manual control settings,
- apply the manual rate/units/direction using the existing manual path,
- run the pump in the selected direction.

The intent is that this global action behaves like pressing each panel's manual `Set Rate` and `Run` controls in rapid succession from a single command.

### Start All Profiles

When the user presses `START ALL PROFILES`:

- iterate over all current sessions,
- skip sessions that are not connected,
- for each connected session with at least one profile segment, start that session's loaded profile,
- for each connected session without a loaded profile, fall back to that panel's current manual control settings and start the pump manually instead.

This action should dispatch all starts from one handler as tightly together as the UI thread allows. Millisecond-level skew is acceptable; no stronger synchronization mechanism is required for this change.

### Fallback Notification

After `START ALL PROFILES` completes dispatch:

- if every connected session had a loaded profile, show no popup,
- if one or more connected sessions fell back to manual mode, show a gentle informational popup,
- the popup should identify the affected pump session numbers and state that they were started using manual control because no profile was loaded.

This is informational only. It must not block the starts from happening.

## Architecture

### Main Window Responsibilities

`main_window.py` remains the owner of global toolbar actions and the list of active sessions. It will gain:

- the two new toolbar buttons,
- handlers for global manual start and global profile start,
- logic to locate the panel object associated with each session when panel-owned state is required.

Because manual settings and loaded profiles currently live in `PumpPanelWidget`, the main window needs access to panel helpers rather than trying to duplicate panel state.

### Panel Responsibilities

`pump_panel_widget.py` will expose small helper methods for global orchestration:

- a helper to report whether the panel has a loaded profile,
- a helper to start manual control using the panel's current manual UI values,
- a helper to start the current loaded profile using the same code path as the local `START Profile` button.

These helpers should delegate to existing handlers or session methods so behavior stays consistent between local and global controls.

### Session Responsibilities

`pump_session.py` should not gain new orchestration state unless implementation reveals a missing primitive. Existing `set_rate`, `run`, and `start_profile` entry points are sufficient for the intended behavior.

## Error Handling

- Unconnected sessions are ignored by both global start actions.
- Existing per-session error signaling remains the source of pump-specific failures.
- A missing profile during `START ALL PROFILES` is not an error; it triggers manual fallback plus the informational popup.
- If a profile is already running on a session, existing session-level protections continue to decide the outcome.

## Testing

Add focused tests around global orchestration behavior:

- `START ALL PUMPS` starts only connected sessions using panel manual settings.
- `START ALL PROFILES` starts profile-backed sessions via profile start.
- `START ALL PROFILES` falls back to manual start for connected sessions with no profile.
- `START ALL PROFILES` shows an informational popup only when fallback occurred.

Tests should verify behavior through the public handler methods and mocked session/popup interactions, rather than duplicating implementation details.

## Implementation Notes

- Keep the new logic minimal and centered in `MainWindow`.
- Reuse the current per-panel start handlers rather than rebuilding manual/profile logic at the window layer.
- Store or discover panel references in a straightforward way so the global handlers can invoke panel helpers safely.
