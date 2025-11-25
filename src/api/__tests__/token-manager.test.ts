import { TokenManager } from '../token-manager';

describe('token-manager', () => {
  test('init() derives cached token value from local-storage and creates new TokenManager instance', () => {
    const mockGetItem = jest.spyOn(Storage.prototype, 'getItem');
    mockGetItem.mockReturnValueOnce('eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9');

    const tokenManager = TokenManager.init();
    expect(tokenManager.getAuthToken()).toBe('eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9');
  });

  test('revokeAuthToken method sets token to null and removes entry from local-storage', () => {
    const mockGetItem = jest.spyOn(Storage.prototype, 'getItem');
    const mockRemoveItem = jest.spyOn(Storage.prototype, 'removeItem');
    mockGetItem.mockReturnValueOnce('eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9');

    const tokenManager = TokenManager.init();
    expect(tokenManager.getAuthToken()).toBe('eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9');

    tokenManager.revokeAuthToken();
    expect(mockRemoveItem).toHaveBeenCalledTimes(1);
    expect(mockRemoveItem).toHaveBeenCalledWith('authToken');
    expect(tokenManager.getAuthToken()).toBe(null);
  });

  test('updateAuthToken method sets token to value provided via args and updates entry in local-storage', () => {
    const mockGetItem = jest.spyOn(Storage.prototype, 'getItem');
    const mockSetItem = jest.spyOn(Storage.prototype, 'setItem');
    mockGetItem.mockReturnValueOnce('eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9');

    const tokenManager = TokenManager.init();

    tokenManager.updateAuthToken('updated-value');
    expect(tokenManager.getAuthToken()).toBe('updated-value');
    expect(mockSetItem).toHaveBeenCalledTimes(1);
    expect(mockSetItem).toHaveBeenCalledWith('authToken', 'updated-value');
  });

  test('updates listeners when token gets updated', () => {
    const mockListener = jest.fn();

    const tokenManager = TokenManager.init();

    tokenManager.subscribe(mockListener);
    expect(mockListener).toHaveBeenCalledTimes(0);

    tokenManager.updateAuthToken('updated-token-value');
    expect(mockListener).toHaveBeenCalledTimes(1);
    expect(mockListener).toHaveBeenCalledWith('updated-token-value');
  });
});
