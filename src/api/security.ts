import type { AxiosInstance } from 'axios';

interface SecurityCamera {
  name: string;
  uuid: string;
}
interface SecurityCameras {
  items: SecurityCamera[];
}

export const buildSecurityApi = (httpClient: AxiosInstance) => {
  const getSecurityCameras = async (): Promise<SecurityCameras> => {
    const response = await httpClient.get<SecurityCameras>(`/api/security/cameras/`);
    return response.data;
  };

  return Object.freeze({
    getSecurityCameras
  });
};

export type { SecurityCamera, SecurityCameras };
