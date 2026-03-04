export declare const tokenPath: string;
export interface TokenCache {
    appid: string;
    accessToken: string;
    expireAt: number;
}
declare class TokenStore {
    private cache;
    private initPromise;
    constructor();
    private load;
    private save;
    isValid(appid: string): boolean;
    getToken(appid: string): string | null;
    setToken(appid: string, accessToken: string, expiresIn: number): Promise<void>;
    clear(): Promise<void>;
}
export declare const tokenStore: TokenStore;
export {};
