export interface MediaInfo {
    media_id: string;
    url: string;
    updated_at?: number;
}
declare class UploadCacheStore {
    private cache;
    private initPromise;
    constructor();
    private load;
    private save;
    get(md5: string): Promise<MediaInfo | undefined>;
    set(md5: string, mediaId: string, url: string): Promise<void>;
}
export declare const uploadCacheStore: UploadCacheStore;
export {};
