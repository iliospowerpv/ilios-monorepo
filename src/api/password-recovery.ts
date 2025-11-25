import type { AxiosInstance } from 'axios';

interface Recovery {
  code: number;
  message: string;
}

interface ResetRequestData {
  email: string;
}

interface EmailTokenData {
  email: string;
  token: string;
}

interface ResetSetupData {
  password: string;
  email: string;
  token: string;
}

export const buildRecoveryApi = (httpClient: AxiosInstance) => {
  const emailToken = async (data: EmailTokenData): Promise<Recovery> => {
    const response = await httpClient.get<Recovery>(
      `/api/users/account/email-token?email=${data.email}&token=${data.token}&mode=recovery`
    );
    return response?.data;
  };

  const resetSetup = async (resetData: ResetSetupData): Promise<Recovery> => {
    const response = await httpClient.post<Recovery>('/api/users/account/password-setup?mode=recovery', resetData);
    return response?.data;
  };

  const resetRequest = async (resetData: ResetRequestData): Promise<Recovery> => {
    const response = await httpClient.post<Recovery>('/api/users/account/password-recovery', resetData);
    return response?.data;
  };

  return Object.freeze({
    emailToken,
    resetSetup,
    resetRequest
  });
};

export type { Recovery, ResetRequestData, EmailTokenData, ResetSetupData };
