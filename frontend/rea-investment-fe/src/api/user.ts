/*
 * TODO: [Cleanup]
 *       This is an illustrative example to show the approach to module structure,
 *       remove the file and references to it when no longer needed
 */

import type { AxiosInstance } from 'axios';

enum Ordering {
  FirstName = 'first_name',
  LastName = 'last_name',
  Role = 'role'
}

enum Direction {
  Asc = 'asc',
  Desc = 'desc'
}

interface LoginData {
  email: string;
  password: string;
}

interface LogoutData {
  token: string;
}

interface Auth {
  access_token: string;
  token_type: string;
}

interface Role {
  id: number;
  name: string;
  description: string;
  created_at: string;
  updated_at: string;
}
interface Roles {
  items: Role[];
}

interface ResetPasswordData {
  email: string;
  token: string;
  password: string;
}

interface CreateUserAttributes {
  email: string;
  phone: string;
  first_name: string;
  last_name: string;
  parent_company_id: number;
  role_id: number;
  sites_ids: number[];
}

interface CreateUserResponse {
  message: string;
  code: number;
}

interface Permissions {
  [key: string]: {
    view: boolean;
    edit: boolean;
  };
}

interface UserRole {
  permissions: Permissions;
  name: string;
  id: number;
  description: string;
}

interface User {
  id: number;
  email: string;
  phone: string;
  first_name: string;
  last_name: string;
  role: UserRole;
  is_registered: boolean;
  parent_company_id: number | null;
  is_system_user: boolean;
  diligence_overview_access: boolean;
}

interface Users {
  skip: number;
  limit: number;
  total: number;
  items: User[];
}

interface Params {
  skip?: number;
  limit?: number;
  search?: string;
  order_by?: Ordering;
  order_direction?: Direction;
}

interface TokenValidationResult {
  message: string;
  code: number;
}

interface SetupPasswordResult {
  message: string;
  code: number;
}

interface Company {
  name: string;
  email: string;
  phone: string;
  address: string;
  company_type: string;
  id: number;
}

interface Site {
  name: string;
  address: string;
  city: string;
  state: string;
  county: string;
  zip_code: string;
  system_size_ac: number;
  system_size_dc: number;
  das: string;
  lon_lat_url: string;
  id: number;
  company: Company;
}

interface UserDetailedInfo {
  email: string;
  first_name: string;
  last_name: string;
  phone: string;
  role: Role;
  sites: Site[];
  parent_company: Company;
}

interface ResendInviteResponse {
  message: string;
  code: number;
}

interface LogoutResponse {
  message: string;
  code: number;
}

type EditUserInfoInputPartial = Omit<CreateUserAttributes, 'first_name' | 'last_name'>;

export const buildUserApi = (httpClient: AxiosInstance) => {
  const login = async (loginData: LoginData): Promise<Auth> => {
    const response = await httpClient.post<Auth>('/api/auth/login', loginData);
    return response.data;
  };
  const logout = async (): Promise<LogoutResponse> => {
    const response = await httpClient.delete<LogoutResponse>('/api/auth/login');
    return response.data;
  };
  const reset = async (resetData: ResetPasswordData): Promise<Auth> => {
    const response = await httpClient.post<Auth>('/api/auth/login', resetData);
    return response.data;
  };
  const roles = async (): Promise<Role[]> => {
    const response = await httpClient.get<Roles>('/api/roles/?skip=0&limit=100');
    return response.data.items;
  };
  const create = async (attributes: CreateUserAttributes): Promise<CreateUserResponse> => {
    const response = await httpClient.post<CreateUserResponse>('/api/users/', attributes);
    return response.data;
  };
  const users = async (params: Params): Promise<Users> => {
    const response = await httpClient.get<Users>('/api/users/', { params });
    return response.data;
  };
  const me = async (): Promise<User> => {
    const response = await httpClient.get<User>('api/users/account/me');
    return response.data;
  };
  const validateEmailToken = async (
    email: string,
    token: string,
    mode: 'sign-up' | 'recovery'
  ): Promise<TokenValidationResult> => {
    const response = await httpClient.get<TokenValidationResult>(
      `/api/users/account/email-token?email=${email}&token=${token}&mode=${mode}`
    );
    return response.data;
  };

  const setupPassword = async (
    email: string,
    token: string,
    password: string,
    mode: 'sign-up' | 'recovery'
  ): Promise<SetupPasswordResult> => {
    const response = await httpClient.post<SetupPasswordResult>(`/api/users/account/password-setup?mode=${mode}`, {
      email,
      token,
      password
    });
    return response.data;
  };
  const getById = async (userId: number): Promise<UserDetailedInfo> => {
    const response = await httpClient.get<UserDetailedInfo>(`/api/users/${userId}`);
    return response.data;
  };

  const edit = async (userId: number, updatedUserInfo: EditUserInfoInputPartial): Promise<void> => {
    await httpClient.put(`/api/users/${userId}`, updatedUserInfo);
    return;
  };

  const resendInvite = async (userId: number): Promise<ResendInviteResponse> => {
    const response = await httpClient.post(`/api/users/${userId}/resend-invite`);
    return response.data;
  };

  return Object.freeze({
    login,
    logout,
    roles,
    reset,
    create,
    users,
    me,
    validateEmailToken,
    setupPassword,
    getById,
    edit,
    resendInvite
  });
};

export type {
  Roles,
  Role,
  Auth as UserAuth,
  LoginData as UserLoginData,
  LogoutData as UserLogoutData,
  ResetPasswordData,
  CreateUserResponse,
  CreateUserAttributes,
  Users,
  User,
  Params,
  UserDetailedInfo,
  EditUserInfoInputPartial
};
