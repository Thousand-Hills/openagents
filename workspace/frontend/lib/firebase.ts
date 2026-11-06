import { initializeApp, getApps, getApp } from 'firebase/app';
import {
  getAuth,
  GoogleAuthProvider,
  signInWithPopup,
  signInWithCustomToken,
  signOut,
  onAuthStateChanged,
  onIdTokenChanged,
  type User,
} from 'firebase/auth';

// Thousand Hills fork: the web config comes from build args (frontend
// Dockerfile) instead of OpenAgents' own `openagentsweb` project. No fallback
// to their project on purpose: a build without these must fail sign-in, not
// log users into someone else's identity tenant.
const firebaseConfig = {
  apiKey: process.env.NEXT_PUBLIC_FIREBASE_API_KEY,
  authDomain: process.env.NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN,
  projectId: process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID,
  appId: process.env.NEXT_PUBLIC_FIREBASE_APP_ID,
};

const app = !getApps().length ? initializeApp(firebaseConfig) : getApp();
const auth = getAuth(app);

const googleProvider = new GoogleAuthProvider();
// `hd` only pre-selects Workspace accounts in Google's chooser; the backend
// enforces the domain.
const hostedDomain = process.env.NEXT_PUBLIC_GOOGLE_HOSTED_DOMAIN;
googleProvider.setCustomParameters({ prompt: 'select_account', ...(hostedDomain ? { hd: hostedDomain } : {}) });

export async function signInWithGoogle() {
  const result = await signInWithPopup(auth, googleProvider);
  return result.user;
}

/**
 * Sign in with a Firebase custom token minted by the openagents.org backend
 * (POST /v1/auth/workspace-handoff). Establishes a native, self-refreshing
 * Firebase session on this origin — the workspace app can't inherit the
 * openagents.org session because Firebase persists auth per-origin.
 */
export async function signInWithCustomTokenValue(customToken: string) {
  const result = await signInWithCustomToken(auth, customToken);
  return result.user;
}

export async function signOutUser() {
  await signOut(auth);
}

export function onAuthChange(callback: (user: User | null) => void) {
  return onAuthStateChanged(auth, callback);
}

/**
 * Like onAuthChange, but also fires whenever the SDK refreshes the ID token
 * (hourly while the page is open). Use this for anything that sends the token:
 * a token captured once at sign-in expires after an hour, and since Workspace
 * v1.1 the backend rejects writes that carry an expired identity rather than
 * falling back to the workspace token.
 */
export function onIdTokenChange(callback: (user: User | null) => void) {
  return onIdTokenChanged(auth, callback);
}

/** The current ID token, refreshed by the SDK if it has expired. `force`
 *  mints a new one regardless (used after the server rejected the old one). */
export async function getFreshIdToken(force = false): Promise<string | null> {
  const user = auth.currentUser;
  if (!user) return null;
  return user.getIdToken(force);
}

export async function getIdToken(): Promise<string | null> {
  const user = auth.currentUser;
  if (!user) return null;
  return user.getIdToken(true);
}

/**
 * Resolve the user's email. Real Firebase accounts (Google/GitHub) expose it as
 * `user.email`; users signed in via a custom token (the email/password handoff)
 * carry it only as an `email` custom claim on the ID token, so fall back to that.
 */
export async function getResolvedEmail(): Promise<string> {
  const user = auth.currentUser;
  if (!user) return '';
  if (user.email) return user.email;
  try {
    const res = await user.getIdTokenResult();
    return (res.claims.email as string) || '';
  } catch {
    return '';
  }
}

export { auth };
