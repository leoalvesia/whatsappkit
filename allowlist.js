/**
 * Allowlist utility for the WhatsApp Bridge
 */

export function parseAllowedUsers(allowedUsersStr) {
  const users = new Set();
  if (!allowedUsersStr) return users;
  allowedUsersStr.split(',').forEach(u => {
    const trimmed = u.trim();
    if (trimmed) users.add(trimmed);
  });
  return users;
}

export function matchesAllowedUser(senderId, allowedUsersSet, sessionDir) {
  if (allowedUsersSet.has('*')) return true;
  const cleanSender = senderId.replace(/@.*/, '').replace(/:.*/, '');
  return allowedUsersSet.has(cleanSender);
}
