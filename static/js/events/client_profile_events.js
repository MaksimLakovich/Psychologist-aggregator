export const CLIENT_PROFILE_UPDATED = "clientProfileUpdated";

export function dispatchClientProfileUpdated() {
    document.dispatchEvent(new Event(CLIENT_PROFILE_UPDATED));
}
