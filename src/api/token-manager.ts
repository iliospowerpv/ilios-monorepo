const LS_AUTH_TOKEN_KEY = 'authToken';

type TokenChangeListener = (token: string | null) => void;

export class TokenManager {
  private token: string | null;
  private listeners: TokenChangeListener[];

  private constructor(token: string | null) {
    this.token = token;
    this.listeners = [];
  }

  public static init(): TokenManager {
    const storedToken = window.localStorage.getItem(LS_AUTH_TOKEN_KEY);
    const instance = new TokenManager(storedToken);
    return instance;
  }

  public getAuthToken(): string | null {
    return this.token;
  }

  public revokeAuthToken(): void {
    this.token = null;
    window.localStorage.removeItem(LS_AUTH_TOKEN_KEY);
    this.notify();
  }

  public updateAuthToken(token: string) {
    this.token = token;
    window.localStorage.setItem(LS_AUTH_TOKEN_KEY, token);
    this.notify();
  }

  public subscribe(listener: TokenChangeListener): void {
    const exist = this.listeners.includes(listener);
    if (exist) return;

    this.listeners.push(listener);
  }

  public unsubscribe(listener: TokenChangeListener): void {
    const listenerIndex = this.listeners.indexOf(listener);
    if (listenerIndex === -1) return;

    this.listeners.splice(listenerIndex, 1);
  }

  private notify(): void {
    for (const notify of this.listeners) {
      notify(this.token);
    }
  }
}
