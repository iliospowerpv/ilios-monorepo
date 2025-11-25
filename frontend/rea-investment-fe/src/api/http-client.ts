import axios from 'axios';
import { TokenManager } from './token-manager';

let baseURL = '';
const timeout = 30000;

if (typeof process.env.REACT_APP_URL === 'string') {
  baseURL = process.env.REACT_APP_URL;
}

const httpClient = axios.create({
  baseURL,
  timeout
});

const tokenManager = TokenManager.init();

setupAuthHeaders(tokenManager.getAuthToken());
tokenManager.subscribe(setupAuthHeaders);

httpClient.interceptors.response.use(
  response => {
    return response;
  },
  async error => {
    if (error.response?.status == 401) {
      // revoke access token to direct the user to the login page
      tokenManager.revokeAuthToken();
    }
    throw error;
  }
);

function setupAuthHeaders(token: string | null): void {
  if (token) {
    httpClient.defaults.headers.common['Authorization'] = `bearer ${token}`;
    return;
  }
  delete httpClient.defaults.headers.common['Authorization'];
}

export { httpClient, tokenManager };
