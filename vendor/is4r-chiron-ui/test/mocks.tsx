import type {
  AuthDatasetType,
  AuthState,
  AuthUserType,
} from "../src/store/authSlice";

const DEFAULT_CHIRON_VERSION = "v0.0.0";

const DEFAULT_TEST_USER: AuthUserType = {
  id: 1,
  username: "testuser",
  name: "Test User",
  email: "test@example.com",
  chironUserId: 1,
  isStaff: false,
  accessLevel: "deid",
};

const DEFAULT_TEST_USER_DATASET: AuthDatasetType = {
  id: 1,
  name: "Default",
  siteTitle: "TEST Chiron",
};

export const SECOND_TEST_USER_DATASET: AuthDatasetType = {
  id: 2,
  name: "Second",
  siteTitle: "Other App",
};

const DEFAULT_ADMIN_USER: AuthUserType = {
  id: 2,
  username: "adminuser",
  name: "Admin User",
  email: "admin@example.com",
  chironUserId: 2,
  isStaff: true,
  accessLevel: "phi",
};

export const UNAUTHENTICATED_AUTH_STATE: AuthState = {
  user: undefined,
  dataset: undefined,
  chironVersion: DEFAULT_CHIRON_VERSION,
  authStatus: "done",
};

export const AUTHENTICATED_USER_AUTH_STATE: AuthState = {
  user: DEFAULT_TEST_USER,
  dataset: DEFAULT_TEST_USER_DATASET,
  chironVersion: DEFAULT_CHIRON_VERSION,
  authStatus: "done",
};

export const AUTHENTICATED_ADMIN_AUTH_STATE: AuthState = {
  user: DEFAULT_ADMIN_USER,
  dataset: DEFAULT_TEST_USER_DATASET,
  chironVersion: DEFAULT_CHIRON_VERSION,
  authStatus: "done",
};
