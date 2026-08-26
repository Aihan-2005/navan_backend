import type {
  DefaultSession,
} from "@auth/core/types";


type AppUserRole =
  | "user"
  | "admin";


type AuthSessionError =
  | "RefreshAccessTokenError";


declare module "@auth/core/types" {
  interface User {
    username?:
      string | null;

    identifier?:
      string | null;

    role?:
      AppUserRole;

    backendAccessToken?:
      string;

    backendRefreshToken?:
      string;

    backendAccessTokenExpiresAt?:
      number;
  }


  interface Session {
    user: {
      id: string;

      username:
        string | null;

      identifier:
        string | null;

      role:
        AppUserRole;
    } & DefaultSession["user"];

    /**
     * Short-lived Django access token.
     *
     * Refresh token is intentionally
     * NOT exposed on Session.
     */
    backendAccessToken?:
      string;

    authError?:
      AuthSessionError;
  }
}


declare module "@auth/core/jwt" {
  interface JWT {
    id?:
      string;

    username?:
      string | null;

    identifier?:
      string | null;

    role?:
      AppUserRole;

    backendAccessToken?:
      string;

    backendRefreshToken?:
      string;

    backendAccessTokenExpiresAt?:
      number;

    authError?:
      AuthSessionError;
  }
}